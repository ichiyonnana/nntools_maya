#! python
# coding:utf-8
"""

"""
import maya.cmds as cmds
import pymel.core as pm

import nnutil.core as nu
import nnutil.decorator as deco
import nnutil.ui as ui
import nnutil.display as nd


dialog_name = "NN_Camera"


class NN_ToolWindow(object):
    def __init__(self):
        self.window = dialog_name
        self.title = dialog_name
        self.size = (300, 95)

        self.all_cameras = pm.ls(type="camera")
        self.active_camera = pm.PyNode(nu.get_active_camera())
        self.active_camera_trs = self.active_camera.getParent()
        self.all_imageplanes = pm.listRelatives(self.active_camera_trs, ad=True)

    def create(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)
        self.window = cmds.window(
            self.window,
            t=self.title,
            widthHeight=self.size
        )
        self.layout()
        cmds.showWindow()

    def layout(self):
        ui.row_layout()

        # 左ペイン
        ui.column_layout()
        ui.row_layout()
        ui.button(label="Update", c=self.onUpdateCameraList)
        ui.button(label="Select Camera", c=self.onSelectCameraObject)
        ui.end_layout()
        self.camera_list = pm.textScrollList(
                                                    numberOfRows=20,
                                                    allowMultiSelection=False,
                                                    append=self.all_cameras,
                                                    selectItem=self.active_camera_trs,
                                                    showIndexedItem=1,
                                                    selectCommand=self.onClickCameraListItem,
                                                    doubleClickCommand=self.onDoubleClickCameraListItem
                                                    )
        ui.end_layout()

        # 右ペイン
        ui.column_layout()
        ui.button(label="Select Item", c=self.onSelectImageplane)
        self.item_list = pm.textScrollList(
                                                    numberOfRows=20,
                                                    allowMultiSelection=True,
                                                    append=self.all_imageplanes,
                                                    showIndexedItem=1,
                                                    selectCommand=self.onClickImageplaneListItem
                                                    )

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
        """カメラ選択のハンドラ｡子供のリストを更新する"""
        camera_name = pm.textScrollList(self.camera_list, q=True, selectItem=True)[0]
        camera = pm.PyNode(camera_name)
        camera_trs = camera.getParent()
        all_imageplanes = nu.pynode(nu.list_diff(pm.listRelatives(camera_trs, ad=True,  shapes=True), [camera_name]))
        visible_indices = [i+1 for i, x in enumerate(all_imageplanes) if x.visibility.get()]

        pm.textScrollList(self.item_list, e=True, removeAll=True)
        pm.textScrollList(self.item_list, e=True, append=all_imageplanes, sii=visible_indices)

    def onDoubleClickCameraListItem(self, *args):
        """カメラダブルクリックのハンドラ｡アクティブパネルのカメラを切り替える"""
        camera_name = pm.textScrollList(self.camera_list, q=True, selectItem=True)[0]
        active_panel = pm.getPanel(wf=True)

        pm.lookThru(active_panel, camera_name)

    def onClickImageplaneListItem(self, *args):
        """アイテムの選択状態の更新｡ビジビリティの更新"""
        all_items = pm.textScrollList(self.item_list, q=True, allItems=True)
        selected_items = pm.textScrollList(self.item_list, q=True, selectItem=True)

        for item in all_items:
            if item in selected_items:
                pm.PyNode(item).visibility.set(True)
                pm.PyNode(item).getParent().visibility.set(True)
            else:
                pm.PyNode(item).visibility.set(False)
                pm.PyNode(item).getParent().visibility.set(False)

    def onSelectCameraObject(self, *args):
        camera = pm.PyNode(pm.textScrollList(self.camera_list, q=True, selectItem=True)[0])
        pm.select(camera.getParent())

    def onSelectImageplane(self, *args):
        object = pm.PyNode(pm.textScrollList(self.item_list, q=True, selectItem=True)[0])
        pm.select(object.getParent())


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
