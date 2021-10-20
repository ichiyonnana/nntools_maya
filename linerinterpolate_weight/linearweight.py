# 既存頂点 2 点のウェイトからの線形補間で選択頂点のウェイトを再設定する
import maya.cmds as cmds
import maya.mel as mel

class NN_ToolWindow(object):

    def __init__(self):
        self.window = 'NN_ToolWindow'
        self.title = 'NN Tool'
        self.size = (350, 95)

    def create(self):
        if cmds.window('NN_ToolWindow', exists=True):
            cmds.deleteUI('NN_ToolWindow', window=True)
        self.window = cmds.window(
            self.window,
            t=self.title,
            widthHeight=self.size
        )
        self.layout()
        cmds.showWindow()

    def layout(self):
        self.columnLayout = cmds.columnLayout()

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=4)
        self.sourceVtxName1 = cmds.textField(v="")
        self.buttonA = cmds.button(l='get vtx1', c=self.onGetVtx1)
        cmds.setParent("..")
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=4)
        self.sourceVtxName2 = cmds.textField(v="")
        self.buttonA = cmds.button(l='get vtx2', c=self.onGetVtx2)
        cmds.setParent("..")
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=4)
        self.targetInfluenceName = cmds.textField(v="")
        self.buttonA = cmds.button(l='get influence', c=self.onGetInfluence)
        cmds.setParent("..")
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=4)
        self.buttonA = cmds.button(l='overwrite', c=self.onOverWrite)
        self.buttonA = cmds.button(l='normalize', c=self.onNormalize)
        cmds.setParent("..")


      self.rowLayout1 = cmds.rowLayout(numberOfColumns=4)
        self.sourceVtxName1 = cmds.textField(v="")
        self.buttonA = cmds.button(l='get vtx1', c=self.onGetVtx1)
        cmds.setParent("..")
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=4)
        self.sourceVtxName2 = cmds.textField(v="")
        self.buttonA = cmds.button(l='get vtx2', c=self.onGetVtx2)
        cmds.setParent("..")
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=4)
        self.targetInfluenceName = cmds.textField(v="")
        self.buttonA = cmds.button(l='get influence', c=self.onGetInfluence)
        cmds.setParent("..")
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=4)
        self.buttonA = cmds.button(l='overwrite', c=self.onOverWrite)
        self.buttonA = cmds.button(l='normalize', c=self.onNormalize)

    def onGetVtx1(self, *args):
        pass

    def onGetVtx2(self, *args):
        pass

    def onGetInfluence(self, *args):
        pass

    def onOverWrite(self, *args):
			get vtx1 point
			get vtx1 influence/weight list
			get vtx2 point
			get vtx2 influence/weight list

			get target vertices

			target vertices each
				d1 = distance(p1,p)
				d2 = distance(p2,p)
				e1 = d1/(d1+d2)
				e2 = d2/(d1+d2)
				v1index
				v2index
				for influence in influencelist
					 weightlist[index] = weightlist[v1index] * e1 + weightlist[v2index] * e2

        pass

    def onNormalize(self, *args):
        pass

def showNNToolWindow():
    NN_ToolWindow().create()

showNNToolWindow()