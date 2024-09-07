import maya.cmds as cmds
import maya.mel as mel
import pymel.core as pm


def get_selection(**kwargs):
    """ [cmds]

    Returns:
        [type]: [description]
    """
    return cmds.ls(selection=True, flatten=True, **kwargs)


def selected(**kwargs):
    """ [pm] flatten を有効にした pm.selected()

    Returns:
        [type]: [description]
    """
    return pm.selected(flatten=True, **kwargs)