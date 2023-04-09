#! python
# coding:utf-8
"""
ツールの概要
"""
import pymel.core as pm

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import nnutil.display as nd
import pymel.core.nodetypes as nt


window_name = "NN_Sweep"


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

            # 前回位置に指定したサイズで表示
            self.window = pm.window(
                self.window,
                t=self.title,
                widthHeight=self.size,
                sizeable=False,
                maximizeButton=False,
                minimizeButton=False,
                resizeToFitChildren=True,
                topLeftCorner=position
            )

        else:
            # プリファレンスがなければデフォルト位置に指定サイズで表示
            self.window = pm.window(
                self.window,
                t=self.title,
                widthHeight=self.size,
                sizeable=False,
                maximizeButton=False,
                minimizeButton=False,
                resizeToFitChildren=True
            )

        self.layout()
        pm.showWindow(self.window)

    def layout(self):
        ui.column_layout()

        ui.row_layout()
        ui.header(label="Create:")
        ui.button(label="Sweep", c=self.onCreateSweep)
        ui.end_layout()

        ui.end_layout()

    def onCreateSweep(self, *args):
        """Testハンドラ"""
        selections = pm.ls(selection=True)

        for curve_trs in selections:
            if isinstance(curve_trs.getShape(), nt.NurbsCurve):
                curve_shape = curve_trs.getShape()

                # スウィープの作成
                pm.sweepMeshFromCurve(curve_trs, oneNodePerCurve=True)
                smc_node = pm.listConnections(curve_trs.getShape(), destination=True, type="sweepMeshCreator")[0]

                # 断面の設定
                smc_node.profilePolyType.set(0)
                smc_node.profilePolySides.set(4)
                smc_node.taper.set(1)
                smc_node.interpolationPrecision.set(98)
                smc_node.interpolationOptimize.set(1)

                # テーパー設定
                smc_node.taperCurve[0].taperCurve_Position.set(0.0)
                smc_node.taperCurve[0].taperCurve_FloatValue.set(0.0)
                smc_node.taperCurve[0].taperCurve_Interp.set(3)

                smc_node.taperCurve[2].taperCurve_Position.set(0.5)
                smc_node.taperCurve[2].taperCurve_FloatValue.set(1.0)
                smc_node.taperCurve[2].taperCurve_Interp.set(3)

                smc_node.taperCurve[1].taperCurve_Position.set(1.0)
                smc_node.taperCurve[1].taperCurve_FloatValue.set(0.0)
                smc_node.taperCurve[1].taperCurve_Interp.set(1)

                # メッシュのリファレンス化
                sweep_mesh = pm.listConnections(smc_node, destination=True, type="mesh")[0]
                sweep_mesh.overrideEnabled.set(1)
                sweep_mesh.overrideDisplayType.set(2)

                # カーブの Draw on top 設定
                curve_shape.alwaysDrawOnTop.set(1)
        


    


def main():
    NN_ToolWindow().create()


if __name__ == "__main__":
    main()
