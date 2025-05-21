import maya.cmds as cmds


def place_primitive_in_front_of_camera(primitive_type='sphere'):
    # 現在アクティブなパネルを取得
    panel = cmds.getPanel(withFocus=True)

    # パネルがカメラビューであるかを確認
    if cmds.getPanel(typeOf=panel) == "modelPanel":
        # アクティブパネルのカメラを取得
        camera = cmds.modelPanel(panel, query=True, camera=True)
    else:
        # アクティブパネルがカメラビューでない場合は、デフォルトで 'persp' カメラを使用
        camera = 'persp'

    # カメラの位置と方向を取得
    camera_position = cmds.xform(camera, query=True, worldSpace=True, translation=True)
    camera_direction = cmds.xform(camera, query=True, worldSpace=True, matrix=True)

    # カメラ前方ベクトル
    camera_forward = [
        -camera_direction[8],  # -matrix[2][0]
        -camera_direction[9],  # -matrix[2][1]
        -camera_direction[10]  # -matrix[2][2]
    ]

    # カメラの Center of Interest (COI) を取得
    coi_distance = cmds.getAttr(camera + '.centerOfInterest')

    # カメラの位置からCOI距離分Z方向にオフセットを計算
    primitive_position = [
        camera_position[0] + camera_forward[0] * coi_distance,
        camera_position[1] + camera_forward[1] * coi_distance,
        camera_position[2] + camera_forward[2] * coi_distance
    ]

    # プリミティブを作成して位置を設定
    if primitive_type == 'sphere':
        primitive = cmds.polySphere(subdivisionsAxis=8, subdivisionsHeight=8)[0]
    elif primitive_type == 'cube':
        primitive = cmds.polyCube(subdivisionsX=1, subdivisionsY=1, subdivisionsZ=1)[0]
    elif primitive_type == 'cylinder':
        primitive = cmds.polyCylinder(subdivisionsAxis=8, subdivisionsHeight=1, subdivisionsCaps=1)[0]
    elif primitive_type == 'plane':
        primitive = cmds.polyPlane(subdivisionsX=1, subdivisionsY=1)[0]
    elif primitive_type == 'torus':
        primitive = cmds.polyTorus(subdivisionsAxis=8, subdivisionsHeight=8)[0]
    else:
        cmds.error("Unsupported primitive type: " + primitive_type)
        return

    cmds.xform(primitive, worldSpace=True, translation=primitive_position)

    print(f"Placed {primitive_type} at {primitive_position} in front of the '{camera}' camera.")


def set_translation_to_zero(axis):
    # 選択中のオブジェクトを取得
    selected_objects = cmds.ls(selection=True)

    if not selected_objects:
        cmds.error("No objects selected.")
        return

    # 選択したオブジェクトのtranslateを設定
    for obj in selected_objects:
        if axis == 'X':
            cmds.setAttr(f"{obj}.translateX", 0)
        elif axis == 'Y':
            cmds.setAttr(f"{obj}.translateY", 0)
        elif axis == 'Z':
            cmds.setAttr(f"{obj}.translateZ", 0)


def rotate90(axis):
    # 選択中のオブジェクトを取得
    selected_objects = cmds.ls(selection=True)

    if not selected_objects:
        cmds.error("No objects selected.")
        return

    # 選択したオブジェクトを回転
    for obj in selected_objects:
        if axis == 'X':
            cmds.rotate(90, 0, 0, obj, relative=True)
            cmds.setAttr(f"{obj}.rotateX", cmds.getAttr(f"{obj}.rotateX") % 360)
        elif axis == 'Y':
            cmds.rotate(0, 90, 0, obj, relative=True)
            cmds.setAttr(f"{obj}.rotateY", cmds.getAttr(f"{obj}.rotateY") % 360)
        elif axis == 'Z':
            cmds.rotate(0, 0, 90, obj, relative=True)
            cmds.setAttr(f"{obj}.rotateZ", cmds.getAttr(f"{obj}.rotateZ") % 360)


def create_ui():
    window_name = "nnPrimitiveWindow"
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)

    cmds.window(
        window_name,
        title="nnPrimitive",
        minimizeButton=False,
        maximizeButton=False,
        resizeToFitChildren=True,
        sizeable=False,
        widthHeight=(150, 200)
    )

    cmds.columnLayout(adjustableColumn=True)

    cmds.button(label="Cube", command=lambda _: place_primitive_in_front_of_camera('cube'))
    cmds.button(label="Cylinder", command=lambda _: place_primitive_in_front_of_camera('cylinder'))
    cmds.button(label="Sphere", command=lambda _: place_primitive_in_front_of_camera('sphere'))
    cmds.button(label="Plane", command=lambda _: place_primitive_in_front_of_camera('plane'))
    cmds.button(label="Torus", command=lambda _: place_primitive_in_front_of_camera('torus'))

    cmds.separator(height=10)

    cmds.button(label="X=0", command=lambda _: set_translation_to_zero('X'))
    cmds.button(label="Y=0", command=lambda _: set_translation_to_zero('Y'))
    cmds.button(label="Z=0", command=lambda _: set_translation_to_zero('Z'))

    cmds.separator(height=10)

    cmds.button(label="Rot X", command=lambda _: rotate90('X'))
    cmds.button(label="Rot Y", command=lambda _: rotate90('Y'))
    cmds.button(label="Rot Z", command=lambda _: rotate90('Z'))

    cmds.separator(height=5)

    cmds.showWindow(window_name)


def main():
    create_ui()


if __name__ == "__main__":
    main()
