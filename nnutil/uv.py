import maya.cmds as cmds
import maya.mel as mel

import nnutil.core as nu


def align_uv(components=None, axis="U", side="max"):
    if not components:
        components = cmds.ls(selection=True, flatten=True)

        if not components:
            return

    if nu.type_of_component(components[0]) == "edge":
        for edge in components:
            cmds.select(edge, replace=True)
            mel.eval(f"alignUV {side}{axis};")

        cmds.select(components, replace=True)

    if nu.type_of_component(components[0]) == "uv":
        mel.eval(f"alignUV {side}{axis};")

    elif cmds.selectType(q=True, msh=True):
        mel.eval(f"texAlignShells {side}{axis} {{}} \"\";")
