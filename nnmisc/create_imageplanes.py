#! python
# coding:utf-8

import pymel.core as pm
import pymel.core.datatypes as dt
import re
import glob
import os


def main():
    """images フォルダの画像からイメージプレーンとカメラを作成する｡

    すでに同名のイメージプレーンが存在する場合はファイルをスキップする｡
    イメージプレーンはカメラの子にして奥方向 10.1 の位置に配置する｡
    カメラの Near は 10.0 に設定する｡
    """
    project_root = re.sub(r"scenes.*$", "", pm.sceneName())
    files = glob.glob(project_root + "images/*")

    camera_grp_name = "cameras"

    if not pm.objExists(camera_grp_name):
        camera_grp = pm.createNode("transform", name=camera_grp_name)
    else:
        camera_grp = pm.PyNode(camera_grp_name)

    for file in files:
        ip_name = re.sub(r"\..*$", "", os.path.basename(file))
        cam_name = re.sub(r"^ip", "cam", ip_name)

        if not pm.objExists(ip_name):
            ip_trs, ip_shape = pm.imagePlane(width=2.5, height=2.5, maintainRatio=1)
            camera_trs, camera_shape = pm.camera(
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

            ip_trs.rename(ip_name)
            camera_trs.rename(cam_name)

            ip_shape.imageName.set(file)

            pm.parent(ip_trs, camera_trs)
            pm.parent(camera_trs, camera_grp)

            ip_trs.translate.set(dt.Vector(0, 0, -10.1))
            ip_shape.colorGain.set(dt.Vector(0.5, 0.5, 0.5))
            ip_shape.alphaGain.set(0.5)

            camera_shape.nearClipPlane.set(10)


if __name__ == "__main__":
    main()
