# ダイアログのテンプレ
# self.window だけユニークならあとはそのままで良い

import re
import os
import sys
import traceback

import pymel.core as pm
import maya.cmds as cmds
import maya.mel as mel

import nnutil


window_name = "NN_Transform"
window = None


def get_window():
    return window


window_width = 220
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
        self.window = window_name
        self.title = window_name
        self.size = (window_width, 210)

    def create(self):
        if pm.window(self.window, exists=True):
            pm.deleteUI(self.window, window=True)

        # プリファレンスの有無による分岐
        if pm.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = pm.windowPref(self.window, q=True, topLeftCorner=True)
            pm.windowPref(self.window, remove=True)

            # 前回位置に指定したサイズで表示
            pm.window(
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
            pm.window(
                self.window,
                t=self.title,
                maximizeButton=False,
                minimizeButton=False,
                widthHeight=self.size,
                sizeable=False,
                resizeToFitChildren=True
                )

        self.layout()
        pm.showWindow(self.window)

    def layout(self):
        self.columnLayout = cmds.columnLayout()

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=16)
        self.label1 = cmds.text(label='Freeze', width=header_width)
        self.buttonA = cmds.button(l='All', c=self.onFreezeTransformAll, width=bw_single)
        self.buttonA = cmds.button(l='Tra', c=self.onFreezeTransformTra, width=bw_single)
        self.buttonA = cmds.button(l='Rot', c=self.onFreezeTransformRot, width=bw_single)
        self.buttonA = cmds.button(l='Sca', c=self.onFreezeTransformSca, width=bw_single)
        self.buttonA = cmds.button(l='Op', c=self.onFreezeTransformOp, width=bw_single)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=16)
        self.label1 = cmds.text(label='Reset', width=header_width)
        self.buttonA = cmds.button(l='All', c=self.onResetTransformAll, width=bw_single)
        self.buttonA = cmds.button(l='Op', c=self.onResetTransformOp, width=bw_single)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=16)
        self.label1 = cmds.text(label='Unlock', width=header_width)
        self.buttonA = cmds.button(l='unlock', c=self.onUnlockTRS, width=bw_single)
        self.buttonA = cmds.button(l='lock', c=self.onLockTRS, width=bw_single)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=16)
        self.label1 = cmds.text(label='Match', width=header_width)
        self.buttonA = cmds.button(l='All', c=self.onMatchTransformAll, width=bw_single)
        self.buttonA = cmds.button(l='Tra', c=self.onMatchTransformTra, width=bw_single)
        self.buttonA = cmds.button(l='Rot', c=self.onMatchTransformRot, width=bw_single)
        self.buttonA = cmds.button(l='Sca', c=self.onMatchTransformSca, width=bw_single)
        self.buttonA = cmds.button(l='Piv', c=self.onMatchTransformPivot, width=bw_single)
        self.buttonA = cmds.button(l='Sp', c=self.onMatchTransformValue, width=bw_single)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=16)
        self.label1 = cmds.text(label='Pivot', width=header_width)
        self.buttonA = cmds.button(l='Center', c=self.onCenterPivot, width=bw_double)
        self.buttonA = cmds.button(l='Bake', c=self.onBakePivot, width=bw_double)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=16)
        self.label1 = cmds.text(label='Create', width=header_width)
        self.buttonA = cmds.button(l='Locator', c=self.onCreateLOcator, width=bw_double)
        self.buttonA = cmds.button(l='Joint', c=self.onCreateJoint, width=bw_double)
        self.buttonA = cmds.button(l='Empty', c=self.onCreateEmpty, width=bw_double)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=16)
        self.label1 = cmds.text(label='Convert', width=header_width)
        self.buttonA = cmds.button(l='Instance to Mesh', c=self.onInstanceToMesh, width=bw_double)
        cmds.setParent("..")

        cmds.separator(width=window_width)

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

    def onResetTransformOp(self, *args):
        mel.eval("ResetTransformationsOptions;")

    def onUnlockTRS(self, *args):
        objects = cmds.ls(selection=True)

        for obj in objects:
            nnutil.unlock_trs(obj)

    def onLockTRS(self, *args):
        objects = cmds.ls(selection=True)

        for obj in objects:
            nnutil.lock_trs(obj)

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

    def onCreateLOcator(self, *args):
        mel.eval("CreateLocator")

    def onCreateJoint(self, *args):
        mel.eval("JointTool")

    def onCreateEmpty(self, *args):
        mel.eval("doGroup 0 1 1;")

    def onInstanceToMesh(self, *args):
        nnutil.freeze_instance()


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()