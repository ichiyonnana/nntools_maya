# coding:utf-8

# 選択されたすべてのジョイントに対してエンドジョイントを作成する

import maya.cmds as cmds
import math

def distance(p1, p2):
    return math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2 + (p2[2]-p1[2])**2)

def vector(p1, p2):
    return (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])

### ベクトルの正規化
def normalize(v):
    norm = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
    if norm != 0:
        return (v[0]/norm, v[1]/norm, v[2]/norm)
    else:
        return (0,0,0)

def isJoint(obj):
    return cmds.objectType(obj, isType="joint")

def printd(s):
    print(s)


def getNewJointName(basename):
    return basename + "_end"

def main():
    # 設定値
    interval = 20  # 選択ジョイントとエンドジョイントの距離


    selections = cmds.ls(selection=True)

    for sel in selections:
        # 親の取得
        parent = cmds.listRelatives(sel, parent=True, path=True)
        # 親が無ければスキップ
        if parent == None:
          next

        # 親・選択オブジェクトがともにジョイントで無ければスキップ
        if not isJoint(sel) or not isJoint(parent):
          next

        # 親と選択オブジェクトのワールド座標取得
        parentPos = cmds.xform(parent, q=True, ws=True, t=True)
        selPos = cmds.xform(sel, q=True, ws=True, t=True)

        # 親->子 方向の単位ベクトル作成
        toChildVector = normalize(vector(parentPos, selPos))

        # 追加ジョイントの位置は 親->子ベクトル 方向 * 設定距離
        endJointAbsPos = (selPos[0] + toChildVector[0]*interval
                            , selPos[1] + toChildVector[1]*interval
                            , selPos[2] + toChildVector[2]*interval)

        # 追加するジョイント名
        newJointName = getNewJointName(sel.decode())

        # ジョイントの追加
        cmds.joint(sel)

        # 追加ジョイントのリネームとアトリビュートの設定
        cmds.joint(name=newJointName, e=True, p=endJointAbsPos)

    # 即座に方向付け出来るように選択を元に戻す
    cmds.select(selections)
