#! python
# coding:utf-8

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

window_width = 300
header_width = 50


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


def rebuild_lattice(lattice=None, s=2, t=2, u=2):
    """ラティスの分割数を変更する｡現状 Undo 不可

    Args:
        s (int):
        t (int):
        u (int):
    """
    # 処理終了後に設定する編集モード
    object_mode = pm.selectMode(q=True, object=True)

    # 対象ラティスの取得
    if not lattice:
        selected_lattice_point = [x for x in pm.selected(flatten=True) if type(x) == pm.LatticePoint]

        if selected_lattice_point:
            # ラティスポイントが選択されていた場合
            lattice = nu.pynode(pm.polyListComponentConversion(selected_lattice_point[0])[0]).getParent()
            object_mode = False

        else:            
            selected_lattice = [x for x in pm.selected(flatten=True) if hasattr(x, "getShape") and type(x.getShape()) == nt.Lattice]

            if selected_lattice:
                # ラティスが選択されていた場合    
                lattice = selected_lattice[0]

        if not lattice:
            # リビルド対象が特定でき無かった場合
            print("select lattice")
            return

    # 対象ラティスのノード取得
    lattice_trs = lattice
    lattice_node = lattice.getShape()
    
    # 対象ラティスの分割数を保存
    orig_s, orig_t, orig_u = lattice_node.getDivisions()
    
    # 対象ラティスの CV 座標を保存
    old_pt_coords = [[[None for x in range(orig_u)] for x in range(orig_t)] for x in range(orig_s)]
    
    for s_i in range(orig_s):
        for t_i in range(orig_t):
            for u_i in range(orig_u):
                old_pt_coords[s_i][t_i][u_i] = pm.xform(lattice_node.pt[s_i][t_i][u_i], q=True, ws=True, t=True)

    # 対象ラティスのリセットと分割数設定
    lattice_node.reset()
    lattice_node.setDivisions(s, t, u)

    # 対象ラティスの外側に元の分割数でラティス作成
    pm.select(clear=True)
    pm.select(lattice_trs)
    mel.eval("CreateLattice")
    outer_lattice_trs = pm.selected(flatten=True)[0]
    outer_lattice_node = outer_lattice_trs.getShape()

    # 外側ラティスに分割数とCV座標設定
    outer_lattice_node.setDivisions(orig_s, orig_t, orig_u)

    # 外側ラティスのポイントに座標設定
    for s_i in range(orig_s):
        for t_i in range(orig_t):
            for u_i in range(orig_u):
                # ラティスポイントオブジェクト
                new_pt = outer_lattice_node.pt[s_i][t_i][u_i]

                # ラティスポイントのローカル座標取得
                # from_coord = lattice_node.point(s_i, t_i, u_i)
                # to_coord = to_lattice_node.point(s_i, t_i, u_i)

                # ラティスポイントをワールド座標で設定
                pm.xform(new_pt, ws=True, t=old_pt_coords[s_i][t_i][u_i])

    # 外側ラティスの適用
    pm.select(lattice_node, replace=True)
    pm.delete(ch=True)

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


class NN_ToolWindow(object):

    def __init__(self):
        self.window = 'NN_Lattice'
        self.title = 'NN_Lattice'
        self.size = (window_width, 95)

        pm.selectPref(trackSelectionOrder=True)

    def create(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)
        self.window = cmds.window(
            self.window,
            t=self.title,
            widthHeight=self.size
        )
        self.layout()
        cmds.showWindow()

    def layout(self):
        ui.column_layout()

        # 絶対モード

        ui.row_layout()
        ui.header(label='Divsions')
        self.rebuild_s = ui.eb_int(v=3)
        self.rebuild_t = ui.eb_int(v=3)
        self.rebuild_u = ui.eb_int(v=3)
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
        ui.button(label='Rebuild', c=self.onRebuidLattice)
        ui.button(label='Smooth', c=self.onSmoothLatticePoint)
        self.cb_smooth_completely = ui.check_box(label="completely", v=False)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.button(label='Add Member', c=self.onAddMember)
        ui.button(label='Match Lattice', c=self.onMatchLattice)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='Select')
        ui.button(label='inner', c=self.onSelectInner)
        ui.button(label='surface', c=self.onSelectSurface)
        ui.button(label='grow', c=self.onSelectGrow)
        ui.button(label='shrink', c=self.onSelectShrink)
        ui.end_layout()

        ui.end_layout()

    # イベントハンドラ
    def onAddMember(self, *args):
        add_lattice_menber()

    def onMatchLattice(self, *args):
        match_latice()

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


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
