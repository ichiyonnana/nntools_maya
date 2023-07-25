#! python
# coding:tuf-8
"""
ジョイントと頂点が 1:1 になるポリゴンを作成する
ポリゴンをデフォームした後ジョイントを対応する頂点に移動する
"""

import pymel.core as pm

proxy_obj_name = "jlproxyobj"


def deform_joints_prepare():
    """ジョイントと頂点が 1:1 になるポリゴンを作成する"""
    all_joints = pm.ls(type="joint")
    positions = [x.getTranslation(space="world") for x in all_joints]

    obj_name, shape = pm.polyCreateFacet(ch=True, tx=1, s=1, p=positions)
    obj = pm.PyNode(obj_name)

    obj.overrideEnabled.set(1)
    obj.overrideEnabled.set(1)
    obj.overrideShading.set(0)
    obj.overrideTexturing.set(0)
    obj.overridePlayback.set(0)

    obj.rename(proxy_obj_name)


def hierarchy_depth(obj_name):
    """DAGの階層の深さを取得する｡ルートは 1 ｡

    Args:
        obj_name (str): オブジェクト名

    Returns:
        int: DAG の深さを表す整数
    """
    obj = pm.PyNode(obj_name)

    return obj.longName().count("|")


def deform_joints_apply():
    """デフォームされたポリゴンに一致するようにジョイントを対応する頂点に移動する"""
    obj = pm.PyNode(proxy_obj_name)
    positions = obj.getShape().getPoints(space="world")

    all_joints = pm.ls(type="joint")

    joint_pos_table = {}

    for i in range(len(all_joints)):
        joint_pos_table[all_joints[i].name()] = positions[i]

    all_joints.sort(key=lambda x: hierarchy_depth(x.name()))

    for joint in all_joints:
        joint.setTranslation(joint_pos_table[joint.name()], space="world")
