import maya.cmds as cmds
import re

#TODO: toe,head,hips の end 追加処理と方向付け

def getCSPNameFromHIKName(name):
    trans_table = [
      ["Hips" ," hips_bb_"],
      ["LeftUpLeg", "leftupleg_bb_"],
      ["LeftLeg", "leftleg_bb_"],
      ["LeftFoot" ," leftfoot_bb_"],
      ["LeftToeBase", "lefttoebase_bb_"],
      ["RightUpLeg" ," rightupleg_bb_"],
      ["RightLeg" ," rightleg_bb_"],
      ["RightFoot", "rightfoot_bb_"],
      ["RightToeBase" ," righttoebase_bb_"],
      ["Spine", "spine_bb_"],
      ["Spine1" ," spine1_bb_"],
      ["Spine2" ," spine2_bb_"],
      ["LeftShoulder" ," leftshoulder_bb_"],
      ["LeftArm", "leftarm_bb_"],
      ["LeftForeArm", "leftforearm_bb_"],
      ["LeftHand" ," lefthand_bb_"],
      ["LeftHandThumb1" ," lefthandthumb1_bb_"],
      ["LeftHandThumb2" ," lefthandthumb2_bb_"],
      ["LeftHandThumb3" ," lefthandthumb3_bb_"],
      ["LeftHandThumb4" ," lefthandthumb4_bb_"],
      ["LeftHandIndex1" ," lefthandindex1_bb_"],
      ["LeftHandIndex2" ," lefthandindex2_bb_"],
      ["LeftHandIndex3" ," lefthandindex3_bb_"],
      ["LeftHandIndex4" ," lefthandindex4_bb_"],
      ["LeftHandMiddle1", "lefthandmiddle1_bb_"],
      ["LeftHandMiddle2", "lefthandmiddle2_bb_"],
      ["LeftHandMiddle3", "lefthandmiddle3_bb_"],
      ["LeftHandMiddle4", "lefthandmiddle4_bb_"],
      ["LeftHandRing1", "lefthandring1_bb_"],
      ["LeftHandRing2", "lefthandring2_bb_"],
      ["LeftHandRing3", "lefthandring3_bb_"],
      ["LeftHandRing4", "lefthandring4_bb_"],
      ["LeftHandPinky1" ," lefthandpinky1_bb_"],
      ["LeftHandPinky2" ," lefthandpinky2_bb_"],
      ["LeftHandPinky3" ," lefthandpinky3_bb_"],
      ["LeftHandPinky4" ," lefthandpinky4_bb_"],
      ["RightShoulder", "rightshoulder_bb_"],
      ["RightArm" ," rightarm_bb_"],
      ["RightForeArm" ," rightforearm_bb_"],
      ["RightHand", "righthand_bb_"],
      ["RightHandThumb1", "righthandthumb1_bb_"],
      ["RightHandThumb2", "righthandthumb2_bb_"],
      ["RightHandThumb3", "righthandthumb3_bb_"],
      ["RightHandThumb4", "righthandthumb4_bb_"],
      ["RightHandIndex1", "righthandindex1_bb_"],
      ["RightHandIndex2", "righthandindex2_bb_"],
      ["RightHandIndex3", "righthandindex3_bb_"],
      ["RightHandIndex4", "righthandindex4_bb_"],
      ["RightHandMiddle1" ," righthandmiddle1_bb_"],
      ["RightHandMiddle2" ," righthandmiddle2_bb_"],
      ["RightHandMiddle3" ," righthandmiddle3_bb_"],
      ["RightHandMiddle4" ," righthandmiddle4_bb_"],
      ["RightHandRing1" ," righthandring1_bb_"],
      ["RightHandRing2" ," righthandring2_bb_"],
      ["RightHandRing3" ," righthandring3_bb_"],
      ["RightHandRing4" ," righthandring4_bb_"],
      ["RightHandPinky1", "righthandpinky1_bb_"],
      ["RightHandPinky2", "righthandpinky2_bb_"],
      ["RightHandPinky3", "righthandpinky3_bb_"],
      ["RightHandPinky4", "righthandpinky4_bb_"],
      ["Neck", "neck_bb_"],
      ["Head", "head_bb_"],
    ]

    for x in trans_table:
        hikname = x[0]
        cspname = x[1]

        r = re.compile('_' + hikname + '$')
        m = r.search(name)

        if m:
            return cspname

    return name

joints = cmds.ls(selection=True)

for joint in joints:
    oldname = joint
    newname = getCSPNameFromHIKName(oldname)
    cmds.rename(oldname, newname)

