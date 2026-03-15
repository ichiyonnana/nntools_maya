"""
リグ･アニメーション関連
"""
import re

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import nnutil.display as nd

window_name = "NN_Anim"


def get_num_cv(curve):
    """カーブから CV の数を取得する｡

    Args:
        curve (str): nurbsCurve ノードの名称
    """
    spans = cmds.getAttr(curve + ".spans")
    degree = cmds.getAttr(curve + ".degree")
    cvs = spans + degree

    return cvs


class NN_ToolWindow(object):    
    prefix = "NNANM_"
    handle_name = prefix + "ikHandle"
    locator_name = prefix + "locator"
    curve_name = prefix + "curve"

    hair_system_name = "NNANIMHS_hairSystem"
    hair_system_grp_name = "NNANIMHS_hairSystemGrp"
    nucleus_name = "NNANIMHS_nucleus"
    hair_curves_grp_name = "NNANIMHS_hairSystemGrpOutputCurves"
    hair_curve_name = "NNANIMHS_dynamicscurve"
    base_curve_name = "NNANIMHS_basecurve"
    hair_follicle_grp_name = "NNANIMHS_hairSystemGrpFollicles"
    follicle_name = "NNANIMHS_follicle"
    hair_ik_grp_name = "NNANIMHS_objects"

    dup_prefix = "dup_"

    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (300, 220)

        self.is_chunk_open = False

        self.ik_handle = None
        self.polevector_locator = None
        self.spline_curve = None

        self.hair_system = None
        self.nucleus = None

        if cmds.objExists(self.hair_system_name):
            self.hair_system = self.hair_system_name

        if cmds.objExists(self.nucleus_name):
            self.nucleus = self.nucleus_name

    def create(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)

        # プリファレンスの有無による分岐
        if cmds.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = cmds.windowPref(self.window, q=True, topLeftCorner=True)
            cmds.windowPref(self.window, remove=True)

            # 前回位置に指定したサイズで表示
            cmds.window(
                self.window,
                t=self.title,
                maximizeButton=False,
                minimizeButton=False,
                topLeftCorner=position,
                widthHeight=self.size,
                sizeable=False,
                resizeToFitChildren=True
                )

        else:
            # プリファレンスがなければデフォルト位置に指定サイズで表示
            cmds.window(
                self.window,
                t=self.title,
                maximizeButton=False,
                minimizeButton=False,
                widthHeight=self.size,
                sizeable=False,
                resizeToFitChildren=True
                )

        self.layout()
        cmds.showWindow(self.window)

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
        ui.button(label="IK (Hair)", c=self.onMakeIKHandleHair)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.button(label="Delete IK", c=self.onDeleteIK)
        ui.button(label="Interactive", c=self.onInteractivePlayback, dgc=self.onInteractivePlaybackCurrentFrame)
        ui.end_layout()

        ui.separator(height=ui.height(1))

        ui.row_layout()
        ui.header(label="Collider")
        ui.button(label="Set to Passive", c=self.onSetToPassiveCollider)
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
        start_joint = cmds.ls(selection=True)[0]
        end_joint = cmds.ls(selection=True)[-1]
        start_joint_child = cmds.listRelatives(start_joint, children=True)[0]
        handle, effector = cmds.ikHandle(startJoint=start_joint, endEffector=end_joint, name=self.handle_name)
        p1 = om.MVector(cmds.xform(start_joint, q=True, worldSpace=True, translation=True)[3][0:3])
        p2 = om.MVector(cmds.xform(end_joint, q=True, worldSpace=True, translation=True)[3][0:3])
        p3 = om.MVector(cmds.xform(start_joint_child, q=True, worldSpace=True, translation=True)[3][0:3])
        p = p3 + (p3-p1 + p3-p2) / 2
        locator = cmds.spaceLocator(p=(0, 0, 0), absolute=True, name=self.locator_name)
        cmds.setAttr(locator + ".translate", *p)
        cmds.poleVectorConstraint(locator, handle)

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
        start_joint, end_joint = cmds.ls(selection=True)[0:2]
        handle = cmds.ikHandle(sol="ikSCsolver", startJoint=start_joint, endEffector=end_joint, name=self.handle_name)

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
        start_joint, end_joint = cmds.ls(selection=True)[0:2]
        span = 2
        handle, effector, curve = cmds.ikHandle(sol="ikSplineSolver", startJoint=start_joint, endEffector=end_joint, name=self.handle_name, numSpans=span)
        curve = cmds.rename(curve, self.curve_name)
        cmds.select(curve)
        cmds.setAttr(handle + ".visibility", False)

        self.ik_handle = handle
        self.polevector_locator = None
        self.spline_curve = curve

        n = self.spline_curve.numCVs() - 1
        cmds.intSlider(self.sl_cv_index, e=True, max=n)

        ui.disable_ui(self.bt_ik_handle)
        ui.disable_ui(self.bt_pv_locator)
        ui.enable_ui(self.bt_spline_curve)
        ui.enable_ui(self.sl_cv_index)

    def _create_hair_system(self):
        """HiarSystem を作成する｡すでに存在する場合は何もしない
        アトリビュートの接続は
        """
        if cmds.objExists(self.hair_system_name):
            self.hair_system = self.hair_system_name
        else:
            self.hair_system = cmds.createNode("hairSystem", name=self.hair_system_name, skipSelect=True)
            parent = cmds.listRelatives(self.hair_system, parent=True)[0]
            parent = cmds.rename(parent, self.hair_system_grp_name)

        if cmds.objExists(self.nucleus_name):
            self.nucleus = self.nucleus_name
        else:
            self.nucleus = cmds.createNode("nucleus", name=self.nucleus_name, skipSelect=True)

        time_node = "time1"
        cmds.connectAttr(time_node + ".outTime", self.hair_system + ".currentTime")
        cmds.connectAttr(time_node + ".outTime", self.nucleus + ".currentTime")
        cmds.connectAttr(self.nucleus + ".outputObjects[0]", self.hair_system + ".nextState")
        cmds.connectAttr(self.nucleus + ".startFrame", self.hair_system + ".startFrame")
        cmds.connectAttr(self.hair_system + ".currentState", self.nucleus + ".inputActive[0]")
        cmds.connectAttr(self.hair_system + ".startState", self.nucleus + ".inputActiveStart[0]")

        # パラメーターの設定 (暫定)
        cmds.setAttr(self.nucleus + ".timeScale", 10)

        cmds.setAttr(self.hair_system + ".startCurveAttract", 0)
        cmds.setAttr(self.hair_system + ".drag", 0)
        cmds.setAttr(self.hair_system + ".motionDrag", 0.1)
        cmds.setAttr(self.hair_system + ".bendResistance", 0.01)

        cmds.setAttr(self.hair_system + ".active", 1)

    def get_duplicated_joint_name(self, name):
        """"""
        base_name = re.sub(r".*\|", "", name)

        return self.dup_prefix + base_name

    def onMakeIKHandleHair(self, *args):
        """nHair をハンドルとしたスプラインIKを作成する
        """
        selection = cmds.ls(selection=True)

        if len(selection) < 2:
            print("select 2 joints ")
            return

        start_joint, end_joint = cmds.ls(selection=True)[0:2]

        # IK 開始ジョイントの親から複製してリネーム
        parent_joint = (cmds.listRelatives(start_joint, parent=True) or [None])[0]
        if parent_joint:
            # start_joint に親がある場合
            dup_parent_joint = cmds.duplicate(parent_joint)[0]
            parent_joint_name = cmds.ls(parent_joint, long=True)[0]
            dup_parent_joint = cmds.rename(dup_parent_joint, self.get_duplicated_joint_name(parent_joint_name))
            dup_tree = cmds.listRelatives(dup_parent_joint, allDescendents=True, fullPath=True)

        else:
            # start_joint に親がない場合
            dup_parent_joint = cmds.createNode("joint")
            dup_start_joint = cmds.duplicate(start_joint)[0]
            cmds.parent(dup_start_joint, dup_parent_joint)
            dup_parent_joint = cmds.rename(dup_parent_joint, "dup_root")
            dup_start_joint = cmds.rename(dup_start_joint, start_joint)
            dup_tree = cmds.listRelatives(dup_parent_joint, allDescendents=True, fullPath=True)

        for joint in dup_tree:
            joint_name = cmds.ls(joint, long=True)[0]
            cmds.rename(joint, self.get_duplicated_joint_name(joint_name))

        # 複製ジョイントを非表示にする
        cmds.setAttr(dup_parent_joint + ".visibility", False)

        # 複製ジョイントに splineIK を作成
        dup_start_joint = self.get_duplicated_joint_name(start_joint)
        dup_end_joint = self.get_duplicated_joint_name(end_joint)
        span = 10
        # cmds.curve(d=2, p=[(),(),()])
        handle, effector, base_curve = cmds.ikHandle(sol="ikSplineSolver", startJoint=dup_start_joint, endEffector=dup_end_joint, name=self.handle_name, numSpans=span)
        base_curve = cmds.rename(base_curve, self.base_curve_name)

        # カーブをnHairダイナミクスに変換
        self._create_hair_system()
        cmds.select([base_curve, self.hair_system], self.hair_system, replace=True)
        mel.eval('makeCurvesDynamic 2 { "0", "0", "1", "1", "0"};')
        cmds.setAttr(base_curve + ".visibility", False)
        hair_curve = cmds.listRelatives(self.hair_curves_grp_name, children=True)[-1]

        hair_curve = cmds.rename(hair_curve, self.hair_curve_name)

        # follicle の固定を根元だけに変更
        follicle = cmds.listRelatives(base_curve, parent=True)[0]
        follicle_shape = cmds.listRelatives(follicle, shapes=True)[0]
        cmds.setAttr(follicle_shape + ".pointLock", 1)
        follicle = cmds.rename(follicle, self.follicle_name)
        follicle_shape = cmds.listRelatives(follicle, shapes=True)[0]

        # シミュレーションされるカーブを IKHandle に接続
        hair_curve_shape = cmds.listRelatives(hair_curve, shapes=True)[0]
        cmds.connectAttr(hair_curve_shape + ".worldSpace", handle + ".inCurve", force=True)
        cmds.setAttr(handle + ".visibility", False)

        # グループにまとめる
        if not cmds.objExists(self.hair_ik_grp_name):
            cmds.createNode("transform", name=self.hair_ik_grp_name)

        cmds.parent(handle, self.hair_ik_grp_name)
        cmds.parent(self.hair_system_grp_name, self.hair_ik_grp_name)
        cmds.parent(self.nucleus_name, self.hair_ik_grp_name)
        cmds.parent(self.hair_curves_grp_name, self.hair_ik_grp_name)
        cmds.parent(dup_parent_joint, self.hair_ik_grp_name)

        # オリジナルジョイントから複製ジョイントへペアレントコンストレイン作成
        if parent_joint:
            cmds.parentConstraint(parent_joint, dup_parent_joint, maintainOffset=True)

        # 複製ジョイントから rotate を接続
        start_depth = cmds.ls(start_joint, long=True)[0].count("|")
        end_depth = cmds.ls(end_joint, long=True)[0].count("|")

        for i in range(start_depth, end_depth+1):
            end_joint_fullpath = cmds.ls(end_joint, long=True)[0]
            orig_joint_name = "|".join(end_joint_fullpath.split("|")[1:i+1])
            dup_joint_name = self.get_duplicated_joint_name(orig_joint_name)
            cmds.connectAttr(dup_joint_name + ".rotate", orig_joint_name + ".rotate")

        # follicle 関連のアトリビュート接続
        cmds.connectAttr(dup_start_joint + ".worldMatrix", follicle_shape + ".inputWorldMatrix")
        base_curve_shape = cmds.listRelatives(base_curve, shapes=True)[0]
        cmds.connectAttr(base_curve_shape + ".local", follicle_shape + ".startPosition", force=True)
        cmds.connectAttr(base_curve + ".worldMatrix", follicle_shape + ".startPositionMatrix", force=True)
        cmds.connectAttr(follicle_shape + ".outRotate", follicle + ".rotate")
        cmds.connectAttr(follicle_shape + ".outTranslate", follicle + ".translate")

        # UI の更新
        self.ik_handle = handle
        self.polevector_locator = None
        self.spline_curve = hair_curve
        spline_curve_shape = cmds.listRelatives(self.spline_curve, shapes=True)[0]

        n = get_num_cv(self.spline_curve) - 1
        cmds.intSlider(self.sl_cv_index, e=True, max=n)

        ui.disable_ui(self.bt_ik_handle)
        ui.disable_ui(self.bt_pv_locator)
        ui.enable_ui(self.bt_spline_curve)
        ui.enable_ui(self.sl_cv_index)

    def onDeleteIK(self, *args):
        """このツールで作成した全てのオブジェクトを削除する"""
        handles = cmds.ls(self.handle_name + "*")
        cmds.delete(handles)

        locators = cmds.ls(self.locator_name + "*")
        cmds.delete(locators)

        curves = cmds.ls(self.curve_name + "*")
        cmds.delete(curves)

        hair_objects = self.hair_ik_grp_name
        cmds.delete(hair_objects)

        follicles = cmds.ls(self.follicle_name + "*")
        cmds.delete(follicles)

        hair_curves = cmds.ls(self.hair_curve_name + "*")
        cmds.delete(hair_curves)

        self.ik_handle = None
        self.polevector_locator = None
        self.spline_curve = None

        ui.disable_ui(self.bt_ik_handle)
        ui.disable_ui(self.bt_pv_locator)
        ui.disable_ui(self.bt_spline_curve)
        ui.disable_ui(self.sl_cv_index)

    def onInteractivePlayback(self, *arg):
        """Interactive Playback を実行｡カレントタイムはリセットする"""
        cmds.currentTime(0)
        mel.eval("InteractivePlayback")

    def onInteractivePlaybackCurrentFrame(self, *arg):
        """Interactive Playback をカレントタイムを維持して実行"""
        mel.eval("InteractivePlayback")

    def onSetToPassiveCollider(self, *args):
        """選択オブジェクトをコライダーに設定する"""
        selection = cmds.ls(selection=True)

        if selection:
            for obj in selection:
                shape = cmds.listRelatives(obj, shapes=True)[0]
                target = shape if shape else obj

                if target:
                    if cmds.objectType(target, isType="mesh"):
                        mel.eval("makeCollideNCloth")

                    rigid = None
                    shape_outputs = cmds.listConnections(shape, destination=True)
                    for output in shape_outputs:
                        output_shape = (cmds.listRelatives(output, shapes=True) or [None])[0]

                        if output_shape and cmds.objectType(isAType="nRigid"):
                            rigid = output_shape
                            break

                    cmds.connectAttr(rigid + ".currentState", self.nucleus + ".inputPassive[0]", force=True)
                    cmds.connectAttr(rigid + ".startState", self.nucleus + ".inputPassiveStart[0]", force=True)

    def onPickIKHandle(self, *args):
        """最後に作成したIKハンドルの選択"""
        if self.ik_handle:
            cmds.select(self.ik_handle)

    def onPickPoleVector(self, *args):
        """最後に作成した回転プレーンソルバIKのポールベクターロケーターを選択する"""
        if self.polevector_locator:
            cmds.select(self.polevector_locator)

    def onPickSplineCurve(self, *args):
        """最後に作成したスプラインIKのカーブを選択する"""
        if self.spline_curve:
            cmds.select(self.spline_curve)

    def onChangePickSplineCurveCV(self, *args):
        """最後に作成したスプラインIKのカーブCVを選択する"""
        if self.spline_curve:
            i = ui.get_value(self.sl_cv_index)
            cv = f"{self.spline_curve}.cv[{i}]"
            cmds.select(cv)

    def onDragPickSplineCurveCV(self, *args):
        """スプラインIKのカーブCV用スライダーのドラッグハンドラ"""
        self.onChangePickSplineCurveCV()


def main():
    NN_ToolWindow().create()


if __name__ == "__main__":
    main()
