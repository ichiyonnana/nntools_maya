#! python
# coding:utf-8

# マニピュレーター設定ウィンドウ
import maya.cmds as cmds
import maya.mel as mel

class NN_ManipWindow(object):

    def __init__(self):
        self.window = 'NN_ManipWindow'
        self.title = 'NN Manip'
        self.size = (350, 95)

    def create(self):
        if cmds.window('NN_ManipWindow', exists=True):
            cmds.deleteUI('NN_ManipWindow', window=True)
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

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=5)
        self.buttonA = cmds.button(l='World', c=self.onWorld)
        self.buttonA = cmds.button(l='Object', c=self.onObject)
        self.buttonA = cmds.button(l='Component', c=self.onComponent)
        self.buttonA = cmds.button(l='Normal', c=self.onNormal)
        self.buttonA = cmds.button(l='Parent', c=self.onParent)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=2)
        self.buttonA = cmds.button(l='Set Object', c=self.onSetObject)
        self.buttonA = cmds.button(l='Set Component', c=self.onSetComponent)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=7)
        self.buttonA = cmds.button(l='XYZ', c=self.onActiveHandleXYZ)
        self.buttonA = cmds.button(l=' X ', c=self.onActiveHandleX)
        self.buttonA = cmds.button(l=' Y ', c=self.onActiveHandleY)
        self.buttonA = cmds.button(l=' Z ', c=self.onActiveHandleZ)
        self.buttonA = cmds.button(l='Xp', c=self.onActiveHandleXplane)
        self.buttonA = cmds.button(l='Yp', c=self.onActiveHandleYplane)
        self.buttonA = cmds.button(l='Zp', c=self.onActiveHandleZplane)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=4)
        self.buttonA = cmds.button(l='Pin pivot', c=self.onPinOn)
        self.buttonA = cmds.button(l='off', c=self.onPinOff)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=6)
        self.buttonA = cmds.button(l='Keep spacing', c=self.onKeepSpacingOn)
        self.buttonA = cmds.button(l='off', c=self.onKeepSpacingOff)
        self.buttonA = cmds.button(l='Preserve UV', c=self.onPreserveUVOn)
        self.buttonA = cmds.button(l='off', c=self.onPreserveUVOff)
        self.buttonA = cmds.button(l='Preserve Child', c=self.onPreserveChildOn)
        self.buttonA = cmds.button(l='off', c=self.onPreserveChildOff)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=1)
        self.label1 = cmds.text( label='set pivot to neighbor component:' )
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=7)
        self.buttonA = cmds.button(l='edge', c=self.onSetPivtToEdge)
        self.buttonA = cmds.button(l='vtx', c=self.onSetPivtToVertex)
        self.buttonA = cmds.button(l='face', c=self.onSetPivtToFace)
        self.buttonA = cmds.button(l='center', c=self.onSetPivtToCenter)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=3)
        self.buttonA = cmds.button(l='Reset', c=self.onReset)
        cmds.setParent("..")


    def onWorld(self, *args):
        mode = 2
        cmds.manipMoveContext('Move', e=True, mode=mode);
        cmds.manipScaleContext('Scale', e=True, mode=mode);
        mode = 1 # rotate の 2 は Gimbal
        cmds.manipRotateContext('Rotate', e=True, mode=mode);

    def onObject(self, *args):
        mode = 0
        cmds.manipMoveContext('Move', e=True, mode=mode);
        cmds.manipRotateContext('Rotate', e=True, mode=mode);
        cmds.manipScaleContext('Scale', e=True, mode=mode);

    def onComponent(self, *args):
        mode = 10
        cmds.manipMoveContext('Move', e=True, mode=mode);
        cmds.manipRotateContext('Rotate', e=True, mode=mode);
        cmds.manipScaleContext('Scale', e=True, mode=mode);

    def onNormal(self, *args):
        mode = 3
        cmds.manipMoveContext('Move', e=True, mode=mode);
        cmds.manipRotateContext('Rotate', e=True, mode=mode);
        cmds.manipScaleContext('Scale', e=True, mode=mode);

    def onParent(self, *args):
        mode = 1
        cmds.manipMoveContext('Move', e=True, mode=mode);
        cmds.manipRotateContext('Rotate', e=True, mode=mode);
        cmds.manipScaleContext('Scale', e=True, mode=mode);

    def onSetObject(self, *args):
        mel.eval('manipMoveOrient 5')

    def onSetComponent(self, *args):
        mel.eval('manipMoveOrient 4')

    def onKeepSpacingOn(self, *args):
        cmds.manipMoveContext('Move', e=True, snapComponentsRelative=True);

    def onKeepSpacingOff(self, *args):
        cmds.manipMoveContext('Move', e=True, snapComponentsRelative=False);

    def onPinOn(self, *args):
        mel.eval('setTRSPinPivot true')

    def onPinOff(self, *args):
        mel.eval('setTRSPinPivot false')

    def onPreserveUVOn(self, *args):
        mel.eval('setTRSPreserveUVs true')
    def onPreserveUVOff(self, *args):
        mel.eval('setTRSPreserveUVs false')

    def onPreserveChildOn(self, *args):
        mel.eval('setTRSPreserveChildPosition true')
    def onPreserveChildOff(self, *args):
        mel.eval('setTRSPreserveChildPosition false')


    def onActiveHandleXYZ(self, *args):
        mode = 3
        cmds.manipMoveContext('Move', e=True, currentActiveHandle=mode)
        cmds.manipRotateContext('Rotate', e=True, currentActiveHandle=mode)
        cmds.manipScaleContext('Scale', e=True, currentActiveHandle=mode)

    def onActiveHandleX(self, *args):
        mode = 0
        cmds.manipMoveContext('Move', e=True, currentActiveHandle=mode)
        cmds.manipRotateContext('Rotate', e=True, currentActiveHandle=mode)
        cmds.manipScaleContext('Scale', e=True, currentActiveHandle=mode)

    def onActiveHandleY(self, *args):
        mode = 1
        cmds.manipMoveContext('Move', e=True, currentActiveHandle=mode)
        cmds.manipRotateContext('Rotate', e=True, currentActiveHandle=mode)
        cmds.manipScaleContext('Scale', e=True, currentActiveHandle=mode)

    def onActiveHandleZ(self, *args):
        mode = 2
        cmds.manipMoveContext('Move', e=True, currentActiveHandle=mode)
        cmds.manipRotateContext('Rotate', e=True, currentActiveHandle=mode)
        cmds.manipScaleContext('Scale', e=True, currentActiveHandle=mode)

    def onActiveHandleXplane(self, *args):
        mode = 5
        cmds.manipMoveContext('Move', e=True, currentActiveHandle=mode)
        cmds.manipRotateContext('Rotate', e=True, currentActiveHandle=mode)
        cmds.manipScaleContext('Scale', e=True, currentActiveHandle=mode)

    def onActiveHandleYplane(self, *args):
        mode = 6
        cmds.manipMoveContext('Move', e=True, currentActiveHandle=mode)
        cmds.manipRotateContext('Rotate', e=True, currentActiveHandle=mode)
        cmds.manipScaleContext('Scale', e=True, currentActiveHandle=mode)

    def onActiveHandleZplane(self, *args):
        mode = 4
        cmds.manipMoveContext('Move', e=True, currentActiveHandle=mode)
        cmds.manipRotateContext('Rotate', e=True, currentActiveHandle=mode)
        cmds.manipScaleContext('Scale', e=True, currentActiveHandle=mode)

    # 選択コンポーネントに隣接するコンポーネントにピボットを設定する
    # vtx: ピボットポイントのみ設定
    # edge: 位置を変えずに軸を設定
    # face: 位置と方向を設定
    def onSetPivtToEdge(self, *args):
        pass
    def onSetPivtToVertex(self, *args):
        pass
    def onSetPivtToFace(self, *args):
        pass
    def onSetPivtToCenter(self, *args):
        pass


    def onReset(self, *args):
        cmds.resetTool('Move')
        cmds.resetTool('Rotate')
        cmds.resetTool('Scale')
        mel.eval('buildRotateMM')
        mel.eval('buildScaleMM')
        mel.eval('buildTranslateMM')

def showNNManipWindow():
    NN_ManipWindow().create()

def main():
    showNNManipWindow()
