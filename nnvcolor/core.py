#! python
# coding:utf-8
"""頂点カラーツール"""
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import nnutil.display as nd


def get_all_vertex_colors(obj_name):
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
        self.size = (251, 220)

        self.is_chunk_open = False

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
        ui.column_layout()

        ui.row_layout()
        ui.button(label="RGBA", c=self.onSetColorRGBA, dgc=self.onGetColorRGBA)
        ui.button(label="Create Set [Op]", c=self.onCreateColorSet, dgc=self.onColorSetEditor, width=ui.width(3.75))
        ui.button(label="Toggle Disp", c=self.onToggleDisplay, width=ui.width(3.75))
        ui.end_layout()

        ui.separator(width=1, height=5)

        ui.row_layout()
        ui.button(label="R", c=self.onSetColorR, dgc=self.onGetColorR, width=ui.header_width)
        ui.button(label="0.00", c=self.onSetColorR000, bgc=(0, 0, 0), width=ui.width1_5)
        ui.button(label="0.25", c=self.onSetColorR025, bgc=(0.25, 0, 0), width=ui.width1_5)
        ui.button(label="0.50", c=self.onSetColorR050, bgc=(0.5, 0, 0), width=ui.width1_5)
        ui.button(label="0.75", c=self.onSetColorR075, bgc=(0.75, 0, 0), width=ui.width1_5)
        ui.button(label="1.00", c=self.onSetColorR100, bgc=(1.0, 0, 0), width=ui.width1_5)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        self.fs_red = ui.float_slider(min=0, max=1.0, value=1.0, width=ui.width(7.5), dc=self.onDragRed, cc=self.onCloseChunk)
        ui.end_layout()

        ui.separator(width=1, height=5)

        ui.row_layout()
        ui.button(label="G", c=self.onSetColorG, dgc=self.onGetColorG, width=ui.header_width)
        ui.button(label="0.00", c=self.onSetColorG000, bgc=(0, 0, 0), width=ui.width1_5)
        ui.button(label="0.25", c=self.onSetColorG025, bgc=(0, 0.25, 0), width=ui.width1_5)
        ui.button(label="0.50", c=self.onSetColorG050, bgc=(0, 0.5, 0), width=ui.width1_5)
        ui.button(label="0.75", c=self.onSetColorG075, bgc=(0, 0.75, 0), width=ui.width1_5)
        ui.button(label="1.00", c=self.onSetColorG100, bgc=(0, 1.0, 0), width=ui.width1_5)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        self.fs_green = ui.float_slider(min=0, max=1.0, value=1.0, width=ui.width(7.5), dc=self.onDragGreen, cc=self.onCloseChunk)
        ui.end_layout()

        ui.separator(width=1, height=5)

        ui.row_layout()
        ui.button(label="B", c=self.onSetColorB, dgc=self.onGetColorB, width=ui.header_width)
        ui.button(label="0.00", c=self.onSetColorB000, bgc=(0, 0, 0), width=ui.width1_5)
        ui.button(label="0.25", c=self.onSetColorB025, bgc=(0, 0, 0.25), width=ui.width1_5)
        ui.button(label="0.50", c=self.onSetColorB050, bgc=(0, 0, 0.5), width=ui.width1_5)
        ui.button(label="0.75", c=self.onSetColorB075, bgc=(0, 0, 0.75), width=ui.width1_5)
        ui.button(label="1.00", c=self.onSetColorB100, bgc=(0, 0, 1.0), width=ui.width1_5)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        self.fs_blue = ui.float_slider(min=0, max=1.0, value=1.0, width=ui.width(7.5), dc=self.onDragBlue, cc=self.onCloseChunk)
        ui.end_layout()

        ui.separator(width=1, height=5)

        ui.row_layout()
        ui.button(label="A", c=self.onSetColorA, dgc=self.onGetColorA, width=ui.header_width)
        ui.button(label="0.00", c=self.onSetColorA000, bgc=(0, 0, 0), width=ui.width1_5)
        ui.button(label="0.25", c=self.onSetColorA025, bgc=(0.25, 0.25, 0.25), width=ui.width1_5)
        ui.button(label="0.50", c=self.onSetColorA050, bgc=(0.5, 0.5, 0.5), width=ui.width1_5)
        ui.button(label="0.75", c=self.onSetColorA075, bgc=(0.75, 0.75, 0.75), width=ui.width1_5)
        ui.button(label="1.00", c=self.onSetColorA100, bgc=(1.0, 1.0, 1.0), width=ui.width1_5)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
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

        color_components = cmds.polyColorPerVertex(q=True, r=True, g=True, b=True, a=True)

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

    def onGetColorG(self, *args):
        """選択している全ての頂点の頂点カラーの平均の G 成分をスライダーに設定する"""
        color = self._get_color()

        if color:
            ui.set_value(self.fs_green, value=color[1])

    def onGetColorB(self, *args):
        """選択している全ての頂点の頂点カラーの平均の B 成分をスライダーに設定する"""
        color = self._get_color()

        if color:
            ui.set_value(self.fs_blue, value=color[2])

    def onGetColorA(self, *args):
        """選択している全ての頂点の頂点カラーの平均の A 成分をスライダーに設定する"""
        color = self._get_color()

        if color:
            ui.set_value(self.fs_alpha, value=color[3])

    def onSetColorR(self, *args):
        """R をスライダーの値に設定する"""
        v = ui.get_value(self.fs_red)
        selection = cmds.ls(selection=True)

        if selection:
            if cmds.selectType(q=True, polymeshUV=True):
                selection = cmds.polyListComponentConversion(selection, tvf=True)
            elif cmds.selectType(q=True, edge=True):
                selection = cmds.polyListComponentConversion(selection, tv=True)

            objects = cmds.polyListComponentConversion(selection)
            stored_colors = store_colors(objects)
            cmds.polyColorPerVertex(selection, r=v)
            restore_colors(objects, stored_colors, r=False, g=True, b=True, a=True)

    def onSetColorG(self, *args):
        """G をスライダーの値に設定する"""
        v = ui.get_value(self.fs_green)
        selection = cmds.ls(selection=True)

        if selection:
            if cmds.selectType(q=True, polymeshUV=True):
                selection = cmds.polyListComponentConversion(selection, tvf=True)
            elif cmds.selectType(q=True, edge=True):
                selection = cmds.polyListComponentConversion(selection, tv=True)

            objects = cmds.polyListComponentConversion(selection)
            stored_colors = store_colors(objects)
            cmds.polyColorPerVertex(selection, g=v)
            restore_colors(objects, stored_colors, r=True, g=False, b=True, a=True)

    def onSetColorB(self, *args):
        """B をスライダーの値に設定する"""
        v = ui.get_value(self.fs_blue)
        selection = cmds.ls(selection=True)

        if selection:
            if cmds.selectType(q=True, polymeshUV=True):
                selection = cmds.polyListComponentConversion(selection, tvf=True)
            elif cmds.selectType(q=True, edge=True):
                selection = cmds.polyListComponentConversion(selection, tv=True)

            objects = cmds.polyListComponentConversion(selection)
            stored_colors = store_colors(objects)
            cmds.polyColorPerVertex(selection, b=v)
            restore_colors(objects, stored_colors, r=True, g=True, b=False, a=True)

    def onSetColorA(self, *args):
        """A をスライダーの値に設定する"""
        v = ui.get_value(self.fs_alpha)
        selection = cmds.ls(selection=True)

        if selection:
            if cmds.selectType(q=True, polymeshUV=True):
                selection = cmds.polyListComponentConversion(selection, tvf=True)
            elif cmds.selectType(q=True, edge=True):
                selection = cmds.polyListComponentConversion(selection, tv=True)

            objects = cmds.polyListComponentConversion(selection)
            stored_colors = store_colors(objects)
            cmds.polyColorPerVertex(selection, a=v)
            restore_colors(objects, stored_colors, r=True, g=True, b=True, a=False)

    def onSetColorR000(self, *args):
        """R を 0.00 に設定する"""
        v = 0.0
        ui.set_value(self.fs_red, value=v)
        self.onSetColorR()

    def onSetColorR025(self, *args):
        """R を 0.25 に設定する"""
        v = 0.25
        ui.set_value(self.fs_red, value=v)
        self.onSetColorR()

    def onSetColorR050(self, *args):
        """R を 0.50 に設定する"""
        v = 0.5
        ui.set_value(self.fs_red, value=v)
        self.onSetColorR()

    def onSetColorR075(self, *args):
        """R を 0.75 に設定する"""
        v = 0.75
        ui.set_value(self.fs_red, value=v)
        self.onSetColorR()

    def onSetColorR100(self, *args):
        """R を 1.00 に設定する"""
        v = 1.0
        ui.set_value(self.fs_red, value=v)
        self.onSetColorR()

    def onSetColorG000(self, *args):
        """G を 0.00 に設定する"""
        v = 0.0
        ui.set_value(self.fs_green, value=v)
        self.onSetColorG()

    def onSetColorG025(self, *args):
        """G を 0.25 に設定する"""
        v = 0.25
        ui.set_value(self.fs_green, value=v)
        self.onSetColorG()

    def onSetColorG050(self, *args):
        """G を 0.50 に設定する"""
        v = 0.5
        ui.set_value(self.fs_green, value=v)
        self.onSetColorG()

    def onSetColorG075(self, *args):
        """G を 0.75 に設定する"""
        v = 0.75
        ui.set_value(self.fs_green, value=v)
        self.onSetColorG()

    def onSetColorG100(self, *args):
        """G を 1.00 に設定する"""
        v = 1.0
        ui.set_value(self.fs_green, value=v)
        self.onSetColorG()

    def onSetColorB000(self, *args):
        """B を 0.00 に設定する"""
        v = 0.0
        ui.set_value(self.fs_blue, value=v)
        self.onSetColorB()

    def onSetColorB025(self, *args):
        """B を 0.25 に設定する"""
        v = 0.25
        ui.set_value(self.fs_blue, value=v)
        self.onSetColorB()

    def onSetColorB050(self, *args):
        """B を 0.50 に設定する"""
        v = 0.5
        ui.set_value(self.fs_blue, value=v)
        self.onSetColorB()

    def onSetColorB075(self, *args):
        """B を 0.75 に設定する"""
        v = 0.75
        ui.set_value(self.fs_blue, value=v)
        self.onSetColorB()

    def onSetColorB100(self, *args):
        """B を 1.00 に設定する"""
        v = 1.0
        ui.set_value(self.fs_blue, value=v)
        self.onSetColorB()

    def onSetColorA000(self, *args):
        """A を 0.00 に設定する"""
        v = 0.0
        ui.set_value(self.fs_alpha, value=v)
        self.onSetColorA()

    def onSetColorA025(self, *args):
        """A を 0.25 に設定する"""
        v = 0.25
        ui.set_value(self.fs_alpha, value=v)
        self.onSetColorA()

    def onSetColorA050(self, *args):
        """A を 0.50 に設定する"""
        v = 0.5
        ui.set_value(self.fs_alpha, value=v)
        self.onSetColorA()

    def onSetColorA075(self, *args):
        """A を 0.75 に設定する"""
        v = 0.75
        ui.set_value(self.fs_alpha, value=v)
        self.onSetColorA()

    def onSetColorA100(self, *args):
        """A を 1.00 に設定する"""
        v = 1.0
        ui.set_value(self.fs_alpha, value=v)
        self.onSetColorA()

    def onDragRed(self, *args):
        """R ドラッグ中の処理"""
        selection = cmds.ls(selection=True)        

        if selection:
            if not self.is_chunk_open:
                cmds.undoInfo(openChunk=True)
                self.is_chunk_open = True

            self.onSetColorR()

    def onDragGreen(self, *args):
        """G ドラッグ中の処理"""
        selection = cmds.ls(selection=True)        

        if selection:
            if not self.is_chunk_open:
                cmds.undoInfo(openChunk=True)
                self.is_chunk_open = True

            self.onSetColorG()

    def onDragBlue(self, *args):
        """B ドラッグ中の処理"""
        selection = cmds.ls(selection=True)        

        if selection:
            if not self.is_chunk_open:
                cmds.undoInfo(openChunk=True)
                self.is_chunk_open = True

            self.onSetColorB()

    def onDragAlpha(self, *args):
        """A ドラッグ中の処理"""
        selection = cmds.ls(selection=True)        

        if selection:
            if not self.is_chunk_open:
                cmds.undoInfo(openChunk=True)
                self.is_chunk_open = True

            self.onSetColorA()

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
