# エッジのリスト選択して実行すると片側固定して幅を統一するやつ
import maya.cmds as cmds
import maya.api.OpenMaya as om
import math

import nnutil.core as nu
import nnutil.ui as ui


window_name = "NN_RingWidth"
window = None

color_in = (0x80 / 255, 0x40 / 255, 0x40 / 255)  # Align In ボタンの背景色 (#804040)
color_out = (0x40 / 255, 0x40 / 255, 0x80 / 255)  # Align Out ボタンの背景色 (#404080)
color_center = (0x80 / 255, 0x60 / 255, 0x40 / 255)  # Align Center ボタンの背景色 (#806040)


def get_window():
    return window


# vertex から point 取得
def pointFromVertex(vtx):
    return cmds.xform(vtx, q=True, ws=True, t=True)


def distance(p1, p2):
    return math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2 + (p2[2]-p1[2])**2)


def path_length(points):
    """隣り合う点同士の距離の合計"""
    return sum(distance(p1, p2) for p1, p2 in zip(points[:-1], points[1:]))


def vector(p1, p2):
    return (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])


# ベクトルの正規化
def normalize(v):
    norm = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
    if norm != 0:
        return (v[0]/norm, v[1]/norm, v[2]/norm)
    else:
        return (0, 0, 0)


def set_highlight_appearance(curve, color=(1.0, 0.0, 0.0)):
    """強調表示用カーブの見た目を設定する (赤・太線)"""
    curve_shape = cmds.listRelatives(curve, shapes=True, fullPath=True)[0]
    cmds.setAttr(curve + ".overrideEnabled", True)
    cmds.setAttr(curve + ".overrideRGBColors", True)
    cmds.setAttr(curve + ".overrideColorR", color[0])
    cmds.setAttr(curve + ".overrideColorG", color[1])
    cmds.setAttr(curve + ".overrideColorB", color[2])
    cmds.setAttr(curve_shape + ".lineWidth", 6)


class NN_AlignedgeRingWindow(object):
    MSG_NOT_SELECTED = "エッジが選択されていません"
    MSG_UNK_ALIGNMODE = "未知の整列モードです"
    MSG_UNK_RELMODE = "未知の相対モードです"
    MSG_NOT_IMPLEMENTED = "未実装"

    HIGHLIGHT_PREFIX = "NN_RingWidth_HighlightInner_"  # 強調表示用に生成したノード名のプリフィクス

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

        self.highlight_job = None  # 強調表示を選択に追従させる scriptJob の番号
        self.highlight_selections = None  # 強調表示を最後に作ったときの選択
        self.highlight_updating = False  # 強調表示の作り直し中なら True

    def create(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)

        cmds.window(
            self.window,
            t=self.title,
            maximizeButton=False,
            minimizeButton=False,
            widthHeight=self.size,
            sizeable=False,
            resizeToFitChildren=True
            )

        self.layout()
        cmds.showWindow(self.window)

    def layout(self):
        window_width = 260

        with ui.column_layout():
            # モード切り替え
            with ui.row_layout():
                ui.radio_collection()
                self.rb_absolute = ui.radio_button(label="Absolute", width=ui.width(4), height=ui.height(1), select=True, onCommand=self.onChangeMode)
                self.rb_relative = ui.radio_button(label="Relative", width=ui.width(4), height=ui.height(1), onCommand=self.onChangeMode)

            ui.separator(width=window_width)

            # 絶対モード
            with ui.column_layout() as self.layout_absolute:
                with ui.row_layout():
                    ui.header(label="Absolute")

                with ui.row_layout():
                    ui.header(label='width1:')
                    ui.button(label='-', c=self.onDecreaseLength1)
                    self.field_length1 = ui.eb_float(v=0.1, dc=self.onChangeLength1)
                    ui.button(label='+', c=self.onIncreaseLength1)
                    ui.button(label='swap', c=self.onSwapLength)

                with ui.row_layout():
                    ui.header(label='width2:')
                    ui.button(label='-', c=self.onDecreaseLength2)
                    self.field_length2 = ui.eb_float(v=0.1, en=False, dc=self.onChangeLength2)
                    ui.button(label='+', c=self.onIncreaseLength2)
                    self.constMode = ui.check_box(label='const', v=True, cc=self.onSetConst)

                with ui.row_layout():
                    ui.header(label="Align")
                    ui.button(label='In', c=self.onAlignInAbsolute, bgc=color_in)
                    ui.button(label='Center', c=self.onAlignCenterAbsolute, bgc=color_center)
                    ui.button(label='Out', c=self.onAlignOutAbsolute, bgc=color_out)

                ui.separator(width=window_width)

                # 取得系
                with ui.row_layout():
                    ui.header(label='Get from ')
                    ui.button(label='First', c=self.onSetLengthFromFirstEdge)
                    ui.button(label='Last', c=self.onSetLengthFromLastEdge)
                    ui.button(label='Mode', c=self.onSetLengthFromMode)
                    ui.button(label='Path', c=self.onSetLengthFromEdgePath)

                with ui.row_layout():
                    ui.header(label='')
                    ui.button(label='Min', c=self.onSetLengthFromMin)
                    ui.button(label='Max', c=self.onSetLengthFromMax)
                    ui.button(label='Average', c=self.onSetLengthFromAverage)

                ui.separator(width=window_width)

            # 相対モード
            with ui.column_layout(visible=False) as self.layout_relative:
                with ui.row_layout():
                    ui.header(label="Relative")

                with ui.row_layout():
                    ui.header(label="mul")
                    ui.button(label='-10%', c=self.onRelativeDiv_90, width=ui.width(1.5))
                    ui.button(label='-1%', c=self.onRelativeDiv_99, width=ui.width(1.5))
                    self.ff_acc_mul = ui.eb_float(v=1)
                    ui.button(label='+1%', c=self.onRelativeMul_1, width=ui.width(1.5))
                    ui.button(label='+10%', c=self.onRelativeMul_10, width=ui.width(1.5))

                with ui.row_layout():
                    ui.header(label="add")
                    ui.button(label='-0.1', c=self.onRelativeDiff_10, width=ui.width(1.5))
                    ui.button(label='-0.01', c=self.onRelativeDiff_1, width=ui.width(1.5))
                    self.ff_acc_add = ui.eb_float(v=0)
                    ui.button(label='+0.01', c=self.onRelativeAdd_1, width=ui.width(1.5))
                    ui.button(label='+0.1', c=self.onRelativeAdd_10, width=ui.width(1.5))

                with ui.row_layout():
                    ui.header(label="Align")
                    ui.button(label='In', c=self.onAlignInRelative, bgc=color_in)
                    ui.button(label='Center', c=self.onAlignCenterRelative, bgc=color_center)
                    ui.button(label='Out', c=self.onAlignOutRelative, bgc=color_out)

                ui.separator(width=window_width)

            with ui.column_layout():
                # その他機能
                with ui.row_layout():
                    ui.header(label='Angle')
                    ui.text(label="To Bisector")
                    ui.button(label='In', c=self.onToBisectorIn, bgc=color_in)
                    ui.button(label='Out', c=self.onToBisectorOut, bgc=color_out)
                    
                with ui.row_layout():
                    ui.header(label='')
                    ui.text(label="Parallel To")
                    ui.button(label='In', c=self.onParallelToIn, bgc=color_in)
                    ui.button(label='Out', c=self.onParallelToOut, bgc=color_out)
                                   
                ui.separator(width=window_width)
                 
                with ui.row_layout():
                    ui.header(label='Func')
                    ui.button(label='Reset', c=self.onReset)    
                    ui.button(label='ClearCache', c=self.onClearCache)
                    

                with ui.row_layout():
                    ui.header(label='')
                    self.cb_highlight_inner = ui.check_box(label="Highlight Inner", v=False, cc=self.onHighlightInner)

                ui.separator(width=window_width)

    def onChangeMode(self, *args):
        """モード切り替えラジオボタンのハンドラ。選択されたモードのグループだけを表示する"""
        is_absolute = cmds.radioButton(self.rb_absolute, q=True, select=True)
        cmds.columnLayout(self.layout_absolute, e=True, visible=is_absolute)
        cmds.columnLayout(self.layout_relative, e=True, visible=not is_absolute)

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
            sortedSelEdges = self._get_sorted_edges(selEdges)
            v0, v1 = cmds.filterExpand(cmds.polyListComponentConversion(
                sortedSelEdges[0], fe=True, tv=True), sm=31)
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
            sortedSelEdges = self._get_sorted_edges(selEdges)
            v0, v1 = cmds.filterExpand(cmds.polyListComponentConversion(
                sortedSelEdges[-1], fe=True, tv=True), sm=31)
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

    def onHighlightInner(self, *args):
        """内側エッジ列の強調表示を切り替える。有効な間は選択変更のたびに表示を作り直す"""
        if cmds.checkBox(self.cb_highlight_inner, q=True, v=True):
            if not self.highlight_job or not cmds.scriptJob(exists=self.highlight_job):
                self.highlight_job = cmds.scriptJob(event=["SelectionChanged", self._update_highlight], parent=self.window)

            self.highlight_selections = None
            self._update_highlight()

        else:
            if self.highlight_job and cmds.scriptJob(exists=self.highlight_job):
                cmds.scriptJob(kill=self.highlight_job, force=True)

            self.highlight_job = None
            self._delete_highlight()

    def _update_highlight(self):
        """現在の選択エッジから内側エッジ列を求めて強調表示用カーブを作り直す"""
        # カーブ作成時の一時的な選択と選択の復元でも SelectionChanged が発生するため、同じ選択に対しては作り直さない
        current_selections = cmds.ls(orderedSelection=True, flatten=True)
        if self.highlight_updating or current_selections == self.highlight_selections:
            return

        self.highlight_updating = True
        self.highlight_selections = current_selections

        # 強調表示の生成と削除はアンドゥの対象にしない
        undo_state = cmds.undoInfo(q=True, stateWithoutFlush=True)
        cmds.undoInfo(stateWithoutFlush=False)

        try:
            self._delete_highlight()

            selEdges = cmds.filterExpand(current_selections, selectionMask=32) or []
            if not selEdges:
                return

            # 選択がキャッシュと同じなら Align と同じ判定結果を使う
            if set(selEdges) == set(self.selEdges):
                vtxListA, vtxListB, pntListA, pntListB = self.vtxListA, self.vtxListB, self.pntListA, self.pntListB
            else:
                _, vtxListA, vtxListB, pntListA, pntListB = self._evaluate_ring(selEdges)

            if path_length(pntListA) <= path_length(pntListB):
                innerVtx, outerVtx = vtxListA, vtxListB
            else:
                innerVtx, outerVtx = vtxListB, vtxListA

            # 強調表示するエッジ列とその色 (内側は赤、外側は青)
            highlights = []
            for vtxList, color in [(innerVtx, (1.0, 0.0, 0.0)), (outerVtx, (0.0, 0.0, 1.0))]:
                # 隣り合う頂点を結ぶエッジ (ループしている場合は末尾と先頭も繋がる)
                edges = []
                for v0, v1 in zip(vtxList, vtxList[1:] + vtxList[:1]):
                    edges += cmds.polyListComponentConversion([v0, v1], fromVertex=True, toEdge=True, internal=True)

                if edges:
                    highlights.append((edges, color))

            if not highlights:
                return

            # polyToCurve の引数仕様が不明なため引数でのコンポーネント指定をせず選択経由で実行する
            # polyToCurve が変更した選択モードと選択オブジェクトをもとに戻す
            is_component_mode = cmds.selectMode(q=True, component=True)
            hilited_objects = cmds.ls(hilite=True)
            select_types = {x: cmds.selectType(q=True, **{x: True}) for x in ["polymeshVertex", "polymeshEdge", "polymeshFace", "polymeshUV", "polymeshVtxFace"]}

            created_curves = []
            for edges, color in highlights:
                cmds.select(edges, replace=True)
                created_nodes = cmds.polyToCurve(form=2, degree=1, conformToSmoothMeshPreview=False)
                created_curves.append((created_nodes, color))

            if is_component_mode:
                cmds.selectMode(component=True)
            else:
                cmds.selectMode(object=True)

            cmds.selectType(**select_types)

            if hilited_objects:
                cmds.hilite(hilited_objects, replace=True)

            cmds.select(current_selections, replace=True)

            for created_nodes, color in created_curves:
                curve = cmds.rename(created_nodes[0], self.HIGHLIGHT_PREFIX + "curve#")
                cmds.rename(created_nodes[1], self.HIGHLIGHT_PREFIX + "polyEdgeToCurve#")
                set_highlight_appearance(curve, color)

        finally:
            cmds.undoInfo(stateWithoutFlush=undo_state)
            self.highlight_updating = False

    def _delete_highlight(self):
        """強調表示用のプリフィクスを持つノードをすべて削除する"""
        existing_nodes = cmds.ls(self.HIGHLIGHT_PREFIX + "*")
        if existing_nodes:
            cmds.delete(existing_nodes)

    def onToBisectorIn(self, *args):
        """In 側を固定し、各エッジを In 側エッジ列の角の二等分方向へ向ける"""
        self._orient_edge_ring(alignMode=self.AM_IN, parallel=False)

    def onToBisectorOut(self, *args):
        """Out 側を固定し、各エッジを Out 側エッジ列の角の二等分方向へ向ける"""
        self._orient_edge_ring(alignMode=self.AM_OUT, parallel=False)

    def onParallelToIn(self, *args):
        """In 側を固定し、Out 側エッジ列を In 側エッジ列と近似的に平行にする"""
        self._orient_edge_ring(alignMode=self.AM_IN, parallel=True)

    def onParallelToOut(self, *args):
        """Out 側を固定し、In 側エッジ列を Out 側エッジ列と近似的に平行にする"""
        self._orient_edge_ring(alignMode=self.AM_OUT, parallel=True)

    def _orient_edge_ring(self, alignMode, parallel):
        """動かない側のエッジ列を基準に、反対側の頂点を移動する

        parallel が False なら反対側の頂点を既存のエッジ列上でスライドさせ、エッジを二等分面に乗せる
        parallel が True なら選択エッジの向きを保ったまま頂点を選択エッジ上でスライドさせ、反対側のエッジ列を動かない側のエッジ列に近似的に平行にする
        """
        selEdges = cmds.ls(orderedSelection=True, flatten=True)
        if not selEdges:
            print(self.MSG_NOT_SELECTED)

            return

        if set(selEdges) != set(self.selEdges):
            self._build_cache(selEdges)

        # 経路が短い方が IN
        a_is_in = path_length(self.pntListA) <= path_length(self.pntListB)
        if a_is_in == (alignMode == self.AM_IN):
            baseVtx, moveVtx, basePoints, movePoints = self.vtxListA, self.vtxListB, self.pntListA, self.pntListB
        else:
            baseVtx, moveVtx, basePoints, movePoints = self.vtxListB, self.vtxListA, self.pntListB, self.pntListA

        n = len(basePoints)
        if n < 2:
            return

        # 動かない側の先頭と末尾の頂点がエッジで繋がっていればループ
        is_loop = n > 2 and bool(cmds.polyListComponentConversion([baseVtx[0], baseVtx[-1]], fromVertex=True, toEdge=True, internal=True))

        P = [om.MPoint(p) for p in basePoints]
        Q = [om.MPoint(p) for p in movePoints]

        # 各頂点の二等分面の法線 (動かない側の経路の接線方向)。ループしていない場合の両端は None
        tangents = [None] * n
        for i in range(n):
            if not is_loop and (i == 0 or i == n - 1):
                continue

            a = (P[i - 1] - P[i]).normal()
            b = (P[(i + 1) % n] - P[i]).normal()
            tangents[i] = (b - a).normal()

        newPoints = list(Q)

        if not parallel:
            # 前後どちらかの動かす側エッジと二等分面の交点へスライドする
            for i, t in enumerate(tangents):
                if t is None:
                    continue

                fi = (Q[i] - P[i]) * t
                for j in (i + 1, i - 1):
                    Qj = Q[j % n]
                    fj = (Qj - P[i]) * t
                    if fi * fj <= 0 and fi != fj:
                        newPoints[i] = Q[i] + (Qj - Q[i]) * (fi / (fi - fj))
                        break

        else:
            # 動かす側の各セグメントを、中点を通り対応する動かない側のセグメントと平行な直線に置き換え、
            # 両端の選択エッジの直線との交点 (ねじれの位置なら選択エッジ側の最近点) を求める
            candidates = [[] for _ in range(n)]
            for i in range(n if is_loop else n - 1):
                j = (i + 1) % n
                s = (P[j] - P[i]).normal()
                m = Q[i] + (Q[j] - Q[i]) * 0.5
                for k in (i, j):
                    e = (Q[k] - P[k]).normal()
                    es = e * s
                    if 1.0 - es * es < 1e-6:
                        continue

                    w = P[k] - m
                    candidates[k].append(P[k] + e * ((es * (s * w) - e * w) / (1.0 - es * es)))

            # 前後のセグメントから求めた 2 点の中間点 (両端は 1 点) を新しい位置にする
            for i, points in enumerate(candidates):
                if points:
                    newPoints[i] = points[0] + (points[-1] - points[0]) * 0.5

        for vtx, p in zip(moveVtx, newPoints):
            cmds.xform(vtx, worldSpace=True, translation=(p.x, p.y, p.z))

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

    def _build_cache(self, selEdges):
        """選択エッジをソートして両側の頂点列に振り分け、キャッシュを更新する"""
        sortedSelEdges, vtxListA, vtxListB, pntListA, pntListB = self._evaluate_ring(selEdges)

        # キャッシュの更新
        self.selEdges = selEdges
        self.sortedSelEdges = sortedSelEdges
        self.vtxListA = vtxListA
        self.vtxListB = vtxListB
        self.pntListA = pntListA
        self.pntListB = pntListB

    def _get_sorted_edges(self, selEdges):
        """選択エッジを Align と同じ順序 (width1 側の端から width2 側の端へ) に並べたリストを返す"""
        # 選択がキャッシュと同じなら Align と同じ順序を使う
        if set(selEdges) == set(self.selEdges):
            return self.sortedSelEdges

        return self._evaluate_ring(selEdges)[0]

    def _evaluate_ring(self, selEdges):
        """選択エッジをソートして両側の頂点列に振り分ける

        Returns:
            tuple: (ソート済みエッジ, A 側頂点列, B 側頂点列, A 側座標列, B 側座標列)
        """
        sortedSelEdges = []
        vtxListA = []
        vtxListB = []
        pntListA = []
        pntListB = []

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
            startEdge = selEdges[-1]
            faces = cmds.filterExpand(cmds.polyListComponentConversion(
                startEdge, fe=True, tf=True), sm=34)
            startFace = faces[0]

            # 選択順で最後の 2 エッジが隣接していれば、その間で切って両端にする (共有フェースを処理済みにして反対側へ進める)
            prevFaces = cmds.filterExpand(cmds.polyListComponentConversion(selEdges[-2], fe=True, tf=True), sm=34)
            sharedFaces = list(set(faces) & set(prevFaces))
            if sharedFaces:
                startFace = sharedFaces[0]

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

        # 同じ選択なら常に同じ向きになるよう、先頭のエッジ ID が末尾より小さくなる向きにそろえる
        if not nu.get_index(sortedSelEdges[0]) < nu.get_index(sortedSelEdges[-1]):
            sortedSelEdges.reverse()

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

        return sortedSelEdges, vtxListA, vtxListB, pntListA, pntListB

    # 選択エッジの幅を揃える機能本体
    def _align_edge_ring(self, length1, length2, alignMode, relativeMode=None):
        constMode = cmds.checkBox(self.constMode, q=True, v=True)
        if constMode:
            length2 = length1

        # 選択コンポーネントの取得
        selEdges = cmds.ls(os=True, fl=True)
        edgeCount = len(selEdges)

        if edgeCount == 0:
            print(self.MSG_NOT_SELECTED)
            return

        # 選択コンポーネントを持つオブジェクトの取得
        selObj = selEdges[0].split(".", 1)[0]

        u = []  # 開始頂点を0.0 最終頂点を1.0 とする頂点の位置
        length = []  # u値等や Tri 等で変化した最終的な辺の長さ

        # 選択エッジがキャッシュと同じならエッジの順序と頂点座標は現在のコンポーネントの値ではなくキャッシュの値を使う
        if set(selEdges) != set(self.selEdges):
            self._build_cache(selEdges)

        sortedSelEdges = self.sortedSelEdges
        vtxListA = self.vtxListA
        vtxListB = self.vtxListB
        pntListA = self.pntListA
        pntListB = self.pntListB
        edgeCount = len(sortedSelEdges)

        baseVtx = []  # 動かない側の頂点オブジェクト
        moveVtx = []  # 動かす側の頂点オブジェクト
        basePoints = []  # 動かす側の頂点座標
        movePoints = []  # 動かさない側の頂点座標
        vecBM = []    # basePoint から movePoint へ向く単位ベクトル
        pivots = []  # 頂点移動の起点
        vecDir = []     # 実際に移動させる方向の単位ベクトル

        # base,move がどちら側か決定する
        # ABの各経路の長さ計算
        pathLengthA = path_length(pntListA)
        pathLengthB = path_length(pntListB)
        basePathLength = 0

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
