# 頂点ロック関連

import maya.cmds as cmds

def lock_selected_vtx():
    """選択頂点をロック"""
    selections = cmds.ls(selection=True)

    for vtx in selections:
        doLock = True
        attr_str = "%(vtx)s.px" % locals()
        cmds.setAttr(attr_str, lock=doLock)
        attr_str = "%(vtx)s.py" % locals()
        cmds.setAttr(attr_str, lock=doLock)
        attr_str = "%(vtx)s.pz" % locals()
        cmds.setAttr(attr_str, lock=doLock)

    msg = "lock selected vtx"
    cmds.inViewMessage(smg=msg, pos="topCenter", bkc="0x00000000", fade=True)

def unlock_selected_vtx():
    """選択をアンロック、選択していなければ全アンロック"""
    selections = cmds.ls(selection=True)
    if len(selections) > 0:
        for vtx in selections:
            doLock = False
            attr_str = "%(vtx)s.px" % locals()
            cmds.setAttr(attr_str, lock=doLock)
            attr_str = "%(vtx)s.py" % locals()
            cmds.setAttr(attr_str, lock=doLock)
            attr_str = "%(vtx)s.pz" % locals()
            cmds.setAttr(attr_str, lock=doLock)
    else:
        cmds.SelectAll()

        for vtx in all_vtx:
            doLock = False
            attr_str = "%(vtx)s.px" % locals()
            cmds.setAttr(attr_str, lock=doLock)
            attr_str = "%(vtx)s.py" % locals()
            cmds.setAttr(attr_str, lock=doLock)
            attr_str = "%(vtx)s.pz" % locals()
            cmds.setAttr(attr_str, lock=doLock)

    msg = "unlock selected vtx"
    cmds.inViewMessage(smg=msg, pos="topCenter", bkc="0x00000000", fade=True)


def lock_unselected_vtx():
    """非選択頂点をロックし、選択頂点はアンロック"""
    selections = cmds.ls(selection=True)
    cmds.InvertSelection()

    unselections = cmds.ls(selection=True)
    for vtx in unselections:
        doLock = True
        attr_str = "%(vtx)s.px" % locals()
        cmds.setAttr(attr_str, lock=doLock)
        attr_str = "%(vtx)s.py" % locals()
        cmds.setAttr(attr_str, lock=doLock)
        attr_str = "%(vtx)s.pz" % locals()
        cmds.setAttr(attr_str, lock=doLock)

    cmds.select(cl=True)
    for vtx in selections:
        cmds.select(vtx, add=True)

    for vtx in selections:
        doLock = False
        attr_str = "%(vtx)s.px" % locals()
        cmds.setAttr(attr_str, lock=doLock)
        attr_str = "%(vtx)s.py" % locals()
        cmds.setAttr(attr_str, lock=doLock)
        attr_str = "%(vtx)s.pz" % locals()
        cmds.setAttr(attr_str, lock=doLock)

    msg = "lock unselected vtx"
    cmds.inViewMessage(smg=msg, pos="topCenter", bkc="0x00000000", fade=True)
