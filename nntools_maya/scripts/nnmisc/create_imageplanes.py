import maya.cmds as cmds
import re
import glob
import os

import nnutil.core as nu


def main():
    """images フォルダの画像からイメージプレーンとカメラを作成する｡

    すでに同名のイメージプレーンが存在する場合はファイルをスキップする｡
    イメージプレーンはカメラの子にして奥方向 10.1 の位置に配置する｡
    カメラの Near は 10.0 に設定する｡
    """
    # images フォルダの画像ファイルを取得
    scene_name = cmds.file(q=True, sceneName=True)
    project_root = re.sub(r"scenes.*$", "", scene_name)
    files = glob.glob(project_root + "images/*")

    # カメラの親となるグループを作成
    camera_grp_name = "cameras"

    if not cmds.objExists(camera_grp_name):
        camera_grp = cmds.createNode("transform", name=camera_grp_name)
    else:
        camera_grp = camera_grp_name

    # ファイル毎にイメージプレーンを作成してカメラの子にする
    added_imageplanes = []
    for file in files:
        # イメージプレーンと親となるカメラのノード名
        ip_name = re.sub(r"\..*$", "", os.path.basename(file))
        cam_name = re.sub(r"^ip", "cam", ip_name)

        # すでに同名のイメージプレーンが存在する場合はスキップ
        if cmds.objExists(ip_name):
            print("Skip: " + ip_name)
            continue

        # イメージプレーンの作成
        ip_trs, ip_shape = cmds.imagePlane(width=2.5, height=2.5, maintainRatio=1)
        ip_trs = cmds.rename(ip_trs, ip_name)
        ip_shape = nu.get_shape(ip_trs)

        print(ip_shape)
        cmds.setAttr(ip_shape + ".imageName", file, type="string")

        # 親となるカメラの作成､もしくは取得しイメージプレーンを子にする
        if cmds.objExists(cam_name):
            camera_trs = cam_name
            camera_shape = nu.get_shape(camera_trs)

            cmds.parent(ip_trs, camera_trs)

        else:
            camera_trs, camera_shape = cmds.camera(
                    name=cam_name,
                    centerOfInterest=5,
                    focalLength=70,
                    lensSqueezeRatio=1,
                    cameraScale=1,
                    horizontalFilmAperture=1.4173,
                    horizontalFilmOffset=0,
                    verticalFilmAperture=0.9449,
                    verticalFilmOffset=0,
                    filmFit="Fill",
                    overscan=1,
                    motionBlur=0,
                    shutterAngle=144,
                    nearClipPlane=0.1,
                    farClipPlane=10000,
                    orthographic=0,
                    orthographicWidth=30,
                    panZoomEnabled=0,
                    horizontalPan=0,
                    verticalPan=0,
                    zoom=1
                    )

            # カメラのアトリビュート設定
            cmds.setAttr(camera_shape + ".nearClipPlane", 10)

            # イメージプレーンとカメラグループの親子設定
            cmds.parent(ip_trs, camera_trs)
            cmds.parent(camera_trs, camera_grp)

        # イメージプレーンの設定
        print("set trs: " + ip_trs)
        cmds.setAttr(ip_trs + ".translate", 0, 0, -10.1)
        cmds.setAttr(ip_trs + ".rotate", 0, 0, 0)
        cmds.setAttr(ip_shape + ".colorGain", 0.5, 0.5, 0.5)
        cmds.setAttr(ip_shape + ".alphaGain", 0.5)

        added_imageplanes.append(ip_name)

    cmds.select(added_imageplanes)


if __name__ == "__main__":
    main()
