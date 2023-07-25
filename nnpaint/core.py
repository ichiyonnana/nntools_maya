#! python
# coding:utf-8
"""
ツールの概要
"""
import pymel.core as pm

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import pymel.core.nodetypes as nt
import nnutil.display as nd

window_name = "NN_Tools"


def initialize_paint():
    
    # ペイント用 Lambert 作成
    paint_material = None

    # tripleShadingSwitch 接続
    switch = None

    target_objects = pm.selected()

    for target_object in target_objects:

        # 現在のマテリアル取得
        print(target_object)
        shape = target_object.getShape()

        shading_groups = pm.listConnections(shape, source=False, destination=True, type="shadingEngine")
        for shading_group in shading_groups:
            materials = pm.ls(pm.listConnections(shading_group, source=True, destination=False), materials=True)

            for material in materials:
                print(material)

        # マテリアルのファイルノード取得

        # オブジェクトの複製

        # UV 正規化

        # ペイントマテリアル割り当て

        # tripleShadingSwitch にオブジェクトとファイルの組み合わせ登録

        # 元マテリアルの file ノードか file ノードの内容差し替える


def enable_paint():
    selections = pm.selected()

    if selections:
        if isinstance(selections[0], (nt.Mesh, nt.Transform)):
            object = selections[0]
            faces = None

        elif isinstance(selections[0], pm.MeshFace):
            object = pm.polyListComponentConversion(selections[0])[0]
            faces = selections
        
        # ペイントツール起動
        mel.eval("Art3dPaintToolOptions")


def change_brush():
    mode = pm.alphaBlend_uiToMel("Lighten")
    current_ctx = pm.currentCtx()
    pm.art3dPaintCtx(current_ctx, e=True, alphablendmode=mode)
    
    mode = pm.alphaBlend_uiToMel("Darken")
    current_ctx = pm.currentCtx()
    pm.art3dPaintCtx(current_ctx, e=True, alphablendmode=mode)

    current_ctx = pm.currentCtx()
    pm.art3dPaintCtx(current_ctx, e=True, reflection=True)

    current_ctx = pm.currentCtx()
    pm.art3dPaintCtx(current_ctx, e=True, reflection=False)

    mode = pm.attributeToPaint_uiToMel("Ambient")
    current_ctx = pm.currentCtx()
    pm.art3dPaintCtx(current_ctx, e=True, painttxtattrname=mode)

    mode = pm.attributeToPaint_uiToMel("Color")
    current_ctx = pm.currentCtx()
    pm.art3dPaintCtx(current_ctx, e=True, painttxtattrname=mode)


class NN_ToolWindow(object):
    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (251, 220)

        self.is_chunk_open = False

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
