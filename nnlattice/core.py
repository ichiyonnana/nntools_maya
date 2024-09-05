import os
import re
import sys
import traceback

import maya.cmds as cmds
import maya.mel as mel
import pymel.core as pm
import pymel.core.datatypes as dt
import pymel.core.nodetypes as nt

import nnutil as nu
import nnutil.ui as ui
import nnutil.display as nd


window_name = "NN_Lattice"
window = None


def get_window():
    return window


window_width = 280
header_width = 50
window_height = 220


def match_latice(from_objects=None, to_object=None):
    """ ラティスを別のラティスに一致させる。

    ワールドでのトランスフォーム、分割数、ラティスポイントを一致させる。
    引数が未指定の場合は選択オブジェクトを使用する。
    to_object は 最後に選択されたオブジェクト
    from_objects はそれ以外すべて

    Args:
        from_objects (list[Transform]):   変形元ラティスのリスト
        to_object(list[Transform]):      変形先のラティス
    """
    # ラティス関連クラス
    lattice_types = [pm.nodetypes.BaseLattice, pm.nodetypes.Lattice]

    # マッチ元ラティスとマッチ先ラティス
    from_lattices = []
    to_lattice = None

    # 引数が無効なら選択オブジェクトを利用する
    if not from_objects or from_objects is None or to_object is None:
        selected_lattice = [x for x in pm.selected(flatten=True) if type(x.getShape()) in lattice_types]

        if len(selected_lattice) < 2:
            return
        else:
            from_lattices = selected_lattice[0:-1]
            to_lattice = selected_lattice[-1]
    else:
        from_lattices = from_objects
        to_lattice = to_object

    # マッチ元ラティス毎の処理
    for lattice in from_lattices:

        # ラティスのシェイプとトランスフォームノード
        trs_node = lattice
        lattice_node = lattice.getShape()

        to_trs_node = to_lattice
        to_lattice_node = to_lattice.getShape()

        # トランスフォームの一致
        trs_node.setMatrix(to_trs_node.getMatrix())

        # ラティスの処理
        if type(lattice_node) == pm.nodetypes.Lattice:
            # 分割数を変更するため変形をリセットする
            lattice_node.latticeReset()

            # 分割数を合わせる
            s, t, u = to_lattice_node.getDivisions()
            lattice_node.setDivisions(s, t, u)

            # ラティスポイントの一致
            for s_i in range(s):
                for t_i in range(t):
                    for u_i in range(u):
                        # ラティスポイントオブジェクト
                        from_point = lattice_node.pt[s_i][t_i][u_i]
                        to_point = to_lattice_node.pt[s_i][t_i][u_i]

                        # ラティスポイントのローカル座標取得
                        # from_coord = lattice_node.point(s_i, t_i, u_i)
                        # to_coord = to_lattice_node.point(s_i, t_i, u_i)

                        # ラティスポイントをワールド座標で取得・設定
                        to_coord = pm.xform(to_point, q=True, ws=True, t=True)
                        pm.xform(from_point, ws=True, t=to_coord)


def add_lattice_menber(lattice=None, targets=None):
    """ 既存のラティスにメンバーを追加する

    引数が未指定の場合は選択オブジェクトから推定する
    lattice は 選択オブジェクトの内最後に選択されたラティス
    targets は lattice を除いたすべてのオブジェクト (他にラティスがあればそれも含む)

    Args:
        lattice (Transform or Lattice):
        targets (list[Transform or Lattice]):
    """
    lattice_types = [nt.BaseLattice, nt.Lattice]

    # メンバーを追加するラティスのデフォーマーノード
    ffd = None

    # 引数が無効な場合は選択オブジェクトから推定する
    if not lattice or not targets:
        selections = pm.selected(flatten=True)
        lattice = [x for x in selections if type(x.getShape()) == pm.nodetypes.Lattice][-1]
        targets = selections
        targets.remove(lattice)

    # lattice が Lattice や BaseLattice なら FFD ノードを取得する
    if type(lattice) in lattice_types:
        ffd = pm.listConnections(lattice, type="ffd")[0]
    elif type(lattice) == pm.nodetypes.Transform:
        ffd = pm.listConnections(lattice.getShape(), type="ffd")[0]

    # メンバーの追加
    object_set = [x for x in pm.listConnections(ffd) if type(x) == nt.ObjectSet][0]
    object_set.addMembers(targets)


def get_lattice_menber(lattice):
    """ ラティスのメンバーを取得する

    引数が未指定の場合は選択オブジェクトを使用する

    Args:
        lattice (Transform or Lattice):
        targets (list[Transform or Lattice]):
    """
    lattice_types = [nt.BaseLattice, nt.Lattice]

    # メンバーを選択するラティスのデフォーマーノード
    ffd = None

    # lattice が Lattice や BaseLattice なら FFD ノードを取得する
    if type(lattice) in lattice_types:
        ffd = pm.listConnections(lattice, type="ffd")[0]
    elif type(lattice) == pm.nodetypes.Transform:
        ffd = pm.listConnections(lattice.getShape(), type="ffd")[0]

    # メンバーの取得
    if sys.version_info.major >= 3:
        members = ffd.outputs()
    else:
        object_set = [x for x in pm.listConnections(ffd) if type(x) == nt.ObjectSet][0]
        members = [nu.get_object(x) for x in object_set.members()]

    return members


def select_lattice_menber(lattice=None):
    """ ラティスのメンバーを選択する

    引数が未指定の場合は選択オブジェクトを使用する

    Args:
        lattice (Transform or Lattice):
        targets (list[Transform or Lattice]):
    """
    lattice_types = [nt.BaseLattice, nt.Lattice]

    # 引数が無効な場合は選択オブジェクトを使用する
    if not lattice:
        selections = pm.selected(flatten=True)
        lattice = [x for x in selections if type(x.getShape()) == pm.nodetypes.Lattice][-1]

    # メンバーの取得と選択
    members = get_lattice_menber(lattice)
    pm.select(members, replace=True)


def get_selected_lattice_and_points(selected_lattice_points=[]):
    """ ラティスかラティスポイントが選択されている場合に､選択されているラティスとラティスポイントのリストを返す
    選択が無効な場合は None
    ラティス選択時はそのラティスと空リスト [lattice, []]
    ポイント選択時はそのポイントを持つラティスと選択ポイントリスト [lattice, [pt,pt,pt,...]]

    Args:
        selected_lattice_points (list[LatticePoint]):
    """
    lattice = None

    if not selected_lattice_points:
        selected_lattice_points = [x for x in pm.selected(flatten=True) if type(x) == pm.LatticePoint]

    if selected_lattice_points:
        # ラティスポイントが選択されていた場合
        lattice = nu.pynode(pm.polyListComponentConversion(selected_lattice_points[0])[0]).getParent()

    else:
        selected_lattice = [x for x in pm.selected(flatten=True) if hasattr(x, "getShape") and type(x.getShape()) == nt.Lattice]

        if selected_lattice:
            # ラティスが選択されていた場合
            lattice = selected_lattice[0]
            selected_lattice_points = []

    if not lattice:
        # ラティスもラティスポイントも選択されていなかった場合
        return None

    return [lattice, selected_lattice_points]


def get_divisions(lattice_name):
    """ラティスの分割数を取得する"""
    s = cmds.getAttr(lattice_name + ".sDivisions")
    t = cmds.getAttr(lattice_name + ".tDivisions")
    u = cmds.getAttr(lattice_name + ".uDivisions")

    return [s, t, u]


def rebuild_lattice(lattice=None, s=None, t=None, u=None):
    """ラティスの分割数を変更する｡

    Args:
        s (int): 新しい S 分割数
        t (int): 新しい T 分割数
        u (int): 新しい U 分割数
    """
    if not lattice and not cmds.ls(selection=True):
        print("select lattice")
        return

    # 処理終了後に設定する編集モード
    object_mode = pm.selectMode(q=True, object=True)

    # 再分割対象ラティスの取得
    if not lattice:
        selected_trs = cmds.ls(selection=True, type="transform")

        # シェープとしてラティスを持つトランスフォームが選択されている場合
        if selected_trs:
            shapes = cmds.listRelatives(selected_trs[0], shapes=True)

            if shapes and cmds.objectType(shapes[0]) == "lattice":
                lattice = selected_trs[0]

        else:
            # ラティス以外が選択されていた場合
            selection = cmds.ls(selection=True, flatten=True)
            selected_lattice_point = cmds.filterExpand(selection, sm=46)

            if selected_lattice_point:
                # ラティスポイントが選択されていた場合
                lattice_shape = cmds.polyListComponentConversion(selected_lattice_point[0])[0]
                lattice = cmds.listRelatives(lattice_shape, parent=True)[0]
                object_mode = False

        if not lattice:
            # リビルド対象が特定できなかった場合
            print("select lattice")
            return

    # 再分割対象ラティスのノード名取得
    lattice_trs = lattice
    lattice_name = cmds.listRelatives(lattice_trs, shapes=True)[0]

    # 再分割対象ラティスの分割数を保存
    orig_s = cmds.getAttr(lattice_name + ".sDivisions")
    orig_t = cmds.getAttr(lattice_name + ".tDivisions")
    orig_u = cmds.getAttr(lattice_name + ".uDivisions")

    # 引数が未指定の場合は元の分割数を使用
    s = s or orig_s
    t = t or orig_t
    u = u or orig_u

    # 再分割対象ラティスの CV 座標を保存
    old_pt_coords = [[[None for x in range(orig_u)] for x in range(orig_t)] for x in range(orig_s)]

    for s_i in range(orig_s):
        for t_i in range(orig_t):
            for u_i in range(orig_u):
                old_pt_coords[s_i][t_i][u_i] = cmds.xform(f"{lattice_name}.pt[{s_i}][{t_i}][{u_i}]", q=True, ws=True, t=True)

    # 対象ラティスをリセットして指定の分割数を設定
    cmds.lattice(lattice_name, e=True, latticeReset=True)
    cmds.setAttr(lattice_name + ".sDivisions", s)
    cmds.setAttr(lattice_name + ".tDivisions", t)
    cmds.setAttr(lattice_name + ".uDivisions", u)

    # ラティスを複製
    dup_lattice_trs = cmds.duplicate(lattice_name)[0]
    dup_lattice_name = cmds.listRelatives(dup_lattice_trs, shapes=True)[0]

    # 複製ラティスの外側に元の分割数でラティス作成
    outer_lattice_trs = cmds.lattice(dup_lattice_trs, divisions=(orig_s, orig_t, orig_u), ldivisions=(2, 2, 2), objectCentered=True)
    outer_lattice_name = cmds.listRelatives(outer_lattice_trs, shapes=True)[0]

    # 外側ラティスのポイントにリセット前の座標を設定
    for s_i in range(orig_s):
        for t_i in range(orig_t):
            for u_i in range(orig_u):
                lattice_pt = f"{outer_lattice_name}.pt[{s_i}][{t_i}][{u_i}]"
                cmds.xform(lattice_pt, ws=True, t=old_pt_coords[s_i][t_i][u_i])

    # 複製ラティスのポイントの座標を取得
    new_pt_coords = [[[None for x in range(u)] for x in range(t)] for x in range(s)]

    for s_i in range(s):
        for t_i in range(t):
            for u_i in range(u):
                new_pt_coords[s_i][t_i][u_i] = cmds.xform(f"{dup_lattice_name}.pt[{s_i}][{t_i}][{u_i}]", q=True, ws=True, t=True)

    # 複製ラティス･外側ラティスを削除
    cmds.delete(outer_lattice_trs)
    cmds.delete(dup_lattice_trs)

    # 再分割対象ラティスのポイントに座標を設定
    for s_i in range(s):
        for t_i in range(t):
            for u_i in range(u):
                lattice_pt = f"{lattice_name}.pt[{s_i}][{t_i}][{u_i}]"
                cmds.xform(lattice_pt, ws=True, t=new_pt_coords[s_i][t_i][u_i])

    # 実行時の選択モードに復帰する
    if object_mode:
        # ラティスのトランスフォームノードを選択した状態にする
        pm.selectMode(object=True)
        pm.select(lattice_trs, replace=True)
    else:
        pm.selectMode(component=True)
        pm.selectType(latticePoint=True)


def is_surface_indices(s, t, u, div_s, div_t, div_u):
    """ラティスの分割数とインデックスを渡してそれが表面にあれば True を返す

    Args:
        s (int): 表面にあるかチェックするインデックス
        t (int)): 表面にあるかチェックするインデックス
        u (int): 表面にあるかチェックするインデックス
        div_s (int): 分割数
        div_t (int): 分割数
        div_u (int): 分割数

    Returns:
        bool: 表面にあれば True を返す
    """
    return (s == 0 or s == div_s-1 or t == 0 or t == div_t-1 or u == 0 or u == div_u-1)


def smooth_lattice_point(ratio=0.1, prevent_dent=True):
    """
    選択されたラティスポイントのスムース

    """
    # 選択されているラティスポイント
    selected_lattice_points = [x for x in pm.selected(flatten=True) if type(x) == pm.LatticePoint]

    if not selected_lattice_points:
        return

    # ラティスオブジェクト
    lattice = nu.pynode(pm.polyListComponentConversion(selected_lattice_points[0])[0]).getParent()

    # インデックス範囲
    div_s, div_t, div_u = lattice.getDivisions()

    # ポイント毎の処理
    for pt in selected_lattice_points:
        s, t, u = pt.indices()[0]

        # 隣接ラティスポイントのインデックスの組み合わせ
        adjacent_indices_list = [
            (s, t, u+1),
            (s, t, u-1),
            (s, t+1, u),
            (s, t-1, u),
            (s+1, t, u),
            (s-1, t, u),
        ]

        # 隣接ラティスポイントの座標取得
        adjacent_points_coords = []

        for a_s, a_t, a_u, in adjacent_indices_list:
            if 0 <= a_s < div_s and 0 <= a_t < div_t and 0 <= a_u < div_u:
                if prevent_dent and is_surface_indices(s, t, u, div_s, div_t, div_u) and not is_surface_indices(a_s, a_t, a_u, div_s, div_t, div_u):
                    # 凹み抑止モードが有効なら対象ポイントが表面で比較ポイントが内部の場合無視する
                    continue
                else:
                    adjacent_points_coords.append(dt.Vector(pm.xform(lattice.pt[a_s][a_t][a_u], q=True, ws=True, t=True)))

        # 平均値で座標値を設定
        old_coord = dt.Vector(pm.xform(lattice.pt[s][t][u], q=True, ws=True, t=True))
        avg_coord = sum(adjacent_points_coords) / len(adjacent_points_coords)
        new_coord = old_coord * (1.0 - ratio) + avg_coord * ratio
        pm.xform(lattice.pt[s][t][u], ws=True, t=tuple(new_coord))


def select_inner(lattice=None):
    """ ラティスポイントの内側だけを選択する
    Args:
        lattice (Lattice):
    """
    # 対象ラティスの取得
    lattice, points = get_selected_lattice_and_points()

    # 最終的に選択するポイント
    selections = []

    div_s, div_t, div_u = lattice.getDivisions()

    for s in range(div_s):
        for t in range(div_t):
            for u in range(div_u):
                if not is_surface_indices(s, t, u, div_s, div_t, div_u):
                    selections.append(lattice.pt[s][t][u])

    pm.selectMode(component=True)
    pm.selectType(latticePoint=True)
    pm.select(selections, replace=True)


def select_surface(lattice=None):
    """ ラティスポイントの表面だけを選択する
    """
    # 対象ラティスの取得
    lattice, points = get_selected_lattice_and_points()

    # 最終的に選択するポイント
    selections = []

    div_s, div_t, div_u = lattice.getDivisions()

    for s in range(div_s):
        for t in range(div_t):
            for u in range(div_u):
                if is_surface_indices(s, t, u, div_s, div_t, div_u):
                    selections.append(lattice.pt[s][t][u])

    pm.selectMode(component=True)
    pm.selectType(latticePoint=True)
    pm.select(selections, replace=True)


def select_grow(r=1):
    """ ラティスポイントの選択を拡大する

    Args
        r (int, optinal):  拡大ホップ数
    """
    # 対象ラティスの取得
    lattice, points = get_selected_lattice_and_points()

    selected_indices = [tuple(p.indices()[0]) for p in points]

    # 最終的に選択するポイント
    selections = []

    div_s, div_t, div_u = lattice.getDivisions()

    for s in range(div_s):
        for t in range(div_t):
            for u in range(div_u):
                for ss, st, su in selected_indices:
                    if abs(s-ss) <= r and abs(t-st) <= r and abs(u-su) <= r:
                        selections.append(lattice.pt[s][t][u])
                    else:
                        continue

    pm.select(selections, replace=True)


def select_shrink():
    """ ラティスポイントの選択を縮小する
    """
    # 対象ラティスの取得
    lattice, points = get_selected_lattice_and_points()

    selected_indices = [tuple(p.indices()[0]) for p in points]

    # 最終的に選択するポイント
    selections = []

    div_s, div_t, div_u = lattice.getDivisions()

    for s in range(div_s):
        for t in range(div_t):
            for u in range(div_u):
                for ss, st, su in selected_indices:
                    if ((s, t, u) in selected_indices and
                        (s, t, u+1) in selected_indices and
                        (s, t, u-1) in selected_indices and
                        (s, t+1, u) in selected_indices and
                        (s, t-1, u) in selected_indices and
                        (s+1, t, u) in selected_indices and
                        (s-1, t, u) in selected_indices):

                        selections.append(lattice.pt[s][t][u])
                    else:
                        continue

    pm.select(selections, replace=True)


def toggle_envelope(lattices=None):
    # 対象ラティスの取得
    if not lattices:
        selected_lattice_point = [x for x in pm.selected(flatten=True) if type(x) == pm.LatticePoint]

        if selected_lattice_point:
            # ラティスポイントが選択されていた場合
            lattices = [nu.pynode(pm.polyListComponentConversion(selected_lattice_point[0])[0])]

        else:
            lattices = [x.getShape() for x in pm.selected(flatten=True) if hasattr(x, "getShape") and type(x.getShape()) == nt.Lattice]

        # ラティスもラティスポイントも選択されていなければシーン中の全てのラティス
        lattices = lattices or pm.ls(type="lattice")

        # 対象が無ければ終了
        if not lattices:
            print("select lattice")
            return

    # トグル後の値の決定
    ffd = pm.listConnections(lattices[0], type="ffd")[0]
    new_state = 0 if ffd.nodeState.get() == 1 else 1

    # 各ラティスの処理
    for lattice in lattices:
        ffd = pm.listConnections(lattice, type="ffd")[0]
        ffd.nodeState.set(new_state)

    # 新しくセットされた状態をインビューメッセージで表示
    if new_state == 0:
        nd.message("lattice state: Normal")
    else:
        nd.message("lattice state: No Effect")


def apply_lattice(lattices=[]):
    """ラティスの変形をコンポーネント座標に適用し、ラティスを削除する

    引数未指定の場合は選択オブジェクト中のラティスを使用する

    Args:
        lattices (list[Lattice]): 適用するラティス
    """
    # 引数が無効なら選択オブジェクトからラティスを取得する
    if not lattices:
        lattices = [x for sel in pm.selected(flatten=True) for x in pm.listRelatives(sel, ad=True) if isinstance(x, nt.Lattice)]

        if not lattices:
            raise(Exception)

    # 削除対象ラティス
    lattices_to_remove = []

    # シェイプと座標配列の辞書
    shape_points_table = dict()

    # ラティス毎の処理
    for lattice in lattices:
        # メンバーの取得
        objects = get_lattice_menber(lattice)

        # メンバー毎にシェイプと座標配列を取得する
        for obj in objects:
            if hasattr(obj, "getShape"):
                shape = obj.getShape()
            elif isinstance(obj, nt.Mesh):
                shape = obj
            else:
                continue

            points = shape.getPoints()
            lattices = [x for x in shape.connections() if isinstance(x, nt.Ffd)]
            lattices_to_remove.extend(lattices)
            shape_points_table[shape] = points

    lattices_to_remove = nu.uniq(lattices_to_remove)

    # ラティスの削除
    for lattice in lattices_to_remove:
        if pm.objExists(lattice):
            pm.delete(lattice)

    # シェイプにラティス削除前の座標を上書き
    for shape, points in shape_points_table.items():
        shape.setPoints(points)


def reset_lattice(lattices=[]):
    # 引数が無効なら選択オブジェクトからラティスを取得する
    if not lattices:
        lattices = [x for sel in pm.selected(flatten=True) for x in pm.listRelatives(sel, ad=True) if isinstance(x, nt.Lattice)]

        if not lattices:
            raise(Exception)

    for lattice in lattices:
        pm.lattice(e=True, latticeReset=True)


class NN_ToolWindow(object):

    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (window_width, window_height)

        pm.selectPref(trackSelectionOrder=True)

    def create(self):
        if pm.window(self.window, exists=True):
            pm.deleteUI(self.window, window=True)

        # プリファレンスの有無による分岐
        if pm.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = pm.windowPref(self.window, q=True, topLeftCorner=True)
            pm.windowPref(self.window, remove=True)

            # 前回位置に指定したサイズで表示
            pm.window(
                self.window,
                t=self.title,
                maximizeButton=False,
                minimizeButton=False,
                topLeftCorner=position,
                widthHeight=self.size,
                sizeable=False,
                resizeToFitChildren=True
                )

        else:
            # プリファレンスがなければデフォルト位置に指定サイズで表示
            pm.window(
                self.window,
                t=self.title,
                maximizeButton=False,
                minimizeButton=False,
                widthHeight=self.size,
                sizeable=False,
                resizeToFitChildren=True
                )

        self.layout()
        pm.showWindow(self.window)

    def layout(self):
        ui.column_layout()

        # 絶対モード

        ui.row_layout()
        ui.header(label='Divsions')
        self.rebuild_s = ui.eb_int(v=3, cc=self.onChangeS)
        self.rebuild_t = ui.eb_int(v=3, cc=self.onChangeT)
        self.rebuild_u = ui.eb_int(v=3, cc=self.onChangeU)
        ui.button(label='Get', c=self.onGetDivisions)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='Rebuild')
        ui.button(label='S', c=self.onRebuildS, width=ui.width(2))
        ui.button(label='T', c=self.onRebuildT, width=ui.width(2))
        ui.button(label='U', c=self.onRebuildU, width=ui.width(2))
        ui.button(label='STU', c=self.onRebuidLattice)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='-1', c=self.onSub1)
        ui.button(label='+1', c=self.onAdd1)
        ui.button(label='/2', c=self.onDiv2)
        ui.button(label='x2', c=self.onMul2)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='Func')
        ui.button(label='Smooth', c=self.onSmoothLatticePoint)
        self.cb_smooth_completely = ui.check_box(label="completely", v=False)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.button(label='Add Member', c=self.onAddMember)
        ui.button(label='Select Member', c=self.onSelectMember)
        ui.end_layout()
        ui.row_layout()

        ui.header(label="")
        ui.button(label='Apply Lattice', c=self.onApplyLattice)
        ui.button(label='Match Lattice', c=self.onMatchLattice)
        ui.button(label='Reset', c=self.onResetLattice)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='Select')
        ui.button(label='inner', c=self.onSelectInner)
        ui.button(label='surface', c=self.onSelectSurface)
        ui.button(label='grow', c=self.onSelectGrow)
        ui.button(label='shrink', c=self.onSelectShrink)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='Etc')
        ui.button(label='Toggle Envelope', c=self.onToggleEnvelope)
        ui.button(label='Hide Deformers', c=self.onHideDeformers)
        ui.end_layout()

        ui.end_layout()

    def onChangeS(self, *args):
        s = ui.get_value(self.rebuild_s)
        if s < 2:
            ui.set_value(self.rebuild_s, 2)

    def onChangeT(self, *args):
        t = ui.get_value(self.rebuild_t)
        if t < 2:
            ui.set_value(self.rebuild_t, 2)

    def onChangeU(self, *args):
        u = ui.get_value(self.rebuild_u)
        if u < 2:
            ui.set_value(self.rebuild_u, 2)

    def onGetDivisions(self, *args):
        """選択ラティスの分割数を取得して UI に設定する"""
        target_lattice = None
        selected_trs = cmds.ls(selection=True, type="transform")

        if selected_trs:
            shapes = cmds.listRelatives(selected_trs[0], shapes=True)

            if shapes and cmds.objectType(shapes[0]) == "lattice":
                target_lattice = selected_trs[0]

        if not target_lattice:
            # リビルド対象が特定できなかった場合
            print("select lattice")
            return

        lattice_trs = target_lattice
        lattice_name = cmds.listRelatives(lattice_trs, shapes=True)[0]

        s, t, u = get_divisions(lattice_name)

        ui.set_value(self.rebuild_s, s)
        ui.set_value(self.rebuild_t, t)
        ui.set_value(self.rebuild_u, u)

    # イベントハンドラ
    def onAddMember(self, *args):
        add_lattice_menber()

    def onMatchLattice(self, *args):
        match_latice()

    def onSelectMember(self, *args):
        select_lattice_menber()

    def onApplyLattice(self, *args):
        apply_lattice()

    def onResetLattice(self, *args):
        reset_lattice()

    def onDiv2(self, *args):
        s = ui.get_value(self.rebuild_s)
        t = ui.get_value(self.rebuild_t)
        u = ui.get_value(self.rebuild_u)

        s = max((s + 1) // 2, 2)
        t = max((t + 1) // 2, 2)
        u = max((u + 1) // 2, 2)

        ui.set_value(self.rebuild_s, s)
        ui.set_value(self.rebuild_t, t)
        ui.set_value(self.rebuild_u, u)

    def onMul2(self, *args):
        s = ui.get_value(self.rebuild_s)
        t = ui.get_value(self.rebuild_t)
        u = ui.get_value(self.rebuild_u)

        s = s * 2 - 1
        t = t * 2 - 1
        u = u * 2 - 1

        ui.set_value(self.rebuild_s, s)
        ui.set_value(self.rebuild_t, t)
        ui.set_value(self.rebuild_u, u)

    def onSub1(self, *args):
        s = ui.get_value(self.rebuild_s)
        t = ui.get_value(self.rebuild_t)
        u = ui.get_value(self.rebuild_u)

        s = max(s - 1, 2)
        t = max(t - 1, 2)
        u = max(u - 1, 2)

        ui.set_value(self.rebuild_s, s)
        ui.set_value(self.rebuild_t, t)
        ui.set_value(self.rebuild_u, u)

    def onAdd1(self, *args):
        s = ui.get_value(self.rebuild_s)
        t = ui.get_value(self.rebuild_t)
        u = ui.get_value(self.rebuild_u)

        s = s + 1
        t = t + 1
        u = u + 1

        ui.set_value(self.rebuild_s, s)
        ui.set_value(self.rebuild_t, t)
        ui.set_value(self.rebuild_u, u)

    def onRebuidLattice(self, *args):
        s = ui.get_value(self.rebuild_s)
        t = ui.get_value(self.rebuild_t)
        u = ui.get_value(self.rebuild_u)
        rebuild_lattice(s=s, t=t, u=u)

    def onRebuildS(self, *args):
        s = ui.get_value(self.rebuild_s)
        rebuild_lattice(s=s)

    def onRebuildT(self, *args):
        t = ui.get_value(self.rebuild_t)
        rebuild_lattice(t=t)

    def onRebuildU(self, *args):
        u = ui.get_value(self.rebuild_u)
        rebuild_lattice(u=u)

    def onSmoothLatticePoint(self, *args):
        if ui.get_value(self.cb_smooth_completely):
            smooth_lattice_point(ratio=1.0)
        else:
            smooth_lattice_point()

    def onSelectInner(self, *args):
        select_inner()

    def onSelectSurface(self, *args):
        select_surface()

    def onSelectGrow(self, *args):
        select_grow()

    def onSelectShrink(self, *args):
        select_shrink()

    def onToggleEnvelope(self, *args):
        toggle_envelope()

    def onHideDeformers(self, *args):
        """"""
        all_model_panels = cmds.getPanel(type="modelPanel")

        if not all_model_panels:
            raise

        current_value = cmds.modelEditor(all_model_panels[0], q=True, deformers=True)
        new_value = not current_value

        for panel in all_model_panels:
            pm.modelEditor(panel, e=True, deformers=new_value)


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
