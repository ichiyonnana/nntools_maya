#! python
# coding:utf-8

import re

import maya.cmds as cmds
import pymel.core as pm
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


@nd.repeatable
def translate_uv(pivot, translate):
    """ 選択中 UV の移動

    Args:
        pivot ([type]): [description]
        translate ([type]): [description]
    """
    cmds.polyEditUV(pu=pivot[0], pv=pivot[1], u=translate[0], v=translate[1])


@nd.repeatable
def scale_uv(pivot, scale):
    """ 選択中 UV のスケール

    Args:
        pivot ([type]): [description]
        scale ([type]): [description]
    """
    cmds.polyEditUV(pu=pivot[0], pv=pivot[1], u=scale[0], v=scale[1])


@nd.repeatable
def rotate_uv(angle):
    """ 選択中 UV の回転

    Args:
        pivot ([type]): [description]
        angle ([type]): [description]
    """
    mel.eval("polyRotateUVs %f 1" % angle)


@nd.repeatable
def project_planer_x():
    mel.eval("polyProjection -type Planar -ibd on -kir -md x")


@nd.repeatable
def project_planer_y():
    mel.eval("polyProjection -type Planar -ibd on -kir -md y")


@nd.repeatable
def project_planer_z():
    mel.eval("polyProjection -type Planar -ibd on -kir -md z")


@nd.repeatable
def project_planer_camera():
    mel.eval("polyProjection -type Planar -ibd on -kir -md camera")


@nd.repeatable
def project_planer_best():
    mel.eval("polyProjection -type Planar -ibd on -kir -md b;")


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
    mel.eval("texLinearAlignUVs")


@nd.repeatable
def ari_gridding():
    mel.eval("AriUVGridding")


@nd.repeatable
def _rectilinearize(corner_uv_comps=None, target_texel=15, map_size=1024):
    rectilinearize.main(corner_uv_comps=corner_uv_comps, target_texel=target_texel, map_size=map_size)

@nd.repeatable
def change_uvtk_texel_value(texel):
    """ UVToolkit のテクセル値フィールドを設定する"""
    mel.eval("floatField -e -v %f uvTkTexelDensityField" % texel)


@nd.repeatable
def change_uvtk_map_size(mapsize):
    """mapSize 変更時に UVToolkit のフィールドを同じ値に変更する"""
    mel.eval("intField -e -v %d uvTkTexelDensityMapSizeField" % mapsize)


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
        # UVToolkit の機能でテクセル取得
        mel.eval("uvTkDoGetTexelDensity")
        uvTkTexel = mel.eval("floatField -q -v uvTkTexelDensityField")

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
        # UVToolkit の値を更新
        mel.eval("floatField -e -v %f uvTkTexelDensityField" % currentTexel)
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

    for uvPair in targetUVsList:
        uv1 = cmds.polyEditUV(uvPair[0], q=True)  # ペアの 1 つめの UV座標を持つリスト
        uv2 = cmds.polyEditUV(uvPair[1], q=True)  # ペアの 2 つめの UV座標を持つリスト
        vtxComponent1 = cmds.polyListComponentConversion(uvPair[0], fuv=True, tv=True)  # uv1 に対応する ポリゴン頂点のコンポーネント文字列
        vtxComponent2 = cmds.polyListComponentConversion(uvPair[1], fuv=True, tv=True)  # uv2 に対応する ポリゴン頂点のコンポーネント文字列
        p1 = cmds.xform(vtxComponent1, q=True, ws=True, t=True)  # uv1 の XYZ 座標
        p2 = cmds.xform(vtxComponent2, q=True, ws=True, t=True)  # uv2 の XYZ 座標
        geoLength = nu.distance(p1, p2)
        uLength = abs(uv2[0] - uv1[0])
        vLength = abs(uv2[1] - uv1[1])
        uvLength = nu.distance2d(uv1, uv2)

        if mode == "u_min":
            currentTexel = uLength / geoLength * mapsize
            scale = target_texel / currentTexel
            pivU = min(uv1[0], uv2[0])
            pivV = 0
            cmds.polyEditUV(uvPair[0], pu=pivU, pv=pivV, su=scale, sv=1)
            cmds.polyEditUV(uvPair[1], pu=pivU, pv=pivV, su=scale, sv=1)

        elif mode == "u_max":
            currentTexel = uLength / geoLength * mapsize
            scale = target_texel / currentTexel
            pivU = max(uv1[0], uv2[0])
            pivV = 0
            cmds.polyEditUV(uvPair[0], pu=pivU, pv=pivV, su=scale, sv=1)
            cmds.polyEditUV(uvPair[1], pu=pivU, pv=pivV, su=scale, sv=1)

        elif mode == "v_min":
            currentTexel = vLength / geoLength * mapsize
            scale = target_texel / currentTexel
            pivU = 0
            pivV = min(uv1[1], uv2[1])
            cmds.polyEditUV(uvPair[0], pu=pivU, pv=pivV, su=1, sv=scale)
            cmds.polyEditUV(uvPair[1], pu=pivU, pv=pivV, su=1, sv=scale)

        elif mode == "v_max":
            currentTexel = vLength / geoLength * mapsize
            scale = target_texel / currentTexel
            pivU = 0
            pivV = max(uv1[1], uv2[1])
            cmds.polyEditUV(uvPair[0], pu=pivU, pv=pivV, su=1, sv=scale)
            cmds.polyEditUV(uvPair[1], pu=pivU, pv=pivV, su=1, sv=scale)

        else:
            print(MSG_NOT_IMPLEMENTED)
            currentTexel = uvLength / geoLength * mapsize
            scale = target_texel / currentTexel
            cmds.polyEditUV(uvPair[0], pu=uv1[0], pv=uv1[1], su=scale, sv=scale)
            cmds.polyEditUV(uvPair[1], pu=uv1[0], pv=uv1[1], su=scale, sv=scale)


@nd.repeatable
def ari_uvratio():
    mel.eval("AriUVRatio")


@nd.repeatable
def ari_uvratio_options():
    mel.eval("AriUVRatioOptions")


@nd.repeatable
def unfold_u():
    mel.eval("unfold -i 5000 -ss 0.001 -gb 0 -gmb 0.5 -pub 0 -ps 0 -oa 2 -us off")


@nd.repeatable
def unfold_v():
    mel.eval("unfold -i 5000 -ss 0.001 -gb 0 -gmb 0.5 -pub 0 -ps 0 -oa 1 -us off")


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
        raise(Exception("unknown flip mode"))


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
    uvs = pm.selected(flatten=True)
    uv_coords = nu.split_n_pair(pm.polyEditUV(uvs, q=True), 2)
    avg_u = sum([uv_coord[0] for uv_coord in uv_coords]) / len(uv_coords)
    avg_v = sum([uv_coord[1] for uv_coord in uv_coords]) / len(uv_coords)
    ui.set_value(ui_pivot_u, avg_u)
    ui.set_value(ui_pivot_v, avg_v)


@nd.repeatable
def orient_edge():
    mel.eval("texOrientEdge")


@nd.repeatable
def orient_shells():
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
    texWinName = cmds.getPanel(sty='polyTexturePlacementPanel')[0]
    cmds.textureWindow(texWinName, e=True, checkerDensity=n)


@nd.repeatable
def toggle_checker():
    checkered = cmds.textureWindow("polyTexturePlacementPanel1", q=True, displayCheckered=True)
    cmds.textureWindow("polyTexturePlacementPanel1", e=True, displayCheckered=(not checkered))


@nd.repeatable
def draw_edge(map_size):
    import draw_image as de
    import nnutil as nu

    save_dir = nu.get_project_root() + "/images/"
    filepath = save_dir + "draw_edges.svg"
    mapSize = ui.get_value(map_size)
    de.draw_edge(filepath=filepath, imagesize=mapSize)


class NN_ToolWindow(object):
    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (330, 520)

    def create(self):
        if pm.window(self.window, exists=True):
            pm.deleteUI(self.window, window=True)

        # プリファレンスの有無による分岐
        if pm.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = pm.windowPref(self.window, q=True, topLeftCorner=True)
            pm.windowPref(self.window, remove=True)

            # 前回位置に指定したサイズで表示
            pm.window(self.window, t=self.title, maximizeButton=False, minimizeButton=False, topLeftCorner=position, widthHeight=self.size, sizeable=False)

        else:
            # プリファレンスがなければデフォルト位置に指定サイズで表示
            pm.window(self.window, t=self.title, maximizeButton=False, minimizeButton=False, widthHeight=self.size, sizeable=False)

        self.layout()
        pm.showWindow(self.window)

        ui.set_value(self.mapSize, 1024)

    def layout(self):
        self.columnLayout = ui.column_layout()

        # Projection
        ui.row_layout()
        ui.header(label='Projection')
        ui.button(label='X', c=self.onPlanerX, bgc=ui.color_x)
        ui.button(label='Y', c=self.onPlanerY, bgc=ui.color_y)
        ui.button(label='Z', c=self.onPlanerZ, bgc=ui.color_z)
        ui.button(label='Camera', c=self.onPlanerCamera)
        ui.button(label='Best', c=self.onPlanerBest)
        ui.end_layout()

        # Align & Snap
        ui.row_layout()
        ui.header(label='Align & Snap')
        ui.button(label='Border', c=self.onStraightenBorder)
        ui.button(label='Inner', c=self.onStraightenInner)
        ui.button(label='All', c=self.onStraightenAll)
        ui.button(label='Linear', c=self.onLinearAlign)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='AriGridding', c=self.onGridding)
        ui.button(label='Rectilinearize', c=self.onRectilinearize)
        ui.button(label='MatchUV', c=self.onMatchUV, dgc=self.onMatchUVOptions)
        ui.end_layout()

        # MatchUV
        ui.row_layout()
        ui.text(label='MatchUV')
        ui.button(label='to Front [back]', c=self.onOnewayMatchUVF, dgc=self.onOnewayMatchUVB, width=ui.button_width3)
        ui.button(label='to Pin [unpin]', c=self.onOnewayMatchUVP, dgc=self.onOnewayMatchUVUp, width=ui.button_width3)
        ui.button(label='expand/fold', c=self.onExpandFoldRD, dgc=self.onExpandFoldLU)
        ui.end_layout()

        # Flip
        ui.row_layout()
        ui.header(label="Flip")
        ui.button(label='FlipU', c=self.onFlipUinTile, dgc=self.onFlipUinTilePiv, bgc=ui.color_u)
        ui.button(label='FlipV', c=self.onFlipVinTile, dgc=self.onFlipVinTilePiv, bgc=ui.color_v)
        self.flip_pivot_u = ui.eb_float(width=ui.button_width2)
        self.flip_pivot_v = ui.eb_float(width=ui.button_width2)
        ui.button(label="get", width=ui.button_width1, c=self.onGetFlipPivot)
        ui.end_layout()

        # Cut & Sew
        ui.row_layout()
        ui.header(label='Cut & Sew')
        ui.button(label='Cut', c=self.onCut)
        ui.button(label='Sew', c=self.onSew)
        ui.button(label='Shell', c=self.onCreateShell)
        ui.button(label='Merge', c=self.onMerge)
        ui.end_layout()

        # Optimize
        ui.row_layout()
        ui.header(label='Optimize')
        ui.button(label='Get', c=self.onGetTexel)
        self.texel = ui.eb_float(cc=self.onChangeTexel, v=10, width=ui.button_width2)
        self.mapSize = ui.eb_int(cc=self.onChangeMapSize, width=ui.button_width1_5)
        ui.text(label='px')
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='Set', c=self.onSetTexel)
        ui.button(label='U', c=self.onSetEdgeTexelUMin, dgc=self.onSetEdgeTexelUMax, bgc=ui.color_u)
        ui.button(label='V', c=self.onSetEdgeTexelVMin, dgc=self.onSetEdgeTexelVMax, bgc=ui.color_v)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='AriUVRatio', c=self.onUVRatio, dgc=self.onUVRatioOptions)
        ui.button(label='UnfoldU', c=self.onUnfoldU, bgc=ui.color_u)
        ui.button(label='UnfoldV', c=self.onUnfoldV, bgc=ui.color_v)
        ui.end_layout()

        # Checker
        ui.row_layout()
        ui.header(label='Checker')
        ui.text(label="dense:")
        self.checkerDensity = ui.eb_int(v=256, cc=self.onChangeUVCheckerDensity, width=ui.button_width1_5)
        ui.button(label='/2', c=self.onUVCheckerDensityDiv2)
        ui.button(label='x2', c=self.onUVCheckerDensityMul2)
        ui.button(label="Toggle", c=self.onToggleChecker)
        ui.end_layout()

        # Layout
        ui.row_layout()
        ui.header(label='Layout')
        ui.button(label='Orient to Edge', c=self.onOrientEdge)
        ui.button(label='Orient Shells', c=self.onOrientShells)
        ui.button(label='SymArrange', c=self.onSymArrange)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='SanpStack', c=self.onSnapStack)
        ui.button(label='Stack', c=self.onStack)
        ui.button(label='Unstack', c=self.onUnStack)
        ui.button(label='Normalize', c=self.onNormalize)
        ui.end_layout()

        # Tools
        ui.row_layout()
        ui.header(label='Tools')
        ui.button(label='Lattice', c=self.onUVLatticeTool)
        ui.button(label='Tweak', c=self.onUVTweakTool)
        ui.button(label='Cut', c=self.onUVCutTool)
        ui.button(label='Optimize', c=self.onUVOptimizeTool)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='Symmetrize [setU]', c=self.onUVSymmetrizeTool, dgc=self.onSetUVSymmetrizeCenter)
        ui.button(label='Shortest Tool', c=self.onShortestEdgeTool)
        ui.end_layout()

        # Convert
        ui.row_layout()
        ui.header(label='Convert')
        ui.button(label='to Border', c=self.onConvertToShellBorder)
        ui.button(label='to Inner', c=self.onConvertToShellInner)
        ui.end_layout()

        # Select
        ui.row_layout()
        ui.header(label='Select')
        ui.button(label='Frontface', c=self.onSelectFrontface)
        ui.button(label='Backface', c=self.onSelectBackface)
        ui.button(label='All Borders', c=self.onSelectAllUVBorders)
        ui.end_layout()

        # Transform
        ui.row_layout()
        ui.header(label='Transform')
        ui.text(label='Move')
        self.translateValue = ui.eb_float(v=0.1, width=ui.button_width2)
        ui.button(label=u'←', c=self.onTranslateUDiff, bgc=ui.color_u)
        ui.button(label=u'→', c=self.onTranslateUAdd, bgc=ui.color_u)
        ui.button(label=u'↑', c=self.onTranslateVAdd, bgc=ui.color_v)
        ui.button(label=u'↓', c=self.onTranslateVDiff, bgc=ui.color_v)
        self.cb_transform_in_pixel = ui.check_box(label="px")
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.header(label='Rotate')
        self.rotationAngle = ui.eb_float(v=90, width=ui.button_width2)
        ui.button(label=u'←', c=self.onRotateLeft)
        ui.button(label=u'→', c=self.onRotateRight)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.header(label='Scale')
        self.scaleValue = ui.eb_float(v=2, width=ui.button_width2)
        ui.button(label='U*', c=self.onOrigScaleUMul, bgc=ui.color_u)
        ui.button(label='U/', c=self.onOrigScaleUDiv, bgc=ui.color_u)
        ui.button(label='V*', c=self.onOrigScaleVMul, bgc=ui.color_v)
        ui.button(label='V/', c=self.onOrigScaleVDiv, bgc=ui.color_v)
        ui.end_layout()

        # Editor
        ui.row_layout()
        ui.header(label="Editor")
        ui.button(label='UVEditor', c=self.onUVEditor)
        ui.button(label='UVToolkit', c=self.onUVToolKit)
        ui.button(label='UVSnapShot', c=self.onUVSnapShot)
        ui.button(label='DrawEdge', c=self.onDrawEdge)
        ui.end_layout()

    def initialize(self):
        # テクセルとマップサイズを UVToolkit から取得
        uvtkTexel = mel.eval("floatField -q -v uvTkTexelDensityField")
        uvtkMapSize = mel.eval("intField -q -v uvTkTexelDensityMapSizeField")
        ui.set_value(self.texel, uvtkTexel)
        ui.set_value(self.mapSize, uvtkMapSize)

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
        scale_uv(pivot=(0, 0), scale=(v, 1))

    @nd.undo_chunk
    def onOrigScaleVMul(self, *args):
        v = ui.get_value(self.scaleValue)
        scale_uv(pivot=(0, 0), scale=(1, v))

    @nd.undo_chunk
    def onOrigScaleUDiv(self, *args):
        v = ui.get_value(self.scaleValue)
        scale_uv(pivot=(0, 0), scale=(1.0/v, 1))

    @nd.undo_chunk
    def onOrigScaleVDiv(self, *args):
        v = ui.get_value(self.scaleValue)
        scale_uv(pivot=(0, 0), scale=(1, 1.0/v))

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
        project_planer_x()

    @nd.undo_chunk
    def onPlanerY(self, *args):
        project_planer_y()

    @nd.undo_chunk
    def onPlanerZ(self, *args):
        project_planer_z()

    @nd.undo_chunk
    def onPlanerCamera(self, *args):
        project_planer_camera()

    @nd.undo_chunk
    def onPlanerBest(self, *args):
        project_planer_best()

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
    def onChangeTexel(self, *args):
        """ エディットボックスの値変更ハンドラ。texel 変更時に UVToolkit のフィールドを同じ値に変更する"""
        texel = ui.get_value(self.texel)
        change_uvtk_texel_value(texel=texel)

    @nd.undo_chunk
    def onChangeMapSize(self, *args):
        """ エディットボックスの値変更ハンドラ。mapSize 変更時に UVToolkit のフィールドを同じ値に変更する"""
        mapsize = ui.get_value(self.mapSize)
        change_uvtk_map_size(mapsize=mapsize)

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
        pm.polyMapCut()

    @nd.undo_chunk
    def onSew(self, *args):
        pm.polyMapSew()

    @nd.undo_chunk
    def onCreateShell(self, *args):
        mel.eval("CreateUVShellAlongBorder")

    @nd.undo_chunk
    def onMerge(self, *args):
        pm.polyMergeUV(d=0.0001)

    @nd.undo_chunk
    def onOrientEdge(self, *args):
        orient_edge()

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


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    mel.eval("TextureViewWindow")
    mel.eval("workspaceControl -e -visible true UVToolkitDockControl;")
    mel.eval("workspaceControl -e -close UVToolkitDockControl;")
    showNNToolWindow()


if __name__ == "__main__":
    main()
