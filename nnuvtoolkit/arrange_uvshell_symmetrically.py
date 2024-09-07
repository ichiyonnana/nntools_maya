# 選択した UV シェルを左右対称に配置する

import maya.cmds as cmds

def arrange_uvshell_symmetrically():
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

    def getUVShell(uv_comp):
        pass

    def getUVShellList(uv_comp_list):
        #   uvs[0] から順にシェル変換して変換後のシェルuvs を母集合から除外していく事で
        #   シェルのリスト作成する
        pass

    # 左右対称か上下対称か
    AA_U = 0
    AA_V = 1
    arrange_axis = AA_U

    # 軸の + 側と - 側のどちらを基準にするか
    SS_POSITIVE = 0
    SS_NEGATIVE = 1
    source_side = SS_POSITIVE

    # 選択頂点の取得
    # 選択頂点からシェルのリスト取得

    # シェルが 2 つ出ない場合は終了

    # ソースとターゲット 決定
    # ソースシェルの中心求める
    # ターゲットシェルの中心求める
    # ターゲットシェル移動


# 実行
arrange_uvshell_symmetrically()
