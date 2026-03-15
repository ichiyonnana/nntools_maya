import math
import re
import random

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om


def get_uv_borders(objects):
    """指定したオブジェクトやコンポーネントからUVボーダーとなっているエッジを返す

    Args:
        objects (str): オブジェクト名やコンポーネント名を表す文字列

    Returns:
        list[str]: ボーダーエッジを表す文字列のリスト
    """
    if not objects:
        return None
    
    edges = cmds.ls(cmds.polyListComponentConversion(objects, te=True), flatten=True)
    
    if not edges:
        return []
        
    uv_border_edges = []
    for edge in edges:
        edge_uvs = cmds.ls(cmds.polyListComponentConversion(edge, tuv=True), flatten=True)
        edge_faces = cmds.ls(cmds.polyListComponentConversion(edge, tf=True), flatten=True)
        
        if len(edge_uvs) > 2:  # UV ボーダー
            uv_border_edges.append(edge)
            
        elif len(edge_faces) == 1:  # メッシュボーダー
            uv_border_edges.append(edge)
    
    return uv_border_edges


def get_edge_length(edges):
    """指定したエッジのリストから各エッジの長さのリストを返す.

    Args:
        edges (list[str]): エッジを表す文字列のリスト

    Returns:
        list[float]: エッジの長さのリスト
    """
    if not edges:
     return []

    lengths = []

    for edge in edges:
        v1, v2 = cmds.filterExpand(cmds.polyListComponentConversion(edge, tv=True), sm=31)
        p1 = cmds.xform(v1, q=True, translation=True)
        p2 = cmds.xform(v2, q=True, translation=True)
        length = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2 + (p2[2]-p1[2])**2)
        lengths.append(length)

    return lengths       


def sort_uvs_by_connectivity(uvs, first_uv, allowed_edges):
    """ [cmds] 指定した点から順にエッジたどって末尾まで到達する頂点の列を返す

    Args:
        edges(list[str]): エッジを表すcmdsコンポーネント文字列のリスト
        first_vtx (str): 頂点を表すcmdsコンポーネント文字列
        allowed_edges (list[str]): 接続されていると見なすエッジを表す文字列のリスト

    Returns:
        list[str]: 頂点を表すcmdsコンポーネント文字列のリスト

    """
    def get_next_uv(current_uv, uv_list, allowed_edges):
        connected_faces = cmds.filterExpand(cmds.polyListComponentConversion(current_uv, tf=True), sm=34)  # current_uv を含むフェース
        connected_edges = cmds.filterExpand(cmds.polyListComponentConversion(current_uv, te=True), sm=32)  # current_uv を含むエッジ
        connected_edges = set(connected_edges) & set(allowed_edges)  # 許可されたエッジ以外は接続性の確認に使用しない
        connected_face_uvs = set(cmds.filterExpand(cmds.polyListComponentConversion(connected_faces, tuv=True), sm=35)) - set(current_uv)  # 接続フェースに含まれる全UV
        connected_edge_uvs = set(cmds.filterExpand(cmds.polyListComponentConversion(connected_edges, tuv=True), sm=35)) - set(current_uv)  # 接続エッジに含まれる全UV
        neighbor_uvs = connected_face_uvs & connected_edge_uvs & set(uv_list)  # フェースに含まれる全UV のうち uv_list に含まれるもの

        if neighbor_uvs:
            return list(neighbor_uvs)[0]
        
        else:
            return []
        
    sorted_uvs = [first_uv]  # ソート済みUV
    rest_uvs = uvs.copy()  # 未処理UV
    rest_uvs.remove(first_uv)
    current_uv = first_uv

    while rest_uvs:
        next_uv = get_next_uv(current_uv=current_uv, uv_list=rest_uvs, allowed_edges=allowed_edges)
        
        if not next_uv:
            break
        
        sorted_uvs.append(next_uv)
        rest_uvs.remove(next_uv)
        current_uv = next_uv
    
    return sorted_uvs


def length_each_vertices(vtx_comps):
    """ [pm] 頂点間の距離をリストで返す

    戻り値リストの n 番目は vertices[n] と vertices[n+1] の距離

    Args:
        vtx_comps (list[str]):

    Returns:
        list[float]:

    """
    length_list = []

    for i in range(len(vtx_comps)-1):
        coord1 = cmds.xform(vtx_comps[i], q=True, translation=True, ws=True)
        coord2 = cmds.xform(vtx_comps[i+1], q=True, translation=True, ws=True)
        p1 = om.MVector(coord1)
        p2 = om.MVector(coord2)
        length_list.append((p2 - p1).length())

    return length_list


def is_frontfacing_uvshell(face):
    fi = int(re.search(r"\[(\d+)\]", face).group(1))
    vtx = cmds.filterExpand(cmds.polyListComponentConversion(face, tv=True), sm=31)[0]
    vi = int(re.search(r"\[(\d+)\]", vtx).group(1))
        
    obj_name = cmds.polyListComponentConversion(face)[0]
    slist = om.MGlobal.getSelectionListByName(obj_name)
    dagpath = slist.getDagPath(0)
    fn_mesh = om.MFnMesh(dagpath)

    normal = fn_mesh.getFaceVertexNormal(fi, vi)
    tangent = fn_mesh.getFaceVertexTangent(fi, vi)
    binormal = fn_mesh.getFaceVertexBinormal(fi, vi)

    if (tangent ^ binormal) * normal  < 0:
        return False
    
    else:
        return True
    
def get_average_uv(uvs):
    uv_coords =cmds.polyEditUV(uvs, q=True, u=True, v=True)
    avg_u = sum([uv_coords[i] for i in range(0, len(uv_coords), 2)]) / len(uv_coords) * 2
    avg_v = sum([uv_coords[i] for i in range(1, len(uv_coords), 2)]) / len(uv_coords) * 2

    return (avg_u, avg_v)


def rectilinearize_uvshell(corner_uv_comps, target_texel=15, map_size=1024):
    if not corner_uv_comps:
        return None
    
    if len(corner_uv_comps) != 4:
        return None
    
    # 選択の保持
    current_selections = cmds.ls(selection=True, flatten=True)

    # シェル UV とそのボーダーエッジ
    shell_uvs = cmds.filterExpand(cmds.polyListComponentConversion(corner_uv_comps[0], tuv=True, uvShell=True),  sm=35)
    border_edges = get_uv_borders(shell_uvs)
    border_uvs = cmds.filterExpand(cmds.polyListComponentConversion(border_edges, tuv=True), sm=35)

    # トポロジーの接続順にソートしたUV
    sorted_uvs = sort_uvs_by_connectivity(border_uvs, corner_uv_comps[0], border_edges)
    sorted_uvs.append(sorted_uvs[0])

    # sorted_uvs のコーナーを指すインデックス
    corner_indices = [i for i, x in enumerate(sorted_uvs) if x in corner_uv_comps]
    corner_indices.append(len(sorted_uvs))

    # 各辺を構成するUVのリストのリスト
    all_sides_uvs = []

    for i in range(len(corner_uv_comps)):
        begin_index = corner_indices[i]
        end_index = corner_indices[i+1] + 1
        all_sides_uvs.append(sorted_uvs[begin_index:end_index])

    inner_uvs = set(shell_uvs) - set(border_uvs)

    total_lengths = dict()

    # UV修正前の中心を保持
    original_uv_center = get_average_uv(shell_uvs)

    # UV の再配置
    # 各辺の UV の比率がジオメトリに比例した状態の [0, 1] 正方形を作る
    for i, one_side_uvs in enumerate(all_sides_uvs):
        one_side_vertices = [cmds.polyListComponentConversion(x, tv=True)[0] for x in one_side_uvs]
        lengths = length_each_vertices(one_side_vertices)
        total_length = sum(lengths)
        side = ["left", "top", "right", "bottom"][i]
        total_lengths[side] = total_length

        for j in range(len(one_side_uvs)):
            position = sum(lengths[0:j]) / total_length
            u = 0.0
            v = 0.0

            if side == "left":
                u = 0.0
                v = position
            if side == "top":
                u = position
                v = 1.0
            if side == "right":
                u = 1.0
                v = 1.0 - position
            if side == "bottom":
                u = 1.0 - position
                v = 0.0
            else:
                pass

            
            cmds.polyEditUV(one_side_uvs[j], u=u, v=v, relative=False)

    # 縦横比の調整
    u_max_length = max(total_lengths["top"], total_lengths["bottom"])
    v_max_length = max(total_lengths["left"], total_lengths["right"])
    u_scale = 1.0
    v_scale = 1.0

    if u_max_length > v_max_length:
        u_scale = u_max_length / v_max_length
    elif  v_max_length > u_max_length:    
        v_scale = v_max_length / u_max_length
    else:
        pass

    cmds.polyEditUV(shell_uvs, su=u_scale, sv=v_scale)

    # 内部の unfold
    if inner_uvs:
        cmds.u3dUnfold(inner_uvs, ite=1, p=0, bi=1, tf=1, ms=1024, rs=0)

    # 裏表の修正
    all_faces = cmds.filterExpand(cmds.polyListComponentConversion(shell_uvs, tf=True), sm=34)
    sample_count = min(len(all_faces), 10)
    representative_faces = random.sample(all_faces, sample_count)
    front_face_count = len([x for x in representative_faces if is_frontfacing_uvshell(x)])
    is_flip = front_face_count < sample_count/2

    if is_flip:
        cmds.polyEditUV(shell_uvs, su=-1)
    
    # 内部の optimize
    if inner_uvs:
        cmds.u3dOptimize(inner_uvs, ite=1, pow=1, sa=1, bi=0, tf=1, ms=1024, rs=0)

    cmds.select(shell_uvs)
    mel.eval("texSetTexelDensity %s %s" % (target_texel, map_size))

    # 中心合わせ
    current_uv_center = get_average_uv(shell_uvs)
    offset_u, offset_v = [original - current for original, current in zip(original_uv_center, current_uv_center)]
    cmds.polyEditUV(shell_uvs, u=offset_u, v=offset_v)

    # シェルの方向修正

    # UVスペースで上を向いているエッジの3D空間での方向ベクトル
    v1 = cmds.polyListComponentConversion(sorted_uvs[0], tv=True)[0]
    v2 = cmds.polyListComponentConversion(sorted_uvs[1], tv=True)[0]
    p1 = cmds.xform(v1, q=True, translation=True, ws=True)
    p2 = cmds.xform(v2, q=True, translation=True, ws=True)
    y_vector = om.MVector([b - a for a, b in zip(p1, p2)])
    y_vector.normalize()

    # UVスペースで右を向いているエッジの3D空間での方向ベクトル (裏表フリップ前の右)
    v1 = cmds.polyListComponentConversion(sorted_uvs[-1], tv=True)[0]
    v2 = cmds.polyListComponentConversion(sorted_uvs[-2], tv=True)[0]
    p1 = cmds.xform(v1, q=True, translation=True, ws=True)
    p2 = cmds.xform(v2, q=True, translation=True, ws=True)
    x_vector = om.MVector([b - a for a, b in zip(p1, p2)])
    x_vector.normalize()
    if is_flip:
        x_vector *= -1

    y_axis = om.MVector((0, 1, 0))  # ワールドY軸ベクトル


    # ワールドY軸との類似度で UV シェルを近い向きに回転
    y_dot_y = y_vector * y_axis
    x_dot_y = x_vector * y_axis

    if -1.0 <= y_dot_y <= -0.5:
        cmds.polyEditUV(shell_uvs, pu=original_uv_center[0], pv=original_uv_center[1], rotation=True, angle=180)

    elif -0.5 < y_dot_y < 0.5:
        angle = math.copysign(90, x_dot_y)
        cmds.polyEditUV(shell_uvs, pu=original_uv_center[0], pv=original_uv_center[1], rotation=True, angle=angle)

    elif 0.5 <= y_dot_y <= 1.0:
        pass

    else:
        pass

    # 選択の復帰
    cmds.select(current_selections)

    return True


def split_uvs_each_uv_shell(uvs):
    """指定したUVリストをUVシェル毎に分割したリストのリストとして返す｡

    Args:
        uvs (list[str]): UVを表すコンポーネント文字列のリスト

    Returns:
        list[list[str]]: UVシェル毎にUVコンポーネント文字列をリストにしたもののリスト
    """
    shell_id_to_uvs = dict()

    for uv in uvs:
        shell_uvs = cmds.filterExpand(cmds.polyListComponentConversion(uv, tuv=True, uvShell=True), sm=35)
        shell_id = shell_uvs[0]

        if shell_id not in shell_id_to_uvs.keys():
            shell_id_to_uvs[shell_id] = []

        shell_id_to_uvs[shell_id].append(uv)

    return shell_id_to_uvs.values()


def main(corner_uv_comps=None, target_texel=15, map_size=1024):

    if not corner_uv_comps:
        corner_uv_comps = cmds.ls(selection=True, flatten=True)

    uvs_each_uv_shell = split_uvs_each_uv_shell(corner_uv_comps)

    for uvs in uvs_each_uv_shell:
        rectilinearize_uvshell(uvs, target_texel=target_texel, map_size=map_size)
