"""距離を考慮したウェイトスムース。

メインの関数は smooth_weight_interior
"""
import maya.cmds as cmds
import maya.mel as mel
import pymel.core as pm
import pymel.core.nodetypes as nt

from itertools import *

import math
import re
import copy
import inspect
import time

import pymel.core as pm
import pymel.core.nodetypes as nt

import nnutil.core as nu


class WaightVertex:
    """ インフルエンス･ウェイトの情報を持った頂点クラス
    """

    def __init__(self):

        self.vertex: pm.MeshVertex = None
        self.influence_list: list = []
        self.weight_list: list = []


def get_skincluster(target):
    """ [pm] スキンクラスターの取得
    Args:
        target (PyNode): スキンクラスターを持つオブジェクト
    
    Returns:
        SkinCluster: 
    """
    object = nu.get_object(target, pn=True)
    sc = mel.eval("findRelatedSkinCluster %s" % object)

    return sc


def to_str(data):
    """ [pm] PyNode を cmds のコンポーネント文字列に変換する """
    if type(data) == list:
        return [str(x) for x in data]
    else:
        return str(data)


def orig_point_from_vertex(vtx):
    """ [pm/cmds] maya.cmds のコンポーネント文字列や MeshVertex からデフォーム前の座標を取得する
    
    Args:
        vtx (str or MeshVertex):

    Returns:
        list[float, float, float]
    """
    obj = pm.PyNode(nu.get_object(vtx)).getParent()
    index = pm.PyNode(vtx).index()
    orig_shape = [x for x in pm.listRelatives(obj, noIntermediate=False) if x.intermediateObject.get()][0]
    vtx = orig_shape.vtx[index]

    return pm.xform(vtx, q=True, ws=True, t=True)


def get_vtx_weight(vtx):
    """ [pm] 指定した頂点のインフルエンスとウェイトの組を辞書で返す

    Args:
        vtx (MeshVertex): 

    Returns:
        dic[str: float]: インフルエンスの名称とウェイト値の辞書
    """
    sc = get_skincluster(nu.get_object(vtx))
    influence_list = pm.skinCluster(sc, q=True, influence=True)
    weight_list = pm.skinPercent(sc, vtx, q=True, value=True)
    influence_weight_dic = {}

    for i in range(len(influence_list)):
        influence_weight_dic[influence_list[i]] = weight_list[i]

    return influence_weight_dic


def set_vtx_weight(sc, vtx, weight_dic):
    """ [pm] 辞書でウェイト設定
    
    Args:
        sc (SkinCluster):
        vtx (MeshVertex):
        weight_dic (dic[str: float]):
    """
    weight_list = [(i, w) for i, w in weight_dic.items()]
    pm.skinPercent(sc, vtx, transformValue=weight_list)


def get_average_weight_and_point(vts):
    """ 指定した頂点リストのすべての頂点の平均位置･平均ウェイトを一つ返す

    Args:
        vts (list[MeshVertex]):
    
    Returns:
        list[dic[str: flaot], list[list[flaot, float, float]]]: 平均位置と平均ウェイトが含まれる要素数 1 のリスト
    """

    # 1頂点1辞書でウェイト取得してリストにする
    vts_weight = [get_vtx_weight(vtx) for vtx in vts]

    # 平均化
    avg_vtc_weight = {}
    vts_count = len(vts)

    ## ウェイトの平均化
    for vtx_weight in vts_weight:
        for influence, weight in vtx_weight.items():
            if influence not in avg_vtc_weight:
                avg_vtc_weight[influence] = 0
            avg_vtc_weight[influence] += weight / vts_count

    ## 座標の平均化
    points = [orig_point_from_vertex(vtx) for vtx in vts]
    avg_vtc_point = [
        sum([point[0] for point in points]) / vts_count,
        sum([point[1] for point in points]) / vts_count,
        sum([point[2] for point in points]) / vts_count, ]

    return [avg_vtc_weight, avg_vtc_point]


def _linearize_weight(target, end_vts_weights, end_vts_points):
    """ 指定した代表点のウェイトと座標で指定した対象頂点のウェイトをリニアにする

    Args:
        vts (MeshVertex): 操作対象頂点
        end_vts_weights (list[dic[str:flaot]]): 
            複数代表点のインフルエンス-ウェイト辞書をリストでまとめたもの
            [{i1:w1, i2:w2 ...}, {i1:w1, i2:w2 ...}, ...]
        end_vts_points (list[list[float, float, float]]):
            複数代表点の座標をリストでまとめたもの
            [[x,y,z], [x,y,z], ...]
    """

    # 頂点に変換
    vts = nu.to_vtx(target)

    # スキンクラスター取得
    sc = get_skincluster(nu.get_object(target))

    # 各頂点に対して、代表頂点を結ぶ直線上の最も近い点を求め
    # その点の位置で代表頂点のウェイトを内分した値を設定する
    for vtx in vts:

        # 代表点間の距離
        total_distance = nu.distance(end_vts_points[0], end_vts_points[1])

        # 操作対象の頂点に一番近い直線上の座標を求める
        # この点が代表点間の線分範囲外なら値は近い方の代表点のウェイトで飽和させる (ウェイトの性質上外延はしたくない)
        ratio0 = 1 # end_vts_weights[0] の割合
        nearest_point = nu.nearest_point_on_line(end_vts_points[0], end_vts_points[1], orig_point_from_vertex(vtx))
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


def avarage_weights(weights, alpha_list):
    """ ウェイトの加重平均を求める
    
    インフルエンスの名前毎にウェイトに係数をかけて平均する
    
    指定した代表点のウェイトと座標で指定した対象頂点のウェイトをリニアにする
    Args:
        weights (list[dic[str:flaot]]):
                インフルエンス-ウェイト辞書をリストでまとめたもの
                [{i1:w1, i2:w2 ...}, {i1:w1, i2:w2 ...}, ...]
        alpha_list (list[float]): 各ウェイトにかける加重平均のウェイト｡スキンウェイトと紛らわしいので名称はアルファに
    """
    # 返値
    avarage_weights = {}

    # 加重の正規化
    total = sum(alpha_list)
    normalized_alpha = [x / total for x in alpha_list]

    # 係数かけて足す
    for i, weight in enumerate(weights):
        for inf_name in weight.keys():            
            if inf_name not in avarage_weights:
                avarage_weights[inf_name] = 0
            
            avarage_weights[inf_name] += weights[i][inf_name] * normalized_alpha[i] 

    return avarage_weights


def linearize_weight_with_farthest_points(vts):
    """ 選択頂点のウェイトを距離でリニアにする｡ 代表点は最も離れた 2 点

    """
    # 最も離れた2点を代表点にする
    end_vts = nu.get_most_distant_vts(vts)

    # 代表点のウェイトリストと座標リスト
    end_vts_weights = [get_vtx_weight(vtx) for vtx in end_vts]
    end_vts_points = [orig_point_from_vertex(vtx) for vtx in end_vts]
    
    # リニアライズ
    _linearize_weight(vts, end_vts_weights, end_vts_points)
    

def linearize_weight_with_borders(vts):
    """ 二つの穴を持つ選択頂点のウェイトを距離でリニアにする｡代表点は各穴のそれぞれの平均座標･平均ウェイト
    """
    internal_faces = pm.filterExpand(pm.polyListComponentConversion(vts, fv=True, tf=True, internal=True), sm=34)
    border_edges = pm.filterExpand(pm.polyListComponentConversion(internal_faces, ff=True, te=True, border=True), sm=32)
    border_groups = nu.get_all_polylines(border_edges)

    # ボーダーの平均値を代表点とする
    w0, p0 = get_average_weight_and_point(nu.to_vtx(border_groups[0]))
    w1, p1 = get_average_weight_and_point(nu.to_vtx(border_groups[1]))

    # リニアライズ
    _linearize_weight(vts, [w0, w1], [p0, p1])


def smooth_weight_linear(keep_zero=False):
    """ 指定頂点のウェイトを可能な限りリニアにする  
    """
    target_vertices = pm.selected(flatten=True)

    # トポロジーの連続性からボーダーとなっている頂点を調べ
    # ボーダー毎にグループを分ける
    border_groups = []
    
    ## ボーダーエッジの特定
    ### 選択範囲内の最大外周を正とするなら True
    ### 選択範囲外の最小外周を正とするなら False
    use_internal_border = False
    internal_faces = pm.filterExpand(pm.polyListComponentConversion(target_vertices, fv=True, tf=True, internal=use_internal_border), sm=34)
    border_edges = pm.filterExpand(pm.polyListComponentConversion(internal_faces, ff=True, te=True, border=True), sm=32)

    ## ボーダーエッジのグループ分け
    border_groups = nu.get_all_polylines(border_edges)

    # ボーダーグループの数で処理を分ける
    if len(border_groups) == 0:
        ## ボーダー無し
        ## 警告だけ出して処理しない
        message = "no border"
        print(message)
        nu.message(message)

    elif len(border_groups) == 1:
        # ボーダー数 1 ｡ ハンマーみたいな使い方
        ## 
        # 一番遠い 2 点を代表点とする
        linearize_weight_with_farthest_points(nu.idstr(target_vertices))

    elif len(border_groups) == 2:
        # ボーダー数 2 ｡ 典型的なリニアライズ
        linearize_weight_with_borders(nu.idstr(target_vertices))
        # アウターボーダー使ってないので内分で書き換える

    else:
        ## ボーダー数 3 以上
        ## 警告出して処理しない or 面積や距離が大きい上位 2 グループで無理矢理リニアライズしてしまう
        message = "not impl 3 borders"
        print(message)
        nu.message(message)


def profile():
    print(inspect.currentframe(1).f_lineno)
    print(time.time())
    print("")

def smooth_weight_interior(target_vertices=None, keep_zero=True):
    """ 指定頂点のウェイトを距離を考慮してスムースする
    選択範囲の境界の頂点の平均を使い､選択頂点の現在のウェイト値は使わない (インフルエンス自体の維持は可能)  
    """
    if not target_vertices:
        target_vertices = nu.idstr(pm.selected(flatten=True))
    
    obj = nu.pynode(nu.get_object(target_vertices[0]))
    orig_points = [orig_point_from_vertex(nu.idstr(v)) for v in obj.vtx]

    sc = get_skincluster(nu.idstr(target_vertices[0]))

    # トポロジーの連続性からボーダーとなっている頂点を調べ
    # ボーダー毎にグループを分ける
    border_groups = []
    
    ## ボーダーエッジの特定
    ### 選択範囲内の最大外周を正とするなら True
    ### 選択範囲外の最小外周を正とするなら False
    use_internal_border = False
    internal_faces = pm.filterExpand(pm.polyListComponentConversion(target_vertices, fv=True, tf=True, internal=use_internal_border), sm=34)
    border_edges = pm.filterExpand(pm.polyListComponentConversion(internal_faces, ff=True, te=True, border=True), sm=32)

    ## ボーダーエッジのグループ分け
    border_groups = nu.get_all_polylines(border_edges)

    # 内分に使う頂点
    end_vertices = []

    # ボーダー数で場合分け
    if len(border_groups) == 1 or True:

        # ボーダー数 1 は全境界で計算する｡ただし target_vertices に隣接していないものは破棄する
        connected_vertex_indices = [vtx.index() for target_vertex in target_vertices for vtx in nu.pynode(target_vertex).connectedVertices()]
        border_vertex_indices = [vtx.index() for border_group in border_groups for edge in border_group for vtx in nu.pynode(nu.to_vtx(edge))]
        end_vertex_indices = set(border_vertex_indices) & set(connected_vertex_indices)
        end_vertices = nu.idstr([obj.vtx[i] for i in end_vertex_indices])
        
        # ソース頂点のウェイト
        weights = [get_vtx_weight(end_vertex) for end_vertex in end_vertices]
        
        # 対象頂点ごとにボーダーの平均を求めてウェイト設定する
        for v in target_vertices:
            distances = [nu.distance(orig_points[nu.pynode(v).index()], orig_points[nu.pynode(end_vertex).index()]) for end_vertex in end_vertices]
            # 加重平均のウェイトとして使用する距離の逆数
            alpha_list = [1.0 / d for d in distances]
            weight = avarage_weights(weights, alpha_list)

            set_vtx_weight(sc, v, weight)

        
    elif len(border_groups) == 2:
        # ボーダー数 2 は各ボーダーの一番近い頂点同士で計算する
        for border_edges in border_groups:
            vts = nu.to_vtx(border_edges)
            nearest = nu.get_nearest_point_from_point(target_vertices, vts)
            end_vertices.append(nearest)

    else:
        # それ以外は警告出して終わり
        print("selected topology is not supported")
        pass


def smooth_weight_interior_each_vtx():
    target_vertices = nu.idstr(pm.selected(flatten=True))

    for v in target_vertices:
        smooth_weight_interior(target_vertices=[v])
