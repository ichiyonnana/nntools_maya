#! python
# coding:utf-8

"""

"""
import maya.cmds as cmds
import pymel.core as pm
import maya.mel as mel

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import nnutil.display as nd


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
        if pm.window(self.window, exists=True):
            pm.deleteUI(self.window, window=True)

        # プリファレンスの有無による分岐
        if pm.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = pm.windowPref(self.window, q=True, topLeftCorner=True)
            pm.windowPref(self.window, remove=True)

            pm.window(self.window, t=self.title, maximizeButton=False, minimizeButton=False, topLeftCorner=position, widthHeight=self.size, sizeable=False)

        else:
            # プリファレンスがなければデフォルト位置に指定サイズで表示
            pm.window(self.window, t=self.title, maximizeButton=False, minimizeButton=False, widthHeight=self.size, sizeable=False)

        self.layout()
        pm.showWindow(self.window)

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

        if not pm.selected():
            return None

        color_components = pm.polyColorPerVertex(q=True, r=True, g=True, b=True, a=True)

        if color_components:
            r_list = [color_components[4*i+0] for i in range(len(color_components)/4)]
            g_list = [color_components[4*i+1] for i in range(len(color_components)/4)]
            b_list = [color_components[4*i+2] for i in range(len(color_components)/4)]
            a_list = [color_components[4*i+3] for i in range(len(color_components)/4)]
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
        pm.polyColorSet(create=True, clamped=0, rpt="RGBA", colorSet="colorSet")

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
        if pm.selected():
            r = ui.get_value(self.fs_red)
            g = ui.get_value(self.fs_green)
            b = ui.get_value(self.fs_blue)
            a = ui.get_value(self.fs_alpha)
            pm.polyColorPerVertex(r=r, g=g, b=b, a=a)

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

        if pm.selected():
            pm.polyColorPerVertex(r=v)

    def onSetColorG(self, *args):
        """G をスライダーの値に設定する"""
        v = ui.get_value(self.fs_green)

        if pm.selected():
            pm.polyColorPerVertex(g=v)

    def onSetColorB(self, *args):
        """B をスライダーの値に設定する"""
        v = ui.get_value(self.fs_blue)

        if pm.selected():
            pm.polyColorPerVertex(b=v)

    def onSetColorA(self, *args):
        """A をスライダーの値に設定する"""
        v = ui.get_value(self.fs_alpha)

        if pm.selected():
            pm.polyColorPerVertex(a=v)

    def onSetColorR000(self, *args):
        """R を 0.00 に設定する"""
        v = 0.0
        ui.set_value(self.fs_red, value=v)

        if pm.selected():
            pm.polyColorPerVertex(r=v)

    def onSetColorR025(self, *args):
        """R を 0.25 に設定する"""
        v = 0.25
        ui.set_value(self.fs_red, value=v)

        if pm.selected():
            pm.polyColorPerVertex(r=v)

    def onSetColorR050(self, *args):
        """R を 0.50 に設定する"""
        v = 0.5
        ui.set_value(self.fs_red, value=v)

        if pm.selected():
            pm.polyColorPerVertex(r=v)

    def onSetColorR075(self, *args):
        """R を 0.75 に設定する"""
        v = 0.75
        ui.set_value(self.fs_red, value=v)

        if pm.selected():
            pm.polyColorPerVertex(r=v)

    def onSetColorR100(self, *args):
        """R を 1.00 に設定する"""
        v = 1.0
        ui.set_value(self.fs_red, value=v)

        if pm.selected():
            pm.polyColorPerVertex(r=v)

    def onSetColorG000(self, *args):
        """G を 0.00 に設定する"""
        v = 0.0
        ui.set_value(self.fs_green, value=v)

        if pm.selected():
            pm.polyColorPerVertex(g=v)

    def onSetColorG025(self, *args):
        """G を 0.25 に設定する"""
        v = 0.25
        ui.set_value(self.fs_green, value=v)

        if pm.selected():
            pm.polyColorPerVertex(g=v)

    def onSetColorG050(self, *args):
        """G を 0.50 に設定する"""
        v = 0.5
        ui.set_value(self.fs_green, value=v)

        if pm.selected():
            pm.polyColorPerVertex(g=v)

    def onSetColorG075(self, *args):
        """G を 0.75 に設定する"""
        v = 0.75
        ui.set_value(self.fs_green, value=v)

        if pm.selected():
            pm.polyColorPerVertex(g=v)

    def onSetColorG100(self, *args):
        """G を 1.00 に設定する"""
        v = 1.0
        ui.set_value(self.fs_green, value=v)

        if pm.selected():
            pm.polyColorPerVertex(g=v)

    def onSetColorB000(self, *args):
        """B を 0.00 に設定する"""
        v = 0.0
        ui.set_value(self.fs_blue, value=v)

        if pm.selected():
            pm.polyColorPerVertex(b=v)

    def onSetColorB025(self, *args):
        """B を 0.25 に設定する"""
        v = 0.25
        ui.set_value(self.fs_blue, value=v)

        if pm.selected():
            pm.polyColorPerVertex(b=v)

    def onSetColorB050(self, *args):
        """B を 0.50 に設定する"""
        v = 0.5
        ui.set_value(self.fs_blue, value=v)

        if pm.selected():
            pm.polyColorPerVertex(b=v)

    def onSetColorB075(self, *args):
        """B を 0.75 に設定する"""
        v = 0.75
        ui.set_value(self.fs_blue, value=v)

        if pm.selected():
            pm.polyColorPerVertex(b=v)

    def onSetColorB100(self, *args):
        """B を 1.00 に設定する"""
        v = 1.0
        ui.set_value(self.fs_blue, value=v)

        if pm.selected():
            pm.polyColorPerVertex(b=v)

    def onSetColorA000(self, *args):
        """A を 0.00 に設定する"""
        v = 0.0
        ui.set_value(self.fs_alpha, value=v)

        if pm.selected():
            pm.polyColorPerVertex(a=v)

    def onSetColorA025(self, *args):
        """A を 0.25 に設定する"""
        v = 0.25
        ui.set_value(self.fs_alpha, value=v)

        if pm.selected():
            pm.polyColorPerVertex(a=v)

    def onSetColorA050(self, *args):
        """A を 0.50 に設定する"""
        v = 0.5
        ui.set_value(self.fs_alpha, value=v)

        if pm.selected():
            pm.polyColorPerVertex(a=v)

    def onSetColorA075(self, *args):
        """A を 0.75 に設定する"""
        v = 0.75
        ui.set_value(self.fs_alpha, value=v)

        if pm.selected():
            pm.polyColorPerVertex(a=v)

    def onSetColorA100(self, *args):
        """A を 1.00 に設定する"""
        v = 1.0
        ui.set_value(self.fs_alpha, value=v)

        if pm.selected():
            pm.polyColorPerVertex(a=v)

    def onDragRed(self, *args):
        if pm.selected():
            if not self.is_chunk_open:
                pm.undoInfo(openChunk=True)
                self.is_chunk_open = True

            v = ui.get_value(self.fs_red)
            pm.polyColorPerVertex(r=v)

    def onDragGreen(self, *args):
        if pm.selected():
            if not self.is_chunk_open:
                pm.undoInfo(openChunk=True)
                self.is_chunk_open = True

            v = ui.get_value(self.fs_green)
            pm.polyColorPerVertex(g=v)

    def onDragBlue(self, *args):
        if pm.selected():
            if not self.is_chunk_open:
                pm.undoInfo(openChunk=True)
                self.is_chunk_open = True

            v = ui.get_value(self.fs_blue)
            pm.polyColorPerVertex(b=v)

    def onDragAlpha(self, *args):
        if pm.selected():
            if not self.is_chunk_open:
                pm.undoInfo(openChunk=True)
                self.is_chunk_open = True

            v = ui.get_value(self.fs_alpha)
            pm.polyColorPerVertex(a=v)

    def onCloseChunk(self, *args):
        if self.is_chunk_open:
            pm.undoInfo(closeChunk=True)
            self.is_chunk_open = False


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
