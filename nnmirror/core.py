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
import nnutil.ui as ui


def FormatOptionsupported():
    ver = int(cmds.about(version=True))
    if ver > 2018:
        return True
    else:
        return False


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
        # prefix from
        # prefix to
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
        ui.button(label='unlockTRS', c=self.onUnlockTRS)
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
        mel.eval('mirrorJoint -mirrorYZ -mirrorBehavior -searchReplace "R_" "L_";')

    def onMirrorJointY(self, *args):
        mel.eval('mirrorJoint -mirrorXZ -mirrorBehavior -searchReplace "R_" "L_";')

    def onMirrorJointZ(self, *args):
        mel.eval('mirrorJoint -mirrorXY -mirrorBehavior -searchReplace "R_" "L_";')

    def onMirrorJointOp(self, *args):
        mel.eval('MirrorJointOptions')

    def onOrientJointOp(self, *args):
        mel.eval('OrientJointOptions')

    def onJointTool(self, *args):
        mel.eval('JointTool')

    def onSetRadius(self, *args):
        nm.set_radius_auto()

    def sanitize(self, s, *args):
        # ネームスペース削除
        sanitize_name = re.sub(r'^.*\:', "", s, 1)
        # パス形式なら | より前を捨てる
        sanitize_name = re.sub(r'^.*\|', "", sanitize_name, 1)
        return sanitize_name

    def existWeightFile(self, dir, filename):
        path = dir + filename
        return os.path.exists(path)

    def onExportWeight(self, *args):
        temp_mode = ui.get_value(self.tempMode)
        selections = cmds.ls(sl=True, fl=True)

        for obj in selections:
            # meshでなければskip
            if not hasattr(pm.PyNode(obj), "getShape"):
                continue

            skincluster = mel.eval('findRelatedSkinCluster ' + obj)

            # skincluster 無ければskip
            if skincluster == "":
                continue
            
            # エクスポートするファイル名
            filename = ""

            if temp_mode:
                filename = "temp"
            else:
                filename = self.sanitize(obj)

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

    def onExportWeightOptions(self, *args):
        mel.eval('ExportDeformerWeights')

    def importWeight(self, method, *args):
        temp_mode = ui.get_value(self.tempMode)
        selections = cmds.ls(sl=True, fl=True)

        for obj in selections:
            # meshでなければskip
            if not hasattr(pm.PyNode(obj), "getShape"):
                print("skip " + obj)
                continue

            # スキンクラスター取得
            skincluster = mel.eval("findRelatedSkinCluster %(obj)s" % locals())
                        
            # インポートするファイル名
            filename = ""

            if temp_mode:
                filename = "temp.xml"
            else:
                filename = self.sanitize(obj) + ".xml"

            currentScene = cmds.file(q=True, sn=True)
            dir = re.sub(r'/scenes/.+$', '/weights/', currentScene, 1)

            # ウェイトファイルがあるオブジェクトだけ処理
            print(dir+filename)
            if self.existWeightFile(dir, filename):
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
                    cmds.skinCluster(obj, e=True, unbind=True)

                # ウェイトファイルに保存されていたインフルエンスだけで改めてバインドする
                try:
                    cmds.select(cl=True)
                    cmds.select(obj, add=True)
                    for joint in nu.list_diff(influence_list, joints_not_exist):
                        cmds.select(joint, add=True)
                    skincluster = cmds.skinCluster(tsb=True, mi=max_influence)[0]
                    
                except:
                    # TODO: バインド失敗時の処理
                    print("bind error: %(obj)s" % locals())
                    continue

                # インポート
                cmd = 'deformerWeights -import -method "%(method)s" -deformer %(skincluster)s -path "%(dir)s" "%(filename)s"' % locals()
                print(cmd)
                mel.eval(cmd)
                mel.eval("skinCluster -e -forceNormalizeWeights %(skincluster)s" % locals())

    def onImportWeightIndex(self, *args):
        method = "index"
        self.importWeight(method)

    def onImportWeightNearest(self, *args):
        method = "nearest"
        self.importWeight(method)

    def onImportWeightBarycentric(self, *args):
        method = "barycentric"
        self.importWeight(method)

    def onImportWeightBilinear(self, *args):
        method = "bilinear"
        self.importWeight(method)

    def onImportWeightOver(self, *args):
        method = "over"
        self.importWeight(method)

    def onImportWeightOptions(self, *args):
        mel.eval('ImportDeformerWeights')

    def onBindOptions(self, *args):
        mel.eval('SmoothBindSkinOptions')

    def onUnbind(self, *args):
        mel.eval('DetachSkin')

    def onUnbindOptions(self, *args):
        mel.eval('DetachSkinOptions')

    def onUnlockTRS(self, *args):
        selections = cmds.ls(selection=True, flatten=True)
        for obj in selections:
            mel.eval('CBunlockAttr "%(obj)s.tx"' % locals())
            mel.eval('CBunlockAttr "%(obj)s.ty"' % locals())
            mel.eval('CBunlockAttr "%(obj)s.tz"' % locals())
            mel.eval('CBunlockAttr "%(obj)s.rx"' % locals())
            mel.eval('CBunlockAttr "%(obj)s.ry"' % locals())
            mel.eval('CBunlockAttr "%(obj)s.rz"' % locals())
            mel.eval('CBunlockAttr "%(obj)s.sx"' % locals())
            mel.eval('CBunlockAttr "%(obj)s.sy"' % locals())
            mel.eval('CBunlockAttr "%(obj)s.sz"' % locals())

    def onCopyInfuenceList(self, *args):
        pass

    def onPastInfluenceList(self, *args):
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