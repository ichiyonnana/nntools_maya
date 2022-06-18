#! python
# coding:utf-8
"""

"""
from email.mime import image
import os
import re

import maya.cmds as cmds
import pymel.core as pm
import pymel.core.nodetypes as nt

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import nnutil.display as nd


window_name = "NN_Camera"
window = None


def get_window():
    return window


class ListItem:
    def __init__(self):
        self.name = ""
        self.content = ""

    def __str__(self):
        return "ListItem(%s)" % self.content


def get_unmatch_part(path1, path2):
    blocks1 = path1.split("|")
    blocks2 = path2.split("|")
    unmatch_list = []
    length = min(len(blocks1), len(blocks2))

    for i in range(length):
        if blocks1[i] != blocks2[i]:
            unmatch_list.append(blocks1[i])

    if unmatch_list:
        return unmatch_list[0]

    else:
        return None


class NN_ToolWindow(object):
    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (350, 340)

        self.target_panel = None  # Fix Panel 有効時に使用されるパネル

        self.camera_list_items = []  # カメラリストの ListItem 配列
        self.imageplane_list_items = []  # イメージプレーンリストの ListItem 配列

        self.image_editor = r"D:\Program Files\Adobe\Adobe Photoshop 2022\Photoshop.exe"

    def create(self):
        if pm.window(self.window, exists=True):
            pm.deleteUI(self.window, window=True)

        # プリファレンスの有無による分岐
        if pm.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = pm.windowPref(self.window, q=True, topLeftCorner=True)
            pm.windowPref(self.window, remove=True)

            # 前回位置に指定したサイズで表示
            pm.window(self.window, t=self.title, maximizeButton=False, minimizeButton=False, topLeftCorner=position, widthHeight=self.size, sizeable=False)

        else:
            # プリファレンスがなければデフォルト位置に指定サイズで表示
            pm.window(self.window, t=self.title, maximizeButton=False, minimizeButton=False, widthHeight=self.size, sizeable=False)

        self.layout()
        self.onUpdateCameraList()
        pm.showWindow(self.window)

    def layout(self):
        ui.column_layout()

        ui.row_layout()

        # 左ペイン
        ui.column_layout()
        ui.row_layout()
        ui.button(label="Update", c=self.onUpdateCameraList)
        ui.button(label="Select", c=self.onSelectCameraObject)
        ui.button(label="Lock", c=self.onLockCamera, dgc=self.onUnLockCamera)
        ui.end_layout()
        self.camera_list = pm.textScrollList(
                                                    numberOfRows=20,
                                                    allowMultiSelection=False,
                                                    append=[""],
                                                    selectIndexedItem=1,
                                                    showIndexedItem=1,
                                                    selectCommand=self.onClickCameraListItem,
                                                    doubleClickCommand=self.onDoubleClickCameraListItem,
                                                    height=ui.height(10)
                                                    )
        ui.end_layout()

        # 右ペイン
        ui.column_layout()
        ui.row_layout()
        ui.button(label="Lock", c=self.onLockImageplane, dgc=self.onUnLockImageplane)
        ui.button(label="Dup", c=self.onDuplicateImageplane)
        ui.button(label="Edit", c=self.onEditImage, dgc=self.onSetImageEditor)
        ui.end_layout()
        self.item_list = pm.textScrollList(
                                                    numberOfRows=20,
                                                    allowMultiSelection=True,
                                                    append=[""],
                                                    selectIndexedItem=1,
                                                    selectCommand=self.onClickImageplaneListItem,
                                                    doubleClickCommand=self.onDoubleClickImageplaneListItem,
                                                    height=ui.height(10)
                                                    )
        ui.end_layout()

        ui.end_layout()

        ui.row_layout()
        ui.button(label="TearOff", c=self.onTearOff)
        ui.button(label="Toggle Display", c=self.onToggleDisplay)
        ui.button(label="Fix Panel", c=self.onFixPanel)
        self.cb_fix_target = ui.check_box(label="Fix Panel")
        ui.end_layout()

        ui.row_layout()
        ui.button(label="LookThrough Parent", c=self.onLookThroughParent)
        ui.button(label="Create ImagePlane", c=self.onCreateImageplane)
        ui.end_layout()

        ui.end_layout()

    def get_selected_camera_item(self):
        """カメラリストUIで選択されているカメラの ListItem オブジェクトを返す"""
        indices = pm.textScrollList(self.camera_list, q=True, selectIndexedItem=True)

        if indices:
            return self.camera_list_items[indices[0]-1]
        else:
            return None

    def get_selected_imageplane_items(self):
        """イメージプレーンリストUIで選択されているイメージプレーンの ListItem オブジェクトを返す"""
        indices = [x - 1 for x in pm.textScrollList(self.item_list, q=True, selectIndexedItem=True)]

        if indices:
            return [x for i, x in enumerate(self.imageplane_list_items) if i in indices]
        else:
            return []

    def onUpdateCameraList(self, *args):
        """Update ボタンクリックハンドラ｡カメラリストを更新する"""
        # ListItem 配列の更新
        self.camera_list_items = []

        for camera in cmds.ls(type="camera", long=True):
            item = ListItem()
            item.content = camera
            item.name = re.match(r"(.*\|)?(.+)(Shape)", camera).groups()[1]
            basename = re.sub(r"^.*\|", "", camera)

            # 名前の重複があればパスの差異を付与
            if not pm.uniqueObjExists(basename):
                duplicates = cmds.ls(basename, long=True)
                duplicates.remove(item.content)
                uniq_str = get_unmatch_part(item.content, duplicates[0])

                if uniq_str:
                    item.name = "{}    ({})".format(item.name, uniq_str)

            self.camera_list_items.append(item)

        # ソート
        self.camera_list_items.sort(key=lambda x: x.content)

        # アクティブなカメラのリストUI上でのインデックス
        active_camera_name = pm.PyNode(nu.get_active_camera()).name()
        camera_list = [x.content for x in self.camera_list_items]

        if active_camera_name in camera_list:
            active_camera_index = [x.content for x in self.camera_list_items].index(active_camera_name) + 1
        else:
            active_camera_index = 1

        # リストUIの更新
        pm.textScrollList(self.camera_list, e=True, removeAll=True)
        pm.textScrollList(
                            self.camera_list,
                            e=True,
                            numberOfRows=20,
                            allowMultiSelection=False,
                            append=[x.name for x in self.camera_list_items],
                            selectIndexedItem=active_camera_index,
                            selectCommand=self.onClickCameraListItem,
                            doubleClickCommand=self.onDoubleClickCameraListItem
                            )

    def onClickCameraListItem(self, *args):
        """カメラリストアイテムのクリックのハンドラ｡子供のリストを更新する"""
        camera = self.get_selected_camera_item()
        pn_camera = pm.PyNode(camera.content)
        camera_trs = pn_camera.getParent()
        all_imageplanes = nu.list_diff(pm.listRelatives(camera_trs, ad=True,  shapes=True), [camera.content])
        visible_indices = [i+1 for i, x in enumerate(all_imageplanes) if x.visibility.get()]

        # ListItem 配列の更新
        self.imageplane_list_items = []

        for imageplane in all_imageplanes:
            if type(imageplane) is nt.ImagePlane:
                item = ListItem()
                item.content = imageplane.fullPathName()
                item.name = re.sub(r"^.*\|", "", item.content)
                self.imageplane_list_items.append(item)

        # イメージプレーンリストUIの更新
        pm.textScrollList(self.item_list, e=True, removeAll=True)

        if self.imageplane_list_items:
            pm.textScrollList(self.item_list, e=True, append=[x.name for x in self.imageplane_list_items], sii=visible_indices)

    def onDoubleClickCameraListItem(self, *args):
        """カメラリストアイテムのダブルクリックのハンドラ｡アクティブパネルのカメラを切り替える"""
        camera_name = self.get_selected_camera_item().content
        active_panel = pm.getPanel(wf=True)

        if ui.get_value(self.cb_fix_target):
            pm.lookThru(self.target_panel, camera_name)

        else:
            pm.lookThru(active_panel, camera_name)

    def onClickImageplaneListItem(self, *args):
        """イメージプレーンリストアイテムのクリック｡ビジビリティの更新"""
        selected_indices = [x - 1 for x in pm.textScrollList(self.item_list, q=True, selectIndexedItem=True)]

        for index in range(len(self.imageplane_list_items)):
            imageplane = self.imageplane_list_items[index].content
            # シェープの非表示解除
            pm.PyNode(imageplane).visibility.set(True)

            # 親トランスフォームノードのビジビリティ変更
            if index in selected_indices:
                pm.PyNode(imageplane).getParent().visibility.set(True)
            else:
                pm.PyNode(imageplane).getParent().visibility.set(False)

    def onDoubleClickImageplaneListItem(self, *args):
        """アイテムの選択"""
        self.onSelectImageplane()

    def onSelectCameraObject(self, *args):
        """カメラオブジェクトの選択"""
        camera = self.get_selected_camera_item()

        if camera:
            pn_camera = pm.PyNode(camera.content)
            pm.select(pn_camera.getParent())

    def onSelectImageplane(self, *args):
        """イメージプレーンオブジェクトの選択"""
        pm.select(clear=True)
        imageplanes = self.get_selected_imageplane_items()

        for imageplane in imageplanes:
            pn_imageplane = pm.PyNode(imageplane.content)
            pm.select(pn_imageplane.getParent(), add=True)

    def onDuplicateImageplane(self, *args):
        """イメージプレーンオブジェクトと参照先の画像ファイルの複製"""
        # TODO: 実装

    def onEditImage(self, *args):
        """選択されているイメージプレーンを開く"""
        imageplanes = self.get_selected_imageplane_items()

        for imageplane in imageplanes:
            pn_imageplane = pm.PyNode(imageplane.content)
            filename = re.sub(r"/", r"\\", pn_imageplane.imageName.get())
            cmd = '"%s" %s' % (self.image_editor, filename)
            os.system(cmd)

    def onSetImageEditor(self, *args):
        """画像編集エディターの指定ダイアログ"""
        image_editor_path = ui.input_dialog(title="image editor path", message="input image editor path")

        if image_editor_path:
            self.image_editor = image_editor_path

    def onLockCamera(self, *args):
        """カメラオブジェクトのロック"""
        camera = self.get_selected_camera_item()

        if camera:
            pn_camera = pm.PyNode(camera.content).getParent()
            pn_camera.translateX.lock()
            pn_camera.translateY.lock()
            pn_camera.translateZ.lock()
            pn_camera.rotateX.lock()
            pn_camera.rotateY.lock()
            pn_camera.rotateZ.lock()
            pn_camera.scaleX.lock()
            pn_camera.scaleY.lock()
            pn_camera.scaleZ.lock()

    def onUnLockCamera(self, *args):
        """カメラオブジェクトのアンロック"""
        camera = self.get_selected_camera_item()

        if camera:
            pn_camera = pm.PyNode(camera.content).getParent()
            pn_camera.translateX.unlock()
            pn_camera.translateY.unlock()
            pn_camera.translateZ.unlock()
            pn_camera.rotateX.unlock()
            pn_camera.rotateY.unlock()
            pn_camera.rotateZ.unlock()
            pn_camera.scaleX.unlock()
            pn_camera.scaleY.unlock()
            pn_camera.scaleZ.unlock()

    def onLockImageplane(self, *args):
        """イメージプレーンオブジェクトのロック"""
        imageplanes = self.get_selected_imageplane_items()

        for imageplane in imageplanes:
            pn_imageplane = pm.PyNode(imageplane.content).getParent()
            pn_imageplane.translateX.lock()
            pn_imageplane.translateY.lock()
            pn_imageplane.translateZ.lock()
            pn_imageplane.rotateX.lock()
            pn_imageplane.rotateY.lock()
            pn_imageplane.rotateZ.lock()
            pn_imageplane.scaleX.lock()
            pn_imageplane.scaleY.lock()
            pn_imageplane.scaleZ.lock()

    def onUnLockImageplane(self, *args):
        imageplanes = self.get_selected_imageplane_items()

        for imageplane in imageplanes:
            pn_imageplane = pm.PyNode(imageplane.content).getParent()
            pn_imageplane.translateX.unlock()
            pn_imageplane.translateY.unlock()
            pn_imageplane.translateZ.unlock()
            pn_imageplane.rotateX.unlock()
            pn_imageplane.rotateY.unlock()
            pn_imageplane.rotateZ.unlock()
            pn_imageplane.scaleX.unlock()
            pn_imageplane.scaleY.unlock()
            pn_imageplane.scaleZ.unlock()

    def onToggleDisplay(self, *args):
        """シーン内のすべてのイメージプレーンの Display モード (lokking through camera / in all views) をトグルする"""
        ips = pm.ls(type="imagePlane")
        current = ips[0].displayOnlyIfCurrent.get()

        for ip in ips:
            print(ip.name())
            ip.displayOnlyIfCurrent.set(not current)
            print(ip.displayOnlyIfCurrent.get())

        pm.select(ips)

    def onFixPanel(self, *args):
        """"""
        self.target_panel = pm.getPanel(wf=True)
        ui.set_value(self.cb_fix_target, value=True)

    def onLookThroughParent(self, *args):
        """"""
        ips = pm.ls(type="imagePlane")

        for ip_shape in ips:
            ip_trs = ip_shape.getParent()
            camera_shape = ip_trs.getParent().getShape()

            ip_shape.lookThroughCamera.disconnect()
            ip_shape.displayOnlyIfCurrent.set(True)
            camera_shape.message.connect(ip_shape.lookThroughCamera)

            pm.imagePlane(ip_shape, e=True, lookThrough=camera_shape, showInAllViews=False)

    def onCreateImageplane(self, *args):
        """"""
        camera = pm.PyNode(self.get_selected_camera_item().content)
        ip_trs, ip_shape = pm.imagePlane(width=10, height=10, maintainRatio=1, lookThrough=camera.name(), showInAllViews=False)
        print(ip_trs)
        print(camera)
        pm.parent(ip_trs, camera.getParent())

        ip_trs.translateX.set(0)
        ip_trs.translateY.set(0)
        ip_trs.translateZ.set(-20)
        ip_trs.rotateX.set(0)
        ip_trs.rotateY.set(0)
        ip_trs.rotateZ.set(0)
        ip_trs.scaleX.set(1)
        ip_trs.scaleY.set(1)
        ip_trs.scaleZ.set(1)

        ip_shape.alphaGain.set(0.5)
        ip_shape.colorGain.set((0.5, 0.5, 0.5))

    def onTearOff(self, *args):
        """"""
        active_panel = pm.getPanel(wf=True)
        panel_type = pm.getPanel(typeOf=active_panel)

        if panel_type == "modelPanel":
            pm.modelPanel(tearOffCopy=active_panel)


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
