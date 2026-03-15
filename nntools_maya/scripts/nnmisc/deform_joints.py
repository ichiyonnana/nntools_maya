"""
ジョイントと頂点が 1:1 になるポリゴンを作成する
ポリゴンをデフォームした後ジョイントを対応する頂点に移動する
"""
import maya.cmds as cmds

import nnutil.core as nu

proxy_obj_name = "jlproxyobj"


def deform_joints_prepare():
    """ジョイントと頂点が 1:1 になるポリゴンを作成する"""
    all_joints = cmds.ls(type="joint")
    positions = [cmds.xform(x, q=True, translation=True, worldSpace=True) for x in all_joints]

    obj_name, shape = cmds.polyCreateFacet(ch=True, tx=1, s=1, p=positions)

    cmds.setAttr(obj_name + ".overrideEnabled", 1)
    cmds.setAttr(obj_name + ".overrideEnabled", 1)
    cmds.setAttr(obj_name + ".overrideShading", 0)
    cmds.setAttr(obj_name + ".overrideTexturing", 0)
    cmds.setAttr(obj_name + ".overridePlayback", 0)

    cmds.rename(obj_name, proxy_obj_name)


def hierarchy_depth(obj_name):
    """DAGの階層の深さを取得する｡ルートは 1 ｡

    Args:
        obj_name (str): オブジェクト名

    Returns:
        int: DAG の深さを表す整数
    """
    return cmds.ls(obj_name, long=True).count("|")


def deform_joints_apply():
    """デフォームされたポリゴンに一致するようにジョイントを対応する頂点に移動する"""
    positions = nu.get_points(proxy_obj_name, space="world")

    all_joints = cmds.ls(type="joint")

    joint_pos_table = {}

    for i in range(len(all_joints)):
        joint_pos_table[all_joints[i]] = positions[i]

    all_joints.sort(key=lambda x: hierarchy_depth(x))

    for joint in all_joints:
        cmds.xform(joint, translation=list(joint_pos_table[joint]), worldSpace=True)
