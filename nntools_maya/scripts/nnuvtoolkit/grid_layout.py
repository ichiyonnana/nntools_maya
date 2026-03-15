import maya.cmds as cmds
import maya.mel as mel

import nnutil.decorator as deco


ls_nonscalse = 1
ls_uniform = 2
ls_nonuniform = 3

default_texel = 4.0
default_mapsize = 1024


def set_texel(texel=default_texel, mapsize=default_mapsize):
    """
    UVシェル、もしくはUVエッジのテクセルを設定
    shell選択ならMayaの機能を使用し それ以外なら独自のUVエッジに対するテクセル設定モードを使用する
    """
    mel.eval("texSetTexelDensity %f %d" % (texel, mapsize))


@deco.repeatable
def project_uv(axis="x"):
    cmds.polyProjection(type="Planar", ibd=1, kir=True, md=axis)


layout_buttons = dict()
unused_color = (0.25, 0.25, 0.25)
used_color = (0.5, 0.5, 0.5)


def main():
    # ダイアログを作成
    if cmds.window("myWindow", exists=True):
        cmds.deleteUI("myWindow", window=True)

    myWindow = cmds.window("myWindow", title="UV Layout Tool", widthHeight=(10, 10), sizeable=False, resizeToFitChildren=True, maximizeButton=False, minimizeButton=False)

    # プロジェクションボタン
    cmds.columnLayout()
    cmds.rowLayout(numberOfColumns=6)
    cmds.button(label="X", width=40, height=40, bgc=(1.0, 0.5, 0.5), command=lambda x, axis="x": project_uv(axis=axis))
    cmds.button(label="Y", width=40, height=40, bgc=(0.5, 1.0, 0.5), command=lambda x, axis="y": project_uv(axis=axis))
    cmds.button(label="Z", width=40, height=40, bgc=(0.5, 0.5, 1.0), command=lambda x, axis="z": project_uv(axis=axis))

    cmds.button(label="Cut", width=40, height=40, command=lambda x: cmds.polyMapCut())
    cmds.button(label="Sew", width=40, height=40, command=lambda x: cmds.polyMapSew())
    cmds.button(label="Set Texel", width=80, height=40, command=lambda x: set_texel())

    cmds.setParent('..')  # rowLayout
    cmds.setParent('..')  # columnLayout

    # レイアウトボタン
    cmds.gridLayout(numberOfColumns=10, cellWidthHeight=(40, 40))
    for i in range(10):
        for j in range(10):
            layout_buttons[(i, j)] = cmds.button(label=str(i)+str(j), bgc=unused_color, command=lambda *args, i=i, j=j: on_layout(i, j), dgc=lambda *args, i=i, j=j, : clear_button_color(i, j))

    cmds.setParent('..')

    cmds.showWindow(myWindow)


def on_layout(i, j):
    u = j * 0.1
    v = (9 - i) * 0.1
    cmds.u3dLayout(res=1024, spc=0.0015625, mar=0.000390625, box=(u, u+0.1, v, v+0.1), ls=ls_uniform)

    cmds.button(layout_buttons[(i, j)], e=True, bgc=used_color)


def clear_button_color(i, j):
    cmds.button(layout_buttons[(i, j)], e=True, bgc=unused_color)


if __name__ == "__main__":
    main()
