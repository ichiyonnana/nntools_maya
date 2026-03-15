"""
ジオデシック距離で頂点を選択する
"""
import igl
import numpy as np
import maya.cmds as cmds
import maya.api.OpenMaya as om

from datetime import datetime


def triangulate(faces):
    """フェースを三角形に分割する

    Args:
        faces (list[list[int]]): ポリゴン毎の頂点インデックスリストのリスト

    Returns:
        list[list[int]]: 引数を三角形に分割したもの
    """
    tris = []
    for face in faces:
        for i in range(len(face)-2):
            tris.append([face[0], face[i+1], face[i+2]])

    return tris


# Maya からメッシュデータを取得
def get_mesh_data_from_selection():
    # 選択オブジェクトの名前を取得
    selection_list = om.MGlobal.getActiveSelectionList()
    dag_path = selection_list.getDagPath(0)
    mfn_mesh = om.MFnMesh(dag_path)

    # 頂点座標を取得
    points = mfn_mesh.getPoints(om.MSpace.kWorld)
    vertices = np.array([[p.x, p.y, p.z] for p in points])

    # ポリゴンのインデックスリストを取得
    vertex_indices = []
    for i in range(mfn_mesh.numPolygons):
        vertex_indices.append(mfn_mesh.getPolygonVertices(i))

    # 四角形メッシュを三角形メッシュに変換
    faces = np.array(triangulate(vertex_indices))

    return vertices, faces


# libigl を使ってジオデシック距離を計算し、指定距離以内の頂点を取得
def get_nearby_vertices(vertices, faces, source_vertex_idx, max_distance):
    # メッシュを初期化 (V: 頂点, F: 面)
    V = np.array(vertices)
    F = np.array(faces)

    # ジオデシック距離を計算 (ソース頂点を指定)
    vs = np.array([source_vertex_idx], dtype=np.int32)  # ソース頂点インデックス
    vt = np.arange(len(V))  # 全ての頂点に対して距離を計算

    distances = igl.exact_geodesic(V, F, vs, vt)  # 戻り値は1つの配列

    # 指定距離以内の頂点を選別
    nearby_vertices = np.where(distances <= max_distance)[0]

    return nearby_vertices


# Maya で指定の頂点を選択する
def select_vertices_in_maya(dag_path, vertex_indices):
    cmds.select(clear=True)
    for idx in vertex_indices:
        cmds.select(f"{dag_path.fullPathName()}.vtx[{idx}]", add=True)


# メイン処理
def main():
    max_distance = 5  # 10 cm (Maya の単位に依存)

    # Maya からメッシュデータを取得
    vertices, faces = get_mesh_data_from_selection()

    print(datetime.now())
    # 頂点インデックス 0 から 10cm 以内の頂点を取得
    nearby_vertices = get_nearby_vertices(vertices, faces, 0, max_distance)
    print(datetime.now())

    # Maya で近くの頂点を選択
    selection_list = om.MGlobal.getActiveSelectionList()
    dag_path = selection_list.getDagPath(0)
    select_vertices_in_maya(dag_path, nearby_vertices)


# 実行
main()
