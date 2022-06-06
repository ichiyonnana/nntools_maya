#! python
# coding:utf-8
import re
import os
import sys
import traceback

import pymel.core as pm
import pymel.core.nodetypes as nt
import pymel.core.datatypes as dt
import maya.cmds as cmds
import maya.mel as mel

import nnutil.core as nu
import nnutil.misc as nm
import nnutil.display as nd
import nnutil.ui as ui

window_name = "NN_Mirror"
window = None


def get_window():
    return window


def mirror_objects(objects=None, axis=0, direction=1, cut=False):
    if cut:
        merge_mode = 0
    else:
        merge_mode = 1

    objects = pm.selected(flatten=True)

    if isinstance(objects[0], (nt.Mesh, nt.Transform)):
        # オブジェクト
        for obj in objects:
            if obj.getShape():
                pm.polyMirrorFace(obj, cutMesh=1, axis=axis, axisDirection=direction, mergeMode=merge_mode, mergeThresholdType=1, mergeThreshold=0.01, mirrorAxis=1, mirrorPosition=0, smoothingAngle=180, flipUVs=0, ch=1)
                pm.bakePartialHistory(obj, ppt=True)
    else:
        # コンポーネント
        pm.polyMirrorFace(cutMesh=1, axis=axis, axisDirection=direction, mergeMode=merge_mode, mergeThresholdType=1, mergeThreshold=0.01, mirrorAxis=1, mirrorPosition=0, smoothingAngle=180, flipUVs=0, ch=1)


def export_weight(objects=None, specified_name=None):
    """ウェイトをXMLでエクスポートする

    Args:
        objects (Transform or Mesh, optional): 対象のオブジェクト。省略時は選択オブジェクトを使用する. Defaults to None.
        temp_mode (bool, optional): True の場合オブジェクト名にかかわらず同一のファイル名を使用する. Defaults to False.
        specified_name (str, optional): ウェイトを書き出す際のファイル名。省略時はオブジェクト名。 Defaults to None.
    """
    # 選択復帰用
    current_selections = pm.selected()

    # オブジェクト未指定時は選択オブジェクトを使用する
    if not objects:
        objects = pm.selected(flatten=True)

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
        if not hasattr(pm.PyNode(obj), "getShape") and not isinstance(obj, nt.Mesh):
            continue

        skincluster = mel.eval('findRelatedSkinCluster ' + obj)

        # skincluster 無ければskip
        if skincluster == "":
            continue

        # エクスポートするファイル名の決定
        filename = ""

        if specified_name is None:
            filename = nu.get_basename(obj.name())

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
    pm.select(current_selections, replace=True)


# バインドメソッド
BM_INDEX = "index"
BM_NEAREST = "nearest"
BM_BARYCENTRIC = "barycentric"
BM_BILINEAR = "bilinear"
BM_OVER = "over"


def import_weight(objects=None, method=BM_BILINEAR, specified_name=None):
    """ウェイトをXMLからインポートする

    Args:
        objects (Transform or Mesh, optional): 対象のオブジェクト。省略時は選択オブジェクトを使用する. Defaults to None.
        method (str, optional): バインドメソッド. Defaults to BM_BILINEAR.
        temp_mode (bool, optional): True の場合オブジェクト名にかかわらず同一のファイル名を使用する. Defaults to False.
        filename (str, optional): ウェイトを読み込む際のファイル名。省略時はオブジェクト名。temp_mode よりも優先される. Defaults to None.
    """
    current_selections = pm.selected()

    if not objects:
        objects = pm.selected(flatten=True)

        if not objects:
            raise(Exception("no targets"))

    elif not isinstance(objects, list):
        raise(Exception())

    currentScene = cmds.file(q=True, sn=True)
    dir = re.sub(r'/scenes/.+$', '/weights/', currentScene, 1)

    for obj in objects:
        # meshでなければskip
        if not hasattr(pm.PyNode(obj), "getShape") and not isinstance(obj, nt.Mesh):
            print("skip " + obj)
            continue

        # スキンクラスター取得
        skincluster = mel.eval("findRelatedSkinCluster %(obj)s" % locals())

        # インポートするファイル名の決定
        filename = ""

        if specified_name is None:
            filename = nu.get_basename(obj.name()) + ".xml"

        else:
            if ".xml" in specified_name:
                filename = specified_name
            else:
                filename = specified_name + ".xml"

        # ウェイトファイルがあるオブジェクトだけ処理
        print(dir+filename)
        if nu.exist_file(dir, filename):
            # ウェイトファイル直接開いてインフルエンスリスト取得
            influence_list = []
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
                if not mel.eval('objExists %(joint)s' % locals()):
                    joints_not_exist.append(joint)

            if len(joints_not_exist) != 0:
                print("The following joints do not exist in the scene:")
                print(joints_not_exist)

            # バインド済なら一度アンバインドする
            skincluster = mel.eval("findRelatedSkinCluster %(obj)s" % locals())
            if skincluster != "":
                mel.eval('gotoBindPose')
                pm.skinCluster(obj, e=True, unbind=True)

            # ウェイトファイルに保存されていたインフルエンスだけで改めてバインドする
            try:
                pm.select(cl=True)
                pm.select(obj, add=True)
                for joint in nu.list_diff(influence_list, joints_not_exist):
                    pm.select(joint, add=True)
                skincluster = pm.skinCluster(tsb=True, mi=max_influence)

            except:
                print("bind error: " + obj.name())

            # インポート
            cmd = 'deformerWeights -import -method "%(method)s" -deformer %(skincluster)s -path "%(dir)s" "%(filename)s"' % locals()
            print(cmd)
            mel.eval(cmd)
            mel.eval("skinCluster -e -forceNormalizeWeights %s" % skincluster)

    pm.select(current_selections, replace=True)


def combine_skined_mesh(objects=None):
    """指定したオブジェクトをウェイトを維持して結合する。

    バインド済みのメッシュとそうでないメッシュが混在していた場合はすべてバインド済みにした上で結合する。

    Args:
        objects (list[Mesh or Transform], optional): 結合対象のオブジェクト. Defaults to None.
    """
    if not objects:
        objects = pm.selected(flatten=True)

        if not objects:
            raise(Exception())

    elif not isinstance(objects, list):
        raise(Exception())

    all_meshes = []

    for obj in objects:
        meshes = [x for x in pm.listRelatives(obj, allDescendents=True, noIntermediate=True) if isinstance(x, nt.Mesh)]
        all_meshes.extend(meshes)

    skined_meshes = []

    for mesh in all_meshes:
        if [x for x in mesh.connections() if isinstance(x, nt.SkinCluster)]:
            skined_meshes.append(mesh)

    name = objects[-1].name()
    parent = objects[-1].getParent()

    if len(all_meshes) == len(skined_meshes):
        # すべてのメッシュがスキンクラスターを持っていれば polyUniteSkinned で結合する
        object, node = pm.polyUniteSkinned(all_meshes, ch=1, mergeUVSets=1, objectPivot=True)
        nu.unlock_trs(object)
        pm.parent(object, parent)
        nu.lock_trs(object)
        pm.bakePartialHistory(object, ppt=True)
        nu.pynode(object).rename(name)

    elif skined_meshes:
        # スキンクラスターを持っているメッシュと持っていないメッシュが混在している場合は
        # 先に適当なメッシュのウェイトをコピーしてから polyUniteSkinned で結合する
        static_meshes = nu.list_diff(all_meshes, skined_meshes)
        weight_file_name = "combine_skined_mesh_temp"
        export_weight([skined_meshes[0]], specified_name=weight_file_name)

        import_weight(static_meshes, specified_name=weight_file_name)

        object, node = pm.polyUniteSkinned(all_meshes, ch=1, mergeUVSets=1, objectPivot=True)
        pm.parent(object, parent)
        pm.bakePartialHistory(object, ppt=True)
        nu.pynode(object).rename(name)

    else:
        # すべてが静的なメッシュなら polyUnite で結合する
        object, node = pm.polyUnite(all_meshes, ch=1, mergeUVSets=1, objectPivot=True)
        pm.parent(object, parent)
        pm.bakePartialHistory(object, ppt=True)
        nu.pynode(object).rename(name)


def duplicate_mesh(extract=False):
    selected_faces = pm.selected(flatten=True)
    object = pm.polyListComponentConversion(selected_faces[0])
    object2 = pm.duplicate(object)

    pm.select(object2)
    pm.selectMode(component=True)
    mel.eval("invertSelection")
    pm.delete()

    if extract:
        pm.delete(selected_faces)


class NN_ToolWindow(object):

    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (300, 95)

    def create(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)
        self.window = cmds.window(
            self.window,
            t=self.title,
            widthHeight=self.size
        )
        self.layout()
        cmds.showWindow()

    def layout(self):
        ui.column_layout()

        ui.row_layout()
        ui.header(label='Geo')
        ui.button(label='X+', c=self.onMirrorFaceXPosi, dgc=self.onCutGeoXPosi, bgc=ui.color_x)
        ui.button(label='X-', c=self.onMirrorFaceXNega, dgc=self.onCutGeoXNega, bgc=ui.color_x)
        ui.button(label='Y+', c=self.onMirrorFaceYPosi, dgc=self.onCutGeoYPosi, bgc=ui.color_y)
        ui.button(label='Y-', c=self.onMirrorFaceYNega, dgc=self.onCutGeoYNega, bgc=ui.color_y)
        ui.button(label='Z+', c=self.onMirrorFaceZPosi, dgc=self.onCutGeoZPosi, bgc=ui.color_z)
        ui.button(label='Z-', c=self.onMirrorFaceZNega, dgc=self.onCutGeoZNega, bgc=ui.color_z)
        ui.button(label='Op', c=self.onMirrorFaceOp)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='Set')
        ui.button(label='X = ', c=self.onSetZeroX, bgc=ui.color_x, width=ui.width1)
        ui.button(label='Y = ', c=self.onSetZeroY, bgc=ui.color_y, width=ui.width1)
        ui.button(label='Z = ', c=self.onSetZeroZ, bgc=ui.color_z, width=ui.width1)
        self.coord_value = ui.eb_float(v=0, width=ui.width2)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='Flip')
        ui.button(label='X', c=self.onFlipX, bgc=ui.color_x, width=ui.width2)
        ui.button(label='Y', c=self.onFlipY, bgc=ui.color_y, width=ui.width2)
        ui.button(label='Z', c=self.onFlipZ, bgc=ui.color_z, width=ui.width2)
        ui.end_layout()

        ui.separator()

        ui.row_layout()
        ui.header(label='Weight')
        ui.button(label='X+', c=self.onMirrorWeightXPosi, bgc=ui.color_x)
        ui.button(label='X-', c=self.onMirrorWeightXNega, bgc=ui.color_x)
        ui.button(label='Y+', c=self.onMirrorWeightYPosi, bgc=ui.color_y)
        ui.button(label='Y-', c=self.onMirrorWeightYNega, bgc=ui.color_y)
        ui.button(label='Z+', c=self.onMirrorWeightZPosi, bgc=ui.color_z)
        ui.button(label='Z-', c=self.onMirrorWeightZNega, bgc=ui.color_z)
        ui.button(label='Op', c=self.onMirrorWeightOp)
        ui.end_layout()

        ui.separator()

        ui.row_layout()
        ui.header(label='Joint')
        ui.button(label='X', c=self.onMirrorJointX, bgc=ui.color_x, width=ui.width2)
        ui.button(label='Y', c=self.onMirrorJointY, bgc=ui.color_y, width=ui.width2)
        ui.button(label='Z', c=self.onMirrorJointZ, bgc=ui.color_z, width=ui.width2)
        ui.button(label='Op', c=self.onMirrorJointOp)
        ui.end_layout()

        ui.row_layout()
        ui.header()
        self.eb_prefix_from = ui.eb_text(text="L_")
        self.eb_prefix_to = ui.eb_text(text="R_")
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='OrientOp', c=self.onOrientJointOp)
        ui.button(label='JointTool', c=self.onJointTool, bgc=ui.color_joint, width=ui.width2)
        ui.button(label='SetRadius', c=self.onSetRadius, width=ui.width2)
        ui.end_layout()

        ui.separator()

        ui.row_layout()
        ui.header(label='weight')
        ui.button(label='export', c=self.onExportWeight, dgc=self.onExportWeightOptions)
        self.cb_specify_name = ui.check_box(label='specify name', v=False)
        self.eb_tempname = ui.eb_text(text="temp", width=ui.width(3))
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='index', c=self.onImportWeightIndex, dgc=self.onImportWeightOptions)
        ui.button(label='nearest', c=self.onImportWeightNearest, dgc=self.onImportWeightOptions)
        # ui.button(label='barycentric', c=self.onImportWeightBarycentric, dgc=self.onImportWeightOptions)
        ui.button(label='bilinear', c=self.onImportWeightBilinear, dgc=self.onImportWeightOptions)
        ui.button(label='over', c=self.onImportWeightOver, dgc=self.onImportWeightOptions)
        ui.end_layout()

        ui.separator()

        ui.row_layout()
        ui.header(label='bind')
        ui.button(label='bind Op', c=self.onBindOptions, dgc=self.onBind)
        ui.button(label='unbind', c=self.onUnbind, dgc=self.onUnbindOptions)
        ui.button(label='unlockTRS [lock]', c=self.onUnlockTRS, dgc=self.onLockTRS)
        ui.end_layout()

        ui.separator()

        ui.row_layout()
        ui.header(label='combine')
        ui.button(label='combine', c=self.onCombine)
        ui.button(label='combine Op', c=self.onCombineOptions)
        ui.end_layout()

        ui.separator()

        ui.row_layout()
        ui.header(label='Anim')
        ui.button(label='export', c=self.onExportAnim)
        ui.button(label='import', c=self.onImportAnim)
        ui.end_layout()

        ui.separator()

        ui.row_layout()
        ui.header(label='Editor')
        ui.button(label='SIWE', c=self.onEditorSIWE)
        ui.button(label='copyWeightOp', c=self.onCopyWeightOp)
        ui.end_layout()

        ui.separator()

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

        ui.separator()

        ui.row_layout()
        ui.header(label='NnTools')
        ui.button(label='EdgeRing', c=self.onNnEdgeLength)
        ui.button(label='Curve', c=self.onNnCurve)
        ui.button(label='Straighten', c=self.onNnStraighten)
        ui.end_layout()

        ui.separator()

        ui.row_layout()
        ui.header(label='Mesh')
        ui.button(label='Extract', c=self.onExtract)
        ui.button(label='Duplicate', c=self.onDuplicate)
        ui.button(label='QRemesher', c=self.onQuadRemesher)
        ui.end_layout()

        ui.separator()

        ui.row_layout()
        ui.header(label='Etc')
        ui.button(label='Get Pos', c=self.onGetPos)
        ui.button(label='Set Pos', c=self.onSetPos)
        ui.end_layout()

    def onMirrorFaceXPosi(self, *args):
        mirror_objects(axis=0, direction=0, cut=False)

    def onMirrorFaceXNega(self, *args):
        mirror_objects(axis=0, direction=1, cut=False)

    def onMirrorFaceYPosi(self, *args):
        mirror_objects(axis=1, direction=0, cut=False)

    def onMirrorFaceYNega(self, *args):
        mirror_objects(axis=1, direction=1, cut=False)

    def onMirrorFaceZPosi(self, *args):
        mirror_objects(axis=2, direction=0, cut=False)

    def onMirrorFaceZNega(self, *args):
        mirror_objects(axis=2, direction=1, cut=False)

    def onMirrorFaceOp(self, *args):
        mel.eval('MirrorPolygonGeometryOptions')

    def onSetZeroX(self, *args):
        v = ui.get_value(self.coord_value)
        nm.set_coord('x', v)

    def onSetZeroY(self, *args):
        v = ui.get_value(self.coord_value)
        nm.set_coord('y', v)

    def onSetZeroZ(self, *args):
        v = ui.get_value(self.coord_value)
        nm.set_coord('z', v)

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

    def onMirrorWeightXPosi(self, *args):
        mel.eval('copySkinWeights -ss  -ds  -mirrorMode YZ -mirrorInverse -surfaceAssociation closestPoint -influenceAssociation closestJoint;')

    def onMirrorWeightXNega(self, *args):
        mel.eval('copySkinWeights -ss  -ds  -mirrorMode YZ -surfaceAssociation closestPoint -influenceAssociation closestJoint;')

    def onMirrorWeightYPosi(self, *args):
        mel.eval('copySkinWeights -ss  -ds  -mirrorMode XZ -mirrorInverse -surfaceAssociation closestPoint -influenceAssociation closestJoint;')

    def onMirrorWeightYNega(self, *args):
        mel.eval('copySkinWeights -ss  -ds  -mirrorMode XZ -surfaceAssociation closestPoint -influenceAssociation closestJoint;')

    def onMirrorWeightZPosi(self, *args):
        mel.eval('copySkinWeights -ss  -ds  -mirrorMode XY -mirrorInverse -surfaceAssociation closestPoint -influenceAssociation closestJoint;')

    def onMirrorWeightZNega(self, *args):
        mel.eval('copySkinWeights -ss  -ds  -mirrorMode XY -surfaceAssociation closestPoint -influenceAssociation closestJoint;')

    def onMirrorWeightOp(self, *args):
        mel.eval('MirrorSkinWeightsOptions')

    def onMirrorJointX(self, *args):
        prefix_from = ui.get_value(self.eb_prefix_from)
        prefix_to = ui.get_value(self.eb_prefix_to)
        mel.eval('mirrorJoint -mirrorYZ -mirrorBehavior -searchReplace "%s" "%s";' % (prefix_from, prefix_to))

    def onMirrorJointY(self, *args):
        prefix_from = ui.get_value(self.eb_prefix_from)
        prefix_to = ui.get_value(self.eb_prefix_to)
        mel.eval('mirrorJoint -mirrorXZ -mirrorBehavior -searchReplace "%s" "%s";' % (prefix_from, prefix_to))

    def onMirrorJointZ(self, *args):
        prefix_from = ui.get_value(self.eb_prefix_from)
        prefix_to = ui.get_value(self.eb_prefix_to)
        mel.eval('mirrorJoint -mirrorXY -mirrorBehavior -searchReplace "%s" "%s";' % (prefix_from, prefix_to))

    def onMirrorJointOp(self, *args):
        mel.eval('MirrorJointOptions')

    def onOrientJointOp(self, *args):
        mel.eval('OrientJointOptions')

    def onJointTool(self, *args):
        mel.eval('JointTool')

    def onSetRadius(self, *args):
        nm.set_radius_auto()

    def onExportWeight(self, *args):
        is_specify_name = ui.get_value(self.cb_specify_name)
        filename = ui.get_value(self.eb_tempname)

        if is_specify_name:
            export_weight(specified_name=filename)
        else:
            export_weight()

    def onExportWeightOptions(self, *args):
        mel.eval('ExportDeformerWeights')

    def onImportWeightIndex(self, *args):
        is_specify_name = ui.get_value(self.cb_specify_name)
        filename = ui.get_value(self.eb_tempname)
        method = BM_INDEX

        if is_specify_name:
            import_weight(specified_name=filename, method=method)
        else:
            import_weight(method=method)

    def onImportWeightNearest(self, *args):
        is_specify_name = ui.get_value(self.cb_specify_name)
        filename = ui.get_value(self.eb_tempname)
        method = BM_NEAREST

        if is_specify_name:
            import_weight(specified_name=filename, method=method)
        else:
            import_weight(method=method)

    def onImportWeightBarycentric(self, *args):
        is_specify_name = ui.get_value(self.cb_specify_name)
        filename = ui.get_value(self.eb_tempname)
        method = BM_BARYCENTRIC

        if is_specify_name:
            import_weight(specified_name=filename, method=method)
        else:
            import_weight(method=method)

    def onImportWeightBilinear(self, *args):
        is_specify_name = ui.get_value(self.cb_specify_name)
        filename = ui.get_value(self.eb_tempname)
        method = BM_BILINEAR

        if is_specify_name:
            import_weight(specified_name=filename, method=method)
        else:
            import_weight(method=method)

    def onImportWeightOver(self, *args):
        is_specify_name = ui.get_value(self.cb_specify_name)
        filename = ui.get_value(self.eb_tempname)
        method = BM_OVER

        if is_specify_name:
            import_weight(specified_name=filename, method=method)
        else:
            import_weight(method=method)

    def onImportWeightOptions(self, *args):
        mel.eval('ImportDeformerWeights')

    def onBindOptions(self, *args):
        mel.eval('SmoothBindSkinOptions')

    def onBind(self, *args):
        pm.skinCluster()

    def onUnbind(self, *args):
        mel.eval('DetachSkin')

    def onUnbindOptions(self, *args):
        mel.eval('DetachSkinOptions')

    def onUnlockTRS(self, *args):
        for obj in pm.selected(flatten=True):
            nu.unlock_trs(obj)

    def onLockTRS(self, *args):
        for obj in pm.selected(flatten=True):
            nu.lock_trs(obj)

    def onCombine(self, *args):
        combine_skined_mesh()

    def onCombineOptions(self, *args):
        mel.eval("CombinePolygonsOptions")

    def onCopyInfuenceList(self, *args):
        pass

    def onPasteInfluenceList(self, *args):
        influence_list = []
        for joint in influence_list:
            try:
                cmds.skinCluster(skincluster, e=True, dr=4, ai=joint)
            except:
                # TODO: 既にインフルエンスが存在した場合のエラー処理
                pass
        pass

    def onExportAnim(self, *args):
        if 2019 <= int(pm.about(version=True)):
            mel.eval('ExportAnim')
        else:
            mel.eval('ExportAnimOptions')

    def onImportAnim(self, *args):
        if 2019 <= int(pm.about(version=True)):
            mel.eval('ImportAnim')
        else:
            mel.eval('ImportAnimOptions')

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

    def onNnEdgeLength(self, *args):
        import align_edgering_length
        align_edgering_length.main()

    def onNnCurve(self, *args):
        import nncurve
        nncurve.main()

    def onNnStraighten(self, *args):
        import nnstraighten
        nnstraighten.main()

    def onQuadRemesher(self, *args):
        import QuadRemesher
        QuadRemesher.QuadRemesher()

    def onExtract(self, *args):
        duplicate_mesh(extract=True)

    def onDuplicate(self, *args):
        duplicate_mesh()

    def onGetPos(self, *args):
        obj = pm.selected(flatten=True)[0]

        if ui.is_shift():
            self.getpos_points = nu.get_points(obj, space=om.MSpace.kWorld)
            nd.message("copy points (world space)")

        else:
            self.getpos_points = nu.get_points(obj, space=om.MSpace.kObject)
            nd.message("copy points (object space)")

    def onSetPos(self, *args):
        obj = pm.selected(flatten=True)[0]

        if ui.is_shift():
            nu.set_points(obj, points=self.getpos_points, space=om.MSpace.kWorld)
            nd.message("paste points (world space)")

        else:
            nu.set_points(obj, points=self.getpos_points, space=om.MSpace.kObject)
            nd.message("paste points (object space)")


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()