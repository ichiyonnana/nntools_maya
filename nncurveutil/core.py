# ダイアログのテンプレ
# self.window だけユニークならあとはそのままで良い
import maya.cmds as cmds
import maya.mel as mel

import nnutil

window_width = 300
header_width = 50
color_x = (1.0, 0.5, 0.5)
color_y = (0.5, 1.0, 0.5)
color_z = (0.5, 0.5, 1.0)
color_joint = (0.5, 1.0, 0.75)
color_select = (0.5, 0.75, 1.0)
bw_single = 24
bw_double = bw_single*2 + 2

import maya.cmds as cmds
import maya.mel as mel

def make_parallel_plane_to_curve(curve):
    # カーブ選択状態で起動
    curve_str = str(curve)

    # カーブの始点終点中間点取得
    cvs = cmds.getAttr(curve_str + '.cv[*]')
    ci0 = 0
    ci1 = len(cvs)//2
    ci2 = len(cvs)

    # 1x1プレーン作成
    plane1 = cmds.polyPlane(w=1, h=1, sx=1, sy=1)[0]

    #3to3 でアライン
    sel = [
        plane1 + ".vtx[0]",
        plane1 + ".vtx[1]",
        plane1 + ".vtx[3]",
        curve_str + ".cv[%d]" % ci0,
        curve_str + ".cv[%d]" % ci1,
        curve_str + ".cv[%d]" % ci2,
    ]
    cmds.select(sel, replace=True)
    mel.eval("snap3PointsTo3Points(0)")

    # コンストラクションプレーン作成
    plane2 = cmds.plane(s=1)
    cmds.matchTransform(plane2, plane1)
    cmds.rotate(90, 0, 0, plane2, r=True, os=True)

    # プレーン削除
    print(plane1)
    cmds.delete(plane1)

    # コンストラクションプレーン make live
    cmds.makeLive(plane2)


def replace_object(old, new):
    new_name = old
    cmds.delete(old)
    cmds.rename(new, new_name)


class NN_ToolWindow(object):

    def __init__(self):
        self.window = 'NN_CurveUtil'
        self.title = 'NN_CurveUtil'
        self.size = (window_width, 95)

        self.new_curve = None

    def create(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)
        self.window = cmds.window(
            self.window,
            t=self.title,
            widthHeight=self.size,
            resizeToFitChildren=True
        )
        self.layout()
        cmds.showWindow()

    def layout(self):
        self.columnLayout = cmds.columnLayout()

        self.rowLayout1 = cmds.rowLayout( numberOfColumns=16 )
        self.label1 = cmds.text( label='Geo' ,width=header_width)
        self.buttonA = cmds.button(l='make plane', c=self.onMakePlane)
        self.buttonA = cmds.button(l='pencil tool', c=self.onPencilTool)
        self.buttonA = cmds.button(l='replace', c=self.onReplace)
        cmds.setParent("..")

    def onMakePlane(self, *args):
        curve = cmds.ls(selection=True)[0]
        make_parallel_plane_to_curve(curve)

    def onPencilTool(self, *args):
        # ペンシルツール起動
        mel.eval("PencilCurveTool")

    def onReplace(self, *args):
        c1, c2 = cmds.ls(selection=True, flatten=True)
        replace_object(c1, c2)


def showNNToolWindow():
    NN_ToolWindow().create()

def main():
    showNNToolWindow()

if __name__ == "__main__":
    main()