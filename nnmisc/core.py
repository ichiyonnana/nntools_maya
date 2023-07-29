# coding:utf-8
"""単独で機能する細かい関数｡カスタムスクリプトやシェルフから呼ぶ."""

import re

import maya.cmds as cmds
import maya.mel as mel
import pymel.core as pm
import maya.OpenMaya as om

import nnutil.ui as ui
import nnutil.misc as nm
import nnutil.decorator as nd


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


@nd.undo_chunk
def extrude_edges():
    """UV･頂点カラー等が設定されたエッジのextrude."""
    selected_edges = cmds.ls(selection=True, flatten=True)

    extrude_node = cmds.polyExtrudeEdge(
        selected_edges,
        constructionHistory=True,
        keepFacesTogether=True,
        divisions=1,
        offset=0.1,
        thickness=0)

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

