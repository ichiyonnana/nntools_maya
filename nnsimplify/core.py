#! python
# coding:utf-8

"""

"""
import math

import maya.cmds as cmds
import pymel.core as pm
# import pymel.core.datatypes as dt
# import pymel.core.nodetypes as nt

import nnutil.core as nu
import nnutil.curve as nc
import nnutil.ui as ui
import nnutil.display as nd


window_name = "NN_Simplify"
window = None


def get_window():
    return window


window_width = 240
header_width = 50

equalize_span = 16
smooth_span = 16


@nu.no_warning
def simplify_edges(edges=None, span=4, keep_ratio=True):
    """ 指定した連続エッジの形状を簡略化する

    Args:
        edges: 簡略化対象のエッジ列
        span: 簡略化に使用するカーブのスパン数｡ 0 で直線､ n で n+2 のスパン数になる
    """
    
    if not edges:
        edges = [x for x in pm.selected(flatten=True) if type(x) == pm.MeshEdge]
    
    if not edges:
        return

    edges_list = nu.get_all_polylines(edges)
    span_f = math.floor(span)
    span_c = math.ceil(span)

    for i, target_edges in enumerate(edges_list):
                
        if span_f == span_c:
            print("fast mode")
            curve1 = nc.make_curve_from_edges(target_edges, n=span_f)
            vertices = nu.sort_vertices(nu.to_vtx(target_edges, pn=True))
            nc.match_direction(curve1, vertices)
            nc.fit_vertices_to_curve(vertices, curve=curve1, keep_ratio=keep_ratio)
            pm.delete(curve1)

        else:
            alpha = math.fmod(span, 1.0)
            curve1 = nc.make_curve_from_edges(target_edges, n=span_f)
            curve2 = nc.make_curve_from_edges(target_edges, n=span_c)
            vertices = nu.sort_vertices(nu.to_vtx(target_edges, pn=True))
            nc.match_direction(curve1, vertices)
            nc.match_direction(curve2, vertices)
            nc.fit_vertices_to_curve_lerp(vertices, curve1=curve1, curve2=curve2, alpha=alpha, keep_ratio=keep_ratio)
            pm.delete(curve1)
            pm.delete(curve2)

    print("finish")


@nu.no_warning
def smooth_edges(edges=None, span=4, smooth=1, keep_ratio=True):
    """ 指定した連続エッジの形状を平滑化する

    Args:
        edges: 平滑化対象のエッジ列
        span: 簡略化に使用するカーブのスパン数｡ 0 で直線､ n で n+2 のスパン数になる
        smooth: スムースの反復回数
    """
    if not edges:
        edges = [x for x in pm.selected(flatten=True) if type(x) == pm.MeshEdge]
    
    if not edges:
        return

    edges_list = nu.get_all_polylines(edges)

    for i, target_edges in enumerate(edges_list):
        print("%s/%s" % (i, len(edges_list)))
        curve = nc.make_curve_from_edges(target_edges, n=span)
        cv_str = curve.name() + ".cv[*]"
        pm.smoothCurve(cv_str, ch=1, rpo=1, s=smooth)
        vertices = nu.sort_vertices(nu.to_vtx(target_edges, pn=True))
        nc.match_direction(curve, vertices)
        nc.fit_vertices_to_curve(vertices, curve, keep_ratio=keep_ratio)
        pm.delete(curve)

    pm.select(edges, replace=True)
    print("finish")


@nu.no_warning
def equalize_edges(edges=None, multiplier=1.0):
    """ 指定したエッジの間隔を均一にする

    Argas:
        edges (list[MeshEdge]): 均一化対象のエッジ列
        multiplier (float, optinal): エッジ長の比率の指数
    """
    if not edges:
        edges = [x for x in pm.selected(flatten=True) if type(x) == pm.MeshEdge]

    if not edges:
        return
        
    span = equalize_span

    edges_list = nu.get_all_polylines(edges)

    for i, edges in enumerate(edges_list):
        print("%s/%s" % (i, len(edges_list)))
        curve = nc.make_curve_from_edges(edges, n=span)
        vertices = nu.sort_vertices(nu.to_vtx(edges, pn=True))
        nc.match_direction(curve, vertices)
        nc.fit_vertices_to_curve(vertices, curve, keep_ratio=False, multiplier=multiplier)        
        pm.delete(curve)
        
    print("finish")


class NN_ToolWindow(object):

    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (window_width, 80)

        pm.selectPref(trackSelectionOrder=True)

        self.last_simplify_span = 4.0
        self.max_smooth = 100

    def create(self):
        if pm.window(self.window, exists=True):
            pm.deleteUI(self.window, window=True)

        # プリファレンスの有無による分岐
        if pm.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = pm.windowPref(self.window, q=True, topLeftCorner=True)
            pm.windowPref(self.window, remove=True)

            # 前回位置に指定したサイズで表示
            pm.window(self.window, t=self.title, maximizeButton=False, minimizeButton=False, topLeftCorner=position, widthHeight=self.size, sizeable=False)

        else:
            # プリファレンスがなければデフォルト位置に指定サイズで表示
            pm.window(self.window, t=self.title, maximizeButton=False, minimizeButton=False, widthHeight=self.size, sizeable=False)

        self.layout()
        pm.showWindow(self.window)

    def layout(self):
        ui.column_layout()

        ui.row_layout()
        ui.button(label="Simplify", c=self.onSimplify)
        self.simplify_slider = ui.float_slider(min=0, max=8, value=self.last_simplify_span, step=1,
                                               dc=self.onUpdateSimplifySlider, cc=self.onChangeSimplifySlider, width=ui.button_width5)
        self.simplify_label = ui.text(label=self.last_simplify_span, width=ui.button_width2)
        ui.end_layout()

        ui.row_layout()
        ui.button(label="Smooth", c=self.onSmooth)
        self.smooth_slider = ui.float_slider(min=0, max=self.max_smooth, value=self.max_smooth/2, step=1, 
                                             dc=self.onUpdateSmoothSlider, cc=self.onChangeSmoothSlider, width=ui.button_width5)
        self.smooth_label = ui.text(label=str(self.max_smooth/2), width=ui.button_width2)
        ui.end_layout()

        ui.row_layout()
        ui.button(label="Equalize", c=self.onEqualize, dgc=self.onEqualizeReverse)
        self.equalize_slider = ui.float_slider(min=0.5, max=1.0, value=1.0, step=0.1, 
                                               dc=self.onUpdateEqualizeSlider, cc=self.onChangeEqualizeSlider, width=ui.button_width5)
        self.equalize_label = ui.text(label=1.0, width=ui.button_width2)
        ui.end_layout()

        ui.end_layout()

    @nu.undo_chunk
    def onSimplify(self, *args):
        """ Simplify の実行 """
        span = ui.get_value(self.simplify_slider)
        simplify_edges(edges=None, span=span)
        self.last_simplify_span = span

    @nu.undo_chunk
    def onSmooth(self, *args):
        """ Smooth の実行 """
        span = smooth_span
        smooth = ui.get_value(self.smooth_slider)
        smooth_edges(edges=None, span=span, smooth=smooth)

    @nu.undo_chunk
    def onEqualize(self, *args):
        """ エッジ間隔の均一化 """
        multiplier = ui.get_value(self.equalize_slider)
        equalize_edges(multiplier=multiplier)

    @nu.undo_chunk
    def onEqualizeReverse(self, *args):
        """ エッジ間隔の均一化 """
        multiplier = ui.get_value(self.equalize_slider)
        equalize_edges(multiplier=1/multiplier)

    def updateLabel(self, *args): 
        """ 現在のスライダーの値でラベルを更新 """
        v = ui.get_value(self.simplify_slider)
        v = round(v, 1)
        ui.set_value(self.simplify_label, value=v)

        v = ui.get_value(self.smooth_slider)
        v = round(v, 1)
        ui.set_value(self.smooth_label, value=v)

        v = ui.get_value(self.equalize_slider)
        v = round(v, 3)
        ui.set_value(self.equalize_label, value=v)

    def onUpdateSimplifySlider(self, *args):
        """ Simplify スライダーの変更 (ドラッグ中) """
        # Shift 押下時はきりの良い数値にする
        mods = pm.getModifiers()

        if mods & 1:
            v = ui.get_value(self.simplify_slider)
            ui.set_value(self.simplify_slider, round(v, 0))
            
        self.updateLabel()

    def onChangeSimplifySlider(self, *args):
        """ Simplify スライダーの変更 (リリース時) """
        self.updateLabel()

    def onUpdateSmoothSlider(self, *args):
        """ Smooth スライダーの変更 (ドラッグ中) """
        # Shift 押下時はきりの良い数値にする
        mods = pm.getModifiers()

        if mods & 1:
            v = ui.get_value(self.smooth_slider)
            ui.set_value(self.smooth_slider, round(v, 0))

        self.updateLabel()

    def onChangeSmoothSlider(self, *args):
        """ Smooth スライダーの変更 (リリース時) """
        self.updateLabel()

    def onUpdateEqualizeSlider(self, *args):
        """ Equalize スライダーの変更 (ドラッグ中) """
        # Shift 押下時はきりの良い数値にする
        mods = pm.getModifiers()

        if mods & 1:
            v = ui.get_value(self.equalize_slider)
            ui.set_value(self.equalize_slider, round(v, 1))

        self.updateLabel()

    def onChangeEqualizeSlider(self, *args):
        """ Equalize スライダーの変更 (リリース時) """
        self.updateLabel()


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
