import re

import maya.cmds as cmds

import nnutil.core as nu
import nnutil.display as nd
import nnutil.ui as ui

# TODO: カーブを比率で分割しても曲率の違いで 全体曲線:部分曲線 と 全体折れ線:部分直線 の比率が一致しない問題どうにかする (元の比率をキャッシュする？)
# TODO: ループ時の対応 (メッセージ出しつつ適当な所始点にしてしまいたい)
# TODO: コンポーネントIDが変化したときに元の形状に近いエッジ列を推定する機能

# TODO: U値スライダー

DEBUG = False


window_name = "NN_Curve"
window = None


def get_window():
    return window


# アトリビュートにエッジ列を文字列で保存する際の区切り文字
component_separator = ','

# このツールで生成されるカーブノードの名称につけるプリフィックス
curve_prefix = "NNAEOC_Curve"

# エッジ列をカーブに保存する際のカスタムアトリビュート名
attr_name = "dst_edges"


def printd(description, message):
    if DEBUG:
        print(str(description) + ": " + str(message))


def addAttributes(curve, edges):
    """
    カーブオブジェクトにアトリビュート追加
    """

    edges_str = edges
    curve_str = curve
    attr_fullname = curve_str + "." + attr_name

    if not cmds.attributeQuery(attr_name, node=curve_str, exists=True):
        cmds.addAttr(curve_str, ln=attr_name, dt="string")

    cmds.setAttr(attr_fullname, edges_str, e=True, type="string")
    cmds.setAttr(attr_fullname, e=True, channelBox=True)


def changeAppearance(curve):
    """カーブの見た目を変更する"""
    line_width = 2
    color = [1.0, 0.3, 0.0]

    cmds.setAttr('%s.lineWidth' % curve, line_width)
    cmds.setAttr('%s.overrideEnabled' % curve, 1)
    cmds.setAttr('%s.overrideRGBColors' % curve, 1)
    cmds.setAttr('%s.overrideColorR' % curve, color[0])
    cmds.setAttr('%s.overrideColorG' % curve, color[1])
    cmds.setAttr('%s.overrideColorB' % curve, color[2])
    cmds.setAttr('%s.useOutlinerColor' % curve, True)
    cmds.setAttr('%s.outlinerColor' % curve, color[0], color[1], color[2])


def makeCurve(edges, n=4):
    """
    引数のエッジ列からカーブを生成してアトリビュート付与する
    連続しない複数エッジ列の場合はエラーを返す (エッジ列の分割は関数の外で行う)
    """
    # カーブ作成
    cmds.select(edges, replace=True)
    curve = cmds.polyToCurve(form=2, degree=3, conformToSmoothMeshPreview=1)[0]

    # リビルドしてヒストリ消す
    cmds.rebuildCurve(curve, ch=1, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s=n, d=3, tol=0.01)
    cmds.DeleteHistory(curve)

    # 見た目の変更
    changeAppearance(curve)

    # 選択エッジ集合と構成頂点
    edge_set = edges
    vtx_set = cmds.filterExpand(
        cmds.polyListComponentConversion(edges, fe=True, tv=True), sm=31)

    end_vts = nu.get_end_vtx_e(edge_set)

    # 開いた状態の連続した一本のエッジ列以外は現状エラーで終了
    if not len(end_vts) == 2:
        raise Exception

    sorted_vts = nu.sortVtx(edge_set, end_vts[0])

    # カーブの始点終点と頂点リストお始点終点が逆なら頂点リストを反転する
    if not nu.isStart(sorted_vts[0], curve):
        sorted_vts.reverse()

    addAttributes(curve, edges)

    return [curve, edges]


def alignEdgesOnCurve(edges, curve, keep_ratio_mode=True, n=4):
    """
    edges 編集するエッジ
    curve 整形に使用するカーブ
    keep_ratio_mode Trueなら元のエッジの長さの比率を維持する, False なら頂点をカーブ上に均等配置する
    """

    # 内部リビルド
    # 直線時に開始位置がずれるバグ対策も兼ね
    target_curve = cmds.duplicate(curve)
    k = 8
    cmds.rebuildCurve(target_curve, ch=1, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s=n*k, d=3, tol=0.01)
    cmds.DeleteHistory(target_curve)

    # 選択エッジ集合と構成頂点
    edge_set = edges
    vtx_set = cmds.filterExpand(
        cmds.polyListComponentConversion(edges, fe=True, tv=True), sm=31)

    end_vts = nu.get_end_vtx_e(edge_set)

    # 閉じていない連続した一本のエッジ列以外は現状エラーで終了
    if not len(end_vts) == 2:
        raise(Exception)

    sorted_vts = nu.sortVtx(edge_set, end_vts[0])

    # カーブの始点終点と頂点リストお始点終点が逆なら頂点リストを反転する
    if not nu.isStart(sorted_vts[0], target_curve):
        sorted_vts.reverse()

    # 各頂点の移動先の座標を計算
    new_positions = []

    if keep_ratio_mode:
        # 頂点列間の比率を維持してカーブに再配置
        for i in range(len(sorted_vts)):
            u = nu.vtxListPath(sorted_vts, i)/nu.vtxListPath(sorted_vts)
            new_positions.append(cmds.pointOnCurve(target_curve, pr=u, p=True))

    else:  # even space mode
        # 頂点列間の比率を無視してカーブに等間隔で配置
        for i in range(len(sorted_vts)):
            u = float(i)/(len(sorted_vts)-1)
            new_positions.append(cmds.pointOnCurve(target_curve, pr=u, p=True))

    # 実際のコンポーネント移動
    for i in range(len(sorted_vts)):
        cmds.xform(sorted_vts[i], ws=True, t=new_positions[i])

    cmds.delete(target_curve)

    return [target_curve, edges]

    # TODO: カーブ・エッジの同期モード欲しい
    """
      両方向コンストレイント
      頂点が変更されたらカーブを再生成
      カーブが変更されたら keep ratio mode で頂点を更新する
      カーブで形を変えて、頂点でエッジフローだけ直すのを平行してやる感じ
    """


def isValid(curve):
    """
    このツールで利用できる有効なカーブかどうかの判定
    """
    return cmds.attributeQuery(attr_name, node=curve, exists=True)


def isAvailable(curve):
    """
    processAll 時に fitToCurve を適用するなら Trueを返す
    現状はビジビリティで判定
    """
    return cmds.getAttr("%(curve)s.visibility" % locals())


def getAllCurves():
    """
    このツールで生成したカーブをすべて取得する
    """
    return cmds.ls(curve_prefix + "*")


class NN_ToolWindow(object):

    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (10, 10)

    def create(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)

        # プリファレンスの有無による分岐
        if cmds.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = cmds.windowPref(self.window, q=True, topLeftCorner=True)
            cmds.windowPref(self.window, remove=True)

            # 前回位置に指定したサイズで表示
            cmds.window(
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
        window_width = 255

        ui.column_layout()

        ui.row_layout()
        ui.header(label='Make')
        ui.button(label='Make Curve', c=self.onMakeCurve)
        ui.end_layout()

        ui.separator(width=window_width)

        ui.row_layout()
        ui.header(label='Curve')
        self.ed_curve = cmds.textField(tx='')
        ui.button(label='Set', c=self.onSetCurve)
        ui.button(label='Sel', c=self.onSelectCurve)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='Edges')
        self.ed_edges = cmds.textField(tx='')
        ui.button(label='Set', c=self.onSetEdges)
        ui.button(label='Sel', c=self.onSelectEdges)
        ui.end_layout()

        ui.separator(width=window_width)

        ui.row_layout()
        ui.button(label='Active', c=self.onSetActive, width=ui.width(2))
        ui.button(label='Fit to Curve', c=self.onFitActive, width=ui.width(2.5))
        ui.button(label='Smooth', c=self.onSmoothActive, width=ui.width(2.5))
        self.cb_keep_ratio_mode = cmds.checkBox(l='keep ratio', v=True, cc=self.onSetKeepRatio)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='Remake', c=self.onReMakeCurve, width=ui.width(2.5))
        ui.button(label='Reassign', c=self.onReAssignEdges, width=ui.width(2.5))
        ui.end_layout()

        ui.row_layout()
        ui.header(label="")
        ui.button(label='Rebuild', c=self.onRebuildActive, width=ui.width(2.5))
        ui.button(label='/2', c=self.onRebuildResolutionDiv2)
        self.tx_rebuild_resolution = cmds.textField(tx='2', width=32)
        ui.button(label='x2', c=self.onRebuildResolutionMul2)
        ui.end_layout()

        ui.separator(width=window_width)

        ui.row_layout()
        ui.header(label='Selected')
        ui.button(label='Fit', c=self.onFitSelection)
        ui.button(label='Rebuild [Op]', c=self.onRebuildSelection, dgc=self.onRebuildOp, width=ui.width(2.8))
        ui.button(label='Smooth [Op]', c=self.onSmoothSelection, dgc=self.onSmoothOp, width=ui.width(2.8))
        ui.end_layout()

        ui.separator(width=window_width)

        ui.row_layout()
        ui.header(label='Select')
        ui.button(label='All', c=self.onSelectAll)
        ui.button(label='Visible [invis]', c=self.onSelectVisible, dgc=self.onSelectInvisible)
        ui.end_layout()

        ui.separator(width=window_width)

        ui.row_layout()
        ui.header(label='Display')
        ui.button(label='Draw On Top [off]', c=self.onEnableDrawOnTop, dgc=self.onDisableDrawOnTop, width=ui.width(3.8))
        ui.button(label="Show Curve [off]", c=self.onShowCurve, dgc=self.onHideCurve, width=ui.width(3.8))
        ui.end_layout()

        ui.separator(width=window_width)

        ui.end_layout()

    def onSetKeepRatio(self, *args):
        pass

    def onMakeCurve(self, *args):
        """
        カーブ生成とアトリビュート設定
        """
        keep_ratio_mode = cmds.checkBox(self.cb_keep_ratio_mode, q=True, v=True)
        resolution = int(cmds.textField(self.tx_rebuild_resolution, q=True, tx=True))

        selections = cmds.ls(selection=True, flatten=True)

        polyline_list = nu.get_all_polylines(selections)    

        curves = []

        for edges in polyline_list:
            # 選択エッジ列からカーブ生成
            ret = makeCurve(edges, n=resolution)
            curve = ret[0]
            edges = ret[1]

            # リネーム
            curve = cmds.rename(curve, curve_prefix, ignoreShape=True)

            # 生成されたカーブと選択エッジをエディットボックスに設定
            edges_str = component_separator.join(edges)
            cmds.textField(self.ed_edges, e=True, tx=edges_str)
            curve_str = curve
            cmds.textField(self.ed_curve, e=True, tx=curve_str)

            # カーブオブジェクトにアトリビュート追加
            edges_str = cmds.textField(self.ed_edges, q=True, tx=True)
            curve_str = cmds.textField(self.ed_curve, q=True, tx=True)
            addAttributes(curve_str, edges_str)

            curves.append(curve_str)

        # 生成カーブの選択
        cmds.select(curves)

        # 生成カーブを全ての isolation セットに追加
        all_isolation_sets = [x for x in cmds.ls(type="objectSet") if re.match(r"modelPanel\dViewSelectedSet", x)]

        for set_name in all_isolation_sets:
            cmds.sets(curves, e=True, add=set_name)

    def onSetActive(self, *args):
        """
        選択オブジェクトとカーブからフィールドを入力
        メッシュとカーブが選択されている場合
            カーブは選択カーブをそのまま
            エッジ列はカーブの始点終点の最短パスエッジ列を設定
        カーブのみ選択されている場合は特殊アトリビュートが存在すればその値をセットする
            アトリビュート無しカーブのみの選択なら警告して何もしない
        """
        # TODO:オブジェクトとカーブ選択した場合の処理実装して

        selections = cmds.ls(selection=True)

        if len(selections) == 0:
            return

        if curve_prefix in selections[0]:
            curve_str = selections[0]
            attr_fullname = curve_str + "." + attr_name
            edges_str = cmds.getAttr(attr_fullname)
            cmds.textField(self.ed_curve, e=True, tx=curve_str)
            cmds.textField(self.ed_edges, e=True, tx=edges_str)

    def onSetEdges(self, *args):
        """
        選択エッジの取得
        """
        edges = cmds.ls(selection=True, flatten=True)
        edges_str = component_separator.join(edges)
        cmds.textField(self.ed_edges, e=True, tx=edges_str)

        # カーブオブジェクトにアトリビュート追加
        edges_str = cmds.textField(self.ed_edges, q=True, tx=True)
        curve_str = cmds.textField(self.ed_curve, q=True, tx=True)
        if curve_str != "":
            addAttributes(curve_str, edges_str)

    def onSelectEdges(self, *args):
        edges_str = cmds.textField(self.ed_edges, q=True, tx=True)
        edges = edges_str.split(component_separator)

        curve_str = cmds.textField(self.ed_curve, q=True, tx=True)
        curve = curve_str

        cmds.select(edges)

    def onSetCurve(self, *args):
        """
        選択カーブの取得
        """
        curve = cmds.ls(selection=True, flatten=True)[0]
        cmds.textField(self.ed_curve, e=True, tx=curve)

        # カーブオブジェクトにアトリビュート追加
        edges_str = cmds.textField(self.ed_edges, q=True, tx=True)
        curve_str = cmds.textField(self.ed_curve, q=True, tx=True)
        if curve_str != "":
            addAttributes(curve_str, edges_str)

    def onSelectCurve(self, *args):
        edges_str = cmds.textField(self.ed_edges, q=True, tx=True)
        edges = edges_str.split(component_separator)

        curve_str = cmds.textField(self.ed_curve, q=True, tx=True)
        curve = curve_str

        cmds.select(curve)

    def onFitActive(self, *args):
        edges_str = cmds.textField(self.ed_edges, q=True, tx=True)
        edges = edges_str.split(component_separator)
        curve_str = cmds.textField(self.ed_curve, q=True, tx=True)
        curve = curve_str
        keep_ratio_mode = cmds.checkBox(
            self.cb_keep_ratio_mode, q=True, v=True)

        n = int(cmds.textField(self.tx_rebuild_resolution, q=True, tx=True))
        alignEdgesOnCurve(edges, curve_str, keep_ratio_mode)

        # Alt 押下時は削除
        if ui.is_alt():
            cmds.delete(curve)

    def onFitSelection(self, *args):
        """ 選択カーブのみ fit to curve """
        select_objects = [nu.get_object(x) for x in cmds.ls(selection=True)]
        curves = [x for x in select_objects if isValid(x)]

        for curve in curves:
            curve_str = curve
            if isValid(curve_str) and isAvailable(curve_str):
                attr_fullname = curve_str + "." + attr_name
                edges_str = cmds.getAttr(attr_fullname)
                edges = edges_str.split(component_separator)
                keep_ratio_mode = cmds.checkBox(self.cb_keep_ratio_mode, q=True, v=True)
                alignEdgesOnCurve(edges, curve_str, keep_ratio_mode)

        cmds.select(select_objects)

        # Alt 押下時は削除
        if ui.is_alt():
            cmds.delete(curves)

    def onFitAll(self, *args):
        """ 全カーブfit to curve """

        all_curves = getAllCurves()
        for curve in all_curves:
            curve_str = curve
            if isValid(curve_str) and isAvailable(curve_str):
                attr_fullname = curve_str + "." + attr_name
                edges_str = cmds.getAttr(attr_fullname)
                edges = edges_str.split(component_separator)
                keep_ratio_mode = cmds.checkBox(self.cb_keep_ratio_mode, q=True, v=True)
                alignEdgesOnCurve(edges, curve_str, keep_ratio_mode)

    def onReMakeCurve(self, *args):
        """
        アクティブエッジでアクティブカーブを作り直す
        """
        edges_str = cmds.textField(self.ed_edges, q=True, tx=True)
        edges = edges_str.split(component_separator)

        curve_str = cmds.textField(self.ed_curve, q=True, tx=True)
        curve = curve_str

        # 既存カーブの削除
        cmds.delete(curve)

        cmds.select(edges)
        new_curve = cmds.polyToCurve(
            form=2, degree=3, conformToSmoothMeshPreview=1)[0]
        cmds.rebuildCurve(new_curve, ch=1, rpo=1, rt=0, end=1,
                          kr=0, kcp=0, kep=1, kt=0, s=5, d=3, tol=0.01)
        # カーブのヒストリ消す
        cmds.DeleteHistory(new_curve)

        # リネーム
        cmds.rename(new_curve, curve)

        cmds.textField(self.ed_curve, e=True, tx=curve)

        # カーブオブジェクトにアトリビュート追加
        addAttributes(curve_str, edges_str)

    def onReAssignEdges(self, *args):
        """
        カーブの形状からエッジ列を再設定
        """
        nd.message("not implemented")
        pass

    def onRebuildResolutionDiv2(self, *args):
        n = int(cmds.textField(self.tx_rebuild_resolution, q=True, tx=True))
        cmds.textField(self.tx_rebuild_resolution, e=True, tx=n//2)

    def onRebuildResolutionMul2(self, *args):
        n = int(cmds.textField(self.tx_rebuild_resolution, q=True, tx=True))
        cmds.textField(self.tx_rebuild_resolution, e=True, tx=n*2)

        if n <= 0:
            cmds.textField(self.tx_rebuild_resolution, e=True, tx=1)

    def rebuild_with_setting(self, curve_str, n):
        if n <= 0:
            cmds.rebuildCurve(curve_str, ch=1, rpo=1, rt=0, end=1, kr=2, kcp=0, kep=1, kt=0, s=1, d=1, tol=0.01)
        else:
            cmds.rebuildCurve(curve_str, ch=1, rpo=1, rt=0, end=1, kr=0, kcp=0, kep=1, kt=0, s=n, d=3, tol=0.01)

    def onRebuildActive(self, *args):
        curve_str = cmds.textField(self.ed_curve, q=True, tx=True)
        n = int(cmds.textField(self.tx_rebuild_resolution, q=True, tx=True))
        self.rebuild_with_setting(curve_str, n)
        cmds.select(curve_str)
        cmds.selectMode(component=True)
        cmds.selectType(cv=True)

    def onRebuildSelection(self, *args):
        curves = [x for x in cmds.ls(selection=True) if isValid(x)]
        n = int(cmds.textField(self.tx_rebuild_resolution, q=True, tx=True))

        for curve_str in curves:
            self.rebuild_with_setting(curve_str, n)

        cmds.select(curves)
        cmds.selectMode(component=True)
        cmds.selectType(cv=True)

    def onRebuildAll(self, *args):
        curves = getAllCurves()
        n = int(cmds.textField(self.tx_rebuild_resolution, q=True, tx=True))

        for curve_str in curves:
            self.rebuild_with_setting(curve_str, n)

        cmds.select(curves)
        cmds.selectMode(component=True)
        cmds.selectType(cv=True)

    def onRebuildOp(self, *args):
        cmds.RebuildCurveOptions()

    def smooth_with_setting(self, curve_str):
        target_str = curve_str + ".cv[*]"
        cmds.smoothCurve(target_str, ch=1, rpo=1, s=1)

    def onSmoothActive(self, *args):
        curve_str = cmds.textField(self.ed_curve, q=True, tx=True)
        self.smooth_with_setting(curve_str)

    def onSmoothSelection(self, *args):
        curves = [x for x in cmds.ls(selection=True) if isValid(x)]

        for curve_str in curves:
            self.smooth_with_setting(curve_str)

        cmds.select(curves)

    def onSmoothAll(self, *args):
        curves = getAllCurves()

        for curve_str in curves:
            self.smooth_with_setting(curve_str)

    def onSmoothOp(self, *args):
        cmds.SmoothCurveOptions()

    def onSelectAll(self, *args):
        """
        すべてのカーブを選択する
        """
        all_curves = getAllCurves()
        cmds.select(all_curves)

        # Alt 押下時は削除
        if ui.is_alt():
            cmds.delete(all_curves)

    def onSelectActive(self, *args):
        """
        アクティブなカーブを選択する
        """
        curve_str = cmds.textField(self.ed_curve, q=True, tx=True)
        cmds.select(curve_str)

    def onSelectVisible(self, *args):
        """
        表示されているカーブのみ選択する
        """
        all_curves = getAllCurves()
        visible_curves = [c for c in all_curves if cmds.getAttr(c+".visibility")]
        cmds.select(visible_curves)

    def onSelectInvisible(self, *args):
        """
        非表示のカーブのみ選択する
        """
        all_curves = getAllCurves()
        invisible_curves = [c for c in all_curves if not cmds.getAttr(c+".visibility")]
        cmds.select(invisible_curves)

    def onEnableDrawOnTop(self, *args):
        selections = nu.get_selection()

        for obj in selections:
            if isValid(obj):
                shape = cmds.listRelatives(obj, shapes=True)[0]
                cmds.setAttr(shape + ".alwaysDrawOnTop", 1)

    def onDisableDrawOnTop(self, *args):
        selections = nu.get_selection()

        for obj in selections:
            if isValid(obj):
                shape = cmds.listRelatives(obj, shapes=True)[0]
                cmds.setAttr(shape + ".alwaysDrawOnTop", 0)

    def onShowCurve(self, *args):
        """"""
        active_panel = cmds.getPanel(withFocus=True)
        panel_type = cmds.getPanel(typeOf=active_panel)

        if panel_type == "modelPanel":
            cmds.modelEditor(active_panel, e=True, nurbsCurves=True)

    def onHideCurve(self, *args):
        """"""
        active_panel = cmds.getPanel(withFocus=True)
        panel_type = cmds.getPanel(typeOf=active_panel)

        if panel_type == "modelPanel":
            cmds.modelEditor(active_panel, e=True, nurbsCurves=False)

    def _add_isolation(self, objects):
        """指定のオブジェクトを isolate に追加する"""
        active_panel = cmds.getPanel(withFocus=True)

        for obj in objects:
            cmds.isolateSelect(active_panel, addDagObject=obj)


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
