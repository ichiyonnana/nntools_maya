#! python
# coding:utf-8

# ダイアログのテンプレ
# self.window だけユニークならあとはそのままで良い
import re
import os
import sys
import traceback

import maya.cmds as cmds
import maya.mel as mel

import nnutil

window_width = 600
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
        self.window = 'NN_Launcher'
        self.title = 'NN_Launcher'
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

        self.rowLayout1 = cmds.rowLayout( numberOfColumns=16 )
        self.label1 = cmds.text( label='NNTools' ,width=header_width)
        self.bt_ = cmds.button(l='Mirror', c=self.onMirror, width=bw_double)
        self.bt_ = cmds.button(l='Curve', c=self.onCurve, width=bw_double)
        self.bt_ = cmds.button(l='EdgeRing', c=self.onEdgeRing, width=bw_double)
        self.bt_ = cmds.button(l='Skin', c=self.onSkin, width=bw_double)
        self.bt_ = cmds.button(l='Transform', c=self.onTransform, width=bw_double)
        self.bt_ = cmds.button(l='UV', c=self.onUV, width=bw_double)
        self.bt_ = cmds.button(l='Subdiv', c=self.onSubdiv, width=bw_double)
        self.bt_ = cmds.button(l='Manip', c=self.onManip, width=bw_double)
        cmds.setParent("..")

        cmds.separator(width=window_width)

    def onMirror(self, *args):
        import nnmirror
        nnmirror.main()

    def onCurve(self, *args):
        import align_edges_on_curve
        align_edges_on_curve.main()

    def onEdgeRing(self, *args):
        import align_edgering_length
        align_edgering_length.main()

    def onSkin(self, *args):
        import nnskin
        nnskin.main()

    def onSubdiv(self, *args):
        import nnsubdiv
        nnsubdiv.main()

    def onTransform(self, *args):
        import nntransform
        nntransform.main()

    def onUV(self, *args):
        import nnuvtoolkit
        nnuvtoolkit.main()

    def onManip(self, *args):
        import nnmanip
        nnmanip.main()




def showNNToolWindow():
    NN_ToolWindow().create()

def main():
    showNNToolWindow()

if __name__ == "__main__":
    main()