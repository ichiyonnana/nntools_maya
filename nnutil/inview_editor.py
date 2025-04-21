"""複数ノードの同一アトリビュートを一括編集するダイアログ"""
import maya.cmds as cmds
import pymel.core as pm

import nnutil.ui as ui


window_name = "NNInviewEditor"


class InviewEditor(object):
    """複数ノードの同一アトリビュートを一括編集するダイアログクラス"""
    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (10, 10)

        self.slider = None
        self.min_field = None
        self.max_field = None

        self.is_chunk_open = False

    def show(self, nodes, attribute):
        """ダイアログを表示する"""
        # 現在のアトリビュート値を保存
        original_values = {node: cmds.getAttr(f"{node}.{attribute}") for node in nodes}

        def apply_changes(value):
            """値の適用"""
            for node in nodes:
                cmds.setAttr(f"{node}.{attribute}", value)

        def on_drag_slider(value):
            """スライダーのドラッグハンドラ"""
            if not self.is_chunk_open:
                self.is_chunk_open = True
                cmds.undoInfo(openChunk=True)

            apply_changes(value)

        def on_change_slider(value):
            """スライダーの確定ハンドラ"""
            if self.is_chunk_open:
                self.is_chunk_open = False
                cmds.undoInfo(closeChunk=True)

            apply_changes(value)

        def on_min_change(value):
            """minの変更ハンドラ"""
            pm.floatSlider(self.slider, edit=True, minValue=value)

        def on_max_change(value):
            """maxの変更ハンドラ"""
            pm.floatSlider(self.slider, edit=True, maxValue=value)

        def on_ok(*args):
            """"OKボタンハンドラ"""
            cmds.deleteUI(self.window, window=True)

        def on_cancel(*args):
            """Cancelボタンハンドラ"""
            for node, value in original_values.items():
                cmds.setAttr(f"{node}.{attribute}", value)

            cmds.deleteUI(self.window, window=True)

        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)

        cmds.window(
            self.window,
            t=self.title,
            maximizeButton=False,
            minimizeButton=False,
            widthHeight=self.size,
            sizeable=False,
            resizeToFitChildren=True
            )

        ui.column_layout()

        ui.row_layout()
        ui.header(label="Nodes")
        ui.eb_text(text=",".join(nodes), width=ui.width(4))
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Attribute")
        ui.eb_text(text=attribute, width=ui.width(4))
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Min/Max")
        self.min_field = ui.eb_float(v=0.0, cc=on_min_change)
        self.max_field = ui.eb_float(v=1.0, cc=on_max_change)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Value")
        self.slider = ui.float_slider(min=0.0, max=1.0, value=original_values[nodes[0]], dc=on_drag_slider, cc=on_change_slider, width=ui.width(4))
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.button(label="OK", c=on_ok)
        ui.button(label="Cancel", c=on_cancel)
        ui.end_layout()

        cmds.showWindow(self.window)
