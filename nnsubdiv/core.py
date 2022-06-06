#! python
# coding:utf-8

# ダイアログのテンプレ
# self.window だけユニークならあとはそのままで良い
import re
import os
import sys
import traceback

import maya.cmds as cmds
import maya.mel as mel
import pymel.core as pm
import pymel.core.nodetypes as nt

import nnutil
import nnutil.ui as ui


window_name = "NN_Subdiv"
window = None


def get_window():
    return window


window_width = 300
header_width = 50
color_x = (1.0, 0.5, 0.5)
color_y = (0.5, 1.0, 0.5)
color_z = (0.5, 0.5, 1.0)
color_joint = (0.5, 1.0, 0.75)
color_select = (0.5, 0.75, 1.0)
bw_single = 24
bw_double = bw_single*2 + 2
bw_triple = bw_single*3 + 4


class NN_ToolWindow(object):

    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (window_width, 95)

        pm.selectPref(trackSelectionOrder=True)

    def create(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)
        self.window = cmds.window(
            self.window,
            t=self.title,
            widthHeight=self.size
        )
        self.layout()
        cmds.showWindow()

    def layout(self):
        self.columnLayout = cmds.columnLayout()

        # クリース
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=16)
        self.label1 = cmds.text( label='Crease', width=header_width)
        self.buttonA = cmds.button(l='2.0', c=self.onSetCrease20, width=bw_single)
        self.buttonA = cmds.button(l='1.5', c=self.onSetCrease15, width=bw_single)
        self.buttonA = cmds.button(l='1.0', c=self.onSetCrease10, width=bw_single)
        self.buttonA = cmds.button(l='0.5', c=self.onSetCrease05, width=bw_single)
        self.buttonA = cmds.button(l='0', c=self.onSetCrease00, width=bw_single)
        self.buttonA = cmds.button(l='CreaseSet', c=self.onCreaseSetEditor, width=bw_double)
        cmds.setParent("..")

        # ベベル
        self.rowLayout1 = cmds.rowLayout( numberOfColumns=16 )
        self.label1 = cmds.text( label='Bevel' ,width=header_width)
        self.buttonA = cmds.button(l='0.01', c=self.onSetBevel001, width=bw_single)
        self.buttonA = cmds.button(l='0.05', c=self.onSetBevel005, width=bw_single)
        self.buttonA = cmds.button(l='0.1', c=self.onSetBevel010, width=bw_single)
        self.buttonA = cmds.button(l='0.15', c=self.onSetBevel015, width=bw_single)
        self.buttonA = cmds.button(l='0.2', c=self.onSetBevel020, width=bw_single)
        self.buttonA = cmds.button(l='Op', c=self.onBevelOptions, width=bw_single)
        cmds.setParent("..")    

        self.rowLayout1 = cmds.rowLayout( numberOfColumns=16 )
        self.label1 = cmds.text( label='' ,width=header_width)
        self.label1 = cmds.text( label='x', width=bw_single)
        self.bevel_multiplier = cmds.floatField(v=1.0, width=bw_double)
        self.bevel_parallel = cmds.checkBox(l='parallel', v=False, cc=self.onChangeBevelParallel)
        self.bevel_chamfer = cmds.checkBox(l='chamfer', v=False, cc=self.onChangeBevelChamfer)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        # シュリンクラップ
        self.rowLayout1 = cmds.rowLayout( numberOfColumns=16 )
        self.label1 = cmds.text( label='Shrinkwrap' ,width=header_width)
        self.buttonA = cmds.button(l='obj', c=self.onShrinkwrapForObject, width=bw_single)
        self.buttonA = cmds.button(l='set', c=self.onShrinkwrapForSet, width=bw_single)
        self.buttonA = cmds.button(l='Op', c=self.onShrinkwrapOptions, width=bw_single)
        cmds.setParent("..")

        # マージ
        self.rowLayout1 = cmds.rowLayout( numberOfColumns=16 )
        self.label1 = cmds.text( label='Merge' ,width=header_width)
        self.buttonA = cmds.button(l='center', c=self.onMergeCenter, width=bw_double)
        self.buttonA = cmds.button(l='last', c=self.onMergeLast, width=bw_double)
        self.buttonA = cmds.button(l='range', c=self.onMergeRange, width=bw_double)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        # 設定
        # subdiv レベル設定
        self.rowLayout1 = cmds.rowLayout( numberOfColumns=16 )
        self.label1 = cmds.text( label='setLv' ,width=header_width)
        self.buttonA = cmds.button(l='-1', c=self.onDecLevel, width=bw_single)
        self.buttonA = cmds.button(l='=2', c=self.onSetLevel2, width=bw_single)
        self.buttonA = cmds.button(l='+1', c=self.onIncLevel, width=bw_single)
        cmds.setParent("..")

        # UVスムース設定
        self.rowLayout1 = cmds.rowLayout( numberOfColumns=16 )
        self.label1 = cmds.text( label='smooth UV' ,width=header_width)
        self.buttonA = cmds.button(l='none', c=self.onUVSmoothNone, width=bw_double)
        self.buttonA = cmds.button(l='internal', c=self.onUVSmoothInternal, width=bw_double)
        self.buttonA = cmds.button(l='all', c=self.onUVSmoothAll, width=bw_double)
        cmds.setParent("..")

        cmds.separator(width=window_width)

        # 補助機能
        self.rowLayout1 = cmds.rowLayout( numberOfColumns=16 )
        self.label1 = cmds.text( label='func', width=header_width)
        self.buttonA = cmds.button(l='EdgeRing', c=self.onEdgeRing, width=bw_triple)
        self.buttonA = cmds.button(l='Straighten', c=self.onStraighten, width=bw_triple)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout( numberOfColumns=16 )
        self.label1 = cmds.text( label='', width=header_width)
        self.buttonA = cmds.button(l='sel crease', c=self.onSelectCrease, width=bw_triple)
        self.buttonA = cmds.button(l='crease from vtx', c=self.onCreaseFromVertex, width=bw_triple)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout( numberOfColumns=16 )
        self.label1 = cmds.text( label='', width=header_width)
        self.buttonA = cmds.button(l='remove digon', c=self.onRemoveDigon, width=bw_triple)
        self.buttonA = cmds.button(l="wrap", c=self.onCreateWrap, width=bw_triple)
        cmds.setParent("..")


    # イベントハンドラ

    def onSetCrease20(self, *args):
        pm.polyCrease(ch=True, value=2.0, vertexValue=2.0)

    def onSetCrease15(self, *args):
        pm.polyCrease(ch=True, value=1.5, vertexValue=1.5)

    def onSetCrease10(self, *args):
        pm.polyCrease(ch=True, value=1.0, vertexValue=1.0)

    def onSetCrease05(self, *args):
        pm.polyCrease(ch=True, value=0.5, vertexValue=0.5)

    def onSetCrease00(self, *args):
        pm.polyCrease(ch=True, value=0.0, vertexValue=0.0)

    def onCreaseSetEditor(self, *args):
        try:
            mel.eval("OpenCreaseEditor")
        except:
            from maya.app.general import creaseSetEditor
            creaseSetEditor.showCreaseSetEditor()

    def do_bevel(self, offset, force_parallel, chamfer):
        pm.polyBevel3(offset=offset, offsetAsFraction=0, autoFit=1, forceParallel=force_parallel, depth=1, mitering=0, miterAlong=0, chamfer=chamfer, segments=1, worldSpace=1, smoothingAngle=30, subdivideNgons=1, mergeVertices=1, mergeVertexTolerance=0.0001, miteringAngle=180, angleTolerance=180, ch=1)

    # ベベル
    def onSetBevel001(self, *args):
        multiplier = cmds.floatField(self.bevel_multiplier, q=True, v=True)
        offset = 0.01 * multiplier
        force_parallel = cmds.checkBox(self.bevel_parallel, q=True, v=True)
        chamfer = cmds.checkBox(self.bevel_chamfer, q=True, v=True)
        self.do_bevel(offset, force_parallel, chamfer)

    def onSetBevel005(self, *args):
        multiplier = cmds.floatField(self.bevel_multiplier, q=True, v=True)
        offset = 0.05 * multiplier
        force_parallel = cmds.checkBox(self.bevel_parallel, q=True, v=True)
        chamfer = cmds.checkBox(self.bevel_chamfer, q=True, v=True)
        self.do_bevel(offset, force_parallel, chamfer)

    def onSetBevel010(self, *args):
        multiplier = cmds.floatField(self.bevel_multiplier, q=True, v=True)
        offset = 0.10 * multiplier
        force_parallel = cmds.checkBox(self.bevel_parallel, q=True, v=True)
        chamfer = cmds.checkBox(self.bevel_chamfer, q=True, v=True)
        self.do_bevel(offset, force_parallel, chamfer)

    def onSetBevel015(self, *args):
        multiplier = cmds.floatField(self.bevel_multiplier, q=True, v=True)
        offset = 0.15 * multiplier
        force_parallel = cmds.checkBox(self.bevel_parallel, q=True, v=True)
        chamfer = cmds.checkBox(self.bevel_chamfer, q=True, v=True)
        self.do_bevel(offset, force_parallel, chamfer)

    def onSetBevel020(self, *args):
        multiplier = cmds.floatField(self.bevel_multiplier, q=True, v=True)
        offset = 0.20 * multiplier
        force_parallel = cmds.checkBox(self.bevel_parallel, q=True, v=True)
        chamfer = cmds.checkBox(self.bevel_chamfer, q=True, v=True)
        self.do_bevel(offset, force_parallel, chamfer)

    def onBevelOptions(self, *args):
        mel.eval("BevelPolygonOptions")

    def onChangeBevelParallel(self, *args):
        pass

    def onChangeBevelChamfer(self, *args):
        pass

    # シュリンクラップ
    def onShrinkwrapForObject(self, *args):
        mel.eval("CreateShrinkWrap")

    def onShrinkwrapForSet(self, *args):
        nnutil.shrinkwrap_for_set()

    def onShrinkwrapOptions(self, *args):
        mel.eval("CreateShrinkWrapOptions")

    # マージ
    def onMergeCenter(self, *args):
        mel.eval("polyMergeToCenter")

    def onMergeLast(self, *args):
        nnutil.merge_to_last()

    def onMergeRange(self, *args):
        r = pm.softSelect(q=True, ssd=True)
        selections = [x for x in pm.selected(flatten=True) if type(x) == pm.MeshVertex]
        nnutil.merge_in_range(selections, r=r, connected=True)

    # 補助
    # 二角形ホール処理
    def onRemoveDigon(self, *args):
        nnutil.remove_digon_holes_from_objects()

    def onEdgeRing(self, *args):
        import align_edgering_length
        align_edgering_length.main()

    def onStraighten(self, *args):
        import nnstraighten
        nnstraighten.main()

    def onCreateWrap(self, *args):
        mel.eval("CreateWrap")

    def onSelectCrease(self, *args):
        """ Select creased edges that are not in a Crease Set """
        selections = cmds.ls(sl=True, l=True)
        edges = cmds.filterExpand(cmds.polyListComponentConversion(selections, te=True), sm=32, expand=True)

        creased_edges = []

        for edge in edges:
            edgeValue = cmds.polyCrease(edge, query=True, value=True)
            if edgeValue[0] > 0:
                creased_edges.append(edge)

        cmds.select(creased_edges)

    # 押し出し側面のクリース
    def onCreaseFromVertex(self, *args):
        vertices = [x for x in pm.selected(flatten=True) if type(x) == pm.MeshVertex]

        for v in vertices:
            print(v)
            value = pm.polyCrease(v, query=True, vertexValue=True)

            if not value == 0:
                edges = v.connectedEdges()
                shortest_edge = sorted(edges, key=lambda x: x.getLength())[0]
                pm.polyCrease(shortest_edge, value=value)

    # 設定
    # subdiv レベル設定
    def onSetLevel2(self, *args):
        for obj in pm.ls(selection=True, flatten=True):
            lv = 2
            cmds.setAttr(obj.name() + ".smoothLevel", lv)

    def onIncLevel(self, *args):
        for obj in pm.ls(selection=True, flatten=True): 
            lv = cmds.getAttr(obj.name() + ".smoothLevel")
            cmds.setAttr(obj.name() + ".smoothLevel", lv+1)

    def onDecLevel(self, *args):
        for obj in pm.ls(selection=True, flatten=True): 
            lv = cmds.getAttr(obj.name() + ".smoothLevel")
            cmds.setAttr(obj.name() + ".smoothLevel", lv-1)

    # UVスムース設定
    def onUVSmoothNone(self, *args):
        for obj in pm.ls(selection=True, flatten=True): 
            shape_name = obj.getShape().name()
            pm.setAttr(shape_name + ".useGlobalSmoothDrawType", 0)
            pm.setAttr(shape_name + ".smoothDrawType", 0)
            pm.setAttr(shape_name + ".smoothUVs", 1)
            pm.setAttr(shape_name + ".keepMapBorders", 2)

    def onUVSmoothInternal(self, *args):
        for obj in pm.ls(selection=True, flatten=True): 
            shape_name = obj.getShape().name()
            pm.setAttr(shape_name + ".useGlobalSmoothDrawType", 0)
            pm.setAttr(shape_name + ".smoothDrawType", 0)
            pm.setAttr(shape_name + ".smoothUVs", 1)
            pm.setAttr(shape_name + ".keepMapBorders", 1)

    def onUVSmoothAll(self, *args):
        for obj in pm.ls(selection=True, flatten=True): 
            shape_name = obj.getShape().name()
            pm.setAttr(shape_name + ".useGlobalSmoothDrawType", 0)
            pm.setAttr(shape_name + ".smoothDrawType", 0)
            pm.setAttr(shape_name + ".smoothUVs", 1)
            pm.setAttr(shape_name + ".keepMapBorders", 0)
            
        
def showNNToolWindow():
    NN_ToolWindow().create()

def main():
    showNNToolWindow()

if __name__ == "__main__":
    main()