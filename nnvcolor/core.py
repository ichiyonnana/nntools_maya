#! python
# coding:utf-8
"""頂点カラーツール"""
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

import nnutil.ui as ui


class InvalidArgumentCombinationError(Exception):
    """引数の値の組み合わせが不正な場合の例外｡"""
    pass


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
        self.fs_red = ui.float_slider(min=0, max=1.0, value=1.0, width=ui.width(7.5), height=row_height2, dc=self.onDragRed, cc=self.onCloseChunk)
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
        self.fs_green = ui.float_slider(min=0, max=1.0, value=1.0, width=ui.width(7.5), dc=self.onDragGreen, cc=self.onCloseChunk)
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
        self.fs_blue = ui.float_slider(min=0, max=1.0, value=1.0, width=ui.width(7.5), dc=self.onDragBlue, cc=self.onCloseChunk)
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
        self.fs_alpha = ui.float_slider(min=0, max=1.0, value=1.0, width=ui.width(7.5), dc=self.onDragAlpha, cc=self.onCloseChunk)
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

    @staticmethod
    def _set_unified_color_via_cmds(targets, channel, value):
        """指定頂点カラーに同一値を設定する｡最終的な設定は cmds経由で Undo 可能｡同一色での塗りつぶし1回なので早い｡

        Args:
            targets (list[str]): 対象コンポーネント
            channel (str): 上書きするチャンネル
            value (float): 上書きする値
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

    @staticmethod
    def _set_each_colors_via_cmds(targets, colors, channels):
        """頂点カラーそれぞれに指定した値を設定する｡最終的な設定は cmds経由で Undo 可能｡コンポーネント反復するので遅い｡

        Args:
            targets (list[str]): 対象コンポーネント
            channel (str): 上書きするチャンネル
            value (float): 上書きする値
        """
        for i in range(len(targets)):
            if channels == 4:
                r, g, b, a = (colors + [0])[i*channels:(i+1)*channels]
                cmds.polyColorPerVertex(targets[i], r=r, g=g, b=b, a=a)

            elif channels == 3:
                r, g, b, a = (colors + [0])[i*channels:(i+1)*channels]
                cmds.polyColorPerVertex(targets[i], r=r, g=g, b=b)

            else:
                pass

    @staticmethod
    def _set_each_colors_via_api(target_indices, colors):
        """頂点カラーを設定する｡最終的な設定は API 経由で Undo 不可｡早いがあくまで一時的な表示用"""
        set_all_vertex_colors

        if cmds.softSelect(q=True, softSelectEnabled=True):
            # MRichSeleciton オブジェクト構築
            rich_selection = om.MGlobal.getRichSelection()
            slist = rich_selection.getSelection()
            slist_sym = rich_selection.getSymmetry()

            # オブジェクト毎の処理
            for sl in [slist, slist_sym]:
                for i in range(sl.length()):
                    obj, comp = sl.getComponent(i)
                    fn_comp = om.MFnSingleIndexedComponent(comp)
                    selected_vi = fn_comp.getElements()

                    fn_mesh = om.MFnMesh(obj)

                    for i in range(len(selected_vi)):
                        vi = selected_vi[i]
                        w = fn_comp.weight(i).influence
                        name = obj.fullPathName()
                        cmds.polyColorPerVertex(name + ".vtx[%s]" % vi, r=1.0-w)

    def onSetColorR(self, *args):
        """R をスライダーの値に設定する"""
        v = ui.get_value(self.fs_red)
        selection = cmds.ls(selection=True)

        self._set_unified_color_via_cmds(selection, "r", v)

    def onSetColorG(self, *args):
        """G をスライダーの値に設定する"""
        v = ui.get_value(self.fs_green)
        selection = cmds.ls(selection=True)

        self._set_unified_color_via_cmds(selection, "g", v)

    def onSetColorB(self, *args):
        """B をスライダーの値に設定する"""
        v = ui.get_value(self.fs_blue)
        selection = cmds.ls(selection=True)

        self._set_unified_color_via_cmds(selection, "b", v)

    def onSetColorA(self, *args):
        """A をスライダーの値に設定する"""
        v = ui.get_value(self.fs_alpha)
        selection = cmds.ls(selection=True)

        self._set_unified_color_via_cmds(selection, "a", v)

    def onSetColorR000(self, *args):
        """R を 0.00 に設定する"""
        v = 0.0
        ui.set_value(self.fs_red, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorR()

    def onSetColorR025(self, *args):
        """R を 0.25 に設定する"""
        v = 0.25
        ui.set_value(self.fs_red, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorR()

    def onSetColorR050(self, *args):
        """R を 0.50 に設定する"""
        v = 0.5
        ui.set_value(self.fs_red, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorR()

    def onSetColorR075(self, *args):
        """R を 0.75 に設定する"""
        v = 0.75
        ui.set_value(self.fs_red, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorR()

    def onSetColorR100(self, *args):
        """R を 1.00 に設定する"""
        v = 1.0
        ui.set_value(self.fs_red, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorR()

    def onSetColorG000(self, *args):
        """G を 0.00 に設定する"""
        v = 0.0
        ui.set_value(self.fs_green, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorG()

    def onSetColorG025(self, *args):
        """G を 0.25 に設定する"""
        v = 0.25
        ui.set_value(self.fs_green, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorG()

    def onSetColorG050(self, *args):
        """G を 0.50 に設定する"""
        v = 0.5
        ui.set_value(self.fs_green, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorG()

    def onSetColorG075(self, *args):
        """G を 0.75 に設定する"""
        v = 0.75
        ui.set_value(self.fs_green, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorG()

    def onSetColorG100(self, *args):
        """G を 1.00 に設定する"""
        v = 1.0
        ui.set_value(self.fs_green, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorG()

    def onSetColorB000(self, *args):
        """B を 0.00 に設定する"""
        v = 0.0
        ui.set_value(self.fs_blue, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorB()

    def onSetColorB025(self, *args):
        """B を 0.25 に設定する"""
        v = 0.25
        ui.set_value(self.fs_blue, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorB()

    def onSetColorB050(self, *args):
        """B を 0.50 に設定する"""
        v = 0.5
        ui.set_value(self.fs_blue, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorB()

    def onSetColorB075(self, *args):
        """B を 0.75 に設定する"""
        v = 0.75
        ui.set_value(self.fs_blue, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorB()

    def onSetColorB100(self, *args):
        """B を 1.00 に設定する"""
        v = 1.0
        ui.set_value(self.fs_blue, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorB()

    def onSetColorA000(self, *args):
        """A を 0.00 に設定する"""
        v = 0.0
        ui.set_value(self.fs_alpha, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorA()

    def onSetColorA025(self, *args):
        """A を 0.25 に設定する"""
        v = 0.25
        ui.set_value(self.fs_alpha, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorA()

    def onSetColorA050(self, *args):
        """A を 0.50 に設定する"""
        v = 0.5
        ui.set_value(self.fs_alpha, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorA()

    def onSetColorA075(self, *args):
        """A を 0.75 に設定する"""
        v = 0.75
        ui.set_value(self.fs_alpha, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorA()

    def onSetColorA100(self, *args):
        """A を 1.00 に設定する"""
        v = 1.0
        ui.set_value(self.fs_alpha, value=v)
        self._sync_slider_and_editbox(from_slider=True)
        self.onSetColorA()

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

    def onDragEditBoxRed(self, *args):
        """Red エディットボックスのスライド操作"""
        self._sync_slider_and_editbox(from_editbox=True)
        self.onDragRed()

    def onDragEditBoxGreen(self, *args):
        """Green エディットボックスのスライド操作"""
        self._sync_slider_and_editbox(from_editbox=True)
        self.onDragGreen()

    def onDragEditBoxBlue(self, *args):
        """Blue エディットボックスのスライド操作"""
        self._sync_slider_and_editbox(from_editbox=True)
        self.onDragBlue()

    def onDragEditBoxAlpha(self, *args):
        """Alpha エディットボックスのスライド操作"""
        self._sync_slider_and_editbox(from_editbox=True)
        self.onDragAlpha()

    def onChangeEditBoxRed(self, *args):
        """Red エディットボックスの確定操作"""
        self._sync_slider_and_editbox(from_editbox=True)
        self.onSetColorR()
        self.onCloseChunk()

    def onChangeEditBoxGreen(self, *args):
        """Green エディットボックスの確定操作"""
        self._sync_slider_and_editbox(from_editbox=True)
        self.onSetColorG()
        self.onCloseChunk()

    def onChangeEditBoxBlue(self, *args):
        """Blue エディットボックスの確定操作"""
        self._sync_slider_and_editbox(from_editbox=True)
        self.onSetColorB()
        self.onCloseChunk()

    def onChangeEditBoxAlpha(self, *args):
        """Alpha エディットボックスの確定操作"""
        self._sync_slider_and_editbox(from_editbox=True)
        self.onSetColorA()
        self.onCloseChunk()

    def onDragRed(self, *args):
        """R スライダードラッグ中の処理"""
        selection = cmds.ls(selection=True)

        if selection:
            if not self.is_chunk_open:
                cmds.undoInfo(openChunk=True)
                self.is_chunk_open = True

            self.onSetColorR()

        self._sync_slider_and_editbox(from_slider=True)

    def onDragGreen(self, *args):
        """G スライダードラッグ中の処理"""
        selection = cmds.ls(selection=True)

        if selection:
            if not self.is_chunk_open:
                cmds.undoInfo(openChunk=True)
                self.is_chunk_open = True

            self.onSetColorG()

        self._sync_slider_and_editbox(from_slider=True)

    def onDragBlue(self, *args):
        """B スライダードラッグ中の処理"""
        selection = cmds.ls(selection=True)

        if selection:
            if not self.is_chunk_open:
                cmds.undoInfo(openChunk=True)
                self.is_chunk_open = True

            self.onSetColorB()

        self._sync_slider_and_editbox(from_slider=True)

    def onDragAlpha(self, *args):
        """A スライダードラッグ中の処理"""
        selection = cmds.ls(selection=True)

        if selection:
            if not self.is_chunk_open:
                cmds.undoInfo(openChunk=True)
                self.is_chunk_open = True

            self.onSetColorA()

        self._sync_slider_and_editbox(from_slider=True)

    def onCloseChunk(self, *args):
        """スライダー確定時の処理｡ Undo チャンクを閉じる｡"""
        if self.is_chunk_open:
            cmds.undoInfo(closeChunk=True)
            self.is_chunk_open = False


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
