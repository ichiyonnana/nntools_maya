import pymel.core as pm
import maya.mel as mel


def align_uv(components=None, axis="U", side="max"):
    if not components:
        components = pm.ls(selection=True, flatten=True)

        if not components:
            return

    if isinstance(components[0], pm.MeshEdge):
        for edge in components:
            pm.select(edge, replace=True)
            mel.eval(f"alignUV {side}{axis};")

        pm.select(components, replace=True)

    elif isinstance(components[0], pm.MeshUV):
        mel.eval(f"alignUV {side}{axis};")

    elif pm.selectType(q=True, msh=True):
        mel.eval(f"texAlignShells {side}{axis} {{}} \"\";")
