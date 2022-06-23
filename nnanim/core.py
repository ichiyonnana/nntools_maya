#! python
# coding:utf-8
"""
リグ･アニメーション関連
"""
import pymel.core as pm

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import nnutil.display as nd

window_name = "NN_Anim"


class NN_ToolWindow(object):
    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (300, 220)

        self.is_chunk_open = False

        self.prefix = "NNANM_"
        self.handle_name = self.prefix + "ikHandle"
        self.locator_name = self.prefix + "locator"
        self.curve_name = self.prefix + "curve"

    def create(self):
        if pm.window(self.window, exists=True):
            pm.deleteUI(self.window, window=True)

        # プリファレンスの有無による分岐
        if pm.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = pm.windowPref(self.window, q=True, topLeftCorner=True)
            pm.windowPref(self.window, remove=True)

            # 前回位置に指定したサイズで表示
            pm.window(self.window, t=self.title, maximizeButton=False, minimizeButton=False, topLeftCorner=position, widthHeight=self.size, sizeable=False)

        else:
            # プリファレンスがなければデフォルト位置に指定サイズで表示
            pm.window(self.window, t=self.title, maximizeButton=False, minimizeButton=False, widthHeight=self.size, sizeable=False)

        self.layout()
        pm.showWindow(self.window)

    def layout(self):
        ui.column_layout()

        ui.row_layout()
        ui.header(label="Rig:")
        ui.button(label="IK (Plane)", c=self.onMakeIKHandlePlane)
        ui.button(label="IK (Chain)", c=self.onMakeIKHandleChain)
        ui.button(label="IK (Spline)", c=self.onMakeIKHandleSpline)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.button(label="Delete IK", c=self.onDeleteIK)
        ui.end_layout()

        ui.end_layout()

    def onMakeIKHandlePlane(self, *args):
        """IK (Plane) ボタンクリック"""
        start_joint, end_joint = pm.selected()[0:2]
        handle, effector = pm.ikHandle(startJoint=start_joint, endEffector=end_joint, name=self.handle_name)
        locator = pm.spaceLocator(p=(0, 0, 0), name=self.locator_name)
        p1 = start_joint.getMatrix(worldSpace=True)[3][0:3]
        p2 = end_joint.getMatrix(worldSpace=True)[3][0:3]
        p3 = start_joint.getChildren()[0].getMatrix(worldSpace=True)[3][0:3]
        p = p3 + (p3-p1 + p3-p2) / 2
        locator = pm.spaceLocator(p=(0, 0, 0), absolute=True, name=self.locator_name)
        locator.translate.set(p)
        pm.poleVectorConstraint(locator, handle)

    def onMakeIKHandleChain(self, *args):
        """IK (Chain) ボタンクリック"""
        start_joint, end_joint = pm.selected()[0:2]
        pm.ikHandle(sol="ikSCsolver", startJoint=start_joint, endEffector=end_joint, name=self.handle_name)

    def onMakeIKHandleSpline(self, *args):
        """IK (Spline) ボタンクリック"""
        start_joint, end_joint = pm.selected()[0:2]
        handle, effector, curve = pm.ikHandle(sol="ikSplineSolver", startJoint=start_joint, endEffector=end_joint, name=self.handle_name)
        pm.rename(curve, self.curve_name)
        pm.select(curve)

    def onDeleteIK(self, *args):
        """"""
        handles = pm.ls(self.handle_name + "*")
        pm.delete(handles)

        locators = pm.ls(self.locator_name + "*")
        pm.delete(locators)

        curves = pm.ls(self.curve_name + "*")
        pm.delete(curves)

    def onTest(self, *args):
        """Testハンドラ"""
        pass


def main():
    NN_ToolWindow().create()


if __name__ == "__main__":
    main()
