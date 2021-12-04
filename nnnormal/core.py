# coding:utf-8

import re
import maya.cmds as cmds
import pymel.core as pm
import pymel.core.nodetypes as nt
import pymel.core.datatypes as dt

import nnutil.core as nu
import nnutil.display as nd
import nnutil.ui as ui
import nnutil.decorator as deco


# 法線転送に使用するデフォルトの転送方法
# 0:法線に沿った最近接 3:ポイントに最近接
default_search_method = 3


def transfar_normal(objects=None, source_type=None, space="world", search_method=default_search_method):
    """ [pm] オブジェクトからオブジェクトへ法線を転送する

    引数未指定の場合は選択オブジェクトを対象とする

    Args:
        objects (list[Transform]): 転送元と転送先のオブジェクトを含むリスト
        source_type (str): objects のうちどれを転送元とするか。SO_FIRST:最初のオブジェクト SO_LAST:最後のオブジェクト
        search_method (int): 法線転送に使用する転送方法。0:法線に沿った最近接 3:ポイントに最近接
    """
    SO_FIRST = "First"
    SO_LAST = "Last"
    SO_CANCEL = "Cancel"

    # 引数が無効なら選択オブジェクト取得
    if not objects:
        objects = pm.selected(flatten=True)

    # オブジェクトが一つなら警告して終了
    if len(objects) <= 1:
        print("select 2 or more objects.")
        return

    # ソースオブジェクトの決定
    source = []
    targets = []

    # オブジェクトが複数あればソースを確認
    if source_type not in [SO_FIRST, SO_LAST]:
        source_type = pm.confirmDialog(title='Transfer Normal',
                                       message='Select Source',
                                       button=[SO_FIRST, SO_LAST, SO_CANCEL],
                                       defaultButton=SO_LAST,
                                       cancelButton=SO_CANCEL,
                                       dismissString=SO_CANCEL
                                       )

        if source_type == SO_CANCEL:
            print("canceled")
            return

    if source_type == SO_FIRST:
        source = objects[0]
        targets = objects[1:]
    else:
        source = objects[-1]
        targets = objects[0:-1]

    # 転送
    for target in targets:
        pm.transferAttributes([source, target],
                              transferPositions=0,
                              transferNormals=1,
                              transferUVs=0,
                              transferColors=0,
                              sampleSpace=0,
                              sourceUvSpace="map1",
                              targetUvSpace="map1",
                              searchMethod=search_method,
                              flipUVs=0,
                              colorBorders=1
                              )


copied_normal_object = None  # copy_normal,paste_normal で使用されるコピー元オブジェクト
copied_normal = None  # copy_normal,paste_normal で使用されるコピーされた法線


def copy_normal(targets=None):
    """ [pm] 法線のコピー｡複数ある場合は平均

    引数未指定の場合は選択オブジェクトを対象とする
    オブジェクトの場合は転送ソースにする

    Args:
        targets(list[Transform or MeshVertex or MeshEdge or MeshFace or MeshVertexFace]): 法線をコピーするオブジェクトかコンポーネント
    """
    global copied_normal_object
    global copied_normal

    # 引数が無効なら選択オブジェクト取得
    if not targets:
        targets = pm.selected(flatten=True)

        if not targets:
            "no targets"
            return

    # ターゲットの種類による分岐
    # TODO: targets の要素がすべて同じ型かどうかのチェック
    if isinstance(targets[0], nt.Transform) and isinstance(targets[0].getShape(), nt.Mesh):
        # ターゲットがオブジェクトならオブジェクトコピー
        copied_normal_object = targets[0]
        copied_normal = None
        nd.message("copied (object)")

    else:
        copy_source = []
        if isinstance(targets[0], pm.MeshFace):
            # フェースの場合は頂点フェース経由でノーマルを平均
            # TODO: 選択範囲内での接するフェース数によみ重み付け (問題なければ無視)
            copy_source = nu.to_vtxface(targets)

        elif isinstance(targets[0], pm.MeshEdge):
            # エッジの場合は頂点変換して平均
            copy_source = nu.to_vtx(targets)

        elif isinstance(targets[0], pm.MeshVertex):
            # 頂点の場合は頂点法線取得して平均
            copy_source = targets

        elif isinstance(targets[0], pm.MeshVertexFace):
            # 頂点フェースの場合は選択されたものだけそのまま平均
            copy_source = targets

        else:
            print(str(type(targets[0])) + "is not supported.")
            return

        # 法線取得して平均したものをモジュール変数に保持
        coords = pm.polyNormalPerVertex(copy_source, q=True, xyz=True)
        normals = nu.coords_to_vector(coords)
        copied_normal_object = None
        copied_normal = sum(normals)
        copied_normal.normalize()
        copied_normal = tuple(copied_normal)

        # 平均した結果がゼロベクトルなら破棄する
        if not copied_normal == (0.0, 0.0, 0.0):
            nd.message("copied")

        else:
            nd.message("zero vector")
            copied_normal_object = None
            copied_normal = None


def paste_normal(targets=None):
    """ [pm] 法線のペースト｡オブジェクト選択時はソースにより法線ペーストか転送か切り替える｡

    Args:
        targets(list[Transform or MeshVertex or MeshEdge or MeshFace or MeshVertexFace]): 法線をペーストするオブジェクトかコンポーネント
    """
    global copied_normal_object
    global copied_normal

    # 引数が無効なら選択オブジェクト取得
    if not targets:
        targets = pm.selected(flatten=True)

        if not targets:
            "no targets"
            return

    # コピー元オブジェクトによる分岐
    if copied_normal_object:
        # コピー元がオブジェクト
        if isinstance(targets[0], nt.Transform) and isinstance(targets[0].getShape(), nt.Mesh):
            # オブジェクト to オブジェクトの場合は転送
            if len(nu.list_diff(targets, [copied_normal_object])) > 0:
                objects = [copied_normal_object] + nu.list_diff(targets, [copied_normal_object])
                transfar_normal(objects=objects, source_type="First")
        else:
            # オブジェクト to コンポーネントの場合は部分転送
            target_components = []
            set_node = pm.sets(targets)

            pm.transferAttributes([copied_normal_object, set_node],
                                  transferPositions=0,
                                  transferNormals=1,
                                  transferUVs=0,
                                  transferColors=0,
                                  sampleSpace=0,
                                  sourceUvSpace="map1",
                                  targetUvSpace="map1",
                                  searchMethod=default_search_method,
                                  flipUVs=0,
                                  colorBorders=1
                                  )

            # TODO: 転送後に法線上書きしてセットと転送ノード消す

    elif copied_normal:
        # コピー元がコンポーネントの場合
        # ペースト対象コンポーネント
        target_components = []
        # ペースト後にソフトエッジ復帰するエッジのリスト
        softedges = []

        # コピー先による分岐
        if isinstance(targets[0], nt.Transform) and isinstance(targets[0].getShape(), nt.Mesh):
            # コピー先がオブジェクト
            target_components = targets

        elif isinstance(targets[0], pm.MeshFace):
            # コピー先がフェースの場合
            target_components = nu.to_vtxface(targets)
            border_vertices = nu.to_border_vertices(targets)

            # 外周はハードエッジの有無によって一つ外側までペースト範囲に含める
            for v in border_vertices:
                if not [e for e in nu.to_edge(v) if nu.is_hardedge(e)]:
                    target_components.append(v)

                else:
                    vtxfaces = nu.list_intersection(nu.to_vtxface(v), target_components)
                    additions = [cvf for vf in vtxfaces for cvf in nu.get_connected_vtx_faces(vf)]
                    target_components.extend(additions)

            # ターゲットに接しているすべてのエッジのソフトエッジ/ハードエッジを保存する
            softedges = [e for e in nu.to_edge(target_components) if not nu.is_hardedge(e)]

        elif isinstance(targets[0], pm.MeshEdge):
            # エッジの場合は頂点変換
            # TODO: ハードエッジ考慮
            target_components = nu.to_vtx(targets)

        elif isinstance(targets[0], pm.MeshVertex):
            # 頂点の場合はそのまま
            target_components = targets

        elif isinstance(targets[0], pm.MeshVertexFace):
            # 頂点フェースの場合はそのまま
            target_components = targets

        else:
            print(str(type(targets[0])) + "is not supported.")
            return

        # 複数コンポーネントで polyNormalPerVertex 呼ぶとクラッシュすることがあるのでループにする
        for comp in target_components:
            pm.polyNormalPerVertex(comp, xyz=tuple(copied_normal))

        if softedges:
            pm.polySoftEdge(softedges, a=180, ch=1)

        nd.message("pasted")

    else:
        # コピーされていない場合
        print("not yet copied")

    pm.select(targets)


class NN_ToolWindow(object):
    window_width = 300

    def __init__(self):
        self.window = 'NormalTools'
        self.title = 'NormalTools'
        self.size = (self.window_width, 95)

        pm.selectPref(trackSelectionOrder=True)

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
        ui.column_layout()

        ui.row_layout()
        ui.button(label="Transfer (First)", c=self.onTransferNormalFirst)
        ui.button(label="Transfer (Last)", c=self.onTransferNormalLast)
        ui.button(label="Transfer (Prompt)", c=self.onTransferNormalPrompt)
        ui.end_layout()

        ui.row_layout()
        ui.button(label="Copy", c=self.onCopyNormal)
        ui.button(label="Paste", c=self.onPasteNormal)
        ui.end_layout()

        ui.end_layout()

    # イベントハンドラ
    @deco.undo_chunk
    def onTransferNormalFirst(self, *args):
        """From First で転送"""
        transfar_normal(source_type="First")

    @deco.undo_chunk
    def onTransferNormalLast(self, *args):
        """From Last で転送"""
        transfar_normal(source_type="Last")

    @deco.undo_chunk
    def onTransferNormalPrompt(self, *args):
        """ユーザーに確認して転送"""
        transfar_normal()

    @deco.undo_chunk
    def onCopyNormal(self, *args):
        """法線コピー"""
        copy_normal()

    @deco.undo_chunk
    def onPasteNormal(self, *args):
        """法線ペースト"""
        paste_normal()


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
