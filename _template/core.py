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

dialog_name = "NN_"


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
        ui.end_layout()

        ui.end_layout()


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
