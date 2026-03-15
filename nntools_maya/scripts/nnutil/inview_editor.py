"""複数ノードの同一アトリビュートを一括編集するダイアログ"""
import maya.cmds as cmds
import pymel.core as pm

import nnutil.ui as ui


window_name = "NNInviewEditor"


class InviewEditor(object):
    """複数ノードの同一アトリビュートを一括編集するダイアログクラス"""
    min_value = 0.0
    max_value = 1.0
    last_attribute = ""

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

        # アトリビュートが変更された場合、最小値と最大値をリセット
        if InviewEditor.last_attribute != attribute:
            InviewEditor.min_value = 0.0
            InviewEditor.max_value = 1.0
            InviewEditor.last_attribute = attribute

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
            InviewEditor.min_value = ui.get_value(self.min_field)

        def on_max_change(value):
            """maxの変更ハンドラ"""
            pm.floatSlider(self.slider, edit=True, maxValue=value)
            InviewEditor.max_value = ui.get_value(self.max_field)

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
        self.min_field = ui.eb_float(v=InviewEditor.min_value, cc=on_min_change)
        self.max_field = ui.eb_float(v=InviewEditor.max_value, cc=on_max_change)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Value")
        self.slider = ui.float_slider(min=InviewEditor.min_value, max=InviewEditor.max_value, value=original_values[nodes[0]], dc=on_drag_slider, cc=on_change_slider, width=ui.width(4))
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.button(label="OK", c=on_ok)
        ui.button(label="Cancel", c=on_cancel)
        ui.end_layout()

        cmds.showWindow(self.window)
