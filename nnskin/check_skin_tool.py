#! python
# coding:utf-8

"""

"""
import maya.cmds as cmds
import pymel.core as pm

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import nnutil.display as nd

dialog_name = "NN_SkinChecker"


class NN_ToolWindow(object):
    def __init__(self):
        self.window = dialog_name
        self.title = dialog_name
        self.size = (300, 95)

        self.root_joint = None
        self.joints = []

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
        ui.header()
        ui.button(label="Set Root", c=self.onSetRoot)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.text(label="Root Joint :", width=ui.width3)
        self.text_root = ui.text(label="None")
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.text(label="Current Joint :", width=ui.width3)
        self.text_current = ui.text(label="None")
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.button(label="Prev", c=self.onPrev)
        ui.button(label="Reset", c=self.onReset)
        ui.button(label="Next", c=self.onNext)
        ui.end_layout()

        ui.separator(height=ui.height1)

        ui.row_layout()
        ui.header(label="Translate")
        ui.text(label="X", bgc=ui.color_x)
        self.fs_tra_x = ui.float_slider(min=-1.0, max=1.0, value=0, width=ui.width6, dc=self.onDragTranslateX, cc=self.onChangeTranslateX)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.text(label="Y", bgc=ui.color_y)
        self.fs_tra_y = ui.float_slider(min=-1.0, max=1.0, value=0, width=ui.width6, dc=self.onDragTranslateY, cc=self.onChangeTranslateY)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.text(label="Z", bgc=ui.color_z)
        self.fs_tra_z = ui.float_slider(min=-1.0, max=1.0, value=0, width=ui.width6, dc=self.onDragTranslateZ, cc=self.onChangeTranslateZ)
        ui.end_layout()

        ui.separator(height=ui.height1)

        ui.row_layout()
        ui.header(label="Rotate")
        ui.text(label="X", bgc=ui.color_x)
        self.fs_rot_x = ui.float_slider(min=-1.0, max=1.0, value=0, width=ui.width6, dc=self.onDragRotateX, cc=self.onChangeRotateX)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.text(label="Y", bgc=ui.color_y)
        self.fs_rot_y = ui.float_slider(min=-1.0, max=1.0, value=0, width=ui.width6, dc=self.onDragRotateY, cc=self.onChangeRotateY)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.text(label="Z", bgc=ui.color_z)
        self.fs_rot_z = ui.float_slider(min=-1.0, max=1.0, value=0, width=ui.width6, dc=self.onDragRotateZ, cc=self.onChangeRotateZ)
        ui.end_layout()

        ui.separator(height=ui.height1)

        ui.row_layout()
        ui.header(label="")
        ui.button(label="Gradation", c=self.onGradation)
        ui.button(label="Animation", c=self.onAnimation)
        ui.end_layout()

        ui.end_layout()

    def onSetRoot(self, *args):
        pass

    def onDragTranslateX(self, *args):
        pass

    def onDragTranslateY(self, *args):
        pass

    def onDragTranslateZ(self, *args):
        pass

    def onDragRotateX(self, *args):
        pass

    def onDragRotateY(self, *args):
        pass

    def onDragRotateZ(self, *args):
        pass

    def onChangeTranslateX(self, *args):
        if ui.is_shift():
            ui.set_value(self.fs_tra_x, value=0)

    def onChangeTranslateY(self, *args):
        if ui.is_shift():
            ui.set_value(self.fs_tra_y, value=0)

    def onChangeTranslateZ(self, *args):
        if ui.is_shift():
            ui.set_value(self.fs_tra_z, value=0)

    def onChangeRotateX(self, *args):
        if ui.is_shift():
            ui.set_value(self.fs_rot_x, value=0)

    def onChangeRotateY(self, *args):
        if ui.is_shift():
            ui.set_value(self.fs_rot_y, value=0)

    def onChangeRotateZ(self, *args):
        if ui.is_shift():
            ui.set_value(self.fs_rot_z, value=0)

    def onGradation(self, *args):
        pass

    def onAnimation(self, *args):
        pass

    def onPrev(self, *args):
        pass

    def onReset(self, *args):
        pass

    def onNext(self, *args):
        pass


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
