"""
カーブ関連
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om

from . import core


def make_curve_from_edges(edges, n=4):
    """ [cmds] エッジからカーブを生成する

    エッジ列からカーブを生成して､カーブを返す
    エッジ列がひとつながりでない場合はどれか一つだけがカーブ生成される (polyToCurve の振る舞いに従う)
    複数カーブが必要な場合､エッジ列の適切な分割は関数の外で行い複数回呼ぶ

    Args:
        edges (list[str]): カーブの生成に使うエッジ列｡ すべてのエッジが連続していればリストの要素自体は順不同
        n (int, optional): 生成されるカーブのスパン数｡ 0 で スパン数 1 ､それ以外は n+2 ｡ デフォルト 4

    Returns:
        str: 生成されたカーブのトランスフォームノード名
    """
    n = int(n)

    current_selections = cmds.ls(selection=True, flatten=True)

    # カーブ生成とリビルド
    cmds.select(edges, replace=True)
    curve = cmds.polyToCurve(form=2, degree=3, conformToSmoothMeshPreview=1)[0]

    # n が 0 の時は 直線にする
    if n <= 0:
        cmds.rebuildCurve(curve, ch=1, rpo=1, rt=0, end=1, kr=2, kcp=0, kep=1, kt=0, s=1, d=1, tol=0.01)
    else:
        cmds.rebuildCurve(curve, ch=1, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s=n, d=3, tol=0.01)

    cmds.delete(curve, ch=True)
    cmds.select(current_selections, replace=True)

    return curve


def get_points_at_params(curve, params, space="world"):
    """ [cmds] getPointAtParam の複数パラメーター版

    Args:
        curve (str): カーブのトランスフォームノード名
        params (list[float]): サンプリングする param の配列

    Returns:
        list[om.MPoint]: 各 param に対応するワールド座標のリスト
    """
    current_selections = cmds.ls(selection=True, flatten=True)

    # 内部リビルド
    # 直線時に開始位置がずれるバグ対策も兼ね
    target_curve = cmds.duplicate(curve)[0]
    shape = cmds.listRelatives(curve, shapes=True)[0]
    n = cmds.getAttr(f"{shape}.degree") + cmds.getAttr(f"{shape}.spans")
    k = 8
    cmds.rebuildCurve(target_curve, ch=1, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s=n*k, d=3, tol=0.01)
    cmds.delete(target_curve, ch=True)

    target_shape = cmds.listRelatives(target_curve, shapes=True)[0]
    sel = om.MGlobal.getSelectionListByName(target_shape)
    fn_curve = om.MFnNurbsCurve(sel.getDagPath(0))

    om_space = om.MSpace.kWorld if space == "world" else om.MSpace.kObject
    points = [fn_curve.getPointAtParam(param, om_space) for param in params]

    cmds.delete(target_curve)
    if current_selections:
        cmds.select(current_selections, replace=True)

    return points


def fit_vertices_to_curve(vertices, curve, keep_ratio=True, multiplier=1.0, auto_reverse=True, space="world", surface_constraint=False, preserve_uv=False):
    """ [cmds] 頂点リストをカーブの形状に合わせる

    Args:
        vertices (list[str]): 編集対象頂点
        curve (str): フィッティングに使われるカーブのトランスフォームノード名
        keep_ratio (bool, optional): True で元の頂点間の比率を維持し､ False で均一化する｡ Defaults to True.
        multiplier (float): keep_ratio=False 時に使用される｡ n番目の長さと n+1番目の長さの比率｡ 1.0 で均等
        auto_reverse (bool, optional): 頂点の並び順とカーブの方向が不一致の場合に自動で調整する
        surface_constraint (bool, optional): True でサーフェスに拘束して移動する
        preserve_uv (bool, optional): True で UV を保持して移動する
    """
    current_selections = cmds.ls(selection=True, flatten=True)

    params = []
    xformConstraint = "surface" if surface_constraint else "none"

    # 最初の頂点がカーブの始点より終点に近ければカーブ方向が逆と判断してカーブを反転させる
    if auto_reverse:
        match_direction(curve, vertices)

    if keep_ratio:
        length_list = [0] + core.length_each_vertices(vertices)
        total_path = sum(length_list)
        params = [sum(length_list[0:i+1]) / total_path for i in range(len(vertices))]

    else:
        interval = [pow(multiplier, i) for i in range(len(vertices)-1)]
        interval.insert(0, 0)
        params = [sum(interval[0:i+1]) for i in range(len(vertices))]
        params = [x/params[-1] for x in params]

    new_positions = get_points_at_params(curve, params, space=space)

    # 実際のコンポーネント移動
    for i in range(len(vertices)):
        p = new_positions[i]
        cmds.move(p.x, p.y, p.z, vertices[i], ws=True, absolute=True, xformConstraint=xformConstraint, preserveUV=preserve_uv)

    if current_selections:
        cmds.select(current_selections, replace=True)


def fit_vertices_to_curve_lerp(vertices, curve1, curve2, alpha, keep_ratio=True, multiplier=1.0, auto_reverse=True, space="world", surface_constraint=False, preserve_uv=False):
    """ [cmds] 頂点リストを複数のカーブを合成した形状に合わせる

    Args:
        vertices (list[str]): 編集対象頂点
        curve1 (str): フィッティングに使われるカーブのトランスフォームノード名
        curve2 (str): フィッティングに使われるカーブのトランスフォームノード名
        alpha (float): カーブの合成比率｡ 0.0 で curve1 に一致し､ 1.0 で curve2 に一致する線形補間
        keep_ratio (bool, optional): True で元の頂点間の比率を維持し､ False で均一化する｡ Defaults to True.
        multiplier (float): keep_ratio=False 時に使用される｡ n番目の長さと n+1番目の長さの比率｡ 1.0 で均等
        auto_reverse (bool, optional): 頂点の並び順とカーブの方向が不一致の場合に自動で調整する
        surface_constraint (bool, optional): True でサーフェスに拘束して移動する
        preserve_uv (bool, optional): True で UV を保持して移動する
    """
    current_selections = cmds.ls(selection=True, flatten=True)

    params = []
    xformConstraint = "surface" if surface_constraint else "none"

    # 最初の頂点がカーブの始点より終点に近ければカーブ方向が逆と判断してカーブを反転させる
    if auto_reverse:
        match_direction(curve1, vertices)
        match_direction(curve2, vertices)

    if keep_ratio:
        length_list = [0] + core.length_each_vertices(vertices)
        total_path = sum(length_list)
        params = [sum(length_list[0:i+1]) / total_path for i in range(len(vertices))]

    else:
        interval = [pow(multiplier, i) for i in range(len(vertices)-1)]
        interval.insert(0, 0)
        params = [sum(interval[0:i+1]) for i in range(len(vertices))]
        params = [x/params[-1] for x in params]

    new_positions1 = get_points_at_params(curve1, params, space=space)
    new_positions2 = get_points_at_params(curve2, params, space=space)

    # 実際のコンポーネント移動
    for i in range(len(vertices)):
        p1 = om.MVector(new_positions1[i].x, new_positions1[i].y, new_positions1[i].z)
        p2 = om.MVector(new_positions2[i].x, new_positions2[i].y, new_positions2[i].z)
        p = p1 * (1.0 - alpha) + p2 * alpha
        cmds.move(p.x, p.y, p.z, vertices[i], ws=True, absolute=True, xformConstraint=xformConstraint, preserveUV=preserve_uv)

    if current_selections:
        cmds.select(current_selections, replace=True)


def match_direction(curve, vertices, space="world"):
    """ [cmds] 頂点の並び順とカーブの方向が不一致の場合に自動で調整する｡ curve は書き換えられる

    TODO: カーブを反転するのか頂点を反転するのかはオプションで選ばせる｡
    TODO: 引数を書き換えず戻り値使って

    Args:
        curve (str): カーブのトランスフォームノード名
        vertices (list[str]):
        space (str, optional)

    Returns:
        bool: カーブを反転した場合 True
    """
    om_space = om.MSpace.kWorld if space == "world" else om.MSpace.kObject

    shape = cmds.listRelatives(curve, shapes=True)[0]
    sel = om.MGlobal.getSelectionListByName(shape)
    fn_curve = om.MFnNurbsCurve(sel.getDagPath(0))

    curve_first_point = fn_curve.getPointAtParam(0, om_space)
    curve_last_point = fn_curve.getPointAtParam(1, om_space)

    vtx_pos = cmds.xform(vertices[0], q=True, t=True, ws=(space == "world"))
    first_vertex_point = om.MVector(*vtx_pos)

    p_first = om.MVector(curve_first_point.x, curve_first_point.y, curve_first_point.z)
    p_last = om.MVector(curve_last_point.x, curve_last_point.y, curve_last_point.z)

    if (p_last - first_vertex_point).length() < (p_first - first_vertex_point).length():
        cmds.reverseCurve(curve, ch=False, rpo=True)
        return True
    else:
        return False
