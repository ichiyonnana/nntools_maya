import math
import re
import maya.cmds as cmds
import maya.mel as mel

import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

import nnutil.core as nu
import nnutil.ui as ui
import nnutil.decorator as deco


window_name = "NN_Skin"
window = None


def get_window():
    return window


def get_skincluster(target):
    """
    スキンクラスターの取得
    """
    object = nu.get_object(target)
    sc = mel.eval("findRelatedSkinCluster %(object)s" % locals())
    return sc


def conv_to_vtx(target):
    """
    target を頂点に変換する
    オブジェクトの場合
        オブジェクトの持つすべての頂点
    頂点の場合
        そのまま返す
    エッジの場合
        エッジの持つすべての頂点
    フェースの場合
        フェースの持つすべての頂点
    """

    vtx_list = cmds.polyListComponentConversion(target, tv=True)
    vtx_list_flatten = cmds.filterExpand(vtx_list, sm=31)

    return vtx_list_flatten


def get_vtx_weight(vtx):
    """
    指定した頂点のインフルエンスとウェイトの組を辞書で返す
    """
    sc = get_skincluster(nu.get_object(vtx))
    influence_list = cmds.skinCluster(sc, q=True, influence=True)
    weight_list = cmds.skinPercent(sc, vtx, q=True, value=True)
    influence_weight_dic = {}

    for i in range(len(influence_list)):
        influence_weight_dic[influence_list[i]] = weight_list[i]

    return influence_weight_dic


def curve_function(x, mode, formula=None):
    x = min(max(x, 0.0), 1.0)

    if mode == "linear":
        return x

    if mode == "cosine":
        return 0.5 - 0.5 * math.cos(math.pi * x)

    if mode == "formula":
        def f(x):
            return eval(formula)

        y_min = float('inf')
        y_max = float('-inf')

        resolution = 100
        for i in range(0, resolution+1):
            y = f(i / resolution)

            if y < y_min:
                y_min = y

            if y > y_max:
                y_max = y

        return (f(x) - y_min) / (y_max - y_min)

    else:
        raise ValueError(f"不明なモード: {mode}")


def _linearize_weight(target, end_vts_weights, end_vts_points, mode="linear", formula=None):
    """
    指定した代表点のウェイトと座標で指定した対象頂点のウェイトをリニアにする
    vts:
        操作対象頂点
    end_vts_weights:
        複数代表点のインフルエンス-ウェイト辞書をリストでまとめたもの
        [{i1:w1, i2:w2 ...}, {i1:w1, i2:w2 ...}, ...]
    end_vts_points:
        複数代表点の座標をリストでまとめたもの
        [[x,y,z], [x,y,z], ...]
    """

    # 頂点に変換
    vts = conv_to_vtx(target)

    # スキンクラスター取得
    sc = get_skincluster(nu.get_object(vts[0]))

    # 各頂点に対して、代表頂点を結ぶ直線上の最も近い点を求め
    # その点の位置で代表頂点のウェイトを内分した値を設定する
    for vtx in vts:

        # 代表点間の距離
        total_distance = nu.distance(end_vts_points[0], end_vts_points[1])

        # 操作対象の頂点に一番近い直線上の座標を求める
        # この点が代表点間の線分範囲外なら値は近い方の代表点のウェイトで飽和させる (ウェイトの性質上外延はしたくない)
        ratio0 = 1  # end_vts_weights[0] の割合
        nearest_point = nu.nearest_point_on_line(end_vts_points[0], end_vts_points[1], nu.point_from_vertex(vtx))
        d0 = nu.distance(nearest_point, end_vts_points[0])
        d1 = nu.distance(nearest_point, end_vts_points[1])
        if d0 > total_distance or d1 > total_distance:
            if d0 < d1:
                ratio = 1
            else:
                ratio = 0
        else:
            u = 1 - d0 / total_distance
            ratio = curve_function(u, mode=mode, formula=formula)

        # 最終的に頂点に適用するウェイト
        interior_division_weight = {}

        # interior_division_weight に比率をかけたウェイトを合成する
        for influence in end_vts_weights[0].keys():
            if influence not in interior_division_weight:
                interior_division_weight[influence] = 0
            interior_division_weight[influence] = end_vts_weights[0][influence] * ratio + end_vts_weights[1][influence] * (1 - ratio)

        # 頂点に内分したウェイトを適用
        weight_list = [(i, w) for i, w in interior_division_weight.items()]
        cmds.skinPercent(sc, vtx, transformValue=weight_list)


@deco.repeatable
def linearize_weight_with_farthest_points(mode, formula):
    """
    選択頂点のウェイトを距離でリニアにする
    代表点も選択頂点内から選ぶ
    """

    selections = cmds.ls(selection=True, flatten=True)
    vts = conv_to_vtx(selections)

    # 最も離れた2点を代表点にする
    end_vts = nu.get_most_distant_vts(vts)

    # 代表点のウェイトリストと座標リスト
    end_vts_weights = [get_vtx_weight(vtx) for vtx in end_vts]
    end_vts_points = [nu.point_from_vertex(vtx) for vtx in end_vts]
    _linearize_weight(vts, end_vts_weights, end_vts_points, mode=mode, formula=formula)


# linearize_weight_selected_with_specified_end_points で使用する代表点情報
specified_end_vts_weights = []
specified_end_vts_points = []


@deco.repeatable
def set_end_point_with_selection():
    """
    選択コンポーネントの平均値を代表点に設定する
    """
    selections = cmds.ls(selection=True, flatten=True)
    vts = conv_to_vtx(selections)
    set_end_point_with_vts(vts)


@deco.repeatable
def set_multi_end_points_with_selection():
    """
    複数ある選択コンポーネントで複数代表点を設定する
    """
    selections = cmds.ls(selection=True, flatten=True)
    vts = conv_to_vtx(selections)

    for vtx in vts:
        set_end_point_with_vts([vtx])


@deco.repeatable
def set_end_point_with_vts(vts):
    """
    選択コンポーネントを代表点にする
    複数ある場合は平均位置の平均ウェイト
    """

    global specified_end_vts_weights
    global specified_end_vts_points

    # 1頂点1辞書でウェイト取得してリストにする
    vts_weight = [get_vtx_weight(vtx) for vtx in vts]

    # 平均化
    avg_vtc_weight = {}
    vts_count = len(vts)

    for vtx_weight in vts_weight:
        for influence, weight in vtx_weight.items():
            if influence not in avg_vtc_weight:
                avg_vtc_weight[influence] = 0
            avg_vtc_weight[influence] += weight / vts_count

    points = [nu.point_from_vertex(vtx) for vtx in vts]
    avg_vtc_point = [sum([point[0] for point in points]) / vts_count,
                     sum([point[1] for point in points]) / vts_count,
                     sum([point[2] for point in points]) / vts_count]

    if len(specified_end_vts_weights) < 2:
        specified_end_vts_weights.append(avg_vtc_weight)
        specified_end_vts_points.append(avg_vtc_point)

    specified_end_vts_weights = [avg_vtc_weight, specified_end_vts_weights[0]]
    specified_end_vts_points = [avg_vtc_point, specified_end_vts_points[0]]


@deco.repeatable
def linearize_weight_with_specified_points(mode, formula=None):
    """
    選択頂点のウェイトを距離でリニアにする
    代表点は事前に指定したものを使用する
    """
    global specified_end_vts_weights
    global specified_end_vts_points

    selections = cmds.ls(selection=True, flatten=True)
    vts = conv_to_vtx(selections)

    # 最も離れた2点を代表点にする
    end_vts = nu.get_most_distant_vts(vts)

    # 代表点のウェイトリストと座標リスト
    _linearize_weight(vts, specified_end_vts_weights, specified_end_vts_points, mode=mode, formula=formula)


# ウェイトのコピー元になる代理頂点
proxy_vts = []


@deco.repeatable
def set_proxy_vts(vts):
    proxy_vts = vts


def copy_from_proxy_vts():
    """
    連続する選択頂点内に代理頂点が含まれていれば連続する頂点内をすべて代理頂点のウェイトに設定する
    """
    pass


# コピーしているウェイト情報を持つ辞書
weightclipboard = None


def copy_weight(selections=None):
    """
    選択頂点からウェイトをコピーする
    複数頂点ある場合は平均化して保存する
    """
    global weightclipboard

    selections = cmds.ls(selection=True, flatten=True)
    vts = conv_to_vtx(selections)
    # 1頂点1辞書でウェイト取得してリストにする
    vts_weight = [get_vtx_weight(vtx) for vtx in vts]

    # 平均化
    avg_vtc_weight = {}
    vts_count = len(vts)

    for vtx_weight in vts_weight:
        for influence, weight in vtx_weight.items():
            if influence not in avg_vtc_weight:
                avg_vtc_weight[influence] = 0
            avg_vtc_weight[influence] += weight / vts_count

    weightclipboard = avg_vtc_weight


def paste_weight(selections=None):
    paste_weight_as_possible(selections)


def paste_weight_as_possible(selections=None):
    """
    選択頂点へ保存したウェイトをペーストする
    すでに存在するインフルエンスにのみウェイトをペーストする
    """
    global weightclipboard

    # コピーしているウェイト情報が無ければ終了
    if not weightclipboard:
        return

    # 引数で操作対象が指定されていなければ現在の選択コンポーネントを使用する
    if not selections:
        selections = cmds.ls(selection=True, flatten=True)

    # この時点で操作対象がなければ終了 (引数未指定かつコンポーネント未選択)
    if len(selections) == 0:
        return

    vts = conv_to_vtx(selections)
    sc = get_skincluster(vts[0])
    for vtx in vts:
        weight_list = [(i, w) for i, w in weightclipboard.items()]
        cmds.skinPercent(sc, vtx, transformValue=weight_list)


def paste_weight_force(selections=None):
    """
    選択頂点へ保存したウェイトをペーストする
    別オブジェクトへのペースト等でインフルエンスが足りないときは add influence する
    """

    influences = weightclipboard.keys()
    obj = nu.get_object(selections)
    cmds.addInfluence(obj, influences)
    paste_weight_as_possible(selections)


def average_weight(selections=None):
    """選択範囲のウェイトを平均化する"""
    global weightclipboard

    tmp = weightclipboard
    copy_weight()
    paste_weight_as_possible()
    weightclipboard = tmp


def get_influence_order(obj):
    skincluster = get_skincluster(obj)

    if skincluster:
        return cmds.skinCluster(skincluster, q=True, influence=True)

    if not skincluster:
        return None


def set_influence_order(obj, influence_order):
    # バインド済みか調べる
    current_skincluster = get_skincluster(obj)
    bound = bool(current_skincluster)

    # APIオブジェクトの初期化
    slist = om.MGlobal.getSelectionListByName(obj)
    dp_obj, comp = slist.getComponent(0)
    fn_mesh = om.MFnMesh(dp_obj)

    if bound:
        # バインド済みならウェイトを保存してアンバインド

        # 現在のウェイトを取得
        dg_skincluster = om.MGlobal.getSelectionListByName(current_skincluster).getDependNode(0)
        fn_skin = oma.MFnSkinCluster(dg_skincluster)

        weights = fn_skin.getWeights(dp_obj, om.MObject.kNullObj)[0]
        influences = cmds.skinCluster(current_skincluster, q=True, influence=True)
        num_influence = len(influences)
        num_vtx = fn_mesh.numVertices
        inf_to_weights = dict()

        # ひとかたまりのウェイトのリストから インフルエンス名:ウェイト の辞書を作成する
        for i, influence in enumerate(influences):
            weights_per_vertex = num_vtx * num_influence
            inf_to_weights[influence] = weights[i::num_influence]

        # バインドポーズに戻す
        bindpose = cmds.listConnections(current_skincluster, source=True, type="dagPose")
        cmds.dagPose(bindpose, restore=True )
        cmds.skinCluster(obj, e=True, unbind=True)

    # 指定の順序でバインド
    print("インフルエンス順の変更: ", obj, influence_order)
    cmds.skinCluster(influence_order, obj, bindMethod=0, toSelectedBones=True, removeUnusedInfluence=False)

    if bound:
        # ウェイトの復帰
        new_skincluster = get_skincluster(obj)
        dg_skincluster = om.MGlobal.getSelectionListByName(new_skincluster).getDependNode(0)
        fn_skin = oma.MFnSkinCluster(dg_skincluster)
        influence_indices = om.MIntArray(list(range(len(fn_skin.influenceObjects()))))
        fn_comp = om.MFnSingleIndexedComponent()
        all_vtx_comp = fn_comp.create(om.MFn.kMeshVertComponent)
        fn_comp.addElements(list(range(fn_mesh.numVertices)))

        # 保存済みのウェイトを指定のインフルエンス順に並べ直す
        sorted_weights = []
        for vi in range(num_vtx):
            for inf in influence_order:
                if inf in inf_to_weights:
                    sorted_weights.append(inf_to_weights[inf][vi])
                else:
                    sorted_weights.append(0.0)

        # ウェイトの設定
        fn_skin.setWeights(dp_obj, all_vtx_comp, influence_indices, om.MDoubleArray(sorted_weights))


def copy_weights_from_nearest_unselected_vertex(max_distance=1.0):
    """選択頂点に対して一番近い非選択頂点からウェイトをコピーする｡"""
    # 選択を頂点に変換
    selection = cmds.ls(selection=True, flatten=True)
    vtx_list = cmds.polyListComponentConversion(selection, toVertex=True)
    sel_vtx = cmds.filterExpand(vtx_list, sm=31) if vtx_list else []

    if not sel_vtx:
        cmds.warning("頂点を選択してください。")
        return

    mesh = cmds.polyListComponentConversion(sel_vtx[0])[0]
    all_vtx = cmds.ls(mesh + ".vtx[*]", flatten=True)
    sel_set = set(sel_vtx)
    unsel_vtx = [v for v in all_vtx if v not in sel_set]

    def grid_key(pos):
        """座標をグリッドキーに変換して返す"""
        return (int(pos[0] // max_distance), int(pos[1] // max_distance), int(pos[2] // max_distance))

    # 非選択頂点を座標毎に区切って辞書に格納
    grid = {}  # key: (vtx, pos)
    for v in unsel_vtx:
        pos = cmds.pointPosition(v, world=True)
        key = grid_key(pos)
        grid.setdefault(key, []).append((v, pos))

    # スキンクラスターを取得
    sc_list = cmds.ls(cmds.listHistory(mesh), type="skinCluster")

    if not sc_list:
        cmds.warning("スキンクラスターが見つかりません。")
        return
        
    sc = sc_list[0]
    influences = cmds.skinCluster(sc, q=True, inf=True)

    # 選択頂点に対して最も近い非選択頂点からウェイトをコピー
    failed_vtx = []
    max_dist2 = max_distance * max_distance
    for v in sel_vtx:
        # 座標を取得し隣接グリッドから座標を取得
        pos = cmds.pointPosition(v, world=True)
        key = grid_key(pos)
        candidates = []
        for offset_x in [-1, 0, 1]:
            for offset_y in [-1, 0, 1]:
                for offset_z in [-1, 0, 1]:
                    k = (key[0]+offset_x, key[1]+offset_y, key[2]+offset_z)
                    candidates.extend(grid.get(k, []))

        # 隣接グリッドから取得した候補頂点から最も近い頂点を選択
        min_dist2 = None
        nearest = None
        for vtx, coord in candidates:
            dist2 = (pos[0]-coord[0])**2 + (pos[1]-coord[1])**2 + (pos[2]-coord[2])**2
            if min_dist2 is None or dist2 < min_dist2:
                min_dist2 = dist2
                nearest = vtx

        # 指定の距離よりも近い頂点が見つかった場合、ウェイトをコピーする
        # 見つからなかった場合はコピー失敗頂点としてリストに追加する
        if nearest and min_dist2 < max_dist2:
            w = cmds.skinPercent(sc, nearest, q=True, value=True)
            weight_list = list(zip(influences, w))
            cmds.skinPercent(sc, v, transformValue=weight_list)
        else:
            failed_vtx.append(v)

    # コピー失敗頂点を選択し、メッセージを表示
    cmds.warning(f"コピー失敗: {len(failed_vtx)}/{len(sel_vtx)}")

    if failed_vtx:
        cmds.select(failed_vtx, replace=True)
        
###################################################################################################
###################################################################################################
# UI部

class NN_ToolWindow(object):

    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (10, 10)

        self.ring_source_vertices = []
        self.copied_influence_order = []

    def create(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)

        # プリファレンスの有無による分岐
        if cmds.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = cmds.windowPref(self.window, q=True, topLeftCorner=True)
            cmds.windowPref(self.window, remove=True)

            # 前回位置に指定したサイズで表示
            cmds.window(
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
            cmds.window(
                self.window,
                t=self.title,
                maximizeButton=False,
                minimizeButton=False,
                widthHeight=self.size,
                sizeable=False,
                resizeToFitChildren=True
                )

        self.layout()
        cmds.showWindow(self.window)

    def layout(self):
        ui.column_layout()

        ui.row_layout()
        ui.header(label="Set")
        cmds.button(l='End (Avg)', c=self.on_set_end_point)
        cmds.button(l='End (Multi)', c=self.on_set_multi_end_point)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Linearize")
        cmds.button(l='Specified', c=self.on_linearize_specified)
        cmds.button(l='End to End')
        cmds.button(l='Farthest', c=self.on_linearize_farthest)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Mode")
        self.rbc_mode = ui.radio_collection()
        ui.radio_button(label="Linear", width=ui.width(2), select=True)
        ui.radio_button(label="Cosine", width=ui.width(2))
        ui.radio_button(label="Gaussian", width=ui.width(2))
        ui.radio_button(label="Formula", width=ui.width(2))
        ui.end_layout()  # radio_collection
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Formula")
        ui.text(label="f(x) = ", width=ui.width(1.5))
        self.eb_formula = ui.eb_text(text="", width=ui.width(6))
        ui.end_layout()

        ui.row_layout()
        ui.header(label="RingCopy")
        ui.button(label="Set Ring Source", c=self.on_set_ring_source)
        ui.button(label="Ring Paste", c=self.on_ring_paste)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="CopyPaste")
        cmds.button(l='copy', c=self.on_copy)
        cmds.button(l='paste_p', c=self.on_paste_possible)
        cmds.button(l='paste_f', c=self.on_paste_force)
        cmds.button(l='avg', c=self.on_average)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.button(label='copy from nearest', c=self.on_copy_from_nearest)
        self.eb_max_distance = ui.eb_float(v=1.0)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Inf Order")
        cmds.button(l='copy', c=self.on_copy_influence_order)
        cmds.button(l='paste', c=self.on_paste_influence_order)
        cmds.button(l='compare', c=self.on_compare_influence_order)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Replace")
        self.eb_replace_before = ui.eb_text(width=ui.width(3))
        self.eb_replace_after = ui.eb_text(width=ui.width(3))
        ui.button(label="Replace", c=self.on_replace)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Etc")
        cmds.button(l='Checker', c=self.on_skin_checker)
        cmds.button(l='SIWE', c=self.on_siwe)
        ui.end_layout()

        ui.row_layout()
        ui.header()
        cmds.button(l='Delete Dup Orig', c=self.on_delete_non_connected_orig_mesh)
        cmds.button(l='Check Fractions', c=self.on_check_fractions)
        ui.end_layout()

        ui.end_layout()

    @deco.undo_chunk
    def on_set_end_point(self, *args):
        set_end_point_with_selection()

    @deco.undo_chunk
    def on_set_multi_end_point(self, *args):
        set_multi_end_points_with_selection()

    @deco.undo_chunk
    def on_set_proxy_point(self, *args):
        selection = cmds.ls(selection=True, flatten=True)
        vts = conv_to_vtx(selection)
        set_proxy_vts(vts)

    @deco.undo_chunk
    def on_linearize_farthest(self, *args):
        linearize_weight_with_farthest_points(mode=self._get_mode(), formula=self.get_formula())

    def _get_mode(self):
        radio_button_name = cmds.radioCollection(self.rbc_mode, q=True, select=True)

        return cmds.radioButton(radio_button_name, q=True, label=True).lower()

    def get_formula(self):
        return ui.get_value(self.eb_formula)

    @deco.undo_chunk
    def on_linearize_specified(self, *args):
        linearize_weight_with_specified_points(mode=self._get_mode(), formula=self.get_formula())

    @deco.undo_chunk
    def on_copy_proxy(self, *args):
        copy_from_proxy_vts()

    def on_copy_influence_order(self, *args):
        """選択オブジェクトのインフルエンス順序を保存する"""
        selections = cmds.ls(selection=True, flatten=True)

        if not selections:
            print("バインドされたメッシュを選択してください｡")
            return

        obj = selections[0]
        skincluster = get_skincluster(obj)

        if not skincluster:
            print("バインドされたメッシュを選択してください｡")
            return

        # インフルエンスの順序を保存する
        self.copied_influence_order = get_influence_order(obj)
        print("インフルエンス順をコピー:", self.copied_influence_order)

    def on_paste_influence_order(self, *args):
        """選択オブジェクトのインフルエンス順序をコピーした順序に一致させる"""
        selections = cmds.ls(selection=True, flatten=True)

        if not selections:
            print("オブジェクトを選択してください｡")
            return

        # 全オブジェクトのインフルエンス順序を設定する
        for obj in selections:
            set_influence_order(obj, self.copied_influence_order)

        # 選択の復帰
        cmds.select(selections, replace=True)

    def on_compare_influence_order(self, *args):
        """選択オブジェクトのインフルエンス順序を比較する"""
        selections = cmds.ls(selection=True, flatten=True)

        if not selections:
            print("バインドされたメッシュを選択してください｡")
            return

        for obj in selections:
            dst_skincluster = get_skincluster(obj)
            dst_influence_order = cmds.skinCluster(dst_skincluster, q=True, influence=True)

            if self.copied_influence_order != dst_influence_order:
                print(f"不一致: {obj}")
                print("    ", self.copied_influence_order)
                print("    ", dst_influence_order)
            else:
                print(f"一致: {obj}")



    @deco.undo_chunk
    def on_copy(self, *args):
        copy_weight()

    @deco.undo_chunk
    def on_paste_possible(self, *args):
        paste_weight_as_possible()

    @deco.undo_chunk
    def on_paste_force(self, *args):
        paste_weight_force()

    @deco.undo_chunk
    def on_average(self, *args):
        copy_weight()
        paste_weight_as_possible()

    def on_copy_from_nearest(self, *args):
        max_distance = ui.get_value(self.eb_max_distance)
        if max_distance <= 0:
            max_distance = 0.000001
        copy_weights_from_nearest_unselected_vertex(max_distance=max_distance)

    def on_replace(self, *args):
        # 置換用文字列
        before = ui.get_value(self.eb_replace_before)
        after = ui.get_value(self.eb_replace_after)

        if not before or not after:
            return

        target_vertices = cmds.ls(selection=True, flatten=True)
        if not target_vertices:
            return

        skincluster = get_skincluster(target_vertices[0])

        if not skincluster:
            return

        influences = cmds.skinCluster(skincluster, q=True, influence=True)

        for vtx in target_vertices:
            weights = cmds.skinPercent(skincluster, vtx, q=True, value=True)
            influences_with_weights = [influences[i] for i, weight in enumerate(weights) if weight > 0]

            for before_name in influences_with_weights:
                # 名前の置換
                after_name = re.sub(before, after, before_name)

                if before_name == after_name:
                    continue

                # 置換後の名前が存在すればウェイトを移動する
                if after_name in influences:
                    print(f"move: {before_name} -> {after_name}")
                    cmds.skinPercent(skincluster, vtx, transformMoveWeights=[before_name, after_name])

    def on_delete_non_connected_orig_mesh(self, *args):
        error_objects = []

        for mesh in cmds.ls(type="mesh"):
            if cmds.getAttr(mesh + ".intermediateObject") and not cmds.listConnections(mesh, destination=True):
                error_objects.append(mesh)

        if error_objects:
            print(error_objects)
            cmds.delete(error_objects)

    def on_skin_checker(self, *args):
        import nnskin.check_skin_tool
        nnskin.check_skin_tool.main()

    def on_siwe(self, *args):
        import siweighteditor.siweighteditor
        siweighteditor.siweighteditor.Option()

    def on_check_fractions(self, *args):
        import nnskin.check_weights_fractions
        nnskin.check_weights_fractions.main()

    def on_set_ring_source(self, *args):
        """Ring Paste のソースとなる頂点を保存する"""
        selection = cmds.ls(selection=True, flatten=True)
        if not selection:
            print("Select vertices to set as ring source")
            return

        self.ring_source_vertices = conv_to_vtx(selection)
        print(f"Vertices as ring source: {self.ring_source_vertices}")

    def on_ring_paste(self, *args):
        """選択したエッジ列の中にソースとなる頂点が含まれていればその頂点のウェイトをエッジ列にペーストする"""
        # 選択エッジを連続するエッジ列ごとに分割
        selection = cmds.ls(selection=True, flatten=True)
        if not selection:
            print("Select vertices to paste ring")
            return

        edges = cmds.filterExpand(selection, sm=32)
        if not edges:
            print("Select edges to paste ring")
            return

        polylines = nu.get_all_polylines(edges)

        # エッジ列ごとにペースト処理
        for edges in polylines:
            target_vertices = [x for x in conv_to_vtx(edges) if x not in self.ring_source_vertices]
            print("target vertices: ", target_vertices)

            source_vertices = [x for x in conv_to_vtx(edges) if x in self.ring_source_vertices]
            if not source_vertices:
                print("No source vertices in selection")
                continue

            # ソースからターゲットへウェイトをコピー
            cmds.select(source_vertices)
            copy_weight()
            cmds.select(target_vertices)
            paste_weight()


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
