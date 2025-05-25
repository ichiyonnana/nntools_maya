import svgwrite

import maya.cmds as cmds

import nnutil.core as nu


def draw_edge(filepath, imagesize=4096, stroke_width=1, integer_mode=False, normalize=True):
    """
    選択エッジを svg 形式で指定したパスに書き出す
    integer_mode: True で UV 座標をピクセル変換後に端数を切り捨てる
                    水平垂直ラインをそのままテクスチャとして使用したい場合等に使う
    normalize: True なら UV 座標を [0, 1) に納める
    """
    print(filepath)

    dwg = svgwrite.Drawing(filepath, size=(imagesize, imagesize) )

    selections = cmds.ls(selection=True, flatten=True)

    for edge in selections:
        vf_list = nu.to_vtxface(edge)
        vf_pairs = []

        if len(vf_list) > 2 :
            vf_pairs = [vf_list[0:0+2] , vf_list[2:2+2]]
        else:
            vf_pairs = [vf_list[0:0+2]]

        # ライン描画
        for vf_pair in vf_pairs:
            if vf_pair[0]:
                uv_comp1, uv_comp2 = nu.to_uv(vf_pair)
                uv_coord1 = nu.get_uv_coord(uv_comp1)
                uv_coord2 = nu.get_uv_coord(uv_comp2)

                if normalize:
                    uv_coord1 = [x % 1.0 for x in uv_coord1]
                    uv_coord2 = [x % 1.0 for x in uv_coord2]

                uv_px_coord1 = nu.mul(uv_coord1, imagesize)
                uv_px_coord2 = nu.mul(uv_coord2, imagesize)

                # 上下反転
                uv_px_coord1[1] = imagesize - uv_px_coord1[1]
                uv_px_coord2[1] = imagesize - uv_px_coord2[1]

                # 整数座標モード
                if integer_mode:
                    uv_px_coord1 = [int(x) for x in uv_px_coord1]
                    uv_px_coord2 = [int(x) for x in uv_px_coord2]


                dwg.add(dwg.line(uv_px_coord1, uv_px_coord2, stroke=svgwrite.rgb(0, 0, 0, '%'), stroke_width=stroke_width))

    # ファイルとして保存
    dwg.save()
