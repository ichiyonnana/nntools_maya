# coding:utf-8
""" ウェイトのスムーズ機能

選択頂点のウェイトをリニアになるようにスムーズ

選択頂点の周囲が十分に多い場合は四次元超平面での近似でウェイトを計算する
選択頂点や周囲の頂点が極端に少ない場合や平面近似が失敗した場合は加重平均でウェイトを計算する

TODO: インフルエンスの主従対応
      ゼロ境界とノーマライズがある以上すべてのインフルエンスをリニアには出来なくて､
      優先してリニアになるインフルエンスとそれに合わせて目減りさせるインフルエンスがあり
      優先インフルエンスを指定する必要がある
      またその場合の正規化タイミング (主インフルエンスウェイト以外でノーマライズした上で主ウェイト分を減ずる)

TODO: アルゴリズム毎に正規化タイミングがあってないので複数組み合わせるとおかしくなる
      各アルゴリズム内でサンプル数等に依存しない数値にしておく (特にWA)

"""
import itertools
import maya.cmds as cmds
import maya.mel as mel
import pymel.core as pm
import pymel.core.nodetypes as nt

from itertools import *

import datetime
import math
import re
import copy
import inspect
import time
import random

import nnutil as nu
import nnskin.matrix as matrix


def get_skinclusters(target):
    """ [pm] スキンクラスターをすべて取得

    Args:
        target (PyNode): スキンクラスターを持つオブジェクト

    Returns:
        SkinCluster: 
    """
    object = nu.get_object(target, pn=True)
    shape = None

    if isinstance(object, nt.Transform):
        shape = object.getShape()
    elif isinstance(object, nt.Mesh):
        shape = object
    else:
        raise(Exception("not mesh or parent of mesh"))
        
    skinclusters = [x for x in shape.connections() if type(x) == nt.SkinCluster]

    object_sets = [x for x in shape.connections() if type(x) == nt.ObjectSet]
    skinclusters.extend([con for object_set in object_sets for con in object_set.connections() if type(con) == nt.SkinCluster])

    return skinclusters


def get_skincluster(target):
    """ [pm] スキンクラスターをひとつだけ取得

    Args:
        target (PyNode): スキンクラスターを持つオブジェクト

    Returns:
        SkinCluster: 
    """

    return get_skinclusters(target)[0]


def to_str(data):
    """ [pm] PyNode を cmds のコンポーネント文字列に変換する """
    if type(data) == list:
        return [str(x) for x in data]
    else:
        return str(data)


def get_orig_points(object):
    """ [pm] オブジェクトのシェイプのデフォーム前の座標を取得する
    
    TODO: 最後の中間オブジェクトを返してるけどそれが skincluser 直前のシェイプだという保証がないのでなんとかしたい

    Args:
        obj (Pynode): シェイプを持つトランスフォームノード

    Returns:
        list[dt.point]: OrigShape の座標のリスト
    """
    transform_node = None

    if isinstance(object, nt.Transform):
        transform_node = object
    elif isinstance(object, nt.Mesh):
        transform_node = object.getParent()
    else:
        raise(Exception("not mesh or parent of mesh"))

    orig_shape = [x for x in pm.listRelatives(transform_node, noIntermediate=False) if x.intermediateObject.get()][-1]

    return orig_shape.getPoints()


def get_vtx_weight(sc, vtx):
    """ [pm] 指定した頂点のインフルエンスとウェイトの組を辞書で返す

    Args:
        sc (SkinCluster):
        vtx (MeshVertex): 

    Returns:
        dic[str: float]: インフルエンスの名称とウェイト値の辞書
    """
    influence_list = pm.skinCluster(sc, q=True, influence=True)
    weight_list = pm.skinPercent(sc, vtx, q=True, value=True)
    influence_weight_dic = dict(zip(influence_list, weight_list))

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


class OrderedNormalize:
    """インフルエンスに優先順位を付けたノーマライズ機能を提供する
    
    優先度は数字が高い方が優先度高｡優先度が同じ場合は通常のノーマライズを行う
    """

    def __init__(self):
        self.priority = dict()

    def init_from_joint(self, joint_hierarchy_root):
        pass

    def init_from_dict(self, inf_priority_dict):
        pass

    def get_priorities(self):
        pass

    def get_priority(self, influence):
        pass

    def set_priority(self, influence, value):
        pass

    def normalize(self, inf_weight_dict):
        pass


class WaightVertex:
    """ インフルエンス･ウェイトの情報を持った頂点クラス
    """

    def __init__(self, vertex, points, influence_list, weight_list, skincluster):
        """[summary]

        Args:
            vertex (nt.MeshVertex): MeshVertex オブジェクト
            points (dt.Point): XYZ座標
            influence_list (list[str]): インフルエンスの名称リスト
            weight_list (list[float]): influence_list と同じ順番のウェイトリスト
        """
        self.vertex = vertex  # pm.MeshVertex
        self.points = points  # dt.Point
        self.influence_list = to_str(influence_list)  # list[str]
        self.weight_list = weight_list  # list[float]
        self.skincluster = skincluster

        self._index = self.vertex.index()
        self._connected_vertices_index = [x.index() for x in vertex.connectedVertices()]

    def get_position(self):
        return self.points

    def index(self):
        return self._index

    def connected_vertices_index(self):
        return self._connected_vertices_index

    def get_influences(self, has_value=True):
        """ インフルエンスのリストを返す

        Args:
            has_value (bool, optional): ウェイトが非ゼロのインフルエンスのみ返す｡ Defaults to True.

        Returns:
            list(str): インフルエンス名のリスト
        """

        return [inf for i, inf in enumerate(self.influence_list) if not has_value or self.weight_list[i] != 0]

    def get_weight(self, influence):
        """インフルエンス名でウェイトを取得する

        Args:
            influence (str): インフルエンス名

        Returns:
            float: 指定インフルエンスのウェイト値
        """

        if influence in self.influence_list:
            index = self.influence_list.index(influence)
            return self.weight_list[index]
        else:
            return 0.0

    def set_weight(self, influence, weight):
        """指定したインフルエンスのウェイトを設定する

        内部で持っている値の更新のみで実際の頂点に反省させる場合には update_weight() を呼ぶ

        Args:
            influence ([type]): [description]
            weight ([type]): [description]

        Returns:
            [type]: [description]
        """
        if influence in self.influence_list:
            index = self.influence_list.index(influence)
        else:
            raise
        
        self.weight_list[index] = weight

    def update_weight(self):
        weight_list = dict(zip(self.influence_list, self.weight_list))
        total = sum(self.weight_list)
        tupled = [(inf, value / total) for inf, value in weight_list.items()]
        
        # TODO: 自前でノーマライズする

        pm.skinPercent(self.skincluster, self.vertex, transformValue=tupled)

    def get_point_4d(self, influence):
        return list(self.points) + [self.get_weight(influence)]


class Plane4D:
    """四次元空間の超平面を扱うクラス

    独立変数 x,y,z から従属変数 w を求める関数を提供する
    """
    # ゼロではないとみなす最小の行列式
    min_det = 0.001

    def __init__(self, points):
        """(x,y,z,w) の 4 頂点での初期化

        Args:
            points (list[list[float,float,float,float]]): [description]
        """
        self.valid = False

        if len(points) != 4:
            return

        x1, y1, z1, w1 = points[0]
        x2, y2, z2, w2 = points[1]
        x3, y3, z3, w3 = points[2]
        x4, y4, z4, w4 = points[3]

        t1 = matrix.Matrix([x1, y1, z1, w1],
                           [x2, y2, z2, w2],
                           [x3, y3, z3, w3],
                           [x4, y4, z4, w4]
                           )

        if t1.det < self.min_det:
            return
        
        t2 = matrix.Matrix(1, 1, 1, 1).reshape(4, 1)
        
        t3 = t1.inv * t2

        self.a = t3[0]
        self.b = t3[1]
        self.c = t3[2]
        self.d = t3[3]
        
        self.valid = True

    def get_w(self, x, y, z, max_v=1.0, min_v=0.0):
        """ x,y,z から w を求める

        Args:
            x (float): [description]
            y (float): [description]
            z (float): [description]
            max_v (float, optional): w をクランプする最大値. Defaults to 1.0.
            min_v (float, optional): w をクランプする最小値. Defaults to 0.0.

        Returns:
            float: w の値
        """
        return max(min_v, min(max_v, (-self.a * x - self.b * y - self.c * z + 1) / self.d))


def get_outer_vertices(vertices):
    """ 指定した頂点の1層外側の頂点を取得しリストで返す

    戻り値に vertices の頂点は含まれない｡

    Args:
        vertices (list[MeshVertex]): 外側の頂点を調べたい頂点リスト

    Returns:
        list[MeshVertex]: 指定した頂点の1層外側の頂点リスト
    """
    faces = nu.to_edge(vertices, pn=True)
    grow_vertices = nu.to_vtx(faces, pn=True)
    outer_vertices = list(set(grow_vertices) - set(vertices))
    
    return outer_vertices


def get_source_points_p4d(wvertices, influence, n=1):
    """ 指定した頂点からウェイト･座標の誤差が小さくなるような4点の組み合わせを複数リストで返す

    Args:
        wvertices (WaitedVertex): 4点抽出するための頂点リスト
        influence (str): 抽出のスコアリングに使われるインフルエンス名
        n (int): 抽出ペア数

    Returns:
        list[WaitedVertex]: 抽出された4点
    """
    if len(wvertices) < 4:
        return []

    elif len(wvertices) == 4:
        return [wvertices]

    else:
        ret = []

        x_sorted_wv = sorted(wvertices, key=lambda wvtx: wvtx.get_position().x)
        y_sorted_wv = sorted(wvertices, key=lambda wvtx: wvtx.get_position().y)
        z_sorted_wv = sorted(wvertices, key=lambda wvtx: wvtx.get_position().z)
        w_sorted_wv = sorted(wvertices, key=lambda wvtx: wvtx.get_weight(influence))
        
        ext_vertices = [x_sorted_wv[0],
                        x_sorted_wv[-1],
                        y_sorted_wv[0],
                        y_sorted_wv[-1],
                        z_sorted_wv[0],
                        z_sorted_wv[-1],
                        ] + w_sorted_wv[:3] + w_sorted_wv[-3:]

        pairs = itertools.combinations(ext_vertices, 4)
        max_score = 0
        best_pair = []

        for pair in pairs:
            a = matrix.Matrix(pair[0].get_point_4d(influence))
            b = matrix.Matrix(pair[1].get_point_4d(influence))
            c = matrix.Matrix(pair[2].get_point_4d(influence))
            d = matrix.Matrix(pair[3].get_point_4d(influence))

            ab = (b-a)
            ac = (c-a)
            ad = (d-a)

            if ab.norm() == 0 or ac.norm() == 0 or ad.norm() == 0:
                continue

            ab *= 1.0/ab.norm()
            ac *= 1.0/ac.norm()
            ad *= 1.0/ad.norm()

            score = (1.0-abs((ab*ac.reshape(4,1))[0])) * (1.0-abs((ac*ad.reshape(4,1))[0])) * (1.0-abs((ad*ab.reshape(4,1))[0]))

            if score > max_score and Plane4D([wv.get_point_4d(influence) for wv in pair]).valid:
                best_pair = pair
                max_score = score

        if max_score > 0:
            return [best_pair]
        else:
            return []


def get_source_points_wa(wvertices, influence, n=1):
    """ 指定した頂点からウェイト･座標の誤差が小さくなるような4点の組み合わせを複数リストで返す

    Args:
        wvertices (WaitedVertex): 4点抽出するための頂点リスト
        influence (str): 抽出のスコアリングに使われるインフルエンス名
        n (int): 抽出ペア数

    Returns:
        list[WaitedVertex]: 抽出された4点
    """
    
    if len(wvertices) == 0:
        return []

    elif len(wvertices) == 1:
        return []

    elif 2 <= len(wvertices) <= 4:
        return [wvertices]

    else:
        ret = []

        x_sorted_wv = sorted(wvertices, key=lambda wvtx: wvtx.get_position().x)
        y_sorted_wv = sorted(wvertices, key=lambda wvtx: wvtx.get_position().y)
        z_sorted_wv = sorted(wvertices, key=lambda wvtx: wvtx.get_position().z)
        w_sorted_wv = sorted(wvertices, key=lambda wvtx: wvtx.get_weight(influence))
        

        pairs = itertools.product(w_sorted_wv[:5], w_sorted_wv[-5:])
        
        max_score = 0
        best_pair = []

        for p0, p1 in pairs:
            d = (p0.get_position() - p1.get_position()).length()

            if d == 0:
                continue

            else:
                dw = abs(p0.get_weight(influence) - p1.get_weight(influence))
                score = dw * d

                if score > max_score:
                    best_pair = [p0, p1]
                    max_score = score

        if max_score > 0:
            return [best_pair]
        else:
            return []


@nu.timer
def smooth_weight_by_weighted_planer(target_vertices=None, force_plane4d=False, force_weightedavarage=False, protect_zero=False, protect_one=False, protect_upper=None, protect_lower=None):
    """ [pm] 指定頂点のウェイトを距離を考慮してスムースする
    選択範囲の境界の頂点の平均を使い､選択頂点の現在のウェイト値は使わない (インフルエンス自体の維持は可能)  
    """
    # 選択範囲の頂点取得
    if not target_vertices:
        target_vertices = pm.selected(flatten=True)
        
    # 選択範囲 + 1 層の 頂点取得
    outer_vertices = get_outer_vertices(target_vertices)

    # ターゲット+外側の頂点
    whole_vertices = target_vertices + outer_vertices

    # +1 範囲内の全ウェイト取得して WeightedVertex としてキャッシュ (コマンド取得はここで終えて以降は on memory でやる)
    obj = nu.get_object(target_vertices[0], pn=True)
    sc = get_skincluster(target_vertices[0])
    orig_points = get_orig_points(obj)
    whole_weights = [get_vtx_weight(sc, v) for v in whole_vertices]
    
    # デフォーム前の頂点情報とウェイト｡ key=頂点インデックス, value=WaitedVertexオブジェクト
    orig_w_vertices = dict()
    for i, v in enumerate(whole_vertices):
        wv = WaightVertex(v, orig_points[v.index()], to_str(whole_weights[i].keys()), whole_weights[i].values(), sc)
        orig_w_vertices[v.index()] = wv
    
    # スムース後の頂点情報とウェイト｡ key=頂点インデックス, value=WaitedVertexオブジェクト
    new_w_vertices = copy.deepcopy(orig_w_vertices)

    # +1 範囲内に存在する全インフルエンスの取得
    all_influences = nu.uniq(to_str(([inf for wv in orig_w_vertices.values() for inf in wv.get_influences(has_value=True)])))

    # インフルエンス毎に
    for influence in all_influences:
        # ウェイト計算対象頂点
        partial_vertices = copy.copy(target_vertices)
        
        # モードにより選択範囲からターゲット頂点を絞り込む
        # 0保護on/off, 100保護on/off, 上位下位n%保護on/off ...
        if protect_zero:
            partial_vertices = [v for v in partial_vertices if orig_w_vertices[v.index()].get_weight(influence=influence) != 0.0]

        if protect_one:
            partial_vertices = [v for v in partial_vertices if orig_w_vertices[v.index()].get_weight(influence=influence) != 1.0]
            
        if protect_upper:
            # TODO: 実装
            pass

        if protect_lower:
            # TODO: 実装
            pass

        if partial_vertices:
            # 絞り込んだ頂点の +1 層外側を取得する (ソース頂点)
            partial_outer_vertices = get_outer_vertices(partial_vertices)

            # ソース頂点から代表点のセットを作成して Plane4D 初期化を試みる
            plane_4d_list = []
            n = 1

            # TODO: それぞれのスムース処理関数切り出しして
            if len(partial_outer_vertices) >= 4 and not force_weightedavarage:
                source_set_list = get_source_points_p4d([orig_w_vertices[v.index()] for v in partial_outer_vertices], influence, n=n)

                for src_vts in source_set_list:
                    points4d = [list(sv.get_position()) + [orig_w_vertices[sv.index()].get_weight(influence)] for sv in src_vts]
                    p4d = Plane4D(points4d)

                    if p4d.valid:
                        plane_4d_list.append(p4d)

            # plane4D の初期化が成功すれば平面近似､失敗すれば加重平均でウェイトを求める
            if (plane_4d_list or force_plane4d):
                # 平面近似
                print(influence + " : 4d planer")
                for dst_v in partial_vertices:
                    # 対象頂点の xyz から w を求めて WeightedVertex のウェイトを変更する
                    dst_wv = orig_w_vertices[dst_v.index()]
                    x, y, z = dst_wv.get_position()
                    w_list = [p4d.get_w(x, y, z) for p4d in plane_4d_list]
                    w = sum(w_list) / len(w_list)

                    new_w_vertices[dst_wv.index()].set_weight(influence, w)
            else:
                # 加重平均
                print(influence + " : weighted avarage")
                outer_wv = [orig_w_vertices[v.index()] for v in partial_outer_vertices]

                test_wv = orig_w_vertices[partial_vertices[0].index()]
                source_wvts_list = get_source_points_wa(wvertices=outer_wv, influence=influence)[0]
                pm.select([wv.vertex for wv in source_wvts_list])
                raise

                for dst_v in partial_vertices:                    
                    dst_wv = orig_w_vertices[dst_v.index()]
                    p = dst_wv.get_position()
                    new_weight = 0

                    for src_wv in source_wvts_list:
                        w = src_wv.get_weight(influence)
                        d = (p - src_wv.get_position()).length()
                        
                        if d == 0:
                            new_weight = w
                            break
                        else:
                            new_weight += w / d / len(source_wvts_list)

                    # TODO: 距離合計による正規化

                    new_w_vertices[dst_wv.index()].set_weight(influence, new_weight)

    # 実際のウェイトを更新
    for wv in new_w_vertices.values():
        wv.update_weight()

    return True

@nu.timer
def smooth_weight_each_wa(target_vertices=None, force_plane4d=False, force_weightedavarage=False, protect_zero=False, protect_one=False, protect_upper=None, protect_lower=None):
    """1頂点ずつ隣接頂点と加重平均
    適用順序に依存するので良い結果じゃない
    """

    # 選択範囲の頂点取得
    if not target_vertices:
        target_vertices = pm.selected(flatten=True)
        
    # 選択範囲 + 1 層の 頂点取得
    outer_vertices = get_outer_vertices(target_vertices)

    # ターゲット+外側の頂点
    whole_vertices = target_vertices + outer_vertices

    # +1 範囲内の全ウェイト取得して WeightedVertex としてキャッシュ (コマンド取得はここで終えて以降は on memory でやる)
    obj = nu.get_object(target_vertices[0], pn=True)
    sc = get_skincluster(target_vertices[0])
    orig_points = get_orig_points(obj)
    whole_weights = [get_vtx_weight(sc, v) for v in whole_vertices]
    
    # デフォーム前の頂点情報とウェイト｡ key=頂点インデックス, value=WaitedVertexオブジェクト
    orig_w_vertices = dict()
    for i, v in enumerate(whole_vertices):
        wv = WaightVertex(v, orig_points[v.index()], to_str(whole_weights[i].keys()), whole_weights[i].values(), sc)
        orig_w_vertices[v.index()] = wv
    
    # スムース後の頂点情報とウェイト｡ key=頂点インデックス, value=WaitedVertexオブジェクト
    new_w_vertices = copy.deepcopy(orig_w_vertices)

    # +1 範囲内に存在する全インフルエンスの取得
    all_influences = nu.uniq(to_str(([inf for wv in orig_w_vertices.values() for inf in wv.get_influences(has_value=True)])))

    iter = 1
    for i in range(iter):
        # インフルエンス毎に
        for influence in all_influences:
            # ウェイト計算対象頂点
            partial_vertices = copy.copy(target_vertices)
            
            # モードにより選択範囲からターゲット頂点を絞り込む
            # 0保護on/off, 100保護on/off, 上位下位n%保護on/off ...
            if protect_zero:
                partial_vertices = [v for v in partial_vertices if orig_w_vertices[v.index()].get_weight(influence=influence) != 0.0]

            if protect_one:
                partial_vertices = [v for v in partial_vertices if orig_w_vertices[v.index()].get_weight(influence=influence) != 1.0]
                
            if protect_upper:
                # TODO: 実装
                pass

            if protect_lower:
                # TODO: 実装
                pass

            if partial_vertices:
                for d_vtx in partial_vertices:
                    # 加重平均
                    print(influence + " : weighted avarage")
                    d_wvtx = orig_w_vertices[d_vtx.index()]
                    
                    source_vertices = [orig_w_vertices[i] for i in d_wvtx.connected_vertices_index()]

                    p = d_vtx.getPosition(space="world")
                    new_weight = 0

                    for s_wvtx in source_vertices:
                        w = new_w_vertices[s_wvtx.index()].get_weight(influence)
                        d = (p - new_w_vertices[s_wvtx.index()].get_position()).length()
                        
                        if d == 0:
                            new_weight = w
                            break
                        else:
                            new_weight += w / d

                    new_w_vertices[d_vtx.index()].set_weight(influence, new_weight)

    # 実際のウェイトを更新
    for wv in new_w_vertices.values():
        wv.update_weight()

    return True


def propagative_smooth(target_vertices=None, force_plane4d=False, force_weightedavarage=False, protect_zero=False, protect_one=False, protect_upper=None, protect_lower=None):
    """境界外側から順に伝搬するようにスムースする｡
    計算は隣接頂点のみで､距離による加重平均
    """

    # 選択範囲の頂点取得
    if not target_vertices:
        target_vertices = pm.selected(flatten=True)

    # 外側からのホップ数調べる

    # ホップ数で昇順ソート

    # 隣接点のみで距離による加重平均

    # 伝搬ムラを軽減するために低ホップはソースウェイト､高ホップは全体の平均で計算する



print("\n"*100)
if smooth_weight_by_weighted_planer(protect_zero=True, force_weightedavarage=True):
    print("finish")
else:
    print("fail")