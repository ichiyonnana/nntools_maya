#! python
# coding:utf-8
"""

"""
import os
import re

import maya.cmds as cmds
import pymel.core as pm

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import nnutil.display as nd


window_name = "NN_Camera"
window = None


def get_window():
    return window


class ListItem:
    def __init__(self, name, key, content):
        self.name = name
        self.key = key
        self.content = content


class NN_ToolWindow(object):
    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (350, 340)

        self.target_panel = None  # Fix Panel 有効時に使用されるパネル

        self.camera_list_items = []  # カメラリストの ListItem 配列
        self.imageplane_list_items = []  # イメージプレーンリストの ListItem 配列

        self.all_cameras = pm.ls(type="camera")
        self.active_camera = pm.PyNode(nu.get_active_camera())
        self.active_camera_trs = self.active_camera.getParent()
        self.all_imageplanes = pm.listRelatives(self.active_camera_trs, ad=True)

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
                                                    append=self.all_cameras,
                                                    selectItem=self.active_camera_trs,
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
                                                    append=self.all_imageplanes,
                                                    showIndexedItem=1,
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
        ui.end_layout()

        ui.end_layout()

    def onUpdateCameraList(self, *args):
        """Update ボタンクリックハンドラ｡カメラリストを更新する"""
        self.all_cameras = pm.ls(type="camera")
        self.active_camera = pm.PyNode(nu.get_active_camera())
        self.active_camera_trs = self.active_camera.getParent()
        self.all_imageplanes = pm.listRelatives(self.active_camera_trs, ad=True)

        pm.textScrollList(self.camera_list, e=True, removeAll=True)

        pm.textScrollList(
                                self.camera_list,
                                e=True,
                                numberOfRows=20,
                                allowMultiSelection=False,
                                append=self.all_cameras,
                                selectItem=nu.get_active_camera(),
                                selectCommand=self.onClickCameraListItem,
                                doubleClickCommand=self.onDoubleClickCameraListItem
                                )

    def onClickCameraListItem(self, *args):
        """カメラリストアイテムのクリックのハンドラ｡子供のリストを更新する"""
        camera_name = pm.textScrollList(self.camera_list, q=True, selectItem=True)[0]
        camera = pm.PyNode(camera_name)
        camera_trs = camera.getParent()
        all_imageplanes = nu.pynode(nu.list_diff(pm.listRelatives(camera_trs, ad=True,  shapes=True), [camera_name]))
        visible_indices = [i+1 for i, x in enumerate(all_imageplanes) if x.visibility.get()]

        pm.textScrollList(self.item_list, e=True, removeAll=True)
        pm.textScrollList(self.item_list, e=True, append=all_imageplanes, sii=visible_indices)

    def onDoubleClickCameraListItem(self, *args):
        """カメラリストアイテムのダブルクリックのハンドラ｡アクティブパネルのカメラを切り替える"""
        camera_name = pm.textScrollList(self.camera_list, q=True, selectItem=True)[0]
        active_panel = pm.getPanel(wf=True)

        if ui.get_value(self.cb_fix_target):
            pm.lookThru(self.target_panel, camera_name)

        else:
            pm.lookThru(active_panel, camera_name)

    def onClickImageplaneListItem(self, *args):
        """イメージプレーンリストアイテムのクリック｡ビジビリティの更新"""
        all_items = pm.textScrollList(self.item_list, q=True, allItems=True)
        selected_items = pm.textScrollList(self.item_list, q=True, selectItem=True)

        for item in all_items:
            pm.PyNode(item).visibility.set(True)

            if item in selected_items:
                pm.PyNode(item).getParent().visibility.set(True)
            else:
                pm.PyNode(item).getParent().visibility.set(False)

    def onDoubleClickImageplaneListItem(self, *args):
        """アイテムの選択"""
        self.onSelectImageplane()

    def onSelectCameraObject(self, *args):
        """カメラオブジェクトの選択"""
        camera = pm.PyNode(pm.textScrollList(self.camera_list, q=True, selectItem=True)[0])
        pm.select(camera.getParent())

    def onSelectImageplane(self, *args):
        """イメージプレーンオブジェクトの選択"""
        pm.select(clear=True)
        objects = pm.textScrollList(self.item_list, q=True, selectItem=True)

        for object_name in objects:
            object = pm.PyNode(object_name)
            pm.select(object.getParent(), add=True)

    def onDuplicateImageplane(self, *args):
        """イメージプレーンオブジェクトと参照先の画像ファイルの複製"""
        # TODO: 実装

    def onEditImage(self, *args):
        """選択されているイメージプレーンを開く"""
        selected_items = pm.textScrollList(self.item_list, q=True, selectItem=True)

        for item in selected_items:
            ip = pm.PyNode(item)
            filename = re.sub(r"/", r"\\", ip.imageName.get())
            cmd = '"%s" %s' % (self.image_editor, filename)
            os.system(cmd)

    def onSetImageEditor(self, *args):
        """画像編集エディターの指定ダイアログ"""
        image_editor_path = ui.input_dialog(title="image editor path", message="input image editor path")

        if image_editor_path:
            self.image_editor = image_editor_path

    def onLockCamera(self, *args):
        """カメラオブジェクトのロック"""
        camera = pm.PyNode(pm.textScrollList(self.camera_list, q=True, selectItem=True)[0]).getParent()
        camera.translateX.lock()
        camera.translateY.lock()
        camera.translateZ.lock()
        camera.rotateX.lock()
        camera.rotateY.lock()
        camera.rotateZ.lock()
        camera.scaleX.lock()
        camera.scaleY.lock()
        camera.scaleZ.lock()

    def onUnLockCamera(self, *args):
        """カメラオブジェクトのアンロック"""
        camera = pm.PyNode(pm.textScrollList(self.camera_list, q=True, selectItem=True)[0]).getParent()
        camera.translateX.unlock()
        camera.translateY.unlock()
        camera.translateZ.unlock()
        camera.rotateX.unlock()
        camera.rotateY.unlock()
        camera.rotateZ.unlock()
        camera.scaleX.unlock()
        camera.scaleY.unlock()
        camera.scaleZ.unlock()

    def onLockImageplane(self, *args):
        """イメージプレーンオブジェクトのロック"""
        pm.select(clear=True)
        objects = pm.textScrollList(self.item_list, q=True, selectItem=True)

        for object_name in objects:
            object = pm.PyNode(object_name).getParent()
            object.translateX.lock()
            object.translateY.lock()
            object.translateZ.lock()
            object.rotateX.lock()
            object.rotateY.lock()
            object.rotateZ.lock()
            object.scaleX.lock()
            object.scaleY.lock()
            object.scaleZ.lock()

    def onUnLockImageplane(self, *args):
        """イメージプレーンオブジェクトのアンロック"""
        pm.select(clear=True)
        objects = pm.textScrollList(self.item_list, q=True, selectItem=True)

        for object_name in objects:
            object = pm.PyNode(object_name).getParent()
            object.translateX.unlock()
            object.translateY.unlock()
            object.translateZ.unlock()
            object.rotateX.unlock()
            object.rotateY.unlock()
            object.rotateZ.unlock()
            object.scaleX.unlock()
            object.scaleY.unlock()
            object.scaleZ.unlock()

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
