"""単独で機能する細かい関数｡カスタムスクリプトやシェルフから呼ぶ."""

import re

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om
import maya.OpenMayaUI as omui

import nnutil.ui as ui
import nnutil.misc as nm
import nnutil.decorator as nd

if int(cmds.about(version=True)) >= 2025:
    from PySide6 import QtWidgets
    import shiboken6 as shiboken

else:
    from PySide2 import QtWidgets
    import shiboken2 as shiboken


def extract_transform_as_locator(objects=None):
    """指定したオブジェクトのトランスフォームをロケーターとして抽出する."""
    if not objects:
        objects = cmds.ls(selection=True)

    for obj in objects:
        # ロケーターを作成しオブジェクトと同一階層に配置
        locator = cmds.spaceLocator(name=obj + "_TRS")[0]
        obj_parent = cmds.listRelatives(obj, parent=True)
        if obj_parent:
            cmds.parent(locator, obj_parent)

        # ロケーターのトランスフォームをワールド空間でオブジェクトに一致させる
        translation = cmds.xform(obj, query=True, translation=True, worldSpace=True)
        rotation = cmds.xform(obj, query=True, rotation=True, worldSpace=True)
        scale = cmds.xform(obj, query=True, scale=True, relative=True)
        cmds.xform(locator, translation=translation, worldSpace=True)
        cmds.xform(locator, rotation=rotation, worldSpace=True)
        cmds.xform(locator, scale=scale)

        # オブジェクトをロケータの子にする
        cmds.parent(obj, locator)


def add_instance(objects=None, instance=True, replace=False):
    """1番目に選択されたオブジェクトをそれ以外の選択オブジェクトの子としてインスタンスコピーを作成する."""
    if not objects:
        objects = cmds.ls(selection=True)

    if len(objects) < 2:
        print("select 2 or more objects")
        return

    src_object = objects[0]
    target_transforms = objects[1:]

    for dst_trs in target_transforms:
        if replace:
            src_mesh = cmds.listRelatives(src_object, shapes=True, fullPath=True)
            dst_mesh = cmds.listRelatives(dst_trs, shapes=True, fullPath=True)
            cmds.delete(dst_mesh)
            cmds.parent(src_mesh, dst_trs, shape=True, add=True)

            if not instance:
                cmds.select(dst_trs)
                nm.freeze_instance()

        else:
            if instance:
                obj = cmds.instance(src_object)
            else:
                obj = cmds.duplicate(src_object)

            cmds.parent(obj, dst_trs, r=True)

    cmds.select(target_transforms)


def hadamard_product(v1, v2):
    """アダマール積をタプルで返す."""
    dim = len(v1)
    ret = [0] * dim

    for i in range(0, dim):
        ret[i] = v1[i] * v2[i]

    return tuple(ret)


def radial_copy(object, div, axis, instance=False):
    """指定オブジェクトを指定軸･個数で回転コピーする."""
    r = 360/div

    axis_vector = (0, 1, 0)

    if axis == "x":
        axis_vector = (1, 0, 0)
    elif axis == "y":
        axis_vector = (0, 1, 0)
    elif axis == "z":
        axis_vector = (0, 0, 1)
    else:
        pass

    for i in range(1, div):
        dup_obj = None

        if instance:
            dup_obj = cmds.instance(object)[0]
        else:
            dup_obj = cmds.duplicate(object)[0]

        cmds.xform(dup_obj, rotation=hadamard_product((r*i, r*i, r*i), axis_vector))


def radial_copy_prompt():
    """radial_copy の補助プロンプト."""
    selections = cmds.ls(selection=True)

    if selections:
        obj = selections[0]
        code = ui.input_dialog(title="division and axis", message="e.g. 7yi")

        if code:
            div = re.search(r"\d+", code).group()
            axis = re.search(r"[xyz]", code).group()
            instance = re.search(r"i", code)

            if div and axis:
                div = int(div)
                instance = bool(instance)
                radial_copy(object=obj, div=div, axis=axis, instance=instance)


def extrude_joint():
    """選択中のジョイントの子に新しいジョイントを作成する."""
    selections = cmds.ls(selection=True, type="joint")
    cmds.select(clear=True)

    additional_joints = []

    for joint in selections:
        new_joint = cmds.joint()
        cmds.parent(new_joint, joint)
        cmds.setAttr(new_joint + ".jointOrientX", 0)
        cmds.setAttr(new_joint + ".jointOrientY", 0)
        cmds.setAttr(new_joint + ".jointOrientZ", 0)
        cmds.xform(new_joint, translation=(10, 0, 0), objectSpace=True)

        additional_joints.append(new_joint)

    cmds.select(additional_joints)


def lerp_attr(targets=None, attr_names=None):
    """指定した複数のオブジェクトに関して､最初のオブジェクトから最後のオブジェクトにかけて指定したアトリビュートが均等に変化するように設定する."""
    targets = targets or cmds.ls(selection=True)

    if not targets:
        return

    if not attr_names:
        return

    for attr_name in attr_names:
        begin_v = cmds.getAttr(targets[0] + attr_name)
        end_v = cmds.getAttr(targets[-1] + attr_name)
        diff = (end_v - begin_v) / (len(targets) - 1)

        for i, obj in enumerate(targets):
            v = begin_v + i * diff
            cmds.setAttr(obj + attr_name, v)


def spin_or_triangulate(targets=None):
    """選択モードによりエッジスピンとフェースの三角化を実行し分ける."""
    is_face_mode = cmds.selectType(q=True, polymeshFace=True)
    is_edge_mode = cmds.selectType(q=True, polymeshEdge=True)

    current_selections = cmds.ls(selection=True, flatten=True)
    new_selections = []

    if is_face_mode:
        # triangulate の実行
        # triangulate はインデックスが変わるのでオブジェクト毎に一回で処理する
        comps_each_objects = {}

        for comp in current_selections:
            object_name = cmds.polyListComponentConversion(comp)[0]

            if object_name not in comps_each_objects.keys():
                comps_each_objects[object_name] = []

            comps_each_objects[object_name].append(comp)

        for object_name, components in comps_each_objects.items():
            cmds.polyTriangulate(components)

    elif is_edge_mode:
        for comp in current_selections:
            cmds.polySpinEdge(comp, offset=1)

        cmds.select(current_selections)


def snap_to_pixels(targets=None, texture_resolution=1024, snap_pixels=1):
    """指定した UV をテクスチャのピクセル境界にスナップさせる."""
    snap_uv = 1 / texture_resolution * snap_pixels

    targets = targets or cmds.ls(selection=True, flatten=True)

    if not targets:
        return

    uvs = cmds.filterExpand(targets, selectionMask=35)
    uv_coords = {}

    for uv_str in uvs:
        u, v = cmds.polyEditUV(uv_str, q=True)
        uv_coords[uv_str] = [u, v]

    max_u = max([uv[0] for uv in uv_coords.values()])
    min_u = min([uv[0] for uv in uv_coords.values()])
    max_v = max([uv[1] for uv in uv_coords.values()])
    min_v = min([uv[1] for uv in uv_coords.values()])

    is_snap_u = (max_u - min_u) < (max_v - min_v)

    for uv_str, uv in uv_coords.items():
        new_v = uv[1]
        new_u = uv[0]

        if is_snap_u:
            new_u = round(uv[0] / snap_uv, 0) * snap_uv
        else:
            new_v = round(uv[1] / snap_uv, 0) * snap_uv

        cmds.polyEditUV(uv_str, relative=False, uValue=new_u, vValue=new_v)


@nd.repeatable
def snap_to_ordinal_in_block(targets=None, texture_resolution=1024, block_width=8, ordinal=5, nearest=False):
    """指定した UV をテクスチャのピクセル境界にスナップさせる."""

    def calc_coord_to_snap(coord):
        uv_per_pixel = 1.0 / texture_resolution
        uv_per_block = uv_per_pixel * block_width

        current_ordinal = (coord % uv_per_block) / uv_per_pixel

        # nearest オプションが有効な場合は ordinal を反対側から数えた場合と比較して近い方にスナップする
        if nearest:
            if current_ordinal < block_width / 2:
                actual_ordinal = min(ordinal, block_width - ordinal)
            else:
                actual_ordinal = max(ordinal, block_width - ordinal)

        else:
            actual_ordinal = ordinal

        # 現在 UV が存在するブロック内のスナップ座標
        block_index = coord // uv_per_block

        new_coord = block_index * uv_per_block + uv_per_pixel * actual_ordinal

        return new_coord

    # tagets が未指定なら選択 UV を使用
    targets = targets or cmds.ls(selection=True, flatten=True)

    if not targets:
        return

    # UV 座標取得
    uvs = cmds.filterExpand(targets, selectionMask=35)
    uv_coords = {}

    for uv_str in uvs:
        u, v = cmds.polyEditUV(uv_str, q=True)
        uv_coords[uv_str] = [u, v]

    # 揃えるのが U か V かの判定
    max_u = max([uv[0] for uv in uv_coords.values()])
    min_u = min([uv[0] for uv in uv_coords.values()])
    max_v = max([uv[1] for uv in uv_coords.values()])
    min_v = min([uv[1] for uv in uv_coords.values()])

    is_snap_u = (max_u - min_u) < (max_v - min_v)

    # 各 UV ごとにスナップ処理
    for uv_str, uv in uv_coords.items():
        new_v = uv[1]
        new_u = uv[0]

        # スナップ後の座標
        if is_snap_u:
            new_u = calc_coord_to_snap(uv[0])
        else:
            new_v = calc_coord_to_snap(uv[1])

        # 座標の更新
        cmds.polyEditUV(uv_str, relative=False, uValue=new_u, vValue=new_v)


@nd.undo_chunk
def extrude_edges(offset):
    """UV･頂点カラー等が設定されたエッジのextrude."""
    selected_edges = cmds.ls(selection=True, flatten=True)

    extrude_node = cmds.polyExtrudeEdge(
        selected_edges,
        constructionHistory=True,
        keepFacesTogether=True,
        divisions=1,
        offset=offset,
        thickness=0,
        smoothingAngle=180)

    extruded_edges = cmds.ls(selection=True, flatten=True)
    extruded_faces = cmds.filterExpand(cmds.polyListComponentConversion(extruded_edges, fe=True, tf=True), selectionMask=34)
    perimeter_faces = cmds.filterExpand(cmds.polyListComponentConversion(selected_edges, fe=True, tf=True), selectionMask=34)
    all_bace_faces = list(set(perimeter_faces) - set(extruded_faces))
    all_bace_vfaces = list(set(cmds.filterExpand(cmds.polyListComponentConversion(all_bace_faces, ff=True, tvf=True), selectionMask=70)))

    saw_edges = []

    # 押し出されたフェース毎に反復
    for extruded_face in extruded_faces:
        perimeter_edges = cmds.filterExpand(cmds.polyListComponentConversion(extruded_face, ff=True, te=True), selectionMask=32)
        selected_edge = [x for x in perimeter_edges if x in selected_edges]
        extruded_edge = [x for x in perimeter_edges if x in extruded_edges]
        side_edges = [x for x in perimeter_edges if x not in extruded_edges + selected_edges]
        base_face = cmds.filterExpand(cmds.polyListComponentConversion(selected_edge, fe=True, tf=True), selectionMask=34)
        base_face.remove(extruded_face)
        ext_vfaces = cmds.filterExpand(cmds.polyListComponentConversion(extruded_face, ff=True, tvf=True), selectionMask=70)
        base_vfaces = cmds.filterExpand(cmds.polyListComponentConversion(base_face, ff=True, tvf=True), selectionMask=70)
        sel_vfaces = cmds.filterExpand(cmds.polyListComponentConversion(selected_edge, fe=True, tvf=True), selectionMask=70)

        # 押し出しで作成されたフェース同士の境界エッジごとの反復
        for side_edge in side_edges:
            side_vts = cmds.filterExpand(cmds.polyListComponentConversion(side_edge, fe=True, tv=True), selectionMask=31)
            side_vfaces = cmds.filterExpand(cmds.polyListComponentConversion(side_vts, fv=True, tvf=True), selectionMask=70)

            vf_src = list(set(side_vfaces) & set(base_vfaces))[0]
            vf_dst_list = list(set(side_vfaces) & set(ext_vfaces))

            has_uv = cmds.polyListComponentConversion(vf_src, fvf=True, tuv=True)
            has_vcolor = cmds.polyColorSet(q=True, allColorSets=True)

            for vf_dst in vf_dst_list:

                if has_uv:
                    uv_src = cmds.polyListComponentConversion(vf_src, fvf=True, tuv=True)[0]
                    uv_dst = cmds.polyListComponentConversion(vf_dst, fvf=True, tuv=True)[0]

                    uv = cmds.polyEditUV(uv_src, q=True)
                    cmds.polyEditUV(uv_dst, u=uv[0], v=uv[1], relative=False)

                if has_vcolor:
                    rgb = cmds.polyColorPerVertex(vf_src, q=True, colorRGB=True)
                    a = cmds.polyColorPerVertex(vf_src, q=True, alpha=True)[0]
                    cmds.polyColorPerVertex(vf_dst, colorRGB=rgb, alpha=a)

            # 根元のUVが分離していなければ Saw 対象リストへ追加
            vf = list(set(all_bace_vfaces) & set(side_vfaces))
            uv = cmds.filterExpand(cmds.polyListComponentConversion(vf, fvf=True, tuv=True), selectionMask=35)

            if len(set(uv)) == 1:
                saw_edges.append(side_edge)

    # 押し出しで新規作成されたボーダーエッジの Saw
    cmds.u3dUnfold(extruded_edges, ite=2, p=0, bi=1, tf=1, ms=1024, rs=0)

    # 押し出したフェース同士の境界の Saw
    if saw_edges:
        cmds.polyMapSew(saw_edges)

    # 最初に選択していたエッジの Saw
    cmds.polyMapSew(selected_edges)

    # 選択復帰
    cmds.select(extruded_edges)


def smart_extrude():
    """選択物のタイプによって適切に extrude する."""
    selections = cmds.ls(selection=True)

    if selections:
        if cmds.objectType(selections[0], isType="joint"):
            extrude_joint()

        elif (cmds.objectType(selections[0], isType="mesh")
              and cmds.selectType(q=True, polymeshEdge=True)):
            extrude_edges(offset=0.1)

        else:
            mel.eval("performPolyExtrude 0")


def smart_duplicate():
    """選択物のタイプによって適切に duplicate する."""
    selections = cmds.ls(selection=True)

    if selections:
        if cmds.objectType(selections[0], isType="mesh"):
            if cmds.selectType(q=True, polymeshEdge=True):
                extrude_edges(offset=0.0)

            else:
                pass

        else:
            cmds.duplicate()


def orient_object_from_edges():
    """選択されているエッジを元にローカル座標軸を設定する.

    頂点を共有する 2 エッジのみの対応
    """
    # 選択エッジ
    edges = cmds.ls(orderedSelection=True, flatten=True)

    # 2エッジ以下なら終了
    if len(edges) < 2:
        print("select 2 edges")
        print(edges)
        raise

    # コンポーネントを持つオブジェクト
    obj = cmds.listRelatives(cmds.polyListComponentConversion(edges[0])[0], parent=True, fullPath=True)[0]

    # エッジの構成頂点
    basis0_vts = cmds.filterExpand(cmds.polyListComponentConversion(edges[0], fe=True, tv=True), sm=31)
    basis1_vts = cmds.filterExpand(cmds.polyListComponentConversion(edges[1], fe=True, tv=True), sm=31)

    # 2 エッジの共有頂点のリスト
    intersection_vts = list(set(basis0_vts) & set(basis1_vts))

    # 2 エッジが 1 点で接していなければ終了
    if len(intersection_vts) != 1:
        print("splited edges is not supported.")
        raise

    # 2 エッジの共有頂点
    intersection_vtx = intersection_vts[0]

    # 各選択エッジの終点
    basis0_end_vtx = list(set(basis0_vts) - {intersection_vtx})[0]
    basis1_end_vtx = list(set(basis1_vts) - {intersection_vtx})[0]

    # 共有頂点のワールド座標
    p0 = cmds.xform(intersection_vtx, q=True, translation=True, worldSpace=True)

    # X 軸のベクトル
    p1 = cmds.xform(basis0_end_vtx, q=True, translation=True, worldSpace=True)
    basis0 = om.MVector([p1[0]-p0[0], p1[1]-p0[1], p1[2]-p0[2]])
    basis0.normalize()

    # Y 軸のベクトル
    p2 = cmds.xform(basis1_end_vtx, q=True, translation=True, worldSpace=True)
    basis1 = om.MVector([p2[0]-p0[0], p2[1]-p0[1], p2[2]-p0[2]])
    basis1.normalize()

    # Z 軸のベクトル
    basis2 = basis0 ^ basis1
    basis2.normalize()

    # 新しいワールドマトリックス
    m = [
        basis0.x, basis0.y, basis0.z, 0,
        basis1.x, basis1.y, basis1.z, 0,
        basis2.x, basis2.y, basis2.z, 0,
        p0[0], p0[1], p0[2], 1]

    # 現在の頂点座標を保存
    sel = om.MSelectionList()
    sel.add(obj)
    dag = sel.getDagPath(0)
    fn_mesh = om.MFnMesh(dag)

    current_points = fn_mesh.getPoints(space=om.MSpace.kWorld)

    # ワールドマトリックスの上書き
    cmds.xform(obj, matrix=m, worldSpace=True)

    # 頂点座標の復帰
    fn_mesh.setPoints(current_points, space=om.MSpace.kWorld)
    fn_mesh.updateSurface()


def set_manipulater_to_active_camera():
    """マニピュレーターの方向をアクティブなカメラのローカル軸に設定する."""
    active_panel = cmds.getPanel(withFocus=True)
    active_camera = cmds.modelPanel(active_panel, q=True, camera=True)

    if active_camera:
        current_context = cmds.currentCtx()

        if current_context == "moveSuperContext":
            cmds.manipMoveContext("Move", e=True, mode=6, orientObject=active_camera)

        if current_context == "RotateSuperContext":
            cmds.manipRotateContext("Rotate", e=True, mode=6, orientObject=active_camera)

        if current_context == "scaleSuperContext":
            cmds.manipScaleContext("Scale", e=True, mode=6, orientObject=active_camera)

        # コンポーネント再選択で方向が解除されないためのピン
        mel.eval('setTRSPinPivot true')


def unpin_maniplator_pivot():
    """マニピュレーターのピンを解除する."""
    current_pin = cmds.manipPivot(q=True, pin=True)
    current_pos = [0, 0, 0]

    current_context = cmds.currentCtx()

    if current_context == "moveSuperContext":
        current_pos = cmds.manipMoveContext("Move", q=True, p=True)

    if current_context == "RotateSuperContext":
        current_pos = cmds.manipRotateContext("Rotate", q=True, p=True)

    if current_context == "scaleSuperContext":
        current_pos = cmds.manipScaleContext("Scale", q=True, p=True)

    # ピンされているならピン解除する｡ピンされていないなら現在のピボット位置でピンする
    if current_pin:
        cmds.manipPivot(pin=False, reset=True)

    else:
        cmds.manipPivot(pin=True, p=current_pos)


def get_maya_window():
    """Mayaのメインウィンドウを取得するヘルパー関数."""
    ptr = omui.MQtUtil.mainWindow()
    if ptr is not None:
        return shiboken.wrapInstance(int(ptr), QtWidgets.QWidget)


def resize_editor(window_title, x=-1, y=-1, width=-1, height=-1):
    """指定した名前のウィンドウの位置とサイズを設定する.

    Args:
        window_title (str): タイトルバーに表示されているウィンドウ名
        x (int): 左上の x 座標｡負数で移動しない｡
        y (int): 左上の y 座標｡負数で移動しない｡
        width (int): ウィンドウ幅｡負数でリサイズしない｡
        height (int): ウィンドウ高｡負数でリサイズしない｡
    """
    maya_window = get_maya_window()

    # 全ての子ウィジェットに対して反復
    for child in maya_window.children():
        # ウィジェットが windowTitle 属性を持ち､引数 window_title に位置した場合に配置･リサイズする
        if hasattr(child, "windowTitle") and child.windowTitle() == window_title:
            if x >= 0 and y >= 0:
                child.move(x, y)

            if width >= 0 and height >= 0:
                child.resize(width, height)

            break


def select_all_skined_meshes_from_root_joint(root_object=None, select=True, result=False):
    """選択したジョイント以下にある全てのジョイントがスキンクラスターで影響を与えているメッシュを全て選択･取得する

    Args:
        root_obj (str, optional): スケルトン全体のルートオブジェクト｡省略時は選択オブジェクト. Defaults to None.
        select (bool, optional): 結果のメッシュを選択するかどうか. Defaults to True.

    Returns:
        list[str] | None: メッシュのノード名のリスト.エラー時は None.
    """
    if not root_object:
        selected_object = cmds.ls(selection=True)

        if not selected_object:
            print("select root object.")
            return None

        root_object = selected_object[0]

    all_joints = cmds.listRelatives(root_object, allDescendents=True)
    all_skinclusters = []

    for joint in all_joints:
        skinclusters = cmds.listConnections(joint, destination=True, type="skinCluster")

        if skinclusters:
            all_skinclusters.extend(skinclusters)

    all_skinclusters = list(set(all_skinclusters))

    if not all_skinclusters:
        print("no skincluster.")
        return None

    skined_meshes = []

    for sc in all_skinclusters:
        meshes = cmds.listConnections(sc, destination=True, type="mesh")
        skined_meshes.extend(meshes)

    skined_meshes = list(set(skined_meshes))

    if not skined_meshes:
        print("no skined meshes.", all_skinclusters)
        return None

    if select:
        cmds.select(skined_meshes, replace=True)

    return skined_meshes


def set_component_mode(type):
    """コンポーネントモードに設定する.

    vertex モードでは CV やラティスポイント等のポイント系コンポーネントも選択可能｡

    Args:
        type (str): "vertex", "edge", "face", "uv", "vertex_face" のいずれか｡
    """
    if type == "vertex":
        cmds.selectMode(component=True)
        cmds.selectType(
            subdivMeshPoint=True,
            subdivMeshEdge=False,
            subdivMeshFace=False,
            subdivMeshUV=False,
            polymeshVertex=True,
            polymeshEdge=False,
            polymeshFace=False,
            polymeshUV=False,
            polymeshVtxFace=False,
            controlVertex=True,
            latticePoint=True,
            )

    elif type == "edge":
        cmds.selectMode(component=True)
        cmds.selectType(
            subdivMeshPoint=False,
            subdivMeshEdge=True,
            subdivMeshFace=False,
            subdivMeshUV=False,
            polymeshVertex=False,
            polymeshEdge=True,
            polymeshFace=False,
            polymeshUV=False,
            polymeshVtxFace=False,
            controlVertex=False,
            latticePoint=False,
            )

    elif type == "face":
        cmds.selectMode(component=True)
        cmds.selectType(
            subdivMeshPoint=False,
            subdivMeshEdge=False,
            subdivMeshFace=True,
            subdivMeshUV=False,
            polymeshVertex=False,
            polymeshEdge=False,
            polymeshFace=True,
            polymeshUV=False,
            polymeshVtxFace=False,
            controlVertex=False,
            latticePoint=False,
            )

    elif type == "uv":
        cmds.selectMode(component=True)
        cmds.selectType(
            subdivMeshPoint=False,
            subdivMeshEdge=False,
            subdivMeshFace=False,
            subdivMeshUV=True,
            polymeshVertex=False,
            polymeshEdge=False,
            polymeshFace=False,
            polymeshUV=True,
            polymeshVtxFace=False,
            controlVertex=False,
            latticePoint=False,
            )

    elif type == "vertex_face":
        cmds.selectMode(component=True)
        cmds.selectType(
            subdivMeshPoint=False,
            subdivMeshEdge=False,
            subdivMeshFace=False,
            subdivMeshUV=False,
            polymeshVertex=False,
            polymeshEdge=False,
            polymeshFace=False,
            polymeshUV=False,
            polymeshVtxFace=True,
            controlVertex=False,
            latticePoint=False,
            )
    else:
        cmds.selectMode(component=True)


def edgeflow_each_object(edges=None, value=1):
    """選択エッジをオブジェクト毎にエッジフローを調整する.

    通常の polyEditEdgeFlow はオブジェクトをまたいで使用できないのでオブジェクト毎に実行するだけの関数｡
    """
    if not edges:
        targets = cmds.ls(selection=True)
    else:
        targets = edges

    if not targets:
        return

    edges_per_obj = dict()
    nodes = []

    for edge in targets:
        obj = cmds.polyListComponentConversion(edge)[0]
        edges_per_obj.setdefault(obj, [])
        edges_per_obj[obj].append(edge)

    for edges in edges_per_obj.values():
        nodes.append(cmds.polyEditEdgeFlow(edges, adjustEdgeFlow=value)[0])

    return nodes
