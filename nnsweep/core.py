#! python
# coding:utf-8
"""
sweepMesh 補助モジュール
"""
import maya.cmds as cmds
import pymel.core as pm

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import nnutil.display as nd
import pymel.core.nodetypes as nt


window_name = "NN_Sweep"


def get_all_sweep_meshes(shape=True):
    """全てのスイープメッシュを取得する"""
    meshes = cmds.ls(type="mesh")

    sweep_meshes = []

    for mesh in meshes:
        connections = cmds.listConnections(mesh, destination=True, type="sweepMeshCreator")

        if connections:
            if shape:
                sweep_meshes.append(mesh)
            else:
                trs = cmds.listRelatives(mesh, parent=True)[0]
                sweep_meshes.append(trs)

    return sweep_meshes


def get_objects_in_herarchy(type=None):
    """選択されているオブジェクト以下のすべてのオブジェクトを返す"""
    selections = cmds.ls(selection=True)
    objects = []

    for sel in selections:
        if type:
            descendent_objects = cmds.listRelatives(sel, allDescendents=True, type=type)

        else:
            descendent_objects = cmds.listRelatives(sel, allDescendents=True)

        if descendent_objects:
            objects.extend(descendent_objects)

    objects = list(set(objects))

    return objects


def get_selected_curves():
    """選択されているオブジェクト以下のすべての nurvsCurve を返す"""
    return get_objects_in_herarchy(type="nurbsCurve")


def rebuild_curve(curves=None, span=1):
    """指定のカーブを指定のスパン数でリビルドする.

    curves が未指定の場合は 選択オブジェクトを対象とする｡
    span=0 の場合は 1 スパンの直線にする｡

    """
    curves = curves or get_selected_curves()

    if not curves:
        print("curves should be selected.")
        return

    for curve in curves:
        if span == 0:
            cmds.rebuildCurve(curve, ch=1, rpo=1, rt=0, end=1, kr=2, kcp=0, kep=0, kt=0, fr=0, s=1, d=1, tol=0.01)

        else:
            cmds.rebuildCurve(curve, ch=1, rpo=1, rt=0, end=1, kr=2, kcp=0, kep=0, kt=0, fr=0, s=span, d=2, tol=0.01)

    print("rebuild")


class NN_ToolWindow(object):
    """"""
    IM_Precision = 0
    IM_Distance = 3

    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (251, ui.height(10))

        self.is_chunk_open = False

    def create(self):
        if pm.window(self.window, exists=True):
            pm.deleteUI(self.window, window=True)

        # プリファレンスの有無による分岐
        if pm.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = pm.windowPref(self.window, q=True, topLeftCorner=True)
            pm.windowPref(self.window, remove=True)

            # 前回位置に指定したサイズで表示
            self.window = pm.window(
                self.window,
                t=self.title,
                widthHeight=self.size,
                sizeable=False,
                maximizeButton=False,
                minimizeButton=False,
                resizeToFitChildren=True,
                topLeftCorner=position
            )

        else:
            # プリファレンスがなければデフォルト位置に指定サイズで表示
            self.window = pm.window(
                self.window,
                t=self.title,
                widthHeight=self.size,
                sizeable=False,
                maximizeButton=False,
                minimizeButton=False,
                resizeToFitChildren=True
            )

        self.layout()
        pm.showWindow(self.window)

    def layout(self):
        """UIレイアウト."""
        ui.column_layout()

        ui.row_layout()
        ui.header(label="Create:")
        ui.button(label="Sweep", c=self.onCreateSweep)
        self.eb_material = ui.eb_text(text="", width=ui.width(5))
        self.cb_auto_material = ui.check_box(label="Auto", v=True)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Attr:")
        ui.button(label="=>", c=self.onSetTaperEither)
        ui.button(label="<>", c=self.onSetTaperBoth)
        ui.button(label="==", c=self.onSetTaperNeither)
        ui.button(label="cross section", c=self.onSetCrossSectionMesh)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Mode")
        ui.button(label="Precision", c=self.onSetModePrecision)
        ui.button(label="Distance", c=self.onSetModeDistance)
        ui.button(label="Whole", c=self.onSetModeWhole)
        ui.button(label="Span", c=self.onSetModeSpan)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Resolution")
        ui.button(label="Low", c=self.onSetResolutionLow)
        ui.button(label="High", c=self.onSetResolutionHigh)
        ui.button(label="Optimize", c=self.onToggleOptimize)
        ui.end_layout()

        ui.separator()

        ui.row_layout()
        ui.header(label="Rebuild:")
        ui.button(label="0", c=self.onRebuild0)
        ui.button(label="1", c=self.onRebuild1)
        ui.button(label="2", c=self.onRebuild2)
        ui.button(label="3", c=self.onRebuild3)
        ui.button(label="4", c=self.onRebuild4)
        ui.check_box(label="with taper pos")
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Select:")
        ui.button(label="1stCV", c=self.onSelectFirstCVs)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Curve:")
        ui.button(label="Show", c=self.onToggleShowCurve)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Mesh:")
        ui.button(label="Ref", c=self.onToggleMeshType)
        ui.end_layout()

        ui.separator()

        ui.row_layout()
        ui.header(label="Scale:")
        self.scale_slider = ui.float_slider(width=ui.width(5), min=0, max=5, value=1, dc=self.onUpdateScale, cc=self.onChangeScale)
        ui.button(label="Reset", c=self.onResetScale)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Rot:")
        self.rotation_slider = ui.float_slider(width=ui.width(5), min=-360, max=360, value=0, dc=self.onUpdateRotation, cc=self.onChangeRotation)
        ui.button(label="Reset", c=self.onResetRotation)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Twist:")
        self.twist_slider = ui.float_slider(width=ui.width(5), min=-2, max=2, value=0, dc=self.onUpdateTwist, cc=self.onChangeTwist)
        ui.button(label="Reset", c=self.onResetTwist)
        ui.end_layout()

        ui.end_layout()

    def onCreateSweep(self, *args):
        """Testハンドラ"""
        selections = pm.ls(selection=True)

        for curve_trs in selections:
            if isinstance(curve_trs.getShape(), nt.NurbsCurve):
                curve_shape = curve_trs.getShape()

                # スウィープの作成
                pm.sweepMeshFromCurve(curve_trs, oneNodePerCurve=True)
                smc_node = pm.listConnections(curve_trs.getShape(), destination=True, type="sweepMeshCreator")[0]

                # マテリアルの設定
                material = None

                if ui.get_value(self.cb_auto_material):
                    pass

                if not material:
                    material_text = ui.get_value(self.eb_material)
                    if cmds.objExists(material_text):
                        material = material_text

                if material:
                    mesh = cmds.listConnections(smc_node.name(), destination=True, type="mesh")[0]
                    cmds.sets(mesh, e=True, forceElement=material)

                # 断面の設定
                smc_node.profilePolyType.set(0)
                smc_node.profilePolySides.set(4)
                smc_node.taper.set(1)
                smc_node.interpolationPrecision.set(98)
                smc_node.interpolationOptimize.set(1)

                # テーパー設定
                smc_node.taperCurve[0].taperCurve_Position.set(0.0)
                smc_node.taperCurve[0].taperCurve_FloatValue.set(1.0)
                smc_node.taperCurve[0].taperCurve_Interp.set(3)

                smc_node.taperCurve[2].taperCurve_Position.set(0.5)
                smc_node.taperCurve[2].taperCurve_FloatValue.set(1.0)
                smc_node.taperCurve[2].taperCurve_Interp.set(3)

                smc_node.taperCurve[1].taperCurve_Position.set(1.0)
                smc_node.taperCurve[1].taperCurve_FloatValue.set(0.0)
                smc_node.taperCurve[1].taperCurve_Interp.set(1)

                # メッシュのリファレンス化
                sweep_mesh = pm.listConnections(smc_node, destination=True, type="mesh")[0]
                sweep_mesh.overrideEnabled.set(1)
                sweep_mesh.overrideDisplayType.set(2)

                # カーブの Draw on top 設定
                curve_shape.alwaysDrawOnTop.set(1)

    def onSelectFirstCVs(self, *args):
        """ハンドラ

        選択しているオブジェクト以下の全てのオブジェクト内のカーブの第一CVを選択する
        """
        selections = cmds.ls(selection=True)
        curves = []

        for obj in selections:
            descendent_curves = cmds.listRelatives(obj, allDescendents=True, type="nurbsCurve")
            curves.extend(descendent_curves)

        curves = list(set(curves))

        first_cvs = []

        for curve in curves:
            first_cvs.append(curve + ".cv[0]")

        cmds.selectMode(component=True)
        cmds.selectType(controlVertex=True)
        cmds.select(first_cvs, replace=True)
        print(first_cvs)

    def onSetTaperEither(self, *args):
        """"""
        selections = cmds.ls(selection=True)
        curves = []

        for obj in selections:
            descendent_curves = cmds.listRelatives(obj, allDescendents=True, type="nurbsCurve")
            curves.extend(descendent_curves)

        curves = list(set(curves))

        for curve in curves:
            smc_node_name = cmds.listConnections(curve, destination=True, type="sweepMeshCreator")[0]
            smc_node = pm.PyNode(smc_node_name)
            smc_node.taperCurve[0].taperCurve_Position.set(0.0)
            smc_node.taperCurve[0].taperCurve_FloatValue.set(1.0)
            smc_node.taperCurve[0].taperCurve_Interp.set(3)

            smc_node.taperCurve[2].taperCurve_Position.set(0.5)
            smc_node.taperCurve[2].taperCurve_FloatValue.set(1.0)
            smc_node.taperCurve[2].taperCurve_Interp.set(3)

            smc_node.taperCurve[1].taperCurve_Position.set(1.0)
            smc_node.taperCurve[1].taperCurve_FloatValue.set(0.0)
            smc_node.taperCurve[1].taperCurve_Interp.set(1)

    def onSetTaperBoth(self, *args):
        """"""
        selections = cmds.ls(selection=True)
        curves = []

        for obj in selections:
            descendent_curves = cmds.listRelatives(obj, allDescendents=True, type="nurbsCurve")
            curves.extend(descendent_curves)

        curves = list(set(curves))

        for curve in curves:
            smc_node_name = cmds.listConnections(curve, destination=True, type="sweepMeshCreator")[0]
            smc_node = pm.PyNode(smc_node_name)
            smc_node.taperCurve[0].taperCurve_Position.set(0.0)
            smc_node.taperCurve[0].taperCurve_FloatValue.set(0.0)
            smc_node.taperCurve[0].taperCurve_Interp.set(3)

            smc_node.taperCurve[2].taperCurve_Position.set(0.5)
            smc_node.taperCurve[2].taperCurve_FloatValue.set(1.0)
            smc_node.taperCurve[2].taperCurve_Interp.set(3)

            smc_node.taperCurve[1].taperCurve_Position.set(1.0)
            smc_node.taperCurve[1].taperCurve_FloatValue.set(0.0)
            smc_node.taperCurve[1].taperCurve_Interp.set(1)

    def onSetTaperNeither(self, *args):
        """"""
        selections = cmds.ls(selection=True)
        curves = []

        for obj in selections:
            descendent_curves = cmds.listRelatives(obj, allDescendents=True, type="nurbsCurve")
            curves.extend(descendent_curves)

        curves = list(set(curves))

        for curve in curves:
            smc_node_name = cmds.listConnections(curve, destination=True, type="sweepMeshCreator")[0]
            smc_node = pm.PyNode(smc_node_name)
            smc_node.taperCurve[0].taperCurve_Position.set(0.0)
            smc_node.taperCurve[0].taperCurve_FloatValue.set(1.0)
            smc_node.taperCurve[0].taperCurve_Interp.set(3)

            smc_node.taperCurve[2].taperCurve_Position.set(0.5)
            smc_node.taperCurve[2].taperCurve_FloatValue.set(1.0)
            smc_node.taperCurve[2].taperCurve_Interp.set(3)

            smc_node.taperCurve[1].taperCurve_Position.set(1.0)
            smc_node.taperCurve[1].taperCurve_FloatValue.set(1.0)
            smc_node.taperCurve[1].taperCurve_Interp.set(1)

    def onRebuild0(self, *args):
        """"""
        rebuild_curve(span=0)

    def onRebuild1(self, *args):
        """"""
        rebuild_curve(span=1)

    def onRebuild2(self, *args):
        """"""
        rebuild_curve(span=2)

    def onRebuild3(self, *args):
        """"""
        rebuild_curve(span=3)

    def onRebuild4(self, *args):
        """"""
        rebuild_curve(span=4)

    def onMatchSpanAndTaperPoints(self, *args):
        """"""
        print("not impl")
        pass

    def onSetCrossSectionMesh(self, *args):
        """"""
        meshes = get_objects_in_herarchy(type="mesh")
        curves = get_objects_in_herarchy(type="nurbsCurve")

        if not meshes or not curves:
            print("meshes and curves should be selected.")
            return

        mesh = meshes[0]

        for curve in curves:
            smc_node = cmds.listConnections(curve, destination=True, type="sweepMeshCreator")[0]
            spc_nodes = cmds.listConnections(smc_node, source=True, type="sweepProfileConverter")

            if spc_nodes:
                spc_node = spc_nodes[0]
            else:
                spc_node = cmds.createNode("sweepProfileConverter")
                cmds.connectAttr(spc_node + ".sweepProfileData", smc_node + ".customSweepProfileData")
                cmds.setAttr(smc_node + ".sweepProfileType", 5)

            cmds.connectAttr(mesh + ".outMesh", spc_node + ".inObjectArray[0].mesh", force=True)
            cmds.connectAttr(mesh + ".worldMatrix[0]",  spc_node + ".inObjectArray[0].worldMatrix", force=True)

    def onSetModePrecision(self, *args):
        """補間モードを に変更する"""
        curves = get_selected_curves()

        for curve in curves:
            smc_node_name = cmds.listConnections(curve, destination=True, type="sweepMeshCreator")[0]
            cmds.setAttr(smc_node_name + ".interpolationMode", 0)
            cmds.setAttr(smc_node_name + ".interpolationPrecision", 98)
        
    def onSetModeDistance(self, *args):
        """補間モードを に変更する"""
        curves = get_selected_curves()

        for curve in curves:
            smc_node_name = cmds.listConnections(curve, destination=True, type="sweepMeshCreator")[0]
            cmds.setAttr(smc_node_name + ".interpolationMode", 3)
            cmds.setAttr(smc_node_name + ".interpolationDistance", 2)
        
    def onSetModeWhole(self, *args):
        """補間モードを に変更する"""
        print("not impl")
        
    def onSetModeSpan(self, *args):
        """補間モードを に変更する"""
        print("not impl")
        
    def onSetResolutionLow(self, *args):
        """"""
        curves = get_selected_curves()

        for curve in curves:
            smc_node_name = cmds.listConnections(curve, destination=True, type="sweepMeshCreator")[0]
            mode = cmds.getAttr(smc_node_name + ".interpolationMode")

            if mode == self.IM_Precision:
                resolution = cmds.getAttr(smc_node_name + ".interpolationPrecision")
                resolution -= 1
                resolution = cmds.setAttr(smc_node_name + ".interpolationPrecision", resolution)

            elif mode == self.IM_Distance:
                resolution = cmds.getAttr(smc_node_name + ".interpolationDistance")
                resolution += 0.1
                resolution = cmds.setAttr(smc_node_name + ".interpolationDistance", resolution)
            else:
                print("not impl")

    def onSetResolutionHigh(self, *args):
        """"""
        curves = get_selected_curves()

        for curve in curves:
            smc_node_name = cmds.listConnections(curve, destination=True, type="sweepMeshCreator")[0]
            mode = cmds.getAttr(smc_node_name + ".interpolationMode")

            if mode == self.IM_Precision:
                resolution = cmds.getAttr(smc_node_name + ".interpolationPrecision")
                resolution += 1
                resolution = cmds.setAttr(smc_node_name + ".interpolationPrecision", resolution)

            elif mode == self.IM_Distance:
                resolution = cmds.getAttr(smc_node_name + ".interpolationDistance")
                resolution -= 0.1
                resolution = cmds.setAttr(smc_node_name + ".interpolationDistance", resolution)
            else:
                print("not impl")

    def onToggleOptimize(self, *args):
        """"""
        curves = get_selected_curves()
        current_optimize = None
        new_optimize = None
        
        if curves:
            smc_node_name = cmds.listConnections(curves[0], destination=True, type="sweepMeshCreator")[0]
            current_optimize = cmds.getAttr(smc_node_name + ".interpolationOptimize")
            new_optimize = not current_optimize

        for curve in curves:
            smc_node_name = cmds.listConnections(curve, destination=True, type="sweepMeshCreator")[0]
            cmds.setAttr(smc_node_name + ".interpolationOptimize", new_optimize)

    def onToggleShowCurve(self, *args):
        """"""
        all_model_panels = cmds.getPanel(type="modelPanel")

        if not all_model_panels:
            raise

        current_value = cmds.modelEditor(all_model_panels[0], q=True, nurbsCurves=True)
        new_value = not current_value

        for panel in all_model_panels:
            pm.modelEditor(panel, e=True, nurbsCurves=new_value)

    def onToggleMeshType(self, *args):
        """"""
        meshes = get_all_sweep_meshes(shape=False)

        if not meshes:
            return

        current_value = cmds.getAttr(meshes[0] + ".overrideEnabled")
        new_value = 0 if current_value else 1

        for mesh in meshes:
            cmds.setAttr(mesh + ".overrideEnabled", new_value)

        if new_value:
            nd.message("Reference")
        else:
            nd.message("Normal")

    def onUpdateScale(self, *args):
        """スケールスライダー変更中のハンドラ"""
        if not self.is_chunk_open:
            self.is_chunk_open = True
            cmds.undoInfo(ock=True)

        selections = cmds.ls(selection=True)
        curves = []

        for obj in selections:
            descendent_curves = cmds.listRelatives(obj, allDescendents=True, type="nurbsCurve")
            curves.extend(descendent_curves)

        # スライダーの値
        value = ui.get_value(self.scale_slider)

        curves = list(set(curves))

        for curve in curves:
            smc_node_name = cmds.listConnections(curve, destination=True, type="sweepMeshCreator")[0]
            cmds.setAttr(smc_node_name + ".scaleProfileX", value)

    def onChangeScale(self, *args):
        """スケールスライダー確定時のハンドラ"""
        self.onUpdateScale()

        # Undo チャンクのクローズ
        if self.is_chunk_open:
            cmds.undoInfo(cck=True)
            self.is_chunk_open = False

    def onUpdateRotation(self, *args):
        """ローテーションスライダー変更中のハンドラ"""
        if not self.is_chunk_open:
            self.is_chunk_open = True
            cmds.undoInfo(ock=True)

        selections = cmds.ls(selection=True)
        curves = []

        for obj in selections:
            descendent_curves = cmds.listRelatives(obj, allDescendents=True, type="nurbsCurve")
            curves.extend(descendent_curves)

        # スライダーの値
        value = ui.get_value(self.rotation_slider)

        curves = list(set(curves))

        for curve in curves:
            smc_node_name = cmds.listConnections(curve, destination=True, type="sweepMeshCreator")[0]
            cmds.setAttr(smc_node_name + ".rotateProfile", value)

    def onChangeRotation(self, *args):
        """ローテーションスライダー確定時のハンドラ"""
        self.onUpdateRotation()

        # Undo チャンクのクローズ
        if self.is_chunk_open:
            cmds.undoInfo(cck=True)
            self.is_chunk_open = False

    def onUpdateTwist(self, *args):
        """ツイストスライダー変更中のハンドラ"""
        if not self.is_chunk_open:
            self.is_chunk_open = True
            cmds.undoInfo(ock=True)

        selections = cmds.ls(selection=True)
        curves = []

        for obj in selections:
            descendent_curves = cmds.listRelatives(obj, allDescendents=True, type="nurbsCurve")
            curves.extend(descendent_curves)

        # スライダーの値
        value = ui.get_value(self.twist_slider)

        curves = list(set(curves))

        for curve in curves:
            smc_node_name = cmds.listConnections(curve, destination=True, type="sweepMeshCreator")[0]
            cmds.setAttr(smc_node_name + ".twist", value)

    def onChangeTwist(self, *args):
        """ツイストスライダー確定時のハンドラ"""
        self.onUpdateTwist()

        # Undo チャンクのクローズ
        if self.is_chunk_open:
            cmds.undoInfo(cck=True)
            self.is_chunk_open = False

    def onResetScale(self, *args):
        """スケールのリセット"""
        ui.set_value(self.scale_slider, value=1)
        self.onChangeScale()

    def onResetRotation(self, *args):
        """ローテーションのリセット"""
        ui.set_value(self.rotation_slider, value=0)
        self.onChangeRotation()

    def onResetTwist(self, *args):
        """ツイストのリセット"""
        ui.set_value(self.twist_slider, value=0)
        self.onChangeTwist()


def main():
    NN_ToolWindow().create()


if __name__ == "__main__":
    main()

