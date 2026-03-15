"""エッジのテクセルを統一する関数"""
import math
import re

from itertools import combinations
from enum import Enum

import maya.cmds as cmds
import maya.api.OpenMaya as om


class UVVector(om.MVector):
    """UV座標を扱うためのクラス

    MVector の x と y を u と v でアクセスできるようにしただけ
    """
    @property
    def u(self):
        return self.x

    @u.setter
    def u(self, value):
        self.x = value

    @property
    def v(self):
        return self.y

    @v.setter
    def v(self, value):
        self.y = value


class AlignMode(Enum):
    """アライン方向を指定するための Enum"""
    U_MIN = "u_min"
    U_MAX = "u_max"
    V_MIN = "v_min"
    V_MAX = "v_max"
    AUTO_EACH = "auto_each"
    AUTO_AVG = "auto_avg"


def unify_edge_texel(target_texel, mapsize, mode):
    """ UV エッジを指定のテクセル密度にする

    エッジ選択モードならすべてのエッジが対象
    UV選択モードなら選択した第一UVと第二UVの距離に

    Args:
        target_texel (float): 統一後のテクセル密度
        mapsize (int): テクスチャのpixel数
        mode (AlignMode): アラインモード

    Raises:
        ValueError: _description_
    """
    is_uv_selection = cmds.selectType(q=True, puv=True)
    is_edge_selection = cmds.selectType(q=True, pe=True)

    target_uv_pairs = []  # エッジをなす2つのUVコンポーネントのタプルをリストにしたもの list[tuple[str, str]]
    selected_uv_comps = []

    # エッジ選択モードならエッジを構成する 2 頂点の UV をペアとして targetUVsList に追加する
    if is_edge_selection:
        selected_edges = cmds.filterExpand(cmds.ls(os=True), sm=32)

        if not selected_edges:
            print("エッジもしくは UV を 2 点選択してください｡")
            return

        for edge in selected_edges:
            selected_uv_comps = cmds.filterExpand(cmds.polyListComponentConversion(edge, tuv=True), sm=35)

            if len(selected_uv_comps) == 2:  # 非ボーダー
                target_uv_pairs.append(selected_uv_comps)

            elif len(selected_uv_comps) == 3:  # L字 ボーダー
                pass  # 勝手にソートされるのでフェースに着目して分離する必要あり

            elif len(selected_uv_comps) == 4:  # I字 ボーダー
                # 勝手にソートされるのでフェースに着目して分離する必要あり
                # 同一シェルの場合に限る
                pass

            else:
                pass

    # UV選択モードならエッジを共有する UV 同士をペアにして targetUVsList に追加する
    elif is_uv_selection:
        edge_uv_dict = dict()  # フェースID･エッジIDのペアをキーとして UV コンポーネント文字列のリストを値に持つ辞書
        selected_uv_comps = cmds.filterExpand(cmds.ls(os=True), sm=35)

        if not selected_uv_comps or len(selected_uv_comps) < 2:
            print("エッジもしくは UV を 2 点選択してください｡")
            return

        for uv_comp in selected_uv_comps:
            # UV に隣接するエッジとフェースを取得
            conv_edge_comps = cmds.filterExpand(cmds.polyListComponentConversion(uv_comp, fuv=True, te=True), sm=32)
            conv_face_comps = cmds.filterExpand(cmds.polyListComponentConversion(uv_comp, fuv=True, tf=True), sm=34)

            for edge_comp in conv_edge_comps:
                for face_comps in conv_face_comps:
                    ei = re.search(r"\[(\d+)\]", edge_comp).groups()[0]
                    fi = re.search(r"\[(\d+)\]", face_comps).groups()[0]
                    key = "e%sf%s" % (ei, fi)

                    edge_uv_dict[key] = edge_uv_dict.get(key, [])
                    edge_uv_dict[key].append(uv_comp)

        for uv_pair in edge_uv_dict.values():
            if len(set(uv_pair)) == 2:
                value = tuple(sorted(uv_pair))
                if value not in target_uv_pairs:
                    target_uv_pairs.append(value)

    if not is_edge_selection and not is_uv_selection:
        print("エッジまたは UV を選択してください｡")
        return

    border_uv_comps = []

    # UVボーダー上の UV
    border_uv_comps = []
    for uv_pair in target_uv_pairs:
        for uv_comp in uv_pair:
            reconv_vts = cmds.polyListComponentConversion(cmds.polyListComponentConversion(uv_comp, tv=True), tuv=True)

            if len(reconv_vts) > 1 or uv_comp in border_uv_comps:
                border_uv_comps.append(uv_comp)

    non_border_uv_comps = list(set(selected_uv_comps) - set(border_uv_comps))

    # ボーダー UV の偏りからアライン方向特定
    if mode == AlignMode.AUTO_AVG:
        if len(target_uv_pairs) == 1:
            print("UV 2 点による Auto モードは使用できません｡")
            return

        if non_border_uv_comps and border_uv_comps:
            # ボーダー･非ボーダーともにある場合は
            # ボーダーの分散で軸方向を決め､ボーダー･非ボーダーの平均座標の比較でmin/maxを決める
            border_uv_coords = [UVVector(cmds.polyEditUV(uvcmp, q=True)) for uvcmp in border_uv_comps]
            non_border_uv_coords = [UVVector(cmds.polyEditUV(uvcmp, q=True)) for uvcmp in non_border_uv_comps]

            border_uv_avg_coord = UVVector(sum(border_uv_coords, UVVector(0, 0)) / len(border_uv_coords))
            non_border_uv_avg_coord = UVVector(sum(non_border_uv_coords, UVVector(0, 0)) / len(non_border_uv_coords))

            distribution_u = max([uv.u for uv in border_uv_coords]) - min([uv.u for uv in border_uv_coords])
            distribution_v = max([uv.v for uv in border_uv_coords]) - min([uv.v for uv in border_uv_coords])

            if distribution_u >= distribution_v:
                if border_uv_avg_coord.v < non_border_uv_avg_coord.v:
                    actual_mode = AlignMode.V_MIN
                else:
                    actual_mode = AlignMode.V_MAX

            else:
                if border_uv_avg_coord.u < non_border_uv_avg_coord.u:
                    actual_mode = AlignMode.U_MIN
                else:
                    actual_mode = AlignMode.U_MAX

        else:
            # それ以外の場合は各 uv_pair の分散の合計で軸方向を決める
            sum_distribution_u = 0
            sum_distribution_v = 0
            for uv_pair in target_uv_pairs:
                uv_coords = [UVVector(cmds.polyEditUV(uvcmp, q=True)) for uvcmp in uv_pair]
                sum_distribution_u += max([uv.u for uv in uv_coords]) - min([uv.u for uv in uv_coords])
                sum_distribution_v += max([uv.v for uv in uv_coords]) - min([uv.v for uv in uv_coords])

            if sum_distribution_u < sum_distribution_v:
                # U の方が狭いので軸は V
                # 各エッジの V 座標から小さい方と大きい方をそれぞれ抽出して分散が小さい方を基準側にする
                smaller_coords = []
                bigger_coords = []
                for uv_pair in target_uv_pairs:
                    coords = [UVVector(cmds.polyEditUV(uvcmp, q=True)).v for uvcmp in uv_pair]
                    smaller_coords.append(min(coords))
                    bigger_coords.append(max(coords))

                distribution_smaller = max(smaller_coords) - min(smaller_coords)
                distribution_bigger = max(bigger_coords) - min(bigger_coords)

                if distribution_smaller < distribution_bigger:
                    actual_mode = AlignMode.V_MIN
                else:
                    actual_mode = AlignMode.V_MAX

            else:
                # V の方が狭いので軸は U
                # 各エッジの U 座標から小さい方と大きい方をそれぞれ抽出して分散が小さい方を基準側にする
                smaller_coords = []
                bigger_coords = []
                for uv_pair in target_uv_pairs:
                    coords = [UVVector(cmds.polyEditUV(uvcmp, q=True)).u for uvcmp in uv_pair]
                    smaller_coords.append(min(coords))
                    bigger_coords.append(max(coords))

                distribution_smaller = max(smaller_coords) - min(smaller_coords)
                distribution_bigger = max(bigger_coords) - min(bigger_coords)

                if distribution_smaller < distribution_bigger:
                    actual_mode = AlignMode.U_MIN
                else:
                    actual_mode = AlignMode.U_MAX

    elif mode == AlignMode.AUTO_EACH:
        pass

    else:
        actual_mode = mode

    # エッジごとにテクセル設定処理
    for uv_pair in target_uv_pairs:
        # uv に対応する頂点
        vtx1 = cmds.polyListComponentConversion(uv_pair[0], fuv=True, tv=True)[0]
        vtx2 = cmds.polyListComponentConversion(uv_pair[1], fuv=True, tv=True)[0]

        # UV 座標と XYZ 座標取得
        uv1 = UVVector(cmds.polyEditUV(uv_pair[0], q=True))
        uv2 = UVVector(cmds.polyEditUV(uv_pair[1], q=True))
        p1 = om.MVector(cmds.xform(vtx1, q=True, ws=True, t=True))
        p2 = om.MVector(cmds.xform(vtx2, q=True, ws=True, t=True))

        xyz_length = (p1 - p2).length()
        u_length = abs(uv1.u - uv2.u)
        v_length = abs(uv1.v - uv2.v)

        if mode == AlignMode.AUTO_EACH:
            pass

        # 3D 空間でのエッジの傾きによるスケール補正率の計算
        # アライン方向から固定する UV と動かす UV を決定
        if actual_mode == AlignMode.U_MIN:
            if uv1.u < uv2.u:
                base_uv = uv_pair[0]
                end_uv = uv_pair[1]
            else:
                base_uv = uv_pair[1]
                end_uv = uv_pair[0]

        elif actual_mode == AlignMode.U_MAX:
            if uv1.u > uv2.u:
                base_uv = uv_pair[0]
                end_uv = uv_pair[1]
            else:
                base_uv = uv_pair[1]
                end_uv = uv_pair[0]

        elif actual_mode == AlignMode.V_MIN:
            if uv1.v < uv2.v:
                base_uv = uv_pair[0]
                end_uv = uv_pair[1]
            else:
                base_uv = uv_pair[1]
                end_uv = uv_pair[0]

        elif actual_mode == AlignMode.V_MAX:
            if uv1.v > uv2.v:
                base_uv = uv_pair[0]
                end_uv = uv_pair[1]
            else:
                base_uv = uv_pair[1]
                end_uv = uv_pair[0]

        else:
            base_uv = uv_pair[0]
            end_uv = uv_pair[1]

        # 補助軸となる UV を決定する
        # この UV を頂点に変換して 3D 空間でのエッジの傾きを計算する

        neighbor_uvs = cmds.filterExpand(cmds.polyListComponentConversion(cmds.polyListComponentConversion(base_uv, tf=True), tuv=True), sm=35)
        neighbor_uvs = list(set(neighbor_uvs) - set(uv_pair))

        uv_coord_base = UVVector(cmds.polyEditUV(base_uv, q=True))
        uv_coord_end = UVVector(cmds.polyEditUV(end_uv, q=True))
        pair_vector = uv_coord_end - uv_coord_base

        angle_comp_pairs = []
        for neighbor_uv in neighbor_uvs:
            uv_coord_neighbor = UVVector(cmds.polyEditUV(neighbor_uv, q=True))
            neighbor_vector = uv_coord_neighbor - uv_coord_base

            # 2つのベクトルのなす角を計算
            angle = pair_vector.angle(neighbor_vector)

            angle_comp_pairs.append((angle, neighbor_uv))

        # なす角が最も大きい UV を補助軸とする
        sub_uvcomp = sorted(angle_comp_pairs, key=lambda x: x[0], reverse=True)[0][1]

        base_vtx = cmds.polyListComponentConversion(base_uv, tv=True)[0]
        end_vtx = cmds.polyListComponentConversion(end_uv, tv=True)[0]
        sub_vtx = cmds.polyListComponentConversion(sub_uvcomp, tv=True)[0]

        p_base = om.MVector(cmds.xform(base_vtx, q=True, ws=True, t=True))
        p_end = om.MVector(cmds.xform(end_vtx, q=True, ws=True, t=True))
        p_sub = om.MVector(cmds.xform(sub_vtx, q=True, ws=True, t=True))

        # TODO: base_vtx に接続されている複数のエッジがある程度角度を成している場合は平均ベクトルとのなす角で計算する｡垂直ベクトルはフェース法線とエッジベクトルの外積
        angle = (p_base - p_sub).angle(p_base - p_end)
        adj_scale = math.sin(angle)

        if actual_mode == AlignMode.U_MIN:
            currentTexel = u_length / xyz_length * mapsize
            if currentTexel == 0:
                continue
            scale = target_texel / currentTexel * adj_scale
            pivot_u = min(uv1.u, uv2.u)
            pivot_v = 0
            cmds.polyEditUV(uv_pair[0], pu=pivot_u, pv=pivot_v, su=scale, sv=1)
            cmds.polyEditUV(uv_pair[1], pu=pivot_u, pv=pivot_v, su=scale, sv=1)

        elif actual_mode == AlignMode.U_MAX:
            currentTexel = u_length / xyz_length * mapsize
            if currentTexel == 0:
                continue
            scale = target_texel / currentTexel * adj_scale
            pivot_u = max(uv1.u, uv2.u)
            pivot_v = 0
            cmds.polyEditUV(uv_pair[0], pu=pivot_u, pv=pivot_v, su=scale, sv=1)
            cmds.polyEditUV(uv_pair[1], pu=pivot_u, pv=pivot_v, su=scale, sv=1)

        elif actual_mode == AlignMode.V_MIN:
            currentTexel = v_length / xyz_length * mapsize
            if currentTexel == 0:
                continue
            scale = target_texel / currentTexel * adj_scale
            pivot_u = 0
            pivot_v = min(uv1.v, uv2.v)
            cmds.polyEditUV(uv_pair[0], pu=pivot_u, pv=pivot_v, su=1, sv=scale)
            cmds.polyEditUV(uv_pair[1], pu=pivot_u, pv=pivot_v, su=1, sv=scale)

        elif actual_mode == AlignMode.V_MAX:
            currentTexel = v_length / xyz_length * mapsize
            if currentTexel == 0:
                continue
            scale = target_texel / currentTexel * adj_scale
            pivot_u = 0
            pivot_v = max(uv1.v, uv2.v)
            cmds.polyEditUV(uv_pair[0], pu=pivot_u, pv=pivot_v, su=1, sv=scale)
            cmds.polyEditUV(uv_pair[1], pu=pivot_u, pv=pivot_v, su=1, sv=scale)

        else:
            raise ValueError(f"未知のモード: {actual_mode}")


def get_texel(mapsize):
    """テクセル密度の取得

    UVシェル、もしくはUVエッジのテクセルを設定
    shell選択ならMayaの機能を使用し それ以外なら独自のUVエッジに対するテクセル設定モードを使用する
    """
    is_uv_selection = cmds.selectType(q=True, puv=True)
    is_edge_selection = cmds.selectType(q=True, pe=True)

    if is_edge_selection:
        selected_edges = cmds.filterExpand(cmds.ls(selection=True), sm=32)

        if not selected_edges:
            print("エッジもしくは UV を 2 点選択してください｡")
            return None

        selected_uvs = cmds.filterExpand(cmds.polyListComponentConversion(selected_edges, tuv=True), sm=35)

    elif is_uv_selection:
        selected_uvs = cmds.ls(selection=True, flatten=True)

        if len(selected_uvs) < 2:
            print("エッジもしくは UV を 2 点選択してください｡")
            return None

    else:
        print("エッジもしくは UV を 2 点選択してください｡")
        return None

    # スタックされてる UV をまとめて選択した場合にモデルの左右の UVをピックしないように
    # 隣接 (エッジ共有) していることを条件にペアを作る
    if len(selected_uvs) != 2:
        for uv_pair in combinations(selected_uvs, 2):
            edges0 = cmds.filterExpand(cmds.polyListComponentConversion(uv_pair[0], te=True), sm=32)
            edges1 = cmds.filterExpand(cmds.polyListComponentConversion(uv_pair[1], te=True), sm=32)

            if set(edges0) & set(edges1):
                uv1 = uv_pair[0]
                uv2 = uv_pair[1]
                break

    else:
        uv1 = selected_uvs[0]
        uv2 = selected_uvs[1]

    uv1_coord = UVVector(cmds.polyEditUV(uv1, q=True))
    uv2_coord = UVVector(cmds.polyEditUV(uv2, q=True))

    vtx1 = cmds.polyListComponentConversion(uv1, tv=True)[0]
    vtx2 = cmds.polyListComponentConversion(uv2, tv=True)[0]
    vtx1_coord = om.MVector(cmds.xform(vtx1, q=True, ws=True, t=True))
    vtx2_coord = om.MVector(cmds.xform(vtx2, q=True, ws=True, t=True))

    geoLength = (vtx1_coord - vtx2_coord).length()
    uvLength = (uv1_coord - uv2_coord).length()
    texel_density = uvLength / geoLength * mapsize

    return texel_density
