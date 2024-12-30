"""
単独で機能になっていないもの
基本的にはほかのモジュールが呼び出すもの
戻り値のある物
"""
import datetime
import math
import re
import copy
import os
import sys
import hashlib

import itertools as it
import functools

import maya.cmds as cmds
import maya.mel as mel
import pymel.core as pm
import pymel.core.nodetypes as nt
import pymel.core.datatypes as dt

import maya.api.OpenMaya as om


DEBUG = False


class Hashable:
    def __init__(self, object, hash):
        hash_str = hashlib.md5(hash.encode())
        self.hash = int(hash_str.hexdigest(), 16)
        self.object = object

    def __hash__(self):
        return self.hash

    def object(self):
        return self.object


def is_python2():
    """Python が 3 系未満なら True を返す"""

    return sys.version_info.major < 3


def get_selection(**kwargs):
    """ [cmds]

    Returns:
        [type]: [description]
    """
    return cmds.ls(selection=True, flatten=True, **kwargs)


def selected(**kwargs):
    """ [pm] flatten を有効にした pm.selected()

    Returns:
        [type]: [description]
    """
    return pm.selected(flatten=True, **kwargs)


def undo_chunk(function):
    """ Undo チャンク用デコレーター """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        cmds.undoInfo(ock=True)
        ret = function(*args, **kwargs)
        cmds.undoInfo(cck=True)
        return ret

    return wrapper


if DEBUG:
    def timer(function):
        """時間計測デコレーター"""
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            start = datetime.datetime.today()
            ret = function(*args, **kwargs)
            end = datetime.datetime.today()
            delta = (end - start)
            sec = delta.seconds + delta.microseconds/1000000.0
            print('time(sec): ' + str(sec) + " " + str(function))
            return ret

        return wrapper

else:
    def timer(function):
        """デバッグ無効時の時間計測デコレーター"""
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            return function(*args, **kwargs)

        return wrapper


def no_warning(function):
    """警告抑止デコレーター"""
    def wrapper(*args, **kwargs):
        warning_flag = cmds.scriptEditorInfo(q=True, suppressWarnings=True)
        info_flag = cmds.scriptEditorInfo(q=True, suppressInfo=True)
        cmds.scriptEditorInfo(e=True, suppressWarnings=True, suppressInfo=True)
        ret = function(*args, **kwargs)
        cmds.scriptEditorInfo(e=True, suppressWarnings=warning_flag, suppressInfo=info_flag)
        return ret

    return wrapper


def idstr(pynode):
    """ [pm] PyNode を cmds 用の文字列に変換する """
    if type(pynode) == list:
        return [idstr(x) for x in pynode]
    else:
        return str(pynode)


def pynode(object_name):
    """ [pm/cmds] cmds 用の文字列 を PyNode に変換する """
    if type(object_name) == list:
        return [pynode(x) for x in object_name]
    else:
        return pm.PyNode(object_name)


def list_add(l1, l2):
    """ リスト同士の和 (l1 + l2 ) を返す

    重複削除はせずただ結合しただけのリストが返る
    TODO: *args で可変長 (l1 + l2 + l3 + ...) に対応して

    """
    if not isinstance(l1, list) or not isinstance(l2, list):
        print("list_add: The argument is not a list. It will convert automatically, but it may not be the intended result.")
        l1 = list(l1)
        l2 = list(l2)

    return l1 + l2


def list_diff(l1, l2):
    """ リスト同士の差集合 (l1 - l2) を返す

    list(set() - set()) よりは軽い
    TODO: *args で可変長 (l1 - l2 - l3 - ... )に対応して

    """
    if not isinstance(l1, list) or not isinstance(l2, list):
        print("list_diff: The argument is not a list. It will convert automatically, but it may not be the intended result.")
        l1 = list(l1)
        l2 = list(l2)

    return list(filter(lambda x: x not in l2, l1))


def list_intersection(l1, l2):
    """ リストの積集合 (l1 & l2) を返す

    list(set() & set()) よりは軽い
    TODO: *args で可変長 (l1 & l2 & l3 & ...) に対応して

    """
    if not isinstance(l1, list) or not isinstance(l2, list):
        print("list_intersection: The argument is not a list. It will convert automatically, but it may not be the intended result.")
        l1 = list(l1)
        l2 = list(l2)

    return list(filter(lambda x: x in l2, l1))


def distance(p1, p2):
    """ [cmds] p1,p2の三次元空間での距離を返す

    Args:
        p1 (list[float, float, float] or str): 三次元座標のリスト or cmds のコンポーネント文字列
        p2 (list[float, float, float] or str): 三次元座標のリスト or cmds のコンポーネント文字列

    Returns:
        float:
    """

    return math.sqrt(distance_sq(p1, p2))


def distance_sq(p1, p2):
    """ [cmds] p1,p2の三次元距離の二乗を返す

    Args:
        p1 (list[float, float, float] or str): 三次元座標のリスト or cmds のコンポーネント文字列
        p2 (list[float, float, float] or str): 三次元座標のリスト or cmds のコンポーネント文字列

    Returns:
        float:
    """
    if not isinstance(p1, list):
        p1 = point_from_vertex(p1)

    if not isinstance(p2, list):
        p2 = point_from_vertex(p2)

    return (p2[0]-p1[0])**2 + (p2[1]-p1[1])**2 + (p2[2]-p1[2])**2


def distance2d(p1, p2):
    """ [cmds] 二次元座標の距離を返す

    Args:
        p1 (list[float, float]): 二次元座標のリスト
        p2 (list[float, float]): 二次元座標のリスト

    Returns:
        float: 二次元座標の距離
    """
    return math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)


def distance_uv(uv1, uv2):
    """ [cmds] UV 2 点間の距離を返す

    Args:
        p1 (list[float, float]): cmds の UV コンポーネント文字列
        p2 (list[float, float]): cmds の UV コンポーネント文字列

    Returns:
        float: 二次元座標の距離
    """
    uvCoord1 = cmds.polyEditUV(uv1, query=True)
    uvCoord2 = cmds.polyEditUV(uv2, query=True)
    return distance2d(uvCoord1, uvCoord2)


def copy_uv(dst, src):
    """ [cmds] UV を設定する

    Args:
        dst (str): コピー先 UV の cmds コンポーネント文字列
        src ([type]): コピー元 UV の cmds コンポーネント文字列
    """
    src_coord = cmds.polyEditUV(src, q=True, relative=False)
    cmds.polyEditUV(dst, relative=False, u=src_coord[0], v=src_coord[1])


def filter_backface_uv_comp(uv_comp_list):
    """ [cmds] 指定した UV のうち裏表が反転しているUVシェルを取得する

    Args:
        uv_comp_list (list[str]): フィルター対象の UV の cmds コンポーネント文字列

    Returns:
        list[str]: 裏表が反転している UV の cmds コンポーネント文字列
    """
    cmds.SelectUVBackFacingComponents()
    backface_uvs = list(set(cmds.ls(selection=True, flatten=True)) & set(uv_comp_list))

    return backface_uvs


def dot(v1, v2):
    """ 三次元ベクトルの内積

    Args:
        v1 (list[float, float]):
        v2 (list[float, float]):

    Returns:
        float:
    """
    return sum([x1 * x2 for x1, x2 in zip(v1, v2)])


def cross(a, b):
    """ 三次元ベクトルの外積

    Args:
        a (list[float, float, float]):
        b (list[float, float, float]):

    Returns:
        list[float, float, float]:
    """
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def add(v1, v2):
    """ 三次元ベクトルの加算

    Args:
        v1 (list[float, float, float]):
        v2 (list[float, float, float]):

    Returns:
        list[float, float, float]:
    """
    return [x1 + x2 for x1, x2 in zip(v1, v2)]


def diff(v2, v1):
    """ 三次元ベクトルの減算

    Args:
        v1 (list[float, float, float]):
        v2 (list[float, float, float]):

    Returns:
        list[float, float, float]:
    """
    return [x2 - x1 for x1, x2 in zip(v1, v2)]


def mul(v1, f):
    """ 三次元ベクトルと実数の積

    Args:
        v1 (list[float, float, float]):
        f (float):

    Returns:
        list[float, float, float]:
    """
    return [x * f for x in v1]


def div(v1, f):
    """ 三次元ベクトルと実数の商

    Args:
        v1 (list[float, float, float]):
        f (float):

    Returns:
        list[float, float, float]:
    """
    return [x / f for x in v1]


def angle(v1, v2, degrees=False):
    """ 2ベクトル間のなす角

    Args:
        v1 (list[float, float, float]):
        v2 (list[float, float, float]):

    Returns:
        float:
    """
    rad = math.acos(dot(v1, v2))

    if degrees:
        return math.degrees(rad)
    else:
        return rad


def edge_to_vector(edge, normalize=False):
    """ [cmds] エッジからベクトルを取得する｡ベクトルの前後は不定

    Args:
        edge (str): エッジを表すcmdsコンポーネント文字列
        normalize (bool, optional): Trueの場合正規化を行う. Defaults to False.

    Returns:
        list[float, float, float]: エッジから作成されたベクトル
    """
    p1, p2 = [get_vtx_coord(x) for x in to_vtx(edge)]
    v = diff(p2, p1)

    if normalize:
        return normalize(v)
    else:
        return v


def get_farthest_point_pair(points):
    """ points に含まれる点のうち一番遠い二点を返す

    Args:
        points (list[list[float, float, float]]):

    Returns:
        list[list[float, float, float]]
    """
    point_pairs = it.combinations(points, 2)
    max_distance = -1

    for a, b in point_pairs:
        d = distance_sq(a, b)

        if d > max_distance:
            most_distant_vtx_pair = [a, b]
            max_distance = d

    return most_distant_vtx_pair


def get_nearest_point_from_point(point, target_points):
    """ target_points のうち point に一番近い点の座標を返す

    Args:
        point (list[float, float, float]):
        target_points (list[list[float, float, float]]):

    Returns:
        list[float, float, float]
    """

    ret_point = []
    min_distance = -1

    for target_point in target_points:
        d = distance(point, target_point)
        if d < min_distance or min_distance < 0:
            min_distance = d
            ret_point = target_point

    return ret_point


def nearest_point_on_line(p1, p2, p3):
    """ p1 p2 を通る直線を構成する頂点うち p3 に最も近いものの座標を返す (垂線を下ろした交点)

    Args:
        p1 (list[float, float, float]): 直線の通過する点1
        p2 (list[float, float, float]): 直線の通過する点2
        p2 (list[float, float, float]): 垂線を下ろす点

    Returns:
        list[float, float, float]
    """

    v = normalize(vector(p1, p2))
    p = vector(p1, p3)

    return add(p1, mul(v, dot(p, v)))


def vector(p1, p2):
    """ p1->p2ベクトルを返す

    Args:
        p1 (list[float, float, float]): ベクトルの起点座標
        p2 (list[float, float, float]): ベクトルの終点座標
    """
    return (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])


def normalize(v):
    """ ベクトルを渡して正規化したベクトルを返す

    Args:
        v (list[float, float, float]): 正規化するベクトル
    """
    norm = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
    if norm != 0:
        return (v[0]/norm, v[1]/norm, v[2]/norm)
    else:
        return (0, 0, 0)


def point_from_vertex(vtx):
    """ [cmds] maya.cmds のコンポーネント文字列から座標を取得

    Args:
        vtx (str): 頂点を表すコンポーネント文字列

    Returns:
        list[float, float, float]: vtx のワールド空間座標
    """
    return cmds.xform(vtx, q=True, ws=True, t=True)


def get_vtx_coord(vtx):
    """ [cmds] maya.cmds のコンポーネント文字列から座標を取得

    Args:
        vtx (str): 頂点を表すコンポーネント文字列

    Returns:
        list[float, float, float]: vtx のワールド空間座標
    """
    return cmds.xform(vtx, q=True, ws=True, t=True)


def set_vtx_coord(vtx, point):
    """ [cmds] maya.cmds のコンポーネント文字列から座標を設定

    Args:
        vtx (str): 頂点を表すコンポーネント文字列
        point(list[float, float, float]): 設定するワールド座標

    Returns:
        None
    """
    cmds.xform(vtx, ws=True, t=point)


def get_uv_coord(uv):
    """ [cmds] maya.cmds のコンポーネント文字列からUV座標を取得

    Args:
        uv (str):

    Return:
        list[float, float]:

    """
    uv_coord = cmds.polyEditUV(uv, query=True)
    return uv_coord


def get_connected_vertices(comp):
    """ [pm/cmds] pymel の getConnectedVertices の代替関数

    pymel の getConnectedVertices より若干早い

    Args:
        comp ([type]): [description]

    Returns:
        [type]: [description]
    """
    if type(comp) in [type(""), type(u"")]:
        # comp 自体を取り除く (obj, objShape 対策でインデックスのみ比較)
        return [x for x in to_vtx(to_edge(comp)) if re.search(r"(\[\d+\])", comp).groups()[0] not in x]

    elif type(comp) in [pm.MeshEdge, pm.MeshVertex]:
        return pynode(get_connected_vertices(idstr(comp)))

    else:
        raise


def get_end_vtx_e(edges):
    """ [cmds] edges に含まれる端の頂点をすべて返す

    Args:
        edges(list[str]): エッジを表すcmdsコンポーネント文字列のリスト

    Returns:
        list[str]: 頂点を表すcmdsコンポーネント文字列のリスト
    """
    endvtx = []

    vts = cmds.filterExpand(cmds.polyListComponentConversion(
        edges, fe=True, tv=True), sm=31)

    for vtx in vts:
        neighbors = set(cmds.filterExpand(cmds.polyListComponentConversion(
            vtx, fv=True, te=True), sm=32)) & set(edges)
        if len(neighbors) == 1:
            endvtx.append(vtx)

    return endvtx


def get_end_vtx_v(vts):
    """ [cmds] 連続したエッジで接続される頂点の端の頂点をすべて返す

    Args:
        vts (list[str]): 頂点を表すcmdsコンポーネント文字列のリスト

    Returns:
        list[str]: 頂点を表すcmdsコンポーネント文字列のリスト
    """
    conv_edges = to_edge(vts)
    edges = [e for e in conv_edges if len(set(to_vtx(e)) & set(vts)) == 2]

    return get_end_vtx_e(edges)


def get_most_distant_vts(vts):
    """ [cmds] 引数で渡した頂点集合のうち最も離れた2点を返す

    Args:
        vts (list[str]): 頂点を表すcmdsコンポーネント文字列のリスト

    Returns:
        (list[str, str]):
    """
    most_distant_vtx_pair = []
    max_distance = -1

    vtx_point_dic = {vtx: point_from_vertex(vtx) for vtx in vts}
    vtx_pairs = it.combinations(vts, 2)

    for vtx_pair in vtx_pairs:
        d = abs(distance_sq(vtx_point_dic[vtx_pair[0]], vtx_point_dic[vtx_pair[1]]))

        if d > max_distance:
            most_distant_vtx_pair = vtx_pair
            max_distance = d

    return most_distant_vtx_pair


def sortVtx(edges, first_vtx=None):
    """ [cmds] 指定した点から順にエッジたどって末尾まで到達する頂点の列を返す

    Args:
        edges(list[str]): エッジを表すcmdsコンポーネント文字列のリスト
        first_vtx (str): 頂点を表すcmdsコンポーネント文字列

    Returns:
        list[str]: 頂点を表すcmdsコンポーネント文字列のリスト

    """
    def partVtxList(partEdges, startVtx):
        """ 部分エッジ集合と開始頂点から再帰的に頂点列を求める """
        neighbors = cmds.filterExpand(
            cmds.polyListComponentConversion(startVtx, fv=True, te=True), sm=32)
        nextEdges = list_intersection(neighbors, partEdges)

        if len(nextEdges) == 1:
            nextEdge = nextEdges[0]
            vset1 = set(cmds.filterExpand(cmds.polyListComponentConversion(nextEdge, fe=True, tv=True), sm=31))
            vset2 = {startVtx}
            nextVtx = list(vset1-vset2)[0]
            restEdges = list(set(partEdges) - set(nextEdges))
            partial_vts = partVtxList(restEdges, nextVtx)
            partial_vts.insert(0, startVtx)
            return partial_vts
        else:
            return [startVtx]

    if not first_vtx:
        first_vtx = get_end_vtx_e(edges)[0]

    return partVtxList(edges, first_vtx)


def isStart(vtx, curve):
    """ [cmds] vts[0] とカーブの始点･終点の距離を比較して始点の方が近ければ True 返す

    Args:

    Returns:

    """
    curve_start = cmds.pointOnCurve(curve, pr=0, p=True)
    curve_end = cmds.pointOnCurve(curve, pr=1, p=True)
    pnt = get_vtx_coord(vtx)
    d1 = distance(pnt, curve_start)
    d2 = distance(pnt, curve_end)
    if d1 < d2:
        return True
    else:
        return False


def vtxListPath(vts, n=None):
    """ [cmds] vts で渡された頂点の i 番目までの距離を返す｡ n を省略した場合は道のり全長を返す

    Args:

    Returns:

    """
    if n is None or n > len(vts):
        n = len(vts)-1

    path = 0.0

    for i in range(n):
        pnt1 = get_vtx_coord(vts[i])
        pnt2 = get_vtx_coord(vts[i+1])
        path += distance(pnt1, pnt2)

    return path


def length_each_vertices(vertices, space="world"):
    """ [pm] 頂点間の距離をリストで返す

    戻り値リストの n 番目は vertices[n] と vertices[n+1] の距離

    Args:
        vertices (list[MeshVertex]):
        space (str):

    Returns:
        list[float]:

    """
    length_list = []

    for i in range(len(vertices)-1):
        pnt1 = vertices[i].getPosition(space=space)
        pnt2 = vertices[i+1].getPosition(space=space)
        length_list.append((pnt1 - pnt2).length())

    return length_list


def vertices_path_length(vertices, n=None, space="world"):
    """ [pm] vertices で渡された頂点の i 番目までの距離を返す｡ n を省略した場合は道のり全長を返す

    すべての頂点間の距離を調べるときは length_each_vertices() 推奨｡ピンポイント 1 点とかならこっちでも｡

    Args:
        vertices (list[MeshVertex]):
        space (str):

    Returns:
        float:

    """
    if n is None or n > len(vertices):
        n = len(vertices)-1

    path = 0.0

    for i in range(n):
        pnt1 = vertices[i].getPosition(space=space)
        pnt2 = vertices[i+1].getPosition(space=space)
        path += (pnt1 - pnt2).length()

    return path


def is_string(v):
    """文字列かどうか調べる

    Python2,3 併用メソッド

    Args:
        v (any): 型をチェックするオブジェクト
    """
    return isinstance(v, (str, type(u"")))


def get_object(component, pn=False, transform=False):
    """ [pm/cmds] component の所属するオブジェクトを取得する

    Args:
        component (Mesh, MeshVertex, MeshEdge, MeshFace, MeshVertexFace or str): 所属オブジェクトを取得するコンポーネント
        pn (bool): 現在は使用されていません
        transform (bool): True の場合 Mesh の親の Transform を返し、False の場合Mesh オブジェクトを返す

    Returns:
        str or PyNode: component の所属オブジェクト。component の型により str か PyNode を返す
    """
    if not component:
        return component

    pn = not is_string(component)

    if pn:
        if isinstance(component, nt.Transform):
            if transform:
                return component
            else:
                return component.getShape()

        elif isinstance(component, nt.Mesh):
            if transform:
                return component.getParent()
            else:
                return component
        elif isinstance(component, (pm.MeshVertex, pm.MeshEdge, pm.MeshFace, pm.MeshVertexFace)):
            if transform:
                return component.node().getParent()
            else:
                return component.node()
        else:
            raise(Exception("%s is not supported" % str(type(component))))

    else:
        return cmds.polyListComponentConversion(component)[0]


def to_vtx(components, pn=False):
    """ [pm/cmds]

    Args:
        components ([type]): [description]
        pn (bool, optional): [description]. Defaults to False.

    Returns:
        list[str or PyNode]:
    """
    if not components:
        return components

    if isinstance(components, list):
        pn = not is_string(components[0])
    else:
        pn = not is_string(components)

    if pn:
        return uniq(pynode(pm.filterExpand(pm.polyListComponentConversion(components, tv=True), sm=31)))
    else:
        return uniq(cmds.filterExpand(cmds.polyListComponentConversion(components, tv=True), sm=31))


def to_edge(components, pn=False):
    """ [pm/cmds]

    Args:
        components ([type]): [description]
        pn (bool, optional): [description]. Defaults to False.

    Returns:
        list[str or PyNode]:
    """
    if not components:
        return components

    if isinstance(components, list):
        pn = not is_string(components[0])
    else:
        pn = not is_string(components)

    if pn:
        return uniq(pynode(pm.filterExpand(pm.polyListComponentConversion(components, te=True), sm=32)))
    else:
        return uniq(cmds.filterExpand(cmds.polyListComponentConversion(components, te=True), sm=32))


def to_face(components, pn=False):
    """ [pm/cmds]

    Args:
        components ([type]): [description]
        pn (bool, optional): [description]. Defaults to False.

    Returns:
        list[str or PyNode]:
    """
    if not components:
        return components

    if isinstance(components, list):
        pn = not is_string(components[0])
    else:
        pn = not is_string(components)

    if pn:
        return uniq(pynode(pm.filterExpand(pm.polyListComponentConversion(components, tf=True), sm=34)))
    else:
        return uniq(cmds.filterExpand(cmds.polyListComponentConversion(components, tf=True), sm=34))


def to_uv(components, pn=False):
    """ [pm/cmds]

    Args:
        components ([type]): [description]
        pn (bool, optional): [description]. Defaults to False.

    Returns:
        list[str or PyNode]:
    """
    if not components:
        return components

    if isinstance(components, list):
        pn = not is_string(components[0])
    else:
        pn = not is_string(components)

    if pn:
        return uniq(pynode(pm.filterExpand(pm.polyListComponentConversion(components, tuv=True), sm=35)))
    else:
        return uniq(cmds.filterExpand(cmds.polyListComponentConversion(components, tuv=True), sm=35))


def to_vtxface(components, pn=False):
    """ [pm/cmds]

    Args:
        components ([type]): [description]
        pn (bool, optional): [description]. Defaults to False.

    Returns:
        list[str or PyNode]:
    """
    if not components:
        return components

    if isinstance(components, list):
        pn = not is_string(components[0])
    else:
        pn = not is_string(components)

    if pn:
        return uniq(pynode(pm.filterExpand(pm.polyListComponentConversion(components, tvf=True), sm=70)))
    else:
        return uniq(cmds.filterExpand(cmds.polyListComponentConversion(components, tvf=True), sm=70))


def to_border_vertices(components):
    """ [pm]
    """
    if not components:
        return components

    if isinstance(components, list):
        pn = not is_string(components[0])
    else:
        pn = not is_string(components)

    border = pm.filterExpand(pm.polyListComponentConversion(components, tv=True, border=True), sm=31)

    if border:
        if pn:
            return uniq(pynode(border))
        else:
            return uniq(border)
    else:
        return []


def to_border_edges(components):
    """ [pm]
    """
    if not components:
        return components

    if isinstance(components, list):
        pn = not is_string(components[0])
    else:
        pn = not is_string(components)

    border = pm.filterExpand(pm.polyListComponentConversion(components, te=True, border=True), sm=32)

    if border:
        if pn:
            return uniq(pynode(border))
        else:
            return uniq(border)
    else:
        return []


def to_border_vtxfaces(components):
    """ [pm]
    """
    if not components:
        return components

    if isinstance(components, list):
        pn = not is_string(components[0])
    else:
        pn = not is_string(components)

    faces = to_face(components)
    inner_vf = to_vtxface(faces)
    border_vertices = to_border_vertices(components)
    double_sided_border_vf = to_vtxface(border_vertices)

    border = list_intersection(double_sided_border_vf, inner_vf)

    if border:
        if pn:
            return uniq(pynode(border))
        else:
            return uniq(border)
    else:
        return []


def is_hardedge(edge):
    """ 引数のエッジがハードエッジなら True を返す

    Args:
        edge ([MeshEdge]): [description]

    Returns:
        bool: edge がハードエッジなら True
    """
    return "Hard" in pm.polyInfo(edge, edgeToVertex=True)[0]


def get_all_hardedges(obj):
    """オブジェクトのすべてのハードエッジを取得し cmds 形式の文字列のリストとして返す。

    引数は PyNode で戻り値は cmds 文字列なので注意。

    Args:
        obj (Transform or Mesh): ハードエッジを取得するオブジェクトかメッシュ

    Returns:
        list[MeshEdge]: [description]
    """
    current_selection = cmds.ls(selection=True)

    harden = []
    pm.select(obj.edges)
    pm.polySelectConstraint(mode=3, type=0x8000, smoothness=1)
    harden = cmds.ls(selection=True, flatten=True)
    pm.polySelectConstraint(mode=3, type=0x8000, smoothness=0)

    cmds.select(current_selection, replace=True)

    return harden


def get_all_softedges(obj):
    """オブジェクトのすべてのソフトエッジを取得し cmds 形式の文字列のリストとして返す。

    引数は PyNode で戻り値は cmds 文字列なので注意。

    Args:
        obj (Transform or Mesh): ハードエッジを取得するオブジェクトかメッシュ

    Returns:
        list[MeshEdge]: [description]
    """
    current_selection = cmds.ls(selection=True)

    harden = []
    pm.select(obj.edges)
    pm.polySelectConstraint(mode=3, type=0x8000, smoothness=2)
    harden = cmds.ls(selection=True, flatten=True)
    pm.polySelectConstraint(mode=3, type=0x8000, smoothness=0)

    cmds.select(current_selection, replace=True)

    return harden


def is_connected_vtxfaces(vf1, vf2):
    """ 頂点を共有する頂点フェース vf1 から vf2 へハードエッジを挟まずに到達できるか

    計算を途中で切り上げる分 get_connected_vtx_faces より高速｡
    ただし頂点を共有する全頂点フェースについて接続性を調べるなら get_connected_vtx_faces の方が高速｡

    Args:
        vf1 (MeshVertexFace): [description]
        vf2 (MeshVertexFace): [description]

    Returns:
        bool:

    """
    shared_vertex = to_vtx(vf1)[0]
    internal_vtxfaces = to_vtxface(shared_vertex)
    internal_edges = to_edge(shared_vertex)

    edge_queue = [e for e in to_edge(to_face(vf1)) if not is_hardedge(e) and e in internal_edges]
    processed_edges = []
    processed_vtxfaces = []

    processed_edges.extend([e for e in internal_edges if is_hardedge(e)] + edge_queue)

    i = 0
    while edge_queue:
        e = edge_queue.pop(0)
        processed_edges.append(e)
        adjacent_vtxfaces = list_intersection(to_vtxface(e), internal_vtxfaces)
        processed_vtxfaces.extend(adjacent_vtxfaces)

        if vf2 in adjacent_vtxfaces:
            return True

        next_edges = [ne for ne in to_edge(to_face(e)) if ne in internal_edges and ne != e and not is_hardedge(ne) and ne not in processed_edges]
        edge_queue.extend(next_edges)

        i += 1
        if i > 10:
            raise

    return False


def get_connected_vtx_faces(vf):
    """ 指定した頂点フェースと頂点を共有するすべての頂点フェースのうち､ハードエッジを挟まずに到達できるものをすべて返す

    Args:
        vf (MeshVertexFace): [description]

    Returns:
        list[MeshVertexFace]: [description]
    """
    connected_vtx_faces = []
    shared_vertex = to_vtx(vf)[0]
    internal_vtxfaces = to_vtxface(shared_vertex)
    internal_edges = to_edge(shared_vertex)

    edge_queue = [e for e in to_edge(to_face(vf)) if not is_hardedge(e) and e in internal_edges]
    processed_edges = []
    processed_vtxfaces = []

    processed_edges.extend([e for e in internal_edges if is_hardedge(e)] + edge_queue)

    i = 0
    while edge_queue:
        e = edge_queue.pop(0)
        processed_edges.append(e)
        adjacent_vtxfaces = list_intersection(to_vtxface(e), internal_vtxfaces)
        processed_vtxfaces.extend(adjacent_vtxfaces)

        connected_vtx_faces.extend(adjacent_vtxfaces)

        next_edges = [ne for ne in to_edge(to_face(e)) if ne in internal_edges and ne != e and not is_hardedge(ne) and ne not in processed_edges]
        edge_queue.extend(next_edges)

        i += 1
        if i > 10:
            raise

    return uniq(connected_vtx_faces)


def type_of_component(comp):
    """ [cmds] component の種類を返す

    TODO: 大雑把すぎるので修正する｡種類の網羅｡

    Args:
        comp (str):

    Returns:
        str or None: "e", "f", "v", None
    """
    if ".vtx[" in comp:
        return "vtx"
    elif ".e[" in comp:
        return "edge"
    elif ".f[" in comp:
        return "face"
    elif ".map[" in comp:
        return "uv"
    elif ".vtxFace[" in comp:
        return "vf"
    elif ".pt[" in comp:
        return "lattice_point"
    elif ".cv[" in comp:
        return "control_vertex"
    else:
        return None


def flatten(a):
    """ 多次元配列を一次元配列にする """
    from itertools import chain
    return list(chain.from_iterable(a))


def uniq(a):
    """ 配列の重複要素を取り除く """
    if a:
        elemtype = type(a[0])
        string_types = [type(""), type(u"")]  # Supports python2.x and python3.x
        if elemtype in string_types:
            elements_tuple_list = list(set([tuple(x) for x in a]))
            return ["".join(elements_tuple) for elements_tuple in elements_tuple_list]
        else:
            if is_python2():
                return list(set(a))
            else:
                hashable_a = [Hashable(x, str(x)) for x in a]
                list(set(hashable_a))
                a = [x.object for x in hashable_a]

                return a

    else:
        return a


def split_n_pair(a, n):
    """リストの要素を n 個ずつに区切りリストのリストとして返す

    Args:
        a (list[any]): 区切られるリスト

    Returns:
        list[list[any]]: n 個ずつに区切られたリストのリスト
    """
    if n == 0:
        raise(Exception("1以上の"))

    if len(a) % n != 0:
        raise(Exception(""))

    ret = [a[i:i+n] for i in range(0, len(a), n)]

    return ret


def round_vector(v, fraction):
    """ ベクトルの各要素をそれぞれ round する

    Args:
        v (list[float, float, float]):

    Returns:
        list[float, float, float]:
    """
    v = [round(x, fraction) for x in v]
    return v


def get_poly_line(edges, intersections=[]):
    """ [pm/cmds] edges を連続するエッジのまとまりとしてエッジリストを一つ返す

    intersections を指定することで実際には連続しているエッジ同士を分離する事が可能
    edges の型で pm/cmds を判断する｡

    Args:
        edges (list[str]):
        intersections (list[str or MeshVertex]): 実際にはトポロジーが連続していても連続していないと見なす点のリスト

    Returns:
        list[str]:

    """
    if isinstance(edges[0], pm.MeshEdge):
        return _get_poly_line_pm(edges, intersections=intersections)

    first_edge = edges[0]
    rest_edges = edges[1:]
    processed_edges = [first_edge]
    processed_vts = []
    vtx_queue = []
    polyline = [first_edge]

    # edges[0]のvts[0] から開始
    vtx_queue = list_diff(to_vtx(first_edge), intersections)

    while len(vtx_queue) > 0:
        for vtx in vtx_queue:
            # 処理済み頂点にvtx 追加
            processed_vts.append(vtx)
            vtx_queue = list_diff(list_diff(vtx_queue, processed_vts), intersections)  # TODO:本当に set set set より早いか

            # 未処理の隣接エッジの取得
            adjacent_edges = list_intersection(to_edge(vtx), rest_edges)

            if len(adjacent_edges) > 0:
                # 隣接エッジがあれば連続エッジに追加
                polyline.extend(adjacent_edges)

                # 処理済みエッジに追加
                processed_edges.extend(adjacent_edges)
                rest_edges = list_diff(rest_edges, adjacent_edges)

                # 隣接エッジの構成頂点のうち未処理のものをキューに追加する
                vtx_queue.extend(list_diff(list_diff(to_vtx(adjacent_edges), processed_vts), intersections))
            else:
                # 隣接エッジなし
                pass

    return polyline


def get_all_polylines(edges):
    """ [cmds] edges で指定したエッジ列を連続するエッジ列の集まりに分割してリストを返す

    edges の型で pm/cmds を判断する｡

    Args:
        edges (list[str]):

    Returns:
        list[list[str]]:

    """
    if isinstance(edges[0], pm.MeshEdge):
        return _get_all_polylines_pm(edges)

    polylines = []
    rest_edges = edges
    intersections = [v for v in to_vtx(edges) if len(set(to_edge(v)) & set(edges)) > 2]

    while len(rest_edges) > 0:
        polyline = get_poly_line(rest_edges, intersections)
        polylines.append(polyline)
        rest_edges = list_diff(rest_edges, polyline)

    return polylines


def _get_poly_line_pm(edges, intersections=[]):
    """ [pm] edges を連続するエッジのまとまりとしてエッジリストを一つ返す

    get_poly_line() から呼ばれる Pymel 版の実装｡基本的には直接呼ばず get_poly_line() を使う｡
    intersections を指定することで実際には連続しているエッジ同士を分離する事が可能

    Args:
        edges (list[MeshEdge]):
        intersections (list[MeshVertex]): 複数のエッジの交点と見なす頂点

    Returns:
        list[MeshEdge]:
    """
    first_edge = edges[0]
    rest_edges = edges[1:]  # 未処理エッジ
    processed_edges = [first_edge]  # 処理済みエッジ
    processed_vts = []  # 処理済み頂点
    polyline = [first_edge]  # 返値
    vtx_queue = list_diff(get_connected_vertices(first_edge), intersections)

    while len(vtx_queue) > 0:
        for vtx in vtx_queue:
            # 処理済み頂点にvtx 追加
            processed_vts.append(vtx)
            vtx_queue = list_diff(vtx_queue, processed_vts)

            # 隣接する未処理エッジの取得
            adjacent_edges = list_intersection(list(vtx.connectedEdges()), rest_edges)

            if len(adjacent_edges) > 0:
                # 隣接エッジがあれば連続エッジに追加
                polyline.extend(adjacent_edges)

                # 処理済みエッジに追加
                processed_edges.extend(adjacent_edges)
                rest_edges = list_diff(rest_edges, adjacent_edges)

                # 隣接エッジの構成頂点のうち未処理のものをキューに追加する
                vtx_queue.extend(list_diff(list_diff(to_vtx(adjacent_edges, pn=True), processed_vts), intersections))
            else:
                # 隣接エッジなし
                pass

    return polyline


def _get_all_polylines_pm(edges):
    """ [pm] edges で指定したエッジ列を連続するエッジ列の集まりに分割してリストを返す

    get_all_polylines() から呼ばれる Pymel 版の実装｡基本的には直接呼ばず get_all_polylines() を使う｡

    Args:
        edges (list[MeshEdge]):

    Returns:
        list[list[MeshEdge]]:

    """
    polylines = []
    rest_edges = edges

    # エッジ同士の交点
    intersections = []

    # 全ての構成頂点のうち､その頂点の接続エッジが edges に 2 本以上含まれていればその頂点は交点
    for v in to_vtx(edges, pn=True):
        connected_edges = to_edge(v, pn=True)
        if len(list_intersection(connected_edges, edges)) > 2:
            intersections.append(v)

    while len(rest_edges) > 0:
        polyline = _get_poly_line_pm(edges=rest_edges, intersections=intersections)
        polylines.append(polyline)
        rest_edges = list_diff(rest_edges, polyline)

    return polylines


def name_to_uuid(name):
    """ [cmds] ノード名からUUIDを取得する """
    uuid_list = cmds.ls(name, uuid=True)
    if len(uuid_list) == 1:
        return uuid_list[0]
    else:
        raise("name: " + name + "is not unique. try fullpath")


def uuid_to_name(uuid):
    """ [cmds] UUIDからノード名を取得する """
    return cmds.ls(uuid)[0]


def get_fullpath(name):
    """ [cmds] オブジェクト名のフルパスを取得する """
    return cmds.ls(name, l=True)[0]


def get_basename(name):
    """ネームスペースとパスを取り除いたオブジェクト自身の名前を取得する

    Args:
        name (str): ネームスペースやパスを含んでいる可能性のあるオブジェクト名

    Returns:
        str: ネームスペースとパスを取り除いたオブジェクト自身の名前
    """
    return re.sub(r"^.*\|", "", name)


def get_active_camera():
    """" 関数を呼んだ時点でアクティブなパネルでのアクティブカメラの取得 """
    active_panel = cmds.getPanel(wf=True)
    camera = cmds.modelPanel(active_panel, q=True, camera=True)

    return camera


def is_supported_weight_format_option():
    """ ウェイト関連機能の format オプションに対応しているかどうか

    Returns:
        bool:
    """
    ver = int(cmds.about(version=True))
    if ver > 2018:
        return True
    else:
        return False


def get_end_vertices_e(edges):
    """ [pm] 連続するエッジの端の頂点をすべて返す

    Args:
        edges(list[MeshEdge]): エッジリスト (順不同)

    Returns:
        list[MeshVertex]:
    """

    return get_end_vertices_v(to_vtx(edges, pn=True))


def get_end_vertices_v(vertices):
    """ [pm] 連続したエッジで接続される頂点の端の頂点を返す

    Args:
        vertices (list[MeshVertx]): 頂点リスト (順不同)

    Returns:
        list[MeshVertx]
    """
    end_vertices = []

    for vertex in vertices:
        connected_vertices = get_connected_vertices(vertex)
        if len(list_intersection(connected_vertices, vertices)) == 1:
            end_vertices.append(vertex)

    return end_vertices


def sort_edges(edges):
    """ [pm] エッジをトポロジーの連続性でソートする

    Args:
        edges (list[MeshEdge]): 未ソートエッジリスト

    Returns:
        list[MeshEdge]: ソート済エッジリスト
    """
    def part_vertex_list(edges, first_vertex):
        """ 部分エッジ集合と開始頂点から再帰的に頂点列を求める """
        neighbors = to_edge(first_vertex)
        next_edges = list_intersection(neighbors, edges)

        if len(next_edges) == 1:
            next_edge = next_edges[0]
            vset1 = set(to_vtx(next_edge))
            vset2 = {first_vertex}
            next_vertex = list(vset1-vset2)[0]
            rest_edges = list_diff(edges, next_edges)
            partial_vts = part_vertex_list(rest_edges, next_vertex)
            partial_vts.insert(0, first_vertex)
            return partial_vts
        else:
            return [first_vertex]

    first_vertex = get_end_vertices_e(edges)[0]

    return part_vertex_list(edges, first_vertex)


def sort_vertices(vertices):
    """ [pm] 頂点をトポロジーの連続性でソートする

    やや重いのでソート済エッジがすでの存在するならば sorted_edges_to_vertices() 使う

    Args:
        vertices (list[MeshVertex): 未ソート頂点リスト

    Returns:
        list[MeshVertex]: ソート済頂点リスト
    """
    def part_vertex_list(vertices, first_vertex):
        """ 部分エッジ集合と開始頂点から再帰的に頂点列を求める """
        neighbors = list(first_vertex.connectedVertices())
        next_vertices = list_intersection(neighbors, vertices)

        if len(next_vertices) == 1:
            next_vertex = next_vertices[0]
            rest_vertices = list_diff(vertices, next_vertices)
            partial_vertices = part_vertex_list(rest_vertices, next_vertex)
            partial_vertices.insert(0, first_vertex)
            return partial_vertices
        else:
            return [first_vertex]

    first_vertex = get_end_vertices_v(vertices)[0]
    rest_vertices = list_diff(vertices, [first_vertex])

    return part_vertex_list(rest_vertices, first_vertex)


def sorted_edges_to_vertices(edges):
    """ [pm] ソートされたエッジを同じ順序でソートされた頂点に変換する

    Args:
        edges (list[MeshEdge]): ソート済エッジリスト

    Returns:
        list[MeshVertex]: ソート済頂点リスト
    """
    sorted_vertices = []
    first_vertices = list_diff(edges[0].vertices(), edges[1].vertices())[0]
    sorted_vertices.append(first_vertices)

    for i in range(len(edges)-1):
        edge = edges[i]
        next_edge = edges[i+1]
        shared_vertex = list_intersection(edge.vertices(), next_edge.vertices())[0]
        sorted_vertices.append(shared_vertex)

    return sorted_vertices


def sorted_vertices_to_edges(vertices):
    """ [pm] ソートされた頂点を同じ順序でソートされたエッジに変換する

    Args:
        list[MeshVertex]: ソート済頂点リスト

    Returns:
        edges (list[MeshEdge]): ソート済エッジリスト
    """
    sorted_edges = []

    for i in range(len(vertices)-1):
        vertex = vertices[i]
        next_vertex = vertices[i+1]
        shared_edge = list_intersection(list(vertex.connectedEdges()), list(next_vertex.connectedEdges()))[0]
        sorted_edges.append(shared_edge)

    return sorted_edges


def coords_to_vector(coords):
    """ [pm] フラットなリストとして保存されている複数法線を 3 つずつ区切って Pymel の Vector に変換する

    Args:
        coords ([type]): [description]

    Returns:
        [type]: [description]
    """
    vectors = [dt.Vector(coords[i], coords[i+1], coords[i+2]) for i in range(0, len(coords), 3)]

    return vectors


def apply_tweak(target, delete_history=True):
    """ Tweakノードと pnts アトリビュートをコンポーネント座標に適用する

    Args:
        target (Mesh or Transform): 適用対象の Mesh 自身か Mesh を子に持つ Transform
        delete_history (bool): True の場合処理の最後にノンデフォーマーヒストリーを削除する. default to True

    Returns:
        bool: 成功した場合は True, 失敗した場合は False
    """
    current_selection = pm.selected()

    if isinstance(target, nt.Transform):
        obj = target
        shape = target.getShape()

    elif isinstance(target, nt.Mesh):
        obj = target.getParent()
        shape = target

    else:
        return False

    # Tweak ノードの適用
    tweak_nodes = [x for x in shape.connections() if isinstance(x, nt.Tweak)]

    if tweak_nodes:
        tweak_node = tweak_nodes[0]
        current_points = get_points(shape.name())
        pm.delete(tweak_node)
        set_points(shape.name(), current_points)

    # pnts の適用
    pm.polyMergeVertex(obj.verts[0])

    if delete_history:
        pm.bakePartialHistory(obj, ppt=True)

    pm.select(current_selection)


def get_position(comp, space):
    """ コンポーネントから座標を取得する

    Args:
        comp ([type]): [description]
        space ([type]): [description]

    Returns:
        [type]: [description]
    """
    # TODO: ひととおり型毎の分岐書く
    if isinstance(comp, pm.MeshVertex):
        return comp.getPosition(space=space)
    else:
        return to_vtx(comp)[0].getPosition(space=space)


def get_center_point(targets):
    """ 指定したコンポーネントのローカル空間でのバウンディングボックスの中心を取得する

    API 等で取得できるバウンディングボックスは親の座標系でのバウンディングボックス。これは子のシェープの座標系でのバウンディングボックス。

    Args:
        targets ([type]): [description]

    Returns:
        [type]: [description]
    """

    if not targets:
        raise(Exception())

    points = [x.getPosition(space="object") for x in to_vtx(targets)]

    min_x = points[0].x
    min_y = points[0].y
    min_z = points[0].z
    max_x = points[0].x
    max_y = points[0].y
    max_z = points[0].z

    for p in points:

        if p.x < min_x:
            min_x = p.x

        if p.x > max_x:
            max_x = p.x

        if p.y < min_y:
            min_y = p.y

        if p.y > max_y:
            max_y = p.y

        if p.z < min_z:
            min_z = p.z

        if p.z > max_z:
            max_z = p.z

    return dt.Point((max_x+min_x)/2, (max_y+min_y)/2, (max_z+min_z)/2)


def get_normals(shape):
    """[pm] APIを使用した法線取得｡引数は PyNode"""
    sel = om.MSelectionList()
    sel.add(shape.name())
    dag = sel.getDagPath(0)
    fn_mesh = om.MFnMesh(dag)

    return fn_mesh.getNormals()


def set_normals(shape, normals):
    """[pm] APIを使用した法線設定｡引数は PyNode"""
    sel = om.MSelectionList()
    sel.add(shape.name())
    dag = sel.getDagPath(0)
    fn_mesh = om.MFnMesh(dag)

    fn_mesh.setNormals(normals)
    fn_mesh.updateSurface()


def get_points(shape, space=om.MSpace.kObject):
    """APIを使用した頂点座標取得"""
    sel = om.MSelectionList()
    sel.add(shape)
    dag = sel.getDagPath(0)
    fn_mesh = om.MFnMesh(dag)

    return fn_mesh.getPoints(space=space)


def set_points(shape, points, space=om.MSpace.kObject):
    """APIを使用した頂点座標設定"""
    sel = om.MSelectionList()
    sel.add(shape)
    dag = sel.getDagPath(0)
    fn_mesh = om.MFnMesh(dag)

    fn_mesh.setPoints(points, space=space)
    fn_mesh.updateSurface()


def get_smooths(shape):
    """[pm] APIを使用したハードエッジ情報取得。引数はPyNode"""
    sel = om.MSelectionList()
    sel.add(shape.name())
    dag = sel.getDagPath(0)
    fn_mesh = om.MFnMesh(dag)
    all_edge_ids = range(fn_mesh.numEdges)
    edge_smooths = [fn_mesh.isEdgeSmooth(ei) for ei in all_edge_ids]

    return edge_smooths


def set_smooths(shape, edge_smooths):
    """[pm] APIを使用したハードエッジ情報設定。引数はPyNode"""
    sel = om.MSelectionList()
    sel.add(shape.name())
    dag = sel.getDagPath(0)
    fn_mesh = om.MFnMesh(dag)
    all_edge_ids = range(fn_mesh.numEdges)
    fn_mesh.setEdgeSmoothings(all_edge_ids, edge_smooths)


def get_normal_locks(shape):
    """[pm] APIを使用した法線ロック情報取得。引数はPyNode"""
    obj = om.MGlobal.getSelectionListByName(shape.name()).getDagPath(0)
    fn_mesh = om.MFnMesh(obj)

    # ロック状態の取得
    locks = [None] * fn_mesh.numNormals

    all_vf = om.MItMeshFaceVertex(obj, om.MObject.kNullObj)
    while not all_vf.isDone():
        vf = all_vf
        fi = vf.faceId()
        vi = vf.vertexId()
        ni = vf.normalId()

        locks[ni] = fn_mesh.isNormalLocked(ni)

        all_vf.next()

    return locks


def set_normal_locks(shape, locks):
    """[pm] APIを使用した法線ロック情報設定。引数はPyNode"""
    obj = om.MGlobal.getSelectionListByName(shape.name()).getDagPath(0)
    fn_mesh = om.MFnMesh(obj)

    smooths = get_smooths(shape)

    # API の引数用リストの作成
    locked_fi = []
    locked_vi = []
    unlocked_fi = []
    unlocked_vi = []

    all_vf = om.MItMeshFaceVertex(obj, om.MObject.kNullObj)
    while not all_vf.isDone():
        vf = all_vf
        fi = vf.faceId()
        vi = vf.vertexId()
        ni = vf.normalId()

        if locks[ni]:
            locked_fi.append(fi)
            locked_vi.append(vi)

        else:
            unlocked_fi.append(fi)
            unlocked_vi.append(vi)

        all_vf.next()

    fn_mesh.lockFaceVertexNormals(locked_fi, locked_vi)
    fn_mesh.unlockFaceVertexNormals(unlocked_fi, unlocked_vi)

    # ハードエッジの復帰
    set_smooths(shape, smooths)

    fn_mesh.updateSurface()


def get_normal_locks_index_pair(shape):
    """[pm] APIを使用した法線ロック情報取得。引数はPyNode"""
    obj = om.MGlobal.getSelectionListByName(shape.name()).getDagPath(0)
    fn_mesh = om.MFnMesh(obj)

    # ロック状態の取得
    locks = dict()

    all_vf = om.MItMeshFaceVertex(obj, om.MObject.kNullObj)
    while not all_vf.isDone():
        vf = all_vf
        fi = vf.faceId()
        vi = vf.vertexId()
        ni = vf.normalId()

        locks[(fi, vi)] = fn_mesh.isNormalLocked(ni)

        all_vf.next()

    return locks


def set_normal_locks_index_pair(shape, locks):
    """[pm] APIを使用した法線ロック情報設定。引数はPyNode"""
    if not isinstance(locks, dict):
        raise

    obj = om.MGlobal.getSelectionListByName(shape.name()).getDagPath(0)
    fn_mesh = om.MFnMesh(obj)

    smooths = get_smooths(shape)

    # API の引数用リストの作成
    locked_fi = []
    locked_vi = []
    unlocked_fi = []
    unlocked_vi = []

    all_vf = om.MItMeshFaceVertex(obj, om.MObject.kNullObj)
    while not all_vf.isDone():
        vf = all_vf
        fi = vf.faceId()
        vi = vf.vertexId()
        ni = vf.normalId()

        if locks[(fi, vi)]:
            locked_fi.append(fi)
            locked_vi.append(vi)

        else:
            unlocked_fi.append(fi)
            unlocked_vi.append(vi)

        all_vf.next()

    fn_mesh.lockFaceVertexNormals(locked_fi, locked_vi)
    fn_mesh.unlockFaceVertexNormals(unlocked_fi, unlocked_vi)

    # ハードエッジの復帰
    set_smooths(shape, smooths)

    fn_mesh.updateSurface()


def is_face(comp):
    """[om] 指定したコンポーネント(MObject) がフェースなら True を返す

    Args:
        comp ([MObject]): コンポーネント

    Returns:
        bool: コンポーネントがフェースならTrue, それ以外なら False
    """
    return comp.apiType() == om.MFn.kMeshPolygonComponent


def is_edge(comp):
    """[om] 指定したコンポーネント(MObject) がエッジなら True を返す

    Args:
        comp ([MObject]): コンポーネント

    Returns:
        bool: コンポーネントがエッジならTrue, それ以外なら False
    """
    return comp.apiType() == om.MFn.kMeshEdgeComponent


def is_vertex(comp):
    """[om] 指定したコンポーネント(MObject) が頂点なら True を返す

    Args:
        comp ([MObject]): コンポーネント

    Returns:
        bool: コンポーネントが頂点ならTrue, それ以外なら False
    """
    return comp.apiType() == om.MFn.kMeshVertComponent


def is_vertexface(comp):
    """[om] 指定したコンポーネント(MObject) が頂点フェースなら True を返す

    Args:
        comp ([MObject]): コンポーネント

    Returns:
        bool: コンポーネントが頂点フェースならTrue, それ以外なら False
    """
    return comp.apiType() == om.MFn.kMeshVtxFaceComponent


def convert_mobject_type(obj, comp, from_type, to_type):
    """[om] MObject のコンポーネントタイプを変換する

    Args:
        obj (MDagPath): コンポーネントが所属するオブジェクト
        comp (MObject): コンポーネント
        from_type (str): 変換元のコンポーネントタイプ
        to_type (str): 変換先のコンポーネントタイプ

    Returns:
        MObject: 変換されたコンポーネント
    """
    fn_mesh = om.MFnMesh(obj)
    converted_comp = None

    if from_type == "e" and to_type == "v":
        # 変換元エッジのイテレーター
        e_itr = om.MItMeshEdge(obj, comp)

        # 変換後のコンポーネントと MObject
        components = om.MFnSingleIndexedComponent()
        converted_comp = components.create(om.MFn.kMeshVertComponent)

        # エッジの構成頂点をすべて MObject に追加する
        while not e_itr.isDone():
            ei = e_itr.index()
            ids = list(fn_mesh.getEdgeVertices(ei))
            components.addElements(ids)

            e_itr.next()

    elif from_type == "f" and to_type == "v":
        # 変換元エッジのイテレーター
        f_itr = om.MItMeshPolygon(obj, comp)

        # 変換後のコンポーネントと MObject
        components = om.MFnSingleIndexedComponent()
        converted_comp = components.create(om.MFn.kMeshVertComponent)

        # エッジの構成頂点をすべて MObject に追加する
        while not f_itr.isDone():
            fi = f_itr.index()
            ids = list(fn_mesh.getPolygonVertices(fi))
            components.addElements(ids)

            f_next(f_itr)

    elif from_type == "vf" and to_type == "v":
        # 変換元エッジのイテレーター
        vf_itr = om.MItMeshFaceVertex(obj, comp)

        # 変換後のコンポーネントと MObject
        components = om.MFnSingleIndexedComponent()
        converted_comp = components.create(om.MFn.kMeshVertComponent)

        # エッジの構成頂点をすべて MObject に追加する
        while not vf_itr.isDone():
            vi = vf_itr.vertexId()
            components.addElements([vi])

            vf_itr.next()

    return converted_comp


def is_skined(shape):
    """指定したシェイプがバインド済みならTrueを返す

    Args:
        shape (Mesh): バインド済みか調べるメッシュ

    Returns:
        bool: バインド済みならTrue, 未バインドならFalse を返す
    """
    skined = False

    if any([isinstance(x, nt.SkinCluster) for x in shape.inputs()]):
        skined = True
    else:
        object_sets = [x for x in shape.inputs() if isinstance(x, nt.ObjectSet)]
        for object_set in object_sets:
            if any([isinstance(x, nt.SkinCluster) for x in object_set.inputs()]):
                skined = True

    return skined


def get_orig_shape(skined_mesh):
    """指定したシェイプの Orig シェイプを取得する

    Args:
        shape (Mesh): Origメッシュを取得するバインド済みメッシュ

    Returns:
        Mesh: Origメッシュ
    """
    obj = skined_mesh.getParent()
    intermediate_shapes = [x for x in pm.listRelatives(obj, shapes=True, noIntermediate=False) if x.intermediateObject.get()]

    for shape in intermediate_shapes:
        connections = shape.connections()
        non_info_nodes = [c for c in connections if not isinstance(c, nt.NodeGraphEditorInfo)]

        if len(non_info_nodes) != 0 and shape.intermediateObject.get():
            return shape

    if intermediate_shapes:
        return intermediate_shapes[0]

    else:
        return None


def delete_invalid_orig_shape(obj):
    """指定したトランスフォームノード以下にある不要な Orig シェイプを削除する

    Args:
        obj (Transform): バインドされたシェイプを持つトランスフォームノード
    """
    for shape in pm.listRelatives(obj, s=True):
        connections = shape.connections()
        non_info_nodes = [c for c in connections if not isinstance(c, nt.NodeGraphEditorInfo)]

        if len(non_info_nodes) == 0:
            pm.delete(shape)


def f_next(face_itr):
    """MItMeshPolygon の next() を呼ぶ。

    Maya2019 以前の不具合対策
    https://forums.autodesk.com/t5/maya-programming/mitmeshpolygon-next-takes-an-argument-wrong-documentation/td-p/6252636

    Args:
        face_itr (MItMeshPolygon): フェースのイテレーター
    """
    ver = int(cmds.about(version=True))

    if ver < 2019:
        face_itr.next(None)
    else:
        face_itr.next()
# フォーマットオプションをサポートしているかを返す


def is_same_topology(shape1, shape2):
    """[pm] 二つのシェープのトポロジーが一致しているか調べる｡

    Args:
        shape1 (Mesh): 比較するメッシュ1
        shape2 (Mesh): 比較するメッシュ2

    Returns:
        bool: ふたつのシェープのトポロジーが一致していれば True を返す
    """
    return pm.polyCompare(shape1, shape2, faceDesc=True) == 0


def is_format_option_supported():
    """ウェイトのインポートエクスポートが format オプションに対応している場合 True を返す

    Returns:
        [type]: [description]
    """
    ver = int(cmds.about(version=True))
    if ver > 2018:
        return True
    else:
        return False


def lock_trs(obj):
    """[pm/cmds]指定したオブジェクトのトランスフォームをロックする

    Args:
        obj (Transform or str): トランスフォームをロックするトランスフォームノード
    """
    obj = pynode(obj)
    obj.translateX.lock()
    obj.translateY.lock()
    obj.translateZ.lock()
    obj.rotateX.lock()
    obj.rotateY.lock()
    obj.rotateZ.lock()
    obj.scaleX.lock()
    obj.scaleY.lock()
    obj.scaleZ.lock()


def unlock_trs(obj):
    """[pm/cmds]指定したオブジェクトのトランスフォームをアンロックする

    Args:
        obj (Transform or str): トランスフォームをアンロックするトランスフォームノード
    """
    obj = pynode(obj)
    obj.translateX.unlock()
    obj.translateY.unlock()
    obj.translateZ.unlock()
    obj.rotateX.unlock()
    obj.rotateY.unlock()
    obj.rotateZ.unlock()
    obj.scaleX.unlock()
    obj.scaleY.unlock()
    obj.scaleZ.unlock()


def exist_file(dir, filename):
    """ファイルが存在する場合は True を返す

    Args:
        dir (str): 存在するか調べるパス
        filename (str): 存在するか調べるファイル名

    Returns:
        bool: ファイルが存在する場合は True, 存在しない場合は False
    """
    path = dir + filename

    return os.path.exists(path)


def get_shape(object, fullPath=False, path=True):
    """オブジェクトからシェイプを取得する

    Args:
        object (str): シェイプを取得するオブジェクト名

    Returns:
        str or None: シェイプノード
    """
    shape = (cmds.listRelatives(object, shapes=True, fullPath=fullPath, path=path) or [None])[0]

    return shape


def get_parent(object, fullPath=False, path=True):
    """オブジェクトの親を取得する

    Args:
        object (str): 親を取得するオブジェクト名

    Returns:
        str or None: 親ノード
    """
    parent = (cmds.listRelatives(object, parent=True, fullPath=fullPath, path=path) or [None])[0]

    return parent


def get_indices(comp):
    """コンポーネント文字列からインデックスを取得する

    Args:
        comp (str): コンポーネントを表す文字列
    """
    indices = re.findall(r"\[(\d+)\]", comp)

    return [int(i) for i in indices]
