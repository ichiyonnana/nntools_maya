"""カーブをプリミティブ (キューブ・スフィア・シリンダー) に変換する。

ジェスチャ
    キューブ    : 矩形を構成する2辺をストロークする。始点と終点が対角になる。
    スフィア    : 線の往復(1.5往復以上)をストロークする。ストロークの幅が球の直径となる。
    シリンダー  : 閉じた四角形を描く。最初に描いた辺が柱の側面になる。

図形の判定
    長さ比   = ストローク長 / バウンディングボックスの周長
    始終点比 = 始点と終点の距離 / ストローク長
    上から順に当てはめる。
        長さ比 >= 1.5   -> スフィア（往復線やぐるぐる書いた円）
        始終点比 <= 0.1 -> シリンダー（閉じた四角形）
        長さ比 >= 0.7   -> スフィア（閉じていない長めのストローク）
        どれでもない    -> キューブ (閉じていない短いストローク)

サイズと姿勢
    3 点で決める。A = 始点、B = 対角の点、F = 直線 AB から最も遠い点。
    スフィア    : 最も遠い 2 点を直径とし、その中点を中心とする（A・B・F は使わない）。
    キューブ    : B = 終点。A と F を通る直線に辺が乗る長方形を作るので、角は必ず直角になる。
    シリンダー  : B = A から最も遠い点。長方形の作り方はキューブと同じ。
                  側面はストローク上の通過順で決める（仕様上の呼び名で ACB / ABC 方式）。
                      A -> F -> B の順なら AF に平行な辺が側面
                      A -> B -> F の順なら AF に垂直な辺が側面
                  残る 2 辺が円の断面。F がどちらの角に落ちても同じ辺が選ばれる。

軸の取り方
    キューブ    : AF がローカル Y、FB がローカル X。Z の厚みは FB に合わせる。
    スフィア    : 回転なし（常にワールド空間）。
    シリンダー  : Y が柱の方向、Z はワールド Z。
    カーブが XY 平面にあるため、どれも Z 回転だけで姿勢が決まる。
    Z 位置はサンプリング点の Z の平均を使う。
"""

import math

import maya.cmds as cmds

# --- 調整用の閾値 ------------------------------------------------------------
WIND_RATIO = 1.5     # ストローク長 / バウンディングボックス周長。これ以上なら始終点に関わらず円
CIRCLE_RATIO = 0.7   # 同上。始終点が離れたストロークでこれ以上なら円
CLOSE_RATIO = 0.1    # 始点と終点の距離 / ストローク長。これ以下なら始終点が近い

MIN_SAMPLES = 200    # カーブの再サンプリング数


# --- ストロークの指標 --------------------------------------------------------
def stroke_length(points):
    return sum(math.dist(points[i - 1], points[i]) for i in range(1, len(points)))


def bbox_perimeter(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return 2 * ((max(xs) - min(xs)) + (max(ys) - min(ys)))


def farthest_pair(points):
    """最も遠い 2 点を返す。総当たりで求める。"""
    best = (points[0], points[0])
    far = -1.0
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            d = math.dist(points[i], points[j])
            if d > far:
                best, far = (points[i], points[j]), d
    return best


def farthest_index(points, origin):
    return max(range(len(points)), key=lambda i: math.dist(points[i], origin))


def farthest_index_from_line(points, a, b):
    """直線 ab から最も遠い点の番号を返す。長方形の向きを決める基準になる。"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    span = math.hypot(dx, dy)
    if span == 0:
        return farthest_index(points, a)
    return max(range(len(points)), key=lambda i: abs(dy * (points[i][0] - a[0]) - dx * (points[i][1] - a[1])) / span)


# --- 形状と姿勢の決定 --------------------------------------------------------
def rect_from_diagonal(p1, p3, f):
    """p1-p3 を対角線とし、p1 と f を通る直線に辺が乗る長方形の 4 頂点を返す。"""
    ux, uy = f[0] - p1[0], f[1] - p1[1]
    norm = math.hypot(ux, uy)
    if norm == 0:
        ux, uy = p3[0] - p1[0], p3[1] - p1[1]
        norm = math.hypot(ux, uy)
    ux, uy = ux / norm, uy / norm
    t = (p3[0] - p1[0]) * ux + (p3[1] - p1[1]) * uy
    p2 = (p1[0] + t * ux, p1[1] + t * uy)
    p4 = (p1[0] + p3[0] - p2[0], p1[1] + p3[1] - p2[1])
    return [p1, p2, p3, p4]


def circle_shape(points):
    a, b = farthest_pair(points)
    center = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    return ("circle", center, math.dist(a, b) / 2), [a, b]


def rect_shape(points, p1, p3):
    f = points[farthest_index_from_line(points, p1, p3)]
    return ("rect", rect_from_diagonal(p1, p3, f)), [p1, p3, f]


def cylinder_shape(points):
    """始点 A、最も遠い点 B、AB から最も遠い点 C で長方形を作り、最初に描いた辺を側面とする。

    ストローク上の順序が ACB なら最初に描いた辺は AC に平行、ABC なら AC に垂直。
    """
    a = points[0]
    ib = farthest_index(points, a)
    ic = farthest_index_from_line(points, a, points[ib])
    verts = rect_from_diagonal(a, points[ib], points[ic])
    return ("cylinder", verts, ic < ib), [a, points[ib], points[ic]]


def cylinder_edges(verts, side_parallel):
    """円柱の (側面の 2 辺, 円の断面の 2 辺) を返す。辺は頂点のペア。"""
    a, p2, b, p4 = verts
    parallel, perpendicular = [(a, p2), (b, p4)], [(p2, b), (p4, a)]
    return (parallel, perpendicular) if side_parallel else (perpendicular, parallel)


def describe(shape):
    """図形データを姿勢が読み取れる文字列にする。"""
    if shape[0] == "circle":
        center, r = shape[1], shape[2]
        return "中心 (%.0f, %.0f) / 直径 %.1f" % (center[0], center[1], r * 2)
    verts = shape[1]
    w = math.dist(verts[0], verts[1])
    h = math.dist(verts[1], verts[2])
    angle = math.degrees(math.atan2(verts[1][1] - verts[0][1], verts[1][0] - verts[0][0]))
    corners = " ".join("(%.0f, %.0f)" % (x, y) for x, y in verts)
    text = "頂点 %s / 辺 %.1f x %.1f / 角度 %.1f 度" % (corners, w, h, angle)
    if shape[0] == "cylinder":
        side, cap = cylinder_edges(verts, shape[2])
        text += " / 描き順 %s / 軸長 %.1f / 直径 %.1f" % ("ACB" if shape[2] else "ABC", math.dist(*side[0]), math.dist(*cap[0]))
    return text


def recognize(points):
    """ストロークを図形へ変換する。戻り値は (図形名, 指標の文字列, 図形データ, 構成点)。"""
    length = stroke_length(points)
    perimeter = bbox_perimeter(points)
    if length == 0 or perimeter == 0:
        return "点", "長さ 0", None, []

    ratio = length / perimeter
    gap_ratio = math.dist(points[0], points[-1]) / length

    if ratio >= WIND_RATIO:
        name = "円"
    elif gap_ratio <= CLOSE_RATIO:
        name = "円柱"
    elif ratio >= CIRCLE_RATIO:
        name = "円"
    else:
        name = "矩形"

    if name == "円":
        shape, basis = circle_shape(points)
    elif name == "円柱":
        shape, basis = cylinder_shape(points)
    else:
        shape, basis = rect_shape(points, points[0], points[-1])

    detail = "点数 %d / 長さ %.1f / 周長 %.1f / 長さ比 %.3f (円 >=%.2f, 開いた円 >=%.2f) / 始終点比 %.3f (近い <=%.2f)" % (len(points), length, perimeter, ratio, WIND_RATIO, CIRCLE_RATIO, gap_ratio, CLOSE_RATIO)
    return name, detail + "\n" + describe(shape), shape, basis


# --- Maya への配置 -----------------------------------------------------------
def sample_curve(curve):
    """カーブ上を等間隔パラメータでサンプリングし、XY 平面の点列と Z の平均を返す。"""
    lo = cmds.getAttr(curve + ".minValue")
    hi = cmds.getAttr(curve + ".maxValue")
    count = max(MIN_SAMPLES, cmds.getAttr(curve + ".spans") * 2)
    points = [cmds.pointPosition("%s.u[%f]" % (curve, lo + (hi - lo) * i / (count - 1)), world=True) for i in range(count)]
    return [(p[0], p[1]) for p in points], sum(p[2] for p in points) / len(points)


def diagonal_center(verts):
    return ((verts[0][0] + verts[2][0]) / 2, (verts[0][1] + verts[2][1]) / 2)


def direction_angle(a, b):
    """a から b へ向かう向きの角度（度）。"""
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def place_cube(verts, z):
    a, f, b = verts[0], verts[1], verts[2]
    height = math.dist(a, f)   # AF がローカル Y
    width = math.dist(f, b)    # FB がローカル X
    cube = cmds.polyCube(w=1, h=1, d=1)[0]
    center = diagonal_center(verts)
    cmds.xform(cube, translation=(center[0], center[1], z), rotation=(0, 0, direction_angle(f, b)), scale=(width, height, width))
    return cube


def place_sphere(center, radius, z):
    sphere = cmds.polySphere(r=1, sa=16, sh=8)[0]  # 円周 16 / 高さ 8
    cmds.xform(sphere, translation=(center[0], center[1], z), scale=(radius, radius, radius))
    return sphere


def place_cylinder(verts, side_parallel, z):
    side, cap = cylinder_edges(verts, side_parallel)
    axis = side[0]
    radius = math.dist(*cap[0]) / 2
    cylinder = cmds.polyCylinder(r=1, h=1, sa=8, sh=1, sc=1)[0]  # 円周 8 / 高さ 1 / キャップ分割あり
    center = diagonal_center(verts)
    # polyCylinder の軸は Y。柱の方向へ向けるぶんだけ Z 回転させれば、ローカル Z はワールド Z のまま残る。
    cmds.xform(cylinder, translation=(center[0], center[1], z), rotation=(0, 0, direction_angle(axis[0], axis[1]) - 90), scale=(radius, math.dist(*axis), radius))
    return cylinder


def convert(curve):
    """カーブ 1 本をプリミティブへ置き換える。戻り値は (図形名, 生成ノード, 指標の文字列)。"""
    points, z = sample_curve(curve)
    name, detail, shape, _ = recognize(points)
    if shape is None:
        return None
    if shape[0] == "circle":
        node = place_sphere(shape[1], shape[2], z)
    elif shape[0] == "cylinder":
        node = place_cylinder(shape[1], shape[2], z)
    else:
        node = place_cube(shape[1], z)
    transform = cmds.listRelatives(curve, parent=True, fullPath=True)[0]
    parent = cmds.listRelatives(transform, parent=True, fullPath=True)
    if parent:
        node = cmds.parent(node, parent[0])[0]  # ワールド位置は保たれる
    cmds.delete(transform)
    return name, node, detail


def main():
    curves = cmds.ls(selection=True, dag=True, type="nurbsCurve", long=True)
    if not curves:
        cmds.warning("カーブが選択されていません")
        return
    created = []
    for curve in curves:
        result = convert(curve)
        if result is None:
            cmds.warning("%s は点が足りず変換できません" % curve)
            continue
        name, node, detail = result
        created.append(node)
        print("%s -> %s  |  %s" % (node, name, detail.replace("\n", "  |  ")))
    cmds.select(created)
