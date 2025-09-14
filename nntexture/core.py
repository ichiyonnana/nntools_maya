"""ツールの概要."""
import maya.cmds as cmds

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import nnutil.display as nd

from .get_perimeter_uv_paths import get_perimeter_uv_paths
from .photoshop import (
    UVCoord,
    SubPath,
    Shape,
    create_shape_with_photoshop
)

window_name = "NN_Texture"


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

        ui.row_layout(numberOfColumns=100)
        ui.header(label="Temptex:")
        for i in range(16):
            ui.button(label=str(i), c=lambda x, *args: self.on_temptex(i))

        ui.end_layout()

        ui.row_layout()
        ui.header(label="Photoshop")
        ui.button(label="Create Shape", c=self.on_create_shape)

        ui.end_layout()

    def onTest(self, *args):
        """Testハンドラ."""
        pass

    def on_temptex(self, index):
        """Temptexボタンハンドラ."""
        pass

    def on_create_shape(self, *args):
        """Create Shapeボタンハンドラ.

        選択メッシュのUV境界をPhotoshopのシェイプとして生成する.
        """
        selections = cmds.ls(selection=True, flatten=True)
        uv_paths_dict = get_perimeter_uv_paths(selections)

        subpaths = []
        for mesh, uv_paths in uv_paths_dict.items():
            for path in uv_paths:
                points = []
                for uvi in path:
                    u, v = cmds.polyEditUV(f"{mesh}.map[{uvi}]", query=True)
                    u %= 1.0
                    v %= 1.0
                    points.append(UVCoord(u, v))
                subpath = SubPath(points)
                subpaths.append(subpath)

        shape = Shape(subpaths)

        # Photoshopでシェイプを作成
        jsx_path = create_shape_with_photoshop([shape])
        print("execute jsx: ", jsx_path)


def main():
    """メイン関数."""
    NN_ToolWindow().create()


if __name__ == "__main__":
    main()
