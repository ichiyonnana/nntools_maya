#! python
# coding:utf-8

import pymel.core as pm
import maya.cmds as cmds
import maya.mel as mel

import nnutil.core as nu
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


def _linearize_weight(target, end_vts_weights, end_vts_points):
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
            ratio = 1 - d0 / total_distance

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
def linearize_weight_with_farthest_points():
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
    _linearize_weight(vts, end_vts_weights, end_vts_points)


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
def linearize_weight_with_specified_points():
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
    _linearize_weight(vts, specified_end_vts_weights, specified_end_vts_points)


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
        cmds.skinPercent(sc, vts, transformValue=weight_list)


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


###################################################################################################
###################################################################################################
# UI部

class NN_ToolWindow(object):

    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (350, 95)

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
        cmds.columnLayout()

        cmds.rowLayout(numberOfColumns=10)
        cmds.text(label='set')
        cmds.setParent("..")

        cmds.rowLayout(numberOfColumns=10)
        cmds.button(l='end (avg)', c=self.on_set_end_point)
        cmds.button(l='end (multi)', c=self.on_set_multi_end_point)
        cmds.button(l='proxy', c=self.on_set_proxy_point)
        cmds.setParent("..")

        cmds.rowLayout(numberOfColumns=10)
        cmds.text(label='linearize')
        cmds.setParent("..")

        cmds.rowLayout(numberOfColumns=10)
        cmds.button(l='specified', c=self.on_linearize_specified)
        cmds.button(l='farthest', c=self.on_linearize_farthest)
        cmds.button(l='proxy', c=self.on_copy_proxy)
        cmds.setParent("..")

        cmds.rowLayout(numberOfColumns=10)
        cmds.text(label='copy & paste')
        cmds.setParent("..")

        cmds.rowLayout(numberOfColumns=10)
        cmds.button(l='copy', c=self.on_copy)
        cmds.button(l='paste_p', c=self.on_paste_possible)
        cmds.button(l='paste_f', c=self.on_paste_force)
        cmds.button(l='avg', c=self.on_average)
        cmds.setParent("..")

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
        linearize_weight_with_farthest_points()

    @deco.undo_chunk
    def on_linearize_specified(self, *args):
        linearize_weight_with_specified_points()

    @deco.undo_chunk
    def on_copy_proxy(self, *args):
        copy_from_proxy_vts()

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


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()
