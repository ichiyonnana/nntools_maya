"""頂点やエッジを座標値で揃えるツール｡

頂点選択時は全ての頂点の指定した成分の値が同一になる｡
エッジ選択時は各エッジ毎に成分の値を統一する｡
"""

import maya.cmds as cmds


def align_component(axis="x", mode="min"):
    """選択コンポーネントの成分値を統一する｡

    Args:
        axis (str, optional): 値を統一する座標軸. Defaults to "x".
        mode (str, optional): 基準となる値. Defaults to "min".
    """
    if cmds.selectMode(q=True, component=True):
        if cmds.selectType(q=True, polymeshVertex=True):
            vertices = cmds.ls(selection=True, flatten=True)
            current_coords = [cmds.pointPosition(vertex, world=True) for vertex in vertices]
            new_coords = []

            if axis == "x":
                if mode == "min":
                    min_x = min(coord[0] for coord in current_coords)
                    new_coords = [(min_x, coord[1], coord[2]) for coord in current_coords]
                elif mode == "max":
                    max_x = max(coord[0] for coord in current_coords)
                    new_coords = [(max_x, coord[1], coord[2]) for coord in current_coords]
                elif mode == "avg":
                    avg_x = sum(coord[0] for coord in current_coords) / len(current_coords)
                    new_coords = [(avg_x, coord[1], coord[2]) for coord in current_coords]

            elif axis == "y":
                if mode == "min":
                    min_y = min(coord[1] for coord in current_coords)
                    new_coords = [(coord[0], min_y, coord[2]) for coord in current_coords]
                elif mode == "max":
                    max_y = max(coord[1] for coord in current_coords)
                    new_coords = [(coord[0], max_y, coord[2]) for coord in current_coords]
                elif mode == "avg":
                    avg_y = sum(coord[1] for coord in current_coords) / len(current_coords)
                    new_coords = [(coord[0], avg_y, coord[2]) for coord in current_coords]

            elif axis == "z":
                if mode == "min":
                    min_z = min(coord[2] for coord in current_coords)
                    new_coords = [(coord[0], coord[1], min_z) for coord in current_coords]
                elif mode == "max":
                    max_z = max(coord[2] for coord in current_coords)
                    new_coords = [(coord[0], coord[1], max_z) for coord in current_coords]
                elif mode == "avg":
                    avg_z = sum(coord[2] for coord in current_coords) / len(current_coords)
                    new_coords = [(coord[0], coord[1], avg_z) for coord in current_coords]

            for vertex, coord in zip(vertices, new_coords):
                cmds.move(coord[0], coord[1], coord[2], vertex, absolute=True, worldSpace=True)

        if cmds.selectType(q=True, polymeshEdge=True):
            selections = cmds.ls(selection=True, flatten=True)
            for edge in selections:
                vertices = cmds.filterExpand(cmds.polyListComponentConversion(edge, fromEdge=True, toVertex=True), sm=31)
                current_coords = [cmds.pointPosition(vertex, world=True) for vertex in vertices]
                new_coords = []

                if axis == "x":
                    if mode == "min":
                        min_x = min(coord[0] for coord in current_coords)
                        new_coords = [(min_x, coord[1], coord[2]) for coord in current_coords]
                    elif mode == "max":
                        max_x = max(coord[0] for coord in current_coords)
                        new_coords = [(max_x, coord[1], coord[2]) for coord in current_coords]
                    elif mode == "avg":
                        avg_x = sum(coord[0] for coord in current_coords) / len(current_coords)
                        new_coords = [(avg_x, coord[1], coord[2]) for coord in current_coords]

                elif axis == "y":
                    if mode == "min":
                        min_y = min(coord[1] for coord in current_coords)
                        new_coords = [(coord[0], min_y, coord[2]) for coord in current_coords]
                    elif mode == "max":
                        max_y = max(coord[1] for coord in current_coords)
                        new_coords = [(coord[0], max_y, coord[2]) for coord in current_coords]
                    elif mode == "avg":
                        avg_y = sum(coord[1] for coord in current_coords) / len(current_coords)
                        new_coords = [(coord[0], avg_y, coord[2]) for coord in current_coords]

                elif axis == "z":
                    if mode == "min":
                        min_z = min(coord[2] for coord in current_coords)
                        new_coords = [(coord[0], coord[1], min_z) for coord in current_coords]
                    elif mode == "max":
                        max_z = max(coord[2] for coord in current_coords)
                        new_coords = [(coord[0], coord[1], max_z) for coord in current_coords]
                    elif mode == "avg":
                        avg_z = sum(coord[2] for coord in current_coords) / len(current_coords)
                        new_coords = [(coord[0], coord[1], avg_z) for coord in current_coords]

                for vertex, coord in zip(vertices, new_coords):
                    cmds.move(coord[0], coord[1], coord[2], vertex, absolute=True, worldSpace=True)


def align_x_min(*args):
    align_component(axis="x", mode="min")


def align_x_max(*args):
    align_component(axis="x", mode="max")


def align_x_avg(*args):
    align_component(axis="x", mode="avg")


def align_y_min(*args):
    align_component(axis="y", mode="min")


def align_y_max(*args):
    align_component(axis="y", mode="max")


def align_y_avg(*args):
    align_component(axis="y", mode="avg")


def align_z_min(*args):
    align_component(axis="z", mode="min")


def align_z_max(*args):
    align_component(axis="z", mode="max")


def align_z_avg(*args):
    align_component(axis="z", mode="avg")


def create_ui():
    if cmds.window("myWindow", exists=True):
        cmds.deleteUI("myWindow", window=True)

    myWindow = cmds.window("myWindow", title="Align UI", widthHeight=(200, 120))
    cmds.columnLayout(adjustableColumn=True)

    cmds.rowLayout(numberOfColumns=4)
    cmds.text(label='x')
    cmds.button(label='min', command=align_x_min)
    cmds.button(label='max', command=align_x_max)
    cmds.button(label='avg', command=align_x_avg)
    cmds.setParent('..')

    cmds.rowLayout(numberOfColumns=4)
    cmds.text(label='y')
    cmds.button(label='min', command=align_y_min)
    cmds.button(label='max', command=align_y_max)
    cmds.button(label='avg', command=align_y_avg)
    cmds.setParent('..')

    cmds.rowLayout(numberOfColumns=4)
    cmds.text(label='z')
    cmds.button(label='min', command=align_z_min)
    cmds.button(label='max', command=align_z_max)
    cmds.button(label='avg', command=align_z_avg)
    cmds.setParent('..')

    cmds.showWindow(myWindow)


def main():
    create_ui()


if __name__ == "__main__":
    main()
