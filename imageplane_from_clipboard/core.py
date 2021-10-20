#! python
# coding:utf-8

import maya.cmds as cmds
import maya.mel as mel
import re
import datetime
import os
from PySide2 import QtGui

def main():
    filename = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+ ".png"
    currentScene = cmds.file(q=True, sn=True)
    saveDir = re.sub(r'/scenes/.+$', '/images/', currentScene, 1)

    # イメージプレーンの初期幅
    w = 10.0

    try:
        os.mkdir(saveDir)
    except:
        pass

    result = cmds.promptDialog(
            title='create imageplane',
            message='Enter FileName:',
            button=['OK', 'Cancel'],
            defaultButton='OK',
            cancelButton='Cancel',
            dismissString='Cancel')

    if result == 'OK':
        input = cmds.promptDialog(query=True, text=True)
        if input == '':
            filename = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+ ".png"
        else:
            filename = input + '.png'
    else:
        exit

    savePath = saveDir + filename

    cb = QtGui.QClipboard()
    isImage = cb.mimeData().hasImage()

    if isImage:
        cb.image().save(savePath)
        imageplaneShape = mel.eval('imagePlane -width 1 -height 1 -maintainRatio 1 -lookThrough persp -name %(input)s;' % locals())[1]

        mel.eval("AttributeEditor")

        mel.eval('setAttr -type "string" %(imageplaneShape)s.imageName "%(savePath)s";' % locals())
        mel.eval('changeImageSize %(imageplaneShape)s.maintainRatio %(imageplaneShape)s.width %(imageplaneShape)s.height 1;' % locals())
        mel.eval('changeImageSize %(imageplaneShape)s.maintainRatio %(imageplaneShape)s.height %(imageplaneShape)s.width 0;' % locals())
        cx = cmds.getAttr('%(imageplaneShape)s.coverageX' % locals() )
        cy = cmds.getAttr('%(imageplaneShape)s.coverageY' % locals() )
        h = w * cy / cx
        mel.eval('setAttr "%(imageplaneShape)s.width" %(w)s;' % locals())
        mel.eval('setAttr "%(imageplaneShape)s.height" %(h)s;' % locals())
