import maya.cmds as cmds
import maya.mel as mel

ELT_CYLINDER = 0
ELT_PLANE = 1
ELT_CUBE = None
#
elemType = ELT_CYLINDER

def meshElement(type=ELT_CYLINDER):
    """
    各エレメントタイプ毎のエレメント生成
    """

    if(type == ELT_CYLINDER):
        return( cmds.polyCylinder(r=1, h=2, sx=8, sy=1, sz=1, ax=(0,1,0), rcp=0, cuv=3, ch=1)[0] )
    elif(type == ELT_PLANE):
        return( cmds.polyPlane(w=1, h=1, sx=2, sy=2, ax=(0,1,0), cuv=2, ch=1)[0] )
    else:
        return( cmds.polyCylinder(r=1, h=2, sx=8, sy=1, sz=1, ax=(0,1,0), rcp=0, cuv=3, ch=1)[0] )

def setElementAttr(mesh, childJoint, type='cyl'):
    """
    各エレメントタイプ毎のアトリビュートとエクスプレッションの設定
    """

    if(type == ELT_CYLINDER):
        cmds.setAttr('%(mesh)s.translateX' % locals(), 0 )
        cmds.setAttr('%(mesh)s.translateY' % locals(), 0 )
        cmds.setAttr('%(mesh)s.translateZ' % locals(), 0 )
        cmds.setAttr('%(mesh)s.rotateX' % locals(), 0 )
        cmds.setAttr('%(mesh)s.rotateY' % locals(), 0 )
        cmds.setAttr('%(mesh)s.rotateZ' % locals(), -90 )
        expressionCode = '%(mesh)s.scaleY = mag(<<%(childJoint)s.translateX, %(childJoint)s.translateY, %(childJoint)s.translateZ>>) / 2' % locals()
        cmds.expression(s=expressionCode, ae=1, uc="all" )
    elif(type == ELT_PLANE):
        cmds.setAttr('%(mesh)s.translateX' % locals(), 0 )
        cmds.setAttr('%(mesh)s.translateY' % locals(), 0 )
        cmds.setAttr('%(mesh)s.translateZ' % locals(), 0 )
        cmds.setAttr('%(mesh)s.rotateX' % locals(), 0 )
        cmds.setAttr('%(mesh)s.rotateY' % locals(), 0 )
        cmds.setAttr('%(mesh)s.rotateZ' % locals(), 0 )
        expressionCode = '%(mesh)s.scaleX = mag(<<%(childJoint)s.translateX, %(childJoint)s.translateY, %(childJoint)s.translateZ>>)' % locals()
        cmds.expression(s=expressionCode, ae=1, uc="all" )
    else:
        cmds.setAttr('%(mesh)s.translateX' % locals(), 0 )
        cmds.setAttr('%(mesh)s.translateY' % locals(), 0 )
        cmds.setAttr('%(mesh)s.translateZ' % locals(), 0 )
        cmds.setAttr('%(mesh)s.rotateX' % locals(), 0 )
        cmds.setAttr('%(mesh)s.rotateY' % locals(), 0 )
        cmds.setAttr('%(mesh)s.rotateZ' % locals(), -90 )
        expressionCode = '%(mesh)s.scaleY = mag(<<%(childJoint)s.translateX, %(childJoint)s.translateY, %(childJoint)s.translateZ>>) / 2' % locals()
        cmds.expression(s=expressionCode, ae=1, uc="all" )


def main(mode = ELT_CYLINDER):
    elemType = mode
    selections = cmds.ls(selection=True)

    for childJoint in selections:
        try:
            parentJoint = cmds.listRelatives(childJoint, parent=True, path=True)[0]
        except:
            pass
        else:
            # ロケータ-作成
            locator = cmds.spaceLocator()[0]
            locatorShape = cmds.listRelatives(locator, shapes=True, children=True)[0]
            cmds.setAttr('%(locatorShape)s.visibility' % locals(), 0 )

            # ロケータ-のアトリビュートロック
            cmds.setAttr('%(locator)s.sx' % locals(), lock=True)
            cmds.setAttr('%(locator)s.sy' % locals(), lock=True)
            cmds.setAttr('%(locator)s.sz' % locals(), lock=True)

            # 親+子をドライバとしてポイントコンストレイント
            cmds.pointConstraint(childJoint, parentJoint, locator, maintainOffset=False)

            # 子をドライバとしてエイムコンストレイント (constraint axes xyz)
            cmds.aimConstraint(childJoint, locator, skip='none')
            #ロケータの子にシリンダ作成
            mesh = meshElement(elemType)
            cmds.parent(mesh, locator)
            setElementAttr(mesh, childJoint, elemType)
