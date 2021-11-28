#! python
# coding:utf-8

import math

import maya.cmds as cmds
import maya.mel as mel

import nnutil.core as nu
import nnutil.ui as ui

MSG_NOT_IMPLEMENTED = "未実装"


def OnewayMatchUV(mode):
    MM_BACK_TO_FRONT = 0
    MM_UNPIN_TO_PIN = 1
    MM_FRONT_TO_BACK = 2
    MM_PIN_TO_UNPIN = 3

    if mode is None:
        match_mode = MM_BACK_TO_FRONT
    elif mode == "front":
        match_mode = MM_BACK_TO_FRONT
    elif mode == "back":
        match_mode = MM_FRONT_TO_BACK
    elif mode == "pin":
        match_mode = MM_UNPIN_TO_PIN
    elif mode == "unpin":
        match_mode = MM_PIN_TO_UNPIN
    else:
        print("unknown match mode: ", mode)
        match_mode = MM_BACK_TO_FRONT

    # 選択UV
    selected_uvs = cmds.ls(selection=True, flatten=True)

    # シェル変換したUV
    cmds.SelectUVShell()
    uvs = cmds.ls(selection=True, flatten=True)

    # 全バックフェース取得
    cmds.SelectUVBackFacingComponents()
    uvs_back = list(set(cmds.ls(selection=True, flatten=True)) & set(uvs))

    # 全フロントフェース取得
    cmds.SelectUVFrontFacingComponents()
    uvs_front = list(set(cmds.ls(selection=True, flatten=True)) & set(uvs))

    # 選択内で pin 取得
    uvs_pined = []
    uvs_unpined = []
    for uv in uvs:
        pin_weight = cmds.polyPinUV(uv, q=True, v=True)[0]
        if pin_weight != 0:
            uvs_pined.append(uv)
        else:
            uvs_unpined.append(uv)

    # 積集合で選択UVをソースとターゲットに分ける
    source_uvs = []
    target_uvs = []
    if match_mode == MM_BACK_TO_FRONT:
        source_uvs = list(set(uvs_front) & set(uvs))
        target_uvs = list(set(uvs_back) & set(uvs))
    elif match_mode == MM_UNPIN_TO_PIN:
        source_uvs = list(set(uvs_pined) & set(uvs))
        target_uvs = list(set(uvs_unpined) & set(uvs))
    elif match_mode == MM_FRONT_TO_BACK:
        source_uvs = list(set(uvs_back) & set(uvs))
        target_uvs = list(set(uvs_front) & set(uvs))
    elif match_mode == MM_UNPIN_TO_PIN:
        source_uvs = list(set(uvs_unpined) & set(uvs))
        target_uvs = list(set(uvs_pined) & set(uvs))
    else:
        pass

    target_uvs = list(set(target_uvs) & set(selected_uvs))

    # ターゲット.each
    for target_uv in target_uvs:
        nearest_uv = source_uvs[0]
        for source_uv in source_uvs:
            if nu.distance_uv(target_uv, source_uv) < nu.distance_uv(target_uv, nearest_uv):
                nearest_uv = source_uv
        nu.copy_uv(target_uv, nearest_uv)
        # TODO:複数のターゲットが束ねられて閉まったソースのセットを作成or選択状態にする

    cmds.select(clear=True)


def half_expand_fold(right_down=True):
    """
    right_down=True で横なら右、縦なら下へ畳む
    """
    # フリップの軸
    FA_U = 0
    FA_V = 1
    flip_axis = FA_U

    # フリップ方向
    # fold 時のみ使用
    FD_TO_LEFT = 0
    FD_TO_RIGHT = 1
    FD_TO_UP = 2
    FD_TO_DOWN = 3
    flip_direction = FD_TO_LEFT

    # 選択UV取得
    selected_uvs = cmds.ls(selection=True, flatten=True)
    cmds.SelectUVShell()
    selected_sehll_uvs = cmds.ls(selection=True, flatten=True)

    if len(selected_uvs) == 0:
        return

    # フリップ軸の決定
    u_dist = [cmds.polyEditUV(x, q=True)[0] for x in selected_uvs]
    u_length = max(u_dist) - min(u_dist)
    v_dist = [cmds.polyEditUV(x, q=True)[1] for x in selected_uvs]
    v_length = max(v_dist) - min(v_dist)

    if u_length < v_length:
        flip_axis = FA_U
        if right_down:
            flip_direction = FD_TO_RIGHT
        else:
            flip_direction = FD_TO_LEFT
    else:
        flip_axis = FA_V
        if right_down:
            flip_direction = FD_TO_DOWN
        else:
            flip_direction = FD_TO_UP

    # 選択UVからピボット決定
    selected_uv_coord_list = [nu.get_uv_coord(x) for x in selected_uvs]
    piv_u = sum([x[0] for x in selected_uv_coord_list]) / len(selected_uv_coord_list)
    piv_v = sum([x[1] for x in selected_uv_coord_list]) / len(selected_uv_coord_list)

    # 裏面の UV 取得
    # expand 用 (expand の操作対象を "軸の外側UV" にすると四つ折りfoldができるけど折ったきりexpandできなくなる)
    backface_uvs = nu.filter_backface_uv_comp(selected_sehll_uvs)

    # 編集対象 UV
    target_uvs = []

    # 編集対象の決定
    if len(backface_uvs) > 0:
        # 裏面があれば裏面が編集対象 (expand動作)
        target_uvs = backface_uvs
    else:
        # 裏面が無ければフリップ外側のUVを編集対象にする (fold動作)
        # 軸よりもフリップ反対方向の UV 取得
        if flip_direction == FD_TO_LEFT:
            target_uvs = [x for x in selected_sehll_uvs if nu.get_uv_coord(x)[0] > piv_u]
        if flip_direction == FD_TO_RIGHT:
            target_uvs = [x for x in selected_sehll_uvs if nu.get_uv_coord(x)[0] < piv_u]
        if flip_direction == FD_TO_UP:
            target_uvs = [x for x in selected_sehll_uvs if nu.get_uv_coord(x)[1] < piv_v]
        if flip_direction == FD_TO_DOWN:
            target_uvs = [x for x in selected_sehll_uvs if nu.get_uv_coord(x)[1] > piv_v]

    # スケール値の決定
    su = 1
    sv = 1

    if flip_axis == FA_U:
        su = -1
    if flip_axis == FA_V:
        sv = -1

    # ピボットを指定して反転処理
    cmds.polyEditUV(target_uvs, pu=piv_u, pv=piv_v, su=su, sv=sv)

    cmds.select(clear=True)


class NN_ToolWindow(object):
    def __init__(self):
        self.window = 'NN_UVToolkit'
        self.title = 'NN_UVToolkit'
        self.size = (350, 95)

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

        self.initialize()

    def layout(self):
        self.columnLayout = ui.column_layout()

        # Projection
        ui.row_layout()
        ui.header(label='Projection')
        ui.button(label='X', c=self.onPlanerX, bgc=ui.color_x)
        ui.button(label='Y', c=self.onPlanerY, bgc=ui.color_y)
        ui.button(label='Z', c=self.onPlanerZ, bgc=ui.color_z)
        ui.button(label='Camera', c=self.onPlanerCamera)
        ui.button(label='Best', c=self.onPlanerBest)
        ui.end_layout()

        # Align & Snap
        ui.row_layout()
        ui.header(label='Align & Snap')
        ui.button(label='Border', c=self.onStraightenBorder)
        ui.button(label='Inner', c=self.onStraightenInner)
        ui.button(label='All', c=self.onStraightenAll)
        ui.button(label='Linear', c=self.onLinearAlign)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='AriGridding', c=self.onGridding)
        ui.button(label='MatchUV', c=self.onMatchUV, dgc=self.onMatchUVOptions)
        ui.end_layout()

        # MatchUV
        ui.row_layout()
        ui.text(label='MatchUV')
        ui.button(label='to Front [back]', c=self.onOnewayMatchUVF, dgc=self.onOnewayMatchUVB, width=ui.button_width3)
        ui.button(label='to Pin [unpin]', c=self.onOnewayMatchUVP, dgc=self.onOnewayMatchUVUp, width=ui.button_width3)
        ui.button(label='expand/fold', c=self.onExpandFoldRD, dgc=self.onExpandFoldLU)
        ui.end_layout()

        # Flip
        ui.row_layout()
        ui.header(label="Flip")
        ui.button(label='FlipU', c=self.onFlipUinTile, bgc=ui.color_u)
        ui.button(label='FlipV', c=self.onFlipVinTile, bgc=ui.color_v)
        self.flip_pivot_u = ui.eb_float(width=ui.button_width2)
        self.flip_pivot_v = ui.eb_float(width=ui.button_width2)
        ui.button(label="get", width=ui.button_width1)
        ui.end_layout()

        # Cut & Sew
        ui.row_layout()
        ui.header(label='Cut & Sew')
        ui.button(label='Cut', c=self.onSewMatchingEdges)
        ui.button(label='Sew', c=self.onSewMatchingEdges)
        ui.button(label='Shell', c=self.onSewMatchingEdges)
        ui.button(label='MatchingE', c=self.onSewMatchingEdges)
        ui.end_layout()

        # Optimize
        ui.row_layout()
        ui.header(label='Optimize')
        ui.button(label='Get', c=self.onGetTexel)
        self.texel = cmds.floatField(cc=self.onChangeTexel, width=ui.button_width2)
        self.mapSize = cmds.intField(cc=self.onChangeMapSize, width=ui.button_width1_5)
        ui.text(label='px')
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='Set', c=self.onSetTexel)
        ui.button(label='U', c=self.onSetEdgeTexelUMin, dgc=self.onSetEdgeTexelUMax, bgc=ui.color_u)
        ui.button(label='V', c=self.onSetEdgeTexelVMin, dgc=self.onSetEdgeTexelVMax, bgc=ui.color_v)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='AriUVRatio', c=self.onUVRatio, dgc=self.onUVRatioOptions)
        ui.button(label='UnfoldU', c=self.onUnfoldU, bgc=ui.color_u)
        ui.button(label='UnfoldV', c=self.onUnfoldV, bgc=ui.color_v)
        ui.end_layout()

        # Checker
        ui.row_layout()
        ui.header(label='Checker')
        ui.text(label="dense:")
        self.checkerDensity = cmds.intField(v=256, cc=self.onChangeUVCheckerDensity, width=ui.button_width1_5)
        ui.button(label='/2', c=self.onUVCheckerDensityDiv2)
        ui.button(label='x2', c=self.onUVCheckerDensityMul2)
        ui.button(label="Toggle", c=self.onToggleChecker)
        ui.end_layout()

        # Layout
        ui.row_layout()
        ui.header(label='Layout')
        ui.button(label='Orient to Edge', c=self.onOrientEdge)
        ui.button(label='Orient Shells', c=self.onOrientShells)
        ui.button(label='SymArrange', c=self.onSymArrange)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='SanpStack', c=self.onSnapStack)
        ui.button(label='Stack', c=self.onStack)
        ui.button(label='Unstack', c=self.onUnStack)
        ui.button(label='Normalize', c=self.onNormalize)
        ui.end_layout()

        # Tools
        ui.row_layout()
        ui.header(label='Tools')
        ui.button(label='Lattice', c=self.onUVLatticeTool)
        ui.button(label='Tweak', c=self.onUVTweakTool)
        ui.button(label='Cut', c=self.onUVCutTool)
        ui.button(label='Optimize', c=self.onUVOptimizeTool)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.button(label='Symmetrize [setU]', c=self.onUVSymmetrizeTool, dgc=self.onSetUVSymmetrizeCenter)
        ui.button(label='Shortest Tool', c=self.onShortestEdgeTool)
        ui.end_layout()

        # Convert
        ui.row_layout()
        ui.header(label='Convert')
        ui.button(label='to Border', c=self.onConvertToShellBorder)
        ui.button(label='to Inner', c=self.onConvertToShellInner)
        ui.end_layout()

        # Select
        ui.row_layout()
        ui.header(label='Select')
        ui.button(label='Frontface', c=self.onSelectFrontface)
        ui.button(label='Backface', c=self.onSelectBackface)
        ui.button(label='All Borders', c=self.onSelectAllUVBorders)
        ui.end_layout()

        # Transform
        ui.row_layout()
        ui.header(label='Transform')
        ui.text(label='Move')
        self.translateValue = cmds.floatField(v=0.1, width=ui.button_width2)
        ui.button(label=u'←', c=self.onTranslateUDiff, bgc=ui.color_u)
        ui.button(label=u'→', c=self.onTranslateUAdd, bgc=ui.color_u)
        ui.button(label=u'↑', c=self.onTranslateVAdd, bgc=ui.color_v)
        ui.button(label=u'↓', c=self.onTranslateVDiff, bgc=ui.color_v)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.header(label='Rotate')
        self.rotationAngle = cmds.floatField(v=90, width=ui.button_width2)
        ui.button(label=u'←', c=self.onRotateLeft)
        ui.button(label=u'→', c=self.onRotateRight)
        ui.end_layout()

        ui.row_layout()
        ui.header(label='')
        ui.header(label='Scale')
        self.scaleValue = cmds.floatField(v=2, width=ui.button_width2)
        ui.button(label='U*', c=self.onOrigScaleUMul, bgc=ui.color_u)
        ui.button(label='U/', c=self.onOrigScaleUDiv, bgc=ui.color_u)
        ui.button(label='V*', c=self.onOrigScaleVMul, bgc=ui.color_v)
        ui.button(label='V/', c=self.onOrigScaleVDiv, bgc=ui.color_v)
        ui.end_layout()

        # Editor
        ui.row_layout()
        ui.header(label="Editor")
        ui.button(label='UVEditor', c=self.onUVEditor)
        ui.button(label='UVToolkit', c=self.onUVToolKit)
        ui.button(label='UVSnapShot', c=self.onUVSnapShot)
        ui.button(label='DrawEdge', c=self.onDrawEdge)
        ui.end_layout()

    def initialize(self):
        # テクセルとマップサイズを UVToolkit から取得
        uvtkTexel = mel.eval("floatField -q -v uvTkTexelDensityField")
        uvtkMapSize = mel.eval("intField -q -v uvTkTexelDensityMapSizeField")
        cmds.floatField(self.texel, e=True, v=uvtkTexel)
        cmds.intField(self.mapSize, e=True, v=uvtkMapSize)

    # getter/setter
    # フォームからの値を取るだけ
    def getTexel(self):
        return cmds.floatField(self.texel, q=True, v=True)

    def getMapSize(self):
        return cmds.intField(self.mapSize, q=True, v=True)

    def onTranslateUAdd(self, *args):
        v = cmds.floatField(self.translateValue, q=True, v=True)
        cmds.polyEditUV(pu=0, pv=0, u=v, v=0)

    def onTranslateUDiff(self, *args):
        v = cmds.floatField(self.translateValue, q=True, v=True)
        cmds.polyEditUV(pu=0, pv=0, u=-v, v=0)

    def onTranslateVAdd(self, *args):
        v = cmds.floatField(self.translateValue, q=True, v=True)
        cmds.polyEditUV(pu=0, pv=0, u=0, v=v)

    def onTranslateVDiff(self, *args):
        v = cmds.floatField(self.translateValue, q=True, v=True)
        cmds.polyEditUV(pu=0, pv=0, u=0, v=-v)

    def onOrigScaleUMul(self, *args):
        v = cmds.floatField(self.scaleValue, q=True, v=True)
        cmds.polyEditUV(pu=0, pv=0, su=v, sv=1)

    def onOrigScaleVMul(self, *args):
        v = cmds.floatField(self.scaleValue, q=True, v=True)
        cmds.polyEditUV(pu=0, pv=0, su=1, sv=v)

    def onOrigScaleUDiv(self, *args):
        v = cmds.floatField(self.scaleValue, q=True, v=True)
        cmds.polyEditUV(pu=0, pv=0, su=1/v, sv=1)

    def onOrigScaleVDiv(self, *args):
        v = cmds.floatField(self.scaleValue, q=True, v=True)
        cmds.polyEditUV(pu=0, pv=0, su=1, sv=1/v)

    def onRotateLeft(self, *args):
        angle = cmds.floatField(self.rotationAngle, q=True, v=True)
        mel.eval("polyRotateUVs %f 1" % angle)

    def onRotateRight(self, *args):
        angle = cmds.floatField(self.rotationAngle, q=True, v=True) * -1
        mel.eval("polyRotateUVs %f 1" % angle)

    def onPlanerX(self, *args):
        mel.eval("polyProjection -type Planar -ibd on -kir -md x")

    def onPlanerY(self, *args):
        mel.eval("polyProjection -type Planar -ibd on -kir -md y")

    def onPlanerZ(self, *args):
        mel.eval("polyProjection -type Planar -ibd on -kir -md z")

    def onPlanerCamera(self, *args):
        mel.eval("polyProjection -type Planar -ibd on -kir -md camera")

    def onPlanerBest(self, *args):
        mel.eval("polyProjection -type Planar -ibd on -kir -md b;")

    def onStraightenBorder(self, *args):
        mel.eval("StraightenUVBorder")

    def onStraightenInner(self, *args):
        mel.eval("texStraightenShell")

    def onStraightenAll(self, *args):
        mel.eval("UVStraighten")

    def onLinearAlign(self, *args):
        mel.eval("texLinearAlignUVs")

    def onGridding(self, *args):
        mel.eval("AriUVGridding")

    def onChangeTexel(self, *args):
        """texel 変更時に UVToolkit のフィールドを同じ値に変更する"""
        texel = cmds.floatField(self.texel, q=True, v=True)
        mel.eval("floatField -e -v %f uvTkTexelDensityField" % texel)

    def onChangeMapSize(self, *args):
        """mapSize 変更時に UVToolkit のフィールドを同じ値に変更する"""
        mapSize = cmds.intField(self.mapSize, q=True, v=True)
        mel.eval("intField -e -v %d uvTkTexelDensityMapSizeField" % mapSize)

    def onGetTexel(self, *args):
        """
        UVシェル、もしくはUVエッジのテクセルを設定
        shell選択ならMayaの機能を使用し それ以外なら独自のUVエッジに対するテクセル設定モードを使用する
        """
        isUVShellSelection = cmds.selectType(q=True, msh=True)
        isFaceSelection = cmds.selectType(q=True, pf=True)
        isUVSelection = cmds.selectType(q=True, puv=True)

        if isUVShellSelection or isFaceSelection:
            # UVToolkit の機能でテクセル取得
            mel.eval("uvTkDoGetTexelDensity")
            uvTkTexel = mel.eval("floatField -q -v uvTkTexelDensityField")

            # ダイアログの値更新
            cmds.floatField(self.texel, e=True, v=uvTkTexel)

        elif isUVSelection:
            uvComponents = cmds.ls(os=True)
            uvComponents = cmds.filterExpand(cmds.ls(os=True), sm=35)

            uv1 = cmds.polyEditUV(uvComponents[0], q=True)
            uv2 = cmds.polyEditUV(uvComponents[1], q=True)
            vtxComponent1 = cmds.polyListComponentConversion(uvComponents[0], fuv=True, tv=True)
            vtxComponent2 = cmds.polyListComponentConversion(uvComponents[1], fuv=True, tv=True)
            p1 = cmds.xform(vtxComponent1, q=True, ws=True, t=True)
            p2 = cmds.xform(vtxComponent2, q=True, ws=True, t=True)
            geoLength = nu.distance(p1, p2)
            uvLength = nu.distance_uv(uv1, uv2)
            mapSize = self.getMapSize()
            currentTexel = uvLength / geoLength * mapSize

            # ダイアログの値を更新
            cmds.floatField(self.texel, e=True, v=currentTexel)
            # UVToolkit の値を更新
            mel.eval("floatField -e -v %f uvTkTexelDensityField" % currentTexel)
        else:
            print(MSG_NOT_IMPLEMENTED)

    def onSetTexel(self, *args):
        """
        UVシェル、もしくはUVエッジのテクセルを設定
        shell選択ならMayaの機能を使用し それ以外なら独自のUVエッジに対するテクセル設定モードを使用する
        """
        isUVShellSelection = cmds.selectType(q=True, msh=True)
        if isUVShellSelection:
            texel = cmds.floatField(self.texel, q=True, v=True)
            mapSize = cmds.intField(self.mapSize, q=True, v=True)
            mel.eval("texSetTexelDensity %f %d" % (texel, mapSize))
        else:
            self.setEdgeTexel(mode="uv")

    def setEdgeTexel(self, mode):
        """
        UVエッジを指定のテクセル密度にする
        エッジ選択モードならすべてのエッジに
        UV選択モードなら選択した第一UVと第二UVの距離に
        """

        targetTexel = self.getTexel()
        mapSize = self.getMapSize()

        isUVSelection = cmds.selectType(q=True, puv=True)
        isEdgeSelection = cmds.selectType(q=True, pe=True)

        targetUVsList = []
        uvComponents = []

        # エッジ選択モードならエッジを構成する 2 頂点の UV をペアとして targetUVsList に追加する
        if isEdgeSelection:
            edges = cmds.filterExpand(cmds.ls(os=True), sm=32)
            for edge in edges:
                uvComponents = cmds.filterExpand(cmds.polyListComponentConversion(edge, fe=True, tuv=True), sm=35)
                if len(uvComponents) == 2:  # 非UVシーム
                    targetUVsList.append(uvComponents)
                elif len(uvComponents) == 4:  # UVシーム
                    targetUVsList.append([uvComponents[0], uvComponents[2]])
                    targetUVsList.append([uvComponents[1], uvComponents[3]])
                else:
                    pass

        # UV選択モードなら選択UVの先頭 2 要素をペアとして targetUVsList に追加する
        elif isUVSelection:
            uvComponents = cmds.filterExpand(cmds.ls(os=True), sm=35)
            targetUVsList.append(uvComponents)

        if not isEdgeSelection and not isUVSelection:
            return

        for uvPair in targetUVsList:
            uv1 = cmds.polyEditUV(uvPair[0], q=True)  # ペアの 1 つめの UV座標を持つリスト
            uv2 = cmds.polyEditUV(uvPair[1], q=True)  # ペアの 2 つめの UV座標を持つリスト
            vtxComponent1 = cmds.polyListComponentConversion(uvPair[0], fuv=True, tv=True)  # uv1 に対応する ポリゴン頂点のコンポーネント文字列
            vtxComponent2 = cmds.polyListComponentConversion(uvPair[1], fuv=True, tv=True)  # uv2 に対応する ポリゴン頂点のコンポーネント文字列
            p1 = cmds.xform(vtxComponent1, q=True, ws=True, t=True)  # uv1 の XYZ 座標
            p2 = cmds.xform(vtxComponent2, q=True, ws=True, t=True)  # uv2 の XYZ 座標
            geoLength = nu.distance(p1, p2)
            uLength = abs(uv2[0] - uv1[0])
            vLength = abs(uv2[1] - uv1[1])
            uvLength = nu.distance_uv(uv1, uv2)

            if mode == "u_min":
                currentTexel = uLength / geoLength * mapSize
                scale = targetTexel / currentTexel
                pivU = min(uv1[0], uv2[0])
                pivV = 0
                cmds.polyEditUV(uvPair[0], pu=pivU, pv=pivV, su=scale, sv=1)
                cmds.polyEditUV(uvPair[1], pu=pivU, pv=pivV, su=scale, sv=1)

            elif mode == "u_max":
                currentTexel = uLength / geoLength * mapSize
                scale = targetTexel / currentTexel
                pivU = max(uv1[0], uv2[0])
                pivV = 0
                cmds.polyEditUV(uvPair[0], pu=pivU, pv=pivV, su=scale, sv=1)
                cmds.polyEditUV(uvPair[1], pu=pivU, pv=pivV, su=scale, sv=1)

            elif mode == "v_min":
                currentTexel = vLength / geoLength * mapSize
                scale = targetTexel / currentTexel
                pivU = 0
                pivV = min(uv1[1], uv2[1])
                cmds.polyEditUV(uvPair[0], pu=pivU, pv=pivV, su=1, sv=scale)
                cmds.polyEditUV(uvPair[1], pu=pivU, pv=pivV, su=1, sv=scale)

            elif mode == "v_max":
                currentTexel = vLength / geoLength * mapSize
                scale = targetTexel / currentTexel
                pivU = 0
                pivV = max(uv1[1], uv2[1])
                cmds.polyEditUV(uvPair[0], pu=pivU, pv=pivV, su=1, sv=scale)
                cmds.polyEditUV(uvPair[1], pu=pivU, pv=pivV, su=1, sv=scale)

            else:
                print(self.MSG_NOT_IMPLEMENTED)
                currentTexel = uvLength / geoLength * mapSize
                scale = targetTexel / currentTexel
                cmds.polyEditUV(uvPair[0], pu=uv1[0], pv=uv1[1], su=scale, sv=scale)
                cmds.polyEditUV(uvPair[1], pu=uv1[0], pv=uv1[1], su=scale, sv=scale)

    def onSetEdgeTexelUAuto(self, *args):
        self.setEdgeTexel(mode="u_auto")

    def onSetEdgeTexelUMin(self, *args):
        self.setEdgeTexel(mode="u_min")

    def onSetEdgeTexelUMax(self, *args):
        self.setEdgeTexel(mode="u_max")

    def onSetEdgeTexelVAuto(self, *args):
        self.setEdgeTexel(mode="v_auto")

    def onSetEdgeTexelVMin(self, *args):
        self.setEdgeTexel(mode="v_min")

    def onSetEdgeTexelVMax(self, *args):
        self.setEdgeTexel(mode="v_max")

    def onUVRatio(self, *args):
        mel.eval("AriUVRatio")

    def onUVRatioOptions(self, *args):
        mel.eval("AriUVRatioOptions")

    def onUnfoldU(self, *args):
        mel.eval("unfold -i 5000 -ss 0.001 -gb 0 -gmb 0.5 -pub 0 -ps 0 -oa 2 -us off")

    def onUnfoldV(self, *args):
        mel.eval("unfold -i 5000 -ss 0.001 -gb 0 -gmb 0.5 -pub 0 -ps 0 -oa 1 -us off")

    def onMatchUV(self, *args):
        mel.eval("texMatchUVs 0.01")

    def onMatchUVOptions(self, *args):
        mel.eval("MatchUVsOptions")

    def onOnewayMatchUVF(self, *args):
        OnewayMatchUV("front")

    def onOnewayMatchUVB(self, *args):
        OnewayMatchUV("back")

    def onOnewayMatchUVP(self, *args):
        OnewayMatchUV("pin")

    def onOnewayMatchUVUp(self, *args):
        OnewayMatchUV("unpin")

    def onExpandFoldRD(self, *args):
        half_expand_fold(True)

    def onExpandFoldLU(self, *args):
        half_expand_fold(False)

    def onFlipUinTile(self, *args):
        cmds.ConvertSelectionToUVs()
        uv_comp = cmds.ls(selection=True, flatten=True)[0]
        uv_coord = cmds.polyEditUV(uv_comp, query=True)
        u = uv_coord[0]
        v = uv_coord[1]
        piv_u = u // 1 + 0.5
        piv_v = v // 1 + 0.5
        cmds.SelectUVShell()
        cmds.polyEditUV(pu=piv_u, pv=piv_v, su=-1, sv=1)

    def onFlipVinTile(self, *args):
        cmds.ConvertSelectionToUVs()
        uv_comp = cmds.ls(selection=True, flatten=True)[0]
        uv_coord = cmds.polyEditUV(uv_comp, query=True)
        u = uv_coord[0]
        v = uv_coord[1]
        piv_u = u // 1 + 0.5
        piv_v = v // 1 + 0.5
        cmds.SelectUVShell()
        cmds.polyEditUV(pu=piv_u, pv=piv_v, su=1, sv=-1)

    def onSewMatchingEdges(self, *args):
        edges = cmds.ls(selection=True, flatten=True)

        for edge in edges:
            uvs = nu.to_uv(edge)
            if len(uvs) > 2:
                uv_coords = [nu.round_vector(nu.get_uv_coord(x), 4) for x in uvs]
                print(edge)
                unique_uv = set([tuple(x) for x in uv_coords])
                print(len(unique_uv))
                if len(unique_uv) == 2:
                    cmds.polyMapSew(edge, ch=1)

    def onOrientEdge(self, *args):
        mel.eval("texOrientEdge")

    def onOrientShells(self, *args):
        mel.eval("texOrientShells")

    def onSymArrange(self, *args):
        pass

    def onSnapStack(self, *args):
        mel.eval("texSnapStackShells")

    def onStack(self, *args):
        mel.eval("texStackShells({})")

    def onUnStack(self, *args):
        mel.eval("UVUnstackShells")

    def onNormalize(self, *args):
        mel.eval("polyNormalizeUV -normalizeType 1 -preserveAspectRatio on -centerOnTile on -normalizeDirection 0")

    # Tool
    def onUVLatticeTool(self, *args):
        mel.eval("LatticeUVTool")

    def onUVTweakTool(self, *args):
        mel.eval("setToolTo texTweakSuperContext")

    def onUVCutTool(self, *args):
        mel.eval("setToolTo texCutUVContext")

    def onUVOptimizeTool(self, *args):
        mel.eval("setToolTo texUnfoldUVContext")

    def onUVSymmetrizeTool(self, *args):
        mel.eval("setToolTo texSymmetrizeUVContext")

    def onSetUVSymmetrizeCenter(self, *args):
        uv = nu.get_selection()[0]
        uv_coord = nu.get_uv_coord(uv)

        cmds.optionVar(fv=["polySymmetrizeUVAxisOffset", uv_coord[0]])
        mel.eval("SymmetrizeUVContext -e -ap `optionVar -q polySymmetrizeUVAxisOffset` texSymmetrizeUVContext;")

    # Select & Convert
    def onConvertToShellBorder(self, *args):
        mel.eval("ConvertSelectionToUVs")
        mel.eval("ConvertSelectionToUVShellBorder")

    def onConvertToShellInner(self, *args):
        mel.eval("ConvertSelectionToUVShell")
        mel.eval("ConvertSelectionToUVs")
        mel.eval("PolySelectTraverse 2")

    def onSelectAllUVBorders(self, *args):
        mel.eval("SelectUVBorderComponents")

    def onShortestEdgeTool(self, *args):
        mel.eval("SelectShortestEdgePathTool")

    def onSelectFrontface(self, *args):
        pass

    def onSelectBackface(self, *args):
        pass

    # etc
    def onUVEditor(self, *args):
        mel.eval("TextureViewWindow")

    def onUVToolKit(self, *args):
        mel.eval("toggleUVToolkit")

    def onUVSnapShot(self, *args):
        mel.eval("performUVSnapshot")

    def onChangeUVCheckerDensity(self, *args):
        n = cmds.intField(self.checkerDensity, q=True, v=True) 
        texWinName = cmds.getPanel(sty='polyTexturePlacementPanel')[0]
        cmds.textureWindow(texWinName, e=True, checkerDensity=n)

    def onUVCheckerDensityMul2(self, *args):
        n = cmds.intField(self.checkerDensity, q=True, v=True) 
        cmds.intField(self.checkerDensity, e=True, v=n*2) 
        self.onChangeUVCheckerDensity()

    def onUVCheckerDensityDiv2(self, *args):
        n = cmds.intField(self.checkerDensity, q=True, v=True) 
        cmds.intField(self.checkerDensity, e=True, v=n/2) 
        self.onChangeUVCheckerDensity()

    def onToggleChecker(self, *args):
        checkered = cmds.textureWindow("polyTexturePlacementPanel1", q=True, displayCheckered=True)
        cmds.textureWindow("polyTexturePlacementPanel1", e=True, displayCheckered=(not checkered))

    def onDrawEdge(self, *args):
        import draw_image as de
        import nnutil as nu

        save_dir = nu.get_project_root() + "/images/"
        filepath = save_dir + "draw_edges.svg"
        mapSize = cmds.intField(self.mapSize, q=True, v=True)
        de.draw_edge(filepath=filepath, imagesize=mapSize)


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    mel.eval("TextureViewWindow")
    mel.eval("workspaceControl -e -visible true UVToolkitDockControl;")
    mel.eval("workspaceControl -e -close UVToolkitDockControl;")
    showNNToolWindow()


if __name__ == "__main__":
    main()