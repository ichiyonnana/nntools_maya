# UVシェルを選択したUVを軸に裏面をシンメトリにフリップしたり開いたシェルをたたんだりする

import maya.cmds as cmds

def half_expand_fold():
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
  flip_direction = FD_TO_RIGHT


  # 選択UV取得
  selected_uvs = cmds.ls(selection=True, flatten=True)
  cmds.SelectUVShell()
  selected_sehll_uvs = cmds.ls(selection=True, flatten=True)

  if len(selected_uvs) == 0:
    return

  # 選択UVからピボット決定
  selected_uv_coord_list = [getUV(x) for x in selected_uvs]
  piv_u = sum([x[0] for x in selected_uv_coord_list]) / len(selected_uv_coord_list)
  piv_v = sum([x[1] for x in selected_uv_coord_list]) / len(selected_uv_coord_list)

  # 裏面の UV 取得
  backface_uvs = getBackFaceUVcomp(selected_sehll_uvs)

  # 編集対象 UV
  target_uvs = []

  # 編集対象の決定
  if len(backface_uvs) > 0:
    # 裏面があれば裏面が編集対象
    target_uvs = backface_uvs
  else:
    # 裏面が無ければフリップ外側のUVを編集対象にする
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


# 実行
half_expand_fold()