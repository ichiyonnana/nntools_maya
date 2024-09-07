# coding:utf-8

import re
import maya.cmds as cmds
import pymel.core as pm
import pymel.core.nodetypes as nt
import pymel.core.datatypes as dt

import nnutil.core as nu
import nnutil.display as nd
import nnutil.ui as ui
import nnutil.decorator as deco


class NN_ToolWindow(object):
    window_width = 300

    def __init__(self):
        self.window = 'NormalTools'
        self.title = 'NormalTools'
        self.size = (self.window_width, 95)

        pm.selectPref(trackSelectionOrder=True)

    def create(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)
        self.window = cmds.window(
            self.window,
            t=self.title,
            widthHeight=self.size,
            resizeToFitChildren=True
        )
        self.layout()
        cmds.showWindow()

    def layout(self):
        ui.column_layout()

        ui.end_layout()

    # イベントハンドラ


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
