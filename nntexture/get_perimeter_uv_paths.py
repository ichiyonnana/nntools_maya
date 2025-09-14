"""指定フェイスからオブジェクト･シェルを考慮したUVボーダーを求める関数"""
import re
import maya.api.OpenMaya as om
import maya.cmds as cmds


class UVEdge:
    """UVエッジを表すクラス

    Args:
        uvid1 (int): UVインデックス1
        uvid2 (int): UVインデックス2
    """
    def __init__(self, uvid1, uvid2):
        self.uvid1 = min(uvid1, uvid2)
        self.uvid2 = max(uvid1, uvid2)

    def __hash__(self):
        return hash((self.uvid1, self.uvid2))

    def __eq__(self, other):
        return (self.uvid1, self.uvid2) == (other.uvid1, other.uvid2)

    def __str__(self):
        return f"({self.uvid1}-{self.uvid2})"

    def __repr__(self):
        return f"UVEdge({self.uvid1}, {self.uvid2})"


def get_face_uvs_dict(mesh, face_ids):
    """各フェースごとのUVインデックスリストを取得

    Args:
        mesh (str): メッシュ名
        face_ids (list[int]): フェースIDリスト
    Returns:
        fn_mesh (MFnMesh): メッシュ関数セット
        face_uvs (dict): {face_id: [uv_index, ...]}
    """
    sel_list = om.MSelectionList()
    sel_list.add(mesh)
    dag = sel_list.getDagPath(0)
    fn_mesh = om.MFnMesh(dag)
    fid_to_uvids = dict()
    for fid in face_ids:
        verts = fn_mesh.getPolygonVertices(fid)
        uvs = [fn_mesh.getPolygonUVid(fid, i) for i in range(len(verts))]
        fid_to_uvids[fid] = uvs
    return fn_mesh, fid_to_uvids


def group_uvs_by_shell(fn_mesh, face_uvs):
    """UVシェルIDごとにUVインデックスをグループ化

    Args:
        fn_mesh (MFnMesh): メッシュ関数セット
        face_uvs (dict): {face_id: [uv_index, ...]}
    Returns:
        shell_uvs (dict): {shell_id: set(uv_index)}
    """
    uv_shell_ids = fn_mesh.getUvShellsIds()[1]
    shellid_to_uvids = dict()
    for uvs in face_uvs.values():
        for uvi in uvs:
            shell_id = uv_shell_ids[uvi]
            shellid_to_uvids.setdefault(shell_id, set()).add(uvi)
    return shellid_to_uvids


def get_shell_uv_border(fn_mesh, shellid_to_uvs, fid_to_uvs, target_face_ids):
    """
    指定したフェースがもつ UV 空間でのボーダーを取得する関数。
    選択境界かテクスチャボーダーのどちらかとなるUVエッジを全て返す。

    Args:
        fn_mesh (MFnMesh): 対象メッシュの MFnMesh インスタンス
        shellid_to_uvs (dict[int, set[int]]): シェルID: UVIDのセットとなる辞書
        fid_to_uvs (dict[int, list[int]]): フェイスID: UVIDのセットとなる辞書
        target_face_ids (set[int]): ボーダーを調べるフェースIDのセット
    Returns:
        uv_border (dict[int, set[int]]): {shell_id: set(uv_index)}
        uv_border_edges (dict[int, set[UVEdge]]): {shell_id: set(UVEdge)}
    """
    # 対象フェースをエッジに変換 (ボーダー以外も含む全構成エッジ)
    face_components = [f".f[{fid}]" for fid in target_face_ids]
    mesh_name = fn_mesh.name()
    face_strs = [f"{mesh_name}{fc}" for fc in face_components]
    edge_components = cmds.polyListComponentConversion(face_strs, toEdge=True)
    edge_components = cmds.ls(edge_components, flatten=True) if edge_components else []

    # ボーダーエッジのみ取得
    border_edge_components = cmds.polyListComponentConversion(face_strs, toEdge=True, border=True)
    border_edge_components = cmds.ls(border_edge_components, flatten=True) if border_edge_components else []
    border_edge_ids = set()
    for ec in border_edge_components:
        m = re.search(r"\.e\[(\d+)\]", ec)
        if m:
            border_edge_ids.add(int(m.group(1)))

    # テクスチャボーダーエッジのみ取得
    tex_border_edge_ids = set()
    for ec in edge_components:
        m = re.search(r"\.e\[(\d+)\]", ec)
        if not m:
            continue
        eid = int(m.group(1))
        # エッジのUV情報を取得
        tuv = cmds.polyListComponentConversion(f"{mesh_name}.e[{eid}]", fromEdge=True, toUV=True)
        tuv = cmds.ls(tuv, flatten=True) if tuv else []
        if len(tuv) == 4:
            tex_border_edge_ids.add(eid)

    # UV空間でのボーダーエッジのIDセット
    all_border_edge_ids = border_edge_ids | tex_border_edge_ids

    # UVに分解しシェルごとに整理
    shellid_to_border_uvids = dict()
    shellid_to_uvedges = dict()
    uv_shell_ids = fn_mesh.getUvShellsIds()[1]

    for shell_id in shellid_to_uvs:
        shellid_to_border_uvids[shell_id] = set()
        shellid_to_uvedges[shell_id] = set()

    # UVエッジに再構成しシェル毎にまとめる
    for eid in all_border_edge_ids:
        # エッジに接続するフェースを取得
        edge_iter = om.MItMeshEdge(fn_mesh.object())
        edge_iter.setIndex(eid)
        connected_faces = edge_iter.getConnectedFaces()
        # 各フェースでのUVインデックスを取得
        for fid in connected_faces:
            if fid not in fid_to_uvs:
                continue
            uvlist = fid_to_uvs[fid]
            verts = fn_mesh.getPolygonVertices(fid)
            num_verts = len(verts)
            for i in range(num_verts):
                v1 = verts[i]
                v2 = verts[(i+1) % num_verts]
                if set([v1, v2]) == set([edge_iter.vertexId(0), edge_iter.vertexId(1)]):
                    uvi1 = uvlist[i]
                    uvi2 = uvlist[(i+1) % num_verts]
                    shell_id1 = uv_shell_ids[uvi1]
                    shell_id2 = uv_shell_ids[uvi2]
                    if shell_id1 == shell_id2:
                        shellid_to_border_uvids[shell_id1].add(uvi1)
                        shellid_to_border_uvids[shell_id1].add(uvi2)
                        shellid_to_uvedges[shell_id1].add(UVEdge(uvi1, uvi2))

    return shellid_to_border_uvids, shellid_to_uvedges


def get_all_sorted_uv_paths(uvedges):
    """ボーダーUVエッジ集合から、同一シェル内の全ての閉じた経路（ループや開区間）を抽出して返す。

    Args:
        uvedges (set[UVEdge]): ボーダーUVエッジ集合（UVEdgeインスタンスのセット）
    Returns:
        list[list[int]]: 各経路ごとのUVインデックスリスト（[[uv1, uv2, ...], ...]）
    """
    from collections import defaultdict

    edge_map = defaultdict(list)
    for uvedge in uvedges:
        a, b = uvedge.uvid1, uvedge.uvid2
        edge_map[a].append(b)
        edge_map[b].append(a)
    paths = []
    visited = set()
    nodes = set(edge_map.keys())
    while nodes:
        # 経路端点（次数1）を優先、なければ残りから
        endpoints = [n for n in nodes if len(edge_map[n]) == 1]
        if endpoints:
            start = endpoints[0]
        else:
            start = next(iter(nodes))
        path = [start]
        visited.add(start)
        cur = start
        while True:
            nexts = [n for n in edge_map[cur] if n not in visited]
            if not nexts:
                break
            cur = nexts[0]
            path.append(cur)
            visited.add(cur)
        paths.append(path)
        nodes -= set(path)
    return paths


def get_perimeter_uv_paths(target_faces):
    """
    メイン処理: 選択フェースからUVシェルごとにボーダーUV経路を出力
    Args:
        target_faces (list[str]): 対象フェース名リスト（省略時は選択）
    Returns:
        dict[str, list[list[int]]]:
            {mesh名: [ [uv_index, uv_index, ...], ... ]} 各メッシュごとに、各シェル内の全ての境界UV経路リスト
    """
    if not target_faces:
        target_faces = cmds.ls(selection=True, flatten=True)

    target_faces = cmds.filterExpand(target_faces, sm=34) if target_faces else []

    if not target_faces:
        return

    # オブジェクト名をキーにして辞書に格納
    obj_to_faces = {}
    for f in target_faces:
        obj = f.split('.')[0]
        obj_to_faces.setdefault(obj, []).append(f)

    mesh_to_paths = dict()

    # オブジェクト毎に処理
    for mesh, faces in obj_to_faces.items():
        # UV情報を取得
        face_ids = [int(re.findall(r"\[(\d+)\]", f)[0]) for f in faces]
        fn_mesh, fid_to_uvids = get_face_uvs_dict(mesh, face_ids)
        shellid_to_uvids = group_uvs_by_shell(fn_mesh, fid_to_uvids)

        shellid_to_border_uvids, shellid_to_uvedges = get_shell_uv_border(fn_mesh, shellid_to_uvids, fid_to_uvids, set(face_ids))

        ret = []
        for shell_id, uvedges in shellid_to_uvedges.items():
            paths = get_all_sorted_uv_paths(uvedges)
            ret.extend(paths)

        mesh_to_paths[mesh] = ret

    return mesh_to_paths
