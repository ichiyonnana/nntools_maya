#! python
# coding:utf-8
"""
ツールの概要
"""
import sys

if sys.version_info.major >= 3:
    import importlib

import pymel.core as pm

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import nnutil.display as nd

from PySide2 import QtGui

window_name = "NN_Launcher"
window = None


def get_window():
    return window


class NN_ToolWindow(object):
    all_modules = [
        "nnmirror",
        "nnuvtoolkit",
        "nncamera",
        "nnringwidth",
        "nncurve",
        "nnsimplify",
        "nnstraighten",
        "nnlattice",
        "nnlauncher",
        "altunt",
        "nnvcolor",
        "nnskin",
        "nnsubdiv",
        "nnanim",
        "nntransform",
        "nnsweep",
        ]

    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (280, 260)

        self.common_button_height = 1.5

        self.is_chunk_open = False

    def create(self):
        if pm.window(self.window, exists=True):
            pm.deleteUI(self.window, window=True)

        cursor_pos = QtGui.QCursor().pos()

        # プリファレンスの有無による分岐
        if pm.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = (cursor_pos.y(), cursor_pos.x())
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
        ui.header(label="Editor:")
        ui.button(label="Mirror", width=ui.width(2), height=ui.height(self.common_button_height), c=self.onMirror)
        ui.button(label="UV", width=ui.width(2), height=ui.height(self.common_button_height), c=self.onUV)
        ui.button(label="Camera", width=ui.width(2), height=ui.height(self.common_button_height), c=self.onCamera)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Align:")
        ui.button(label="RingWidth", width=ui.width(2), height=ui.height(self.common_button_height), c=self.onRingWidth)
        ui.button(label="Curve", width=ui.width(2), height=ui.height(self.common_button_height), c=self.onCurve)
        ui.button(label="Simplify", width=ui.width(2), height=ui.height(self.common_button_height), c=self.onSimplify)
        ui.button(label="Straighten", width=ui.width(2), height=ui.height(self.common_button_height), c=self.onStraighten)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Util:")
        ui.button(label="Lattice", width=ui.width(2), height=ui.height(self.common_button_height), c=self.onLattice)
        ui.button(label="Normal", width=ui.width(2), height=ui.height(self.common_button_height), c=self.onNormal)
        ui.button(label="VColor", width=ui.width(2), height=ui.height(self.common_button_height), c=self.onVColor)
        ui.button(label="Sweep", width=ui.width(2), height=ui.height(self.common_button_height), c=self.onSweep)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="Etc")
        ui.button(label="SKin", width=ui.width(2), height=ui.height(self.common_button_height), c=self.onSKin)
        ui.button(label="Subdiv", width=ui.width(2), height=ui.height(self.common_button_height), c=self.onSubdiv)
        ui.button(label="Anim", width=ui.width(2), height=ui.height(self.common_button_height), c=self.onAnim)
        ui.button(label="Transform", width=ui.width(2), height=ui.height(self.common_button_height), c=self.onTransform)
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.button(label="Close All", width=ui.width(2), height=ui.height(self.common_button_height), c=self.onCloseAll)
        ui.button(label="Reload All", width=ui.width(2), height=ui.height(self.common_button_height), c=self.onReloadAll)
        ui.end_layout()

        ui.separator(height=ui.height(0.5))

        ui.row_layout()
        ui.header(label="")
        ui.button(label="Close", width=ui.width(8), height=ui.height(self.common_button_height), c=self.onClose)
        ui.end_layout()

        ui.end_layout()

    def onMirror(self, *args):
        """"""
        import nnmirror.core
        nnmirror.core.main()
        if not ui.is_shift():
            pm.deleteUI(self.window, window=True)

    def onUV(self, *args):
        """"""
        import nnuvtoolkit.core
        nnuvtoolkit.core.main()
        if not ui.is_shift():
            pm.deleteUI(self.window, window=True)

    def onCamera(self, *args):
        """"""
        import nncamera.core
        nncamera.core.main()
        if not ui.is_shift():
            pm.deleteUI(self.window, window=True)

    def onRingWidth(self, *args):
        """"""
        import nnringwidth.core
        nnringwidth.core.main()
        if not ui.is_shift():
            pm.deleteUI(self.window, window=True)

    def onCurve(self, *args):
        """"""
        import nncurve.core
        nncurve.core.main()
        if not ui.is_shift():
            pm.deleteUI(self.window, window=True)

    def onSimplify(self, *args):
        """"""
        import nnsimplify.core
        nnsimplify.core.main()
        if not ui.is_shift():
            pm.deleteUI(self.window, window=True)

    def onStraighten(self, *args):
        """"""
        import nnstraighten.core
        nnstraighten.core.main()
        if not ui.is_shift():
            pm.deleteUI(self.window, window=True)

    def onLattice(self, *args):
        """"""
        import nnlattice.core
        nnlattice.core.main()
        if not ui.is_shift():
            pm.deleteUI(self.window, window=True)

    def onNormal(self, *args):
        """"""
        import altunt.core
        altunt.core.main()
        if not ui.is_shift():
            pm.deleteUI(self.window, window=True)

    def onVColor(self, *args):
        """"""
        import nnvcolor.core
        nnvcolor.core.main()
        if not ui.is_shift():
            pm.deleteUI(self.window, window=True)

    def onSweep(self, *args):
        """"""
        import nnsweep.core
        nnsweep.core.main()        
        if not ui.is_shift():
            pm.deleteUI(self.window, window=True)

    def onSKin(self, *args):
        """"""
        import nnskin.core
        nnskin.core.main()
        if not ui.is_shift():
            pm.deleteUI(self.window, window=True)

    def onSubdiv(self, *args):
        """"""
        import nnsubdiv.core
        nnsubdiv.core.main()
        if not ui.is_shift():
            pm.deleteUI(self.window, window=True)

    def onAnim(self, *args):
        """"""
        import nnanim.core
        nnanim.core.main()
        if not ui.is_shift():
            pm.deleteUI(self.window, window=True)

    def onTransform(self, *args):
        """"""
        import nntransform.core
        nntransform.core.main()
        if not ui.is_shift():
            pm.deleteUI(self.window, window=True)

    def onCloseAll(self, *args):
        """全ての NNTools ダイアログを閉じる"""
        for module_name in self.all_modules:
            module = __import__(module_name)

            if pm.window(module.core.window_name, exists=True):
                pm.deleteUI(module.core.window_name, window=True)

        if not ui.is_shift():
            pm.deleteUI(self.window, window=True)

    def onReloadAll(self, *args):
        """全ての NNTools のモジュールをリロードする"""
        for module_name in self.all_modules:
            print("reload %s" % module_name)
            module = __import__(module_name)

            if sys.version_info.major >= 3:
                if hasattr(module, "core"):
                    importlib.reload(module.core)
                else:
                    print("%s has no attribute 'core'" % module_name)

            else:
                reload(module.core)

        if not ui.is_shift():
            pm.deleteUI(self.window, window=True)

    def onClose(self, *args):
        """ランチャーを閉じる"""
        if not ui.is_shift():
            pm.deleteUI(self.window, window=True)


def smart_launch():
    """選択オブジェクト等から自動で適切なツールを起動する"""
    print("smart_launch")


def main():
    """ウインドウの表示
    
    すでに表示されていた場合は閉じるだけ
    """
    global window
    window = NN_ToolWindow()

    if pm.window(window.window, exists=True):
        pm.deleteUI(window.window, window=True)

    else:
        window.create()


if __name__ == "__main__":
    main()
