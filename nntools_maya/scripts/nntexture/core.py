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

# 選択UVの所属セルを示すボタンの色 (#8a8a45)
highlight_color = (0.541, 0.541, 0.271)


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
        self.grid_num_v = 8

        cmds.selectPref(trackSelectionOrder=True)

        self.is_chunk_open = False

    def create(self):
        """ウィンドウの作成."""
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)

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
        self.temptex_buttons = []
        for i in range(self.grid_num):
            self.temptex_buttons.append(ui.button(label=str(i), c=lambda *args, i=i: self.on_temptex(i), width=ui.width(1), height=ui.height(1)))

        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        self.base_button = ui.button(label="Base", c=self.on_base)
        self.shadow_button = ui.button(label="Shadow", c=self.on_shadow)
        ui.button(label="Get", c=self.on_get)

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

        全UVがすでに指定セル内にある場合はシェル化も変形も行わない.
        """
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

        # セルは横幅 1/grid_num 、高さ 1/grid_num_v の縦長
        cell_width = 1.0 / self.grid_num
        cell_height = 1.0 / self.grid_num_v

        # 左下を 0 として右方向へ採番したグリッドセルを、現在のUVタイル内で求める
        row, col = divmod(index, self.grid_num)
        cell_min_u = center_u // 1 + col * cell_width
        cell_min_v = center_v // 1 + row * cell_height
        cell_max_u = cell_min_u + cell_width
        cell_max_v = cell_min_v + cell_height

        # すでにセル内に配置されていれば何もしない
        if all(cell_min_u <= u <= cell_max_u and cell_min_v <= v <= cell_max_v for u, v in uv_coords):
            return

        # 移動前にシェルでカットする
        mel.eval("CreateUVShellAlongBorder")

        # シェル化でUVと選択が変わるため、変形対象はシェル化後の選択から取り直す
        uvs = nu.to_uv(cmds.ls(selection=True, flatten=True))

        # バウンディングボックスの長辺をグリッド1マスの 1/3 に合わせる
        longest = max(max_u - min_u, max_v - min_v)
        scale = cell_width / 3 / longest if longest else 1.0

        cmds.polyEditUV(uvs, pivotU=center_u, pivotV=center_v, scaleU=scale, scaleV=scale)

        # 移動先UV座標
        dest_u = cell_min_u + cell_width / 2
        dest_v = cell_min_v + cell_height / 4

        cmds.polyEditUV(uvs, uValue=dest_u - center_u, vValue=dest_v - center_v)

    @deco.undo_chunk
    def on_base(self, *args):
        """Baseボタンハンドラ.

        選択UVをグリッドセルの下半分へ移動する.
        """
        self.move_to_half(to_upper=False)

    @deco.undo_chunk
    def on_shadow(self, *args):
        """Shadowボタンハンドラ.

        選択UVをグリッドセルの上半分へ移動する.
        """
        self.move_to_half(to_upper=True)

    def move_to_half(self, to_upper):
        """選択部分を独立したUVシェルに切り離し、縦長グリッドセルの上半分か下半分へ移動する.

        全UVがすでに移動先の半分にある場合はシェル化も移動も行わない.
        """
        uvs = nu.to_uv(cmds.ls(selection=True, flatten=True))

        if not uvs:
            nd.message("select component")

            return

        uv_coords = nu.split_n_pair(cmds.polyEditUV(uvs, query=True), 2)

        # セルは縦長で、その上半分が Shadow 、下半分が Base
        cell_height = 1.0 / self.grid_num_v
        half_height = cell_height / 2
        offsets = [uv[1] % cell_height for uv in uv_coords]

        # すでに指定のセルに収まっているかの判定
        if to_upper:
            is_inside = all(offset >= half_height or offset == 0 for offset in offsets)
        else:
            is_inside = all(offset <= half_height for offset in offsets)

        # すでに指定のセルに収まっていればシェルカット含めて何もしない
        if is_inside:
            return

        # シェルカットとシェルカット後の uvid を取得
        mel.eval("CreateUVShellAlongBorder")
        uvs = nu.to_uv(cmds.ls(selection=True, flatten=True))

        cmds.polyEditUV(uvs, vValue=half_height if to_upper else -half_height)

    def on_get(self, *args):
        """Getボタンハンドラ.

        選択UVが属するセルの列と上下半分に対応するボタンを色で示す.
        選択が無ければ色を初期状態に戻す.
        """
        for control in self.temptex_buttons + [self.base_button, self.shadow_button]:
            cmds.button(control, edit=True, backgroundColor=ui.color_default)

        uvs = nu.to_uv(cmds.ls(selection=True, flatten=True))

        if not uvs:
            return

        uv_coords = nu.split_n_pair(cmds.polyEditUV(uvs, query=True), 2)
        cell_width = 1.0 / self.grid_num
        cell_height = 1.0 / self.grid_num_v
        half_height = cell_height / 2

        # 選択UVが所属するセルに対応するボタンをハイライトする。
        # Base/Shadow は一つでもUVが存在すればハイライトする。
        indices = set()
        uppers = set()

        for u, v in uv_coords:
            col = int(u % 1.0 // cell_width)
            row = int(v % 1.0 // cell_height)
            index = row * self.grid_num + col

            if index < len(self.temptex_buttons):
                indices.add(index)

            uppers.add(v % cell_height >= half_height)

        for index in indices:
            cmds.button(self.temptex_buttons[index], edit=True, backgroundColor=highlight_color)

        if True in uppers:
            cmds.button(self.shadow_button, edit=True, backgroundColor=highlight_color)

        if False in uppers:
            cmds.button(self.base_button, edit=True, backgroundColor=highlight_color)

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
