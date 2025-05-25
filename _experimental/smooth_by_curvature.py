"""
選択オブジェクトの全ての頂点の主曲率を出力する

TODO: curvature_smooth で interior_division オプション
TODO: 独立したリラックス機能
"""
import math

import igl
import scipy.sparse
import scipy.sparse.linalg
import numpy as np
from numpy.typing import NDArray

import maya.cmds as cmds
import maya.api.OpenMaya as om


def get_boundary_vertex_ids(vertex_ids_per_face):
    """フェース情報から境界頂点の頂点IDを返す

    Args:
        vertex_ids_per_face (ndarray): フェースの頂点インデックスリスト

    Returns:
        ndarray: 境界頂点の頂点IDリスト
    """
    boundary_edges = igl.boundary_facets(vertex_ids_per_face)
    boundary_vertices = np.unique(boundary_edges)

    return boundary_vertices


def triangulate(vertex_ids_per_face):
    """フェースを三角形に分割する

    Args:
        vertex_ids_per_face (list[list[int]]): ポリゴン毎の頂点インデックスリストのリスト

    Returns:
        list[list[int]]: 引数を三角形に分割したもの
    """
    tris = []
    for ids in vertex_ids_per_face:
        for i in range(len(ids)-2):
            tris.append([ids[0], ids[i+1], ids[i+2]])

    return tris


def get_selected_mesh():
    """選択されているメッシュを取得し mesh ノードのノード名を返す

    Raises:
        RuntimeError: mesh もしくは mesh ノードを持つ transform が選択されていなかった場合

    Returns:
        str: mesh ノードのノード名
    """
    selection = cmds.ls(selection=True)
    shapes = cmds.polyListComponentConversion(selection[0])
    if not shapes:
        raise RuntimeError("No mesh selected.")
    return shapes[0]


def get_mesh_data(mesh):
    """メッシュデータを取得する｡

    Returns:
        tuple[np.ndarray, np.ndarray]: _description_
    """
    # 選択オブジェクトの取得
    slist = om.MGlobal.getSelectionListByName(mesh)
    dag_path = slist.getDagPath(0)
    fn_mesh = om.MFnMesh(dag_path)

    # 頂点座標を取得し､ ndarray に格納
    points = fn_mesh.getPoints(om.MSpace.kWorld)
    vertex_coords = np.array([[p.x, p.y, p.z] for p in points])

    # ポリゴンのインデックスリストを取得
    vertex_ids_per_face = []
    for i in range(fn_mesh.numPolygons):
        vertex_ids_per_face.append(fn_mesh.getPolygonVertices(i))

    # ポリゴンのインデックスリストを三角形化して ndarray に格納
    vertex_ids_per_tri = np.array(triangulate(vertex_ids_per_face))

    return vertex_coords, vertex_ids_per_tri


def adjacency_list_2_hop(faces):
    # 隣接リストを取得
    adj_list = igl.adjacency_list(faces)

    # 2ホップ以内の隣接リストを生成
    adj_list_2_hop = []
    for i, neighbors in enumerate(adj_list):
        two_hop_neighbors = set(neighbors)
        for neighbor in neighbors:
            two_hop_neighbors.update(adj_list[neighbor])
        two_hop_neighbors.discard(i)  # 自分自身を除外
        adj_list_2_hop.append(list(two_hop_neighbors))

    return adj_list_2_hop


def curvature_smooth(mesh, iterations=1, mod_factor=0.2, interior_division=True, exclusive_ids=None, laplacian_lambda=0):
    """曲率に基づいてメッシュをスムージングする

    Args:
        mesh (str): 対象メッシュのノード名
        iterations (int, optional): 反復数. Defaults to 1.
        mod_factor (float, optional): スムーズ強度. Defaults to 0.2.
        exclusive_ids (list[int], optional): スムースしない頂点IDのリスト. Defaults to None.
    """

    exclusive_ids = exclusive_ids or []

    threshold_k = 0.0001
    max_k_ratio = 1
    min_k_ratio = 0.01

    vertex_coords, vertex_ids_per_face = get_mesh_data(mesh)
    vertex_normals = igl.per_vertex_normals(vertex_coords, vertex_ids_per_face)

    # 境界頂点の頂点ID
    boundary_vertex_ids = get_boundary_vertex_ids(vertex_ids_per_face)

    current_coords = np.copy(vertex_coords)
    new_coords = np.copy(vertex_coords)

    neighbor_vis_per_vertex = igl.adjacency_list(vertex_ids_per_face)

    vertex_ids_each_edge = igl.edges(vertex_ids_per_face)
    vertex_size = len(vertex_coords)
    edge_length_matrix = np.full((vertex_size, vertex_size), -1.0, dtype=float)

    row_indices = vertex_ids_each_edge[:, 0]
    col_indices = vertex_ids_each_edge[:, 1]
    edge_ids = np.arange(vertex_ids_each_edge.shape[0])

    for _ in range(iterations):
        # 主曲率を計算
        c1, c2, k1, k2 = igl.principal_curvature(current_coords, vertex_ids_per_face)

        start_coords = vertex_coords[vertex_ids_each_edge[:, 0]]
        end_coords = vertex_coords[vertex_ids_each_edge[:, 1]]
        differences = end_coords - start_coords
        edge_length_each_eid = np.linalg.norm(differences, axis=1)

        for vi in range(len(vertex_coords)):
            # 境界はスキップ
            if vi in boundary_vertex_ids:
                continue

            # 現在の頂点座標
            current_coord = current_coords[vi]

            neighbor_vis = neighbor_vis_per_vertex[vi]

            # 隣接頂点の平均点計算
            # interior_division が True の場合はエッジ長で重み付け
            if interior_division:
                # 頂点IDからエッジ長を得るndarray
                edge_length_matrix[row_indices, col_indices] = np.linalg.norm((vertex_coords[row_indices] - vertex_coords[col_indices]), axis=1)
                edge_length_matrix[col_indices, row_indices] = edge_length_matrix[row_indices, col_indices]

                # 内分点を求める
                # 隣接頂点のエッジ長抽出
                edge_lengths = edge_length_matrix[vi, neighbor_vis]

                # 隣接頂点の頂点座標抽出
                neighbor_coords = current_coords[neighbor_vis]

                # 各座標にエッジ長で重み付けして合計､エッジ長の和で割る
                inner_products = np.sum(neighbor_coords * edge_lengths[:, np.newaxis], axis=0)
                avg_coord = inner_products / np.sum(edge_lengths)
            else:
                avg_coord = np.mean(current_coords[neighbor_vis], axis=0)

            diff_vector = avg_coord - current_coord

            if math.isclose(np.linalg.norm(diff_vector), 0.0):
                continue

            avg_neighbor_k1 = np.mean(k1[neighbor_vis], axis=0)
            avg_neighbor_k2 = np.mean(k2[neighbor_vis], axis=0)
            avg_neighbor_k = (avg_neighbor_k1 + avg_neighbor_k2) / 2
            current_avg_k = (k1[vi] + k2[vi]) / 2
            diff_k = avg_neighbor_k - current_avg_k

            k_ratio = max(min(abs(diff_k / current_avg_k), max_k_ratio), min_k_ratio)

            ideal_coord = avg_coord + diff_vector * np.sign(avg_neighbor_k) * diff_k
            tweak_vector = ideal_coord - current_coord

            if abs(diff_k) < threshold_k:
                continue

            else:
                new_coords[vi] = current_coord + tweak_vector * mod_factor * k_ratio

            if vi == -1:
                print("current_coord: ", current_coord)
                print("diff_vector: ", diff_vector)
                print("new_coord: ", new_coords[vi])
                print("current_avg_k: ", round(current_avg_k, 5))
                print("avg_neighbor_k: ", round(avg_neighbor_k, 5))
                print("diff_k: ", round(diff_k, 5))
                print("k ratio: ", round(diff_k / current_avg_k, 5))
                print("tweak_vector: ", tweak_vector)
                print("tweak amount: ", tweak_vector * mod_factor * k_ratio)

        if laplacian_lambda != 0:
            new_coords = laplacian_smoothing(new_coords, vertex_ids_per_face, iterations=1, lambda_=laplacian_lambda, exclusive_ids=boundary_vertex_ids, projection=True)

        current_coords = np.copy(new_coords)

    # 作成した頂点座標を適用
    for vi in range(len(new_coords)):
        if vi in exclusive_ids:
            continue

        new_coord = new_coords[vi]
        cmds.xform("{}.vtx[{}]".format(cmds.ls(selection=True)[0], vi), t=new_coord, worldSpace=True)


def laplacian_smoothing(vertex_coords, vertex_ids_per_face, iterations, lambda_, projection, exclusive_ids=None):
    """ラプラシアンスムーズを適用して新しい頂点座標を返す

    Args:
        vertex_coords (ndarray): _description_
        vertex_ids_per_face (ndarray): _description_
        iterations (int, optional): スムース反復数. Defaults to 10.
        lambda_ (float, optional): スムース強度. Defaults to 0.5.
        exclusive_ids (ndarray, optional): スムースしない頂点のIDリスト. Defaults to 0.
        projection (bool, optional): True で直接スムーズせずスムーズしたメッシュへのプロジェクションを行う. Defaults to False.

    Returns:
        ndarray: スムーズ後の頂点座標
    """
    if exclusive_ids is None:
        exclusive_ids = np.array([])

    L = igl.cotmatrix(vertex_coords, vertex_ids_per_face)
    M = igl.massmatrix(vertex_coords, vertex_ids_per_face, igl.MASSMATRIX_TYPE_VORONOI)
    S = M - lambda_ * L

    for _ in range(iterations):
        smooth_vertex_coords = scipy.sparse.linalg.spsolve(S, M @ vertex_coords)

    for vi in exclusive_ids:
        smooth_vertex_coords[vi] = vertex_coords[vi]

    if projection:
        new_vertex_coords = project_vertices_to_other_surface(vertex_coords, smooth_vertex_coords, vertex_ids_per_face)

    else:
        new_vertex_coords = smooth_vertex_coords

    return new_vertex_coords


def project_vertices_to_other_surface(src_vertices, dst_vertices, dst_faces):
    _, _, closest_points = igl.point_mesh_squared_distance(src_vertices, dst_vertices, dst_faces)
    return closest_points


def main():
    """メイン処理"""
    mesh = get_selected_mesh()

    if not mesh:
        return

    iteration = 10
    laplacian_lambda = 0

    curvature_smooth(mesh, iterations=iteration, interior_division=False, mod_factor=0.2, exclusive_ids=None, laplacian_lambda=laplacian_lambda)

    print("complete")


if __name__ == "__main__":
    main()
