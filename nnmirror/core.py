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


def FormatOptionsupported():
    """ウェイトのインポートエクスポートが format オプションに対応している場合 True を返す

    Returns:
        [type]: [description]
    """
    ver = int(cmds.about(version=True))
    if ver > 2018:
        return True
    else:
        return False


def lock_trs(obj):
    """指定したオブジェクトのトランスフォームをロックする

    Args:
        obj (Transform): トランスフォームをロックするトランスフォームノード
    """
    obj = nu.pynode(obj)
    obj.translateX.lock()
    obj.translateY.lock()
    obj.translateZ.lock()
    obj.rotateX.lock()
    obj.rotateY.lock()
    obj.rotateZ.lock()
    obj.scaleX.lock()
    obj.scaleY.lock()
    obj.scaleZ.lock()


def unlock_trs(obj):
    """指定したオブジェクトのトランスフォームをアンロックする

    Args:
        obj (Transform): トランスフォームをアンロックするトランスフォームノード
    """
    obj = nu.pynode(obj)
    obj.translateX.unlock()
    obj.translateY.unlock()
    obj.translateZ.unlock()
    obj.rotateX.unlock()
    obj.rotateY.unlock()
    obj.rotateZ.unlock()
    obj.scaleX.unlock()
    obj.scaleY.unlock()
    obj.scaleZ.unlock()


def get_basename(s):
    """ネームスペースとパスを取り除いたオブジェクト自身の名前を取得する

    Args:
        s (str): ネームスペースやパスを含んでいる可能性のあるオブジェクト名

    Returns:
        str: ネームスペースとパスを取り除いたオブジェクト自身の名前
    """
    # ネームスペース削除
    sanitize_name = re.sub(r'^.*\:', "", s, 1)
    # パス形式なら | より前を捨てる
    sanitize_name = re.sub(r'^.*\|', "", sanitize_name, 1)
    return sanitize_name


def exist_file(dir, filename):
    """ファイルが存在する場合は True を返す

    Args:
        dir (str): 存在するか調べるパス
        filename (str): 存在するか調べるファイル名

    Returns:
        bool: ファイルが存在する場合は True, 存在しない場合は False
    """
    path = dir + filename

    return os.path.exists(path)


def export_weight(objects=None, temp_mode=False, filename=None):
    """ウェイトをXMLでエクスポートする

    Args:
        objects (Transform or Mesh, optional): 対象のオブジェクト。省略時は選択オブジェクトを使用する. Defaults to None.
        temp_mode (bool, optional): True の場合オブジェクト名にかかわらず同一のファイル名を使用する. Defaults to False.
        filename (str, optional): ウェイトを書き出す際のファイル名。省略時はオブジェクト名。temp_mode よりも優先される. Defaults to None.
    """
    current_selections = pm.selected()

    if not objects:
        objects = pm.selected(flatten=True)

        if not objects:
            raise(Exception("no targets"))

    name_specified = bool(filename)

    for obj in objects:
        # meshでなければskip
        if not hasattr(pm.PyNode(obj), "getShape") and not isinstance(obj, nt.Mesh):
            continue

        skincluster = mel.eval('findRelatedSkinCluster ' + obj)

        # skincluster 無ければskip
        if skincluster == "":
            continue

        # エクスポートするファイル名
        if not name_specified:
            if temp_mode:
                filename = "temp"
            else:
                filename = get_basename(obj.name())

        currentScene = cmds.file(q=True, sn=True)
        dir = re.sub(r'/scenes/.+$', '/weights/', currentScene, 1)

        try:
            os.mkdir(dir)
        except:
            pass

        if FormatOptionsupported():
            cmd = 'deformerWeights -export -vc -deformer "%(skincluster)s" -format "XML" -path "%(dir)s" "%(filename)s.xml"' % locals()
        else:
            cmd = 'deformerWeights -export -vc -deformer %(skincluster)s -path "%(dir)s" "%(filename)s.xml"' % locals()

        try:
            mel.eval(cmd)
        except:
            print("Unable to export weights: " + obj)
            # エクスポートできないノードのスキップ
            pass

    pm.select(current_selections, replace=True)


# バインドメソッド
BM_INDEX = "index"
BM_NEAREST = "nearest"
BM_BARYCENTRIC = "barycentric"
BM_BILINEAR = "bilinear"
BM_OVER = "over"


def import_weight(objects=None, method=BM_BILINEAR, temp_mode=False, filename=None):
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

    name_specified = bool(filename)

    for obj in objects:
        # meshでなければskip
        if not hasattr(pm.PyNode(obj), "getShape") and not isinstance(obj, nt.Mesh):
            print("skip " + obj)
            continue

        # スキンクラスター取得
        skincluster = mel.eval("findRelatedSkinCluster %(obj)s" % locals())

        # インポートするファイル名の決定
        if not name_specified:
            if temp_mode:
                filename = "temp.xml"
            else:
                filename = get_basename(obj.name()) + ".xml"

        elif ".xml" not in filename:
            filename = filename + ".xml"

        currentScene = cmds.file(q=True, sn=True)
        dir = re.sub(r'/scenes/.+$', '/weights/', currentScene, 1)

        # ウェイトファイルがあるオブジェクトだけ処理
        print(dir+filename)
        if exist_file(dir, filename):
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
        unlock_trs(object)
        pm.parent(object, parent)
        lock_trs(object)
        pm.bakePartialHistory(object, ppt=True)
        nu.pynode(object).rename(name)

    elif skined_meshes:
        # スキンクラスターを持っているメッシュと持っていないメッシュが混在している場合は
        # 先に適当なメッシュのウェイトをコピーしてから polyUniteSkinned で結合する
        static_meshes = nu.list_diff(all_meshes, skined_meshes)
        weight_file_name = "combine_skined_mesh_temp"
        export_weight([skined_meshes[0]], filename=weight_file_name)

        import_weight(static_meshes, filename=weight_file_name)

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


class NN_ToolWindow(object):

    def __init__(self):
        self.window = 'NN_Mirror'
        self.title = 'NN_Mirror'
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
        ui.end_layout()

        ui.row_layout()
        ui.header()
        self.eb_prefix_from = ui.eb_text(text="L_")
        self.eb_prefix_to = ui.eb_text(text="R_")
        ui.button(label='Op', c=self.onMirrorJointOp)
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
        self.tempMode = ui.check_box(label='temporary', v=False)
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
        ui.button(label='bind Op', c=self.onBindOptions, dgc=self.onBindOptions)
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
        ui.button(label='mSkin', c=self.onEditorMskin)
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
        ui.button(label='Straighten', c=self.onAriStraightVertex)
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
        ui.header(label='Remesh')
        ui.button(label='QRemesher', c=self.onQuadRemesher)
        ui.end_layout()

    def onMirrorFaceXPosi(self, *args):
        mel.eval('polyMirrorFace  -cutMesh 1 -axis 0 -axisDirection 0 -mergeMode 1 -mergeThresholdType 1 -mergeThreshold 0.01 -mirrorAxis 1 -mirrorPosition 0 -smoothingAngle 180 -flipUVs 0 -ch 1;')

    def onMirrorFaceXNega(self, *args):
        mel.eval('polyMirrorFace  -cutMesh 1 -axis 0 -axisDirection 1 -mergeMode 1 -mergeThresholdType 1 -mergeThreshold 0.01 -mirrorAxis 1 -mirrorPosition 0 -smoothingAngle 180 -flipUVs 0 -ch 1;')

    def onMirrorFaceYPosi(self, *args):
        mel.eval('polyMirrorFace  -cutMesh 1 -axis 1 -axisDirection 0 -mergeMode 1 -mergeThresholdType 1 -mergeThreshold 0.01 -mirrorAxis 1 -mirrorPosition 0 -smoothingAngle 180 -flipUVs 0 -ch 1;')

    def onMirrorFaceYNega(self, *args):
        mel.eval('polyMirrorFace  -cutMesh 1 -axis 1 -axisDirection 1 -mergeMode 1 -mergeThresholdType 1 -mergeThreshold 0.01 -mirrorAxis 1 -mirrorPosition 0 -smoothingAngle 180 -flipUVs 0 -ch 1;')

    def onMirrorFaceZPosi(self, *args):
        mel.eval('polyMirrorFace  -cutMesh 1 -axis 2 -axisDirection 0 -mergeMode 1 -mergeThresholdType 1 -mergeThreshold 0.01 -mirrorAxis 1 -mirrorPosition 0 -smoothingAngle 180 -flipUVs 0 -ch 1;')

    def onMirrorFaceZNega(self, *args):
        mel.eval('polyMirrorFace  -cutMesh 1 -axis 2 -axisDirection 1 -mergeMode 1 -mergeThresholdType 1 -mergeThreshold 0.01 -mirrorAxis 1 -mirrorPosition 0 -smoothingAngle 180 -flipUVs 0 -ch 1;')

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
        mel.eval('polyMirrorFace  -cutMesh 1 -axis 0 -axisDirection 1 -mergeMode 0 -mergeThresholdType 1 -mergeThreshold 0.01 -mirrorAxis 1 -mirrorPosition 0 -smoothingAngle 180 -flipUVs 0 -ch 1 ;')

    def onCutGeoXNega(self, *args):
        mel.eval('polyMirrorFace  -cutMesh 1 -axis 0 -axisDirection 1 -mergeMode 0 -mergeThresholdType 1 -mergeThreshold 0.01 -mirrorAxis 1 -mirrorPosition 0 -smoothingAngle 180 -flipUVs 0 -ch 1 ;')

    def onCutGeoYPosi(self, *args):
        mel.eval('polyMirrorFace  -cutMesh 1 -axis 1 -axisDirection 1 -mergeMode 0 -mergeThresholdType 1 -mergeThreshold 0.01 -mirrorAxis 1 -mirrorPosition 0 -smoothingAngle 180 -flipUVs 0 -ch 1 ;')

    def onCutGeoYNega(self, *args):
        mel.eval('polyMirrorFace  -cutMesh 1 -axis 1 -axisDirection 1 -mergeMode 0 -mergeThresholdType 1 -mergeThreshold 0.01 -mirrorAxis 1 -mirrorPosition 0 -smoothingAngle 180 -flipUVs 0 -ch 1 ;')

    def onCutGeoZPosi(self, *args):
        mel.eval('polyMirrorFace  -cutMesh 1 -axis 2 -axisDirection 1 -mergeMode 0 -mergeThresholdType 1 -mergeThreshold 0.01 -mirrorAxis 1 -mirrorPosition 0 -smoothingAngle 180 -flipUVs 0 -ch 1 ;')

    def onCutGeoZNega(self, *args):
        mel.eval('polyMirrorFace  -cutMesh 1 -axis 2 -axisDirection 1 -mergeMode 0 -mergeThresholdType 1 -mergeThreshold 0.01 -mirrorAxis 1 -mirrorPosition 0 -smoothingAngle 180 -flipUVs 0 -ch 1 ;')

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
        temp_mode = ui.get_value(self.tempMode)
        export_weight(temp_mode=temp_mode)

    def onExportWeightOptions(self, *args):
        mel.eval('ExportDeformerWeights')

    def onImportWeightIndex(self, *args):
        temp_mode = ui.get_value(self.tempMode)
        method = BM_INDEX
        import_weight(temp_mode=temp_mode, method=method)

    def onImportWeightNearest(self, *args):
        temp_mode = ui.get_value(self.tempMode)
        method = BM_NEAREST
        import_weight(temp_mode=temp_mode, method=method)

    def onImportWeightBarycentric(self, *args):
        temp_mode = ui.get_value(self.tempMode)
        method = BM_BARYCENTRIC
        import_weight(temp_mode=temp_mode, method=method)

    def onImportWeightBilinear(self, *args):
        temp_mode = ui.get_value(self.tempMode)
        method = BM_BILINEAR
        import_weight(temp_mode=temp_mode, method=method)

    def onImportWeightOver(self, *args):
        temp_mode = ui.get_value(self.tempMode)
        method = BM_OVER
        import_weight(temp_mode=temp_mode, method=method)

    def onImportWeightOptions(self, *args):
        mel.eval('ImportDeformerWeights')

    def onBindOptions(self, *args):
        mel.eval('SmoothBindSkinOptions')

    def onUnbind(self, *args):
        mel.eval('DetachSkin')

    def onUnbindOptions(self, *args):
        mel.eval('DetachSkinOptions')

    def onUnlockTRS(self, *args):
        for obj in pm.selected(flatten=True):
            unlock_trs(obj)

    def onLockTRS(self, *args):
        for obj in pm.selected(flatten=True):
            lock_trs(obj)

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

    def onEditorMskin(self, *args):
        import SkyTools.rigging.mSkin as sw
        sw.show()

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


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()