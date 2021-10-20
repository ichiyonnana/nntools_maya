#! python
# coding:utf-8

import math

import maya.cmds as cmds
import maya.mel as mel

import nnutil as nu

#from nnenv import *
window_width = 300
header_width = 50
color_x = (1.0, 0.5, 0.5)
color_y = (0.5, 1.0, 0.5)
color_z = (0.5, 0.5, 1.0)
color_u = (1.0, 0.6, 0.7)
color_v = (0.7, 0.6, 1.0)
color_joint = (0.5, 1.0, 0.75)
color_select = (0.5, 0.75, 1.0)
bw_single = 24
bw_double = bw_single*2 + 2

def distance(p1, p2):
    return math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2 + (p2[2]-p1[2])**2)

def distanceUV(p1, p2):
    return math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)


def OnewayMatchUV(mode):
  def printd(description, message):
      print(str(description) + ": " + str(message))

  def distance2(p1, p2):
      return math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)

  def distance3(p1, p2):
      return math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2 + (p2[2]-p1[2])**2)

  def uvDistance(uv1, uv2):
    uvCoord1 = cmds.polyEditUV(uv1, query=True)
    uvCoord2 = cmds.polyEditUV(uv2, query=True)
    return distance2(uvCoord1, uvCoord2)


  def setUV(lhs, rhs):
    rhs_coord = cmds.polyEditUV(rhs, q=True, relative=False)
    cmds.polyEditUV(lhs, relative=False, u=rhs_coord[0], v=rhs_coord[1])

  MM_BACK_TO_FRONT = 0
  MM_UNPIN_TO_PIN = 1
  MM_FRONT_TO_BACK = 2
  MM_PIN_TO_UNPIN = 3

  if mode == None:
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
    printd("unknown match mode", mode)
    match_mode = MM_BACK_TO_FRONT


  # 選択UV
  selected_uvs = cmds.ls(selection=True, flatten=True)

  # シェル変換したUV
  cmds.SelectUVShell()
  uvs = cmds.ls(selection=True, flatten=True)

  #    全バックフェース取得
  cmds.SelectUVBackFacingComponents()
  uvs_back = list(set(cmds.ls(selection=True, flatten=True)) & set(uvs) )

  #    全フロントフェース取得
  cmds.SelectUVFrontFacingComponents()
  uvs_front = list( set(cmds.ls(selection=True, flatten=True)) & set(uvs) )

  #    選択内で pin 取得
  uvs_pined = []
  uvs_unpined = []
  for uv in uvs:
    pin_weight = cmds.polyPinUV(uv, q=True, v=True)[0]
    if pin_weight != 0:
      uvs_pined.append(uv)
    else:
      uvs_unpined.append(uv)

  #    積集合で選択UVをソースとターゲットに分ける
  source_uvs = []
  target_uvs = []
  if match_mode == MM_BACK_TO_FRONT:
    source_uvs = list( set(uvs_front) & set(uvs) )
    target_uvs = list( set(uvs_back) & set(uvs) )
  elif match_mode == MM_UNPIN_TO_PIN:
    source_uvs = list( set(uvs_pined) & set(uvs) )
    target_uvs = list( set(uvs_unpined) & set(uvs) )
  elif match_mode == MM_FRONT_TO_BACK:
    source_uvs = list( set(uvs_back) & set(uvs) )
    target_uvs = list( set(uvs_front) & set(uvs) )
  elif match_mode == MM_UNPIN_TO_PIN:
    source_uvs = list( set(uvs_unpined) & set(uvs) )
    target_uvs = list( set(uvs_pined) & set(uvs) )
  else:
    pass

  target_uvs = list(set(target_uvs) & set(selected_uvs))

  #    ターゲット.each
  for target_uv in target_uvs:
    nearest_uv = source_uvs[0]
    for source_uv in source_uvs:
      if uvDistance(target_uv, source_uv) < uvDistance(target_uv, nearest_uv):
        nearest_uv = source_uv
    setUV(target_uv, nearest_uv)
    # TODO:複数のターゲットが束ねられて閉まったソースのセットを作成or選択状態にする

  cmds.select(clear=True)

def half_expand_fold(right_down=True):
  """
  right_down=True で横なら右、縦なら下へ畳む
  """
  def printd(description, message):
      print(str(description) + ": " + str(message))

  def distance2(p1, p2):
      return math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)

  def distance3(p1, p2):
      return math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2 + (p2[2]-p1[2])**2)

  def getUV(uv_comp):
    uv_coord = cmds.polyEditUV(uv_comp, query=True)
    return uv_coord

  def setUV(lhs, rhs):
    rhs_coord = cmds.polyEditUV(rhs, q=True, relative=False)
    cmds.polyEditUV(lhs, relative=False, u=rhs_coord[0], v=rhs_coord[1])

  def uvDistance(uv1, uv2):
    uvCoord1 = getUV(uv1)
    uvCoord2 = getUV(uv2)
    return distance2(uvCoord1, uvCoord2)

  def getBackFaceUVcomp(uv_comp_list):
    cmds.SelectUVBackFacingComponents()
    backface_uvs = list(set(cmds.ls(selection=True, flatten=True)) & set(uv_comp_list) )
    return backface_uvs

  def selectUVs(target_uvs):
    cmds.select(clear=True)

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
      filp_direction = FD_TO_LEFT
  else:
    flip_axis = FA_V
    if right_down:
      flip_direction = FD_TO_DOWN
    else:
      flip_direction = FD_TO_UP

  # 選択UVからピボット決定
  selected_uv_coord_list = [getUV(x) for x in selected_uvs]
  piv_u = sum([x[0] for x in selected_uv_coord_list]) / len(selected_uv_coord_list)
  piv_v = sum([x[1] for x in selected_uv_coord_list]) / len(selected_uv_coord_list)

  # 裏面の UV 取得
  # expand 用 (expand の操作対象を "軸の外側UV" にすると四つ折りfoldができるけど折ったきりexpandできなくなる)
  backface_uvs = getBackFaceUVcomp(selected_sehll_uvs)

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
      target_uvs = [x for x in selected_sehll_uvs if getUV(x)[0] > piv_u]
    if flip_direction == FD_TO_RIGHT:
      target_uvs = [x for x in selected_sehll_uvs if getUV(x)[0] < piv_u]
    if flip_direction == FD_TO_UP:
      target_uvs = [x for x in selected_sehll_uvs if getUV(x)[1] < piv_v]
    if flip_direction == FD_TO_DOWN:
      target_uvs = [x for x in selected_sehll_uvs if getUV(x)[1] > piv_v]

  # スケール値の決定
  su = 1
  sv = 1

  if flip_axis == FA_U:
    su = -1
  if flip_axis == FA_V:
    sv = -1

  printd("target_uvs", target_uvs)
  printd("scale value", [su,sv])
  printd("pivot", [piv_u,piv_v])

  # ピボットを指定して反転処理
  cmds.polyEditUV(target_uvs, pu=piv_u, pv=piv_v, su=su, sv=sv)

  cmds.select(clear=True)



class NN_ToolWindow(object):
    MSG_NOT_IMPLEMENTED = "未実装"

    def __init__(self):
        self.window = 'NN_UVToolkit'
        self.title = 'NN_UVToolkit'
        self.size = (350, 95)

    def create(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)
        self.window = cmds.window(
            self.window,
            t = self.title,
            widthHeight = self.size
        )
        self.layout()
        cmds.showWindow()

        self.initialize()

    def layout(self):
        self.columnLayout = cmds.columnLayout()

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text( label='Projection' )
        cmds.setParent("..")
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.buttonA = cmds.button(l='X', c=self.onPlanerX, bgc=color_x, width=bw_single)
        self.buttonA = cmds.button(l='Y', c=self.onPlanerY, bgc=color_y, width=bw_single)
        self.buttonA = cmds.button(l='Z', c=self.onPlanerZ, bgc=color_z, width=bw_single)
        self.buttonA = cmds.button(l='Camera', c=self.onPlanerCamera)
        self.buttonA = cmds.button(l='Best', c=self.onPlanerBest)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text( label='align & snap' )
        cmds.setParent("..")
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.buttonA = cmds.button(l='Border', c=self.onStraightenBorder)
        self.buttonA = cmds.button(l='Inner', c=self.onStraightenInner)
        self.buttonA = cmds.button(l='All', c=self.onStraightenAll)
        self.buttonA = cmds.button(l='Linear', c=self.onLinearAlign)
        self.buttonA = cmds.button(l='AriGridding', c=self.onGridding)
        self.buttonA = cmds.button(l='MatchUV', c=self.onMatchUV, dgc=self.onMatchUVOptions)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text( label='MatchUV' )
        self.buttonA = cmds.button(l='-Front', c=self.onOnewayMatchUVF, dgc=self.onOnewayMatchUVB)
        self.buttonA = cmds.button(l='-Pin', c=self.onOnewayMatchUVP, dgc=self.onOnewayMatchUVUp)
        self.buttonA = cmds.button(l='expand/fold', c=self.onExpandFoldRD, dgc=self.onExpandFoldLU)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.buttonA = cmds.button(l='FlipU', c=self.onFlipUinTile, bgc=color_u, width=bw_double)
        self.buttonA = cmds.button(l='FlipV', c=self.onFlipVinTile, bgc=color_v, width=bw_double)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text( label='Special Sew' )
        self.buttonA = cmds.button(l='MatchingE', c=self.onSewMatchingEdges, width=bw_double)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text( label='optimize' )
        cmds.setParent("..")
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.buttonA = cmds.button(l='Get', c=self.onGetTexel)
        self.texel = cmds.floatField(cc=self.onChangeTexel)
        self.buttonA = cmds.button(l='Set', c=self.onSetTexel)
        self.buttonA = cmds.button(l='U', c=self.onSetEdgeTexelUMin, dgc=self.onSetEdgeTexelUMax, bgc=color_u, width=bw_single)
        self.buttonA = cmds.button(l='V', c=self.onSetEdgeTexelVMin, dgc=self.onSetEdgeTexelVMax, bgc=color_v, width=bw_single)
        self.mapSize = cmds.intField(width=48,  cc=self.onChangeMapSize)
        self.label1 = cmds.text( label='px' )
        cmds.setParent("..")
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.buttonA = cmds.button(l='AriUVRatio', c=self.onUVRatio, dgc=self.onUVRatioOptions)
        self.buttonA = cmds.button(l='UnfoldU', c=self.onUnfoldU, bgc=color_u, width=bw_double)
        self.buttonA = cmds.button(l='UnfoldV', c=self.onUnfoldV, bgc=color_v, width=bw_double)
        cmds.setParent("..")
        
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text( label='CheckerDens:' )
        self.checkerDensity = cmds.intField(width=48, v=256, cc=self.onChangeUVCheckerDensity)
        self.buttonA = cmds.button(l='/2', c=self.onUVCheckerDensityDiv2)
        self.buttonA = cmds.button(l='x2', c=self.onUVCheckerDensityMul2)
        cmds.setParent("..")


        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text( label='layout' )
        cmds.setParent("..")
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.buttonA = cmds.button(l='Orient to Edge', c=self.onOrientEdge)
        self.buttonA = cmds.button(l='Orient Shells', c=self.onOrientShells)
        self.buttonA = cmds.button(l='SymArrange', c=self.onSymArrange)
        cmds.setParent("..")
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        cmds.setParent("..")
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.buttonA = cmds.button(l='SanpStack', c=self.onSnapStack)
        self.buttonA = cmds.button(l='Stack', c=self.onStack)
        self.buttonA = cmds.button(l='Unstack', c=self.onUnStack)
        self.buttonA = cmds.button(l='Normalize', c=self.onNormalize)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text( label='Tools' )
        cmds.setParent("..")
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.buttonA = cmds.button(l='Lattice', c=self.onUVLatticeTool)
        self.buttonA = cmds.button(l='Tweak', c=self.onUVTweakTool)
        self.buttonA = cmds.button(l='Cut', c=self.onUVCutTool)
        self.buttonA = cmds.button(l='Optimize', c=self.onUVOptimizeTool)
        self.buttonA = cmds.button(l='Symmetrize [setU]', c=self.onUVSymmetrizeTool, dgc=self.onSetUVSymmetrizeCenter)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text( label='select, convert, filter' )
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.buttonA = cmds.button(l='cnv to Border', c=self.onConvertToShellBorder)
        self.buttonA = cmds.button(l='cnv to Inner', c=self.onConvertToShellInner)
        self.buttonA = cmds.button(l='sel All Borders', c=self.onSelectAllUVBorders)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.buttonA = cmds.button(l='sel Front', c=self.onSelectFrontface)
        self.buttonA = cmds.button(l='sel Back', c=self.onSelectBackface)
        self.buttonA = cmds.button(l='Shortest Tool', c=self.onShortestEdgeTool)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text( label='Transform' )
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text( label='Translate', width=header_width )
        self.translateValue = cmds.floatField(v=0.1)
        self.buttonA = cmds.button(l=u'←', c=self.onTranslateUDiff, bgc=color_u, width=bw_single)
        self.buttonA = cmds.button(l=u'→', c=self.onTranslateUAdd, bgc=color_u, width=bw_single)
        self.buttonA = cmds.button(l=u'↑', c=self.onTranslateVAdd, bgc=color_v, width=bw_single)
        self.buttonA = cmds.button(l=u'↓', c=self.onTranslateVDiff, bgc=color_v, width=bw_single)
        cmds.setParent("..")
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text( label='Rotate', width=header_width )
        self.rotationAngle = cmds.floatField(v=90)
        self.buttonA = cmds.button(l=u'←', c=self.onRotateLeft, width=bw_single)
        self.buttonA = cmds.button(l=u'→', c=self.onRotateRight, width=bw_single)
        cmds.setParent("..")
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text( label='Scale', width=header_width )
        self.scaleValue = cmds.floatField(v=2)
        self.buttonA = cmds.button(l='U*', c=self.onOrigScaleUMul, bgc=color_u, width=bw_single)
        self.buttonA = cmds.button(l='U/', c=self.onOrigScaleUDiv, bgc=color_u, width=bw_single)
        self.buttonA = cmds.button(l='V*', c=self.onOrigScaleVMul, bgc=color_v, width=bw_single)
        self.buttonA = cmds.button(l='V/', c=self.onOrigScaleVDiv, bgc=color_v, width=bw_single)
        cmds.setParent("..")

        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.label1 = cmds.text( label='' )
        cmds.setParent("..")
        self.rowLayout1 = cmds.rowLayout(numberOfColumns=10)
        self.buttonA = cmds.button(l='UVEditor', c=self.onUVEditor)
        self.buttonA = cmds.button(l='UVToolkit', c=self.onUVToolKit)
        self.buttonA = cmds.button(l='UVSnapShot', c=self.onUVSnapShot)
        self.buttonA = cmds.button(l='DrawEdge', c=self.onDrawEdge)
        cmds.setParent("..")

    def initialize(self):
        # テクセルとマップサイズを UVToolkit から取得
        uvtkTexel = mel.eval("floatField -q -v uvTkTexelDensityField")
        uvtkMapSize = mel.eval("intField -q -v uvTkTexelDensityMapSizeField")
        cmds.floatField(self.texel, e=True, v=uvtkTexel)
        cmds.intField(self.mapSize, e=True, v=uvtkMapSize)

    ### getter/setter
    ### フォームからの値を取るだけ
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
            p1 = cmds.xform(vtxComponent1, q=True,ws=True,t=True)
            p2 = cmds.xform(vtxComponent2, q=True,ws=True,t=True)
            geoLength = distance(p1, p2)
            uvLength = distanceUV(uv1, uv2)
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
            mapSize = cmds.intField(self.mapSize, q=True, v=True )
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
                if len(uvComponents) == 2: # 非UVシーム
                    targetUVsList.append(uvComponents)
                elif len(uvComponents) == 4: # UVシーム
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

        print("targetUVsList")
        print(targetUVsList)
        for uvPair in targetUVsList:
            uv1 = cmds.polyEditUV(uvPair[0], q=True) # ペアの 1 つめの UV座標を持つリスト
            uv2 = cmds.polyEditUV(uvPair[1], q=True) # ペアの 2 つめの UV座標を持つリスト
            vtxComponent1 = cmds.polyListComponentConversion(uvPair[0], fuv=True, tv=True) # uv1 に対応する ポリゴン頂点のコンポーネント文字列
            vtxComponent2 = cmds.polyListComponentConversion(uvPair[1], fuv=True, tv=True) # uv2 に対応する ポリゴン頂点のコンポーネント文字列
            p1 = cmds.xform(vtxComponent1, q=True,ws=True,t=True) # uv1 の XYZ 座標
            p2 = cmds.xform(vtxComponent2, q=True,ws=True,t=True) # uv2 の XYZ 座標
            geoLength = distance(p1, p2)
            uLength = abs(uv2[0] - uv1[0])
            vLength = abs(uv2[1] - uv1[1])
            uvLength = distanceUV(uv1, uv2)

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
                pivV =  max(uv1[1], uv2[1])
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
      import nnutil as nu

      def round_vector(v, fraction):
        v = [round(x, fraction) for x in v]
        return v

      edges = cmds.ls(selection=True, flatten=True)

      for edge in edges:
          uvs = nu.to_uv(edge)
          if len(uvs) > 2:
              uv_coords = [round_vector(nu.get_uv_coord(x), 4) for x in uvs]
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

    ### etc
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
        checkered = cmds.textureWindow("polyTexturePlacementPanel1", e=True, displayCheckered=True)
        cmds.textureWindow("polyTexturePlacementPanel1", e=True, displayCheckered=(not checkerd))

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