""" 表示関連
"""
import maya.cmds as cmds


def message(s, do_print=True):
    """ 簡易 inVewMessage """
    cmds.inViewMessage(smg=s, pos="topCenter", bkc="0x00000000", fade=True)

    if do_print:
        print(s)