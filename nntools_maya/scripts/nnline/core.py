"""ツールの概要."""
import maya.cmds as cmds

import nnutil.ui as ui


window_name = "NN_Line"


class NN_ToolWindow(object):
    """ここにツールの説明."""

    window_width = 10
    window_height = 10

    def __init__(self):
        """コンストラクタ.

        UIウィンドウの設定
        コンポーネント選択順序を保存するプリファレンスの設定
        Undo チャンク用のフラグ初期化
        """
        self.window = window_name
        self.title = window_name
        self.size = (self.window_width, self.window_height)

        cmds.selectPref(trackSelectionOrder=True)

        self.is_chunk_open = False

    def create(self):
        """ウィンドウの作成."""
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)

        # プリファレンスの有無による分岐
        if cmds.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = cmds.windowPref(self.window, q=True, topLeftCorner=True)
            cmds.windowPref(self.window, remove=True)

            # 前回位置に指定したサイズで表示
            self.window = cmds.window(
                self.window,
                t=self.title,
                widthHeight=self.size,
                sizeable=False,
                maximizeButton=False,
                minimizeButton=False,
                resizeToFitChildren=True,
                topLeftCorner=position
            )

        else:
            # プリファレンスがなければデフォルト位置に指定サイズで表示
            self.window = cmds.window(
                self.window,
                t=self.title,
                widthHeight=self.size,
                sizeable=False,
                maximizeButton=False,
                minimizeButton=False,
                resizeToFitChildren=True
            )

        self.layout()
        cmds.showWindow(self.window)

    def layout(self):
        """UI レイアウト."""
        ui.column_layout()

        ui.row_layout()
        ui.header(label="Node")
        ui.button(label="Create", c=self.on_create_node)
        ui.button(label="Select", c=self.on_select_node)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Display")
        ui.button(label="Enable", c=self.on_enable_line_display)
        ui.button(label="Disable", c=self.on_disable_line_display)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Set")
        self.eb_set_name = ui.eb_text(text="")
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Edge")
        ui.button(label="Add", c=self.on_add_component)
        ui.button(label="Remove", c=self.on_remove_component)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Options")
        ui.button(label="X-Ray Component", c=self.on_toggle_xray_component)
        ui.end_layout()

    def _get_set_name(self):
        return self.eb_set_name.getText()

    def _ensure_set(self, set_name):
        """セットが存在しなければ空セットを作成する"""
        if not cmds.objExists(set_name):
            cmds.sets(name=set_name, empty=True)

    def _remove_non_edges(self, set_name):
        """セット内のエッジ以外のコンポーネントを除外する後処理"""
        members = cmds.ls(cmds.sets(set_name, q=True) or [], flatten=True)
        non_edges = [m for m in members if ".e[" not in m]
        if non_edges:
            cmds.sets(non_edges, remove=set_name)

    def on_create_node(self, *_):
        """previewObjectSet ノードを作成する。既存の場合は何もしない。"""
        existing = cmds.ls(type="previewObjectSet")
        if existing:
            set_name = cmds.getAttr(existing[0] + ".setName")
            self.eb_set_name.setText(set_name)
            return

        node = cmds.createNode("previewObjectSet")
        cmds.setAttr(node + ".overrideEnabled", 1)
        cmds.setAttr(node + ".overrideDisplayType", 2)  # 2 = Reference
        set_name = cmds.getAttr(node + ".setName")
        self.eb_set_name.setText(set_name)

    def on_select_node(self, *_):
        """すべての previewObjectSet ノードを選択する。"""
        nodes = cmds.ls(type="previewObjectSet")
        if nodes:
            cmds.select(nodes)

    def on_add_component(self, *_):
        """選択コンポーネントをセットに追加する。
        エッジはそのまま追加。フェースは perimeter エッジに変換して追加。それ以外は無視。
        """
        set_name = self._get_set_name()
        if not set_name:
            return

        selection = cmds.ls(sl=True, flatten=True)
        edges = [s for s in selection if ".e[" in s]
        faces = [s for s in selection if ".f[" in s]

        if faces:
            border_edges = cmds.ls(
                cmds.polyListComponentConversion(faces, fromFace=True, toEdge=True, border=True),
                flatten=True
            )
            edges.extend(border_edges)

        if not edges:
            return

        self._ensure_set(set_name)
        cmds.sets(edges, addElement=set_name)
        self._remove_non_edges(set_name)

    def on_remove_component(self, *_):
        """選択エッジをセットから除外する。エッジ以外は無視。"""
        set_name = self._get_set_name()
        if not set_name or not cmds.objExists(set_name):
            return

        edges = [s for s in cmds.ls(sl=True, flatten=True) if ".e[" in s]
        if not edges:
            return

        cmds.sets(edges, remove=set_name)
        self._remove_non_edges(set_name)

    def on_enable_line_display(self, *_):
        """シーン中のすべての previewObjectSet の display を有効にする。"""
        for node in cmds.ls(type="previewObjectSet"):
            cmds.setAttr(node + ".display", 1)

    def on_disable_line_display(self, *_):
        """シーン中のすべての previewObjectSet の display を無効にする。"""
        for node in cmds.ls(type="previewObjectSet"):
            cmds.setAttr(node + ".display", 0)

    def on_toggle_xray_component(self, *_):
        """全モデルパネルの X-Ray Active Components をトグルする。"""
        panels = cmds.getPanel(type="modelPanel")
        if not panels:
            return
        current = cmds.modelEditor(panels[0], q=True, activeComponentsXray=True)
        for panel in panels:
            cmds.modelEditor(panel, e=True, activeComponentsXray=(not current))


def main():
    """メイン関数."""
    NN_ToolWindow().create()


if __name__ == "__main__":
    main()
