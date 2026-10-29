import collections
import itertools
import math
import re

import maya.api.OpenMaya as om
import maya.cmds as cmds
import maya.mel as mel

import nnutil.core as nu
import nnutil.ui as ui
import nnutil.decorator as nd

from . import rectilinearize

window_name = "NN_UVToolkit"
window = None


def get_window():
    return window


MSG_NOT_IMPLEMENTED = "未実装"


@nd.repeatable
def OnewayMatchUV(mode):
    MM_BACK_TO_FRONT = 0
    MM_UNPIN_TO_PIN = 1
    MM_FRONT_TO_BACK = 2
    MM_PIN_TO_UNPIN = 3

    if mode is None:
        match_mode = MM_BACK_TO_FRONT
    elif mode == "front":
        match_mode = MM_BACK_TO_FRONT
    elif mode == "back":
        match_mode = MM_FRONT_TO_BACK
    elif mode == "pin":
        match_mode = MM_UNPIN_TO_PIN
    elif mode == "unpin":
        match_mode = MM_PIN_TO_UNPIN
    else:
        print("unknown match mode: ", mode)
        match_mode = MM_BACK_TO_FRONT

    # 選択UV
    selected_uvs = cmds.ls(selection=True, flatten=True)

    # シェル変換したUV
    cmds.SelectUVShell()
    uvs = cmds.ls(selection=True, flatten=True)

    # 全バックフェース取得
    cmds.SelectUVBackFacingComponents()
    uvs_back = list(set(cmds.ls(selection=True, flatten=True)) & set(uvs))

    # 全フロントフェース取得
    cmds.SelectUVFrontFacingComponents()
    uvs_front = list(set(cmds.ls(selection=True, flatten=True)) & set(uvs))

    # 選択内で pin 取得
    uvs_pined = []
    uvs_unpined = []
    for uv in uvs:
        pin_weight = cmds.polyPinUV(uv, q=True, v=True)[0]
        if pin_weight != 0:
            uvs_pined.append(uv)
        else:
            uvs_unpined.append(uv)

    # 積集合で選択UVをソースとターゲットに分ける
    source_uvs = []
    target_uvs = []
    if match_mode == MM_BACK_TO_FRONT:
        source_uvs = list(set(uvs_front) & set(uvs))
        target_uvs = list(set(uvs_back) & set(uvs))
    elif match_mode == MM_UNPIN_TO_PIN:
        source_uvs = list(set(uvs_pined) & set(uvs))
        target_uvs = list(set(uvs_unpined) & set(uvs))
    elif match_mode == MM_FRONT_TO_BACK:
        source_uvs = list(set(uvs_back) & set(uvs))
        target_uvs = list(set(uvs_front) & set(uvs))
    elif match_mode == MM_UNPIN_TO_PIN:
        source_uvs = list(set(uvs_unpined) & set(uvs))
        target_uvs = list(set(uvs_pined) & set(uvs))
    else:
        pass

    target_uvs = list(set(target_uvs) & set(selected_uvs))

    # ターゲット.each
    for target_uv in target_uvs:
        nearest_uv = source_uvs[0]
        for source_uv in source_uvs:
            if nu.distance_uv(target_uv, source_uv) < nu.distance_uv(target_uv, nearest_uv):
                nearest_uv = source_uv
        nu.copy_uv(target_uv, nearest_uv)
        # TODO:複数のターゲットが束ねられて閉まったソースのセットを作成or選択状態にする

    cmds.select(clear=True)


@nd.repeatable
def snap_uv_to_pin():
    """選択UVを同一頂点を共有する別のUVのうちピンされた物にスナップする"""
    selected_uvs = cmds.ls(selection=True, flatten=True)
    pinned_uvs = [uv for uv in selected_uvs if cmds.polyPinUV(uv, query=True, value=True)[0]]

    for uv in selected_uvs:
        # ピン済みはスキップ
        if uv in pinned_uvs:
            continue

        # UV を頂点に変換した後 UV に再変換し同一頂点を共有する UV を取得
        vertices = cmds.polyListComponentConversion(uv, toVertex=True)
        uv_comps = cmds.polyListComponentConversion(vertices, toUV=True)
        uv_comps = cmds.filterExpand(uv_comps, selectionMask=35)

        # UV座標を取得
        uv_coords = [cmds.polyEditUV(uv_comp, query=True) for uv_comp in uv_comps]

        # 頂点を共有する UV にピンされたものがあればスナップする
        for uv_comp, uv_coord in zip(uv_comps, uv_coords):
            if uv_comp in selected_uvs and uv_comp in pinned_uvs:
                cmds.polyEditUV(uv, u=uv_coord[0], v=uv_coord[1], relative=False)
                break


@nd.repeatable
def half_expand_fold(right_down=True):
    """
    right_down=True で横なら右、縦なら下へ畳む
    """
    # フリップの軸
    FA_U = 0
    FA_V = 1
    flip_axis = FA_U

    # フリップ方向
    # fold 時のみ使用
    FD_TO_LEFT = 0
    FD_TO_RIGHT = 1
    FD_TO_UP = 2
    FD_TO_DOWN = 3
    flip_direction = FD_TO_LEFT

    # 選択UV取得
    selected_uvs = cmds.ls(selection=True, flatten=True)
    cmds.SelectUVShell()
    selected_sehll_uvs = cmds.ls(selection=True, flatten=True)

    if len(selected_uvs) == 0:
        return

    # フリップ軸の決定
    u_dist = [cmds.polyEditUV(x, q=True)[0] for x in selected_uvs]
    u_length = max(u_dist) - min(u_dist)
    v_dist = [cmds.polyEditUV(x, q=True)[1] for x in selected_uvs]
    v_length = max(v_dist) - min(v_dist)

    if u_length < v_length:
        flip_axis = FA_U
        if right_down:
            flip_direction = FD_TO_RIGHT
        else:
            flip_direction = FD_TO_LEFT
    else:
        flip_axis = FA_V
        if right_down:
            flip_direction = FD_TO_DOWN
        else:
            flip_direction = FD_TO_UP

    # 選択UVからピボット決定
    selected_uv_coord_list = [nu.get_uv_coord(x) for x in selected_uvs]
    piv_u = sum([x[0] for x in selected_uv_coord_list]) / len(selected_uv_coord_list)
    piv_v = sum([x[1] for x in selected_uv_coord_list]) / len(selected_uv_coord_list)

    # 裏面の UV 取得
    # expand 用 (expand の操作対象を "軸の外側UV" にすると四つ折りfoldができるけど折ったきりexpandできなくなる)
    backface_uvs = nu.filter_backface_uv_comp(selected_sehll_uvs)

    # 編集対象 UV
    target_uvs = []

    # 編集対象の決定
    if len(backface_uvs) > 0:
        # 裏面があれば裏面が編集対象 (expand動作)
        target_uvs = backface_uvs
    else:
        # 裏面が無ければフリップ外側のUVを編集対象にする (fold動作)
        # 軸よりもフリップ反対方向の UV 取得
        if flip_direction == FD_TO_LEFT:
            target_uvs = [x for x in selected_sehll_uvs if nu.get_uv_coord(x)[0] > piv_u]
        if flip_direction == FD_TO_RIGHT:
            target_uvs = [x for x in selected_sehll_uvs if nu.get_uv_coord(x)[0] < piv_u]
        if flip_direction == FD_TO_UP:
            target_uvs = [x for x in selected_sehll_uvs if nu.get_uv_coord(x)[1] < piv_v]
        if flip_direction == FD_TO_DOWN:
            target_uvs = [x for x in selected_sehll_uvs if nu.get_uv_coord(x)[1] > piv_v]

    # スケール値の決定
    su = 1
    sv = 1

    if flip_axis == FA_U:
        su = -1
    if flip_axis == FA_V:
        sv = -1

    # ピボットを指定して反転処理
    cmds.polyEditUV(target_uvs, pu=piv_u, pv=piv_v, su=su, sv=sv)

    cmds.select(clear=True)


def get_uv_pivot():
    current_context = cmds.currentCtx()

    if current_context == "moveSuperContext":
        return cmds.texMoveContext("texMoveContext", q=True, position=True)

    elif current_context == "rotateSuperContext":
        return cmds.texRotateContext("texRotateContext", q=True, position=True)

    elif current_context == "scaleSuperContext":
        return cmds.texScaleContext("texScaleContext", q=True, position=True)

    else:
        return None


@nd.repeatable
def translate_uv(pivot, translate):
    """ 選択中 UV の移動

    Args:
        pivot ([type]): [description]
        translate ([type]): [description]
    """
    cmds.polyEditUV(pu=pivot[0], pv=pivot[1], u=translate[0], v=translate[1])


@nd.repeatable
def scale_uv(pivot=None, scale=(1.0, 1.0)):
    """ 選択中 UV のスケール

    Args:
        pivot ([type]): [description]
        scale ([type]): [description]
    """

    if not pivot:
        uv_pivot = get_uv_pivot()

        if uv_pivot:
            pivot = uv_pivot

        else:
            pivot = (0.0, 0.0)

    cmds.polyEditUV(scale=True, pu=pivot[0], pv=pivot[1], scaleU=scale[0], scaleV=scale[1])


@nd.repeatable
def rotate_uv(angle):
    """ 選択中 UV の回転

    Args:
        pivot ([type]): [description]
        angle ([type]): [description]
    """
    mel.eval("polyRotateUVs %f 1" % angle)


def _get_uv_shell_ids(node):
    """node のカレント UV セットの、UV インデックスごとの UV シェル ID を返す"""
    selection_list = om.MSelectionList()
    selection_list.add(node)
    dag_path = selection_list.getDagPath(0).extendToShape()

    return om.MFnMesh(dag_path).getUvShellsIds()[1]


def _get_uv_center_and_area(faces):
    """faces の UV のバウンディングボックス中心と UV 面積の合計を返す。UV が無ければ None"""
    uvs = cmds.polyListComponentConversion(faces, fromFace=True, toUV=True)

    if not uvs:
        return None

    coords = cmds.polyEditUV(uvs, q=True)
    us = coords[0::2]
    vs = coords[1::2]
    center = ((min(us) + max(us)) / 2, (min(vs) + max(vs)) / 2)
    area = sum(abs(face_area) for face_area in cmds.polyEvaluate(faces, uvFaceArea=True))

    return center, area


def _restore_uv_center_and_area(faces, center, area):
    """faces の UV をスケールと移動で、UV 面積の合計とバウンディングボックス中心が指定の値になるようにする"""
    current = _get_uv_center_and_area(faces)

    if current is None:
        return

    current_center, current_area = current
    uvs = cmds.polyListComponentConversion(faces, fromFace=True, toUV=True)

    # 3D の面積は変わらないので、UV 面積を戻せばテクセル密度も戻る
    if area > 0 and current_area > 0:
        scale = (area / current_area) ** 0.5
        cmds.polyEditUV(uvs, pivotU=current_center[0], pivotV=current_center[1], scaleU=scale, scaleV=scale)

    cmds.polyEditUV(uvs, uValue=center[0] - current_center[0], vValue=center[1] - current_center[1])


def _project_planer(projection_command, each_shell, keep_position):
    """
    projection_command を実行する
    each_shell なら選択をフェースに変換して現在の UV シェルごとに分け、シェルごとに実行する
    keep_position なら実行単位ごとに、実行後の UV のバウンディングボックス中心とテクセル密度を実行前の値に戻す
    each_shell / keep_position のどちらかが有効なら、選択は実行前の状態に戻す
    """
    if not each_shell and not keep_position:
        mel.eval(projection_command)

        return

    selection = cmds.ls(selection=True)
    faces = cmds.filterExpand(cmds.polyListComponentConversion(selection, toFace=True), selectionMask=34) or []

    if each_shell:
        face_groups = _group_faces_by_uv_shell(faces)
    else:
        face_groups = [faces] if faces else []

    for faces_in_group in face_groups:
        center_and_area = _get_uv_center_and_area(faces_in_group) if keep_position else None

        cmds.select(faces_in_group, replace=True)
        mel.eval(projection_command)

        if center_and_area is not None:
            _restore_uv_center_and_area(faces_in_group, *center_and_area)

    cmds.select(selection, replace=True)


def _group_faces_by_uv_shell(faces):
    """faces を現在の UV シェルごとに分けたフェースのリストのリストを返す"""
    # (ノード名, シェル ID) ごとにフェースを分ける。シェル ID はフェースの最初の UV のもの。UV の無いフェースは 1 つにまとめる
    shell_faces = collections.defaultdict(list)
    shell_ids_by_node = dict()
    for face in faces:
        node = re.match(r"(.+)\.f\[\d+\]", face).groups()[0]
        uvs = cmds.filterExpand(cmds.polyListComponentConversion(face, fromFace=True, toUV=True), selectionMask=35)
        shell_id = None
        if uvs:
            if node not in shell_ids_by_node:
                shell_ids_by_node[node] = _get_uv_shell_ids(node)

            shell_id = shell_ids_by_node[node][int(re.search(r"\.map\[(\d+)\]", uvs[0]).groups()[0])]

        shell_faces[(node, shell_id)].append(face)

    return list(shell_faces.values())


@nd.repeatable
def project_planer_x(each_shell=False, keep_position=False):
    _project_planer("polyProjection -type Planar -ibd on -kir -md x", each_shell, keep_position)


@nd.repeatable
def project_planer_y(each_shell=False, keep_position=False):
    _project_planer("polyProjection -type Planar -ibd on -kir -md y", each_shell, keep_position)


@nd.repeatable
def project_planer_z(each_shell=False, keep_position=False):
    _project_planer("polyProjection -type Planar -ibd on -kir -md z", each_shell, keep_position)


@nd.repeatable
def project_planer_camera(each_shell=False, keep_position=False):
    _project_planer("polyProjection -type Planar -ibd on -kir -md camera", each_shell, keep_position)


@nd.repeatable
def project_planer_best(each_shell=False, keep_position=False):
    _project_planer("polyProjection -type Planar -ibd on -kir -md b;", each_shell, keep_position)


@nd.repeatable
def straighten_border():
    mel.eval("StraightenUVBorder")


@nd.repeatable
def straighten_inner():
    mel.eval("texStraightenShell")


@nd.repeatable
def straighten_all():
    mel.eval("UVStraighten")


@nd.repeatable
def linear_align():
    """選択UVコンポーネントのうち最も遠い2点を始点と終点としてそれ以外のUVを始点終点を結ぶ直線上に整列する｡"""
    uvs = cmds.ls(selection=True, flatten=True)
    uvs = cmds.filterExpand(uvs, sm=35)
    if not uvs or len(uvs) < 2:
        print("2つ以上のUVを選択してください")
        return

    # UV座標取得
    uv_coords = {uv: cmds.polyEditUV(uv, q=True) for uv in uvs}

    # 最も遠い2点を探す
    max_dist = -1
    uvA, uvB = None, None
    uv_list = list(uv_coords.items())
    for i in range(len(uv_list)):
        for j in range(i+1, len(uv_list)):
            a, ca = uv_list[i]
            b, cb = uv_list[j]
            d = (ca[0]-cb[0])**2 + (ca[1]-cb[1])**2
            if d > max_dist:
                max_dist = d
                uvA, uvB = a, b

    if uvA is None or uvB is None:
        print("最遠点ペアが見つかりません")
        return

    A = uv_coords[uvA]
    B = uv_coords[uvB]
    AB = [B[0]-A[0], B[1]-A[1]]
    ab_len = (AB[0]**2 + AB[1]**2) ** 0.5
    if ab_len == 0:
        print("2点が同じ座標です")
        return

    # 各点を直線上に再配置
    for uv, C in uv_coords.items():
        if uv == uvA:
            cmds.polyEditUV(uv, u=A[0], v=A[1], relative=False)
        elif uv == uvB:
            cmds.polyEditUV(uv, u=B[0], v=B[1], relative=False)
        else:
            # AC, CBベクトル
            AC = [C[0]-A[0], C[1]-A[1]]
            t = (AC[0]*AB[0] + AC[1]*AB[1]) / (ab_len**2)
            # AC:CB比率
            ac_len = (AC[0]**2 + AC[1]**2) ** 0.5
            cb_len = ab_len - ac_len
            if ab_len == 0:
                ratio = 0.5
            else:
                ratio = ac_len / ab_len
            # 新しい位置
            new_u = A[0] + AB[0] * ratio
            new_v = A[1] + AB[1] * ratio
            cmds.polyEditUV(uv, u=new_u, v=new_v, relative=False)

    print("UVを直線上に整列しました")


@nd.repeatable
def ari_gridding():
    mel.eval("AriUVGridding")


@nd.repeatable
def _rectilinearize(corner_uv_comps=None, target_texel=15, map_size=1024):
    rectilinearize.main(corner_uv_comps=corner_uv_comps, target_texel=target_texel, map_size=map_size)


@nd.repeatable
def get_texel(eb_texel, mapsize):
    """
    UVシェル、もしくはUVエッジのテクセルを設定
    shell選択ならMayaの機能を使用し それ以外なら独自のUVエッジに対するテクセル設定モードを使用する
    """
    isUVShellSelection = cmds.selectType(q=True, msh=True)
    isFaceSelection = cmds.selectType(q=True, pf=True)
    isUVSelection = cmds.selectType(q=True, puv=True)

    if isUVShellSelection or isFaceSelection:
        # Maya の機能でテクセル取得
        uvTkTexel = mel.eval("texGetTexelDensity(%d)" % mapsize)

        # ダイアログの値更新
        ui.set_value(eb_texel, uvTkTexel)

    elif isUVSelection:
        uvComponents = cmds.ls(os=True)
        uvComponents = cmds.filterExpand(cmds.ls(os=True), sm=35)

        uv1 = cmds.polyEditUV(uvComponents[0], q=True)
        uv2 = cmds.polyEditUV(uvComponents[1], q=True)
        vtxComponent1 = cmds.polyListComponentConversion(uvComponents[0], fuv=True, tv=True)
        vtxComponent2 = cmds.polyListComponentConversion(uvComponents[1], fuv=True, tv=True)
        p1 = cmds.xform(vtxComponent1, q=True, ws=True, t=True)
        p2 = cmds.xform(vtxComponent2, q=True, ws=True, t=True)
        geoLength = nu.distance(p1, p2)
        uvLength = nu.distance2d(uv1, uv2)
        currentTexel = uvLength / geoLength * mapsize

        # ダイアログの値を更新
        ui.set_value(eb_texel, currentTexel)
    else:
        print(MSG_NOT_IMPLEMENTED)


@nd.repeatable
def set_texel(texel, mapsize):
    """
    UVシェル、もしくはUVエッジのテクセルを設定
    shell選択ならMayaの機能を使用し それ以外なら独自のUVエッジに対するテクセル設定モードを使用する
    """
    isUVShellSelection = cmds.selectType(q=True, msh=True)
    if isUVShellSelection:
        mel.eval("texSetTexelDensity %f %d" % (texel, mapsize))
    else:
        set_edge_texel(target_texel=texel, mapsize=mapsize, mode="uv")


@nd.repeatable
def set_edge_texel(target_texel, mapsize, mode):
    """
    UVエッジを指定のテクセル密度にする
    エッジ選択モードならすべてのエッジに
    UV選択モードなら選択した第一UVと第二UVの距離に
    """
    isUVSelection = cmds.selectType(q=True, puv=True)
    isEdgeSelection = cmds.selectType(q=True, pe=True)

    targetUVsList = []  # UVコンポーネント文字列のリストのリスト list[list[str, str]]
    uvComponents = []

    # エッジ選択モードならエッジを構成する 2 頂点の UV をペアとして targetUVsList に追加する
    if isEdgeSelection:
        edges = cmds.filterExpand(cmds.ls(os=True), sm=32)
        for edge in edges:
            uvComponents = cmds.filterExpand(cmds.polyListComponentConversion(edge, fe=True, tuv=True), sm=35)
            if len(uvComponents) == 2:  # 非UVシーム
                targetUVsList.append(uvComponents)
            elif len(uvComponents) == 4:  # UVシーム
                targetUVsList.append([uvComponents[0], uvComponents[2]])
                targetUVsList.append([uvComponents[1], uvComponents[3]])
            else:
                pass

    # UV選択モードならエッジを共有する UV 同士をペアにして targetUVsList に追加する
    elif isUVSelection:
        edge_uv_dict = dict()
        uvComponents = cmds.filterExpand(cmds.ls(os=True), sm=35)

        for uvCompStr in uvComponents:
            edgeCompStrList = cmds.filterExpand(cmds.polyListComponentConversion(uvCompStr, fuv=True, te=True), sm=32)
            faceCompStrList = cmds.filterExpand(cmds.polyListComponentConversion(uvCompStr, fuv=True, tf=True), sm=34)

            for edgeCompStr in edgeCompStrList:
                for faceCompStr in faceCompStrList:
                    ei = re.search(r"\[(\d+)\]", edgeCompStr).groups()[0]
                    fi = re.search(r"\[(\d+)\]", faceCompStr).groups()[0]
                    key = "e%sf%s" % (ei, fi)

                    if key not in edge_uv_dict.keys():
                        edge_uv_dict[key] = []

                    edge_uv_dict[key].append(uvCompStr)

        for uvPair in edge_uv_dict.values():
            if len(set(uvPair)) == 2:
                targetUVsList.append(uvPair)

    if not isEdgeSelection and not isUVSelection:
        return

    if mode in ("u_min", "u_max", "v_min", "v_max"):
        _set_edge_texel_along_axis(targetUVsList, target_texel=target_texel, mapsize=mapsize, mode=mode)

        return

    for uvPair in targetUVsList:
        uv1 = cmds.polyEditUV(uvPair[0], q=True)  # ペアの 1 つめの UV座標を持つリスト
        uv2 = cmds.polyEditUV(uvPair[1], q=True)  # ペアの 2 つめの UV座標を持つリスト
        vtxComponent1 = cmds.polyListComponentConversion(uvPair[0], fuv=True, tv=True)  # uv1 に対応する ポリゴン頂点のコンポーネント文字列
        vtxComponent2 = cmds.polyListComponentConversion(uvPair[1], fuv=True, tv=True)  # uv2 に対応する ポリゴン頂点のコンポーネント文字列
        p1 = cmds.xform(vtxComponent1, q=True, ws=True, t=True)  # uv1 の XYZ 座標
        p2 = cmds.xform(vtxComponent2, q=True, ws=True, t=True)  # uv2 の XYZ 座標
        geoLength = nu.distance(p1, p2)
        uvLength = nu.distance2d(uv1, uv2)

        print(MSG_NOT_IMPLEMENTED)
        currentTexel = uvLength / geoLength * mapsize
        scale = target_texel / currentTexel
        cmds.polyEditUV(uvPair[0], pu=uv1[0], pv=uv1[1], su=scale, sv=scale)
        cmds.polyEditUV(uvPair[1], pu=uv1[0], pv=uv1[1], su=scale, sv=scale)


def _set_edge_texel_along_axis(targetUVsList, target_texel, mapsize, mode):
    """
    UVペアの U または V 方向の長さを指定のテクセル密度にする
    ペアごとに順にスケールすると動いた UV が隣の UV を追い越して向きが反転するため、
    処理前の座標で各ペアの向きを記録しておき、連結した UV ごとに起点から長さを積み上げて座標を決める
    起点は連結した UV のうち min モードなら最小、max モードなら最大の座標を持つ UV で、起点自身は動かない
    """
    axis = 0 if mode in ("u_min", "u_max") else 1
    useMin = mode in ("u_min", "v_min")

    # 処理前の UV 座標
    uvCoords = dict()
    for uvPair in targetUVsList:
        for uvComp in uvPair:
            if uvComp not in uvCoords:
                uvCoords[uvComp] = cmds.polyEditUV(uvComp, q=True)

    # UV ごとに隣接する UV と、処理後の (隣接 UV の座標 - 自身の座標) を持つ
    adjacency = {uvComp: [] for uvComp in uvCoords}
    for uvPair in targetUVsList:
        vtxComponent1 = cmds.polyListComponentConversion(uvPair[0], fromUV=True, toVertex=True)
        vtxComponent2 = cmds.polyListComponentConversion(uvPair[1], fromUV=True, toVertex=True)
        p1 = cmds.xform(vtxComponent1, q=True, worldSpace=True, translation=True)
        p2 = cmds.xform(vtxComponent2, q=True, worldSpace=True, translation=True)
        targetLength = nu.distance(p1, p2) * target_texel / mapsize

        # 処理前の向きを保つ。同じ座標にある UV 同士は同じ座標のままにする
        diff = uvCoords[uvPair[1]][axis] - uvCoords[uvPair[0]][axis]
        sign = (diff > 0) - (diff < 0)
        adjacency[uvPair[0]].append((uvPair[1], sign * targetLength))
        adjacency[uvPair[1]].append((uvPair[0], -sign * targetLength))

    newCoords = dict()  # 処理後の axis 方向の座標
    for startUV in uvCoords:
        if startUV in newCoords:
            continue

        # startUV と連結した UV を集める
        component = [startUV]
        visited = {startUV}
        queue = collections.deque([startUV])
        while queue:
            uvComp = queue.popleft()
            for neighbor, _ in adjacency[uvComp]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    component.append(neighbor)
                    queue.append(neighbor)

        # 起点から辿って座標を決める。ループしている場合は先に決まった座標を優先する
        if useMin:
            anchor = min(component, key=lambda uvComp: uvCoords[uvComp][axis])
        else:
            anchor = max(component, key=lambda uvComp: uvCoords[uvComp][axis])

        newCoords[anchor] = uvCoords[anchor][axis]
        queue = collections.deque([anchor])
        while queue:
            uvComp = queue.popleft()
            for neighbor, offset in adjacency[uvComp]:
                if neighbor not in newCoords:
                    newCoords[neighbor] = newCoords[uvComp] + offset
                    queue.append(neighbor)

    for uvComp, coord in newCoords.items():
        newCoord = list(uvCoords[uvComp])
        newCoord[axis] = coord
        cmds.polyEditUV(uvComp, uValue=newCoord[0], vValue=newCoord[1], relative=False)

def _unfold_unpinned(unfold_command):
    """選択を UV に変換し、ピンされた UV を除外して unfold を実行する。選択は実行前の状態に戻す"""
    selection = cmds.ls(selection=True)
    uvs = cmds.filterExpand(cmds.polyListComponentConversion(selection, tuv=True), selectionMask=35) or []

    # unfold はピンを無視するため、ピンされた UV を処理対象から外す
    unpinned_uvs = [uv for uv in uvs if not cmds.polyPinUV(uv, query=True, value=True)[0]]

    if unpinned_uvs:
        cmds.select(unpinned_uvs, replace=True)
        mel.eval(unfold_command)

    cmds.select(selection, replace=True)


@nd.repeatable
def unfold_u():
    _unfold_unpinned("unfold -i 5000 -ss 0.001 -gb 0 -gmb 0.5 -pub 0 -ps 0 -oa 2 -us off")


@nd.repeatable
def unfold_v():
    _unfold_unpinned("unfold -i 5000 -ss 0.001 -gb 0 -gmb 0.5 -pub 0 -ps 0 -oa 1 -us off")


@nd.repeatable
def texel_equalize():
    """選択 UV を UV シェルごとに分けて、それぞれ _texel_equalize_uvs で並べ直す"""
    selection = cmds.ls(selection=True)
    uvs = cmds.filterExpand(cmds.polyListComponentConversion(selection, toUV=True), selectionMask=35) or []

    # (ノード名, シェル ID) ごとに UV を分ける
    shell_uvs = collections.defaultdict(list)
    shell_ids_by_node = dict()
    for uv in uvs:
        node, uv_index = re.match(r"(.+)\.map\[(\d+)\]", uv).groups()
        if node not in shell_ids_by_node:
            shell_ids_by_node[node] = _get_uv_shell_ids(node)

        shell_uvs[(node, shell_ids_by_node[node][int(uv_index)])].append(uv)

    for uvs_in_shell in shell_uvs.values():
        _texel_equalize_uvs(uvs_in_shell)


def _texel_equalize_uvs(uvs):
    """
    UV のうち最も離れた 2 点を結ぶ直線上に UV を並べ直し、テクセル密度を統一する
    2 点は動かさず、間の UV は直線へ射影した位置の順に、隣り合う UV の頂点間の 3D 距離に比例する間隔で配置する
    統一後のテクセル密度は 2 点間の UV 距離と、並べた順に辿った 3D 距離の合計で決まる
    """
    if len(uvs) < 3:
        return

    uv_points = [om.MPoint(u, v, 0) for u, v in (cmds.polyEditUV(uv, q=True) for uv in uvs)]

    # 最も離れた 2 点
    start_index, end_index = max(itertools.combinations(range(len(uvs)), 2), key=lambda pair: uv_points[pair[0]].distanceTo(uv_points[pair[1]]))
    start_point = uv_points[start_index]
    direction = uv_points[end_index] - start_point

    if direction.length() == 0:
        return

    # 間の UV は直線へ射影した位置の順に並べる
    middle_indices = [i for i in range(len(uvs)) if i not in (start_index, end_index)]
    middle_indices.sort(key=lambda i: (uv_points[i] - start_point) * direction)
    ordered_indices = [start_index] + middle_indices + [end_index]

    positions = [om.MPoint(cmds.xform(cmds.polyListComponentConversion(uvs[i], fromUV=True, toVertex=True), q=True, worldSpace=True, translation=True)) for i in ordered_indices]
    lengths = [positions[i].distanceTo(positions[i + 1]) for i in range(len(positions) - 1)]
    total_length = sum(lengths)

    if total_length == 0:
        return

    accumulated_length = 0.0
    for i, uv_index in enumerate(middle_indices):
        accumulated_length += lengths[i]
        new_point = start_point + direction * (accumulated_length / total_length)
        cmds.polyEditUV(uvs[uv_index], uValue=new_point.x, vValue=new_point.y, relative=False)


@nd.repeatable
def match_uv():
    mel.eval("texMatchUVs 0.01")


@nd.repeatable
def match_uv_options():
    mel.eval("MatchUVsOptions")


@nd.repeatable
def match_uv_oneway(mode):
    OnewayMatchUV(mode=mode)


@nd.repeatable
def expand_fold_rightdown():
    half_expand_fold(True)


@nd.repeatable
def expand_fold_leftup():
    half_expand_fold(False)


# フリップ方向
FD_U = "u"
FD_V = "v"


@nd.repeatable
def flip_in_tile(pivot=None, direction=FD_U):
    cmds.ConvertSelectionToUVs()
    uv_comp = cmds.ls(selection=True, flatten=True)[0]
    uv_coord = cmds.polyEditUV(uv_comp, query=True)
    u = uv_coord[0]
    v = uv_coord[1]

    if not pivot:
        pivot = (u // 1 + 0.5, v // 1 + 0.5)

    cmds.SelectUVShell()

    if direction == FD_U:
        cmds.polyEditUV(pu=pivot[0], pv=pivot[1], su=-1, sv=1)

    elif direction == FD_V:
        cmds.polyEditUV(pu=pivot[0], pv=pivot[1], su=1, sv=-1)

    else:
        raise Exception("unknown flip mode")


@nd.repeatable
def sew_matching_edges():
    edges = cmds.ls(selection=True, flatten=True)

    for edge in edges:
        uvs = nu.to_uv(edge)
        if len(uvs) > 2:
            uv_coords = [nu.round_vector(nu.get_uv_coord(x), 4) for x in uvs]
            print(edge)
            unique_uv = set([tuple(x) for x in uv_coords])
            print(len(unique_uv))
            if len(unique_uv) == 2:
                cmds.polyMapSew(edge, ch=1)


def get_flip_pivot(ui_pivot_u, ui_pivot_v):
    uvs = cmds.ls(selection=True, flatten=True)
    uv_coords = nu.split_n_pair(cmds.polyEditUV(uvs, q=True), 2)
    avg_u = sum([uv_coord[0] for uv_coord in uv_coords]) / len(uv_coords)
    avg_v = sum([uv_coord[1] for uv_coord in uv_coords]) / len(uv_coords)
    ui.set_value(ui_pivot_u, avg_u)
    ui.set_value(ui_pivot_v, avg_v)


@nd.repeatable
def orient_shells():
    # エッジが選択されていれば OrientEdge を実行し、そうでなければ OrientShells を実行する
    edges = cmds.filterExpand(cmds.ls(selection=True), selectionMask=32)

    if edges:
        mel.eval("texOrientEdge")
    else:
        mel.eval("texOrientShells")


@nd.repeatable
def symmetry_arrange():
    pass


@nd.repeatable
def snap_stack():
    mel.eval("texSnapStackShells")


@nd.repeatable
def stack():
    mel.eval("texStackShells({})")


@nd.repeatable
def unstack():
    mel.eval("UVUnstackShells")


@nd.repeatable
def normalize():
    mel.eval("polyNormalizeUV -normalizeType 1 -preserveAspectRatio on -centerOnTile on -normalizeDirection 0")


@nd.repeatable
def layout_shells(mapsize, margin, scale):
    """選択を含む UV シェル全体を、選択シェルのバウンディングボックス内にレイアウトする

    シェル間のパディングは既定値の場合 mipmap を考慮してテクスチャ長辺の 1/128 取る

    Args:
        mapsize (int): テクスチャの解像度 (px)
        margin (int): シェル間の間隔 (px)。負数の場合は既定値を使う
        scale (bool): False の場合は u3dLayout に layoutScaleMode=1 を指定する
    """
    # 一部のフェースのみの選択でもシェル全体を対象にする
    cmds.select(cmds.polyListComponentConversion(toUV=True), replace=True)
    mel.eval("polySelectBorderShell 0")
    uvs = cmds.ls(selection=True, flatten=True)

    if not uvs:
        return

    # シェル間隔とタイル余白をピクセルで決めてから UV 空間の値に変換する
    if margin < 0:
        spacing_px = mapsize / 128.0
        tile_margin_px = mapsize / 256.0
    else:
        spacing_px = float(margin)
        tile_margin_px = spacing_px / 2

    spacing = spacing_px / mapsize
    tile_margin = tile_margin_px / mapsize

    # 選択 UV のバウンディングボックスを求める
    coords = cmds.polyEditUV(uvs, q=True)
    umin, umax = min(coords[0::2]), max(coords[0::2])
    vmin, vmax = min(coords[1::2]), max(coords[1::2])

    # -mar は box の内側に取られるため、実行のたびに mar 分ずれないよう box を mar だけ外側に広げる
    umin -= tile_margin
    umax += tile_margin
    vmin -= tile_margin
    vmax += tile_margin
    faces = cmds.filterExpand(cmds.polyListComponentConversion(uvs, fromUV=True, toFace=True), selectionMask=34)

    # -res はパッキングのラスタ解像度で、低いとシェル間隔の誤差が大きくなるため 4096 を下限にする
    resolution = max(mapsize, 4096)

    # -spc は UV 座標値ではなくシェルの大きさに対する比率なので、UV 空間での間隔になるよう逆算する
    # -mar は UV 座標値そのままなので変換しない
    if scale:
        # シェルのスケールが有効の場合、事前に spc が求められないため一度レイアウトした結果の大きさを元に spc を再計算しもう一度レイアウトする
        cmds.u3dLayout(uvs, resolution=resolution, shellSpacing=spacing / _get_layout_spacing_base(faces), tileMargin=tile_margin, packBox=(umin, umax, vmin, vmax))
        cmds.u3dLayout(uvs, resolution=resolution, shellSpacing=spacing / _get_layout_spacing_base(faces), tileMargin=tile_margin, packBox=(umin, umax, vmin, vmax))
    else:
        cmds.u3dLayout(uvs, resolution=resolution, shellSpacing=spacing / _get_layout_spacing_base(faces), tileMargin=tile_margin, packBox=(umin, umax, vmin, vmax), layoutScaleMode=1)


def _get_layout_spacing_base(faces):
    """u3dLayout の -spc の基準となる長さを返す

    実測では、レイアウト後のシェル間隔は -spc x sqrt(UV 面積の合計 + シェルごとの UV バウンディングボックス面積の合計) になる
    """
    area = sum(abs(face_area) for face_area in cmds.polyEvaluate(faces, uvFaceArea=True))

    for shell_faces in _group_faces_by_uv_shell(faces):
        coords = cmds.polyEditUV(cmds.polyListComponentConversion(shell_faces, fromFace=True, toUV=True), q=True)
        us = coords[0::2]
        vs = coords[1::2]
        area += (max(us) - min(us)) * (max(vs) - min(vs))

    return math.sqrt(area)


@nd.repeatable
def uv_lattice_tool():
    mel.eval("LatticeUVTool")


@nd.repeatable
def uv_tweak_tool():
    mel.eval("setToolTo texTweakSuperContext")


@nd.repeatable
def uv_cut_tool():
    mel.eval("setToolTo texCutUVContext")


@nd.repeatable
def uv_optimize_tool():
    mel.eval("setToolTo texUnfoldUVContext")


@nd.repeatable
def uv_symmetrize_tool():
    mel.eval("setToolTo texSymmetrizeUVContext")


@nd.repeatable
def set_uv_symmetrize_center():
    """ シンメトライズツールの中心座標を設定する
    """
    uv = nu.get_selection()[0]
    uv_coord = nu.get_uv_coord(uv)

    cmds.optionVar(fv=["polySymmetrizeUVAxisOffset", uv_coord[0]])
    mel.eval("SymmetrizeUVContext -e -ap `optionVar -q polySymmetrizeUVAxisOffset` texSymmetrizeUVContext;")


@nd.repeatable
def convert_to_shell_border():
    mel.eval("ConvertSelectionToUVs")
    mel.eval("ConvertSelectionToUVShellBorder")


@nd.repeatable
def convert_to_shell_inner():
    mel.eval("ConvertSelectionToUVShell")
    mel.eval("ConvertSelectionToUVs")
    mel.eval("PolySelectTraverse 2")


@nd.repeatable
def select_all_uv_borders():
    mel.eval("SelectUVBorderComponents")


@nd.repeatable
def shortest_edge_tool():
    mel.eval("SelectShortestEdgePathTool")


@nd.repeatable
def select_front_face():
    pass


@nd.repeatable
def select_backface(self, *args):
    pass


@nd.repeatable
def display_uveditor():
    mel.eval("TextureViewWindow")


@nd.repeatable
def display_uvtoolkit():
    mel.eval("toggleUVToolkit")


@nd.repeatable
def uv_snapshot_options():
    mel.eval("performUVSnapshot")


@nd.repeatable
def set_checker_density(n):
    texWinName = cmds.getPanel(sty="polyTexturePlacementPanel")[0]
    cmds.textureWindow(texWinName, e=True, checkerDensity=n)


@nd.repeatable
def toggle_checker():
    checkered = cmds.textureWindow("polyTexturePlacementPanel1", q=True, displayCheckered=True)
    cmds.textureWindow("polyTexturePlacementPanel1", e=True, displayCheckered=(not checkered))


@nd.repeatable
def draw_edge(map_size):
    from . import draw_image as de
    import nnutil.core as nu

    save_dir = nu.get_project_root() + "/images/"
    filepath = save_dir + "draw_edges.svg"
    mapSize = ui.get_value(map_size)
    de.draw_edge(filepath=filepath, imagesize=mapSize)


class NN_ToolWindow(object):
    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (1, 1)

    def create(self, parent_to_uveditor=False):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)

        if parent_to_uveditor:
            # UV エディターのウィンドウ名を取得
            all_uv_panels = cmds.getPanel(scriptType="polyTexturePlacementPanel")
            uv_panel = all_uv_panels[0] if all_uv_panels else None
            uv_window = cmds.panel(uv_panel, q=True, control=True)
            parent_window = uv_window.split("|")[0] if uv_window else None
            print("1")

        if parent_to_uveditor and parent_window:
            cmds.window(
                self.window,
                t=self.title,
                maximizeButton=False,
                minimizeButton=False,
                widthHeight=self.size,
                sizeable=False,
                resizeToFitChildren=True,
                parent=parent_window)
        else:
            cmds.window(
                self.window,
                t=self.title,
                maximizeButton=False,
                minimizeButton=False,
                widthHeight=self.size,
                resizeToFitChildren=True,
                sizeable=False)

        self.layout()
        cmds.showWindow(self.window)

        ui.set_value(self.mapSize, 1024)

    def layout(self):
        with ui.column_layout() as self.columnLayout:

            # Projection
            with ui.row_layout():
                ui.header(label='Projection')
                ui.button(label='X', c=self.onPlanerX, bgc=ui.color_x)
                ui.button(label='Y', c=self.onPlanerY, bgc=ui.color_y)
                ui.button(label='Z', c=self.onPlanerZ, bgc=ui.color_z)
                #ui.button(label='Camera', c=self.onPlanerCamera)
                ui.button(label='Best', c=self.onPlanerBest)
                self.cb_projection_each_shell = ui.check_box(label="each shell")
                self.cb_projection_keep_pos = ui.check_box(label="keep pos")

            # Align & Snap
            with ui.row_layout():
                ui.header(label='Align')
                ui.button(label='Border', c=self.onStraightenBorder)
                ui.button(label='Inner', c=self.onStraightenInner)
                ui.button(label='All', c=self.onStraightenAll)
                ui.button(label='Linear', c=self.onLinearAlign)

            with ui.row_layout():
                ui.header(label='')
                ui.button(label='AriGridding', c=self.onGridding)
                ui.button(label='Rectilinearize', c=self.onRectilinearize)
                ui.button(label='MatchUV', c=self.onMatchUV, dgc=self.onMatchUVOptions, annotation="L: Match UV\nM: Options")

            # MatchUV
            with ui.row_layout():
                ui.header(label='MatchUV')
                ui.button(label='to Front [back]', c=self.onOnewayMatchUVF, dgc=self.onOnewayMatchUVB, width=ui.button_width3, annotation="L: to Front\nM: to Back")
                ui.button(label='to Pin [unpin]', c=self.onOnewayMatchUVP, dgc=self.onOnewayMatchUVUp, width=ui.button_width3, annotation="L: to Pined\nM: to UnPined")
                ui.button(label='to Shared', c=self.onOnewayMatchUVS, width=ui.button_width3, annotation="")

            with ui.row_layout():
                ui.header(label='')
                ui.button(label='expand/fold', c=self.onExpandFoldRD, dgc=self.onExpandFoldLU, annotation="L: to Right/Bottom\nM: to Left/Top")

            # Flip
            with ui.row_layout():
                ui.header(label="Flip")
                ui.button(label='FlipU', c=self.onFlipUinTile, dgc=self.onFlipUinTilePiv, bgc=ui.color_u, annotation="L: at Tile Center\nM: at Pivot")
                ui.button(label='FlipV', c=self.onFlipVinTile, dgc=self.onFlipVinTilePiv, bgc=ui.color_v, annotation="L: at Tile Center\nM: at Pivot")
                self.flip_pivot_u = ui.eb_float(width=ui.button_width2)
                self.flip_pivot_v = ui.eb_float(width=ui.button_width2)
                ui.button(label="get", width=ui.button_width1, c=self.onGetFlipPivot)

            # Cut & Sew
            with ui.row_layout():
                ui.header(label='Cut & Sew')
                ui.button(label='Cut', c=self.onCut)
                ui.button(label='Sew', c=self.onSew)
                ui.button(label='Shell', c=self.onCreateShell)
                ui.button(label='Merge', c=self.onMerge)

            # Optimize
            with ui.row_layout():
                ui.header(label='Optimize')
                ui.button(label='Get', c=self.onGetTexel)
                self.texel = ui.eb_float(v=10, width=ui.button_width2)
                self.mapSize = ui.eb_int(width=ui.button_width1_5)
                ui.text(label='px')

            with ui.row_layout():
                ui.header(label='')
                ui.button(label='Set', c=self.onSetTexel)
                ui.button(label='U', c=self.onSetEdgeTexelUMin, dgc=self.onSetEdgeTexelUMax, bgc=ui.color_u, annotation="L: base on Min\nM: base on Max")
                ui.button(label='V', c=self.onSetEdgeTexelVMin, dgc=self.onSetEdgeTexelVMax, bgc=ui.color_v, annotation="L: base on Min\nM: base on Max")
                ui.button(label='Equalize', c=self.onTexelEqualize)

            with ui.row_layout():
                ui.header(label='')
                ui.button(label='UnfoldU', c=self.onUnfoldU, bgc=ui.color_u)
                ui.button(label='UnfoldV', c=self.onUnfoldV, bgc=ui.color_v)

            # Checker
            with ui.row_layout():
                ui.header(label='Checker')
                ui.text(label="dense:")
                self.checkerDensity = ui.eb_int(v=256, cc=self.onChangeUVCheckerDensity, width=ui.button_width1_5)
                ui.button(label='/2', c=self.onUVCheckerDensityDiv2)
                ui.button(label='x2', c=self.onUVCheckerDensityMul2)
                ui.button(label="Toggle", c=self.onToggleChecker)

            # Layout
            with ui.row_layout():
                ui.header(label='Layout')
                ui.button(label='Orient Shells', c=self.onOrientShells)
                ui.button(label='SymArrange', c=self.onSymArrange)

            with ui.row_layout():
                ui.header(label='')
                ui.button(label='SanpStack', c=self.onSnapStack)
                ui.button(label='Stack', c=self.onStack)
                ui.button(label='Unstack', c=self.onUnStack)
                ui.button(label='Normalize', c=self.onNormalize)

            with ui.row_layout():
                ui.header(label='')
                ui.button(label='Layout', c=self.onLayout, width=ui.width(4))
                ui.text(label='margin (px):')
                self.layout_margin = ui.eb_int(v=-1, width=ui.width(1))
                self.cb_layout_scale = ui.check_box(label="scale", v=False)

            # Tools
            with ui.row_layout():
                ui.header(label='Tools')
                ui.button(label='Lattice', c=self.onUVLatticeTool)
                ui.button(label='Tweak', c=self.onUVTweakTool)
                ui.button(label='Cut', c=self.onUVCutTool)
                ui.button(label='Optimize', c=self.onUVOptimizeTool)

            with ui.row_layout():
                ui.header(label='')
                ui.button(label='Symmetrize [setU]', c=self.onUVSymmetrizeTool, dgc=self.onSetUVSymmetrizeCenter, annotation="L: Symmetrize\nM: Set Center")
                ui.button(label='Shortest Tool', c=self.onShortestEdgeTool)

            # Convert
            with ui.row_layout():
                ui.header(label='Convert')
                ui.button(label='to Border', c=self.onConvertToShellBorder)
                ui.button(label='to Inner', c=self.onConvertToShellInner)

            # Select
            with ui.row_layout():
                ui.header(label='Select')
                ui.button(label='Frontface', c=self.onSelectFrontface)
                ui.button(label='Backface', c=self.onSelectBackface)
                ui.button(label='All Borders', c=self.onSelectAllUVBorders)

            # Transform
            with ui.row_layout():
                ui.header(label='Transform')
                ui.text(label='Move')
                self.translateValue = ui.eb_float(v=0.1, width=ui.button_width2)
                ui.button(label=u'←', c=self.onTranslateUDiff, bgc=ui.color_u)
                ui.button(label=u'→', c=self.onTranslateUAdd, bgc=ui.color_u)
                ui.button(label=u'↑', c=self.onTranslateVAdd, bgc=ui.color_v)
                ui.button(label=u'↓', c=self.onTranslateVDiff, bgc=ui.color_v)
                self.cb_transform_in_pixel = ui.check_box(label="px")

            with ui.row_layout():
                ui.header(label='')
                ui.header(label='Rotate')
                self.rotationAngle = ui.eb_float(v=90, width=ui.button_width2)
                ui.button(label=u'←', c=self.onRotateLeft)
                ui.button(label=u'→', c=self.onRotateRight)

            with ui.row_layout():
                ui.header(label='')
                ui.header(label='Scale')
                self.scaleValue = ui.eb_float(v=2, width=ui.button_width2)
                ui.button(label='U*', c=self.onOrigScaleUMul, bgc=ui.color_u)
                ui.button(label='U/', c=self.onOrigScaleUDiv, bgc=ui.color_u)
                ui.button(label='V*', c=self.onOrigScaleVMul, bgc=ui.color_v)
                ui.button(label='V/', c=self.onOrigScaleVDiv, bgc=ui.color_v)

            # Editor
            with ui.row_layout():
                ui.header(label="Editor")
                ui.button(label='UVEditor', c=self.onUVEditor)
                ui.button(label='UVToolkit', c=self.onUVToolKit)
                ui.button(label='UVSnapShot', c=self.onUVSnapShot)
                ui.button(label='DrawEdge', c=self.onDrawEdge)

            with ui.row_layout():
                ui.header(label="")
                ui.button(label="Grid Layout", c=self.onGridLayout)
                ui.button(label="Parent to UVEditor", c=self.onParentToUVEditor)

    # ハンドラ
    @nd.undo_chunk
    def onTranslateUAdd(self, *args):
        v = ui.get_value(self.translateValue)

        if ui.get_value(self.cb_transform_in_pixel):
            v *= 1.0 / ui.get_value(self.mapSize)

        translate_uv(pivot=(0, 0), translate=(v, 0))

    @nd.undo_chunk
    def onTranslateUDiff(self, *args):
        v = ui.get_value(self.translateValue)

        if ui.get_value(self.cb_transform_in_pixel):
            v *= 1.0 / ui.get_value(self.mapSize)

        translate_uv(pivot=(0, 0), translate=(-v, 0))

    @nd.undo_chunk
    def onTranslateVAdd(self, *args):
        v = ui.get_value(self.translateValue)

        if ui.get_value(self.cb_transform_in_pixel):
            v *= 1.0 / ui.get_value(self.mapSize)

        translate_uv(pivot=(0, 0), translate=(0, v))

    @nd.undo_chunk
    def onTranslateVDiff(self, *args):
        v = ui.get_value(self.translateValue)

        if ui.get_value(self.cb_transform_in_pixel):
            v *= 1.0 / ui.get_value(self.mapSize)

        translate_uv(pivot=(0, 0), translate=(0, -v))

    @nd.undo_chunk
    def onOrigScaleUMul(self, *args):
        v = ui.get_value(self.scaleValue)
        scale_uv(scale=(v, 1))

    @nd.undo_chunk
    def onOrigScaleVMul(self, *args):
        v = ui.get_value(self.scaleValue)
        scale_uv(scale=(1, v))

    @nd.undo_chunk
    def onOrigScaleUDiv(self, *args):
        v = ui.get_value(self.scaleValue)
        scale_uv(scale=(1.0/v, 1))

    @nd.undo_chunk
    def onOrigScaleVDiv(self, *args):
        v = ui.get_value(self.scaleValue)
        scale_uv(scale=(1, 1.0/v))

    @nd.undo_chunk
    def onRotateLeft(self, *args):
        angle = ui.get_value(self.rotationAngle)
        rotate_uv(angle=angle)

    @nd.undo_chunk
    def onRotateRight(self, *args):
        angle = ui.get_value(self.rotationAngle)
        rotate_uv(angle=-angle)

    @nd.undo_chunk
    def onPlanerX(self, *args):
        project_planer_x(each_shell=ui.get_value(self.cb_projection_each_shell), keep_position=ui.get_value(self.cb_projection_keep_pos))

    @nd.undo_chunk
    def onPlanerY(self, *args):
        project_planer_y(each_shell=ui.get_value(self.cb_projection_each_shell), keep_position=ui.get_value(self.cb_projection_keep_pos))

    @nd.undo_chunk
    def onPlanerZ(self, *args):
        project_planer_z(each_shell=ui.get_value(self.cb_projection_each_shell), keep_position=ui.get_value(self.cb_projection_keep_pos))

    @nd.undo_chunk
    def onPlanerCamera(self, *args):
        project_planer_camera(each_shell=ui.get_value(self.cb_projection_each_shell), keep_position=ui.get_value(self.cb_projection_keep_pos))

    @nd.undo_chunk
    def onPlanerBest(self, *args):
        project_planer_best(each_shell=ui.get_value(self.cb_projection_each_shell), keep_position=ui.get_value(self.cb_projection_keep_pos))

    @nd.undo_chunk
    def onStraightenBorder(self, *args):
        straighten_border()

    @nd.undo_chunk
    def onStraightenInner(self, *args):
        straighten_inner()

    @nd.undo_chunk
    def onStraightenAll(self, *args):
        straighten_all()

    @nd.undo_chunk
    def onLinearAlign(self, *args):
        linear_align()

    @nd.undo_chunk
    def onGridding(self, *args):
        ari_gridding()

    @nd.undo_chunk
    def onRectilinearize(self, *args):
        target_texel = ui.get_value(self.texel)
        map_size = ui.get_value(self.mapSize)
        _rectilinearize(target_texel=target_texel, map_size=map_size)

    @nd.undo_chunk
    def onGetTexel(self, *args):
        """
        UVシェル、もしくはUVエッジのテクセルを設定
        shell選択ならMayaの機能を使用し それ以外なら独自のUVエッジに対するテクセル設定モードを使用する
        """
        mapsize = ui.get_value(self.mapSize)
        get_texel(eb_texel=self.texel, mapsize=mapsize)

    @nd.undo_chunk
    def onSetTexel(self, *args):
        """
        UVシェル、もしくはUVエッジのテクセルを設定
        shell選択ならMayaの機能を使用し それ以外なら独自のUVエッジに対するテクセル設定モードを使用する
        """
        texel = ui.get_value(self.texel)
        mapsize = ui.get_value(self.mapSize)
        set_texel(texel=texel, mapsize=mapsize)

    @nd.undo_chunk
    def onSetEdgeTexelUAuto(self, *args):
        target_texel = ui.get_value(self.texel)
        mapsize = ui.get_value(self.mapSize)
        mode = "u_auto"
        set_edge_texel(target_texel=target_texel, mapsize=mapsize, mode=mode)

    @nd.undo_chunk
    def onSetEdgeTexelUMin(self, *args):
        target_texel = ui.get_value(self.texel)
        mapsize = ui.get_value(self.mapSize)
        mode = "u_min"
        set_edge_texel(target_texel=target_texel, mapsize=mapsize, mode=mode)

    @nd.undo_chunk
    def onSetEdgeTexelUMax(self, *args):
        target_texel = ui.get_value(self.texel)
        mapsize = ui.get_value(self.mapSize)
        mode = "u_max"
        set_edge_texel(target_texel=target_texel, mapsize=mapsize, mode=mode)

    @nd.undo_chunk
    def onSetEdgeTexelVAuto(self, *args):
        target_texel = ui.get_value(self.texel)
        mapsize = ui.get_value(self.mapSize)
        mode = "v_auto"
        set_edge_texel(target_texel=target_texel, mapsize=mapsize, mode=mode)

    @nd.undo_chunk
    def onSetEdgeTexelVMin(self, *args):
        target_texel = ui.get_value(self.texel)
        mapsize = ui.get_value(self.mapSize)
        mode = "v_min"
        set_edge_texel(target_texel=target_texel, mapsize=mapsize, mode=mode)

    @nd.undo_chunk
    def onSetEdgeTexelVMax(self, *args):
        target_texel = ui.get_value(self.texel)
        mapsize = ui.get_value(self.mapSize)
        mode = "v_max"
        set_edge_texel(target_texel=target_texel, mapsize=mapsize, mode=mode)

    @nd.undo_chunk
    def onTexelEqualize(self, *args):
        texel_equalize()

    @nd.undo_chunk
    def onUVRatio(self, *args):
        ari_uvratio()

    @nd.undo_chunk
    def onUVRatioOptions(self, *args):
        ari_uvratio_options()

    @nd.undo_chunk
    def onUnfoldU(self, *args):
        unfold_u()

    @nd.undo_chunk
    def onUnfoldV(self, *args):
        unfold_v()

    @nd.undo_chunk
    def onMatchUV(self, *args):
        match_uv()

    @nd.undo_chunk
    def onMatchUVOptions(self, *args):
        match_uv_options()

    @nd.undo_chunk
    def onOnewayMatchUVF(self, *args):
        match_uv_oneway(mode="front")

    @nd.undo_chunk
    def onOnewayMatchUVB(self, *args):
        match_uv_oneway(mode="back")

    @nd.undo_chunk
    def onOnewayMatchUVP(self, *args):
        match_uv_oneway(mode="pin")

    @nd.undo_chunk
    def onOnewayMatchUVS(self, *args):
        snap_uv_to_pin()

    @nd.undo_chunk
    def onOnewayMatchUVUp(self, *args):
        match_uv_oneway(mode="unpin")

    @nd.undo_chunk
    def onExpandFoldRD(self, *args):
        expand_fold_rightdown()

    @nd.undo_chunk
    def onExpandFoldLU(self, *args):
        expand_fold_leftup()

    @nd.undo_chunk
    def onFlipUinTile(self, *args):
        flip_in_tile(direction=FD_U)

    @nd.undo_chunk
    def onFlipVinTile(self, *args):
        flip_in_tile(direction=FD_V)

    @nd.undo_chunk
    def onFlipUinTilePiv(self, *args):
        pu = ui.get_value(self.flip_pivot_u)
        pv = ui.get_value(self.flip_pivot_v)
        flip_in_tile(pivot=(pu, pv), direction=FD_U)

    @nd.undo_chunk
    def onFlipVinTilePiv(self, *args):
        pu = ui.get_value(self.flip_pivot_u)
        pv = ui.get_value(self.flip_pivot_v)
        flip_in_tile(pivot=(pu, pv), direction=FD_V)

    @nd.undo_chunk
    def onGetFlipPivot(self, *args):
        get_flip_pivot(self.flip_pivot_u, self.flip_pivot_v)

    @nd.undo_chunk
    def onSewMatchingEdges(self, *args):
        sew_matching_edges()

    @nd.undo_chunk
    def onCut(self, *args):
        cmds.polyMapCut()

    @nd.undo_chunk
    def onSew(self, *args):
        cmds.polyMapSew()

    @nd.undo_chunk
    def onCreateShell(self, *args):
        mel.eval("CreateUVShellAlongBorder")

    @nd.undo_chunk
    def onMerge(self, *args):
        cmds.polyMergeUV(d=0.0001)

    @nd.undo_chunk
    def onOrientShells(self, *args):
        orient_shells()

    @nd.undo_chunk
    def onSymArrange(self, *args):
        symmetry_arrange()

    @nd.undo_chunk
    def onSnapStack(self, *args):
        snap_stack()

    @nd.undo_chunk
    def onStack(self, *args):
        stack()

    @nd.undo_chunk
    def onUnStack(self, *args):
        unstack()

    @nd.undo_chunk
    def onNormalize(self, *args):
        normalize()

    @nd.undo_chunk
    def onLayout(self, *args):
        mapsize = ui.get_value(self.mapSize)
        margin = ui.get_value(self.layout_margin)
        scale = ui.get_value(self.cb_layout_scale)
        layout_shells(mapsize=mapsize, margin=margin, scale=scale)

    # Tool
    @nd.undo_chunk
    def onUVLatticeTool(self, *args):
        uv_lattice_tool()

    @nd.undo_chunk
    def onUVTweakTool(self, *args):
        uv_tweak_tool()

    @nd.undo_chunk
    def onUVCutTool(self, *args):
        uv_cut_tool()

    @nd.undo_chunk
    def onUVOptimizeTool(self, *args):
        uv_optimize_tool()

    @nd.undo_chunk
    def onUVSymmetrizeTool(self, *args):
        uv_symmetrize_tool()

    @nd.undo_chunk
    def onSetUVSymmetrizeCenter(self, *args):
        set_uv_symmetrize_center()

    # Select & Convert
    @nd.undo_chunk
    def onConvertToShellBorder(self, *args):
        convert_to_shell_border()

    @nd.undo_chunk
    def onConvertToShellInner(self, *args):
        convert_to_shell_inner()

    @nd.undo_chunk
    def onSelectAllUVBorders(self, *args):
        select_all_uv_borders()

    @nd.undo_chunk
    def onShortestEdgeTool(self, *args):
        shortest_edge_tool()

    @nd.undo_chunk
    def onSelectFrontface(self, *args):
        select_front_face()

    @nd.undo_chunk
    def onSelectBackface(self, *args):
        select_backface()

    # etc
    @nd.undo_chunk
    def onUVEditor(self, *args):
        display_uveditor()

    @nd.undo_chunk
    def onUVToolKit(self, *args):
        display_uvtoolkit()

    @nd.undo_chunk
    def onUVSnapShot(self, *args):
        uv_snapshot_options()

    @nd.undo_chunk
    def onChangeUVCheckerDensity(self, *args):
        """ UVチェッカー密度エディットボックスの変更ハンドラ。UVTookKit の値を同期する
        """
        n = ui.get_value(self.checkerDensity)
        set_checker_density(n=n)

    @nd.undo_chunk
    def onUVCheckerDensityMul2(self, *args):
        n = ui.get_value(self.checkerDensity) * 2.0
        set_checker_density(n=n)
        ui.set_value(self.checkerDensity, n)
        self.onChangeUVCheckerDensity()

    @nd.undo_chunk
    def onUVCheckerDensityDiv2(self, *args):
        n = ui.get_value(self.checkerDensity) / 2.0
        set_checker_density(n=n)
        ui.set_value(self.checkerDensity, n)
        self.onChangeUVCheckerDensity()

    @nd.undo_chunk
    def onToggleChecker(self, *args):
        toggle_checker()

    @nd.undo_chunk
    def onDrawEdge(self, *args):
        mapsize = ui.get_value(self.mapSize)
        draw_edge(mapsize=mapsize)

    def onGridLayout(self, *args):
        """グリッドレイアウトツールを起動する"""
        import nnuvtoolkit.grid_layout as gl
        gl.main()

    def onParentToUVEditor(self, *args):
        """UVエディターを親にしてウィンドウを再作成する"""
        self.create(parent_to_uveditor=True)


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    mel.eval("TextureViewWindow")

    if cmds.workspaceControl("UVToolkitDockControl", exists=True):
        cmds.workspaceControl("UVToolkitDockControl", e=True, close=True)

    showNNToolWindow()


if __name__ == "__main__":
    main()
