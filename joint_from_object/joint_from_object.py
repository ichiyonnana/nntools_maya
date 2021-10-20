import maya.cmds as cmds
import re

selections = cmds.ls(selection=True)
cmds.select(clear=True)
locators = [obj for obj in selections if cmds.nodeType(obj) == "transform"]
joints = []

# make joint
for obj in locators:
    jnt_name = re.sub(r"^.*\|", "", obj) + "_jnt"
    jnt = cmds.joint(p=(0,0,0), n=jnt_name)
    cmds.matchTransform([jnt, obj], pos=True)
    cmds.select(clear=True)
    joints.append(jnt)

# restruct parent
for obj in locators:
    locator = obj
    jnt = re.sub(r"^.*\|", "", obj) + "_jnt"
    parents = cmds.listRelatives(locator, parent=True, path=True)
    if parents == None:
        continue
    parent_loc = parents[0]
    parent_jnt = re.sub(r"^.*\|", "", parent_loc) + "_jnt"
    if cmds.objExists(parent_jnt):
        cmds.parent(jnt, parent_jnt)

# orient joint
for jnt in joints:
    cmds.joint(jnt, e=True, oj="xyz", secondaryAxisOrient="yup", zso=True)

# restruct scale
for loc in locators:
    loc_trs = cmds.xform(loc, q=True, scale=True, os=True, relative=True)
    if loc_trs != [1.0, 1.0, 1.0]:
        jnt = re.sub(r"^.*\|", "", loc) + "_jnt"
        name = jnt + "_scale"
        scale_group = cmds.group(empty=True, n=name)
        cmds.matchTransform([scale_group, jnt], pos=True, rot=True)
        parents = cmds.listRelatives(jnt, parent=True, path=True)
        if parents != None:
            cmds.parent(scale_group, parents[0])
        cmds.parent(jnt, scale_group)
        cmds.xform(scale_group, scale=loc_trs, os=True)

# match position
for loc in locators:
    jnt = re.sub(r"^.*\|", "", obj) + "_jnt"
    cmds.matchTransform([jnt, obj], pos=True)