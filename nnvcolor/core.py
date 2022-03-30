#! python
# coding:utf-8

"""

"""
import maya.cmds as cmds
import pymel.core as pm
import maya.mel as mel

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import nnutil.display as nd

dialog_name = "NN_VColor"


class NN_ToolWindow(object):
    def __init__(self):
        self.window = dialog_name
        self.title = dialog_name
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
        ui.button(label="Create Set [Op]", c=self.onCreateColorSet, dgc=self.onColorSetEditor)
        ui.button(label="Toggle Disp", c=self.onToggleDisplay)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="R")
        ui.button(label="0.00", c=self.onSetColorR000, bgc=(0, 0, 0), width=ui.width1_5)
        ui.button(label="0.25", c=self.onSetColorR025, bgc=(0.25, 0, 0), width=ui.width1_5)
        ui.button(label="0.50", c=self.onSetColorR050, bgc=(0.5, 0, 0), width=ui.width1_5)
        ui.button(label="0.75", c=self.onSetColorR075, bgc=(0.75, 0, 0), width=ui.width1_5)
        ui.button(label="1.00", c=self.onSetColorR100, bgc=(1.0, 0, 0), width=ui.width1_5)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        self.fs_red = ui.float_slider(min=0, max=1.0, value=1.0, width=ui.width(7.5), dc=self.onDragRed)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="G")
        ui.button(label="0.00", c=self.onSetColorG000, bgc=(0, 0, 0), width=ui.width1_5)
        ui.button(label="0.25", c=self.onSetColorG025, bgc=(0, 0.25, 0), width=ui.width1_5)
        ui.button(label="0.50", c=self.onSetColorG050, bgc=(0, 0.5, 0), width=ui.width1_5)
        ui.button(label="0.75", c=self.onSetColorG075, bgc=(0, 0.75, 0), width=ui.width1_5)
        ui.button(label="1.00", c=self.onSetColorG100, bgc=(0, 1.0, 0), width=ui.width1_5)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        self.fs_green = ui.float_slider(min=0, max=1.0, value=1.0, width=ui.width(7.5), dc=self.onDragGreen)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="B")
        ui.button(label="0.00", c=self.onSetColorB000, bgc=(0, 0, 0), width=ui.width1_5)
        ui.button(label="0.25", c=self.onSetColorB025, bgc=(0, 0, 0.25), width=ui.width1_5)
        ui.button(label="0.50", c=self.onSetColorB050, bgc=(0, 0, 0.5), width=ui.width1_5)
        ui.button(label="0.75", c=self.onSetColorB075, bgc=(0, 0, 0.75), width=ui.width1_5)
        ui.button(label="1.00", c=self.onSetColorB100, bgc=(0, 0, 1.0), width=ui.width1_5)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        self.fs_blue = ui.float_slider(min=0, max=1.0, value=1.0, width=ui.width(7.5), dc=self.onDragBlue)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="A")
        ui.button(label="0.00", c=self.onSetColorA000, bgc=(0, 0, 0), width=ui.width1_5)
        ui.button(label="0.25", c=self.onSetColorA025, bgc=(0.25, 0.25, 0.25), width=ui.width1_5)
        ui.button(label="0.50", c=self.onSetColorA050, bgc=(0.5, 0.5, 0.5), width=ui.width1_5)
        ui.button(label="0.75", c=self.onSetColorA075, bgc=(0.75, 0.75, 0.75), width=ui.width1_5)
        ui.button(label="1.00", c=self.onSetColorA100, bgc=(1.0, 1.0, 1.0), width=ui.width1_5)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        self.fs_alpha = ui.float_slider(min=0, max=1.0, value=1.0, width=ui.width(7.5), dc=self.onDragAlpha)
        ui.end_layout()

        ui.row_layout()
        ui.end_layout()

        ui.row_layout()
        ui.end_layout()

        ui.end_layout()

    def onCreateColorSet(self, *args):
        pm.polyColorSet(create=True, clamped=0, rpt="RGBA", colorSet="colorSet")

    def onColorSetEditor(self, *args):
        mel.eval("colorSetEditor")

    def onToggleDisplay(self, *args):
        mel.eval("toggleShadeMode")

    def onSetColorR000(self, *args):
        pm.polyColorPerVertex(r=0.0)

    def onSetColorR025(self, *args):
        pm.polyColorPerVertex(r=0.25)

    def onSetColorR050(self, *args):
        pm.polyColorPerVertex(r=0.5)

    def onSetColorR075(self, *args):
        pm.polyColorPerVertex(r=0.75)

    def onSetColorR100(self, *args):
        pm.polyColorPerVertex(r=1.0)

    def onSetColorG000(self, *args):
        pm.polyColorPerVertex(g=0.0)

    def onSetColorG025(self, *args):
        pm.polyColorPerVertex(g=0.25)

    def onSetColorG050(self, *args):
        pm.polyColorPerVertex(g=0.5)

    def onSetColorG075(self, *args):
        pm.polyColorPerVertex(g=0.75)

    def onSetColorG100(self, *args):
        pm.polyColorPerVertex(g=1.0)

    def onSetColorB000(self, *args):
        pm.polyColorPerVertex(b=0.0)

    def onSetColorB025(self, *args):
        pm.polyColorPerVertex(b=0.25)

    def onSetColorB050(self, *args):
        pm.polyColorPerVertex(b=0.5)

    def onSetColorB075(self, *args):
        pm.polyColorPerVertex(b=0.75)

    def onSetColorB100(self, *args):
        pm.polyColorPerVertex(b=1.0)

    def onSetColorA000(self, *args):
        pm.polyColorPerVertex(a=0.0)

    def onSetColorA025(self, *args):
        pm.polyColorPerVertex(a=0.25)

    def onSetColorA050(self, *args):
        pm.polyColorPerVertex(a=0.5)

    def onSetColorA075(self, *args):
        pm.polyColorPerVertex(a=0.75)

    def onSetColorA100(self, *args):
        pm.polyColorPerVertex(a=1.0)

    def onDragRed(self, *args):
        v = ui.get_value(self.fs_red)
        pm.polyColorPerVertex(r=v)

    def onDragGreen(self, *args):
        v = ui.get_value(self.fs_green)
        pm.polyColorPerVertex(g=v)

    def onDragBlue(self, *args):
        v = ui.get_value(self.fs_blue)
        pm.polyColorPerVertex(b=v)

    def onDragAlpha(self, *args):
        v = ui.get_value(self.fs_alpha)
        pm.polyColorPerVertex(a=v)


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
