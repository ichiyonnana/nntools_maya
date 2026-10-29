# ダイアログのテンプレ
# self.window だけユニークならあとはそのままで良い

import re
import os
import sys
import traceback

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

import nnutil.core as nu
import nnutil.misc as nm
import nnutil.ui as ui


window_name = "NN_Transform"
window = None


def get_window():
    return window


window_width = 220

color_freeze = (0.529, 0.722, 0.918)
color_reset = (0.918, 0.529, 0.529)
color_lock = (0.918, 0.886, 0.529)


class NN_ToolWindow(object):

    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (window_width, 210)

    def create(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)

        cmds.window(
            self.window,
            t=self.title,
            maximizeButton=False,
            minimizeButton=False,
            widthHeight=self.size,
            sizeable=False,
            resizeToFitChildren=True
            )

        # ls(orderedSelection=True) 用に有効化
        cmds.selectPref(trackSelectionOrder=True)

        self.layout()
        cmds.showWindow(self.window)

    def layout(self):
        separator_width = window_width

        with ui.column_layout():
            with ui.row_layout():
                ui.button(label='Freeze', width=ui.width(2), c=self.onFreezeTransformOp)
                ui.button(label='All', c=self.onFreezeTransformAll, width=ui.width2, bgc=color_freeze)
                ui.button(label='Tra', c=self.onFreezeTransformTra, width=ui.width1, bgc=color_freeze)
                ui.button(label='Rot', c=self.onFreezeTransformRot, width=ui.width1, bgc=color_freeze)
                ui.button(label='Sca', c=self.onFreezeTransformSca, width=ui.width1, bgc=color_freeze)

            ui.separator(width=separator_width)

            with ui.row_layout():
                ui.button(label='Reset', width=ui.width(2), c=self.onResetTransformOp)
                ui.button(label='All', c=self.onResetTransformAll, width=ui.width2, bgc=color_reset)
                ui.button(label='Tra', c=self.onResetTransformTra, width=ui.width1, bgc=color_reset)
                ui.button(label='Rot', c=self.onResetTransformRot, width=ui.width1, bgc=color_reset)
                ui.button(label='Sca', c=self.onResetTransformSca, width=ui.width1, bgc=color_reset)

            ui.separator(width=separator_width)

            with ui.row_layout():
                ui.header(label='TRS Lock')
                ui.button(label='Unlock', c=self.onUnlockTRS, bgc=color_lock)
                ui.button(label='Lock', c=self.onLockTRS, bgc=color_lock)

            ui.separator(width=separator_width)

            with ui.row_layout():
                ui.header(label='Match')
                ui.button(label='All', c=self.onMatchTransformAll, width=ui.width1)
                ui.button(label='Tra', c=self.onMatchTransformTra, width=ui.width1)
                ui.button(label='Rot', c=self.onMatchTransformRot, width=ui.width1)
                ui.button(label='Sca', c=self.onMatchTransformSca, width=ui.width1)
                ui.button(label='Piv', c=self.onMatchTransformPivot, width=ui.width1)
                ui.button(label='Sp', c=self.onMatchTransformValue, width=ui.width1, annotation="形状を変えずにローカル空間だけ一致させる")

            ui.separator(width=separator_width)

            with ui.row_layout():
                ui.header(label='Pivot')
                ui.button(label='Center', c=self.onCenterPivot, width=ui.width2)
                ui.button(label='Bake', c=self.onBakePivot, width=ui.width2)
                ui.button(label='Restore', c=self.onRestoreTransform, width=ui.width2)

            ui.separator(width=separator_width)

            with ui.row_layout():
                ui.header(label='Create')
                ui.button(label='Locator', c=self.onCreateLOcator, width=ui.width2)
                ui.button(label='Joint', c=self.onCreateJoint, width=ui.width2)
                ui.button(label='Empty', c=self.onCreateEmpty, width=ui.width2)

            ui.separator(width=separator_width)

            with ui.row_layout():
                ui.header(label='Convert')
                ui.button(label='Instance to Mesh', c=self.onInstanceToMesh, width=ui.width(6))

            with ui.row_layout():
                ui.header(label='')
                ui.button(label='Smooth Preview to Mesh', c=self.onSmoothPreviewToMesh, width=ui.width(6))

            ui.separator(width=separator_width)

    def onFreezeTransformAll(self, *args):
        mel.eval("makeIdentity -apply true -t 1 -r 1 -s 1 -n 0 -pn 1;")

    def onFreezeTransformTra(self, *args):
        mel.eval("makeIdentity -apply true -t 1 -r 0 -s 0 -n 0 -pn 1;")

    def onFreezeTransformRot(self, *args):
        mel.eval("makeIdentity -apply true -t 0 -r 1 -s 0 -n 0 -pn 1;")

    def onFreezeTransformSca(self, *args):
        mel.eval("makeIdentity -apply true -t 0 -r 0 -s 1 -n 0 -pn 1;")

    def onFreezeTransformOp(self, *args):
        mel.eval("FreezeTransformationsOptions;")

    def onResetTransformAll(self, *args):
        mel.eval("ResetTransformations;")

    def onResetTransformTra(self, *args):
        mel.eval("makeIdentity -apply false -t 1 -r 0 -s 0 -n 0 -pn 1;")

    def onResetTransformRot(self, *args):
        mel.eval("makeIdentity -apply false -t 0 -r 1 -s 0 -n 0 -pn 1;")

    def onResetTransformSca(self, *args):
        mel.eval("makeIdentity -apply false -t 0 -r 0 -s 1 -n 0 -pn 1;")

    def onResetTransformOp(self, *args):
        mel.eval("ResetTransformationsOptions;")

    def onUnlockTRS(self, *args):
        objects = cmds.ls(selection=True)

        for obj in objects:
            nu.unlock_trs(obj)

    def onLockTRS(self, *args):
        objects = cmds.ls(selection=True)

        for obj in objects:
            nu.lock_trs(obj)

    def onMatchTransformAll(self, *args):
        mel.eval("MatchTransform;")

    def onMatchTransformTra(self, *args):
        mel.eval("matchTransform -pos;")

    def onMatchTransformRot(self, *args):
        mel.eval("matchTransform -rot;")

    def onMatchTransformSca(self, *args):
        mel.eval("matchTransform -scl;")

    def onMatchTransformPivot(self, *args):
        mel.eval("matchTransform -piv;")

    def onMatchTransformValue(self, *args):
        """
        見た目を変えずにローカル空間とトランスフォームの値を一致させる
        """

        # 親取得
        # 子にする
        # フリーズ＆リセット
        # 元の親にペアレント戻す

        from_obj, to_obj = cmds.ls(selection=True, flatten=True)
        from_parent = cmds.listRelatives(from_obj, parent=True, path=True)
        cmds.parent(from_obj, to_obj)
        cmds.makeIdentity(from_obj, apply=True, t=True, r=True, s=True, n=False, pn=True)
        cmds.select(from_obj, replace=True)
        mel.eval("ResetTransformations;")
        if from_parent:
            cmds.parent(from_obj, from_parent)
        else:
            cmds.parent(from_obj, w=True)

    def onCenterPivot(self, *args):
        mel.eval("CenterPivot")

    def onBakePivot(self, *args):
        mel.eval("BakeCustomPivot")

    def onRestoreTransform(self, *args):
        """
        選択順の 3 頂点から軸を決め、見た目を変えずに頂点が属するオブジェクトの TRS を設定する

        第一選択→第二選択が X 軸、3 点がつくる平面の法線が Z 軸、3 点の重心が原点。Scale は 1 になる
        """
        vertices = cmds.filterExpand(cmds.ls(orderedSelection=True, flatten=True), selectionMask=31) or []

        if len(vertices) != 3:
            cmds.warning("頂点を 3 つ選択して下さい")
            return

        shapes = set(cmds.ls(vertices, objectsOnly=True, long=True))

        if len(shapes) != 1:
            cmds.warning("同じオブジェクトの頂点を選択して下さい")
            return

        obj = cmds.listRelatives(shapes.pop(), parent=True, path=True)[0]
        p0, p1, p2 = [om.MPoint(cmds.pointPosition(v, world=True)) for v in vertices]
        x_axis = p1 - p0
        z_axis = x_axis ^ (p2 - p0)

        if z_axis.length() == 0:
            cmds.warning("3 頂点が一直線上にあります")
            return

        x_axis.normalize()
        z_axis.normalize()
        y_axis = z_axis ^ x_axis
        center = p0 + ((p1 - p0) + (p2 - p0)) / 3
        matrix = [x_axis.x, x_axis.y, x_axis.z, 0, y_axis.x, y_axis.y, y_axis.z, 0, z_axis.x, z_axis.y, z_axis.z, 0, center.x, center.y, center.z, 1]

        # 目的の軸を持つグループの子にしてフリーズし、元の親へ戻すことでワールド位置を保ったまま TRS を移す
        cmds.undoInfo(openChunk=True)
        try:
            parent = cmds.listRelatives(obj, parent=True, path=True)
            group = cmds.group(empty=True, world=True)
            cmds.xform(group, worldSpace=True, matrix=matrix)
            obj = cmds.parent(obj, group)[0]
            cmds.makeIdentity(obj, apply=True, translate=True, rotate=True, scale=True, normal=False, preserveNormals=True)
            cmds.xform(obj, objectSpace=True, pivots=(0, 0, 0))

            if parent:
                cmds.parent(obj, parent[0])
            else:
                cmds.parent(obj, world=True)

            cmds.delete(group)
            cmds.select(vertices, replace=True)
        finally:
            cmds.undoInfo(closeChunk=True)

    def onCreateLOcator(self, *args):
        mel.eval("CreateLocator")

    def onCreateJoint(self, *args):
        mel.eval("JointTool")

    def onCreateEmpty(self, *args):
        mel.eval("doGroup 0 1 1;")

    def onInstanceToMesh(self, *args):
        nm.freeze_instance()

    def onSmoothPreviewToMesh(self, *args):
        nm.smooth_preview_to_mesh()


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
