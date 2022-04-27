#! python
# coding:utf-8
"""
ツールの概要
"""
import pymel.core as pm

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import nnutil.display as nd

window_name = "NN_Tools"


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
