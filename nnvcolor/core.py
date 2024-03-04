#! python
# coding:utf-8
"""頂点カラーツール"""
import re
import math

from shiboken2 import wrapInstance

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

import maya.OpenMayaUI as omui

from PySide2.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QSlider, QFrame
from PySide2.QtCore import Qt, QEvent, Signal, QPoint
from PySide2.QtGui import QDoubleValidator, QCursor

from maya.app.general.mayaMixin import MayaQWidgetBaseMixin

import nnutil.ui as ui


def to_real_text(v, precision):
    """エディットボックス用の実数のフォーマッティング"""
    format_string = "{:.%sf}" % precision

    return format_string.format(v)


class PushButtonLRM(QPushButton):
    middleClicked = Signal()
    rightClicked = Signal()

    def __init__(self, parent=None):
        super(PushButtonLRM, self).__init__(parent)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.middleClicked.emit()

        elif event.button() == Qt.RightButton:
            self.rightClicked.emit()

        super(PushButtonLRM, self).mouseReleaseEvent(event)


class EditBoxFloatDraggable(QLineEdit):
    dragged = Signal()

    def __init__(self, parent=None):
        super(EditBoxFloatDraggable, self).__init__(parent)
        self.installEventFilter(self)

        self.is_dragging = False
        self.cached_value = 0.0
        self.cached_pos = QPoint(0, 0)
        self.precision = 4
        self.diff_scale = 1.0

    def is_met_drag_condition(self, event):
        """"ドラッグ操作の条件を満たしていれば True"""
        return event.buttons() & Qt.LeftButton and event.modifiers() == Qt.ControlModifier

    def eventFilter(self, source, event):
        """イベントフィルター"""
        if event.type() == QEvent.MouseMove:
            if self.is_met_drag_condition(event):  # ドラッグ継続中処理
                if not self.is_dragging:  # ドラッグ開始フレーム
                    self.cached_value = float(self.text())
                    self.cached_pos = QCursor.pos()
                    self.is_dragging = True

                # ドラッグ開始時のカーソル位置との差分をドラッグ開始時の値に加算する
                current_pos = QCursor.pos()
                diff_pos = round(float(current_pos.x() - self.cached_pos.x()) / 10**self.precision / self.diff_scale, 4)
                diff_sign = math.copysign(1.0, diff_pos)
                diff_abs = max(0.1**self.precision, abs(diff_pos))
                new_value = self.cached_value + diff_abs * diff_sign
                self.setText(to_real_text(new_value, self.precision))
                self.dragged.emit()

            elif not self.is_met_drag_condition(event) and self.is_dragging:
                # ドラッグ完了フレーム
                self.is_dragging = False
                self.dragged.emit()

            else:
                pass

            return False

        return False


class InvalidArgumentCombinationError(Exception):
    """引数の値の組み合わせが不正な場合の例外｡"""
    pass


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
    global window

    return window


class NN_ToolWindow(MayaQWidgetBaseMixin, QMainWindow):
    singleton_instance = None

    def __init__(self, parent=None):
        super(NN_ToolWindow, self).__init__(parent=parent)

        self.is_chunk_open = False
        self.editbox_precision = 4
        self.vf_color_caches = dict()  # スライド開始時の頂点カラーキャッシュ dict[obj_name, list[MColor]]

        self.brush_size_mode = False
        self.cached_value = 1.0  # ブラシサイズ変更開始時のスライダーの値
        self.start_pos = 0
        self.cached_size = 0.1  # ブラシサイズ変更開始時のブラシサイズ

        # UI の初期化
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle(window_name)

    def to_inner_value(self, v):
        """実際の値 [0.0, 1.0] を内部のスケールされた値に変換する"""
        if isinstance(v, list):
            return [int(x * 10 ** self.editbox_precision) for x in v]
        else:
            return int(v * 10 ** self.editbox_precision)

    def to_actual_value(self, v):
        """内部のスケールされた値を実際の値 [0.0, 1.0] に変換する"""
        if isinstance(v, list):
            return [x / 10 ** self.editbox_precision for x in v]
        else:
            return v / 10 ** self.editbox_precision

    def to_real_text(self, v):
        """エディットボックス用の実数のフォーマッティング"""
        return to_real_text(v, self.editbox_precision)

    def create(self):
        """ウィンドウの作成と表示"""
        if NN_ToolWindow.singleton_instance:
            NN_ToolWindow.singleton_instance.close()

        self.layout()
        self.setFixedSize(self.sizeHint())  # コントロール配置後に推奨最小サイズでウィンドウサイズ固定

        # ウィンドウのプリファレンスで起動位置指定する
        if cmds.windowPref(self.window, exists=True):
            position = cmds.windowPref(self.window, q=True, topLeftCorner=True)
            cmds.windowPref(self.window, remove=True)

            self.move(position[0], position[1])

        self.show()
        NN_ToolWindow.singleton_instance = self

    def layout(self):
        row_height1 = 36
        row_height2 = 30
        button_width1 = 80
        button_width2 = 54
        edit_box_width = button_width1
        separater_height1 = 4
        separater_height2 = 8
        outer_margin = 2
        spacing = 3

        # レウアウト枠組み
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        column1 = QVBoxLayout(central_widget)
        column1.setSpacing(0)
        column1.setContentsMargins(outer_margin, outer_margin, outer_margin, outer_margin)

        rows = [QHBoxLayout() for _ in range(10)]
        for row in rows:
            row.setSpacing(spacing)
            row.setContentsMargins(0, 0, 0, 0)

            column1.addLayout(row)

        # UI コントロ-ル定義
        c = PushButtonLRM("RGBA")
        c.clicked.connect(self.onSetColorRGBA)
        c.middleClicked.connect(self.onGetColorRGBA)
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width1)
        rows[0].addWidget(c)

        c = PushButtonLRM("Create Set [Op]")
        c.clicked.connect(self.onCreateColorSet)
        c.middleClicked.connect(self.onColorSetEditor)
        c.setFixedHeight(row_height1)
        rows[0].addWidget(c)

        c = PushButtonLRM("Toggle Disp")
        c.clicked.connect(self.onToggleDisplay)
        c.setFixedHeight(row_height1)
        rows[0].addWidget(c)

        rows[0].setContentsMargins(0, 0, 0, separater_height2)

        # Red
        c = PushButtonLRM("R")
        c.clicked.connect(self.onSetColorR)
        c.middleClicked.connect(self.onGetColorR)
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width1)
        rows[2].addWidget(c)

        c = PushButtonLRM("0.00")
        c.clicked.connect(self.onSetColorR000)
        c.setStyleSheet("background-color: #000000; color: white;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[2].addWidget(c)

        c = PushButtonLRM("0.25")
        c.clicked.connect(self.onSetColorR025)
        c.setStyleSheet("background-color: #400000; color: white;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[2].addWidget(c)

        c = PushButtonLRM("0.50")
        c.clicked.connect(self.onSetColorR050)
        c.setStyleSheet("background-color: #800000; color: white;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[2].addWidget(c)

        c = PushButtonLRM("0.75")
        c.clicked.connect(self.onSetColorR075)
        c.setStyleSheet("background-color: #c00000; color: black;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[2].addWidget(c)

        c = PushButtonLRM("1.00")
        c.clicked.connect(self.onSetColorR100)
        c.setStyleSheet("background-color: #FF0000; color: black;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[2].addWidget(c)

        rows[2].setContentsMargins(0, 0, 0, separater_height1)

        c = EditBoxFloatDraggable()
        c.setValidator(QDoubleValidator())
        c.validator().setDecimals(self.editbox_precision)
        c.setText(self.to_real_text(1.0))
        c.dragged.connect(self.onDragEditBoxRed)
        c.editingFinished.connect(self.onChangeEditBoxRed)
        c.installEventFilter(self)
        c.setFixedHeight(row_height2)
        c.setFixedWidth(edit_box_width)
        rows[3].addWidget(c)
        self.eb_red = c

        c = QSlider(Qt.Horizontal)
        c.setRange(self.to_inner_value(0.0), self.to_inner_value(1.0))
        c.setValue(self.to_inner_value(1.0))
        c.sliderMoved.connect(self.onDragRed)
        c.sliderReleased.connect(self.onChangeSliderRed)
        c.installEventFilter(self)
        c.setFixedHeight(row_height2)
        rows[3].addWidget(c)
        self.fs_red = c

        rows[3].setContentsMargins(0, 0, 0, separater_height2)

        # Green
        c = PushButtonLRM("G")
        c.clicked.connect(self.onSetColorG)
        c.middleClicked.connect(self.onGetColorG)
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width1)
        rows[4].addWidget(c)

        c = PushButtonLRM("0.00")
        c.clicked.connect(self.onSetColorG000)
        c.setStyleSheet("background-color: #000000; color: white;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[4].addWidget(c)

        c = PushButtonLRM("0.25")
        c.clicked.connect(self.onSetColorG025)
        c.setStyleSheet("background-color: #004000; color: white;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[4].addWidget(c)

        c = PushButtonLRM("0.50")
        c.clicked.connect(self.onSetColorG050)
        c.setStyleSheet("background-color: #008000; color: white;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[4].addWidget(c)

        c = PushButtonLRM("0.75")
        c.clicked.connect(self.onSetColorG075)
        c.setStyleSheet("background-color: #00c000; color: black;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[4].addWidget(c)

        c = PushButtonLRM("1.00")
        c.clicked.connect(self.onSetColorG100)
        c.setStyleSheet("background-color: #00FF00; color: black;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[4].addWidget(c)

        rows[4].setContentsMargins(0, 0, 0, separater_height1)

        c = EditBoxFloatDraggable()
        c.setValidator(QDoubleValidator())
        c.validator().setDecimals(self.editbox_precision)
        c.setText(self.to_real_text(1.0))
        c.dragged.connect(self.onDragEditBoxGreen)
        c.editingFinished.connect(self.onChangeEditBoxGreen)
        c.installEventFilter(self)
        c.setFixedHeight(row_height2)
        c.setFixedWidth(edit_box_width)
        rows[5].addWidget(c)
        self.eb_green = c

        c = QSlider(Qt.Horizontal)
        c.setRange(self.to_inner_value(0.0), self.to_inner_value(1.0))
        c.setValue(self.to_inner_value(1.0))
        c.sliderMoved.connect(self.onDragGreen)
        c.sliderReleased.connect(self.onChangeSliderGreen)
        c.installEventFilter(self)
        c.setFixedHeight(row_height2)
        rows[5].addWidget(c)
        self.fs_green = c

        rows[5].setContentsMargins(0, 0, 0, separater_height2)

        # Blue
        c = PushButtonLRM("B")
        c.clicked.connect(self.onSetColorB)
        c.middleClicked.connect(self.onGetColorB)
        rows[6].addWidget(c)

        c = PushButtonLRM("0.00")
        c.clicked.connect(self.onSetColorB000)
        c.setStyleSheet("background-color: #000000; color: white;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[6].addWidget(c)

        c = PushButtonLRM("0.25")
        c.clicked.connect(self.onSetColorB025)
        c.setStyleSheet("background-color: #000040; color: white;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[6].addWidget(c)

        c = PushButtonLRM("0.50")
        c.clicked.connect(self.onSetColorB050)
        c.setStyleSheet("background-color: #000080; color: white;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[6].addWidget(c)

        c = PushButtonLRM("0.75")
        c.clicked.connect(self.onSetColorB075)
        c.setStyleSheet("background-color: #0000c0; color: black;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[6].addWidget(c)

        c = PushButtonLRM("1.00")
        c.clicked.connect(self.onSetColorB100)
        c.setStyleSheet("background-color: #0000FF; color: black;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[6].addWidget(c)

        rows[6].setContentsMargins(0, 0, 0, separater_height1)

        c = EditBoxFloatDraggable()
        c.setValidator(QDoubleValidator())
        c.validator().setDecimals(self.editbox_precision)
        c.setText(self.to_real_text(1.0))
        c.dragged.connect(self.onDragEditBoxBlue)
        c.editingFinished.connect(self.onChangeEditBoxBlue)
        c.installEventFilter(self)
        c.setFixedHeight(row_height2)
        c.setFixedWidth(edit_box_width)
        rows[7].addWidget(c)
        self.eb_blue = c

        c = QSlider(Qt.Horizontal)
        c.setRange(self.to_inner_value(0.0), self.to_inner_value(1.0))
        c.setValue(self.to_inner_value(1.0))
        c.sliderMoved.connect(self.onDragBlue)
        c.sliderReleased.connect(self.onChangeSliderBlue)
        c.installEventFilter(self)
        c.setFixedHeight(row_height2)
        rows[7].addWidget(c)
        self.fs_blue = c

        rows[7].setContentsMargins(0, 0, 0, separater_height2)

        # Alpha
        c = PushButtonLRM("A")
        c.clicked.connect(self.onSetColorA)
        c.middleClicked.connect(self.onGetColorA)
        rows[8].addWidget(c)

        c = PushButtonLRM("0.00")
        c.clicked.connect(self.onSetColorA000)
        c.setStyleSheet("background-color: #000000; color: white;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[8].addWidget(c)

        c = PushButtonLRM("0.25")
        c.clicked.connect(self.onSetColorA025)
        c.setStyleSheet("background-color: #404040; color: white;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[8].addWidget(c)

        c = PushButtonLRM("0.50")
        c.clicked.connect(self.onSetColorA050)
        c.setStyleSheet("background-color: #808080; color: white;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[8].addWidget(c)

        c = PushButtonLRM("0.75")
        c.clicked.connect(self.onSetColorA075)
        c.setStyleSheet("background-color: #c0c0c0; color: black;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[8].addWidget(c)

        c = PushButtonLRM("1.00")
        c.clicked.connect(self.onSetColorA100)
        c.setStyleSheet("background-color: #FFFFFF; color: black;")
        c.setFixedHeight(row_height1)
        c.setFixedWidth(button_width2)
        rows[8].addWidget(c)

        rows[8].setContentsMargins(0, 0, 0, separater_height1)

        c = EditBoxFloatDraggable()
        c.setValidator(QDoubleValidator())
        c.validator().setDecimals(self.editbox_precision)
        c.setText(self.to_real_text(1.0))
        c.dragged.connect(self.onDragEditBoxAlpha)
        c.editingFinished.connect(self.onChangeEditBoxAlpha)
        c.installEventFilter(self)
        c.setFixedHeight(row_height2)
        c.setFixedWidth(edit_box_width)
        rows[9].addWidget(c)
        self.eb_alpha = c

        c = QSlider(Qt.Horizontal)
        c.setRange(self.to_inner_value(0.0), self.to_inner_value(1.0))
        c.setValue(self.to_inner_value(1.0))
        c.sliderMoved.connect(self.onDragAlpha)
        c.sliderReleased.connect(self.onChangeSliderAlpha)
        c.installEventFilter(self)
        c.setFixedHeight(row_height2)
        rows[9].addWidget(c)
        self.fs_alpha = c

        rows[9].setContentsMargins(0, 0, 0, separater_height2)

    def eventFilter(self, source, event):
        """イベントフィルター"""
        if event.type() == QEvent.MouseMove:
            if source == self.fs_red:
                channel = "r"

            elif source == self.fs_red:
                channel = "g"

            elif source == self.fs_red:
                channel = "b"

            elif source == self.fs_red:
                channel = "a"

            else:
                return False

            self._on_drag_slider(channel=channel)

        return False

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
            inner_values = [self.to_inner_value(x) for x in color]
            self.fs_red.setValue(inner_values[0])
            self.fs_green.setValue(inner_values[1])
            self.fs_blue.setValue(inner_values[2])
            self.fs_alpha.setValue(inner_values[3])

            self._sync_slider_and_editbox(from_slider=True)

    def onSetColorRGBA(self, *args):
        """スライダーの値でRGBAを全て設定する"""
        selection = cmds.ls(selection=True)

        if selection:
            r = self.to_actual_value(self.fs_red.value())
            g = self.to_actual_value(self.fs_green.value())
            b = self.to_actual_value(self.fs_blue.value())
            a = self.to_actual_value(self.fs_alpha.value())

            targets = cmds.polyListComponentConversion(selection, tvf=True)
            cmds.polyColorPerVertex(targets, r=r, g=g, b=b, a=a)

    def onGetColorR(self, *args):
        """選択している全ての頂点の頂点カラーの平均の R 成分をスライダーに設定する"""
        color = self._get_color()

        if color:
            self.fs_red.setValue(self.to_inner_value(color[0]))

            self._sync_slider_and_editbox(from_slider=True)

    def onGetColorG(self, *args):
        """選択している全ての頂点の頂点カラーの平均の G 成分をスライダーに設定する"""
        color = self._get_color()

        if color:
            self.fs_green.setValue(self.to_inner_value(color[1]))

            self._sync_slider_and_editbox(from_slider=True)

    def onGetColorB(self, *args):
        """選択している全ての頂点の頂点カラーの平均の B 成分をスライダーに設定する"""
        color = self._get_color()

        if color:
            self.fs_blue.setValue(self.to_inner_value(color[2]))

            self._sync_slider_and_editbox(from_slider=True)

    def onGetColorA(self, *args):
        """選択している全ての頂点の頂点カラーの平均の A 成分をスライダーに設定する"""
        color = self._get_color()

        if color:
            self.fs_alpha.setValue(self.to_inner_value(color[3]))

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
        slider = self.get_slider(channel)
        v = self.to_actual_value(slider.value())

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

    def _set_slider_value_with_channel(self, channel, actual_value, sync=False):
        v = self.to_inner_value(actual_value)
        slider = self.get_slider(channel)
        slider.setValue(v)

        if sync:
            self._sync_slider_and_editbox(from_slider=True)

    def onSetColorR000(self, *args):
        """R を 0.00 に設定する"""
        self._set_slider_value_with_channel("r", 0.0, sync=True)
        self._on_set_color(channel="r", drag=False)

    def onSetColorR025(self, *args):
        """R を 0.25 に設定する"""
        self._set_slider_value_with_channel("r", 0.25, sync=True)
        self._on_set_color(channel="r", drag=False)

    def onSetColorR050(self, *args):
        """R を 0.50 に設定する"""
        self._set_slider_value_with_channel("r", 0.5, sync=True)
        self._on_set_color(channel="r", drag=False)

    def onSetColorR075(self, *args):
        """R を 0.75 に設定する"""
        self._set_slider_value_with_channel("r", 0.75, sync=True)
        self._on_set_color(channel="r", drag=False)

    def onSetColorR100(self, *args):
        """R を 1.00 に設定する"""
        self._set_slider_value_with_channel("r", 1.0, sync=True)
        self._on_set_color(channel="r", drag=False)

    def onSetColorG000(self, *args):
        """G を 0.00 に設定する"""
        self._set_slider_value_with_channel("g", 0.0, sync=True)
        self._on_set_color(channel="g", drag=False)

    def onSetColorG025(self, *args):
        """G を 0.25 に設定する"""
        self._set_slider_value_with_channel("g", 0.25, sync=True)
        self._on_set_color(channel="g", drag=False)

    def onSetColorG050(self, *args):
        """G を 0.50 に設定する"""
        self._set_slider_value_with_channel("g", 0.5, sync=True)
        self._on_set_color(channel="g", drag=False)

    def onSetColorG075(self, *args):
        """G を 0.75 に設定する"""
        self._set_slider_value_with_channel("g", 0.75, sync=True)
        self._on_set_color(channel="g", drag=False)

    def onSetColorG100(self, *args):
        """G を 1.00 に設定する"""
        self._set_slider_value_with_channel("g", 1.0, sync=True)
        self._on_set_color(channel="g", drag=False)

    def onSetColorB000(self, *args):
        """B を 0.00 に設定する"""
        self._set_slider_value_with_channel("b", 0.0, sync=True)
        self._on_set_color(channel="b", drag=False)

    def onSetColorB025(self, *args):
        """B を 0.25 に設定する"""
        self._set_slider_value_with_channel("b", 0.25, sync=True)
        self._on_set_color(channel="b", drag=False)

    def onSetColorB050(self, *args):
        """B を 0.50 に設定する"""
        self._set_slider_value_with_channel("b", 0.5, sync=True)
        self._on_set_color(channel="b", drag=False)

    def onSetColorB075(self, *args):
        """B を 0.75 に設定する"""
        self._set_slider_value_with_channel("b", 0.75, sync=True)
        self._on_set_color(channel="b", drag=False)

    def onSetColorB100(self, *args):
        """B を 1.00 に設定する"""
        self._set_slider_value_with_channel("b", 1.0, sync=True)
        self._on_set_color(channel="b", drag=False)

    def onSetColorA000(self, *args):
        """A を 0.00 に設定する"""
        self._set_slider_value_with_channel("a", 0.0, sync=True)
        self._on_set_color(channel="a", drag=False)

    def onSetColorA025(self, *args):
        """A を 0.25 に設定する"""
        self._set_slider_value_with_channel("a", 0.25, sync=True)
        self._on_set_color(channel="a", drag=False)

    def onSetColorA050(self, *args):
        """A を 0.50 に設定する"""
        self._set_slider_value_with_channel("a", 0.5, sync=True)
        self._on_set_color(channel="a", drag=False)

    def onSetColorA075(self, *args):
        """A を 0.75 に設定する"""
        self._set_slider_value_with_channel("a", 0.75, sync=True)
        self._on_set_color(channel="a", drag=False)

    def onSetColorA100(self, *args):
        """A を 1.00 に設定する"""
        self._set_slider_value_with_channel("a", 1.0, sync=True)
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
            v = self.to_actual_value(self.fs_red.value())
            self.eb_red.setText(self.to_real_text(v))

            v = self.to_actual_value(self.fs_green.value())
            self.eb_green.setText(self.to_real_text(v))

            v = self.to_actual_value(self.fs_blue.value())
            self.eb_blue.setText(self.to_real_text(v))

            v = self.to_actual_value(self.fs_alpha.value())
            self.eb_alpha.setText(self.to_real_text(v))

        # エディットボックスを元にスライダーを変更
        if from_editbox:
            v = self.to_inner_value(float(self.eb_red.text()))
            self.fs_red.setValue(v)

            v = self.to_inner_value(float(self.eb_green.text()))
            self.fs_green.setValue(v)

            v = self.to_inner_value(float(self.eb_blue.text()))
            self.fs_blue.setValue(v)

            v = self.to_inner_value(float(self.eb_alpha.text()))
            self.fs_alpha.setValue(v)

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

    def get_slider(self, channel):
        if channel == "r":
            return self.fs_red
        elif channel == "g":
            return self.fs_green
        elif channel == "b":
            return self.fs_blue
        elif channel == "a":
            return self.fs_alpha
        else:
            return None

    def get_editbox(self, channel):
        if channel == "r":
            return self.eb_red
        elif channel == "g":
            return self.eb_green
        elif channel == "b":
            return self.eb_blue
        elif channel == "a":
            return self.eb_alpha
        else:
            return None

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
            # TODO: Qt に置き換えてドラッグのメッセージ来る方向が違うのでこの辺は書き換えて
            b_down = ui.is_key_pressed(ui.vk.VK_B)

            slider = self.get_slider(channel)
            current_v = self.to_actual_value(slider.value())

            if b_down and not self.brush_size_mode:
                # 押し下げ時
                self.brush_size_mode = True
                self.cached_value = current_v
                self.cached_size = cmds.softSelect(q=True, ssd=True)
                self.start_pos = QCursor.pos().y()

            elif b_down and self.brush_size_mode:
                # 押し下げ継続時
                mul = 0.1
                lower_limit = 0.0001
                current_pos = QCursor.pos().y()
                new_size = self.cached_size + (self.start_pos - current_pos) * mul
                new_size = max(new_size, lower_limit)
                cmds.softSelect(ssd=new_size)

                slider.setValue(self.to_inner_value(self.cached_value))

            elif not b_down and self.brush_size_mode:
                # 押し上げ時
                self.brush_size_mode = False
                slider.setValue(self.to_inner_value(self.cached_value))

            else:
                pass

            self._on_set_color(channel=channel, drag=True)

        self._sync_slider_and_editbox(from_slider=True)

    def onDragRed(self, *args):
        """R スライダードラッグ中のハンドラ"""
        if self.brush_size_mode:
            slider = self.get_slider("r")
            slider.setValue(self.to_inner_value(self.cached_value))

    def onDragGreen(self, *args):
        """G スライダードラッグ中のハンドラ"""
        if self.brush_size_mode:
            slider = self.get_slider("g")
            slider.setValue(self.to_inner_value(self.cached_value))

    def onDragBlue(self, *args):
        """B スライダードラッグ中のハンドラ"""
        if self.brush_size_mode:
            slider = self.get_slider("b")
            slider.setValue(self.to_inner_value(self.cached_value))

    def onDragAlpha(self, *args):
        """A スライダードラッグ中のハンドラ"""
        if self.brush_size_mode:
            slider = self.get_slider("a")
            slider.setValue(self.to_inner_value(self.cached_value))

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


def maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    if main_window_ptr is not None:
        return wrapInstance(int(main_window_ptr), QMainWindow)
    else:
        return None


def main():
    window = NN_ToolWindow(parent=maya_main_window())
    window.create()


if __name__ == "__main__":
    main()
