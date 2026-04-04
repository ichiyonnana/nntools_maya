import copy
import re
import os
import sys
import traceback

import maya.api.OpenMaya as om
import maya.cmds as cmds
import maya.mel as mel

import nnutil.core as nu
import nnutil.misc as nm
import nnutil.display as nd
import nnutil.ui as ui
import nnskin.core as nnskin

import plugin_util.snapshotState as ss


window_name = "NN_Mirror"
window = None


def get_window():
    return window


def mirror_objects(objects=None, axis=0, direction=1, cut=False, center_tolerance=0.001):
    if cut:
        merge_mode = 0
    else:
        merge_mode = 1

    objects = cmds.ls(selection=True, flatten=True)

    if cmds.objectType(objects[0]) in ('transform', 'mesh'):
        # オブジェクトで反復
        for obj in objects:
            if cmds.listRelatives(obj, shapes=True):
                # シンメトリ面から誤差範囲内にある頂点の座標を 0 にする
                points = nu.get_points(obj, space=om.MSpace.kObject)

                for point in points:
                    if axis == 0 and abs(point.x) <= center_tolerance:
                        point.x = 0

                    if axis == 1 and abs(point.y) <= center_tolerance:
                        point.y = 0

                    if axis == 2 and abs(point.z) <= center_tolerance:
                        point.z = 0

                nu.set_points(obj, points=points, space=om.MSpace.kObject)

                # ミラーの実行
                cmds.polyMirrorFace(obj, cutMesh=1, axis=axis, axisDirection=direction, mergeMode=merge_mode, mergeThresholdType=1, mergeThreshold=0.01, mirrorAxis=1, mirrorPosition=0, smoothingAngle=180, flipUVs=0, ch=1)
                cmds.bakePartialHistory(obj, ppt=True)
    else:
        # コンポーネント
        cmds.polyMirrorFace(cutMesh=1, axis=axis, axisDirection=direction, mergeMode=merge_mode, mergeThresholdType=1, mergeThreshold=0.01, mirrorAxis=1, mirrorPosition=0, smoothingAngle=180, flipUVs=0, ch=1)


def export_weight(objects=None, specified_name=None):
    """ウェイトをXMLでエクスポートする

    Args:
        objects (Transform or Mesh, optional): 対象のオブジェクト。省略時は選択オブジェクトを使用する. Defaults to None.
        specified_name (str, optional): ウェイトを書き出す際のファイル名。省略時はオブジェクト名。 Defaults to None.
    """
    # 選択復帰用
    current_selections = cmds.ls(selection=True)

    # オブジェクト未指定時は選択オブジェクトを使用する
    if not objects:
        objects = cmds.ls(selection=True, flatten=True)

        if not objects:
            raise(Exception("no targets"))

    # ウェイト用ディレクトリがなければ作成する
    currentScene = cmds.file(q=True, sn=True)
    dir = re.sub(r'/scenes/.+$', '/weights/', currentScene, 1)

    try:
        os.mkdir(dir)
    except:
        pass

    for obj in objects:
        # meshでなければskip
        if cmds.objectType(obj) not in ('transform', 'mesh'):
            continue

        skincluster_list = cmds.ls(cmds.listHistory(obj), type="skinCluster") or []
        skincluster = skincluster_list[0] if skincluster_list else ""

        # skincluster 無ければskip
        if skincluster == "":
            continue

        # エクスポートするファイル名の決定
        filename = ""

        if specified_name is None:
            filename = nu.get_basename(obj)

        else:
            filename = specified_name

        # エクスポート
        if nu.is_format_option_supported():
            cmd = 'deformerWeights -export -vc -deformer "%(skincluster)s" -format "XML" -path "%(dir)s" "%(filename)s.xml"' % locals()
        else:
            cmd = 'deformerWeights -export -vc -deformer %(skincluster)s -path "%(dir)s" "%(filename)s.xml"' % locals()

        try:
            mel.eval(cmd)
        except:
            print("Unable to export weights: " + obj)
            # エクスポートできないノードのスキップ
            pass

    # 選択復帰
    cmds.select(current_selections, replace=True)


# バインドメソッド
BM_INDEX = "index"
BM_NEAREST = "nearest"
BM_BARYCENTRIC = "barycentric"
BM_BILINEAR = "bilinear"
BM_OVER = "over"


def import_weight(objects=None, method=BM_BILINEAR, specified_name=None, unbind=True):
    """ウェイトをXMLからインポートする

    Args:
        objects (Transform or Mesh, optional): 対象のオブジェクト。省略時は選択オブジェクトを使用する. Defaults to None.
        method (str, optional): バインドメソッド. Defaults to BM_BILINEAR.
        specified_name (str, optional): ウェイトを読み込む際のファイル名。省略時はオブジェクト名。temp_mode よりも優先される. Defaults to None.
    """
    current_selections = cmds.ls(selection=True)

    if not objects:
        objects = cmds.ls(selection=True, flatten=True)

        if not objects:
            raise(Exception("no targets"))

    elif not isinstance(objects, list):
        raise(Exception())

    currentScene = cmds.file(q=True, sn=True)
    dir = re.sub(r'/scenes/.+$', '/weights/', currentScene, 1)

    for obj in objects:
        # meshでなければskip
        if cmds.objectType(obj) not in ('transform', 'mesh'):
            print(f"skip {obj}")
            continue

        # インポートするファイル名の決定
        if specified_name is None:
            filename = nu.get_basename(obj) + ".xml"
        else:
            if ".xml" in specified_name:
                filename = specified_name
            else:
                filename = specified_name + ".xml"

        # ウェイトファイルがあるオブジェクトだけ処理
        print(dir + filename)
        if nu.exist_file(dir, filename):
            # ウェイトファイル直接開いてインフルエンスリスト取得
            path = dir + filename
            with open(path) as f:
                xml = f.read()
                influence_list = re.findall(r'source="(.+?)"', xml)
                max_influence = 4

            if len(influence_list) == 0:
                continue

            # インフルエンス名と一致するジョイントがシーン内に無ければ警告
            joints_not_exist = []
            for joint in influence_list:
                if not cmds.objExists(joint):
                    joints_not_exist.append(joint)

            if len(joints_not_exist) != 0:
                print("The following joints do not exist in the scene:")
                print(joints_not_exist)

            # バインド済なら一度アンバインドする
            if unbind:
                skincluster_list = cmds.ls(cmds.listHistory(obj), type="skinCluster") or []
                skincluster = skincluster_list[0] if skincluster_list else ""
                if skincluster != "":
                    cmds.dagPose(cmds.skinCluster(skincluster, q=True, influence=True), bp=True, restore=True)
                    cmds.skinCluster(obj, e=True, unbind=True)

                # ウェイトファイルに保存されていたインフルエンスだけで改めてバインドする
                try:
                    cmds.select(cl=True)
                    cmds.select(obj, add=True)
                    for joint in nu.list_diff(influence_list, joints_not_exist):
                        cmds.select(joint, add=True)
                    skincluster = cmds.skinCluster(tsb=True, mi=max_influence, obeyMaxInfluences=False)

                except:
                    print(f"bind error: {obj}")

            # インポート
            cmds.deformerWeights(filename, im=True, method=method, deformer=skincluster, path=dir)
            cmds.skinCluster(skincluster, e=True, forceNormalizeWeights=True)

    cmds.select(current_selections, replace=True)


def combine_skined_mesh(objects=None):
    """指定したオブジェクトをウェイトを維持して結合する。

    バインド済みのメッシュとそうでないメッシュが混在していた場合はすべてバインド済みにした上で結合する。

    Args:
        objects (list[Mesh or Transform], optional): 結合対象のオブジェクト. Defaults to None.
    """
    if not objects:
        objects = cmds.ls(selection=True, flatten=True)

        if not objects:
            raise(Exception())

    elif not isinstance(objects, list):
        raise(Exception())

    all_meshes = []

    for obj in objects:
        meshes = cmds.listRelatives(obj, allDescendents=True, noIntermediate=True, type='mesh') or []
        all_meshes.extend(meshes)

    skined_meshes = []

    for mesh in all_meshes:
        if cmds.listConnections(mesh, type='skinCluster'):
            skined_meshes.append(mesh)

    name = objects[-1]
    parent_list = cmds.listRelatives(objects[-1], parent=True)
    parent = parent_list[0] if parent_list else None

    if not skined_meshes:
        # すべてが静的なメッシュなら polyUnite で結合する
        object, node = cmds.polyUnite(all_meshes, ch=1, mergeUVSets=1, objectPivot=True)
        if parent:
            cmds.parent(object, parent)
        else:
            cmds.parent(object, world=True)
        cmds.bakePartialHistory(object, ppt=True)
        cmds.rename(object, name)

    else:
        # バインド済みメッシュが含まれる場合
        # 全てのメッシュのインフルエンスををまとめたリストを作成
        all_influences = []
        for mesh in skined_meshes:
            influences = nnskin.get_influence_order(mesh) or []
            all_influences.extend(influences)

        all_influences = list(set(all_influences))

        # 全てのメッシュのインフルエンス順序を統一する
        for mesh in all_meshes:
            nnskin.set_influence_order(cmds.ls(mesh, long=True)[0], all_influences)

        # polyUniteSkinned で結合する
        object, node = cmds.polyUniteSkinned(all_meshes, ch=1, mergeUVSets=1, objectPivot=True)
        nu.unlock_trs(object)
        if parent:
            cmds.parent(object, parent)
        else:
            cmds.parent(object, world=True)
        nu.lock_trs(object)
        cmds.bakePartialHistory(object, ppt=True)
        cmds.rename(object, name)


def duplicate_object():
    """選択オブジェクトを複製する。スキンバインド済みの場合はウェイトも複製する。

    選択が Transform または Mesh でない場合は何もしない。
    Transform の場合はその Shape (Mesh) を対象とする。
    """
    selection = cmds.ls(selection=True)

    if selection:
        if cmds.objectType(selection[0]) not in ('transform', 'mesh'):
            return

        for sel in selection:
            obj_type = cmds.objectType(sel)

            if obj_type == 'transform':
                shapes = cmds.listRelatives(sel, shapes=True, type='mesh') or []
                if not shapes:
                    continue
                object = shapes[0]

            elif obj_type == 'mesh':
                object = sel

            else:
                continue

            # オブジェクト複製
            dup_transform = cmds.duplicate(object)[0]
            shapes2 = cmds.listRelatives(dup_transform, shapes=True) or []
            object2 = shapes2[0] if shapes2 else dup_transform

            # skined ならウェイト複製
            if nu.is_skined(object):
                weight_name = "duplicated_obj_weight"
                export_weight([object], specified_name=weight_name)
                import_weight([object2], method=BM_INDEX, specified_name=weight_name)


def duplicate_faces(extract=False):
    # 選択コンポーネント取得
    selection = cmds.ls(selection=True, flatten=True)
    selected_faces = cmds.filterExpand(selection, selectionMask=34) or []

    if not selected_faces:
        return None

    # 選択コンポーネントからオブジェクト取得
    object = cmds.polyListComponentConversion(selected_faces[0])[0]

    # オブジェクト複製
    dup_transform = cmds.duplicate(object)[0]
    shapes2 = cmds.listRelatives(dup_transform, shapes=True) or []
    object2 = shapes2[0] if shapes2 else dup_transform

    # skined ならウェイト複製
    if nu.is_skined(object):
        weight_name = "duplicated_obj_weight"
        export_weight([object], specified_name=weight_name)
        import_weight([object2], method=BM_INDEX, specified_name=weight_name)

    # 選択コンポーネント以外削除
    face_indices = [nu.get_index(f) for f in selected_faces]
    num_faces = cmds.polyEvaluate(object2, face=True)
    delete_faces = [f"{object2}.f[{fi}]" for fi in range(num_faces) if fi not in face_indices]

    if delete_faces:
        cmds.delete(delete_faces)

    # extract True なら元オブジェクトの選択コンポーネント削除
    if extract:
        cmds.delete(selected_faces)

    cmds.bakePartialHistory(object, ppt=True)
    cmds.bakePartialHistory(object2, ppt=True)


class NN_ToolWindow(object):

    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (10, 10)

    def create(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)

        # プリファレンスの有無による分岐
        if cmds.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = cmds.windowPref(self.window, q=True, topLeftCorner=True)
            cmds.windowPref(self.window, remove=True)

            # 前回位置に指定したサイズで表示
            cmds.window(
                self.window,
                t=self.title,
                maximizeButton=False,
                minimizeButton=False,
                topLeftCorner=position,
                widthHeight=self.size,
                sizeable=False,
                resizeToFitChildren=True
                )

        else:
            # プリファレンスがなければデフォルト位置に指定サイズで表示
            cmds.window(
                self.window,
                t=self.title,
                maximizeButton=False,
                minimizeButton=False,
                widthHeight=self.size,
                sizeable=False,
                resizeToFitChildren=True
                )

        self.layout()
        cmds.showWindow(self.window)

    def layout(self):
        separator_width = 250

        ui.column_layout()

        ui.row_layout()
        ui.button(label='Geo', width=ui.width(2), c=self.onMirrorFaceOp)
        ui.button(label='X+', c=self.onMirrorFaceXPosi, dgc=self.onCutGeoXPosi, bgc=ui.color_x, annotation="L: Mirror\nM: Cut")
        ui.button(label='X-', c=self.onMirrorFaceXNega, dgc=self.onCutGeoXNega, bgc=ui.color_x, annotation="L: Mirror\nM: Cut")
        ui.button(label='Y+', c=self.onMirrorFaceYPosi, dgc=self.onCutGeoYPosi, bgc=ui.color_y, annotation="L: Mirror\nM: Cut")
        ui.button(label='Y-', c=self.onMirrorFaceYNega, dgc=self.onCutGeoYNega, bgc=ui.color_y, annotation="L: Mirror\nM: Cut")
        ui.button(label='Z+', c=self.onMirrorFaceZPosi, dgc=self.onCutGeoZPosi, bgc=ui.color_z, annotation="L: Mirror\nM: Cut")
        ui.button(label='Z-', c=self.onMirrorFaceZNega, dgc=self.onCutGeoZNega, bgc=ui.color_z, annotation="L: Mirror\nM: Cut")
        self.eb_center_threshold = ui.eb_float(v=0.001, width=ui.width2)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='Set')
        ui.button(label='X = ', c=self.onSetXOS, dgc=self.onSetXWS, bgc=ui.color_x, width=ui.width1, annotation="L: Object\nM: World\nShift: Negative")
        ui.button(label='Y = ', c=self.onSetYOS, dgc=self.onSetYWS, bgc=ui.color_y, width=ui.width1, annotation="L: Object\nM: World\nShift: Negative")
        ui.button(label='Z = ', c=self.onSetZOS, dgc=self.onSetZWS, bgc=ui.color_z, width=ui.width1, annotation="L: Object\nM: World\nShift: Negative")
        self.coord_value = ui.eb_float(v=0, width=ui.width2)
        self.cb_set_position_relative = ui.check_box(label="Relative", v=False)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='Flip')
        ui.button(label='X', c=self.onFlipX, bgc=ui.color_x, width=ui.width2)
        ui.button(label='Y', c=self.onFlipY, bgc=ui.color_y, width=ui.width2)
        ui.button(label='Z', c=self.onFlipZ, bgc=ui.color_z, width=ui.width2)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='Flatten')
        ui.button(label='X', c=self.onFlattenX, bgc=ui.color_x, width=ui.width2)
        ui.button(label='Y', c=self.onFlattenY, bgc=ui.color_y, width=ui.width2)
        ui.button(label='Z', c=self.onFlattenZ, bgc=ui.color_z, width=ui.width2)
        ui.end_layout()

        ui.separator(width=separator_width)

        ui.row_layout()
        ui.button(label='Weight', width=ui.width(2), c=self.onMirrorWeightOp)
        ui.button(label='X+', c=self.onMirrorWeightXPosi, bgc=ui.color_x)
        ui.button(label='X-', c=self.onMirrorWeightXNega, bgc=ui.color_x)
        ui.button(label='Y+', c=self.onMirrorWeightYPosi, bgc=ui.color_y)
        ui.button(label='Y-', c=self.onMirrorWeightYNega, bgc=ui.color_y)
        ui.button(label='Z+', c=self.onMirrorWeightZPosi, bgc=ui.color_z)
        ui.button(label='Z-', c=self.onMirrorWeightZNega, bgc=ui.color_z)
        self.cb_label_mirror = ui.check_box(label="Label", v=False)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='copyWeightOp', c=self.onCopyWeightOp)
        ui.end_layout()

        ui.separator(width=separator_width)

        ui.row_layout()
        ui.button(label='Joint', width=ui.width(2), c=self.onMirrorJointOp)
        ui.button(label='X', c=self.onMirrorJointX, dgc=self.onMirrorJointXWorld, bgc=ui.color_x, width=ui.width2, annotation="L: Object (with parent)\nM: World")
        ui.button(label='Y', c=self.onMirrorJointY, dgc=self.onMirrorJointYWorld, bgc=ui.color_y, width=ui.width2, annotation="L: Object (with parent)\nM: World")
        ui.button(label='Z', c=self.onMirrorJointZ, dgc=self.onMirrorJointZWorld, bgc=ui.color_z, width=ui.width2, annotation="L: Object (with parent)\nM: World")
        ui.button(label='Symm', c=self.onSymmetrizeJointOriPos, width=ui.width(2), annotation="")
        ui.end_layout()

        ui.row_layout()
        ui.header()
        self.eb_prefix_from = ui.eb_text(text="L_")
        self.eb_prefix_to = ui.eb_text(text="R_")
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='JointTool', c=self.onJointTool, bgc=ui.color_joint, width=ui.width2)
        ui.button(label='SetRadius', c=self.onSetRadius, width=ui.width2)
        ui.button(label="Add Inf", c=self.onAddInfluence, width=ui.width(2))
        ui.end_layout()

        ui.separator(width=separator_width)

        ui.row_layout()
        ui.button(label="Orient", c=self.onOrientJointOp, width=ui.width(2))
        ui.button(label="Radial", c=self.onOrientRadial, width=ui.width(2))
        ui.button(label="PreserveY", c=self.onOrientPreserveY, dgc=self.onOrientPreserveZ, width=ui.width(2), annotation="L: Preserve Y \nM: Preserve Z")
        ui.button(label="Equalize", c=self.onJointEqualize, width=ui.width(2))
        ui.end_layout()

        ui.separator(width=separator_width)

        ui.row_layout()
        ui.header(label='weight')
        ui.button(label='export', c=self.onExportWeight, dgc=self.onExportWeightOptions)
        self.cb_specify_name = ui.check_box(label='specify name', v=False)
        self.eb_tempname = ui.eb_text(text="temp", width=ui.width(3))
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='index', c=self.onImportWeightIndex, dgc=self.onImportWeightIndexB, annotation="L: ReBind\nM: Keep Bind")
        ui.button(label='nearest', c=self.onImportWeightNearest, dgc=self.onImportWeightNearestB, annotation="L: ReBind\nM: Keep Bind")
        # ui.button(label='barycentric', c=self.onImportWeightBarycentric, dgc=self.onImportWeightOptions, annotation="L: ReBind\nM: Keep Bind")
        ui.button(label='bilinear', c=self.onImportWeightBilinear, dgc=self.onImportWeightBilinearB, annotation="L: ReBind\nM: Keep Bind")
        ui.button(label='over', c=self.onImportWeightOver, dgc=self.onImportWeightOverB, annotation="L: ReBind\nM: Keep Bind")
        ui.end_layout()

        ui.separator(width=separator_width)

        ui.row_layout()
        ui.header(label='bind')
        ui.button(label='bind Op', c=self.onBindOptions, dgc=self.onBind, annotation="L: Bind Options\nM: Auto")
        ui.button(label='unbind', c=self.onUnbind, dgc=self.onUnbindOptions, annotation="L: Unbind\nM: Options")
        ui.button(label='unlockTRS [lock]', c=self.onUnlockTRS, dgc=self.onLockTRS, annotation="L: Unlock\nM: Lock")
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='reset pose', c=self.onResetPose)
        ui.button(label='move joint', c=self.onMoveSkinedJointTool)
        ui.button(label='del pose', c=self.onDeletePose)
        ui.end_layout()

        ui.separator(width=separator_width)

        ui.row_layout()
        ui.header(label='combine')
        ui.button(label='combine', c=self.onCombine)
        ui.button(label='combine Op', c=self.onCombineOptions)
        ui.end_layout()

        ui.separator(width=separator_width)

        ui.row_layout()
        ui.header(label='Anim')
        ui.button(label='export', c=self.onExportAnim)
        ui.button(label='import', c=self.onImportAnim)
        ui.end_layout()

        ui.separator(width=separator_width)

        ui.row_layout()
        ui.header(label='Editor')
        ui.button(label='SIWE', c=self.onEditorSIWE)
        ui.end_layout()

        ui.separator(width=separator_width)

        ui.row_layout()
        ui.header(label='AriTools')
        ui.button(label='Symm', c=self.onAriSymmetryChecker)
        ui.button(label='Circle', c=self.onAriCircleVertex)
        ui.button(label='SelectEdge', c=self.onAriSelectEdgeLoopRing)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='SplitPolygon', c=self.onAriSplitPolygon)
        ui.end_layout()

        ui.separator(width=separator_width)

        ui.row_layout()
        ui.header(label='Mesh')
        ui.button(label='Extract', c=self.onExtract)
        ui.button(label='Duplicate', c=self.onDuplicate)
        ui.button(label='QRemesher', c=self.onQuadRemesher)
        ui.end_layout()

        ui.separator(width=separator_width)

        ui.row_layout()
        ui.header(label='Etc')
        ui.button(label='Get Pos', c=self.onGetPos, annotation=u"Shift + L: World")
        ui.button(label='Set Pos', c=self.onSetPos, annotation=u"Shift + L: World")
        ui.button(label="GoZ", c=self.onGoZ)
        ui.end_layout()

    def onMirrorFaceXPosi(self, *args):
        center_threshold = ui.get_value(self.eb_center_threshold)
        mirror_objects(axis=0, direction=0, cut=False, center_tolerance=center_threshold)

    def onMirrorFaceXNega(self, *args):
        center_threshold = ui.get_value(self.eb_center_threshold)
        mirror_objects(axis=0, direction=1, cut=False, center_tolerance=center_threshold)

    def onMirrorFaceYPosi(self, *args):
        center_threshold = ui.get_value(self.eb_center_threshold)
        mirror_objects(axis=1, direction=0, cut=False, center_tolerance=center_threshold)

    def onMirrorFaceYNega(self, *args):
        center_threshold = ui.get_value(self.eb_center_threshold)
        mirror_objects(axis=1, direction=1, cut=False, center_tolerance=center_threshold)

    def onMirrorFaceZPosi(self, *args):
        center_threshold = ui.get_value(self.eb_center_threshold)
        mirror_objects(axis=2, direction=0, cut=False, center_tolerance=center_threshold)

    def onMirrorFaceZNega(self, *args):
        center_threshold = ui.get_value(self.eb_center_threshold)
        mirror_objects(axis=2, direction=1, cut=False, center_tolerance=center_threshold)

    def onMirrorFaceOp(self, *args):
        mel.eval('MirrorPolygonGeometryOptions')

    def onSetXOS(self, *args):
        v = ui.get_value(self.coord_value)
        if ui.is_shift():
            v *= -1

        relative = ui.get_value(self.cb_set_position_relative)
        nm.set_coord('x', v, space="object", relative=relative)

    def onSetYOS(self, *args):
        v = ui.get_value(self.coord_value)
        if ui.is_shift():
            v *= -1

        relative = ui.get_value(self.cb_set_position_relative)
        nm.set_coord('y', v, space="object", relative=relative)

    def onSetZOS(self, *args):
        v = ui.get_value(self.coord_value)
        if ui.is_shift():
            v *= -1

        relative = ui.get_value(self.cb_set_position_relative)
        nm.set_coord('z', v, space="object", relative=relative)

    def onSetXWS(self, *args):
        v = ui.get_value(self.coord_value)
        if ui.is_shift():
            v *= -1

        relative = ui.get_value(self.cb_set_position_relative)
        nm.set_coord('x', v, space="world", relative=relative)

    def onSetYWS(self, *args):
        v = ui.get_value(self.coord_value)
        if ui.is_shift():
            v *= -1

        relative = ui.get_value(self.cb_set_position_relative)
        nm.set_coord('y', v, space="world", relative=relative)

    def onSetZWS(self, *args):
        v = ui.get_value(self.coord_value)
        if ui.is_shift():
            v *= -1

        relative = ui.get_value(self.cb_set_position_relative)
        nm.set_coord('z', v, space="world", relative=relative)

    def onSetZeroCenter(objects, axis):
        """
        指定オブジェクトの頂点のうちシンメトリ面に近い頂点の座標を厳密に0に設定する
        """
        selection = cmds.ls(selection=True, flatten=True)
        for v in selection:
            x, y, z = cmds.xform(v, q=True, a=True, os=True, t=True)
            cmds.xform(v, a=True, os=True, t=(0, y, z))

    def onCutGeoXPosi(self, *args):
        mirror_objects(axis=0, direction=0, cut=True)

    def onCutGeoXNega(self, *args):
        mirror_objects(axis=0, direction=1, cut=True)

    def onCutGeoYPosi(self, *args):
        mirror_objects(axis=1, direction=0, cut=True)

    def onCutGeoYNega(self, *args):
        mirror_objects(axis=1, direction=1, cut=True)

    def onCutGeoZPosi(self, *args):
        mirror_objects(axis=2, direction=0, cut=True)

    def onCutGeoZNega(self, *args):
        mirror_objects(axis=2, direction=1, cut=True)

    def onFlipX(self, *args):
        selections = cmds.ls(selection=True, flatten=True)
        vts = cmds.filterExpand(cmds.polyListComponentConversion(selections, tv=True), sm=31)
        for vtx in vts:
            p = cmds.xform(vtx, q=True, os=True, t=True)
            new_point = [-p[0], p[1], p[2]]
            cmds.xform(vtx, os=True, t=new_point)
        cmds.polyNormal(normalMode=0, userNormalMode=0, ch=1)

    def onFlipY(self, *args):
        selections = cmds.ls(selection=True, flatten=True)
        vts = cmds.filterExpand(cmds.polyListComponentConversion(selections, tv=True), sm=31)
        for vtx in vts:
            p = cmds.xform(vtx, q=True, os=True, t=True)
            new_point = [p[0], -p[1], p[2]]
            cmds.xform(vtx, os=True, t=new_point)
        cmds.polyNormal(normalMode=0, userNormalMode=0, ch=1)

    def onFlipZ(self, *args):
        selections = cmds.ls(selection=True, flatten=True)
        vts = cmds.filterExpand(cmds.polyListComponentConversion(selections, tv=True), sm=31)
        for vtx in vts:
            p = cmds.xform(vtx, q=True, os=True, t=True)
            new_point = [p[0], p[1], -p[2]]
            cmds.xform(vtx, os=True, t=new_point)
        cmds.polyNormal(normalMode=0, userNormalMode=0, ch=1)

    def onFlattenX(self, *args):
        nm.align_horizontally(each_polyline=True, axis="x")

    def onFlattenY(self, *args):
        nm.align_horizontally(each_polyline=True, axis="y")

    def onFlattenZ(self, *args):
        nm.align_horizontally(each_polyline=True, axis="z")

    def onMirrorWeightXPosi(self, *args):
        method = "label" if ui.get_value(self.cb_label_mirror) else "closestJoint"
        cmds.copySkinWeights(mirrorMode="YZ", mirrorInverse=True, surfaceAssociation="closestPoint", influenceAssociation=method)

    def onMirrorWeightXNega(self, *args):
        method = "label" if ui.get_value(self.cb_label_mirror) else "closestJoint"
        cmds.copySkinWeights(mirrorMode="YZ", surfaceAssociation="closestPoint", influenceAssociation=method)

    def onMirrorWeightYPosi(self, *args):
        method = "label" if ui.get_value(self.cb_label_mirror) else "closestJoint"
        cmds.copySkinWeights(mirrorMode="XZ", mirrorInverse=True, surfaceAssociation="closestPoint", influenceAssociation=method)

    def onMirrorWeightYNega(self, *args):
        method = "label" if ui.get_value(self.cb_label_mirror) else "closestJoint"
        cmds.copySkinWeights(mirrorMode="XZ", surfaceAssociation="closestPoint", influenceAssociation=method)

    def onMirrorWeightZPosi(self, *args):
        method = "label" if ui.get_value(self.cb_label_mirror) else "closestJoint"
        cmds.copySkinWeights(mirrorMode="XY", mirrorInverse=True, surfaceAssociation="closestPoint", influenceAssociation=method)

    def onMirrorWeightZNega(self, *args):
        method = "label" if ui.get_value(self.cb_label_mirror) else "closestJoint"
        cmds.copySkinWeights(mirrorMode="XY", surfaceAssociation="closestPoint", influenceAssociation=method)

    def onMirrorWeightOp(self, *args):
        mel.eval('MirrorSkinWeightsOptions')

    def onMirrorJointX(self, *args):
        self._mirrorJoint(axis="x")

    def onMirrorJointY(self, *args):
        self._mirrorJoint(axis="y")

    def onMirrorJointZ(self, *args):
        self._mirrorJoint(axis="z")

    def _mirrorJoint(self, axis="x", *args):
        if axis == "x":
            mirror_dir = "mirrorYZ"
        elif axis == "y":
            mirror_dir = "mirrorXZ"
        elif axis == "z":
            mirror_dir = "mirrorXY"
        else:
            raise("unkown axis")

        current_selections = cmds.ls(selection=True)

        joints = cmds.ls(selection=True, type="joint")

        cmds.select(clear=True)
        root_joint = cmds.joint(p=[0, 0, 0])

        for joint in joints:
            cmds.select(joint, replace=True)
            prefix_from = ui.get_value(self.eb_prefix_from)
            prefix_to = ui.get_value(self.eb_prefix_to)
            mel.eval('mirrorJoint -%s -mirrorBehavior -searchReplace "%s" "%s";' % (mirror_dir, prefix_from, prefix_to))

        cmds.select(current_selections)

    def onMirrorJointXWorld(self, *args):
        self._mirrorJointWorld(axis="x")

    def onMirrorJointYWorld(self, *args):
        self._mirrorJointWorld(axis="y")

    def onMirrorJointZWorld(self, *args):
        self._mirrorJointWorld(axis="z")

    def _mirrorJointWorld(self, axis="x", *args):
        if axis == "x":
            mirror_dir = "mirrorYZ"
        elif axis == "y":
            mirror_dir = "mirrorXZ"
        elif axis == "z":
            mirror_dir = "mirrorXY"
        else:
            raise("unkown axis")

        current_selections = cmds.ls(selection=True)

        joints = cmds.ls(selection=True, type="joint")

        cmds.select(clear=True)
        root_joint = cmds.joint(p=[0, 0, 0])

        for joint in joints:
            current_parent = cmds.listRelatives(joint, parent=True)
            cmds.parent(joint, root_joint)
            prefix_from = ui.get_value(self.eb_prefix_from)
            prefix_to = ui.get_value(self.eb_prefix_to)
            cmds.select(joint, replace=True)
            opposite_joint = cmds.mirrorJoint(joint, mirrorBehavior=True, searchReplace=(prefix_from, prefix_to), **{mirror_dir: True})[0]
            print(opposite_joint)
            cmds.parent(opposite_joint, world=True)
            if current_parent:
                cmds.parent(joint, current_parent[0])
            else:
                cmds.parent(joint, world=True)

        cmds.delete(root_joint)
        cmds.select(current_selections)

    def onMirrorJointOp(self, *args):
        mel.eval('MirrorJointOptions')

    def _get_opposite_joint(self, joint_name):    
        prefix_from = ui.get_value(self.eb_prefix_from)
        prefix_to = ui.get_value(self.eb_prefix_to)

        basename = joint_name.split("|")[-1]
        
        if re.search(prefix_from, basename):
            return re.sub(prefix_from, prefix_to, basename)
        
        return None

    def _mirror_joint(self, joint, pos=True, ori=True):
        opposite_joint = self._get_opposite_joint(joint)
        if not opposite_joint or not cmds.objExists(opposite_joint):
            print(f"{joint}に対応するジョイントが見つかりませんでした。")
            return
        
        # ジョイントのワールドマトリクス
        matrix = cmds.xform(joint, query=True, matrix=True, worldSpace=True)

        # 対向ジョイントのワールドマトリクス
        opposite_matrix = cmds.xform(opposite_joint, query=True, matrix=True, worldSpace=True)

        # 対向ジョイントの基底ベクトルと位置を取得
        obx = om.MVector(opposite_matrix[0:3])
        oby = om.MVector(opposite_matrix[4:7])
        obz = om.MVector(opposite_matrix[8:11])
        op = om.MVector(opposite_matrix[12:15])

        # 新しい基底ベクトルと位置を計算
        new_bx = om.MVector(-obx.x, obx.y, obx.z)
        new_by = om.MVector(-oby.x, oby.y, oby.z)
        new_bz = new_bx ^ new_by
        new_p = om.MVector(-op.x, op.y, op.z)

        # 新しいマトリックスを作成
        new_matrix = matrix
        
        if pos:
            new_matrix[12:15] = [new_p.x, new_p.y, new_p.z]

        if ori:
            new_matrix[0:3] = [new_bx.x, new_bx.y, new_bx.z]
            new_matrix[4:7] = [new_by.x, new_by.y, new_by.z]
            new_matrix[8:11] = [new_bz.x, new_bz.y, new_bz.z]

        # 子があればワールドマトリックスを取得
        children = cmds.listRelatives(joint, children=True, fullPath=True)
        child_matrix = None
        if children:
            child_matrix = cmds.xform(children[0], query=True, matrix=True, worldSpace=True)

        # 新しいマトリクスを適用
        cmds.xform(joint, matrix=new_matrix, worldSpace=True)
        
        # 回転をフリーズ
        cmds.makeIdentity(joint, apply=True, rotate=True)

        # 子を復帰
        if child_matrix:
            cmds.xform(children[0], matrix=child_matrix, worldSpace=True)
            cmds.makeIdentity(children[0], apply=True, rotate=True)

    def onSymmetrizeJointOriPos(self, *args):
        # 選択されたジョイントを取得
        selected_joints = cmds.ls(selection=True, type='joint')
        if not selected_joints:
            cmds.error("ジョイントを選択してください。")
            return

        # 階層が浅い順にソート
        selected_joints.sort(key=lambda x: x.count('|'))

        # ジョイントの対象化
        for joint in selected_joints:
            self._mirror_joint(joint)

    def onOrientJointOp(self, *args):
        mel.eval('OrientJointOptions')

    def onOrientRadial(self, *args):
        """ジョイントを親に対して放射状にやるように方向付けする"""
        for joint in cmds.ls(selection=True, type="joint", long=True):
            parent = (cmds.listRelatives(joint, parent=True) or [None])[0]
            child = (cmds.listRelatives(joint, children=True) or [None])[0]

            if not parent:
                continue

            if not child:
                cmds.xform(joint, rotation=(0, 0, 0))
                cmds.setAttr(f"{joint}.jointOrientX", 0)
                cmds.setAttr(f"{joint}.jointOrientY", 0)
                cmds.setAttr(f"{joint}.jointOrientZ", 0)
                continue

            # この復帰用に子の姿勢を保存
            children = cmds.listRelatives(joint, children=True, fullPath=True)
            children_matrix = dict()
            for child in children:
                children_matrix[child] = cmds.xform(child, q=True, matrix=True, worldSpace=True)

            joint_matrix = cmds.xform(joint, q=True, matrix=True, worldSpace=True)
            parent_matrix = cmds.xform(parent, q=True, matrix=True, worldSpace=True)
            child_matrix = cmds.xform(child, q=True, matrix=True, worldSpace=True)

            joint_pos = om.MVector(joint_matrix[12:15])
            parent_pos = om.MVector(parent_matrix[12:15])
            child_pos = om.MVector(child_matrix[12:15])

            parent_dir = (joint_pos - parent_pos).normal()
            child_dir = (child_pos - joint_pos).normal()
            parent_dir

            # 基底ベクトルの計算
            x_basis = child_dir
            z_basis = x_basis ^ parent_dir
            y_basis = -x_basis ^ z_basis

            # 3ジョイントが直線上になっているときは親のYZ軸を使用する
            if abs(parent_dir * child_dir) > 0.99:
                y_basis = om.MVector(parent_matrix[4:7])
                z_basis = om.MVector(parent_matrix[8:11])

            x_basis.normalize()
            y_basis.normalize()
            z_basis.normalize()

            new_matrix = joint_matrix
            new_matrix[0:3] = list(x_basis)
            new_matrix[4:7] = list(y_basis)
            new_matrix[8:11] = list(z_basis)

            # ジョイントの姿勢を変更
            cmds.xform(joint, m=new_matrix, worldSpace=True)

            # 子の復帰
            for child in children:
                cmds.xform(child, m=children_matrix[child], worldSpace=True)

            # 回転のフリーズ
            cmds.makeIdentity(joint, apply=True, rotate=True)

    def onOrientPreserveY(self, *args):
        """Y軸を維持してX軸を子に向ける"""
        from . import orient_joint_preserve_secondary as ojps
        ojps.orient_joint_preserve_secondary(primary="x", secondary="y", zero_leaf_orient=True)

    def onOrientPreserveZ(self, *args):
        """Z軸を維持してX軸を子に向ける"""
        import nnutil.orient_joint_preserve_secondary as ojps
        ojps.orient_joint_preserve_secondary(primary="x", secondary="z", zero_leaf_orient=True)

    def onJointEqualize(self, *args):
        """ジョイントの長さを均等にする"""
        for selected_joint in cmds.ls(selection=True, type="joint"):
            joints = cmds.listRelatives(ad=True)
            total_len = sum([cmds.getAttr(x + ".tx") for x in joints])
            each_len = total_len / len(joints)

            for joint in joints:
                cmds.setAttr(joint + ".tx", each_len)

    def onJointTool(self, *args):
        mel.eval('JointTool')

    def onSetRadius(self, *args):
        nm.set_radius_auto()

    def onAddInfluence(self, *args):
        """"選択された全てのジョイントを選択された全てのメッシュのスキンクラスターにインフルエンスとして追加する｡"""
        joints = cmds.ls(selection=True, exactType="joint")
        transforms = cmds.ls(selection=True, exactType="transform", long=True)
        target_skinclusters = []

        if not joints or not transforms:
            return

        for transform in transforms:
            all_meshes = cmds.listRelatives(transform, shapes=True, noIntermediate=False, type="mesh", fullPath=True) or []

            for mesh in all_meshes:
                skinclusters = cmds.listConnections(mesh, source=True, type="skinCluster") or []
                target_skinclusters.extend(skinclusters)

        for skincluster in target_skinclusters:
            current_influences = cmds.skinCluster(skincluster, q=True, influence=True)
            additional_influences = list(set(joints) - set(current_influences))
            cmds.skinCluster(skincluster, e=True, addInfluence=additional_influences, weight=0)

            print("added joints to ", skincluster, additional_influences)

    def onExportWeight(self, *args):
        is_specify_name = ui.get_value(self.cb_specify_name)
        filename = ui.get_value(self.eb_tempname)

        if is_specify_name:
            export_weight(specified_name=filename)
        else:
            export_weight()

    def onExportWeightOptions(self, *args):
        mel.eval('ExportDeformerWeights')

    def import_weight(self, method, unbind):
        is_specify_name = ui.get_value(self.cb_specify_name)
        filename = ui.get_value(self.eb_tempname)

        if is_specify_name:
            import_weight(specified_name=filename, method=method, unbind=unbind)
        else:
            import_weight(method=method, unbind=unbind)

    def onImportWeightIndex(self, *args):
        self.import_weight(method=BM_INDEX, unbind=True)

    def onImportWeightNearest(self, *args):
        self.import_weight(method=BM_NEAREST, unbind=True)

    def onImportWeightBarycentric(self, *args):
        self.import_weight(method=BM_BARYCENTRIC, unbind=True)

    def onImportWeightBilinear(self, *args):
        self.import_weight(method=BM_BILINEAR, unbind=True)

    def onImportWeightOver(self, *args):
        self.import_weight(method=BM_OVER, unbind=False)

    def onImportWeightIndexB(self, *args):
        self.import_weight(method=BM_INDEX, unbind=False)

    def onImportWeightNearestB(self, *args):
        self.import_weight(method=BM_NEAREST, unbind=False)

    def onImportWeightBarycentricB(self, *args):
        self.import_weight(method=BM_BARYCENTRIC, unbind=False)

    def onImportWeightBilinearB(self, *args):
        self.import_weight(method=BM_BILINEAR, unbind=False)

    def onImportWeightOverB(self, *args):
        self.import_weight(method=BM_OVER, unbind=False)

    def onImportWeightOptions(self, *args):
        mel.eval('ImportDeformerWeights')

    def onBindOptions(self, *args):
        mel.eval('SmoothBindSkinOptions')

    def onBind(self, *args):
        cmds.skinCluster()

    def onUnbind(self, *args):
        mel.eval('DetachSkin')

    def onUnbindOptions(self, *args):
        mel.eval('DetachSkinOptions')

    def onUnlockTRS(self, *args):
        for obj in cmds.ls(selection=True, flatten=True, type="transform"):
            nu.unlock_trs(obj)

    def onLockTRS(self, *args):
        for obj in cmds.ls(selection=True, flatten=True, type="transform"):
            nu.lock_trs(obj)

    def onResetPose(self, *args):
        """バインドポーズに保存されたTRSのうち、現在選択中のジョイントとその子孫のみ現在の TRS でバインドポーズを上書きする"""
        selected_joints = cmds.ls(selection=True, type="joint") or []

        if selected_joints:
            child_joints = [(cmds.listRelatives(x, children=True, type="joint") or [None])[0] for x in selected_joints]

        selected_joints = list(filter(None, selected_joints))
        child_joints = list(filter(None, child_joints))
        target_joints = selected_joints + child_joints

        cmds.dagPose(target_joints, reset=True, n="bindPose1", bindPose=True)

    def onMoveSkinedJointTool(self, *args):
        mel.eval("MoveSkinJointsTool")
        cmds.manipMoveContext("moveSkinJointsToolCtx", e=True, orientJointEnabled=True)

    def onDeletePose(self, *args):
        poses = [x for x in cmds.ls(type="dagPose") if "bindPose" in x]

        if len(poses) == 0:
            return

        elif len(poses) >= 2:
            cmds.delete(poses[1:-1])

        else:
            pass

        cmds.rename(poses[0], "bindPose1")

    def onCombine(self, *args):
        combine_skined_mesh()

    def onCombineOptions(self, *args):
        mel.eval("CombinePolygonsOptions")

    def onExportAnim(self, *args):
        mel.eval('ExportAnim')

    def onImportAnim(self, *args):
        mel.eval('ImportAnim')

    def onEditorSIWE(self, *args):
        import siweighteditor.siweighteditor
        siweighteditor.siweighteditor.Option()

    def onCopyWeightOp(self, *args):
        mel.eval("CopySkinWeightsOptions")

    def onAriSymmetryChecker(self, *args):
        mel.eval("AriSymmetryChecker")

    def onAriCircleVertex(self, *args):
        mel.eval("AriCircleVertex")

    def onAriSelectEdgeLoopRing(self, *args):
        mel.eval("AriSelectEdgeLoopRing")

    def onAriStraightVertex(self, *args):
        mel.eval("AriStraightVertex")

    def onAriSplitPolygon(self, *args):
        mel.eval("AriSplitPolygon")

    def onQuadRemesher(self, *args):
        import QuadRemesher
        QuadRemesher.QuadRemesher()

    def onSimplygon(self, *args):
        mel.eval("SimplygonUI")

    def onExtract(self, *args):
        duplicate_faces(extract=True)

    def onDuplicate(self, *args):
        """"""
        selection = cmds.ls(selection=True)

        if selection:
            if cmds.objectType(selection[0]) in ('transform', 'mesh'):
                duplicate_object()

            elif cmds.filterExpand(selection[0], selectionMask=34):
                duplicate_faces()

            else:
                return

    def onGetPos(self, *args):
        """選択オブジェクトの頂点座標を self.getpos_points に保持する。

        Shift 押下時はワールドスペース、そうでない場合はオブジェクトスペースで取得する。
        self.getpos_points は MFnMesh.getPoints() の返り値 (MPointArray) をそのまま保持する。
        """
        obj = cmds.ls(selection=True, flatten=True)[0]

        if ui.is_shift():
            self.getpos_points = nu.get_points(obj, space=om.MSpace.kWorld)
            nd.message("copy points (world space)")

        else:
            self.getpos_points = nu.get_points(obj, space=om.MSpace.kObject)
            nd.message("copy points (object space)")

    def onSetPos(self, *args):
        """self.getpos_points の頂点座標を選択オブジェクトにペーストする。

        Shift 押下時はワールドスペース、そうでない場合はオブジェクトスペースで設定する。
        オブジェクト選択時は全頂点、頂点選択時は選択頂点のインデックスに対してのみ適用する。
        self.getpos_points は MFnMesh.getPoints() の返り値 (MPointArray) を想定する。
        """
        selections = cmds.ls(selection=True, flatten=True)

        # 選択がない場合は終了
        if not selections:
            return

        # shift が押されている場合はワールドスペースにペースト
        if ui.is_shift():
            space = om.MSpace.kWorld
            nd.message("paste points (world space)")
        else:
            space = om.MSpace.kObject
            nd.message("paste points (object space)")

        # 選択モードによる分岐
        if cmds.selectMode(q=True, object=True):
            # オブジェクト選択の場合は全頂点にペースト
            for obj in selections:
                nu.set_points(obj, points=self.getpos_points, space=space)

        elif cmds.selectType(q=True, polymeshVertex=True):
            # 頂点選択の場合は選択頂点のみにペースト
            obj = nu.get_object(selections[0])

            current_points = nu.get_points(obj, space=space)
            new_points = [x for x in current_points]

            for vtx in selections:
                vid = int(re.search(r"\[(\d+)\]", vtx).group(1))
                new_points[vid] = self.getpos_points[vid]

            with ss.snapshot_state(targets=[obj], position=True):
                nu.set_points(obj, points=new_points, space=space)

    def onGoZ(self, *args):
        mel.eval('source "C:/Users/Public/Pixologic/GoZApps/Maya/GoZBrushFromMaya.mel"')


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()