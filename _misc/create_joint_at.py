from bt_createJointAtCustomPivotAxis import *
import maya.cmds as cmds

def main():
    selections = cmds.ls(selection=True, flatten=True)

    for obj in selections:
        cmds.select(clear=True)
        cmds.select(obj)
        bt_createJointAtCustomPivotAxis()

    cmds.select(clear=True)
    cmds.select(selections)