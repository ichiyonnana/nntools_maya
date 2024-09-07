# ダイアログのテンプレ
# self.window だけユニークならあとはそのままで良い
import re
import os
import sys
import traceback
import math

import pymel.core as pm
import maya.cmds as cmds
import maya.mel as mel

import nnutil.core as nu


window_name = "NN_Straighten"
window = None


def get_window():
    return window


window_width = 200
header_width = 50
color_x = (1.0, 0.5, 0.5)
color_y = (0.5, 1.0, 0.5)
color_z = (0.5, 0.5, 1.0)
color_joint = (0.5, 1.0, 0.75)
color_select = (0.5, 0.75, 1.0)
bw_single = 24
bw_double = bw_single*2 + 2

def straight_component(vts):
    """
    選択頂点がつながっていればパスの端の点、つながっていなければ最も遠い点で直線にする
    """
    pass

def flatten_component(vts_dst, points_dst, vts_src):
    """
    vts_dst/points_dst で定義される平面に vts_src を移動させる
    vts_dst はコンポーネント文字列、 points はXYZ座標値のリスト [[x,y,z], [x,y,z], [x,y,z]]
    vts を優先して参照し、len(vts)<3 なら points_dst の先頭から不足分を補う
    """
    pass

def flatten_component_avg(vts):
    """
    vts からそれらしい平面を求めてすべての vts をその平面上に移動させる
    """
    pass


class NN_ToolWindow(object):
    MD_NONE = 0
    MD_LINE = 1
    MD_PLANE = 2

    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (10, 10)

        self.sample_vts = []
        self.sample_points = []
        self.mode = self.MD_NONE

    def create(self):
        if pm.window(self.window, exists=True):
            pm.deleteUI(self.window, window=True)

        # プリファレンスの有無による分岐
        if pm.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = pm.windowPref(self.window, q=True, topLeftCorner=True)
            pm.windowPref(self.window, remove=True)

            # 前回位置に指定したサイズで表示
            pm.window(
                self.window,
                t=self.title,
                maximizeButton=False,
                minimizeButton=False,
                topLeftCorner=position,
                widthHeight=self.size,
                sizeable=False,
                resizeToFitChildren=True
                )

        else:
            # プリファレンスがなければデフォルト位置に指定サイズで表示
            pm.window(
                self.window,
                t=self.title,
                maximizeButton=False,
                minimizeButton=False,
                widthHeight=self.size,
                sizeable=False,
                resizeToFitChildren=True
                )

        self.layout()
        pm.showWindow(self.window)

    def layout(self):
        window_width = 140

        self.columnLayout = cmds.columnLayout()

        self.rowLayout1 = cmds.rowLayout( numberOfColumns=16 )
        self.bt_ = cmds.button(l='Sample [select]', c=self.onSample, dgc=self.onSelectSamplePoint)
        self.bt_ = cmds.button(l='+camera', c=self.onSelectSamplePointFromCamera)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        self.rowLayout1 = cmds.rowLayout( numberOfColumns=16 )
        self.bt_ = cmds.button(l='Apply', c=self.onApply)
        self.bt_ = cmds.button(l='Flatten (Camera)', c=self.onFlattenWithCamera)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        self.rowLayout1 = cmds.rowLayout( numberOfColumns=16 )
        self.bt_ = cmds.button(l='Farthest', c=self.onLinearizeFarthest)
        self.bt_ = cmds.button(l='end-to-end', c=self.onLinearizeEndToEnd)
        cmds.setParent("..")

        cmds.separator(width=window_width)

    def onSample(self, *args):
        selections = nu.get_selection()
        self.sample_vts = nu.to_vtx(selections)
        self.sample_points = [nu.get_vtx_coord(x) for x in self.sample_vts]
        nu.message("sampling %d points" % len(self.sample_vts))

    def onSelectSamplePointFromCamera(self, *args):
        selections = nu.get_selection()
        self.sample_vts = nu.to_vtx(selections)[0:2]
        self.sample_points = [nu.get_vtx_coord(x) for x in self.sample_vts]

        
        camera = nu.get_active_camera()
        camerapos = cmds.xform(camera, q=True, ws=True, t=True)
        self.sample_points.append(camerapos)
        nu.message("sampling 2 points + camera position")


    def onSelectSamplePoint(self, *args):
        cmds.select(self.sample_vts)
        
    def onApply(self, *args):
        vts = nu.to_vtx(nu.get_selection())

        num_samples = len(self.sample_points)
        if num_samples == 0:
            # nop
            nu.message("sample before apply")

        if len(self.sample_vts) == 2:
            # line
            end_vtx_pair =self.sample_vts
            
            fp = [nu.get_vtx_coord(x) for x in end_vtx_pair]

            for v in vts:
                p = nu.get_vtx_coord(v)
                np = nu.nearest_point_on_line(fp[0], fp[1], p)
                nu.set_vtx_coord(v, np)

            nu.message("linearize")

        else:
            # plane
            va = nu.diff(self.sample_points[1], self.sample_points[0])
            vb = nu.diff(self.sample_points[2], self.sample_points[0])
            cross = nu.cross(va, vb)
            p0 = self.sample_points[0]
            # 平面方程式の係数
            a = cross[0]    
            b = cross[1]
            c = cross[2]
            d = - a*p0[0] - b*p0[1] - c*p0[2]

            for vtx in vts:
                p = nu.get_vtx_coord(vtx)  # 平面状に乗せる頂点 P の座標
                # 外積ベクトルに平行かつ P を通る直線を媒介変数表示 (x + at, y+bt, z+ct) した式を P の座標で計算した際の t の値
                t0 = -(a*p[0] + b*p[1] + c*p[2] + d) / (a*a + b*b + c*c)
                # 媒介変数表示の成分を平面方程式に代入して求めた Q の座標
                q = (a*t0 + p[0], b*t0 + p[1], c*t0 + p[2])
                nu.set_vtx_coord(vtx, q)

            nu.message("flatten")

    def onFlattenWithCamera(self, *args):
        """
        代表点2点 + 現在のカメラ位置での平面化
        """

        active_panel = cmds.getPanel(wf=True)
        camera = cmds.modelPanel(active_panel, q=True, camera=True)
        camerapos = cmds.xform(camera, q=True, ws=True, t=True)

        vts = nu.to_vtx(nu.get_selection())

        num_samples = len(self.sample_points)
        if num_samples == 0:
            # nop
            nu.message("sample before apply")

        if len(self.sample_vts) >= 2:
            # plane
            va = nu.diff(self.sample_points[1], self.sample_points[0])
            vb = nu.diff(camerapos, self.sample_points[0])
            cross = nu.cross(va, vb)
            p0 = self.sample_points[0]
            # 平面方程式の係数
            a = cross[0]
            b = cross[1]
            c = cross[2]
            d = - a*p0[0] - b*p0[1] - c*p0[2]

            for vtx in vts:
                p = nu.get_vtx_coord(vtx)
                t0 = -(a*p[0] + b*p[1] + c*p[2] + d) / (a*a + b*b + c*c)
                q = (a*t0 + p[0], b*t0 + p[1], c*t0 + p[2])
                nu.set_vtx_coord(vtx, q)

            nu.message("flatten with camera")




        
    def onLinearizeFarthest(self, *args):
        """
        選択頂点群の中から一番離れた頂点同士を代表点として直線化
        トポロジーを考慮せず連続している必要は無し
        """
        vts = nu.to_vtx(nu.get_selection())
        end_vtx_pair = nu.get_most_distant_vts(vts)
        fp = [nu.get_vtx_coord(x) for x in end_vtx_pair]

        for v in vts:
            p = nu.get_vtx_coord(v)
            np = nu.nearest_point_on_line(fp[0], fp[1], p)
            nu.set_vtx_coord(v, np)


    def onLinearizeEndToEnd(self, *args):
        """
        選択頂点群/エッジ群の端となる頂点同士を代表点として直線化
        トポロジーを考慮し、連続エッジでつながる区間の終端を代表点とする
        """
        selections = nu.get_selection()
        end_vtx_pair = []
        vts = []

        if all([nu.type_of_component(x) == "edge" for x in selections]):
            end_vtx_pair = nu.get_end_vtx_e(selections)
            vts = nu.to_vtx(selections)

        elif all([nu.type_of_component(x) == "vtx" for x in selections]):
           end_vtx_pair = nu.get_end_vtx_v(selections)
           vts = selections

        fp = [nu.get_vtx_coord(x) for x in end_vtx_pair]

        for v in vts:
            p = nu.get_vtx_coord(v)
            np = nu.nearest_point_on_line(fp[0], fp[1], p)
            nu.set_vtx_coord(v, np)



def showNNToolWindow():
    NN_ToolWindow().create()

def main():
    showNNToolWindow()

if __name__ == "__main__":
    main()