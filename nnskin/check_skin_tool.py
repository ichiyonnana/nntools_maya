#! python
# coding:utf-8
"""

"""
import maya.cmds as cmds
import maya.mel as mel
import pymel.core as pm
import pymel.core.nodetypes as nt

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import nnutil.display as nd
import nnutil.misc as nm


dialog_name = "NN_SkinChecker"

default_translate_factor = 10
default_rotate_factor = 180


def is_weight_paint_mode():
    return pm.currentCtx() == "artAttrSkinContext"


def activate_weight_paint_mode():
    pm.setToolTo("artAttrSkinContext")


def activate_select_mode():
    pm.setToolTo("selectSuperContext")


def focus_object():
    pass


def weight_paint_mode_with_selected_joint(joint=None, meshes=[]):
    """選択したメッシュに対して選択したジョイントがアクティブな状態でウェイトペイントモードに入る"""
    if not joint:
        joint = [x for x in pm.selected(flatten=True) if isinstance(x, nt.Joint)][0]

    if not meshes:
        meshes = [x for x in pm.selected(flatten=True) if isinstance(x, nt.Transform)]

    if joint and meshes:
        print("select: ", meshes)
        pm.select(meshes, replace=True)
        mel.eval("ArtPaintSkinWeightsToolOptions")
        mel.eval('artSkinInflListChanging "%s" 1' % joint.name())
        mel.eval("artSkinInflListChanged artAttrSkinPaintCtx")


def change_paint_target_influence(joint):
    mel.eval('artSkinInflListChanging "%s" 1' % joint.name())
    mel.eval("artSkinInflListChanged artAttrSkinPaintCtx")


@deco.repeatable
def move_cursor(nnskin_window, offset=0, focus=False, reset=False):
    """現在のジョイントを変更する.

    Args:
        nnskin_window(object)
        offset (int): カーソルの移動方向｡0で移動無し､負数で一つ前､正数で一つ後へ移動. Defaults to 0.
        reset (bool): カーソル位置をリセットするかどうか. True でカーソルがリセットされ､その場合 offset は無視される. Defaults to False.
        focus (bool): 選択されたジョイントをフォーカスするかどうか. Defaults to False.
    """
    paint_mode = is_weight_paint_mode()

    # カーソルのリセット､もしくは移動
    if reset:
        nnskin_window.cursor = 0
    
    else:
        nnskin_window.cursor += offset

    # インデックス範囲外になったときにインデックスをループさせる
    if nnskin_window.cursor < 0 or len(nnskin_window.joints) <= nnskin_window.cursor:
        nd.message("finish")
        if offset < 0:
            nnskin_window.cursor = len(nnskin_window.joints) - 1
        elif offset >0:
            nnskin_window.cursor = 0

    # UI 更新
    ui.set_value(nnskin_window.text_current, nnskin_window.current_joint())

    # ジョイントの選択､もしくはペイントモードの編集対象の変更
    if paint_mode:
        change_paint_target_influence(joint=nnskin_window.current_joint())

    else:
        pm.select(nnskin_window.current_joint())

    # ジョイントのフォーカス
    if focus:
        focus_object(nnskin_window.current_joint())


class TRS():
    def __init__(self, obj):
        self.translateX = obj.translateX.get()
        self.translateY = obj.translateY.get()
        self.translateZ = obj.translateZ.get()
        self.rotateX = obj.rotateX.get()
        self.rotateY = obj.rotateY.get()
        self.rotateZ = obj.rotateZ.get()
        self.scaleX = obj.scaleX.get()
        self.scaleY = obj.scaleY.get()
        self.scaleZ = obj.scaleZ.get()


class NN_ToolWindow(object):
    def __init__(self):
        self.window = dialog_name
        self.title = dialog_name
        self.size = (ui.width(11.5), ui.height(13.5))

        self.root_joint = None
        self.joints = []
        self.cursor = 0
        self.fit_factor = 0.1

        self.neutral_trs = []
        self.meshes = []

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
        ui.header(label="Set")
        ui.button(label="Root", c=self.onSetRoot)
        ui.button(label="Joints", c=self.onSetJoints)
        ui.button(label="Meshes", c=self.onSetMeshes)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.text(label="Root Joint :", width=ui.width3)
        self.text_root = ui.text(label="None", width=ui.width3)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.text(label="Current Joint :", width=ui.width3)
        self.text_current = ui.text(label="None", width=ui.width3)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.text(label="Meshes :", width=ui.width3)
        self.text_meshes = ui.text(label="None", width=ui.width3)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.button(label="Prev", c=self.onPrevNoFocus, dgc=self.onPrevFocus)
        ui.button(label="Select", c=self.onSelectNoFocus, dgc=self.onSelectFocus)
        ui.button(label="Next", c=self.onNextNoFocus, dgc=self.onNextFocus)
        ui.button(label="Reset", c=self.onResetNoFocus, dgc=self.onResetFocus)
        ui.end_layout()

        ui.separator(height=ui.height1)

        ui.row_layout()
        ui.header(label="Translate")
        ui.text(label="X", bgc=ui.color_x)
        self.fs_tra_x = ui.float_slider(min=-1.0, max=1.0, value=0, width=ui.width6, dc=self.onDragTranslateX, cc=self.onChangeTranslateX)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.text(label="Y", bgc=ui.color_y)
        self.fs_tra_y = ui.float_slider(min=-1.0, max=1.0, value=0, width=ui.width6, dc=self.onDragTranslateY, cc=self.onChangeTranslateY)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.text(label="Z", bgc=ui.color_z)
        self.fs_tra_z = ui.float_slider(min=-1.0, max=1.0, value=0, width=ui.width6, dc=self.onDragTranslateZ, cc=self.onChangeTranslateZ)
        ui.end_layout()

        ui.separator(height=ui.height1)

        ui.row_layout()
        ui.header(label="Rotate")
        ui.text(label="X", bgc=ui.color_x)
        self.fs_rot_x = ui.float_slider(min=-1.0, max=1.0, value=0, width=ui.width6, dc=self.onDragRotateX, cc=self.onChangeRotateX)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.text(label="Y", bgc=ui.color_y)
        self.fs_rot_y = ui.float_slider(min=-1.0, max=1.0, value=0, width=ui.width6, dc=self.onDragRotateY, cc=self.onChangeRotateY)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.text(label="Z", bgc=ui.color_z)
        self.fs_rot_z = ui.float_slider(min=-1.0, max=1.0, value=0, width=ui.width6, dc=self.onDragRotateZ, cc=self.onChangeRotateZ)
        ui.end_layout()

        ui.separator(height=ui.height1)

        ui.row_layout()
        ui.header(label="")
        ui.button(label="Gradation", c=self.onGradation)
        ui.button(label="Animation", c=self.onAnimation)
        ui.button(label="PaintMode", c=self.onPaintMode)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.button(label="SelHilight 0 [1]", c=self.onSelHilightingFalse, dgc=self.onSelHilightingTrue)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="factor")
        ui.text(label="Tra", width=ui.width1)
        self.eb_translate_factor = ui.eb_int(v=default_translate_factor)
        ui.text(label="Rot", width=ui.width1)
        self.eb_rotate_factor = ui.eb_int(v=default_rotate_factor)
        ui.end_layout()

        ui.end_layout()

    def current_joint(self):
        return self.joints[self.cursor]

    def translate_factor(self):
        return ui.get_value(self.eb_translate_factor)

    def rotate_factor(self):
        return ui.get_value(self.eb_rotate_factor)

    def onSetRoot(self, *args):        
        # 選択以下にある全てのジョイントを取得
        current_selection = pm.selected(flatten=True)
        pm.select(hierarchy=True)
        all_joints = [x for x in pm.selected(flatten=True) if isinstance(x, nt.Joint)]
        pm.select(current_selection)

        self.root_joint = all_joints[0]
        self.joints = all_joints

        self.neutral_trs = [None] * len(self.joints)

        for i, joint in enumerate(self.joints):
            self.neutral_trs[i] = TRS(joint)

        self.meshes = [x.getParent() for x in pm.listRelatives(self.root_joint, allDescendents=True, type="mesh")]

        ui.set_value(self.text_root, self.root_joint)

    def onSetJoints(self, *args):
        selection = pm.selected(flatten=True, type="joint")
        if selection:
            self.joints = selection
            self.root_joint = self.joints[0]

        self.neutral_trs = [None] * len(self.joints)

        for i, joint in enumerate(self.joints):
            self.neutral_trs[i] = TRS(joint)

        ui.set_value(self.text_root, self.root_joint)

    def onSetMeshes(self, *args):
        selection = pm.selected(flatten=True)
        if selection:
            self.meshes = selection

        ui.set_value(self.text_meshes, str(len(self.meshes)))

    def onDragTranslateX(self, *args):
        self.onChangeTranslateX(*args)

    def onDragTranslateY(self, *args):
        self.onChangeTranslateY(*args)

    def onDragTranslateZ(self, *args):
        self.onChangeTranslateZ(*args)

    def onDragRotateX(self, *args):
        self.onChangeRotateX(*args)

    def onDragRotateY(self, *args):
        self.onChangeRotateY(*args)

    def onDragRotateZ(self, *args):
        self.onChangeRotateZ(*args)

    def onChangeTranslateX(self, *args):
        if ui.is_shift():
            ui.set_value(self.fs_tra_x, value=0)

        neutral = self.neutral_trs[self.cursor].translateX
        v = ui.get_value(self.fs_tra_x)
        self.current_joint().translateX.set(neutral + v * self.translate_factor())

    def onChangeTranslateY(self, *args):
        if ui.is_shift():
            ui.set_value(self.fs_tra_y, value=0)

        neutral = self.neutral_trs[self.cursor].translateY
        v = ui.get_value(self.fs_tra_y)
        self.current_joint().translateY.set(neutral + v * self.translate_factor())

    def onChangeTranslateZ(self, *args):
        if ui.is_shift():
            ui.set_value(self.fs_tra_z, value=0)

        neutral = self.neutral_trs[self.cursor].translateZ
        v = ui.get_value(self.fs_tra_z)
        self.current_joint().translateZ.set(neutral + v * self.translate_factor())

    def onChangeRotateX(self, *args):
        if ui.is_shift():
            ui.set_value(self.fs_rot_x, value=0)

        neutral = self.neutral_trs[self.cursor].rotateX
        v = ui.get_value(self.fs_rot_x)
        self.current_joint().rotateX.set(neutral + v * self.rotate_factor())

    def onChangeRotateY(self, *args):
        if ui.is_shift():
            ui.set_value(self.fs_rot_y, value=0)

        neutral = self.neutral_trs[self.cursor].rotateY
        v = ui.get_value(self.fs_rot_y)
        self.current_joint().rotateY.set(neutral + v * self.rotate_factor())

    def onChangeRotateZ(self, *args):
        if ui.is_shift():
            ui.set_value(self.fs_rot_z, value=0)

        neutral = self.neutral_trs[self.cursor].rotateZ
        v = ui.get_value(self.fs_rot_z)
        self.current_joint().rotateZ.set(neutral + v * self.rotate_factor())

    def onGradation(self, *args):
        if is_weight_paint_mode():
            activate_select_mode()
            pm.select(self.current_joint())

        else:
            weight_paint_mode_with_selected_joint(joint=self.current_joint(), meshes=self.meshes)

    def onAnimation(self, *args):
        pass

    def onPrevFocus(self, *args):
        move_cursor(self, offset=-1, focus=True)

    def onSelectFocus(self, *args):
        move_cursor(self, offset=0, focus=True)

    def onNextFocus(self, *args):
        move_cursor(self, offset=1, focus=True)

    def onResetFocus(self, *args):
        move_cursor(self, reset=True, focus=True)

    def onPrevNoFocus(self, *args):
        move_cursor(self, offset=-1, focus=False)

    def onSelectNoFocus(self, *args):
        move_cursor(self, offset=0, focus=False)

    def onResetNoFocus(self, *args):
        move_cursor(self, reset=True, focus=False)

    def onNextNoFocus(self, *args):
        move_cursor(self, offset=1, focus=False)

    def onPaintMode(self, *args):
        import nnutil.misc as nm

        weight_paint_mode_with_selected_joint()

    @staticmethod
    def _set_sel_hilighting_to(visibility):
        """全パネルの Selection Hilighting を切り替える.

        Args:
            visibility (bool): 新しい Selection Hilighting の値｡
        """
        def is_model_panel(panel):
            return cmds.getPanel(typeOf=panel) == "modelPanel"

        all_panels = cmds.getPanel(all=True)
        all_model_panels = [x for x in all_panels if is_model_panel(x)]

        for panel in all_model_panels:
            cmds.modelEditor(panel, e=True, sel=visibility)

    def onSelHilightingFalse(self, *args):
        """全てのモデルパネルの SelectionHilighting を無効にする."""
        self._set_sel_hilighting_to(False)

    def onSelHilightingTrue(self, *args):
        """全てのモデルパネルの SelectionHilighting を有効にする."""
        self._set_sel_hilighting_to(True)


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
