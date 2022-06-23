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

        self.ik_handle = None
        self.polevector_locator = None
        self.spline_curve = None

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
        ui.header(label="Rig")
        ui.button(label="IK (Plane)", c=self.onMakeIKHandlePlane)
        ui.button(label="IK (Chain)", c=self.onMakeIKHandleChain)
        ui.button(label="IK (Spline)", c=self.onMakeIKHandleSpline)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.button(label="Delete IK", c=self.onDeleteIK)
        ui.end_layout()

        ui.separator(height=ui.height(1))

        ui.row_layout()
        ui.header(label="Picker")
        self.bt_ik_handle = ui.button(label="IK Handle", enable=False, c=self.onPickIKHandle)
        self.bt_pv_locator = ui.button(label="Pole Vector", enable=False, c=self.onPickPoleVector)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        self.bt_spline_curve = ui.button(label="Spline Curve", enable=False, c=self.onPickSplineCurve)
        ui.text(label="CV")
        self.sl_cv_index = ui.int_slider(min=0, max=2, width=ui.width(4), enable=False, cc=self.onChangePickSplineCurveCV, dc=self.onDragPickSplineCurveCV)
        ui.end_layout()

        ui.end_layout()

    def onMakeIKHandlePlane(self, *args):
        """IK (Plane) ボタンクリック

        選択したジョイントから回転プレーンソルバの IK ハンドルを作成する
        """
        start_joint = pm.selected()[0]
        end_joint = pm.selected()[-1]
        handle, effector = pm.ikHandle(startJoint=start_joint, endEffector=end_joint, name=self.handle_name)
        p1 = start_joint.getMatrix(worldSpace=True)[3][0:3]
        p2 = end_joint.getMatrix(worldSpace=True)[3][0:3]
        p3 = start_joint.getChildren()[0].getMatrix(worldSpace=True)[3][0:3]
        p = p3 + (p3-p1 + p3-p2) / 2
        locator = pm.spaceLocator(p=(0, 0, 0), absolute=True, name=self.locator_name)
        locator.translate.set(p)
        pm.poleVectorConstraint(locator, handle)

        self.ik_handle = handle
        self.polevector_locator = locator
        self.spline_curve = None

        ui.enable_ui(self.bt_ik_handle)
        ui.enable_ui(self.bt_pv_locator)
        ui.disable_ui(self.bt_spline_curve)
        ui.disable_ui(self.sl_cv_index)

    def onMakeIKHandleChain(self, *args):
        """IK (Chain) ボタンクリック

        選択したジョイントからチェーンソルバの IK ハンドルを作成する
        """
        start_joint, end_joint = pm.selected()[0:2]
        handle = pm.ikHandle(sol="ikSCsolver", startJoint=start_joint, endEffector=end_joint, name=self.handle_name)

        self.ik_handle = handle
        self.polevector_locator = None
        self.spline_curve = None

        ui.enable_ui(self.bt_ik_handle)
        ui.disable_ui(self.bt_pv_locator)
        ui.disable_ui(self.bt_spline_curve)
        ui.disable_ui(self.sl_cv_index)

    def onMakeIKHandleSpline(self, *args):
        """IK (Spline) ボタンクリック

        選択したジョイントからスプラインIK ハンドルを作成する
        """
        start_joint, end_joint = pm.selected()[0:2]
        handle, effector, curve = pm.ikHandle(sol="ikSplineSolver", startJoint=start_joint, endEffector=end_joint, name=self.handle_name)
        pm.rename(curve, self.curve_name)
        pm.select(curve)
        handle.visibility.set(False)

        self.ik_handle = handle
        self.polevector_locator = None
        self.spline_curve = curve

        n = self.spline_curve.numCVs() - 1
        pm.intSlider(self.sl_cv_index, e=True, max=n)

        ui.disable_ui(self.bt_ik_handle)
        ui.disable_ui(self.bt_pv_locator)
        ui.enable_ui(self.bt_spline_curve)
        ui.enable_ui(self.sl_cv_index)

    def onDeleteIK(self, *args):
        """このツールで作成した全てのオブジェクトを削除する"""
        handles = pm.ls(self.handle_name + "*")
        pm.delete(handles)

        locators = pm.ls(self.locator_name + "*")
        pm.delete(locators)

        curves = pm.ls(self.curve_name + "*")
        pm.delete(curves)

        self.ik_handle = None
        self.polevector_locator = None
        self.spline_curve = None

        ui.disable_ui(self.bt_ik_handle)
        ui.disable_ui(self.bt_pv_locator)
        ui.disable_ui(self.bt_spline_curve)
        ui.disable_ui(self.sl_cv_index)

    def onPickIKHandle(self, *args):
        """最後に作成したIKハンドルの選択"""
        if self.ik_handle:
            pm.select(self.ik_handle)

    def onPickPoleVector(self, *args):
        """最後に作成した回転プレーンソルバIKのポールベクターロケーターを選択する"""
        if self.polevector_locator:
            pm.select(self.polevector_locator)

    def onPickSplineCurve(self, *args):
        """最後に作成したスプラインIKのカーブを選択する"""
        if self.spline_curve:
            pm.select(self.spline_curve)

    def onChangePickSplineCurveCV(self, *args):
        """最後に作成したスプラインIKのカーブCVを選択する"""
        i = ui.get_value(self.sl_cv_index)
        cv = "{}.cv[{}]".format(self.spline_curve.name(), i)
        pm.select(cv)

    def onDragPickSplineCurveCV(self, *args):
        """スプラインIKのカーブCV用スライダーのドラッグハンドラ"""
        self.onChangePickSplineCurveCV()


def main():
    NN_ToolWindow().create()


if __name__ == "__main__":
    main()
