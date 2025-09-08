"""指定フェイスからオブジェクト･シェルを考慮したUVボーダーを求める関数"""
import re
import maya.api.OpenMaya as om
import maya.cmds as cmds


def get_face_uvs(mesh, face_ids):
    """
    各フェースごとのUVインデックスリストを取得
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
    """
    UVシェルIDごとにUVインデックスをグループ化
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


def get_shell_uv_border(fn_mesh, shell_uvs, face_uvs, selected_face_ids):
    """
    各UVシェルごとにボーダーUV集合とボーダーUVエッジ集合を抽出
    Args:
        fn_mesh (MFnMesh): メッシュ関数セット
        shell_uvs (dict): {shell_id: set(uv_index)}
        face_uvs (dict): {face_id: [uv_index, ...]}
        selected_face_ids (set[int]): 選択フェースID集合
    Returns:
        uv_border (dict): {shell_id: set(uv_index)}
        uv_border_edges (dict): {shell_id: set((uv1, uv2))}
    """
    # UVごとに隣接フェースを調べ、テクスチャボーダーまたは非選択フェースが隣接なら境界
    shellid_to_border_uvids = dict()
    shellid_to_uvid_pairs = dict()
    for shell_id, uvs in shell_uvs.items():
        border_uvs = set()
        border_edges = set()
        # このシェルに属するフェースのみ抽出
        shell_face_items = [(fid, uvlist) for fid, uvlist in face_uvs.items() if set(uvlist) & uvs]
        for fid, uvlist in shell_face_items:
            verts = fn_mesh.getPolygonVertices(fid)
            num_verts = len(verts)
            for i in range(num_verts):
                uvi1 = uvlist[i]
                uvi2 = uvlist[(i+1) % num_verts]
                # 隣接フェース取得
                v1 = verts[i]
                v2 = verts[(i+1) % num_verts]
                edge_iter = om.MItMeshEdge(fn_mesh.object())
                edge_id = None
                while not edge_iter.isDone():
                    if set([edge_iter.vertexId(0), edge_iter.vertexId(1)]) == set([v1, v2]):
                        edge_id = edge_iter.index()
                        break
                    edge_iter.next()
                adj_faces = []
                if edge_id is not None:
                    edge_iter.setIndex(edge_id)
                    adj_faces = list(edge_iter.getConnectedFaces())
                # テクスチャボーダー or 非選択フェース隣接
                is_tex_border = len(adj_faces) == 1
                is_non_selected = any(f not in selected_face_ids for f in adj_faces)
                if is_tex_border or is_non_selected:
                    border_uvs.add(uvi1)
                    border_uvs.add(uvi2)
                    border_edges.add((uvi1, uvi2))
        shellid_to_border_uvids[shell_id] = border_uvs
        shellid_to_uvid_pairs[shell_id] = border_edges
    return shellid_to_border_uvids, shellid_to_uvid_pairs


def get_all_sorted_uv_paths(uvid_pairs):
    """
    ボーダーUVエッジ集合から、同一シェル内の全ての閉じた経路（ループや開区間）を抽出して返す。
    Args:
        uvid_pairs (set[tuple[int, int]]): ボーダーUVエッジ集合（(uv1, uv2) のペアのセット）
    Returns:
        list[list[int]]: 各経路ごとのUVインデックスリスト（[[uv1, uv2, ...], ...]）
    """
    from collections import defaultdict

    edge_map = defaultdict(list)
    for a, b in uvid_pairs:
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

    faces = [x for x in target_faces if '.f[' in x]

    if not faces:
        return

    # オブジェクト名をキーにして辞書に格納
    face_dict = {}
    for f in faces:
        obj = f.split('.')[0]
        face_dict.setdefault(obj, []).append(f)

    mesh_to_paths = dict()

    # オブジェクト毎に処理
    for mesh, faces in face_dict.items():
        face_ids = [int(re.findall(r"\[(\d+)\]", f)[0]) for f in faces]
        fn_mesh, fid_to_uvids = get_face_uvs(mesh, face_ids)
        shellid_to_uvids = group_uvs_by_shell(fn_mesh, fid_to_uvids)

        shellid_to_border_uvids, shellid_to_uvid_pairs = get_shell_uv_border(fn_mesh, shellid_to_uvids, fid_to_uvids, set(face_ids))

        ret = []
        for shell_id in shellid_to_border_uvids:
            paths = get_all_sorted_uv_paths(shellid_to_uvid_pairs[shell_id])
            ret.extend(paths)

        mesh_to_paths[mesh] = ret

    return mesh_to_paths
