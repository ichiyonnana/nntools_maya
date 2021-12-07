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
import nnutil.misc as nm


dialog_name = "NN_SkinChecker"

default_translate_factor = 10
default_rotate_factor = 180


class TRS():
    def __init__(self, obj):
        self.translateX = obj.translateX.get()
        self.translateY = obj.translateY.get()
        self.translateZ = obj.translateZ.get()
        self.rotateX = obj.rotateX.get()
        self.rotateY = obj.rotateY.get()
        self.rotateZ = obj.rotateZ.get()
        self.scaleX = obj.scaleX.get()
        self.scaleY = obj.scaleY.get()
        self.scaleZ = obj.scaleZ.get()


class NN_ToolWindow(object):
    def __init__(self):
        self.window = dialog_name
        self.title = dialog_name
        self.size = (300, 95)

        self.root_joint = None
        self.joints = []
        self.cursor = 0
        self.fit_factor = 0.1

        self.neutral_trs = []
        self.meshes = []

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
        self.text_root = ui.text(label="None", width=ui.width3)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.text(label="Current Joint :", width=ui.width3)
        self.text_current = ui.text(label="None", width=ui.width3)
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

        ui.row_layout()
        ui.header(label="factor")
        ui.text(label="Tra", width=ui.width1)
        self.eb_translate_factor = ui.eb_int(v=default_translate_factor)
        ui.text(label="Rot", width=ui.width1)
        self.eb_rotate_factor = ui.eb_int(v=default_rotate_factor)
        ui.end_layout()

        ui.end_layout()

    def current_joint(self):
        return self.joints[self.cursor]

    def translate_factor(self):
        return ui.get_value(self.eb_translate_factor)

    def rotate_factor(self):
        return ui.get_value(self.eb_rotate_factor)

    def onSetRoot(self, *args):
        selection = pm.selected(flatten=True)[0]
        self.root_joint = selection
        self.joints = [pm.PyNode(x) for x in pm.listRelatives(self.root_joint, allDescendents=True, type="joint")]

        self.neutral_trs = [None] * len(self.joints)

        for i, joint in enumerate(self.joints):
            self.neutral_trs[i] = TRS(joint)

        self.meshes = pm.listRelatives(self.root_joint, allDescendents=True, type="mesh")

        ui.set_value(self.text_root, self.root_joint)

    def onDragTranslateX(self, *args):
        self.onChangeTranslateX(*args)

    def onDragTranslateY(self, *args):
        self.onChangeTranslateY(*args)

    def onDragTranslateZ(self, *args):
        self.onChangeTranslateZ(*args)

    def onDragRotateX(self, *args):
        self.onChangeRotateX(*args)

    def onDragRotateY(self, *args):
        self.onChangeRotateY(*args)

    def onDragRotateZ(self, *args):
        self.onChangeRotateZ(*args)

    def onChangeTranslateX(self, *args):
        if ui.is_shift():
            ui.set_value(self.fs_tra_x, value=0)

        active_obj = self.joints[self.cursor]
        neutral = self.neutral_trs[self.cursor].translateX
        v = ui.get_value(self.fs_tra_x)
        active_obj.translateX.set(neutral + v * self.translate_factor())

    def onChangeTranslateY(self, *args):
        if ui.is_shift():
            ui.set_value(self.fs_tra_y, value=0)

        active_obj = self.joints[self.cursor]
        neutral = self.neutral_trs[self.cursor].translateY
        v = ui.get_value(self.fs_tra_y)
        active_obj.translateY.set(neutral + v * self.translate_factor())

    def onChangeTranslateZ(self, *args):
        if ui.is_shift():
            ui.set_value(self.fs_tra_z, value=0)

        active_obj = self.joints[self.cursor]
        neutral = self.neutral_trs[self.cursor].translateZ
        v = ui.get_value(self.fs_tra_z)
        active_obj.translateZ.set(neutral + v * self.translate_factor())

    def onChangeRotateX(self, *args):
        if ui.is_shift():
            ui.set_value(self.fs_rot_x, value=0)

        active_obj = self.joints[self.cursor]
        neutral = self.neutral_trs[self.cursor].rotateX
        v = ui.get_value(self.fs_rot_x)
        active_obj.rotateX.set(neutral + v * self.rotate_factor())

    def onChangeRotateY(self, *args):
        if ui.is_shift():
            ui.set_value(self.fs_rot_y, value=0)

        active_obj = self.joints[self.cursor]
        neutral = self.neutral_trs[self.cursor].rotateY
        v = ui.get_value(self.fs_rot_y)
        active_obj.rotateY.set(neutral + v * self.rotate_factor())

    def onChangeRotateZ(self, *args):
        if ui.is_shift():
            ui.set_value(self.fs_rot_z, value=0)

        active_obj = self.joints[self.cursor]
        neutral = self.neutral_trs[self.cursor].rotateZ
        v = ui.get_value(self.fs_rot_z)
        active_obj.rotateZ.set(neutral + v * self.rotate_factor())

    def onGradation(self, *args):
        nm.weight_paint_mode_with_selected_joint(joint=self.current_joint(), meshes=self.meshes)

    def onAnimation(self, *args):
        pass

    def onPrev(self, *args):
        self.cursor -= 1

        if self.cursor < 0:
            nd.message("finish")
            self.cursor = len(self.joints) - 1

        active_obj = self.joints[self.cursor]
        pm.select(active_obj)
        pm.viewFit(animate=True, fitFactor=self.fit_factor)
        ui.set_value(self.text_current, active_obj)

    def onReset(self, *args):
        self.cursor = 0

        active_obj = self.joints[self.cursor]
        pm.select(active_obj)
        pm.viewFit(animate=True, fitFactor=self.fit_factor)
        ui.set_value(self.text_current, active_obj)

    def onNext(self, *args):
        self.cursor += 1

        if self.cursor >= len(self.joints):
            nd.message("finish")
            self.cursor = 0

        active_obj = self.joints[self.cursor]
        pm.select(active_obj)
        pm.viewFit(animate=True, fitFactor=self.fit_factor)
        ui.set_value(self.text_current, active_obj)


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
