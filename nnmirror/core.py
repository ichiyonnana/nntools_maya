#! python
# coding:utf-8

# ダイアログのテンプレ
# self.window だけユニークならあとはそのままで良い
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


def FormatOptionsupported():
    ver = int(cmds.about(version=True))
    if ver > 2018:
        return True
    else:
        return False


window_width = 300
header_width = 50
color_x = (1.0, 0.5, 0.5)
color_y = (0.5, 1.0, 0.5)
color_z = (0.5, 0.5, 1.0)
color_joint = (0.5, 1.0, 0.75)
color_select = (0.5, 0.75, 1.0)
bw_single = 24
bw_double = bw_single*2 + 2


class NN_ToolWindow(object):

    def __init__(self):
        self.window = 'NN_Mirror'
        self.title = 'NN_Mirror'
        self.size = (window_width, 95)

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
        self.columnLayout = cmds.columnLayout()

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=16)
        self.label1 = cmds.text(label='Geo', width=header_width)
        self.buttonA = cmds.button(l='X+', c=self.onMirrorFaceXPosi, dgc=self.onCutGeoXPosi, bgc=color_x, width=bw_single)
        self.buttonA = cmds.button(l='X-', c=self.onMirrorFaceXNega, dgc=self.onCutGeoXNega, bgc=color_x, width=bw_single)
        self.buttonA = cmds.button(l='Y+', c=self.onMirrorFaceYPosi, dgc=self.onCutGeoYPosi, bgc=color_y, width=bw_single)
        self.buttonA = cmds.button(l='Y-', c=self.onMirrorFaceYNega, dgc=self.onCutGeoYNega, bgc=color_y, width=bw_single)
        self.buttonA = cmds.button(l='Z+', c=self.onMirrorFaceZPosi, dgc=self.onCutGeoZPosi, bgc=color_z, width=bw_single)
        self.buttonA = cmds.button(l='Z-', c=self.onMirrorFaceZNega, dgc=self.onCutGeoZNega, bgc=color_z, width=bw_single)
        self.buttonA = cmds.button(l='Op', c=self.onMirrorFaceOp)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=16)
        self.label1 = cmds.text(label='Set 0', width=header_width)
        self.buttonA = cmds.button(l='X = ', c=self.onSetZeroX, bgc=color_x, width=bw_single)
        self.buttonA = cmds.button(l='Y = ', c=self.onSetZeroY, bgc=color_y, width=bw_single)
        self.buttonA = cmds.button(l='Z = ', c=self.onSetZeroZ, bgc=color_z, width=bw_single)
        self.coord_value = cmds.floatField(v=0, width=bw_double)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=16)
        self.label1 = cmds.text(label='Flip', width=header_width)
        self.buttonA = cmds.button(l='X', c=self.onFlipX, bgc=color_x, width=bw_double)
        self.buttonA = cmds.button(l='Y', c=self.onFlipY, bgc=color_y, width=bw_double)
        self.buttonA = cmds.button(l='Z', c=self.onFlipZ, bgc=color_z, width=bw_double)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text(label='Weight', width=header_width)
        self.buttonA = cmds.button(l='X+', c=self.onMirrorWeightXPosi, bgc=color_x, width=bw_single)
        self.buttonA = cmds.button(l='X-', c=self.onMirrorWeightXNega, bgc=color_x, width=bw_single)
        self.buttonA = cmds.button(l='Y+', c=self.onMirrorWeightYPosi, bgc=color_y, width=bw_single)
        self.buttonA = cmds.button(l='Y-', c=self.onMirrorWeightYNega, bgc=color_y, width=bw_single)
        self.buttonA = cmds.button(l='Z+', c=self.onMirrorWeightZPosi, bgc=color_z, width=bw_single)
        self.buttonA = cmds.button(l='Z-', c=self.onMirrorWeightZNega, bgc=color_z, width=bw_single)
        self.buttonA = cmds.button(l='Op', c=self.onMirrorWeightOp)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text(label='Joint', width=header_width)
        self.buttonA = cmds.button(l='X', c=self.onMirrorJointX, bgc=color_x, width=bw_double)
        self.buttonA = cmds.button(l='Y', c=self.onMirrorJointY, bgc=color_y, width=bw_double)
        self.buttonA = cmds.button(l='Z', c=self.onMirrorJointZ, bgc=color_z, width=bw_double)
        #prefix from
        #prefix to
        self.buttonA = cmds.button(l='Op', c=self.onMirrorJointOp)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text(label='', width=header_width)
        self.buttonA = cmds.button(l='OrientOp', c=self.onOrientJointOp)
        self.buttonA = cmds.button(l='JointTool', c=self.onJointTool, bgc=color_joint, width=bw_double)
        self.buttonA = cmds.button(l='SetRadius', c=self.onSetRadius, width=bw_double)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text(label='weight', width=header_width)
        self.buttonA = cmds.button(l='export', c=self.onExportWeight, dgc=self.onExportWeightOptions)
        self.tempMode = cmds.checkBox(l='temporary', v=False)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text(label='', width=header_width)
        self.buttonA = cmds.button(l='index', c=self.onImportWeightIndex, dgc=self.onImportWeightOptions)
        self.buttonA = cmds.button(l='nearest', c=self.onImportWeightNearest, dgc=self.onImportWeightOptions)
        #self.buttonA = cmds.button(l='barycentric', c=self.onImportWeightBarycentric, dgc=self.onImportWeightOptions)
        self.buttonA = cmds.button(l='bilinear', c=self.onImportWeightBilinear, dgc=self.onImportWeightOptions)
        self.buttonA = cmds.button(l='over', c=self.onImportWeightOver, dgc=self.onImportWeightOptions)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text(label='bind', width=header_width)
        self.buttonA = cmds.button(l='bind Op', c=self.onBindOptions, dgc=self.onBindOptions)
        self.buttonA = cmds.button(l='unbind', c=self.onUnbind, dgc=self.onUnbindOptions)
        self.buttonA = cmds.button(l='unlockTRS', c=self.onUnlockTRS)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text(label='Anim', width=header_width)
        self.buttonA = cmds.button(l='export', c=self.onExportAnim)
        self.buttonA = cmds.button(l='import', c=self.onImportAnim)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text(label='Editor', width=header_width)
        self.buttonA = cmds.button(l='SIWE', c=self.onEditorSIWE)
        self.buttonA = cmds.button(l='mSkin', c=self.onEditorMskin)
        self.buttonA = cmds.button(l='copyWeightOp', c=self.onCopyWeightOp)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text(label='AriTools', width=header_width)
        self.buttonA = cmds.button(l='Symm', c=self.onAriSymmetryChecker)
        self.buttonA = cmds.button(l='Circle', c=self.onAriCircleVertex)
        self.buttonA = cmds.button(l='SelectEdge', c=self.onAriSelectEdgeLoopRing)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text(label='', width=header_width)
        self.buttonA = cmds.button(l='Straighten', c=self.onAriStraightVertex)
        self.buttonA = cmds.button(l='SplitPolygon', c=self.onAriSplitPolygon)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text(label='NnTools', width=header_width)
        self.buttonA = cmds.button(l='EdgeRing', c=self.onNnEdgeLength)
        self.buttonA = cmds.button(l='Curve', c=self.onNnCurve)
        self.buttonA = cmds.button(l='Straighten', c=self.onNnStraighten)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text(label='Remesh', width=header_width)
        self.buttonA = cmds.button(l='QRemesher', c=self.onQuadRemesher)
        cmds.setParent("..")

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
        v = cmds.floatField(self.coord_value, q=True, v=True)
        nm.set_coord('x', v)

    def onSetZeroY(self, *args):
        v = cmds.floatField(self.coord_value, q=True, v=True)
        nm.set_coord('y', v)

    def onSetZeroZ(self, *args):
        v = cmds.floatField(self.coord_value, q=True, v=True)
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
        temp_mode = cmds.checkBox(self.tempMode, q=True, v=True)
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
        temp_mode = cmds.checkBox(self.tempMode, q=True, v=True)
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
                    #TODO: バインド失敗時の処理
                    print("bind error: %(obj)s" % locals() )
                    continue

                # インポート
                cmd = 'deformerWeights -import -method "%(method)s" -deformer %(skincluster)s -path "%(dir)s" "%(filename)s"' % locals()
                print(cmd)
                mel.eval(cmd)
                mel.eval("skinCluster -e -forceNormalizeWeights %(skincluster)s" % locals() )

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
        mel.eval('ExportAnim')

    def onImportAnim(self, *args):
        mel.eval('ImportAnim')

    def onEditorSIWE(self, *args):
        import siweighteditor.siweighteditor
        siweighteditor.siweighteditor.Option()

    def onEditorMskin(self, *args):
        import SkyTools.rigging.mSkin as sw
        reload(sw)
        mSkinWindow = sw.show()

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
        qr = QuadRemesher.QuadRemesher()


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()