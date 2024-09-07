"""ツールの概要."""

import pymel.core as pm

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import nnutil.display as nd

window_name = "NN_Tools"


class NN_ToolWindow(object):
    """ここにツールの説明."""

    window_width = 251
    window_height = 220

    def __init__(self):
        """コンストラクタ.

        UIウィンドウの設定
        コンポーネント選択順序を保存するプリファレンスの設定
        Undo チャンク用のフラグ初期化
        """
        self.window = window_name
        self.title = window_name
        self.size = (self.window_width, self.window_height)

        pm.selectPref(trackSelectionOrder=True)

        self.is_chunk_open = False

    def create(self):
        """ウィンドウの作成."""
        if pm.window(self.window, exists=True):
            pm.deleteUI(self.window, window=True)

        # プリファレンスの有無による分岐
        if pm.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = pm.windowPref(self.window, q=True, topLeftCorner=True)
            pm.windowPref(self.window, remove=True)

            # 前回位置に指定したサイズで表示
            self.window = pm.window(
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
            self.window = pm.window(
                self.window,
                t=self.title,
                widthHeight=self.size,
                sizeable=False,
                maximizeButton=False,
                minimizeButton=False,
                resizeToFitChildren=True
            )

        self.layout()
        pm.showWindow(self.window)

    def layout(self):
        """UI レイアウト."""
        ui.column_layout()

        ui.row_layout()
        ui.header(label="sample:")
        ui.button(label="Test", c=self.onTest)
        ui.end_layout()

        ui.end_layout()

    def onTest(self, *args):
        """Testハンドラ."""
        pass


def main():
    """メイン関数."""
    NN_ToolWindow().create()


if __name__ == "__main__":
    main()
