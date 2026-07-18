# ダイアログのテンプレ
# self.window だけユニークならあとはそのままで良い

import re
import os
import sys
import traceback

import maya.cmds as cmds
import maya.mel as mel

import nnutil.core as nu
import nnutil.misc as nm
import nnutil.ui as ui


window_name = "NN_Transform"
window = None


def get_window():
    return window


window_width = 220


class NN_ToolWindow(object):

    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (window_width, 210)

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
        separator_width = window_width

        ui.column_layout()

        ui.row_layout()
        ui.header(label='Freeze')
        ui.button(label='All', c=self.onFreezeTransformAll, width=ui.width1)
        ui.button(label='Tra', c=self.onFreezeTransformTra, width=ui.width1)
        ui.button(label='Rot', c=self.onFreezeTransformRot, width=ui.width1)
        ui.button(label='Sca', c=self.onFreezeTransformSca, width=ui.width1)
        ui.button(label='Op', c=self.onFreezeTransformOp, width=ui.width1)
        ui.end_layout()

        ui.separator(width=separator_width)

        ui.row_layout()
        ui.header(label='Reset')
        ui.button(label='All', c=self.onResetTransformAll, width=ui.width1)
        ui.button(label='Op', c=self.onResetTransformOp, width=ui.width1)
        ui.end_layout()

        ui.separator(width=separator_width)

        ui.row_layout()
        ui.header(label='TRS Lock')
        ui.button(label='Unlock', c=self.onUnlockTRS)
        ui.button(label='Lock', c=self.onLockTRS)
        ui.end_layout()

        ui.separator(width=separator_width)

        ui.row_layout()
        ui.header(label='Match')
        ui.button(label='All', c=self.onMatchTransformAll, width=ui.width1)
        ui.button(label='Tra', c=self.onMatchTransformTra, width=ui.width1)
        ui.button(label='Rot', c=self.onMatchTransformRot, width=ui.width1)
        ui.button(label='Sca', c=self.onMatchTransformSca, width=ui.width1)
        ui.button(label='Piv', c=self.onMatchTransformPivot, width=ui.width1)
        ui.button(label='Sp', c=self.onMatchTransformValue, width=ui.width1)
        ui.end_layout()

        ui.separator(width=separator_width)

        ui.row_layout()
        ui.header(label='Pivot')
        ui.button(label='Center', c=self.onCenterPivot, width=ui.width2)
        ui.button(label='Bake', c=self.onBakePivot, width=ui.width2)
        ui.end_layout()

        ui.separator(width=separator_width)

        ui.row_layout()
        ui.header(label='Create')
        ui.button(label='Locator', c=self.onCreateLOcator, width=ui.width2)
        ui.button(label='Joint', c=self.onCreateJoint, width=ui.width2)
        ui.button(label='Empty', c=self.onCreateEmpty, width=ui.width2)
        ui.end_layout()

        ui.separator(width=separator_width)

        ui.row_layout()
        ui.header(label='Convert')
        ui.button(label='Instance to Mesh', c=self.onInstanceToMesh, width=ui.width(6))
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='Smooth Preview to Mesh', c=self.onSmoothPreviewToMesh, width=ui.width(6))
        ui.end_layout()

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
