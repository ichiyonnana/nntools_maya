"""

"""
import os
import re

import maya.cmds as cmds

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


def is_visible(obj_name):
    """指定した名前のオブジェクトが表示されているかどうか.

    そのものの visibility が true でも DAG の継承で非表示になっていれば false
    """
    full_path_name = cmds.ls(obj_name, long=True)[0]
    splited_path = full_path_name.split("|")
    depth = len(splited_path)

    for i in range(2, depth+1):
        partial_path = "|".join(splited_path[0:i])
        visible = cmds.getAttr(partial_path + ".visibility")
        if not visible:
            return False

    return True


def get_parent_camera(obj):
    """指定したオブジェクトより上の階層にある camera ノードを返す.

    指定したオブジェクトからルートの間にある camera ノードを子に持つトランスフォームノードを探し
    オブジェクトに一番階層が近いカメラオブジェクトを返す

    Args:
        pm_object (str): カメラを親に持つオブジェクト

    Returns:
        PyNode: camera ノード
    """
    full_path_name = cmds.ls(obj, long=True)[0]
    splited_path = full_path_name.split("|")
    depth = len(splited_path)

    for i in reversed(range(1, depth-1)):
        partial_path = "|".join(splited_path[0:i])
        camera_shape = cmds.listRelatives(partial_path, shapes=True, type="camera", fullPath=True)[0]

        if camera_shape:
            return camera_shape

    return None


class NN_ToolWindow(object):
    def __init__(self):
        self.window = window_name
        self.title = window_name
        self.size = (350, 365)

        self.target_panel = None  # Fix Panel 有効時に使用されるパネル

        self.camera_list_items = []  # カメラリストの ListItem 配列
        self.imageplane_list_items = []  # イメージプレーンリストの ListItem 配列

        self.image_editor = r"D:\Program Files\Adobe\Adobe Photoshop 2022\Photoshop.exe"

    def create(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window, window=True)

        # プリファレンスの有無による分岐
        if cmds.windowPref(self.window, exists=True):
            # ウィンドウのプリファレンスがあれば位置だけ保存して削除
            position = cmds.windowPref(self.window, q=True, topLeftCorner=True)
            cmds.windowPref(self.window, remove=True)

            # 前回位置に指定したサイズで表示
            cmds.window(
                self.window,
                t=self.title,
                maximizeButton=False,
                minimizeButton=False,
                topLeftCorner=position,
                widthHeight=self.size,
                sizeable=False,
                resizeToFitChildren=True
                )

        else:
            # プリファレンスがなければデフォルト位置に指定サイズで表示
            cmds.window(
                self.window,
                t=self.title,
                maximizeButton=False,
                minimizeButton=False,
                widthHeight=self.size,
                sizeable=False,
                resizeToFitChildren=True
                )

        self.layout()
        self.onUpdateCameraList()
        cmds.showWindow(self.window)

    def layout(self):
        ui.column_layout()

        ui.row_layout()

        # 左ペイン
        ui.column_layout()
        ui.row_layout()
        ui.button(label="Update", c=self.onUpdateCameraList)
        ui.button(label="Select", c=self.onSelectCameraObject)
        ui.button(label="Lock", c=self.onLockCamera, dgc=self.onUnLockCamera, annotation="L: Lock\nM: Unlock")
        ui.end_layout()
        self.camera_list = cmds.textScrollList(
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
        ui.button(label="Lock", c=self.onLockImageplane, dgc=self.onUnLockImageplane, annotation="L: Lock\nM: Unlock")
        ui.button(label="Dup", c=self.onDuplicateImageplane)
        ui.button(label="Edit", c=self.onEditImage, dgc=self.onSetImageEditor, annotation="L: Launch Editor\nM: Set Editor Path")
        ui.end_layout()
        self.item_list = cmds.textScrollList(
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
        ui.button(label="Hide Camera", c=self.onHideCamera)
        ui.end_layout()

        ui.row_layout()
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
        indices = cmds.textScrollList(self.camera_list, q=True, selectIndexedItem=True)

        if indices:
            return self.camera_list_items[indices[0]-1]
        else:
            return None

    def get_selected_imageplane_items(self):
        """イメージプレーンリストUIで選択されているイメージプレーンの ListItem オブジェクトを返す"""
        indices = [x - 1 for x in cmds.textScrollList(self.item_list, q=True, selectIndexedItem=True)]

        if indices:
            return [x for i, x in enumerate(self.imageplane_list_items) if i in indices]
        else:
            return []

    def onUpdateCameraList(self, *args):
        """Update ボタンクリックハンドラ｡カメラリストを更新する"""
        # ListItem 配列の更新
        self.camera_list_items = []

        for camera in cmds.ls(type="camera", long=True):
            # 非表示ならスキップ
            if not is_visible(camera):
                continue

            item = ListItem()
            item.content = camera
            m = re.match(r"(.*\|)?(.+)(Shape)(\d+)?", camera)
            item.name = m.groups()[1] + (m.groups()[3] or "")
            basename = re.sub(r"^.*\|", "", camera)

            # 名前の重複があればパスの差異を付与
            if cmds.objExists(basename) and len(cmds.ls(basename)) > 1:
                duplicates = cmds.ls(basename, long=True)
                duplicates.remove(item.content)
                uniq_str = get_unmatch_part(item.content, duplicates[0])

                if uniq_str:
                    item.name = "{}    ({})".format(item.name, uniq_str)

            self.camera_list_items.append(item)

        # ソート
        self.camera_list_items.sort(key=lambda x: x.content)

        # アクティブなカメラのリストUI上でのインデックス
        active_camera_name = nu.get_active_camera()
        camera_list = [x.content for x in self.camera_list_items]

        if active_camera_name in camera_list:
            active_camera_index = [x.content for x in self.camera_list_items].index(active_camera_name) + 1
        else:
            active_camera_index = 1

        # リストUIの更新
        cmds.textScrollList(self.camera_list, e=True, removeAll=True)
        cmds.textScrollList(
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
        camera = self.get_selected_camera_item().content
        camera_trs = cmds.listRelatives(camera, parent=True, fullPath=True)[0]
        all_imageplanes = cmds.listRelatives(camera_trs, ad=True, type="imagePlane") or []

        visible_indices = [i+1 for i, x in enumerate(all_imageplanes) if cmds.getAttr(x + ".visibility")]

        # ListItem 配列の更新
        self.imageplane_list_items = []

        for imageplane in all_imageplanes:
            if cmds.objectType(imageplane, isType="imagePlane"):
                item = ListItem()
                item.content = cmds.ls(imageplane, long=True)[0]
                item.name = re.sub(r"^.*\|", "", item.content)
                self.imageplane_list_items.append(item)

        # イメージプレーンリストUIの更新
        cmds.textScrollList(self.item_list, e=True, removeAll=True)

        if self.imageplane_list_items:
            cmds.textScrollList(self.item_list, e=True, append=[x.name for x in self.imageplane_list_items], sii=visible_indices)

    def onDoubleClickCameraListItem(self, *args):
        """カメラリストアイテムのダブルクリックのハンドラ｡アクティブパネルのカメラを切り替える"""
        camera_name = self.get_selected_camera_item().content
        active_panel = cmds.getPanel(wf=True)

        if ui.get_value(self.cb_fix_target):
            cmds.lookThru(self.target_panel, camera_name)

        else:
            cmds.lookThru(active_panel, camera_name)

    def onClickImageplaneListItem(self, *args):
        """イメージプレーンリストアイテムのクリック｡ビジビリティの更新"""
        selected_indices_onebase = cmds.textScrollList(self.item_list, q=True, selectIndexedItem=True) or []
        selected_indices = [x - 1 for x in selected_indices_onebase]

        for index in range(len(self.imageplane_list_items)):
            imageplane = self.imageplane_list_items[index].content
            # シェープの非表示解除
            cmds.setAttr(imageplane + ".visibility", True)

            # 親トランスフォームノードのビジビリティ変更
            imageplane_trs = cmds.listRelatives(imageplane, parent=True)[0]
            if index in selected_indices:
                cmds.setAttr(imageplane_trs + ".visibility", True)
            else:
                cmds.setAttr(imageplane_trs + ".visibility", False)

    def onDoubleClickImageplaneListItem(self, *args):
        """アイテムの選択"""
        self.onSelectImageplane()

    def onSelectCameraObject(self, *args):
        """カメラオブジェクトの選択"""
        camera_item = self.get_selected_camera_item()

        if camera_item:
            camera_name = camera_item.content
            camera_trs = cmds.listRelatives(camera_name, parent=True, fullPath=True)[0]
            cmds.select(camera_trs)

    def onSelectImageplane(self, *args):
        """イメージプレーンオブジェクトの選択"""
        cmds.select(clear=True)
        imageplane_items = self.get_selected_imageplane_items()

        for imageplane_item in imageplane_items:
            imageplane = imageplane_item.content
            imageplane_trs = cmds.listRelatives(imageplane, parent=True)[0]
            cmds.select(imageplane_trs, add=True)

    def onDuplicateImageplane(self, *args):
        """イメージプレーンオブジェクトと参照先の画像ファイルの複製"""
        # TODO: 実装

    def onEditImage(self, *args):
        """選択されているイメージプレーンを開く"""
        imageplane_items = self.get_selected_imageplane_items()

        for imageplane_item in imageplane_items:
            imageplane = imageplane_item.content
            image_name = cmds.getAttr(imageplane + ".imageName")
            filename = re.sub(r"/", r"\\", image_name)
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
            camera_trs = cmds.listRelatives(camera.content, parent=True)[0]
            cmds.setAttr(camera_trs + ".translateX", lock=True)
            cmds.setAttr(camera_trs + ".translateY", lock=True)
            cmds.setAttr(camera_trs + ".translateZ", lock=True)
            cmds.setAttr(camera_trs + ".rotateX", lock=True)
            cmds.setAttr(camera_trs + ".rotateY", lock=True)
            cmds.setAttr(camera_trs + ".rotateZ", lock=True)
            cmds.setAttr(camera_trs + ".scaleX", lock=True)
            cmds.setAttr(camera_trs + ".scaleY", lock=True)
            cmds.setAttr(camera_trs + ".scaleZ", lock=True)

    def onUnLockCamera(self, *args):
        """カメラオブジェクトのアンロック"""
        camera = self.get_selected_camera_item()

        if camera:
            camera_trs = cmds.listRelatives(camera.content, parent=True)[0]
            cmds.setAttr(camera_trs + ".translateX", lock=False)
            cmds.setAttr(camera_trs + ".translateY", lock=False)
            cmds.setAttr(camera_trs + ".translateZ", lock=False)
            cmds.setAttr(camera_trs + ".rotateX", lock=False)
            cmds.setAttr(camera_trs + ".rotateY", lock=False)
            cmds.setAttr(camera_trs + ".rotateZ", lock=False)
            cmds.setAttr(camera_trs + ".scaleX", lock=False)
            cmds.setAttr(camera_trs + ".scaleY", lock=False)
            cmds.setAttr(camera_trs + ".scaleZ", lock=False)

    def onLockImageplane(self, *args):
        """イメージプレーンオブジェクトのロック"""
        imageplanes = self.get_selected_imageplane_items()

        for imageplane in imageplanes:
            imageplane_trs = cmds.listRelatives(imageplane.content, parent=True)[0]
            cmds.setAttr(imageplane_trs + ".translateX", lock=True)
            cmds.setAttr(imageplane_trs + ".translateY", lock=True)
            cmds.setAttr(imageplane_trs + ".translateZ", lock=True)
            cmds.setAttr(imageplane_trs + ".rotateX", lock=True)
            cmds.setAttr(imageplane_trs + ".rotateY", lock=True)
            cmds.setAttr(imageplane_trs + ".rotateZ", lock=True)
            cmds.setAttr(imageplane_trs + ".scaleX", lock=True)
            cmds.setAttr(imageplane_trs + ".scaleY", lock=True)
            cmds.setAttr(imageplane_trs + ".scaleZ", lock=True)

    def onUnLockImageplane(self, *args):
        imageplanes = self.get_selected_imageplane_items()

        for imageplane in imageplanes:
            imageplane_trs = cmds.listRelatives(imageplane.content, parent=True)[0]
            cmds.setAttr(imageplane_trs + ".translateX", lock=False)
            cmds.setAttr(imageplane_trs + ".translateY", lock=False)
            cmds.setAttr(imageplane_trs + ".translateZ", lock=False)
            cmds.setAttr(imageplane_trs + ".rotateX", lock=False)
            cmds.setAttr(imageplane_trs + ".rotateY", lock=False)
            cmds.setAttr(imageplane_trs + ".rotateZ", lock=False)
            cmds.setAttr(imageplane_trs + ".scaleX", lock=False)
            cmds.setAttr(imageplane_trs + ".scaleY", lock=False)
            cmds.setAttr(imageplane_trs + ".scaleZ", lock=False)

    def onToggleDisplay(self, *args):
        """シーン内のすべてのイメージプレーンの Display モード (lokking through camera / in all views) をトグルする"""
        ips = cmds.ls(type="imagePlane")
        current = ips[0].displayOnlyIfCurrent.get()

        for ip in ips:
            print(ip.name())
            ip.displayOnlyIfCurrent.set(not current)
            print(ip.displayOnlyIfCurrent.get())

        cmds.select(ips)

    def onHideCamera(self, *args):
        """全てのパネルのカメラを非表示にする"""
        all_panels = cmds.getPanel(all=True)

        for panel in all_panels:                
            panel_type = cmds.getPanel(typeOf=panel)

            if panel_type == "modelPanel":
                cmds.modelEditor(panel, e=True, cameras=False)

    def onFixPanel(self, *args):
        """"""
        self.target_panel = cmds.getPanel(wf=True)
        ui.set_value(self.cb_fix_target, value=True)

    def onLookThroughParent(self, *args):
        """"""
        ips = cmds.ls(type="imagePlane", long=True)

        for ip_shape in ips:
            camera_shape = get_parent_camera(ip_shape)

            if camera_shape:
                # cmds.disconnectAttr(ip_shape + ".lookThroughCamera")
                cmds.setAttr(ip_shape + ".displayOnlyIfCurrent", True)
                cmds.connectAttr(camera_shape + ".message", ip_shape + ".lookThroughCamera", force=True)

            cmds.imagePlane(ip_shape, e=True, lookThrough=camera_shape, showInAllViews=False)

    def onCreateImageplane(self, *args):
        """"""
        camera = self.get_selected_camera_item().content
        ip_trs, ip_shape = cmds.imagePlane(width=10, height=10, maintainRatio=1, lookThrough=camera, showInAllViews=False)
        camera_trs = cmds.listRelatives(camera, parent=True, fullPath=True)[0]
        print(ip_trs)
        print(camera)
        cmds.parent(ip_trs, camera_trs)

        cmds.setAttr(ip_trs + ".translateX", 0)
        cmds.setAttr(ip_trs + ".translateY", 0)
        cmds.setAttr(ip_trs + ".translateZ", -20)
        cmds.setAttr(ip_trs + ".rotateX", 0)
        cmds.setAttr(ip_trs + ".rotateY", 0)
        cmds.setAttr(ip_trs + ".rotateZ", 0)
        cmds.setAttr(ip_trs + ".scaleX", 1)
        cmds.setAttr(ip_trs + ".scaleY", 1)
        cmds.setAttr(ip_trs + ".scaleZ", 1)

        cmds.setAttr(ip_shape + ".alphaGain", 0.5)
        cmds.setAttr(ip_shape + ".colorGain", 0.5, 0.5, 0.5)

    def onTearOff(self, *args):
        """"""
        active_panel = cmds.getPanel(wf=True)
        panel_type = cmds.getPanel(typeOf=active_panel)

        if panel_type == "modelPanel":
            cmds.modelPanel(tearOffCopy=active_panel)


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
