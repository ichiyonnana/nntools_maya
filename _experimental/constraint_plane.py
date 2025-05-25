import maya.cmds as cmds
import maya.mel as mel
import re
import os

class NN_ToolWindow(object):

    def __init__(self):
        self.window = 'NN_LiveCP'
        self.title = 'NN_LiveCP'
        self.size = (350, 95)

        self.camera = "persp"
        self.target = None
        self.traZRange = 100

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
        self.columnLayout = cmds.columnLayout()

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text( label='camera' )
        self.buttonA = cmds.button(l='Set', c=self.onSetCamera)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text( label='plane' )
        self.buttonA = cmds.button(l='Set', c=self.onSetPlane)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text( label='traZ' )
        self.sliderTraZ = cmds.floatSlider( width=300, min=-1, max=1, dc=self.onChangeTraZ, dgc=self.onRestTraZ)
        self.fieldTraZRange = cmds.floatField( cc=self.onChangeTraZRange )
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.button( label='constrain', c=self.onDoConstraint )
        self.label1 = cmds.button( label='select', c=self.onSelect )
        cmds.setParent("..")

        cmds.floatField(self.fieldTraZRange, e=True, v=self.traZRange)

    def onSetCamera(self, *args):
        pass

    def onSetPlane(self, *args):
        pass

    def onChangeTraZ(self, *args):
        sliderValue = cmds.floatSlider(self.sliderTraZ, q=True, v=True)
        z = sliderValue * self.traZRange
        target = self.target
        cmds.setAttr('%(target)s.translateZ' % locals(), z )

    def onRestTraZ(self, *args):
        cmds.floatSlider(self.sliderTraZ, e=True, v=0)
        self.onChangeTraZ()

    def onChangeTraZRange(self, *args):
        self.traZRange = cmds.floatField(self.fieldTraZRange, q=True, v=True)

    def onDoConstraint(self, *args):
        sel = cmds.ls(selection=True)[0]
        if sel != self.target:
            self.target = sel
            trs = cmds.group(self.target)
            print(self.target)
            cmds.matchTransform(trs, camera, rotation=True)
            cmds.parentConstraint(camera, trs, maintainOffset=True, skipTranslate=['x','y','z'], skipRotate='none')
            cmds.makeLive(sel)

    def onSelect(self, *args):
        cmds.select(self.target)

def showNNToolWindow():
    NN_ToolWindow().create()

showNNToolWindow()
