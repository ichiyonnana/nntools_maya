"""ツールの概要."""
import maya.cmds as cmds
import maya.mel as mel

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
        self.grid_num = 16

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
        for i in range(self.grid_num):
            ui.button(label=str(i), c=lambda *args, i=i: self.on_temptex(i), width=ui.width(1), height=ui.height(1))

        ui.end_layout()

        ui.separator(h=10)

        ui.row_layout()
        ui.header(label="Photoshop")
        ui.button(label="Create Shape", c=self.on_create_shape)

        ui.end_layout()

    def onTest(self, *args):
        """Testハンドラ."""
        pass

    @deco.undo_chunk
    def on_temptex(self, index):
        """Temptexボタンハンドラ.

        選択部分を独立したUVシェルに切り離し、縦横比を保ったまま縮小してグリッドセルの中心へ移動する.
        """
        if not cmds.ls(selection=True):
            nd.message("select component")
            return

        mel.eval("CreateUVShellAlongBorder")

        # シェル化でUVと選択が変わるため、座標の取得はシェル化後の選択から行う
        uvs = nu.to_uv(cmds.ls(selection=True, flatten=True))

        if not uvs:
            nd.message("select component")
            return

        uv_coords = nu.split_n_pair(cmds.polyEditUV(uvs, query=True), 2)
        min_u = min([uv[0] for uv in uv_coords])
        max_u = max([uv[0] for uv in uv_coords])
        min_v = min([uv[1] for uv in uv_coords])
        max_v = max([uv[1] for uv in uv_coords])

        center_u = (min_u + max_u) / 2
        center_v = (min_v + max_v) / 2

        # バウンディングボックスの長辺をグリッド1マスの 1/3 に合わせる
        cell_size = 1.0 / self.grid_num
        longest = max(max_u - min_u, max_v - min_v)
        scale = cell_size / 3 / longest if longest else 1.0

        cmds.polyEditUV(uvs, pivotU=center_u, pivotV=center_v, scaleU=scale, scaleV=scale)

        # 左下を 0 として右方向へ採番したグリッドセルの中心を、現在のUVタイル内で求める
        row, col = divmod(index, self.grid_num)
        dest_u = center_u // 1 + (col + 0.5) * cell_size
        dest_v = center_v // 1 + (row + 0.5) * cell_size

        cmds.polyEditUV(uvs, uValue=dest_u - center_u, vValue=dest_v - center_v)

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
                    # 1.0 が 0.0 になるのを防ぐため % は使わない
                    u = (u % 1.0) or (1.0 if u else 0.0)
                    v = (v % 1.0) or (1.0 if v else 0.0)
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
