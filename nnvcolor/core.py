#! python
# coding:utf-8
"""頂点カラーツール"""
import re

from ctypes import windll, Structure, c_long, byref

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

import nnutil.ui as ui


class InvalidArgumentCombinationError(Exception):
    """引数の値の組み合わせが不正な場合の例外｡"""
    pass


class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]


def get_cursor_pos():
    pt = POINT()
    windll.user32.GetCursorPos(byref(pt))
    return (pt.x, pt.y)


def lerp(a, b, t):
    return (1.0 - t) * a + t * b


def get_all_vertex_colors(obj_name):
    """指定オブジェクトの全てのフェース頂点カラーを取得してリストで返す｡

    Args:
        obj_name (str): オブジェクト名

    Returns:
        list[MColor]: API が返す頂点カラーのリスト
    """
    selection = om.MGlobal.getSelectionListByName(obj_name)
    dagPath = selection.getDagPath(0)
    component = selection.getComponent(0)[1]
    fnMesh = om.MFnMesh(dagPath)

    # 全頂点フェースカラーを取得
    colors = fnMesh.getFaceVertexColors()

    # フェースインデックスと頂点インデックスのリストを作成
    face_indices = om.MIntArray()
    vertex_indices = om.MIntArray()

    for i in range(fnMesh.numPolygons):
        polygon_vertices = fnMesh.getPolygonVertices(i)
        for j in polygon_vertices:
            face_indices.append(i)
            vertex_indices.append(j)

    return colors


def set_all_vertex_colors(obj_name, colors, channels=4, r=False, g=False, b=False, a=False):
    """オブジェクトの頂点カラーを指定チャンネルのみ上書きする

    Args:
        obj_name (str): オブジェクト名
        colors (list[MColor]): 頂点カラーのリスト
        channels (int, optional): 頂点カラーのチャンネル数. Defaults to 4.
        r (bool, optional): Rチャンネルを上書きするか. Defaults to False.
        g (bool, optional): Gチャンネルを上書きするか. Defaults to False.
        b (bool, optional): Bチャンネルを上書きするか. Defaults to False.
        a (bool, optional): Aチャンネルを上書きするか. Defaults to False.
    """
    selection = om.MGlobal.getSelectionListByName(obj_name)
    dagPath = selection.getDagPath(0)
    component = selection.getComponent(0)[1]
    fnMesh = om.MFnMesh(dagPath)

    # フェースインデックスと頂点インデックスのリストを作成
    face_indices = om.MIntArray()
    vertex_indices = om.MIntArray()

    for i in range(fnMesh.numPolygons):
        polygon_vertices = fnMesh.getPolygonVertices(i)
        for j in polygon_vertices:
            face_indices.append(i)
            vertex_indices.append(j)

    new_colors = get_all_vertex_colors(obj_name)

    for i in range(len(new_colors)):
        if channels > 0 and r:
            new_colors[i][0] = colors[i][0]

        if channels > 1 and g:
            new_colors[i][1] = colors[i][1]

        if channels > 2 and b:
            new_colors[i][2] = colors[i][2]

        if channels > 3 and a:
            new_colors[i][3] = colors[i][3]

    # 値の設定
    modifier = om.MDGModifier()
    fnMesh.setFaceVertexColors(new_colors, face_indices, vertex_indices, modifier)
    modifier.doIt()


def store_colors(objects):
    colors_dict = {}

    for obj in objects:
        colors_dict[obj] = get_all_vertex_colors(obj)

    return colors_dict


def restore_colors(objects, colors_dict, r, g, b, a):
    for obj in objects:
        color_component_type = cmds.polyColorSet(obj, q=True, currentColorSet=True, representation=True)
        chanells = len(color_component_type)
        set_all_vertex_colors(obj, colors_dict[obj], channels=chanells, r=r, g=g, b=b, a=a)


def str_to_vfi(vf_comp_string):
    """頂点フェースを表すコンポーネント文字列からインデックスのタプル (fi, vi) を返す｡"""
    match = re.search(r"\[(\d+)\]\[(\d+)\]", vf_comp_string)

    if match:
        vi, fi = match.groups()

        return (fi, vi)

    else:
        return None


def vfi_to_str(obj, fi, vi):
    """オブジェクト名とインデックスから頂点フェースを表すコンポーネント文字列を返す｡"""
    return "%s.vtxFace[%s][%s]" % (obj, vi, fi)


window_name = "NN_VColor"
window = None


def get_window():
    return window


class NN_ToolWindow(object):
    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (250, 240)

        self.is_chunk_open = False
        self.editbox_precision = 4
        self.vf_color_caches = dict()  # スライド開始時の頂点カラーキャッシュ dict[obj_name, list[MColor]]

        self.brush_size_mode = False
        self.cached_value = 1.0
        self.start_pos = (0, 0)
        self.cached_size = 0.1

    def create(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)

        # プリファレンスの有無による分岐
        if cmds.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = cmds.windowPref(self.window, q=True, topLeftCorner=True)
            cmds.windowPref(self.window, remove=True)

            cmds.window(self.window, t=self.title, maximizeButton=False, minimizeButton=False, topLeftCorner=position, widthHeight=self.size, sizeable=False)

        else:
            # プリファレンスがなければデフォルト位置に指定サイズで表示
            cmds.window(self.window, t=self.title, maximizeButton=False, minimizeButton=False, widthHeight=self.size, sizeable=False)

        self.layout()
        cmds.showWindow(self.window)

    def layout(self):
        row_height1 = ui.height(1.0)
        row_height2 = ui.height(0.9)

        ui.column_layout()

        ui.row_layout()
        ui.button(label="RGBA", c=self.onSetColorRGBA, dgc=self.onGetColorRGBA)
        ui.button(label="Create Set [Op]", c=self.onCreateColorSet, dgc=self.onColorSetEditor, width=ui.width(3.75))
        ui.button(label="Toggle Disp", c=self.onToggleDisplay, width=ui.width(3.75))
        ui.end_layout()

        ui.separator(width=1, height=5)

        ui.row_layout()
        ui.button(label="R", c=self.onSetColorR, dgc=self.onGetColorR, width=ui.width(2), height=row_height1)
        ui.button(label="0.00", c=self.onSetColorR000, bgc=(0, 0, 0), width=ui.width1_5, height=row_height1)
        ui.button(label="0.25", c=self.onSetColorR025, bgc=(0.25, 0, 0), width=ui.width1_5, height=row_height1)
        ui.button(label="0.50", c=self.onSetColorR050, bgc=(0.5, 0, 0), width=ui.width1_5, height=row_height1)
        ui.button(label="0.75", c=self.onSetColorR075, bgc=(0.75, 0, 0), width=ui.width1_5, height=row_height1)
        ui.button(label="1.00", c=self.onSetColorR100, bgc=(1.0, 0, 0), width=ui.width1_5, height=row_height1)
        ui.end_layout()

        ui.row_layout()
        self.eb_red = ui.eb_float(min=0.0, max=1.0, v=1.0, precision=self.editbox_precision, width=ui.width(2), height=row_height2, dc=self.onDragEditBoxRed, cc=self.onChangeEditBoxRed)
        self.fs_red = ui.float_slider(min=0, max=1.0, value=1.0, width=ui.width(7.5), height=row_height2, dc=self.onDragRed, cc=self.onChangeSliderRed)
        ui.end_layout()

        ui.separator(width=1, height=5)

        ui.row_layout()
        ui.button(label="G", c=self.onSetColorG, dgc=self.onGetColorG, width=ui.width(2))
        ui.button(label="0.00", c=self.onSetColorG000, bgc=(0, 0, 0), width=ui.width1_5)
        ui.button(label="0.25", c=self.onSetColorG025, bgc=(0, 0.25, 0), width=ui.width1_5)
        ui.button(label="0.50", c=self.onSetColorG050, bgc=(0, 0.5, 0), width=ui.width1_5)
        ui.button(label="0.75", c=self.onSetColorG075, bgc=(0, 0.75, 0), width=ui.width1_5)
        ui.button(label="1.00", c=self.onSetColorG100, bgc=(0, 1.0, 0), width=ui.width1_5)
        ui.end_layout()

        ui.row_layout()
        self.eb_green = ui.eb_float(min=0.0, max=1.0, v=1.0, precision=self.editbox_precision, width=ui.width(2), dc=self.onDragEditBoxGreen, cc=self.onChangeEditBoxGreen)
        self.fs_green = ui.float_slider(min=0, max=1.0, value=1.0, width=ui.width(7.5), dc=self.onDragGreen, cc=self.onChangeSliderGreen)
        ui.end_layout()

        ui.separator(width=1, height=5)

        ui.row_layout()
        ui.button(label="B", c=self.onSetColorB, dgc=self.onGetColorB, width=ui.width(2))
        ui.button(label="0.00", c=self.onSetColorB000, bgc=(0, 0, 0), width=ui.width1_5)
        ui.button(label="0.25", c=self.onSetColorB025, bgc=(0, 0, 0.25), width=ui.width1_5)
        ui.button(label="0.50", c=self.onSetColorB050, bgc=(0, 0, 0.5), width=ui.width1_5)
        ui.button(label="0.75", c=self.onSetColorB075, bgc=(0, 0, 0.75), width=ui.width1_5)
        ui.button(label="1.00", c=self.onSetColorB100, bgc=(0, 0, 1.0), width=ui.width1_5)
        ui.end_layout()

        ui.row_layout()
        self.eb_blue = ui.eb_float(min=0.0, max=1.0, v=1.0, precision=self.editbox_precision, width=ui.width(2), dc=self.onDragEditBoxBlue, cc=self.onChangeEditBoxBlue)
        self.fs_blue = ui.float_slider(min=0, max=1.0, value=1.0, width=ui.width(7.5), dc=self.onDragBlue, cc=self.onChangeSliderBlue)
        ui.end_layout()

        ui.separator(width=1, height=5)

        ui.row_layout()
        ui.button(label="A", c=self.onSetColorA, dgc=self.onGetColorA, width=ui.width(2))
        ui.button(label="0.00", c=self.onSetColorA000, bgc=(0, 0, 0), width=ui.width1_5)
        ui.button(label="0.25", c=self.onSetColorA025, bgc=(0.25, 0.25, 0.25), width=ui.width1_5)
        ui.button(label="0.50", c=self.onSetColorA050, bgc=(0.5, 0.5, 0.5), width=ui.width1_5)
        ui.button(label="0.75", c=self.onSetColorA075, bgc=(0.75, 0.75, 0.75), width=ui.width1_5)
        ui.button(label="1.00", c=self.onSetColorA100, bgc=(1.0, 1.0, 1.0), width=ui.width1_5)
        ui.end_layout()

        ui.row_layout()
        self.eb_alpha = ui.eb_float(min=0.0, max=1.0, v=1.0, precision=self.editbox_precision, width=ui.width(2), dc=self.onDragEditBoxAlpha, cc=self.onChangeEditBoxAlpha)
        self.fs_alpha = ui.float_slider(min=0, max=1.0, value=1.0, width=ui.width(7.5), dc=self.onDragAlpha, cc=self.onChangeSliderAlpha)
        ui.end_layout()

        ui.row_layout()
        ui.end_layout()

        ui.row_layout()
        ui.end_layout()

        ui.end_layout()

    def _get_color(self, *args):
        """選択している全ての頂点の頂点カラーを平均した値を返す"""

        if not cmds.ls(selection=True):
            return None

        selections = cmds.ls(selection=True)

        # 選択オブジェクトにより適切なコンポーネントに変換
        if cmds.selectMode(q=True, object=True):
            if cmds.objectType(selections[0], isType="mesh"):
                targets = cmds.filterExpand(cmds.polyListComponentConversion(selections, tv=True), sm=31)
            else:
                return None

        elif cmds.selectType(q=True, vertex=True) or cmds.selectType(q=True, facet=True):
            targets = selections

        elif cmds.selectType(q=True, polymeshUV=True):
            targets = cmds.polyListComponentConversion(selections, tvf=True)

        elif cmds.selectType(q=True, edge=True):
            targets = cmds.polyListComponentConversion(selections, tv=True)

        else:
            return None

        # 色を取得し平均して返す
        color_components = cmds.polyColorPerVertex(targets, q=True, r=True, g=True, b=True, a=True)

        if color_components:
            r_list = [color_components[4*i+0] for i in range(len(color_components)//4)]
            g_list = [color_components[4*i+1] for i in range(len(color_components)//4)]
            b_list = [color_components[4*i+2] for i in range(len(color_components)//4)]
            a_list = [color_components[4*i+3] for i in range(len(color_components)//4)]
            count = len(r_list)

            r = sum(r_list)/count
            g = sum(g_list)/count
            b = sum(b_list)/count
            a = sum(a_list)/count

            return (r, g, b, a)

        else:
            return None

    def onCreateColorSet(self, *args):
        """カラーセットを作成する"""
        cmds.polyColorSet(create=True, clamped=0, rpt="RGBA", colorSet="colorSet")

    def onColorSetEditor(self, *args):
        """カラーセットエディタを開く"""
        mel.eval("colorSetEditor")

    def onToggleDisplay(self, *args):
        """頂点カラー表示のトグル"""
        mel.eval("toggleShadeMode")

    def onGetColorRGBA(self, *args):
        """選択している全ての頂点の頂点カラーの平均の RGBA 成分をスライダーに設定する"""
        color = self._get_color()

        if color:
            ui.set_value(self.fs_red, value=color[0])
            ui.set_value(self.fs_green, value=color[1])
            ui.set_value(self.fs_blue, value=color[2])
            ui.set_value(self.fs_alpha, value=color[3])

            self._sync_slider_and_editbox(from_slider=True)

    def onSetColorRGBA(self, *args):
        """スライダーの値でRGBAを全て設定する"""
        selection = cmds.ls(selection=True)

        if selection:
            r = ui.get_value(self.fs_red)
            g = ui.get_value(self.fs_green)
            b = ui.get_value(self.fs_blue)
            a = ui.get_value(self.fs_alpha)

            targets = cmds.polyListComponentConversion(selection, tvf=True)
            cmds.polyColorPerVertex(targets, r=r, g=g, b=b, a=a)

    def onGetColorR(self, *args):
        """選択している全ての頂点の頂点カラーの平均の R 成分をスライダーに設定する"""
        color = self._get_color()

        if color:
            ui.set_value(self.fs_red, value=color[0])

            self._sync_slider_and_editbox(from_slider=True)

    def onGetColorG(self, *args):
        """選択している全ての頂点の頂点カラーの平均の G 成分をスライダーに設定する"""
        color = self._get_color()

        if color:
            ui.set_value(self.fs_green, value=color[1])

            self._sync_slider_and_editbox(from_slider=True)

    def onGetColorB(self, *args):
        """選択している全ての頂点の頂点カラーの平均の B 成分をスライダーに設定する"""
        color = self._get_color()

        if color:
            ui.set_value(self.fs_blue, value=color[2])

            self._sync_slider_and_editbox(from_slider=True)

    def onGetColorA(self, *args):
        """選択している全ての頂点の頂点カラーの平均の A 成分をスライダーに設定する"""
        color = self._get_color()

        if color:
            ui.set_value(self.fs_alpha, value=color[3])

            self._sync_slider_and_editbox(from_slider=True)

    def _set_unified_color(self, targets, channel, value, via_api):
        """指定頂点カラーに同一値を設定する｡最終的な設定は cmds経由で Undo 可能｡同一色での塗りつぶし1回なので早い｡

        Args:
            targets (list[str]): 対象コンポーネント
            channel (str): 上書きするチャンネル
            value (float): 上書きする値

        TODO: 高速化が必要な場合は via_api で分岐して API での処理を書く
        """
        if targets:
            # UV選択なら vf 変換､エッジ選択なら vtx 変換する
            if cmds.selectType(q=True, polymeshUV=True):
                targets = cmds.polyListComponentConversion(targets, tvf=True)

            elif cmds.selectType(q=True, edge=True):
                targets = cmds.polyListComponentConversion(targets, tv=True)

            # オブジェクト全体の現在の頂点カラーを保存する
            objects = cmds.polyListComponentConversion(targets)
            stored_colors = store_colors(objects)

            # 指定のチャンネルを上書きする｡ polyColorPerVertex の仕様で他チャンネルが崩れるので
            # 保存した頂点カラーで復帰する
            if channel == "r":
                cmds.polyColorPerVertex(targets, r=value)
                restore_colors(objects, stored_colors, r=False, g=True, b=True, a=True)

            if channel == "g":
                cmds.polyColorPerVertex(targets, g=value)
                restore_colors(objects, stored_colors, r=True, g=False, b=True, a=True)

            if channel == "b":
                cmds.polyColorPerVertex(targets, b=value)
                restore_colors(objects, stored_colors, r=True, g=True, b=False, a=True)

            if channel == "a":
                cmds.polyColorPerVertex(targets, a=value)
                restore_colors(objects, stored_colors, r=True, g=True, b=True, a=False)

            else:
                pass

    def _blend_color(self, vf_color_caches, channel, v, weight_mul=1.0, mode="copy", via_api=False):
        """頂点カラーそれぞれに指定した値を設定する｡最終的な設定は cmds経由で Undo 可能｡コンポーネント反復するので遅い｡

        Args:
            vf_color_caches (dict[str, list[MColor]]): オブジェクト毎の全頂点カラー
            channel (str): 上書きするチャンネル
        """
        if not cmds.softSelect(q=True, softSelectEnabled=True):
            return None

        # MRichSeleciton 構築
        rich_selection = om.MGlobal.getRichSelection()
        sl_rich_sel = rich_selection.getSelection()
        sl_rich_sel_sym = rich_selection.getSymmetry()

        # オブジェクト毎の処理
        for i in range(sl_rich_sel.length()):
            # MRichSeleciton からウェイト取得
            obj, comp = sl_rich_sel.getComponent(i)
            fn_comp = om.MFnSingleIndexedComponent(comp)
            obj_name = obj.fullPathName()
            fn_mesh = om.MFnMesh(obj)

            # 頂点毎のウェイト
            vi_to_weight = dict()

            # ウェイトの取得
            selected_vis = fn_comp.getElements()

            for j in range(len(selected_vis)):
                vi = selected_vis[j]
                vi_to_weight[vi] = fn_comp.weight(j).influence

            # シンメトリ側に同一のオブジェクトがあればウェイト取得してマージする
            # 同一オブジェクトを別々に処理する (sl_rich_sel と sl_rich_sel_sym をそれぞれ for する等) と
            # スライド中にお互いがお互いをキャッシュで上書きされて使い勝手悪い
            for j in range(sl_rich_sel_sym.length()):
                sym_obj, sym_comp = sl_rich_sel_sym.getComponent(j)
                sym_obj_name = sym_obj.fullPathName()

                if obj_name == sym_obj_name:
                    fn_sym_comp = om.MFnSingleIndexedComponent(sym_comp)

                    selected_vis = fn_sym_comp.getElements()

                    for k in range(len(selected_vis)):
                        vi = selected_vis[k]
                        vi_to_weight[vi] = fn_sym_comp.weight(k).influence

                    fn_comp.addElements(fn_sym_comp.getElements())
                    selected_vis = fn_comp.getElements()
                    break

            # 選択コンポーネントを VF に分解
            target_fivi_indices = []  # list[tuple(fi, vi)]

            if comp.apiType() == om.MFn.kMeshVertComponent:
                # 頂点は所属フェース取得して (fi,vi) 構築
                v_itr = om.MItMeshVertex(obj, comp)

                while not v_itr.isDone():
                    vi = v_itr.index()
                    fis = v_itr.getConnectedFaces()

                    target_fivi_indices.extend([(fi, vi) for fi in fis])

                    v_itr.next()
            else:
                # MRichSeleciton が kMeshVertComponent 以外を返すようになったら修正が必要
                print("unknown comptype")
                pass

            # ブレンド元の頂点カラーが渡されていればそれを使用する｡なければ現在の頂点フェースカラーを取得
            if obj_name in vf_color_caches.keys():
                current_vf_colors = [om.MColor(x) for x in vf_color_caches[obj_name]]
            else:
                current_vf_colors = fn_mesh.getFaceVertexColors()

            # 頂点インデックス･フェースインデックスと 頂点フェースインデックス (1次元) の相互変換辞書
            vfi_to_fivi = [None] * len(current_vf_colors)
            fivi_to_vfi = dict()

            for fi in range(fn_mesh.numPolygons):
                vertex_indices = fn_mesh.getPolygonVertices(fi)

                for lvi, gvi in enumerate(vertex_indices):
                    vfi = fn_mesh.getFaceVertexIndex(fi, lvi)
                    vfi_to_fivi[vfi] = (fi, gvi)
                    fivi_to_vfi[(fi, gvi)] = vfi

            # 現在の色と引数で指定された色をブレンドしたリストを作成
            new_vf_colors = [om.MColor(x) for x in current_vf_colors]

            for fi, vi in target_fivi_indices:
                vfi = fivi_to_vfi[(fi, vi)]
                w = vi_to_weight[vi] * weight_mul

                new_vf_colors[vfi] = om.MColor(current_vf_colors[vfi])

                if channel == "r":
                    ci = 0
                elif channel == "g":
                    ci = 1
                elif channel == "b":
                    ci = 2
                elif channel == "a":
                    ci = 3
                else:
                    print("unknown channel")
                    ci = 0

                if mode == "copy":
                    new_vf_colors[vfi][ci] = current_vf_colors[vfi][ci] * (1.0 - w) + v * w

                elif mode == "mul":
                    new_vf_colors[vfi][ci] = current_vf_colors[vfi][ci] * lerp(1.0, v, w)

                elif mode == "div":
                    safe_v = 1e-9 if v == 0 else v
                    new_vf_colors[vfi][ci] = current_vf_colors[vfi][ci] / lerp(1.0, safe_v, w)

                else:
                    print("unknown mode")

            if via_api:
                # API はそのまま全VFに適用
                fis = [fi for fi, vi in vfi_to_fivi]
                vis = [vi for fi, vi in vfi_to_fivi]
                fn_mesh.setFaceVertexColors(new_vf_colors, fis, vis)

            else:
                # 一度キャッシュの内容に戻して cmds が作る Undo にドラッグ前の値を記憶させる
                fis = [fi for fi, vi in vfi_to_fivi]
                vis = [vi for fi, vi in vfi_to_fivi]
                fn_mesh.setFaceVertexColors(current_vf_colors, fis, vis)

                # cmds はインデックスで反復して適用
                for vfi, fivi in enumerate(vfi_to_fivi):
                    fi = fivi[0]
                    vi = fivi[1]

                    # ウェイトが無ければスキップ
                    if vi not in selected_vis:
                        continue

                    # 合成後の色を cmds で上書き
                    color = new_vf_colors[vfi]

                    target = vfi_to_str(obj_name, fi, vi)

                    if len(color) == 4:
                        r, g, b, a = list(color)
                        cmds.polyColorPerVertex(target, r=r, g=g, b=b, a=a)

                    elif len(color) == 3:
                        r, g, b = list(color)
                        cmds.polyColorPerVertex(target, r=r, g=g, b=b)

    def _on_set_color(self, channel, drag):
        """スライダーを元に頂点カラーを設定する

        Args:
            channel (str): 設定するチャンネル. "r" or "g" or "b" or "a"
            drag (bool): ドラッグ中なら True ､確定時なら False を指定する｡
        """
        # スライダーの値取得
        if channel == "r":
            v = ui.get_value(self.fs_red)

        if channel == "g":
            v = ui.get_value(self.fs_green)

        if channel == "b":
            v = ui.get_value(self.fs_blue)

        if channel == "a":
            v = ui.get_value(self.fs_alpha)

        selection = cmds.ls(selection=True)

        if selection:
            # ソフト有効ならコンポーネント毎に色計算､無効なら単色を設定する｡
            # 頂点カラーの変更はドラッグ中は API を使用し､確定時は cmds を使用する｡
            if cmds.softSelect(q=True, softSelectEnabled=True) and not cmds.selectMode(q=True, object=True):
                mode = "mul" if ui.is_alt() else "copy"

                if drag:
                    self._blend_color(self.vf_color_caches, channel, v, mode=mode, via_api=True)

                else:
                    self._blend_color(self.vf_color_caches, channel, v, mode=mode, via_api=False)

            else:
                if drag:
                    self._set_unified_color(selection, channel, v, via_api=True)

                else:
                    self._set_unified_color(selection, channel, v, via_api=False)

    def onSetColorR(self, *args):
        """[R] ボタン押下時のハンドラ｡現在のスライダー値で値を設定する"""
        self._on_set_color(channel="r", drag=False)

    def onSetColorG(self, *args):
        """[G] ボタン押下時のハンドラ｡現在のスライダー値で値を設定する"""
        self._on_set_color(channel="g", drag=False)

    def onSetColorB(self, *args):
        """[B] ボタン押下時のハンドラ｡現在のスライダー値で値を設定する"""
        self._on_set_color(channel="b", drag=False)

    def onSetColorA(self, *args):
        """[A] ボタン押下時のハンドラ｡現在のスライダー値で値を設定する"""
        self._on_set_color(channel="a", drag=False)

    def onSetColorR000(self, *args):
        """R を 0.00 に設定する"""
        v = 0.0
        ui.set_value(self.fs_red, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="r", drag=False)

    def onSetColorR025(self, *args):
        """R を 0.25 に設定する"""
        v = 0.25
        ui.set_value(self.fs_red, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="r", drag=False)

    def onSetColorR050(self, *args):
        """R を 0.50 に設定する"""
        v = 0.5
        ui.set_value(self.fs_red, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="r", drag=False)

    def onSetColorR075(self, *args):
        """R を 0.75 に設定する"""
        v = 0.75
        ui.set_value(self.fs_red, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="r", drag=False)

    def onSetColorR100(self, *args):
        """R を 1.00 に設定する"""
        v = 1.0
        ui.set_value(self.fs_red, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="r", drag=False)

    def onSetColorG000(self, *args):
        """G を 0.00 に設定する"""
        v = 0.0
        ui.set_value(self.fs_green, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="g", drag=False)

    def onSetColorG025(self, *args):
        """G を 0.25 に設定する"""
        v = 0.25
        ui.set_value(self.fs_green, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="g", drag=False)

    def onSetColorG050(self, *args):
        """G を 0.50 に設定する"""
        v = 0.5
        ui.set_value(self.fs_green, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="g", drag=False)

    def onSetColorG075(self, *args):
        """G を 0.75 に設定する"""
        v = 0.75
        ui.set_value(self.fs_green, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="g", drag=False)

    def onSetColorG100(self, *args):
        """G を 1.00 に設定する"""
        v = 1.0
        ui.set_value(self.fs_green, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="g", drag=False)

    def onSetColorB000(self, *args):
        """B を 0.00 に設定する"""
        v = 0.0
        ui.set_value(self.fs_blue, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="b", drag=False)

    def onSetColorB025(self, *args):
        """B を 0.25 に設定する"""
        v = 0.25
        ui.set_value(self.fs_blue, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="b", drag=False)

    def onSetColorB050(self, *args):
        """B を 0.50 に設定する"""
        v = 0.5
        ui.set_value(self.fs_blue, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="b", drag=False)

    def onSetColorB075(self, *args):
        """B を 0.75 に設定する"""
        v = 0.75
        ui.set_value(self.fs_blue, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="b", drag=False)

    def onSetColorB100(self, *args):
        """B を 1.00 に設定する"""
        v = 1.0
        ui.set_value(self.fs_blue, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="b", drag=False)

    def onSetColorA000(self, *args):
        """A を 0.00 に設定する"""
        v = 0.0
        ui.set_value(self.fs_alpha, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="a", drag=False)

    def onSetColorA025(self, *args):
        """A を 0.25 に設定する"""
        v = 0.25
        ui.set_value(self.fs_alpha, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="a", drag=False)

    def onSetColorA050(self, *args):
        """A を 0.50 に設定する"""
        v = 0.5
        ui.set_value(self.fs_alpha, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="a", drag=False)

    def onSetColorA075(self, *args):
        """A を 0.75 に設定する"""
        v = 0.75
        ui.set_value(self.fs_alpha, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="a", drag=False)

    def onSetColorA100(self, *args):
        """A を 1.00 に設定する"""
        v = 1.0
        ui.set_value(self.fs_alpha, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self._on_set_color(channel="a", drag=False)

    def _sync_slider_and_editbox(self, from_slider=False, from_editbox=False):
        """スライダーとエディットボックスの内容を同期する｡

        Args:
            from_slider (bool, optional): スライダーの値をエディットボックスへ反映する. Defaults to False.
            from_editbox (bool, optional): エディットボックスの値をスライダーにスライダーに反映する. Defaults to False.
        """

        if from_slider and from_editbox:
            raise InvalidArgumentCombinationError("Set either from_slider or from_editbox to True.")

        # スライダーを元にエディットボックスを変更
        if from_slider:
            v = ui.get_value(self.fs_red)
            ui.set_value(self.eb_red, v)

            v = ui.get_value(self.fs_green)
            ui.set_value(self.eb_green, v)

            v = ui.get_value(self.fs_blue)
            ui.set_value(self.eb_blue, v)

            v = ui.get_value(self.fs_alpha)
            ui.set_value(self.eb_alpha, v)

        # エディットボックスを元にスライダーを変更
        if from_editbox:
            v = ui.get_value(self.eb_red)
            ui.set_value(self.fs_red, v)

            v = ui.get_value(self.eb_green)
            ui.set_value(self.fs_green, v)

            v = ui.get_value(self.eb_blue)
            ui.set_value(self.fs_blue, v)

            v = ui.get_value(self.eb_alpha)
            ui.set_value(self.fs_alpha, v)

    def _on_drag_editbox(self, channel):
        """エディットボックスのスライド時の処理"""
        # エディットボックスの値をスライダーの値に反映させてスライダードラッグ時の関数を呼ぶ
        self._sync_slider_and_editbox(from_editbox=True)
        self._on_drag_slider(channel=channel)

    def onDragEditBoxRed(self, *args):
        """Red エディットボックスのスライド操作"""
        self._on_drag_editbox(channel="r")

    def onDragEditBoxGreen(self, *args):
        """Green エディットボックスのスライド操作"""
        self._on_drag_editbox(channel="g")

    def onDragEditBoxBlue(self, *args):
        """Blue エディットボックスのスライド操作"""
        self._on_drag_editbox(channel="b")

    def onDragEditBoxAlpha(self, *args):
        """Alpha エディットボックスのスライド操作"""
        self._on_drag_editbox(channel="a")

    def _on_change_editbox(self, channel):
        """エディットボックス確定時の処理 (Ctrl スライド含む) """
        self._sync_slider_and_editbox(from_editbox=True)
        self._on_set_color(channel=channel, drag=False)
        self._close_chunk()

    def onChangeEditBoxRed(self, *args):
        """Red エディットボックス確定時のハンドラ"""
        self._on_change_editbox(channel="r")

    def onChangeEditBoxGreen(self, *args):
        """Green エディットボックス確定時のハンドラ"""
        self._on_change_editbox(channel="g")

    def onChangeEditBoxBlue(self, *args):
        """Blue エディットボックス確定時のハンドラ"""
        self._on_change_editbox(channel="b")

    def onChangeEditBoxAlpha(self, *args):
        """Alpha エディットボックス確定時のハンドラ"""
        self._on_change_editbox(channel="a")

    def _on_drag_slider(self, channel):
        """スライダードラッグ中の処理"""
        selection = cmds.ls(selection=True)

        if selection:
            # スライド開始時の処理
            if not self.is_chunk_open:
                # チャンクのオープン
                cmds.undoInfo(openChunk=True)
                self.is_chunk_open = True

                # スライド開始時の頂点カラーをキャッシュ
                obj_names = cmds.polyListComponentConversion(selection)
                for obj_name in obj_names:
                    full_path = cmds.ls(obj_name, long=True)[0]
                    self.vf_color_caches[full_path] = get_all_vertex_colors(full_path)

            # b キー押し下げでソフト選択半径変更モードにする
            b_down = ui.is_key_pressed(ui.vk.VK_B)

            if channel == "r":
                current_v = ui.get_value(self.fs_red)
            elif channel == "g":
                current_v = ui.get_value(self.fs_green)
            elif channel == "b":
                current_v = ui.get_value(self.fs_blue)
            elif channel == "a":
                current_v = ui.get_value(self.fs_alpha)
            else:
                pass

            if b_down and not self.brush_size_mode:
                # 押し下げ時
                self.brush_size_mode = True
                self.cached_value = current_v
                self.cached_size = cmds.softSelect(q=True, ssd=True)
                self.start_pos = get_cursor_pos()

            elif b_down and self.brush_size_mode:
                # 押し下げ継続時
                mul = 0.1
                lower_limit = 0.0001
                new_size = (self.start_pos[1] - get_cursor_pos()[1]) * mul
                new_size = max(new_size, lower_limit)
                cmds.softSelect(ssd=new_size)

                # スライドで動いた分を戻す
                if channel == "r":
                    current_v = ui.set_value(self.fs_red, value=self.cached_value)
                elif channel == "g":
                    current_v = ui.set_value(self.fs_green, value=self.cached_value)
                elif channel == "b":
                    current_v = ui.set_value(self.fs_blue, value=self.cached_value)
                elif channel == "a":
                    current_v = ui.set_value(self.fs_alpha, value=self.cached_value)
                else:
                    pass

            elif not b_down and self.brush_size_mode:
                # 押し上げ時
                self.brush_size_mode = False

            else:
                pass


            self._on_set_color(channel=channel, drag=True)

        self._sync_slider_and_editbox(from_slider=True)

    def onDragRed(self, *args):
        """R スライダードラッグ中のハンドラ"""
        self._on_drag_slider(channel="r")

    def onDragGreen(self, *args):
        """G スライダードラッグ中のハンドラ"""
        self._on_drag_slider(channel="g")

    def onDragBlue(self, *args):
        """B スライダードラッグ中のハンドラ"""
        self._on_drag_slider(channel="b")

    def onDragAlpha(self, *args):
        """A スライダードラッグ中のハンドラ"""
        self._on_drag_slider(channel="a")

    def _on_change_slider(self, channel):
        """スライダー確定時の処理"""
        selection = cmds.ls(selection=True)

        if selection:
            # Undo 用の API を使用しない確定処理
            self._on_set_color(channel=channel, drag=False)

        # キャッシュの削除とチャンクのクローズ
        self.vf_color_caches = dict()
        self._close_chunk()

    def onChangeSliderRed(self, *args):
        """ R スライダー確定時のハンドラ"""
        self._on_change_slider(channel="r")

    def onChangeSliderGreen(self, *args):
        """ G スライダー確定時のハンドラ"""
        self._on_change_slider(channel="g")

    def onChangeSliderBlue(self, *args):
        """ B スライダー確定時のハンドラ"""
        self._on_change_slider(channel="b")

    def onChangeSliderAlpha(self, *args):
        """ A スライダー確定時のハンドラ"""
        self._on_change_slider(channel="a")

    def _close_chunk(self):
        """チャンクのクローズ処理"""
        if self.is_chunk_open:
            cmds.undoInfo(closeChunk=True)
            self.is_chunk_open = False


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
