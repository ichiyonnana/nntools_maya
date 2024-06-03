#! python
# coding:utf-8
""" 
単独で機能になっているがパッケージにするほどでもないもの
基本的には Maya のホットキーやシェルフから直接呼ぶもの
戻り値のないもの
"""

import itertools
import re
import datetime
import glob
import os

import maya.cmds as cmds
import maya.mel as mel

import pymel.core as pm
import pymel.core.nodetypes as nt
import pymel.core.datatypes as dt

from . import core as nu
from . import command as nuc
from . import ui as ui


def message(s):
    """ 簡易 inVewMessage """
    cmds.inViewMessage(smg=s, pos="topCenter", bkc="0x00000000", fade=True)


def get_project_root():
    """ 現在開いているシーンのルートディレクトリを取得する
    TODO: ディレクトリ構成が違う場合や開いてるシーンと現在のプロジェクトの指定が一致していない場合の処理 (プロンプトで選ばせれば良い)
    file コマンドで l オプション指定してないとたまに空文字列返す場合がある
        https://forums.cgsociety.org/t/cmds-file-scenename-returns-nothing/1565243/2
    """
    currentScene = cmds.file(q=True, sn=True, l=True)[0]
    newProject = re.sub(r'/scenes/.+$', '', currentScene, 1)
    return newProject


def set_project_from_scene():
    """ 現在開いているシーンからプロジェクトを設定する """
    currentScene = cmds.file(q=True, sn=True, l=True)[0]
    newProject = re.sub(r'/scenes/.+$', '', currentScene, 1)
    cmds.workspace(newProject, openWorkspace=True)
    cmds.inViewMessage(amg=newProject, pos="topCenter", fade=True)


def disable_all_maintain_max_inf():
    """ シーンに存在するすべてのスキンクラスターの maintanMaxInfluences を無効にする """
    sc_list = cmds.ls(type="skinCluster")
    for sc in sc_list:
        cmds.setAttr(sc + ".maintainMaxInfluences", 0)


def set_coord(axis, v, space="object", relative=False):
    """ [cmds] 選択頂点の指定した軸の座標値を設定する

    Args:
        axis (str): "x", "y", "z"
        v (str): 頂点を表すコンポーネント文字列
        space (str): 座標系｡ "object" or "world"｡ デフォルトは world
        relative (bool): True なら相対的な移動になる｡デフォルトは False
    """
    selection = cmds.ls(selection=True, flatten=True)

    for vtx in selection:
        if space == "object":
            if relative:
                t = (0, 0, 0)
                if axis == "x":
                    t = (v, 0, 0)
                if axis == "y":
                    t = (0, v, 0)
                if axis == "z":
                    t = (0, 0, v)

                cmds.xform(vtx, relative=True, os=True, t=t)
            else:
                # 現在の座標
                x, y, z = cmds.xform(vtx, q=True, a=True, os=True, t=True)

                t = (0, 0, 0)
                if axis == "x":
                    t = (v, y, z)
                if axis == "y":
                    t = (x, v, z)
                if axis == "z":
                    t = (x, y, v)

                # 新しい座標の設定
                cmds.xform(vtx, absolute=True, os=True, t=t)

        else:
            if relative:
                t = (0, 0, 0)
                if axis == "x":
                    t = (v, 0, 0)
                if axis == "y":
                    t = (0, v, 0)
                if axis == "z":
                    t = (0, 0, v)

                cmds.xform(vtx, relative=True, ws=True, t=t)
            else:
                # 現在の座標
                x, y, z = cmds.xform(vtx, q=True, a=True, ws=True, t=True)

                t = (0, 0, 0)
                if axis == "x":
                    t = (v, y, z)
                if axis == "y":
                    t = (x, v, z)
                if axis == "z":
                    t = (x, y, v)

                # 新しい座標の設定
                cmds.xform(vtx, absolute=True, ws=True, t=t)


def set_x_zero():
    """ 選択頂点の X ローカル座標を 0 に設定する """
    set_coord('x', 0)


def set_y_zero():
    """ 選択頂点の Y ローカル座標を 0 に設定する """
    set_coord('y', 0)


def set_z_zero():
    """ 選択頂点の Z ローカル座標を 0 に設定する """
    set_coord('z', 0)


def extract_transform():
    """ 選択オブジェクトの親に作成したトランスフォームノードに自身のトランスフォームを逃がして TRS を基準値にする """
    selections = pm.ls(selection=True, type="transform")

    for obj in selections:
        parent = obj.getParent()
        group = pm.group(empty=True)

        if parent:
            pm.parent(group, parent)

        group.setTranslation(obj.getTranslation())
        group.setRotation(obj.getRotation())
        group.setScale(obj.getScale())

        pm.parent(obj, group)

    pm.inViewMessage(smg="extract transform", pos="topCenter", bkc="0x00000000", fade=True)


def create_set_with_name():
    """ 名前を指定して選択オブジェクトでセットを作成刷る """

    cmd = """
    string $name;
    string $ret = `promptDialog
            -title "create set"
            -message "Enter Name:"
            -tx "set"
            -button "OK"
            -button "Cancel"
            -defaultButton "OK"
            -cancelButton "Cancel"
            -dismissString "Cancel"`;

    if ($ret == "OK") {
        $name = `promptDialog -query -text`;
        sets -name $name;
    }
    """

    mel.eval(cmd)


def set_transform_constraint_edge():
    """ トランスフォームコンストレイントを edge に設定 """
    cmd = """
    xformConstraint -type "edge";
    inViewMessage -smg "constraint: edge" -pos topCenter -bkc 0x00000000 -fade;
    """

    mel.eval(cmd)


def set_transform_constraint_surface():
    """ トランスフォームコンストレイントをに surface 設定 """
    cmd = """
    xformConstraint -type "surface";
    inViewMessage -smg "constraint: surface" -pos topCenter -bkc 0x00000000 -fade;
    """

    mel.eval(cmd)


def set_transform_constraint_none():
    """ トランスフォームコンストレイントを解除 """
    cmd = """
    xformConstraint -type "none";
    inViewMessage -smg "constraint: none" -pos topCenter -bkc 0x00000000 -fade;
    """

    mel.eval(cmd)


def straighten_uv_shell():
    """ 選択UVを直線化し、同一シェルの他のUVをoptimizeする

    選択UVのU軸/V軸のそれぞれの分布を調べて分布が大きい方(シェルが長い方)に併せて縦横を決める
    """
    uvs = cmds.ls(selection=True)

    u_dist = [cmds.polyEditUV(x, q=True)[0] for x in uvs]
    u_length = max(u_dist) - min(u_dist)
    v_dist = [cmds.polyEditUV(x, q=True)[1] for x in uvs]
    v_length = max(v_dist) - min(v_dist)

    if u_length < v_length:
        mel.eval("alignUV minU;")
        mel.eval("AriUVRatio;")
        mel.eval('polyPerformAction "polyPinUV -value 1" v 0;')
        mel.eval("SelectUVShell;")

        mel.eval("performUnfold 0;")
        mel.eval("performPolyOptimizeUV 0;")
        mel.eval('polyPerformAction "polyPinUV -op 1" v 0;')
        mel.eval("unfold -i 5000 -ss 0.001 -gb 0 -gmb 0.5 -pub 0 -ps 0 -oa 1 -us off;")
    else:
        mel.eval("alignUV minV;")
        mel.eval("AriUVRatio;")
        mel.eval('polyPerformAction "polyPinUV -value 1" v 0;')
        mel.eval("SelectUVShell;")

        mel.eval("performUnfold 0;")
        mel.eval("performPolyOptimizeUV 0;")
        mel.eval('polyPerformAction "polyPinUV -op 1" v 0;')
        mel.eval("unfold -i 5000 -ss 0.001 -gb 0 -gmb 0.5 -pub 0 -ps 0 -oa 1 -us off;")


def make_lattice():
    mel.eval("CreateLattice")


def make_semisphere_bend():
    """ ベンドデフォーマーを直交させて2つかけて平面を半球にするデフォーマー｡
    TODO: ハードコーディング修正して値返して
    """
    target = cmds.ls(selection=True)

    bend1, bendhandle1 = cmds.nonLinear(target, type="bend", lowBound=-1, highBound=1, curvature=90)

    cmds.setAttr("%(bendhandle1)s.scaleX" % locals(), 23.6)
    cmds.setAttr("%(bendhandle1)s.scaleY" % locals(), 23.6)
    cmds.setAttr("%(bendhandle1)s.scaleZ" % locals(), 23.6)

    cmds.setAttr("%(bendhandle1)s.rotateY" % locals(), 90)

    bend2, bendhandle2 = cmds.nonLinear(target, type="bend", lowBound=-1, highBound=1, curvature=90)

    cmds.setAttr("%(bendhandle2)s.scaleX" % locals(), 23.6)
    cmds.setAttr("%(bendhandle2)s.scaleY" % locals(), 23.6)
    cmds.setAttr("%(bendhandle2)s.scaleZ" % locals(), 23.6)

    cmds.setAttr("%(bendhandle2)s.rotateX" % locals(), -90)
    cmds.setAttr("%(bendhandle2)s.rotateY" % locals(), 90)


def toggle_bend():
    """ ベンドの envelope 0/1 トグル    
    TODO: ハードコーディング修正して値返して
    """

    bend_nodes = [
        "bend5",
        "bend6",
        "bend7",
        "bend8",
    ]

    envelope = (cmds.getAttr("bend5.envelope") == 1)

    if envelope:
        for bend in bend_nodes:
            cmds.setAttr("%(bend)s.envelope" % locals(), 0)
    else:
        for bend in bend_nodes:
            cmds.setAttr("%(bend)s.envelope" % locals(), 1)


def connect_file_to_active_material():
    """
    TODO: 選択マテリアルの取得とテクスチャ名のダイアログ
    """
    material = ""
    file = ""
    cmds.connectAttr("%(material)s.color"%locals(), "%(file)s.outColor"%locals())


def rename_imageplane():
    """ 選択したイメージプレーンのノード名をファイル名を元にリネーム
    """
    selections = cmds.ls(selection=True)

    for obj in selections:
        current_name = obj
        image_name = cmds.getAttr(obj, obj + ".imageName")
        file_name = re.sub(r'^.+[/\\]', '', image_name)
        base_name = re.sub(r'\..*$', '', file_name)

        if not base_name == '':
            new_name = re.sub(r'^(ip_)*', 'ip_', base_name)
            cmds.rename(obj, new_name)


def freeze_instance():
    """ 選択オブジェクトのうちインスタンスコピーだけオブジェクトに変換する

    インスタンスコピーとそうじゃないものをまとめて選択した状態でインスタンスだけフリーズする｡
    Maya 標準だと非インスタンスコピーオブジェクトが含まれると警告出て止まるため
    """
    selections = cmds.ls(selection=True)
    cmds.select(clear=True)
    for obj in selections:
        try:
            cmds.select(obj)
            mel.eval("convertInstanceToObject")
        except:
            # 非インスタンスコピーの警告を無視する
            pass


def get_adjacent_edgeloop(edges, incomplete=True):
    """ 指定したエッジの進行方向のエッジを返す

    ___ → _
    返値は隣のエッジを要素とするリスト(最大要素数2)
    incomplete: 候補エッジが複数合った場合の処理
                    True:  それらしいエッジを返す
                    False: 空リストを返す
    """

    # エッジに隣接するエッジ集合のうちフェースを共有しないものを取得する
    # 複数あれば incomplete==True の場合のみなす角が一番小さいものを返す
    pass


def get_adjacent_edgering(edges, incomplete=True):
    """ 指定したエッジの隣のエッジリングとなるエッジを返す

    ||| → |
    返値は隣のエッジを要素とするリスト(最大要素数2)
    incomplete: 候補エッジが複数合った場合の処理
                    True:  それらしいエッジを返す
                    False: 空リストを返す
    """

    # エッジに隣接するフェースを構成するエッジ集合のうちエッジと頂点を共有しないエッジを取得する
    # 複数あれば incomplete==True の場合のみなす角が一番小さいものを返す
    pass


def extend_edgeloop_selection_grow(incomplete=True):
    """ エッジループを伸ばす方向に選択拡張する
    TODO: 実装
    """
    mel.eval("PolySelectTraverse 5")  # TODO: 仮なので置き換えて


def extend_edgeloop_selection_shrink(incomplete=True):
    """ エッジループを伸ばす方向に選択拡張する
    TODO: 実装
    """
    mel.eval("PolySelectTraverse 6")  # TODO: 仮なので置き換えて


def extend_edgering_selection_grow(incomplete=True):
    """ エッジリングを選択拡張する
    TODO: 実装
    """
    pass


def extend_edgering_selection_shrink(incomplete=True):
    """ エッジリングを選択拡張する
    TODO: 実装
    """
    pass


class Line():
    """ 線分クラス
    
    """

    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2


def get_nearest_point_between_lines(p1, p2, p3, p4):
    """[summary]

    TODO:実装

    Args:
        p1 ([type]): [description]
        p2 ([type]): [description]
        p3 ([type]): [description]
        p4 ([type]): [description]
    """
    # https://math.stackexchange.com/questions/1993953/closest-points-between-two-lines
    pass


def debevel(edges):
    """ ベベル面の中央連続エッジを渡すとエッジを移動してベベル前のコーナーを復帰する
    TODO:実装
    """
    # エッジから頂点に変換
    # 頂点の隣接エッジ(引数エッジ列から直行するエッジ)を取得
    # 隣接エッジの延長エッジの線分を取得 (両側で二つ)
    #   エッジが4本なら角度にかかわらず対向エッジの線分
    #   エッジが3本なら2本の中間の線分
    # 線分の延長線上の最近接点に頂点を移動する
    pass


def face_to_camera():
    active_panel = cmds.getPanel(wf=True)
    camera = cmds.modelPanel(active_panel, q=True, camera=True)
    selections = cmds.ls(selection=True)

    for target in selections:
        mel.eval("matchTransform -rot " + target + " " + camera)


def parent_to_camera():
    active_panel = cmds.getPanel(wf=True)
    camera = cmds.modelPanel(active_panel, q=True, camera=True)
    targets = cmds.ls(selection=True)
    cmds.parent(targets, camera)


def delete_uvSet_noncurrent():
    """ カレント以外の UV セットを削除する
    """
    selections = cmds.ls(selection=True)

    for obj in selections:
        uvset_list = cmds.polyUVSet(obj, q=True, allUVSets=True)

        for uvset in uvset_list[1:]:
            cmds.polyUVSet(obj, delete=True, uvSet=uvset)


target_objects = []


def snap_to_closest():
    selections = nuc.get_selection()
    node_type = cmds.nodeType(selections[0])

    global target_objects

    # 選択がオブジェクトならターゲットに設定する
    if node_type == "transform":
        target_objects = selections
        message("set targets: ")
        message(target_objects)

    # 選択がコンポーネントならスナップ処理を行う
    elif node_type == "mesh":
        target_vts = []

        for target_object in target_objects:
            target_vts.extend(nu.to_vtx(target_object))

        target_points = [nu.get_vtx_coord(x) for x in target_vts]
        message(target_objects)
        message(target_vts)

        # 選択頂点の移動
        vts = nu.to_vtx(selections)

        for vtx in vts:
            point = nu.get_vtx_coord(vtx)
            target_point = nu.get_nearest_point_from_point(point, target_points)
            nu.set_vtx_coord(vtx, target_point)

        message("move points")


def close_hole_all(obj=None):
    """ 指定したオブジェクトの穴をすべて塞ぐ
    """
    if not obj:
        obj = nuc.get_selection()

    cmds.selectMode(component=True)
    cmds.selectType(polymeshEdge=True)
    cmds.select(nu.to_edge(obj))
    mel.eval("ConvertSelectionToEdgePerimeter")
    edges = nuc.get_selection()
    polyline_list = nu.get_all_polylines(edges)

    for polyline in polyline_list:
        cmds.select(polyline)
        cmds.polyExtrudeEdge()
        mel.eval("polyMergeToCenter")


# 二角形ホール処理スクリプト
def get_digon_edge_pairs(obj):
    """ obj に含まれるすべての二角形ホールを取得する
    """

    # ボーダーエッジ取得
    border_edges = []

    all_faces = pm.polyListComponentConversion(obj.faces, ff=True, te=True, bo=True)
    if all_faces:
        border_edges = [pm.PyNode(x) for x in pm.filterExpand(all_faces, sm=32, ex=True)]

    # ボーダーエッジ同士で 2 頂点を共有するペアを探す
    digon_edge_pairs = []

    for edge in border_edges:
        for connected_edge in [x for x in edge.connectedEdges() if x in border_edges]:
            if len(nu.list_intersection(edge.connectedVertices(), connected_edge.connectedVertices())) == 2:
                if not (connected_edge, edge) in digon_edge_pairs:
                    digon_edge_pairs.append((edge, connected_edge))
    
    return digon_edge_pairs


def remove_digon_holes(obj):
    """ obj に含まれるすべての二角形ホールを削除する 

    """

    # 二角形ホールの取得
    digon_pairs = get_digon_edge_pairs(obj)

    # 二角形ホールの削除
    if digon_pairs:
        all_edges = [edge for edges in digon_pairs for edge in edges]

        # 辺にそれぞれ頂点を追加する
        pm.select(clear=True)
        pm.polySubdivideEdge(all_edges)
        edges = pm.ls(selection=True, flatten=True)
        vertices = [x for e in edges for x in e.connectedVertices()]
        target_vertices = [x for x in vertices if len(x.connectedEdges()) == 2]

        # 追加した頂点をマージし､マージ後の頂点を削除する
        pm.select(clear=True)
        pm.polyMergeVertex(target_vertices)
        merged_vertex = pm.ls(selection=True, flatten=True)
        pm.delete(merged_vertex)

    return len(digon_pairs)


def select_digon_holes(objects=None):
    """ すべての二角形ホールの構成エッジを選択する
    指定オブジェクトのすべての二角形ホールの構成エッジを選択する
    引数無しで選択オブエクトを対象とする
    """

    if not objects:
        objects = pm.ls(selection=True)

    # 二角形ホールの選択
    pm.select(clear=True)

    for obj in objects:
        digon_pairs = get_digon_edge_pairs(obj)

        if digon_pairs:
            all_edges = [edge for edges in digon_pairs for edge in edges]
            pm.select(all_edges, add=True)


def remove_digon_holes_from_objects(objects=None, display_message=True):
    """ すべての二角形ホールを削除する
    指定オブジェクトのすべての二角形ホールを削除する
    引数無しで選択オブエクトを対象とする
    """

    if not objects:
        objects = pm.ls(selection=True)

    count = 0

    for obj in objects:
        n = remove_digon_holes(obj)
        count += n

    if display_message:
        msg = "remove %d holes." % count
        print(msg)
        message(msg)


def merge_to_last():
    """ 最後に選択した頂点にマージ """
    # 最終選択頂点座標の取得
    sel = pm.ls(orderedSelection=True, flatten=True)
    point = sel[-1].getPosition()

    # センターへマージしてから移動
    mel.eval("polyMergeToCenter")
    vtx = pm.ls(orderedSelection=True, flatten=True)[0]
    vtx.setPosition(point)


def merge_in_range(vertices, r, connected=True):
    """ 指定した頂点から指定した範囲内にある頂点をマージする
    マージ後の頂点座標は引数で指定した頂点の中央

    Args
        vertices (list[MeshVertex]): マージの基準となる頂点リスト。最初に中央へマージされる
        r (float):          vertices からマージ対象となる頂点までの最大距離
        connected (bool): True: 選択頂点の隣接頂点のみをマージ対象とする
                          False:  選択オブジェクト全体の頂点を対象とする
    """
    # 指定頂点をセンターへマージ
    base_position = sum([x.getPosition(space="world") for x in vertices]) / len(vertices)
    pm.polyMergeVertex(vertices, d=100)
    vtx = pm.selected(flatten=True)[0]
    
    # マージ判定対象
    target = []

    if connected:
        target = vtx.connectedVertices() + vtx
    else:
        obj = pm.PyNode(nuc.get_object(vtx))
        target = obj.vertices()

    # マージ対象
    vertices_to_merge = [vtx for vtx in target if (vtx.getPosition(space="world") - base_position).length() <= r]

    pm.polyMergeVertex(vertices_to_merge, d=r)
    vtx = pm.selected(flatten=True)[0]

    # 基準頂点の位置へ移動
    vtx.setPosition(base_position, space="world")


def shorten_filepath():
    """ 選択したファイルノードのパスの sourceimages 前を削除する """
    file_nodes = [x for x in pm.selected() if x.type() == "file"] 

    for file in file_nodes:
        old = pm.getAttr(file + ".fileTextureName")
        new = re.sub(r".*sourceimages", "sourceimages", old)
        pm.setAttr(file + ".fileTextureName", new, type="string")


def replace_mesh_as_instance():
    """ 最後に選択したオブジェクトのインスタンスコピーでそれ以外のオブジェクトを置き換える

    複数のオブジェクトを選択して実行
    """
    # 選択オブジェクトの取得
    selections = [x for x in pm.selected()]

    dst_objects = selections[0:-1]
    src_object = selections[-1]

    # 複製オブジェクト分だけインスタンスコピーを作成
    copies = [pm.instance(src_object)[0] for x in range(len(dst_objects))]

    for i, dst in enumerate(dst_objects):
        # インスタンスコピーを同じ親の子にする
        parent = dst.getParent()

        if parent:
            copies[i].setParent(parent)
        else:
            copies[i].setParent(top=True)
        
        # トランスフォームを一致させる
        matrix = dst.getMatrix(objectSpace=True)
        copies[i].setMatrix(matrix, objectSpace=True)

        # リネームして元のオブジェクトを削除する
        name = dst.name()
        pm.delete(dst)
        copies[i].rename(name)


def replace_mesh_as_connection():
    """ 最後に選択したオブジェクトの形状を inmesh-outmesh 接続でそれ以外のオブジェクトにコピーする

    複数のオブジェクトを選択して実行
    """
    selections = [x for x in pm.selected()]

    dst_objects = selections[0:-1]
    src_object = selections[-1]

    print(dst_objects)
    print(src_object)

    for dst in dst_objects:
        if dst not in src_object.outMesh.connections(dst.inMesh):
            src_object.outMesh.connect(dst.inMesh)


def weight_paint_mode_with_selected_joint(joint=None, meshes=None):
    """選択したメッシュに対して選択したジョイントがアクティブな状態でウェイトペイントモードに入る"""
    if not joint:
        joint = [x for x in nuc.selected() if isinstance(x, nt.Joint)][0]
    
    if not meshes:
        meshes = [x for x in nuc.selected() if isinstance(x, nt.Transform)]

    if joint and meshes:
        pm.select(meshes, replace=True)
        mel.eval("ArtPaintSkinWeightsToolOptions")
        mel.eval('artSkinInflListChanging "%s" 1' % joint.name())
        mel.eval("artSkinInflListChanged artAttrSkinPaintCtx")


def get_isolated_uv_face():
    isolate_objectset = pm.ls("textureEditorIsolateSelectSet")

    if isolate_objectset:
        return isolate_objectset[0].members()
    else:
        return None


def change_uveditor_image(n):
    uveditor_panel_name = "polyTexturePlacementPanel1"

    iso_faces = get_isolated_uv_face()

    if iso_faces:
        pm.select(iso_faces)
        mel.eval("ToggleUVIsolateViewSelected;")

    mel.eval("textureWindowSelectTexture %s %s;" % (n, uveditor_panel_name))
    mel.eval("uvTbUpdateTextureItems %s;" & uveditor_panel_name)

    if iso_faces:
        mel.eval("ToggleUVIsolateViewSelected;")


def toggle_joint_locator_visibility(locator=False):
    active_panel = cmds.getPanel(withFocus=True)
    current_visibility = cmds.modelEditor(active_panel, q=True, joints=True)
    new_visibility = not current_visibility
    cmds.modelEditor(active_panel, e=True, joints=new_visibility)
    cmds.modelEditor(active_panel, e=True, jointXray=1)
    if locator:
        cmds.modelEditor(active_panel, e=True, locators=new_visibility)


def toggle_imageplane_visivility():
    active_panel = cmds.getPanel(withFocus=True)
    current_visibility = cmds.modelEditor(active_panel, q=True, imagePlane=True)
    new_visibility = not current_visibility
    cmds.modelEditor(active_panel, e=True, imagePlane=new_visibility)


def isolate_with_imageplanes():
    active_panel = cmds.getPanel(withFocus=True)

    if "modelPanel" in active_panel:

        is_isolated = cmds.isolateSelect(active_panel, q=True, state=True)

        if is_isolated:
            cmds.isolateSelect(active_panel, state=0)

        else:
            current_selection = cmds.ls(selection=True, flatten=True)
            imageplanes = cmds.ls(type="imagePlane")
            cmds.select(imageplanes, add=True)
            cmds.isolateSelect(active_panel, addSelected=True)
            cmds.editor(active_panel, e=True, lockMainConnection=True, mainListConnection="activeList")
            cmds.isolateSelect(active_panel, state=1)

            cmds.select(current_selection)

    elif "polyTexturePlacementPanel" in active_panel:
        mel.eval("textureEditorToggleIsolateSelect()")

    else:
        raise


def set_radius_auto(joints=[]):
    radius_ratio = 0.2
    min_radius = 0.001

    if not joints:
        joints = pm.selected(flatten=True, type="joint")
    
        if not joints:
            raise(Exception)

    for j in joints:
        children = j.getChildren()

        if children:
            t1 = dt.Point(pm.xform(j, q=True, t=True, ws=True))
            t2 = dt.Point(pm.xform(children[0], q=True, t=True, ws=True))
            radius = (t2 - t1).length() * radius_ratio
            j.setRadius(max(radius, min_radius))

        else:
            parent = j.getParent()
            if parent and isinstance(parent, nt.Joint):
                j.setRadius(parent.getRadius())

            
def set_radius_constant(joints=[], radius=0.001):
    if not joints:
        joints = pm.selected(flatten=True, type="joint")
    
        if not joints:
            raise(Exception)

    for j in joints:
        j.setRadius(radius)


def divide_without_history(delete_history=True):
    selection = pm.selected(flatten=True)

    if selection:
        if type(selection[0]) == nt.Mesh:
            pm.polySubdivideFacet()
        if type(selection[0]) == nt.Transform and hasattr(selection[0], "getShape") and selection[0].getShape():
            pm.polySubdivideFacet()
        elif type(selection[0]) == pm.MeshFace:
            pm.polySubdivideFacet()
        elif type(selection[0]) == pm.MeshEdge:
            pm.polySubdivideEdge()
        else:
            pass

        if delete_history:
            pm.bakePartialHistory(ppt=True)


def soft_connect(edge_flow=0):
    pm.polyConnectComponents(insertWithEdgeFlow=edge_flow, adjustEdgeFlow=1)
    # TODO: ハードエッジ除去処理


def reload_all_texture():
    mel.eval("createViewport20OptionsUI;")
    mel.eval("AEReloadAllTextures;")
    mel.eval("window -e -vis 0 Viewport20OptionsWindow;")


def rename_incremental_saves():
    """インクリメンタルセーブのファイル名を変更する

    連番を取り除き [YYYYmmdd_HHMM_SS]<scene_name>.ma という形式にする
    対象は今開いているシーンのインクリメンタルセーブのみ
    """
    scene_name = re.sub(r"^.+[/\\]", "", pm.system.sceneName())
    project_dir = re.sub(r"scenes.+$", "", pm.system.sceneName())
    incremental_save_dir = project_dir + "scenes/incrementalSave/"
    target_dir = incremental_save_dir + scene_name + "/"

    files = glob.glob(target_dir + "*")

    for filename in files:
        if not re.search(r"\.\d+\.ma", filename):
            continue

        filename = re.sub(r"\\", "/", filename)
        timestamp = datetime.datetime.fromtimestamp(os.stat(filename).st_mtime).strftime("%Y%m%d_%H%M_%S")
        new_name = "[{}]{}".format(timestamp, scene_name)

        if not os.path.isfile(target_dir + new_name):
            os.rename(filename, target_dir + new_name)
            print("rename {}".format(new_name))


def replace_file_node():
    """選択中のファイルノードを既存の別のファイルノードに差し替える
    """
    selection = pm.selected()
    all_materials = pm.ls(materials=True)

    if selection and type(selection[0]) == nt.File:
        # 差し替え元となる選択されているファイルノードを取得
        current_file = selection[0]
        all_files = pm.ls(type="file")
        all_files.remove(current_file.name())

        # 差し替え先となる任意のファイルノードをユーザーに選択させる
        i = ui.ListDialog.create(items=all_files)

        if i is not None:
            replace_file = all_files[i]

        else:
            return

        # 差し替え元ファイルが接続されている他ノードの入力プラグ
        dst_plugs = pm.listConnections(current_file, destination=True, source=False, plugs=True)

        for dst_plug in dst_plugs:
            if dst_plug.node() in all_materials:
                # 差し替え元ファイルの全ての出力プラグを差し替える
                current_src_plugs = pm.listConnections(dst_plugs, destination=False, source=True, plugs=True)

                for current_src_plug in current_src_plugs:
                    # 差し替え先ファイルの出力プラグ決定
                    new_src_plug = pm.Attribute(replace_file.name() + "." + current_src_plug.attrName())

                    # プラグの再接続
                    dst_plug.disconnect()
                    new_src_plug.connect(dst_plug)


def align_horizontally(each_polyline=True, axis="y"):
    """選択中のエッジを特定の軸方向に潰す｡

    選択コンポーネントすべてをひとまとまりで潰す場合は each_polyline に False を渡す｡連続エッジごとにそれぞれ処理する場合は True を渡す｡

    Args:
        each_polyline (bool, optional): 連続するエッジごとに処理を行う場合は True. Defaults to True.
        axis (str, optional): 潰す軸を指定する｡ "x", "y", "z" のいずれか. Defaults to "y".
    """

    def flatten_edges(targets, axis):
        scale_vector = (1, 1, 1)

        if axis == "x":
            scale_vector = (0, 1, 1)
        elif axis == "y":
            scale_vector = (1, 0, 1)
        elif axis == "z":
            scale_vector = (1, 1, 0)
        else:
            raise("axis must be set to x, y, or z")

        vts = pm.filterExpand(pm.polyListComponentConversion(targets, tv=True), sm=31)
        p = sum([pm.PyNode(x).getPosition(space="world") for x in vts]) / len(vts)

        for i in range(10):
            pm.scale(targets, scale_vector, r=True, xc="edge", p=p)

        pm.scale(targets, scale_vector, r=True, p=p)

    selection = pm.selected(flatten=True)

    if selection:
        if each_polyline:
            # 連続するエッジごとに処理する
            polylines = nu.get_all_polylines(selection)

            for edges in polylines:
                flatten_edges(edges, axis=axis)

        else:
            # 選択コンポーネントすべてで処理する
            flatten_edges(selection, axis=axis)


def rename_dialog():
    selections = pm.selected()

    if selections:
        current_name = re.sub(r"^.*\|", "", selections[0].name())

        ret = pm.promptDialog(
            title="Rename Object",
            message="Enter Name:",
            tx=current_name,
            button=["OK", "Cancel"],
            defaultButton="OK",
            cancelButton="Cancel",
            dismissString="Cancel"
            )

        if ret == "OK":
            new_name = pm.promptDialog(q=True, text=True)

            for obj in selections:
                if hasattr(obj, "fullPathName"):
                    pm.rename(obj.fullPathName(), new_name)
                else:
                    pm.rename(obj.name(), new_name)
