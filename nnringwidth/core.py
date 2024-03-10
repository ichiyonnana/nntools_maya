# coding:utf-8
# エッジのリスト選択して実行すると片側固定して幅を統一するやつ
import maya.cmds as cmds
import pymel.core as pm
import math

import nnutil.ui as ui


window_name = "NN_RingWidth"
window = None


def get_window():
    return window


# vertex から point 取得
def pointFromVertex(vtx):
    return cmds.xform(vtx, q=True, ws=True, t=True)


def distance(p1, p2):
    return math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2 + (p2[2]-p1[2])**2)


def vector(p1, p2):
    return (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])


# ベクトルの正規化
def normalize(v):
    norm = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
    if norm != 0:
        return (v[0]/norm, v[1]/norm, v[2]/norm)
    else:
        return (0, 0, 0)


class NN_AlignedgeRingWindow(object):
    MSG_NOT_SELECTED = "エッジが選択されていません"
    MSG_UNK_ALIGNMODE = "未知の整列モードです"
    MSG_UNK_RELMODE = "未知の相対モードです"
    MSG_NOT_IMPLEMENTED = "未実装"

    AM_IN = 1           # 内側基準
    AM_OUT = 2          # 外側基準
    AM_CENTER = 3       # 中央基準
    last_executed_func = None  # 最後に実行した Align メソッド
    last_executed_mode = None  # 最後に実行した Align モード
    last_relative_mode = False  # 最後に実行したアラインの相対モード

    # 相対モード
    RM_ADD = 1
    RM_DIFF = 2
    RM_MUL = 3
    RM_DIV = 4

    selEdges = []        # 前回実行時の選択エッジ
    sortedSelEdges = []  # 前回実行時の選択エッジ (ソート済)
    vtxListA = []        # 最後に更新された sortedSelEdges 集合の片側の頂点オブジェクト列
    vtxListB = []        # 最後に更新された sortedSelEdges 集合の片側の頂点オブジェクト列
    pntListA = []        # 最後に更新された sortedSelEdges 集合の片側の頂点座標列
    pntListB = []        # 最後に更新された sortedSelEdges 集合の片側の頂点座標列
    preserveAngle = True  # もとのエッジの角度を維持するならTrue

    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (10, 10)

        self.absolute_mode_components = []
        self.relative_mode_components = []

    def create(self):
        if pm.window(self.window, exists=True):
            pm.deleteUI(self.window, window=True)

        # プリファレンスの有無による分岐
        if pm.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = pm.windowPref(self.window, q=True, topLeftCorner=True)
            pm.windowPref(self.window, remove=True)

            # 前回位置に指定したサイズで表示
            pm.window(self.window, t=self.title, maximizeButton=False, minimizeButton=False, topLeftCorner=position, widthHeight=self.size, sizeable=False, resizeToFitChildren=True)

        else:
            # プリファレンスがなければデフォルト位置に指定サイズで表示
            pm.window(self.window, t=self.title, maximizeButton=False, minimizeButton=False, widthHeight=self.size, sizeable=False, resizeToFitChildren=True)

        self.layout()
        pm.showWindow(self.window)

    def layout(self):
        window_width = 260

        ui.column_layout()

        # 絶対モード
        ui.row_layout()
        ui.header(label="Absolute")
        ui.end_layout()

        ui.row_layout()
        ui.header(label='width1:')
        ui.button(label='-', c=self.onDecreaseLength1)
        self.field_length1 = ui.eb_float(v=0.1, dc=self.onChangeLength1)
        ui.button(label='+', c=self.onIncreaseLength1)
        ui.button(label='swap', c=self.onSwapLength)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='width2:')
        ui.button(label='-', c=self.onDecreaseLength2)
        self.field_length2 = ui.eb_float(v=0.1, en=False, dc=self.onChangeLength2)
        ui.button(label='+', c=self.onIncreaseLength2)
        self.constMode = ui.check_box(label='const', v=True, cc=self.onSetConst)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Align")
        ui.button(label='In', c=self.onAlignInAbsolute)
        ui.button(label='Center', c=self.onAlignCenterAbsolute)
        ui.button(label='Out', c=self.onAlignOutAbsolute)
        ui.end_layout()

        ui.separator(width=window_width)

        # 相対モード
        ui.row_layout()
        ui.header(label="Relative")
        ui.end_layout()

        ui.row_layout()
        ui.header(label="mul")
        ui.button(label='-10%', c=self.onRelativeDiv_90, width=ui.width(1.5))
        ui.button(label='-1%', c=self.onRelativeDiv_99, width=ui.width(1.5))
        self.ff_acc_mul = ui.eb_float(v=1)
        ui.button(label='+1%', c=self.onRelativeMul_1, width=ui.width(1.5))
        ui.button(label='+10%', c=self.onRelativeMul_10, width=ui.width(1.5))
        ui.end_layout()

        ui.row_layout()
        ui.header(label="add")
        ui.button(label='-0.1', c=self.onRelativeDiff_10, width=ui.width(1.5))
        ui.button(label='-0.01', c=self.onRelativeDiff_1, width=ui.width(1.5))
        self.ff_acc_add = ui.eb_float(v=0)
        ui.button(label='+0.01', c=self.onRelativeAdd_1, width=ui.width(1.5))
        ui.button(label='+0.1', c=self.onRelativeAdd_10, width=ui.width(1.5))
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Align")
        ui.button(label='In', c=self.onAlignInRelative)
        ui.button(label='Center', c=self.onAlignCenterRelative)
        ui.button(label='Out', c=self.onAlignOutRelative)
        ui.end_layout()

        ui.separator(width=window_width)

        # 取得系
        ui.row_layout()
        ui.header(label='Get from ')
        ui.button(label='First', c=self.onSetLengthFromFirstEdge)
        ui.button(label='Last', c=self.onSetLengthFromLastEdge)
        ui.button(label='Mode', c=self.onSetLengthFromMode)
        ui.button(label='Path', c=self.onSetLengthFromEdgePath)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='Min', c=self.onSetLengthFromMin)
        ui.button(label='Max', c=self.onSetLengthFromMax)
        ui.button(label='Average', c=self.onSetLengthFromAverage)
        ui.end_layout()

        ui.separator(width=window_width)

        # その他機能
        ui.row_layout()
        ui.header(label='')
        ui.button(label='Reset', c=self.onReset)
        ui.button(label='ClearCache', c=self.onClearCache)
        ui.button(label='Smooth', c=self.onSmoothAngle)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.check_box(label="Hilite Inner", v=False, cc=self.onHiliteInner)
        ui.end_layout()

        ui.separator(width=window_width)

        ui.end_layout()

    def onChangeLength1(self, *args):
        """値変更時のハンドラ"""
        self.update()

    def onChangeLength2(self, *args):
        self.update()

    def onIncreaseLength1(self, *args):
        """絶対モードの幅1を増加させる"""
        currentLength = cmds.floatField(self.field_length1, q=True, v=True)
        newLength = currentLength * 1.1
        cmds.floatField(self.field_length1, e=True, v=newLength)
        self.update()

    def onIncreaseLength2(self, *args):
        """絶対モードの幅1を増加させる"""
        currentLength = cmds.floatField(self.field_length2, q=True, v=True)
        newLength = currentLength * 1.1
        cmds.floatField(self.field_length2, e=True, v=newLength)
        self.update()

    def onDecreaseLength1(self, *args):
        """絶対モードの幅2を減少させる"""
        currentLength = cmds.floatField(self.field_length1, q=True, v=True)
        newLength = currentLength * 0.9
        cmds.floatField(self.field_length1, e=True, v=newLength)
        self.update()

    def onDecreaseLength2(self, *args):
        """絶対モードの幅2を減少させる"""
        currentLength = cmds.floatField(self.field_length2, q=True, v=True)
        newLength = currentLength * 0.9
        cmds.floatField(self.field_length2, e=True, v=newLength)
        self.update()

    def onSwapLength(self, *args):
        """絶対モードの幅の値を入れ替える"""
        length1 = cmds.floatField(self.field_length1, q=True, v=True)
        length2 = cmds.floatField(self.field_length2, q=True, v=True)
        cmds.floatField(self.field_length1, e=True, v=length2)
        cmds.floatField(self.field_length2, e=True, v=length1)
        self.update()

    def onSetConst(self, *args):
        """等幅モードのチェックボックス変更ハンドラ"""
        constMode = cmds.checkBox(self.constMode, q=True, v=True)

        if constMode:
            cmds.floatField(self.field_length2, e=True, en=False)
        else:
            cmds.floatField(self.field_length2, e=True, en=True)

    def update(self, *args):
        """現在の設定で整列を実行する"""
        if self.last_executed_func:
            self.last_executed_func()

    def onRelativeDiff_1(self, *args):
        """相対モードの加数を減らして実行"""
        current_acc_add = ui.get_value(self.ff_acc_add)
        ui.set_value(self.ff_acc_add, current_acc_add - 0.01)
        self.update()

    def onRelativeDiff_10(self, *args):
        """相対モードの加数を減らして実行"""
        current_acc_add = ui.get_value(self.ff_acc_add)
        ui.set_value(self.ff_acc_add, current_acc_add - 0.1)
        self.update()

    def onRelativeAdd_1(self, *args):
        """相対モードの加数を増やして実行"""
        current_acc_add = ui.get_value(self.ff_acc_add)
        ui.set_value(self.ff_acc_add, current_acc_add + 0.01)
        self.update()

    def onRelativeAdd_10(self, *args):
        """相対モードの加数を増やして実行"""
        current_acc_add = ui.get_value(self.ff_acc_add)
        ui.set_value(self.ff_acc_add, current_acc_add + 0.1)
        self.update()

    def onRelativeDiv_99(self, *args):
        """相対モードの乗数を減らして実行"""
        current_acc_mul = ui.get_value(self.ff_acc_mul)
        ui.set_value(self.ff_acc_mul, current_acc_mul * 0.99)
        self.update()

    def onRelativeDiv_90(self, *args):
        """相対モードの乗数を減らして実行"""
        current_acc_mul = ui.get_value(self.ff_acc_mul)
        ui.set_value(self.ff_acc_mul, current_acc_mul * 0.9)
        self.update()

    def onRelativeMul_1(self, *args):
        """相対モードの乗数を減らして実行"""
        current_acc_mul = ui.get_value(self.ff_acc_mul)
        ui.set_value(self.ff_acc_mul, current_acc_mul * 1.01)
        self.update()

    def onRelativeMul_10(self, *args):
        """相対モードの乗数を減らして実行"""
        current_acc_mul = ui.get_value(self.ff_acc_mul)
        ui.set_value(self.ff_acc_mul, current_acc_mul * 1.1)
        self.update()

    def onSetLengthFromFirstEdge(self, *args):
        """
        選択しているエッジの長さで length フィールドを変更
        最初のエッジの長さのみ使用する
        """

        selEdges = cmds.ls(os=True, fl=True)
        edgeCount = len(selEdges)
        newLength = 0
        if edgeCount != 0:
            v0, v1 = cmds.filterExpand(cmds.polyListComponentConversion(
                selEdges[0], fe=True, tv=True), sm=31)
            p0 = cmds.xform(v0, q=True, ws=True, t=True)
            p1 = cmds.xform(v1, q=True, ws=True, t=True)
            newLength += math.sqrt((p1[0]-p0[0]) **
                                   2 + (p1[1]-p0[1])**2 + (p1[2]-p0[2])**2)
            cmds.floatField(self.field_length1, e=True, v=newLength)
        # self.update()

    def onSetLengthFromLastEdge(self, *args):
        """
        選択しているエッジの長さで length フィールドを変更
        最後のエッジの長さのみ使用する
        """
        selEdges = cmds.ls(os=True, fl=True)
        edgeCount = len(selEdges)
        newLength = 0
        if edgeCount != 0:
            v0, v1 = cmds.filterExpand(cmds.polyListComponentConversion(
                selEdges[-1], fe=True, tv=True), sm=31)
            p0 = cmds.xform(v0, q=True, ws=True, t=True)
            p1 = cmds.xform(v1, q=True, ws=True, t=True)
            newLength += math.sqrt((p1[0]-p0[0]) **
                                   2 + (p1[1]-p0[1])**2 + (p1[2]-p0[2])**2)
            cmds.floatField(self.field_length2, e=True, v=newLength)
        # self.update()

    def onSetLengthFromAverage(self, *args):
        """
        選択しているエッジの長さで length フィールドを変更
        選択されたエッジの長さの平均を使用する
        """
        selEdges = cmds.ls(os=True, fl=True)
        edgeCount = len(selEdges)
        newLength = 0
        for edge in selEdges:
            v0, v1 = cmds.filterExpand(
                cmds.polyListComponentConversion(edge, fe=True, tv=True), sm=31)
            p0 = cmds.xform(v0, q=True, ws=True, t=True)
            p1 = cmds.xform(v1, q=True, ws=True, t=True)
            newLength += math.sqrt((p1[0]-p0[0]) **
                                   2 + (p1[1]-p0[1])**2 + (p1[2]-p0[2])**2)

        if newLength != 0:
            newLength /= edgeCount
            cmds.floatField(self.field_length1, e=True, v=newLength)
            cmds.floatField(self.field_length2, e=True, v=newLength)
        # self.update()

    def onSetLengthFromMin(self, *args):
        """
        選択しているエッジの長さで length フィールドを変更
        一番短いものを使用する
        """
        selEdges = cmds.ls(os=True, fl=True)
        edgeCount = len(selEdges)
        length_list = []

        for edge in selEdges:
            v0, v1 = cmds.filterExpand(
                cmds.polyListComponentConversion(edge, fe=True, tv=True), sm=31)
            p0 = cmds.xform(v0, q=True, ws=True, t=True)
            p1 = cmds.xform(v1, q=True, ws=True, t=True)
            length = math.sqrt((p1[0]-p0[0]) ** 2 + (p1[1]-p0[1])**2 + (p1[2]-p0[2])**2)
            length_list.append(length)

        if len(length_list) != 0:
            new_length = min(length_list)
            cmds.floatField(self.field_length1, e=True, v=new_length)
            cmds.floatField(self.field_length2, e=True, v=new_length)

        # self.update()

    def onSetLengthFromMax(self, *args):
        """
        選択しているエッジの長さで length フィールドを変更
        一番長いものを使用する
        """
        selEdges = cmds.ls(os=True, fl=True)
        edgeCount = len(selEdges)
        length_list = []

        for edge in selEdges:
            v0, v1 = cmds.filterExpand(
                cmds.polyListComponentConversion(edge, fe=True, tv=True), sm=31)
            p0 = cmds.xform(v0, q=True, ws=True, t=True)
            p1 = cmds.xform(v1, q=True, ws=True, t=True)
            length = math.sqrt((p1[0]-p0[0]) ** 2 + (p1[1]-p0[1])**2 + (p1[2]-p0[2])**2)
            length_list.append(length)

        if len(length_list) != 0:
            new_length = max(length_list)
            cmds.floatField(self.field_length1, e=True, v=new_length)
            cmds.floatField(self.field_length2, e=True, v=new_length)

    def onSetLengthFromMode(self, *args):
        """
        選択しているエッジの長さで length フィールドを変更
        選択されたエッジの長さの最頻値を使用する
        """
        selEdges = cmds.ls(os=True, fl=True)
        edgeCount = len(selEdges)
        dictLengthToCount = {}
        if edgeCount != 0:
            for edge in selEdges:
                v0, v1 = cmds.filterExpand(
                    cmds.polyListComponentConversion(edge, fe=True, tv=True), sm=31)
                p0 = cmds.xform(v0, q=True, ws=True, t=True)
                p1 = cmds.xform(v1, q=True, ws=True, t=True)
                length = math.sqrt((p1[0]-p0[0])**2 +
                                   (p1[1]-p0[1])**2 + (p1[2]-p0[2])**2)
                length = round(length, 4)
                if length in dictLengthToCount:
                    dictLengthToCount[length] += 1
                else:
                    dictLengthToCount[length] = 1

            newLength, count = sorted(
                dictLengthToCount.items(), key=lambda x: x[1], reverse=True)[0]
            if count != 1:
                cmds.floatField(self.field_length1, e=True, v=newLength)
                cmds.floatField(self.field_length2, e=True, v=newLength)
            else:
                print("同じ長さのエッジがない")
        # self.update()

    def onSetLengthFromEdgePath(self, *args):
        """
        選択しているエッジの長さで length フィールドを変更
        複数選択されていた場合は全ての長さの和を使用する
        """
        selEdges = cmds.ls(os=True, fl=True)
        newLength = 0
        for edge in selEdges:
            v0, v1 = cmds.filterExpand(
                cmds.polyListComponentConversion(edge, fe=True, tv=True), sm=31)
            p0 = cmds.xform(v0, q=True, ws=True, t=True)
            p1 = cmds.xform(v1, q=True, ws=True, t=True)
            newLength += math.sqrt((p1[0]-p0[0]) **
                                   2 + (p1[1]-p0[1])**2 + (p1[2]-p0[2])**2)

        if newLength != 0:
            cmds.floatField(self.field_length1, e=True, v=newLength)
            cmds.floatField(self.field_length2, e=True, v=newLength)

        # self.update()

    # アラインの実行
    def onAlignInAbsolute(self, *args):
        length1 = cmds.floatField(self.field_length1, q=True, v=True)
        length2 = cmds.floatField(self.field_length2, q=True, v=True)
        mode = self.AM_IN
        relative_mode = False

        if relative_mode != self.last_relative_mode:
            self.onClearCache()

        self._align_edge_ring(length1=length1, length2=length2, alignMode=mode, relativeMode=relative_mode)
        self.last_executed_func = self.onAlignInAbsolute
        self.last_executed_mode = mode
        self.last_relative_mode = False

    def onAlignOutAbsolute(self, *args):
        length1 = cmds.floatField(self.field_length1, q=True, v=True)
        length2 = cmds.floatField(self.field_length2, q=True, v=True)
        mode = self.AM_OUT
        relative_mode = False

        if relative_mode != self.last_relative_mode:
            self.onClearCache()

        self._align_edge_ring(length1=length1, length2=length2, alignMode=mode, relativeMode=relative_mode)
        self.last_executed_func = self.onAlignOutAbsolute
        self.last_executed_mode = mode
        self.last_relative_mode = False

    def onAlignCenterAbsolute(self, *args):
        length1 = cmds.floatField(self.field_length1, q=True, v=True)
        length2 = cmds.floatField(self.field_length2, q=True, v=True)
        mode = self.AM_CENTER
        relative_mode = False

        if relative_mode != self.last_relative_mode:
            self.onClearCache()

        self._align_edge_ring(length1=length1, length2=length2, alignMode=mode, relativeMode=relative_mode)
        self.last_executed_func = self.onAlignCenterAbsolute
        self.last_executed_mode = mode
        self.last_relative_mode = False

    def onAlignInRelative(self, *args):
        length1 = cmds.floatField(self.field_length1, q=True, v=True)
        length2 = cmds.floatField(self.field_length2, q=True, v=True)
        mode = self.AM_IN
        relative_mode = True

        if relative_mode != self.last_relative_mode:
            self.onClearCache()

        self._align_edge_ring(length1=length1, length2=length2, alignMode=mode, relativeMode=relative_mode)
        self.last_executed_func = self.onAlignInRelative
        self.last_executed_mode = mode
        self.last_relative_mode = True

    def onAlignOutRelative(self, *args):
        length1 = cmds.floatField(self.field_length1, q=True, v=True)
        length2 = cmds.floatField(self.field_length2, q=True, v=True)
        mode = self.AM_OUT
        relative_mode = True

        if relative_mode != self.last_relative_mode:
            self.onClearCache()

        self._align_edge_ring(length1=length1, length2=length2, alignMode=mode, relativeMode=relative_mode)
        self.last_executed_func = self.onAlignOutRelative
        self.last_executed_mode = mode
        self.last_relative_mode = True

    def onAlignCenterRelative(self, *args):
        length1 = cmds.floatField(self.field_length1, q=True, v=True)
        length2 = cmds.floatField(self.field_length2, q=True, v=True)
        mode = self.AM_CENTER
        relative_mode = True

        if relative_mode != self.last_relative_mode:
            self.onClearCache()

        self._align_edge_ring(length1=length1, length2=length2, alignMode=mode, relativeMode=relative_mode)
        self.last_executed_func = self.onAlignCenterRelative
        self.last_executed_mode = mode
        self.last_relative_mode = True

    def onHiliteInner(self, *args):
        pass

    # エッジの角度を前後を参照して平均化する
    def onSmoothAngle(self, *args):
        # TODO:実装する
        # p[i] と p[i-1],p[i+1] の三点で作られる平面内で前後エッジの中間角度を求めヨーだけ使用してピッチは元のエッジの値を使う
        # E.first と E.last はそのまま
        print(self.MSG_NOT_IMPLEMENTED)

    # 全ての頂点をキャッシュの位置へ戻す
    def onReset(self, *args):
        edgeCount = len(self.sortedSelEdges)
        for i in range(0, edgeCount):
            cmds.xform(self.vtxListA[i], ws=True, t=(
                self.pntListA[i][0], self.pntListA[i][1], self.pntListA[i][2]))
            cmds.xform(self.vtxListB[i], ws=True, t=(
                self.pntListB[i][0], self.pntListB[i][1], self.pntListB[i][2]))

    def onClearCache(self, *args):
        self.selEdges = []
        self.sortedSelEdges = []
        self.vtxListA = []
        self.vtxListB = []
        self.pntListA = []
        self.pntListB = []
        self.last_executed_func = None
        self.last_relative_mode = None

    # 選択エッジの幅を揃える機能本体
    def _align_edge_ring(self, length1, length2, alignMode, relativeMode=None):
        constMode = cmds.checkBox(self.constMode, q=True, v=True)
        if constMode:
            length2 = length1

        # 選択コンポーネントの取得
        selEdges = cmds.ls(os=True, fl=True)
        edgeCount = len(selEdges)

        vtxListA = []
        vtxListB = []
        pntListA = []
        pntListB = []

        if edgeCount == 0:
            print(self.MSG_NOT_SELECTED)
            return

        # 選択コンポーネントを持つオブジェクトの取得
        selObj = selEdges[0].split(".", 1)[0]

        sortedSelEdges = []  # ソート済み選択エッジ
        u = []  # 開始頂点を0.0 最終頂点を1.0 とする頂点の位置
        length = []  # u値等や Tri 等で変化した最終的な辺の長さ

        # 選択エッジがキャッシュと同じならエッジの順序と頂点座標は現在のコンポーネントの値ではなくキャッシュの値を使う
        if set(selEdges) == set(self.selEdges):
            selEdges = self.selEdges
            sortedSelEdges = self.sortedSelEdges
            vtxListA = self.vtxListA
            vtxListB = self.vtxListB
            pntListA = self.pntListA
            pntListB = self.pntListB
            edgeCount = len(sortedSelEdges)

        else:
            # 開始エッジの決定
            # 開始エッジがフェースの端なら自身を持つフェース==1 のエッジを開始エッジにする
            # そういうエッジがない場合 (選択エッジが完全に島中の場合)は選択エッジに囲まれるすべての面のうち
            # 選択エッジを 1 つしか持たないフェースを検出してその 1 つのエッジを開始エッジにする
            # すべて 2 つ以上持っていたらループしているのでどれから始めてもいいので SelEdge[0] を開始エッジにする
            allSelfaces = cmds.filterExpand(
                cmds.polyListComponentConversion(selEdges, fe=True, tf=True), sm=34)
            startEdge = selEdges[0]  # 端のエッジ
            startFace = None  # 端のフェース
            preprocessedFace = None  # 選択エッジの外側のフェース

            # フェースを一つしか持たないエッジは開始エッジ
            for edge in selEdges:
                faces = cmds.filterExpand(
                    cmds.polyListComponentConversion(edge, fe=True, tf=True), sm=34)
                if len(faces) == 1:
                    startEdge = edge
                    startFace = faces[0]
                    break

            # すべての選択フェイスのうち選択エッジを一つしか持たないフェースは端のフェイス
            if startFace is None:
                for selFace in allSelfaces:
                    edges = cmds.filterExpand(cmds.polyListComponentConversion(
                        selFace, ff=True, te=True), sm=32)
                    if len(set(edges) & set(selEdges)) == 1:
                        startEdge = list(set(edges) & set(selEdges))[0]
                        startFace = selFace
                        preprocessedFace = startFace

            # すべての選択フェイスが選択エッジをふたつ以上持っていればループ
            if startFace is None:
                startEdge = selEdges[0]
                faces = cmds.filterExpand(cmds.polyListComponentConversion(
                    startEdge, fe=True, tf=True), sm=34)
                startFace = faces[0]
                preprocessedFace = startFace

            # エッジのソート
            # 最後に追加されたソート済みエッジを含むフェースから次のエッジを探す
            # SelEdge-sortedSelEdges が空集合 or elEdge-sortedSelEdgesを構成要素として持つフェースが検出できなかったら終了
            processedFaces = []  # 処理済みフェース
            sortedSelEdges.append(startEdge)
            if preprocessedFace is not None:
                processedFaces.append(preprocessedFace)
            untreatedEdges = list(set(selEdges) - set(sortedSelEdges))
            existNextEdge = True  # 次のエッジがあれば True
            while len(untreatedEdges) > 0 and existNextEdge:
                # 最後の処理済みエッジに隣接するフェース
                faces = cmds.filterExpand(cmds.polyListComponentConversion(
                    sortedSelEdges[-1], fe=True, tf=True), sm=34)
                faces = list(set(faces)-set(processedFaces))

                # そのフェース集合のうち未処理エッジを構成要素として持つものを次のフェースとする
                # その構成要素のエッジを sortedSelEdges に追加
                existNextEdge = False
                for face in faces:
                    edges = cmds.filterExpand(
                        cmds.polyListComponentConversion(face, ff=True, te=True), sm=32)
                    shareEdges = list(set(edges) & set(untreatedEdges))
                    if len(shareEdges) != 0:
                        sortedSelEdges.append(shareEdges[0])
                        untreatedEdges.remove(shareEdges[0])
                        processedFaces.append(face)
                        existNextEdge = True

            edgeCount = len(sortedSelEdges)

            # E.first の v0,v1 取得して A,B に追加
            v0, v1 = cmds.filterExpand(cmds.polyListComponentConversion(
                sortedSelEdges[0], fe=True, tv=True), sm=31)
            vtxListA.append(v0)
            vtxListB.append(v1)

            # すべてのエッジを巡回して頂点を A,B に振り分ける
            for edge in sortedSelEdges[1:edgeCount]:
                # 各エッジの片方の頂点と隣接する頂点の取得
                v0, v1 = cmds.filterExpand(
                    cmds.polyListComponentConversion(edge, fe=True, tv=True), sm=31)

                neighborEdges0 = cmds.filterExpand(
                    cmds.polyListComponentConversion(v0, fv=1, te=1), sm=32)

                # 各隣接エッジに関して構成頂点2点を取得する
                neighborVtx = []
                for x in neighborEdges0:
                    nEv0, nEv1 = cmds.filterExpand(
                        cmds.polyListComponentConversion(x, fe=True, tv=True), sm=31)
                    neighborVtx.append(nEv0)
                    neighborVtx.append(nEv1)

                neighborVtx = list(set(neighborVtx))  # uniq

                # v0,v1 どちらかが一致している場合は優先して処理
                if v0 == vtxListA[-1]:
                    vtxListA.append(v0)
                    vtxListB.append(v1)
                elif v0 == vtxListB[-1]:
                    vtxListB.append(v0)
                    vtxListA.append(v1)
                elif v1 == vtxListA[-1]:
                    vtxListB.append(v0)
                    vtxListA.append(v1)
                elif v1 == vtxListB[-1]:
                    vtxListA.append(v0)
                    vtxListB.append(v1)
                else:
                    # edge.v0 が A.last と隣接していれば v0 は同じく A　グループ
                    if vtxListA[-1] in neighborVtx:
                        vtxListA.append(v0)
                        vtxListB.append(v1)
                    else:
                        vtxListB.append(v0)
                        vtxListA.append(v1)

            # 頂点を座標値にパース
            for i in range(0, edgeCount):
                pntListA.append(cmds.xform(
                    vtxListA[i], q=True, ws=True, t=True))
                pntListB.append(cmds.xform(
                    vtxListB[i], q=True, ws=True, t=True))

            # キャッシュの更新
            self.selEdges = selEdges
            self.sortedSelEdges = sortedSelEdges
            self.vtxListA = vtxListA
            self.vtxListB = vtxListB
            self.pntListA = pntListA
            self.pntListB = pntListB

        baseVtx = []  # 動かない側の頂点オブジェクト
        moveVtx = []  # 動かす側の頂点オブジェクト
        basePoints = []  # 動かす側の頂点座標
        movePoints = []  # 動かさない側の頂点座標
        vecBM = []    # basePoint から movePoint へ向く単位ベクトル
        pivots = []  # 頂点移動の起点
        vecDir = []     # 実際に移動させる方向の単位ベクトル

        # base,move がどちら側か決定する
        # ABの各経路の長さ計算
        pathLengthA = 0
        pathLengthB = 0
        basePathLength = 0
        for i in range(0, edgeCount-1):
            p1 = pntListA[i]
            p2 = pntListA[i+1]
            pathLengthA += distance(p1, p2)

            p1 = pntListB[i]
            p2 = pntListB[i+1]
            pathLengthB += distance(p1, p2)

        # 経路が短い方が IN としてモードに従って base/move 決める
        if alignMode == self.AM_IN:
            if pathLengthA <= pathLengthB:
                baseVtx = vtxListA
                moveVtx = vtxListB
                basePoints = pntListA
                movePoints = pntListB
                basePathLength = pathLengthA
            else:
                baseVtx = vtxListB
                moveVtx = vtxListA
                basePoints = pntListB
                movePoints = pntListA
                basePathLength = pathLengthB

        elif alignMode == self.AM_OUT:
            if pathLengthA <= pathLengthB:
                baseVtx = vtxListB
                moveVtx = vtxListA
                basePoints = pntListB
                movePoints = pntListA
                basePathLength = pathLengthB
            else:
                baseVtx = vtxListA
                moveVtx = vtxListB
                basePoints = pntListA
                movePoints = pntListB
                basePathLength = pathLengthA

        elif alignMode == self.AM_CENTER:  # IN と同じ
            if pathLengthA <= pathLengthB:
                baseVtx = vtxListA
                moveVtx = vtxListB
                basePoints = pntListA
                movePoints = pntListB
                basePathLength = pathLengthA
            else:
                baseVtx = vtxListB
                moveVtx = vtxListA
                basePoints = pntListB
                movePoints = pntListA
                basePathLength = pathLengthB
        else:
            print(self.MSG_UNK_ALIGNMODE)
            raise

        # U値の計算
        pathLength = 0
        u = [0.0]*edgeCount
        for i in range(1, edgeCount):
            p1 = basePoints[i-1]
            p2 = basePoints[i]
            pathLength += distance(p1, p2)
            u[i] = (pathLength / basePathLength)
        u[0] = 0.0
        u[-1] = 1.0

        # length の計算
        if relativeMode:
            acc_add = cmds.floatField(self.ff_acc_add, q=True, v=True)
            acc_mul = cmds.floatField(self.ff_acc_mul, q=True, v=True)

            for i in range(0, edgeCount):
                p1 = basePoints[i]
                p2 = movePoints[i]
                current_length = distance(p1, p2)

                length.append(0)
                length[i] = current_length * acc_mul + acc_add
        else:
            for i in range(0, edgeCount):
                length.append(0)
                length[i] = length1 + (length2 - length1) * u[i]

        # TODO: tri による length の調整

        # ピボットの計算
        for i in range(0, edgeCount):
            if alignMode == self.AM_IN:
                pivots.append(basePoints[i])
            elif alignMode == self.AM_OUT:
                pivots.append(basePoints[i])
            elif alignMode == self.AM_CENTER:
                p1 = basePoints[i]
                p2 = movePoints[i]
                pivots.append(
                    ((p1[0]+p2[0])/2, (p1[1]+p2[1])/2, (p1[2]+p2[2])/2))
                # TODO: Tri の場合の処理
            else:
                print(self.MSG_UNK_ALIGNMODE)
                raise

        # エッジ方向単位ベクトルの計算
        for i in range(0, edgeCount):
            p1 = basePoints[i]
            p2 = movePoints[i]
            v = normalize(vector(p1, p2))
            vecBM.append(normalize(v))

        # 移動方向ベクトルの計算
        for i in range(0, edgeCount):
            if alignMode == self.AM_IN:
                vecDir.append(vecBM[i])
            elif alignMode == self.AM_OUT:
                vecDir.append(vecBM[i])
            elif alignMode == self.AM_CENTER:
                vecDir.append(vecBM[i])
            else:
                print(self.MSG_UNK_ALIGNMODE)
                raise

        # TODO: Tri の処理
        if self.preserveAngle:
            pass
        else:
            pass

        # 頂点の変更
        if alignMode == self.AM_IN:
            for i in range(0, edgeCount):
                x = pivots[i][0] + vecDir[i][0] * length[i]
                y = pivots[i][1] + vecDir[i][1] * length[i]
                z = pivots[i][2] + vecDir[i][2] * length[i]
                cmds.xform(baseVtx[i], ws=True, t=(
                    basePoints[i][0], basePoints[i][1], basePoints[i][2]))
                cmds.xform(moveVtx[i], ws=True, t=(x, y, z))

        elif alignMode == self.AM_OUT:
            for i in range(0, edgeCount):
                x = pivots[i][0] + vecDir[i][0] * length[i]
                y = pivots[i][1] + vecDir[i][1] * length[i]
                z = pivots[i][2] + vecDir[i][2] * length[i]
                cmds.xform(baseVtx[i], ws=True, t=(
                    basePoints[i][0], basePoints[i][1], basePoints[i][2]))
                cmds.xform(moveVtx[i], ws=True, t=(x, y, z))

        elif alignMode == self.AM_CENTER:
            for i in range(0, edgeCount):
                x = pivots[i][0] + vecDir[i][0] * length[i] / 2
                y = pivots[i][1] + vecDir[i][1] * length[i] / 2
                z = pivots[i][2] + vecDir[i][2] * length[i] / 2
                cmds.xform(moveVtx[i], ws=True, t=(x, y, z))

                x = pivots[i][0] - vecDir[i][0] * length[i] / 2
                y = pivots[i][1] - vecDir[i][1] * length[i] / 2
                z = pivots[i][2] - vecDir[i][2] * length[i] / 2
                cmds.xform(baseVtx[i], ws=True, t=(x, y, z))

        else:
            print(self.MSG_UNK_ALIGNMODE)
            raise

    def onDump(self, *args):
        print("self.pntListA[0] coord>")
        print(self.pntListA[0])


def alignEdgeRingUI():
    NN_AlignedgeRingWindow().create()


def main():
    alignEdgeRingUI()


if __name__ == "__main__":
    main()
