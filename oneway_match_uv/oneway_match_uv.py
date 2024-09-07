#
#  OneWayMatchUV
#    選択シェルからUVへ変換

import maya.cmds as cmds
import maya.mel as mel
import math

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
