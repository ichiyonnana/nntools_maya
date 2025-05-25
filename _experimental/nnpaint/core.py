"""
ツールの概要
"""
import maya.cmds as cmds
import maya.mel as mel

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import nnutil.display as nd

window_name = "NN_Tools"


def initialize_paint():
    # ペイント用 Lambert 作成
    paint_material = None

    # tripleShadingSwitch 接続
    switch = None

    target_objects = cmds.ls(selection=True)

    for target_object in target_objects:

        # 現在のマテリアル取得
        print(target_object)
        shape = nu.get_shape(target_object)

        shading_groups = cmds.listConnections(shape, source=False, destination=True, type="shadingEngine")
        for shading_group in shading_groups:
            materials = cmds.ls(cmds.listConnections(shading_group, source=True, destination=False), materials=True)

            for material in materials:
                print(material)

        # マテリアルのファイルノード取得

        # オブジェクトの複製

        # UV 正規化

        # ペイントマテリアル割り当て

        # tripleShadingSwitch にオブジェクトとファイルの組み合わせ登録

        # 元マテリアルの file ノードか file ノードの内容差し替える


def enable_paint():
    selections = cmds.ls(selection=True)

    if selections:
        if cmds.objectType(selections[0]) in ("mesh", "transform"):
            object = selections[0]
            faces = None

        elif nu.type_of_component(selections[0]) == "face":
            object = cmds.polyListComponentConversion(selections[0])[0]
            faces = selections

        # ペイントツール起動
        mel.eval("Art3dPaintToolOptions")


def change_brush():
    mode = cmds.alphaBlend_uiToMel("Lighten")
    current_ctx = cmds.currentCtx()
    cmds.art3dPaintCtx(current_ctx, e=True, alphablendmode=mode)

    mode = cmds.alphaBlend_uiToMel("Darken")
    current_ctx = cmds.currentCtx()
    cmds.art3dPaintCtx(current_ctx, e=True, alphablendmode=mode)

    current_ctx = cmds.currentCtx()
    cmds.art3dPaintCtx(current_ctx, e=True, reflection=True)

    current_ctx = cmds.currentCtx()
    cmds.art3dPaintCtx(current_ctx, e=True, reflection=False)

    mode = cmds.attributeToPaint_uiToMel("Ambient")
    current_ctx = cmds.currentCtx()
    cmds.art3dPaintCtx(current_ctx, e=True, painttxtattrname=mode)

    mode = cmds.attributeToPaint_uiToMel("Color")
    current_ctx = cmds.currentCtx()
    cmds.art3dPaintCtx(current_ctx, e=True, painttxtattrname=mode)


class NN_ToolWindow(object):
    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (251, 220)

        self.is_chunk_open = False

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
        ui.header(label="sample:")
        ui.button(label="Test", c=self.onTest)
        ui.end_layout()

        ui.end_layout()

    def onTest(self, *args):
        """Testハンドラ"""
        pass


def main():
    NN_ToolWindow().create()


if __name__ == "__main__":
    main()
