"""ツールの概要."""
import math

import maya.cmds as cmds

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import nnutil.display as nd

window_name = "NN_Deform"


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

        # UI コントロール
        self.eb_radial = "eb_radial"
        self.eb_axial = "eb_axial"
        self.eb_frequency = "eb_frequency"
        self.eb_offset = "eb_offset"

        self.vtx_positions = None

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
        ui.header(label="Radial")
        self.eb_radial = ui.eb_float(v=1.0)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Axial")
        self.eb_axial = ui.eb_float(v=0.5)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Frequency")
        self.eb_frequency = ui.eb_float(v=3.0)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Offset")
        self.eb_offset = ui.eb_float(v=0.0)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.button(label="Deform", c=self.on_deform)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.button(label="Clear Cache", c=self.on_clear_cache)
        ui.end_layout()

        ui.end_layout()

    def _sine_deform(self, radial_amount=1.0, axial_amount=0.5, frequency=1.0, offset=0.0):
        selection = cmds.ls(sl=True, fl=True)
        if not selection:
            cmds.warning("頂点を選択してください。")
            return

        # 選択を頂点に変換
        selection = cmds.polyListComponentConversion(selection, tv=True)
        vertices = cmds.filterExpand(selection, selectionMask=31)  # 頂点
        if not vertices:
            cmds.warning("頂点を選択してください。")
            return

        # 頂点の座標を取得
        positions = [cmds.pointPosition(vtx, world=True) for vtx in vertices]

        # 各軸の min-max を取得
        min_pos = [min(p[i] for p in positions) for i in range(3)]
        max_pos = [max(p[i] for p in positions) for i in range(3)]

        # 最も範囲が小さい軸を中心軸にする
        ranges = [max_pos[i] - min_pos[i] for i in range(3)]
        center_axis = ranges.index(min(ranges))

        # 影響を受ける座標軸を決定
        affected_axes = [(center_axis + 1) % 3, (center_axis + 2) % 3]

        # 中心を計算
        center = [(min_pos[i] + max_pos[i]) / 2.0 for i in range(3)]

        # オフセットをラジアンに変換
        offset_rad = math.radians(offset)

        # サイン波変形を適用
        for vtx, pos in zip(vertices, positions):
            # 中心からの偏角を計算
            dx = pos[affected_axes[0]] - center[affected_axes[0]]
            dy = pos[affected_axes[1]] - center[affected_axes[1]]
            angle = math.atan2(dy, dx) + offset_rad

            # 変形量を計算
            displacement = math.sin(angle * frequency)
            radial_displacement = displacement * radial_amount
            axial_displacement = displacement * axial_amount

            # 新しい座標を設定
            new_pos = list(pos)
            new_pos[affected_axes[0]] += math.cos(angle) * radial_displacement
            new_pos[affected_axes[1]] += math.sin(angle) * radial_displacement
            new_pos[center_axis] += axial_displacement
            cmds.move(new_pos[0], new_pos[1], new_pos[2], vtx, absolute=True)

        cmds.select(vertices)  # 変形後も選択状態を維持

    def on_deform(self, *args):
        """Testハンドラ."""
        self._sine_deform(
            radial_amount=ui.get_value(self.eb_radial),
            axial_amount=ui.get_value(self.eb_axial),
            frequency=ui.get_value(self.eb_frequency),
            offset=ui.get_value(self.eb_offset)
            )

    def on_clear_cache(self, *args):
        """Testハンドラ."""
        self.vtx_positions = None


def main():
    """メイン関数."""
    NN_ToolWindow().create()


if __name__ == "__main__":
    main()
