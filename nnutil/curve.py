# coding:utf-8
"""
カーブ関連
pymel ベース
"""

import os
import re
import sys
import traceback
import importlib

import maya.cmds as cmds
import maya.mel as mel
import pymel.core as pm
import pymel.core.datatypes as dt
import pymel.core.nodetypes as nt

from . import core


def make_curve_from_edges(edges, n=4):
    """ [pm] エッジからカーブを生成する

    エッジ列からカーブを生成して､カーブを返す
    エッジ列がひとつながりでない場合はどれか一つだけがカーブ生成される (polyToCurve の振る舞いに従う) 
    複数カーブが必要な場合､エッジ列の適切な分割は関数の外で行い複数回呼ぶ

    Args:
        edges (list[MeshEdge]): カーブの生成に使うエッジ列｡ すべてのエッジが連続していればリストの要素自体は順不同
        n (int, optional): 生成されるカーブのスパン数｡ 0 で スパン数 1 ､それ以外は n+2 ｡ デフォルト 4

    Returns:
        Transform: 生成されたカーブ｡ カーブオブジェクトのトランスフォームノード
    """
    n = int(n)

    current_selections = pm.selected(flatten=True)

    # カーブ生成とリビルド
    pm.select(edges, replace=True)
    curve = cmds.polyToCurve(form=2, degree=3, conformToSmoothMeshPreview=1)[0]

    # n が 0 の時は 直線にする
    if n <= 0:
        cmds.rebuildCurve(curve, ch=1, rpo=1, rt=0, end=1, kr=2, kcp=0, kep=1, kt=0, s=1, d=1, tol=0.01)
    else:
        cmds.rebuildCurve(curve, ch=1, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s=n, d=3, tol=0.01)

    cmds.delete(curve, ch=True)
    pm.select(current_selections, replace=True)

    return core.pynode(curve)


def get_points_at_params(curve, params, space="world"):
    """ [pm] getPointAtParam の複数パラメーター版

    Args:
        curve (NurbsCurve): カーブオブジェクト
        params (list[float]): getPointAtParam に使用する param の配列

    Returns:

    """
    current_selections = pm.selected(flatten=True)

    # 内部リビルド
    # 直線時に開始位置がずれるバグ対策も兼ね
    target_curve = pm.duplicate(curve)[0]
    n = len(curve.getCVs())
    k = 8
    pm.rebuildCurve(target_curve, ch=1, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s=n*k, d=3, tol=0.01)
    pm.delete(target_curve, ch=True)

    points = [target_curve.getPointAtParam(param=param, space=space) for param in params]

    pm.delete(target_curve)
    pm.select(current_selections, replace=True)

    return points


def fit_vertices_to_curve(vertices, curve, keep_ratio=True, multiplier=1.0,  auto_reverse=True, space="world"):
    """ [pm] 頂点リストをカーブの形状に合わせる

    Args:
        vertices (list[MeshVertex]): 編集対象頂点
        curve (NurbsCurve): フィッティングに使われるカーブ
        keep_ratio (bool, optional): True で元の頂点間の比率を維持し､ False で均一化する｡ Defaults to True.
        multiplier (float): keep_ratio=False 時に使用される｡ n番目の長さと n+1番目の長さの比率｡ 1.0 で均等
        auto_reverse (bool, optional): 頂点の並び順とカーブの方向が不一致の場合に自動で調整する
    """
    current_selections = pm.selected(flatten=True)

    params = []

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
        vertices[i].setPosition(new_positions[i], space=space)
        
    pm.select(current_selections, replace=True)


def fit_vertices_to_curve_lerp(vertices, curve1, curve2, alpha, keep_ratio=True, multiplier=1.0, auto_reverse=True, space="world"):
    """ [pm] 頂点リストを複数のカーブを合成した形状に合わせる

    Args:
        vertices (list[MeshVertex]): 編集対象頂点
        curve1 (NurbsCurve): フィッティングに使われるカーブ
        curve2 (NurbsCurve): フィッティングに使われるカーブ
        alpha (float): カーブの合成比率｡ 0.0 で curve1 に一致し､ 1.0 で curve2 に一致する線形補間
        keep_ratio (bool, optional): True で元の頂点間の比率を維持し､ False で均一化する｡ Defaults to True.
        multiplier (float): keep_ratio=False 時に使用される｡ n番目の長さと n+1番目の長さの比率｡ 1.0 で均等
        auto_reverse (bool, optional): 頂点の並び順とカーブの方向が不一致の場合に自動で調整する
    """
    current_selections = pm.selected(flatten=True)

    params = []

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
        new_position = new_positions1[i] * (1.0-alpha) + new_positions2[i] * alpha
        vertices[i].setPosition(new_position, space=space)
        
    pm.select(current_selections, replace=True)


def match_direction(curve, vertices, space="world"):
    """ [pm] 頂点の並び順とカーブの方向が不一致の場合に自動で調整する｡ curve は書き換えられる

    TODO: カーブを反転するのか頂点を反転するのかはオプションで選ばせる｡
    TODO: 引数を書き換えず戻り値使って

    Args:
        curve (NurbsCurve):
        vertices (list[MeshVertex]):
        space (str, optional)

    Returns:
        [type]: [description]
    """
    curve_first_point = curve.getPointAtParam(param=0, space=space)
    curve_last_point = curve.getPointAtParam(param=1, space=space)
    first_vertex_point = vertices[0].getPosition(space=space)
    
    if (curve_last_point - first_vertex_point).length() < (curve_first_point - first_vertex_point).length():
        curve.reverse()
        return True
    else:
        return False
