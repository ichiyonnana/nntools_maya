import math
import re

import maya.api.OpenMaya as om
import maya.cmds as cmds
import maya.mel as mel

import nnutil.decorator as deco
import nnutil.ui as ui


window_name = "NN_ShellAligner"
window = None

default_shell_margin = 1.0 / 128
default_tile_margin = 1.0 / 256

# 方向ごとの (軸のインデックス, 最大側へ詰めるか)
directions = {
    "left": (0, False),
    "right": (0, True),
    "down": (1, False),
    "up": (1, True),
}

# グループ化中のボタン色
group_color = (0.541, 0.541, 0.271)

# グループ化したシェルごとの (ノード, シェル ID, シェル内の UV インデックス)
group = []

# グループ化した時点のノードごとのシェル数
group_shell_counts = dict()


def _get_uv_shell_ids(node):
    """node のカレント UV セットの、UV インデックスごとの UV シェル ID を返す

    Args:
        node (str): メッシュのトランスフォームまたはシェイプの名前

    Returns:
        om.MIntArray: UV インデックスをインデックスとする UV シェル ID の配列
    """
    selection_list = om.MSelectionList()
    selection_list.add(node)
    dag_path = selection_list.getDagPath(0).extendToShape()

    return om.MFnMesh(dag_path).getUvShellsIds()[1]


def _get_selected_shell_keys(ordered, shell_ids_by_node):
    """選択 UV が属する (ノード, シェル ID) のリストを、最初に現れた順に重複なく返す

    Args:
        ordered (bool): True なら選択 UV の選択順で並べる
        shell_ids_by_node (dict): ノードごとの UV シェル ID のキャッシュ。取得したノードの分が追加される

    Returns:
        list[tuple[str, int]]: (ノード, シェル ID) のリスト
    """
    if ordered:
        uvs = [x for x in cmds.ls(orderedSelection=True, flatten=True) if re.match(r".+\.map\[\d+\]$", x)]
    else:
        uvs = cmds.filterExpand(cmds.polyListComponentConversion(cmds.ls(selection=True), toUV=True), selectionMask=35) or []

    keys = dict()
    for uv in uvs:
        node, index = re.match(r"(.+)\.map\[(\d+)\]", uv).groups()
        if node not in shell_ids_by_node:
            shell_ids_by_node[node] = _get_uv_shell_ids(node)

        keys[(node, shell_ids_by_node[node][int(index)])] = None

    return list(keys)


def _get_group_keys(shell_ids_by_node):
    """グループの (ノード, シェル ID) の集合を返す

    グループ化した時点からシェル数・シェル ID と UV インデックスの対応が変わっていれば、グループを解除して空の集合を返す

    Args:
        shell_ids_by_node (dict): ノードごとの UV シェル ID のキャッシュ。取得したノードの分が追加される

    Returns:
        set[tuple[str, int]]: グループの (ノード, シェル ID) の集合。グループが無いか解除した場合は空
    """
    if not group:
        return set()

    for node, shell_count in group_shell_counts.items():
        if not cmds.objExists(node):
            ungroup()
            cmds.warning("グループのオブジェクトが見つからないため、グループを解除しました")

            return set()

        if node not in shell_ids_by_node:
            shell_ids_by_node[node] = _get_uv_shell_ids(node)

        if len(set(shell_ids_by_node[node])) != shell_count:
            ungroup()
            cmds.warning("グループのシェルが変わったため、グループを解除しました")

            return set()

    for node, shell_id, uv_index in group:
        shell_ids = shell_ids_by_node[node]
        if uv_index >= len(shell_ids) or shell_ids[uv_index] != shell_id:
            ungroup()
            cmds.warning("グループのシェルが変わったため、グループを解除しました")

            return set()

    return {(node, shell_id) for node, shell_id, _ in group}


def get_selected_shells(ordered=False):
    """選択を含む UV シェルごとの UV のリストを返す。シェルの一部だけの選択でもシェル全体の UV を返す

    グループのシェルが 1 つでも選択されていれば、グループ全体を 1 つのシェルとして返す

    Args:
        ordered (bool): True なら選択 UV の選択順で、最初に選択された UV のシェルから順に並べる

    Returns:
        list[list[str]]: シェルごとの UV コンポーネント名のリスト
    """
    shell_ids_by_node = dict()
    keys = _get_selected_shell_keys(ordered, shell_ids_by_node)
    group_keys = _get_group_keys(shell_ids_by_node)

    # (ノード, シェル ID) ごとに、まとめて動かす単位の番号を決める。グループは最初に現れた位置で 1 つの単位にする
    unit_indices = dict()
    unit_count = 0
    for key in keys:
        if key in unit_indices:
            continue

        if key in group_keys:
            for group_key in group_keys:
                unit_indices[group_key] = unit_count
        else:
            unit_indices[key] = unit_count

        unit_count += 1

    shells = [[] for _ in range(unit_count)]
    for node, shell_ids in shell_ids_by_node.items():
        for index, shell_id in enumerate(shell_ids):
            unit_index = unit_indices.get((node, shell_id))
            if unit_index is not None:
                shells[unit_index].append("%s.map[%d]" % (node, index))

    return shells


def ungroup():
    """グループを解除し、グループ化ボタンを元の表示に戻す"""
    global group
    global group_shell_counts

    group = []
    group_shell_counts = dict()

    if window:
        window.update_group_button()


def group_selected_shells():
    """選択シェルをグループ化する"""
    global group
    global group_shell_counts

    shell_ids_by_node = dict()
    keys = _get_selected_shell_keys(False, shell_ids_by_node)

    if len(keys) < 2:
        cmds.warning("シェルを 2 つ以上選択して下さい")

        return

    # シェルごとに最初の UV のインデックスを記録し、シェル ID との対応が変わっていないかの確認に使う
    group = []
    for node, shell_id in keys:
        group.append((node, shell_id, list(shell_ids_by_node[node]).index(shell_id)))

    group_shell_counts = {node: len(set(shell_ids)) for node, shell_ids in shell_ids_by_node.items()}

    if window:
        window.update_group_button()


def select_group_members():
    """グループのシェルの UV をすべて選択する"""
    shell_ids_by_node = dict()
    group_keys = _get_group_keys(shell_ids_by_node)

    if not group_keys:
        return

    uvs = []
    for node, shell_ids in shell_ids_by_node.items():
        for index, shell_id in enumerate(shell_ids):
            if (node, shell_id) in group_keys:
                uvs.append("%s.map[%d]" % (node, index))

    cmds.select(uvs, replace=True)


def _get_bounding_box(uvs):
    """uvs の UV バウンディングボックスを返す

    Args:
        uvs (list[str]): UV コンポーネント名のリスト

    Returns:
        tuple[tuple[float, float], tuple[float, float]]: ((umin, vmin), (umax, vmax))
    """
    coords = cmds.polyEditUV(uvs, q=True)
    us = coords[0::2]
    vs = coords[1::2]

    return (min(us), min(vs)), (max(us), max(vs))


def _move(uvs, axis, offset):
    """uvs を axis 方向に offset だけ移動する

    Args:
        uvs (list[str]): UV コンポーネント名のリスト
        axis (int): 0 なら U 方向、1 なら V 方向
        offset (float): 移動量 (UV 値)
    """
    if axis == 0:
        cmds.polyEditUV(uvs, uValue=offset, vValue=0)
    else:
        cmds.polyEditUV(uvs, uValue=0, vValue=offset)


@deco.repeatable
@deco.undo_chunk
def align_shells(direction, margin):
    """選択シェルを direction 側へ、現在の並び順を保ったまま margin だけ空けて詰める

    最も direction 側にあるシェルは動かさない
    UV 選択モードでは選択順に並べ、最初に選択された UV のシェルを動かさない

    Args:
        direction (str): "left" / "right" / "down" / "up"
        margin (float): シェル間の間隔 (UV 値)
    """
    axis, toward_max = directions[direction]
    ordered = cmds.selectType(q=True, polymeshUV=True)
    shells = get_selected_shells(ordered=ordered)

    if not shells:
        return

    boxes = [_get_bounding_box(shell) for shell in shells]

    # 並び順は選択順か、バウンディングボックスの詰める側の端で決める
    if ordered:
        order = list(range(len(shells)))
    elif toward_max:
        order = sorted(range(len(shells)), key=lambda i: boxes[i][1][axis], reverse=True)
    else:
        order = sorted(range(len(shells)), key=lambda i: boxes[i][0][axis])

    # 先頭のシェルは動かさず、直前のシェルの反対側の端から margin を空けて順に並べる
    first = order[0]
    edge = boxes[first][0][axis] if toward_max else boxes[first][1][axis]
    for i in order[1:]:
        bb_min, bb_max = boxes[i]
        if toward_max:
            offset = (edge - margin) - bb_max[axis]
            edge = bb_min[axis] + offset
        else:
            offset = (edge + margin) - bb_min[axis]
            edge = bb_max[axis] + offset

        _move(shells[i], axis, offset)


@deco.repeatable
@deco.undo_chunk
def align_shells_to_tile(direction, margin):
    """選択シェルをそれぞれ、所属するタイルの direction 側の境界へ margin だけ空けて詰める

    タイル境界をまたいでいるシェルは、またいでいる境界のうち最も direction 側のものへ詰める

    Args:
        direction (str): "left" / "right" / "down" / "up"
        margin (float): タイル境界との間隔 (UV 値)
    """
    axis, toward_max = directions[direction]

    for shell in get_selected_shells():
        bb_min, bb_max = _get_bounding_box(shell)
        lower = math.floor(bb_min[axis])
        upper = math.ceil(bb_max[axis])
        crosses = upper - lower > 1

        if toward_max:
            boundary = upper - 1 if crosses else upper
            offset = (boundary - margin) - bb_max[axis]
        else:
            boundary = lower + 1 if crosses else lower
            offset = (boundary + margin) - bb_min[axis]

        _move(shell, axis, offset)


@deco.repeatable
@deco.undo_chunk
def distribute_shells(axis):
    """選択シェルのうち両端の 2 シェルを動かさず、その間のシェルをシェル間の間隔が均等になるよう並べる

    並び順と両端はバウンディングボックス中心で決める

    Args:
        axis (int): 0 なら U 方向、1 なら V 方向
    """
    shells = get_selected_shells()

    if len(shells) < 3:
        return

    boxes = [_get_bounding_box(shell) for shell in shells]
    order = sorted(range(len(shells)), key=lambda i: boxes[i][0][axis] + boxes[i][1][axis])

    # 両端のシェルの間の空きから間のシェルの幅を引いた残りを、間隔の数で等分する
    first = order[0]
    last = order[-1]
    widths = sum(boxes[i][1][axis] - boxes[i][0][axis] for i in order[1:-1])
    gap = (boxes[last][0][axis] - boxes[first][1][axis] - widths) / (len(order) - 1)

    edge = boxes[first][1][axis]
    for i in order[1:-1]:
        bb_min, bb_max = boxes[i]
        offset = (edge + gap) - bb_min[axis]
        edge = bb_max[axis] + offset

        _move(shells[i], axis, offset)


@deco.repeatable
@deco.undo_chunk
def orient_shells():
    """エッジが選択されていればOrientEdge を実行し、それ以外は OrientShells を実行する"""
    edges = cmds.filterExpand(cmds.ls(selection=True), selectionMask=32)

    if edges:
        mel.eval("texOrientEdge")
    else:
        mel.eval("texOrientShells")


@deco.repeatable
@deco.undo_chunk
def rotate_shells_to_long_side(vertical):
    """選択シェルをそれぞれ、バウンディングボックスの長辺が縦 (vertical) か横になるよう中心で 90 度回転する

    すでにその向きのシェルと、縦横が同じ長さのシェルは回転しない

    Args:
        vertical (bool): True なら縦長、False なら横長にする
    """
    for shell in get_selected_shells():
        bb_min, bb_max = _get_bounding_box(shell)
        width = bb_max[0] - bb_min[0]
        height = bb_max[1] - bb_min[1]

        if (vertical and width > height) or (not vertical and height > width):
            cmds.polyEditUV(shell, pivotU=(bb_min[0] + bb_max[0]) / 2, pivotV=(bb_min[1] + bb_max[1]) / 2, angle=90)


class NN_ToolWindow(object):
    """UV シェルを詰めて並べるツール."""

    def __init__(self):
        """コンストラクタ.

        UIウィンドウの設定
        コンポーネント選択順序を保存するプリファレンスの設定
        """
        self.window = window_name
        self.title = "Shell Aligner"
        self.group_button = None

        # シェル詰めで UV の選択順を使うため
        cmds.selectPref(trackSelectionOrder=True)

    def create(self):
        """ウィンドウの作成."""
        # 作り直したボタンの表示と合わせるため、記憶しているグループは解除する
        ungroup()

        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)

        # UV エディターが開いていればそのウィンドウを親にする
        parent_kwargs = dict()
        uv_panels = cmds.getPanel(scriptType="polyTexturePlacementPanel")
        uv_control = cmds.panel(uv_panels[0], q=True, control=True) if uv_panels else None
        if uv_control:
            parent_kwargs["parent"] = uv_control.split("|")[0]

        self.window = cmds.window(
            self.window,
            t=self.title,
            widthHeight=(10, 10),
            sizeable=False,
            maximizeButton=False,
            minimizeButton=False,
            resizeToFitChildren=True,
            **parent_kwargs
        )

        self.layout()
        cmds.showWindow(self.window)

    def layout(self):
        """UI レイアウト."""
        with ui.column_layout():
            # Default Margin がオンの間は誤編集防止のためエディットボックスを無効にする
            ui.header(label="Margin")
            ui.check_box(label="Default Margin", v=True, cc=self.onChangeDefaultMargin)

            with ui.row_layout():
                ui.text(label="Shell", width=ui.width(1.0))
                self.shell_margin = ui.eb_float(v=default_shell_margin, en=False, precision=6, width=ui.width(2.5))
                ui.text(label="Tile", width=ui.width(1.0))
                self.tile_margin = ui.eb_float(v=default_tile_margin, en=False, precision=6, width=ui.width(2.5))

            ui.separator(width=int(ui.width(7.5)), style="in", height=10)

            buttons = [
                [("水平分配", distribute_shells, (0,)), None, ("┳", self.onAlign, ("up", True)), None, None],
                [("垂直分配", distribute_shells, (1,)), None, ("▲", self.onAlign, ("up", False)), None, None],
                [
                    ("┣", self.onAlign, ("left", True)),
                    ("◀", self.onAlign, ("left", False)),
                    None,
                    ("▶", self.onAlign, ("right", False)),
                    ("┫", self.onAlign, ("right", True)),
                ],
                [None, ("OriV", rotate_shells_to_long_side, (True,)), ("▼", self.onAlign, ("down", False)), None, None],
                [("Orient", orient_shells, ()), ("OriH", rotate_shells_to_long_side, (False,)), ("┻", self.onAlign, ("down", True)), None, None],
            ]

            # ui.width(n) / ui.height(n) と同じ間隔で並べる
            pitch_u = int(ui.width(3) - ui.width(1.5))
            pitch_v = int(ui.height(3) - ui.height(1.5))
            form = cmds.formLayout(width=int(ui.width(7.5)), height=int(ui.height(7.5)))
            for row_index, row in enumerate(buttons):
                for column_index, cell in enumerate(row):
                    if cell is None:
                        continue

                    label, function, function_args = cell
                    width = ui.width(2.5) if function is distribute_shells else ui.width(1.5)

                    # 詰めるボタンは nnuvtoolkit と同じく U 方向・V 方向の色にする
                    bgc = ui.color_default
                    if function == self.onAlign:
                        bgc = ui.color_u if directions[function_args[0]][0] == 0 else ui.color_v

                    button = ui.button(label=label, width=int(width), height=int(ui.height(1.5)), bgc=bgc, c=lambda *args, function=function, function_args=function_args: function(*function_args))
                    cmds.formLayout(form, e=True, attachForm=[(button, "top", row_index * pitch_v), (button, "left", column_index * pitch_u)])

            self.group_button = ui.button(label="グループ化", width=int(ui.width(2.5)), height=int(ui.height(1.5)), c=self.onGroup)
            cmds.formLayout(form, e=True, attachForm=[(self.group_button, "top", 0), (self.group_button, "right", 0)])

            member_button = ui.button(label="メンバー選択", width=int(ui.width(2.5)), height=int(ui.height(1.5)), c=self.onSelectGroupMembers)
            cmds.formLayout(form, e=True, attachForm=[(member_button, "top", pitch_v), (member_button, "right", 0)])

            ui.end_layout()  # formLayout

    def update_group_button(self):
        """グループの有無に合わせてグループ化ボタンの表示を切り替える."""
        if not self.group_button or not cmds.button(self.group_button, exists=True):
            return

        if group:
            cmds.button(self.group_button, e=True, label="グループ解除", backgroundColor=group_color)
        else:
            cmds.button(self.group_button, e=True, label="グループ化", backgroundColor=ui.color_default)

    def onAlign(self, direction, to_tile):
        """シェル詰め・タイル詰めハンドラ.

        Args:
            direction (str): "left" / "right" / "down" / "up"
            to_tile (bool): True ならタイル詰め、False ならシェル詰め
        """
        if to_tile:
            align_shells_to_tile(direction, ui.get_value(self.tile_margin))
        else:
            align_shells(direction, ui.get_value(self.shell_margin))

    def onChangeDefaultMargin(self, value):
        """Default Margin チェックボックスハンドラ.

        Args:
            value (bool): チェックボックスの値
        """
        ui.set_availability(self.shell_margin, not value)
        ui.set_availability(self.tile_margin, not value)

    def onGroup(self, *args):
        """グループ化・グループ解除ハンドラ."""
        if group:
            ungroup()
        else:
            group_selected_shells()

    def onSelectGroupMembers(self, *args):
        """メンバー選択ハンドラ."""
        select_group_members()


def main():
    """メイン関数."""
    global window

    window = NN_ToolWindow()
    window.create()


if __name__ == "__main__":
    main()
