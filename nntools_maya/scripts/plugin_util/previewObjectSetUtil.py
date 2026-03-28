"""previewObjectSet ノード関連の補助機能"""
import re

import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.mel as mel

def add_preview_node_to_all_isolation_set():
    """すべての previewObjectSet ノードをすべての isolation セットへ追加する"""
    # 全ての previewObjectSet ノード 検索
    all_preview_nodes = cmds.ls(type="previewObjectSet")

    if not all_preview_nodes:
        return

    # 全ての isolation セット検索
    all_isolation_sets = [x for x in cmds.ls(type="objectSet") if re.match(r"modelPanel\dViewSelectedSet", x)]

    # isolation セットに previewObjectSet ノード追加
    for set_name in all_isolation_sets:
        cmds.sets(all_preview_nodes, e=True, add=set_name)


def custom_isolate():
    """通常の isolate に追加で add_preview_node_to_all_isolation_set を呼ぶ関数"""
    active_panel = cmds.getPanel(withFocus=True)

    if "modelPanel" in active_panel:
        mel.eval("ToggleIsolateSelect;")

    elif "polyTexturePlacementPanel" in active_panel:
        mel.eval("ToggleUVIsolateViewSelected;")

    else:
        pass
   
    add_preview_node_to_all_isolation_set()
