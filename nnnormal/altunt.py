# coding:utf-8
""" Maya版 UserNormalTranslator
https://github.com/Gotetz/UserNormalTranslator
https://gotetz.github.io/UserNormalTranslator/htdocs/userNormalTranslator_guide_jp.htm
"""

import re
import maya.cmds as cmds
import pymel.core as pm
import pymel.core.nodetypes as nt
import pymel.core.datatypes as dt

import nnutil.core as nu
import nnutil.display as nd
import nnutil.ui as ui
import nnutil.decorator as deco

from . import normal_cache


# offset_normal で使用するオフセットモード
OM_ADD = "add"
OM_MUL = "mul"
OM_OVERWRITE = "overwrite"
OS_WORLD = "world"
OS_LOCAL = "local"

# spherize で使用する中心指定ロケーターのオブジェクト名
center_locator_name = "altunt_center_loc"

# smooth_normal で使用する法線の合成比率
default_current_ratio = 0.5
default_smooth_ratio = 0.1
default_planer_ratio = 0.1


def decide_targets(targets):
    """ 指定した･オブジェクトが選択されていた場合に実際に法線編集を行うコンポーネントを決定する

    Args:
        targets ([type]): [description]

    Returns:
        MeshVertex or MeshVertexFace: [description]
    """
    target_components = []

    # オブジェクトの型による分岐
    if isinstance(targets[0], nt.Transform) and isinstance(targets[0].getShape(), nt.Mesh):
        # オブジェクトの場合は全頂点フェースをターゲットにする
        target_components = nu.to_vtxface(targets)

    elif isinstance(targets[0], pm.MeshFace):
        # フェースの場合は基本はフェース内全頂点をターゲットとし､ハードエッジにより外側を除外する
        target_components = nu.to_vtxface(targets)
        border_vertices = nu.to_border_vertices(targets)

        # ハードエッジにより分断されている頂点フェースはターゲットに含めない
        for v in border_vertices:
            if not [e for e in nu.to_edge(v) if nu.is_hardedge(e)]:
                target_components.append(v)

            else:
                vtxfaces = nu.list_intersection(nu.to_vtxface(v), target_components)
                additions = [cvf for vf in vtxfaces for cvf in nu.get_connected_vtx_faces(vf)]
                target_components.extend(additions)

    elif isinstance(targets[0], pm.MeshEdge):
        # エッジの場合は頂点変換
        target_components = nu.to_vtx(targets)

    elif isinstance(targets[0], pm.MeshVertex):
        # 頂点の場合は基本的にはそのまま
        # ハードエッジ上の頂点のみ､それぞれの頂点フェースをターゲットにする
        for v in targets:
            if any((nu.is_hardedge(e) for e in v.connectedEdges())):
                target_components.extend(nu.to_vtxface(v))

            else:
                target_components.append(v)

    elif isinstance(targets[0], pm.MeshVertexFace):
        # 頂点フェースの場合はそのまま
        target_components = targets

    else:
        print(str(type(targets[0])) + "is not supported.")
        return []

    return nu.uniq(target_components)


def decide_source(target):
    # TODO:
    pass


def sort_components_by_object(components):
    """ コンポーネントを所属オブジェクト毎にまとめて辞書で返す

    Args:
        components (list[MeshVertex or MeshEdge or MeshFace or MeshVertexFace]): 振り分けるコンポーネントのリスト

    Returns:
        dict[Mesh, list[MeshVertex or MeshEdge or MeshFace or MeshVertexFace]]: 所属オブエジェクトをキーとした辞書
    """
    # TODO:
    pass


def offset_normal(targets=None, mode=OM_ADD, values=(0, 0, 0), add_one=True, space=OS_LOCAL):
    """法線の各成分に対して指定した値を加算･乗算･上書きする

    Args:
        targets (list[Transform or Mesh*Type], optional): 編集対象の法線を持つコンポーネントやオブジェクト. Defaults to None.
        mode (str, optional): 編集モード. Defaults to OM_ADD.
        values (tuple(float or None), optional): 編集に使われる値｡None を指定するとその成分は現在の値が維持される｡ Defaults to (0, 0, 0).
        add_one (bool, optinal): 乗算モードで values の値を +1.0 する｡乗算モード以外では無視される｡Defaults to True.
        space (str, optional): 計算する際の座標系. Defaults to OS_LOCAL.

    Returns:
        None
    """
    # 引数が無効なら選択オブジェクト取得
    targets = pm.selected(flatten=True) if not targets else targets

    if not targets:
        print("no targets")
        return

    # オフセットに使われるベクトル
    offset_vector = dt.Vector([x if x else 0.0 for x in values])

    # 乗算モードで add_one が有効なら values = (0,0,0) を 1.0 倍とする
    if mode == OM_MUL and add_one:
        offset_vector += (1.0, 1.0, 1.0)

    # 編集対象コンポーネントの決定とソフトエッジの保存
    target_components = decide_targets(targets)
    softedges = [e for e in nu.to_edge(target_components) if not nu.is_hardedge(e)]

    # オブジェクトと変換行列の取得
    # TODO: 重くなければ targets 個々で取得する
    object = nu.get_object(targets[0])
    object = object.getParent() if isinstance(object, nt.Mesh) else object
    world_matrix = object.getMatrix(worldSpace=True)

    # オフセット処理
    # 複数コンポーネントで polyNormalPerVertex 呼ぶとクラッシュすることがあるのでループにする
    for comp in target_components:
        current_normal = sum(nu.coords_to_vector(pm.polyNormalPerVertex(comp, q=True, xyz=True)))
        current_normal.normalize()

        # 最終的に設定される法線
        new_normal = dt.Vector(current_normal)

        if space == OS_LOCAL:
            if mode == OM_ADD:
                if values[0]:
                    new_normal.x += offset_vector.x
                if values[1]:
                    new_normal.y += offset_vector.y
                if values[2]:
                    new_normal.z += offset_vector.z

            elif mode == OM_MUL:
                if values[0]:
                    new_normal.x *= offset_vector.x
                if values[1]:
                    new_normal.y *= offset_vector.y
                if values[2]:
                    new_normal.z *= offset_vector.z

            elif mode == OM_OVERWRITE:
                if values[0]:
                    new_normal.x = offset_vector.x
                if values[1]:
                    new_normal.y = offset_vector.y
                if values[2]:
                    new_normal.z = offset_vector.z

            else:
                raise(Exception("Unknown mode"))

        elif space == OS_WORLD:
            # TODO: 実装する
            world_offset_vector = (world_matrix * list(offset_vector)).transpose()[0][0:3]
            offset_vector = dt.Vector(world_offset_vector)
            raise(Exception("not impl"))

        pm.polyNormalPerVertex(comp, xyz=tuple(new_normal))

    # ソフトエッジの復帰
    if softedges:
        pm.polySoftEdge(softedges, a=180, ch=1)

    pm.select(targets)


def spherize_normal(targets=None, center=None, ratio=1.0):
    """法線を球状化する

    Args:
        targets (list[Transform or MeshVertex or MeshEdge or MeshFace or MeshVertexFace], optional): [description]. Defaults to None.
        center ([type], optional): [description]. Defaults to None.
        ratio (float, optional): [description]. Defaults to 1.0.
    """
    # 引数が無効なら選択オブジェクト取得
    targets = pm.selected(flatten=True) if not targets else targets

    if not targets:
        print("no targets")
        return

    if isinstance(targets[0], nt.Transform):
        for obj in targets:
            _spherize_normal(targets=[obj], center=center, ratio=ratio)

    else:
        _spherize_normal(targets=targets, center=center, ratio=ratio)

    pm.select(targets)


def _spherize_normal(targets, center=None, ratio=1.0):
    """法線を球状化する。targets はすべて同じメッシュに所属するコンポーネント、もしくはオブジェクトとして処理する。

    Args:
        targets (Transform or MeshVertex or MeshEdge or MeshFace or MeshVertexFace): 球状化対象のコンポーネント
        center (list[float, float, float], optional): 球状化の中心となるローカル座標. Defaults to None.
        ratio (float, optional): 現在の法線に球状化した法線を合成する割合. Defaults to 1.0.
    """
    # 引数が無効なら終了
    if not targets:
        print("no targets")
        return

    # 編集対象コンポーネントの決定
    target_components = decide_targets(targets)

    # 球状化処理

    # 中心の設定
    # center 未指定ならバウンディングボックスの中心を使用する
    center_point = None

    if center:
        center_point = dt.Point(center)

    else:
        center_point = nu.get_center_point(targets)

    # 法線のキャッシュ
    shape = target_components[0].node()
    nc = normal_cache.NormalCache(shape)
    points = shape.getPoints(space="object")

    current_normals = nc.get_vertexface_normals(target_components)
    new_normals = [None] * len(current_normals)

    for i, comp in enumerate(target_components):
        # 法線と球状ベクトル取得
        current_normal = current_normals[i]

        # 頂点フェースの所属する頂点のインデックス
        vi = comp.indices()[0][0]
        
        radial_vector = points[vi] - center_point
        radial_vector.normalize()
        
        # 比率で合成
        new_normals[i] = current_normal * (1.0-ratio) + radial_vector * ratio
    
    # シェイプの法線を上書き
    nc.set_vertexface_normals(target_components, new_normals)
    nc.update_normals()


def create_center_locator():
    """球状化の中心として使うロケーターを作成する"""
    # TODO: 実装
    raise(Exception("not impl"))
    pass


def get_center_position():
    """ 指定のロケーターのワールド座標を取得する｡存在しない場合は None を返す

    Returns:
        Point or None: ロケーターが存在すれば座標を返し､存在しない場合は None を返す
    """
    # TODO: 実装

    return None


def normalize_normal(targets=None):
    """指定したターゲットの法線を正規化する

    Args:
        targets ([Transform or MeshVertex or MeshEdge or MeshFace or MeshVertexFace], optional): 正規化する対象のオブジェクトかコンポーネント。省略時は選択オブジェクトを使用する. Defaults to None.
    """
    # TODO: 実装
    raise(Exception("not impl"))
    pass


def reverse_normal(targets=None):
    """指定したターゲットの法線を反転する

    Args:
        targets ([Transform or MeshVertex or MeshEdge or MeshFace or MeshVertexFace], optional): 反転する対象のオブジェクトかコンポーネント。省略時は選択オブジェクトを使用する. Defaults to None.
    """   
    offset_normal(targets, mode=OM_MUL, values=(-1, -1, -1), add_one=False)


def reset_nromal(targets=None):
    """指定したターゲットの法線をリセットする。

    Args:
        targets ([Transform or MeshVertex or MeshEdge or MeshFace or MeshVertexFace], optional): 反転する対象のオブジェクトかコンポーネント。省略時は選択オブジェクトを使用する. Defaults to None.
    """
    # 引数が無効なら選択オブジェクト取得
    targets = pm.selected(flatten=True) if not targets else targets

    if not targets:
        print("no targets")
        return

    # 編集対象コンポーネントの決定とソフトエッジの保存
    target_components = decide_targets(targets)
    softedges = [e for e in nu.to_edge(target_components) if not nu.is_hardedge(e)]

    # アンロック処理
    pm.polyNormalPerVertex(target_components, ufn=True)

    # ソフトエッジの復帰
    if softedges:
        pm.polySoftEdge(softedges, a=180, ch=1)

    pm.select(targets)


def smooth_normal(targets=None, current_ratio=default_current_ratio, smooth_ratio=default_smooth_ratio, planer_ratio=default_planer_ratio, outer=True, keep_vtxface=False):
    """指定したターゲットの法線をスムースする。

    Args:
        targets ([Transform or MeshVertex or MeshEdge or MeshFace or MeshVertexFace], optional): 法線をスムースするオブジェクトかコンポーネント. Defaults to None.
        current_ratio (float, optional): 現在の法線を合成する比率. Defaults to default_current_ratio.
        smooth_ratio (float, optional): スムースされた法線を合成する比率. Defaults to default_smooth_ratio.
        planer_ratio (float, optional): 平均法線を合成する比率. Defaults to default_planer_ratio.
        outer (bool, optional): ターゲットの隣接コンポーネントを法線計算に含めるかどうか. Defaults to True.
        keep_vtxface (bool, optional): スムースする際に頂点フェースの法線の分離を維持するかどうか. Defaults to False.
    """
    # 引数が無効なら選択オブジェクト取得
    targets = pm.selected(flatten=True) if not targets else targets

    if not targets:
        print("no targets")
        return

    # 編集対象コンポーネントの決定とソフトエッジの保存
    if keep_vtxface:
        target_components = decide_targets(targets)
    else:
        target_components = nu.to_vtx(targets)

    softedges = [e for e in nu.to_edge(target_components) if not nu.is_hardedge(e)]

    # スムース処理
    # 全体の平均法線
    coords = pm.polyNormalPerVertex(target_components, q=True, xyz=True)
    normals = nu.coords_to_vector(coords)
    average_normal = sum(normals)
    average_normal.normalize()

    inner_vertices = nu.to_vtx(targets)

    for target in target_components:
        # 隣接コンポーネントの法線取得
        if outer:
            connected_vertices = nu.get_connected_vertices(nu.to_vtx(target)[0])
        else:
            connected_vertices = nu.list_intersection(nu.get_connected_vertices(nu.to_vtx(target)[0]), inner_vertices)

        if connected_vertices:
            coords = pm.polyNormalPerVertex(connected_vertices, q=True, xyz=True)
            connected_normals = nu.coords_to_vector(coords)
            connected_normal = sum(connected_normals)
            connected_normal.normalize()

        else:
            connected_normal = None

        # 現在の法線の取得
        current_normal = sum(nu.coords_to_vector(pm.polyNormalPerVertex(target, q=True, xyz=True)))
        current_normal.normalize()

        # 現在の法線・平均法線・隣接法線を比率で合成
        if connected_normal:
            new_normal = current_normal * current_ratio + (average_normal * planer_ratio + connected_normal * smooth_ratio) * (1.0-current_ratio)
        else:
            new_normal = current_normal * current_ratio + (average_normal * planer_ratio) * (1.0-current_ratio)

        pm.polyNormalPerVertex(target, xyz=tuple(new_normal))

    # ソフトエッジの復帰
    if softedges:
        pm.polySoftEdge(softedges, a=180, ch=1)

    pm.select(targets)


def fix_normals(shape, normals=None):
    """法線が先祖返りするMayaのふるまい対策。現在の値で法線を固定する

    バインド済みメッシュは Orig の法線の上書き、未バインドのメッシュはメッシュ内の頂点の法線を Average すると
    全体が固定されるのを利用。
    setNormals 後に getNormals するとハードエッジ上の法線の値が変な値を返すので事前に取得してある法線リストがある場合は
    normals に渡しておく。normals 未設定の場合は内部で取得するが方向がおかしくなる場合あり。

    Args:
        shape (Mesh): 対象メッシュ
        normals (list[FloatVector]): 処理後に上書きする getNormals で取得した法線のリスト
    """
    skined = any([isinstance(x, nt.SkinCluster) for x in shape.inputs()])

    # 現在の法線を保持
    if not normals:
        normals = shape.getNormals()

    # 1 回だと固定されない場合があるので同じ処理を複数回行う
    # TODO: 原因特定できたら修正 or 詳細明記する
    for i in range(2):
        if skined:
            orig_shape = [x for x in pm.listRelatives(shape.getParent(), shapes=True, noIntermediate=False) if x.intermediateObject.get()][0]
            orig_shape.setNormals(normals)
        
        else:
            vtx = shape.verts[0]
            pm.polyAverageNormal(vtx, prenormalize=1, allowZeroNormal=1, postnormalize=0, distance=0)

            shape.setNormals(normals)

        # ノンデフォーマーヒストリー削除
        pm.bakePartialHistory(shape, ppt=True)


def cleanup_normal(targets=None, force_locking=True):
    """TransferAttributes により設定されている法線をコンポーネント法線として設定し直し、TransferAttributes を削除する

    Args:
        targets (Transform or MeshVertex or MeshEdge or MeshFace or MeshVertexFace, optional): クリーンナップ対象のオブジェクトかコンポーネント. Defaults to None.
        force_locking (bool, optional): もともとアンロック状態だった法線をロックした状態にするかどうか。False はアンロックの復帰処理を行う分遅い. Defaults to True.
    """
    # 引数が無効なら選択オブジェクト取得
    targets = pm.selected(flatten=True) if not targets else targets

    if not targets:
        print("no targets")
        return

    obj = nu.get_object(targets[0], transform=True)
    shape = obj.getShape()

    # 現在の法線の取得
    normals = shape.getNormals()

    # 各頂点フェースのロック状態の取得
    if not force_locking:
        vtxfaces = nu.to_vtxface(targets)
        locked = pm.polyNormalPerVertex(vtxfaces, q=True, fn=True)
        unlocked_vtxfaces = nu.list_diff(vtxfaces, locked)

    # ノンデフォーマーヒストリー削除
    pm.bakePartialHistory(obj, ppt=True)

    # TransferAttribute があれば削除
    for i in range(10):
        transfer_attributes_nodes = [x for x in obj.getShape().inputs() if isinstance(x, nt.TransferAttributes)]
        if transfer_attributes_nodes:
            print("delete: ", transfer_attributes_nodes)
            pm.delete(transfer_attributes_nodes)
        else:
            break

    # 法線の復元
    shape.setNormals(normals)

    # 各頂点フェースのロック状態の復元
    if not force_locking and unlocked_vtxfaces:
        pm.polyNormalPerVertex(unlocked_vtxfaces, e=True, ufn=True)

    # 法線の固定 (先祖返り防止処理)
    fix_normals(shape, normals=normals)

    pm.select(targets)


def apply_tweak(targets=None):
    """ Tweak ノードの内容をシェイプのコンポーネント座標に適用する

    targets がコンポーネントだった場合はそのコンポーネントを持つオブジェクト全体に適用される。

    Args:
        targets (Mesh or Transform): メッシュ・トランスフォーム・コンポーネント
    """
    targets = pm.selected(flatten=True) if not targets else targets

    if not targets:
        print("no targets")
        return

    objects = nu.uniq([nu.get_object(x) for x in targets])

    for obj in objects:
        nu.apply_tweak(obj)


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
        self.window = 'AltUNT'
        self.title = 'AltUNT'
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

        # オフセット
        ui.row_layout()
        ui.text(label="Offset")
        ui.end_layout()

        ui.row_layout()
        ui.text(label="Mode")
        ui.radio_collection()
        self.radio_add = ui.radio_button(label="Add", select=True)
        self.radio_mul = ui.radio_button(label="Mul")
        self.radio_overwrite = ui.radio_button(label="Overwrite", width=ui.width3)
        ui.end_layout()

        ui.row_layout()
        ui.button(label="X", c=self.onApplyOffsetX)
        self.editbox_offset_x = ui.eb_float(min=-1, max=1, cc=self.onChangeEditboxOffsetX)
        self.slider_offset_x = ui.float_slider(min=-1, max=1, dc=self.onUpdateSliderOffsetX, cc=self.onChangeSliderOffsetX)
        ui.button(label="-0.5", width=ui.button_width1_5, c=self.onOffsetXn05)
        ui.button(label="-0.1", width=ui.button_width1_5, c=self.onOffsetXn01)
        ui.button(label="+0.1", width=ui.button_width1_5, c=self.onOffsetXp01)
        ui.button(label="+0.5", width=ui.button_width1_5, c=self.onOffsetXp05)
        ui.end_layout()

        ui.row_layout()
        ui.button(label="Y", c=self.onApplyOffsetY)
        self.editbox_offset_y = ui.eb_float(min=-1, max=1, cc=self.onChangeEditboxOffsetY)
        self.slider_offset_y = ui.float_slider(min=-1, max=1, dc=self.onUpdateSliderOffsetY, cc=self.onChangeSliderOffsetY)
        ui.button(label="-0.5", width=ui.button_width1_5, c=self.onOffsetYn05)
        ui.button(label="-0.1", width=ui.button_width1_5, c=self.onOffsetYn01)
        ui.button(label="+0.1", width=ui.button_width1_5, c=self.onOffsetYp01)
        ui.button(label="+0.5", width=ui.button_width1_5, c=self.onOffsetYp05)
        ui.end_layout()

        ui.row_layout()
        ui.button(label="Z", c=self.onApplyOffsetZ)
        self.editbox_offset_z = ui.eb_float(min=-1, max=1, cc=self.onChangeEditboxOffsetZ)
        self.slider_offset_z = ui.float_slider(min=-1, max=1, dc=self.onUpdateSliderOffsetZ, cc=self.onChangeSliderOffsetZ)
        ui.button(label="-0.5", width=ui.button_width1_5, c=self.onOffsetZn05)
        ui.button(label="-0.1", width=ui.button_width1_5, c=self.onOffsetZn01)
        ui.button(label="+0.1", width=ui.button_width1_5, c=self.onOffsetZp01)
        ui.button(label="+0.5", width=ui.button_width1_5, c=self.onOffsetZp05)
        ui.end_layout()

        ui.spacer_v()

        ui.row_layout()
        ui.button(label="Reset", c=self.onResetOffsetValue)
        self.checkbox_offset_world = ui.check_box(label="WorldSpace", en=False)
        ui.spacer(width=ui.width3-1)
        ui.button(label="Apply", width=ui.width3, c=self.onApplyOffset)
        ui.end_layout()

        ui.row_layout()
        ui.separator(height=ui.height1)
        ui.end_layout()

        # 球状化
        ui.row_layout()
        ui.text(label="Spherize")
        ui.end_layout()

        ui.row_layout()
        ui.text(label="Ratio", width=ui.width1)
        self.editbox_spherize_ratio = ui.eb_float(min=0, max=1, value=1, cc=self.onChangeEditboxSpherizeRatio)
        self.slider_spherize_ratio = ui.float_slider(min=0, max=1, value=1, dc=self.onUpdateSliderSpherizeRatio, cc=self.onChangeSliderSpherizeRatio)
        ui.button(label="0.1 ", width=ui.button_width1_5, c=self.onSpherize010)
        ui.button(label="0.25", width=ui.button_width1_5, c=self.onSpherize025)
        ui.button(label="0.5 ", width=ui.button_width1_5, c=self.onSpherize050)
        ui.button(label="0.75", width=ui.button_width1_5, c=self.onSpherize075)
        ui.end_layout()

        ui.spacer_v()

        ui.row_layout()
        ui.button(label="Create Center", c=self.onCreateCenter, en=False)
        ui.spacer(width=ui.width5+2)
        ui.button(label="Apply", width=ui.width3, c=self.onApplySpherize)
        ui.end_layout()

        ui.row_layout()
        ui.separator(height=ui.height1)
        ui.end_layout()

        # その他
        ui.row_layout()
        ui.text(label="EditTool")
        ui.end_layout()

        ui.row_layout()
        ui.button(label="Normalize", width=ui.width3, c=self.onNormalize, en=False)
        ui.button(label="Reverse", width=ui.width3, c=self.onReverse)
        ui.button(label="Reset", width=ui.width3, c=self.onResetNormal)
        ui.end_layout()

        ui.row_layout()
        ui.button(label="Smooth", width=ui.width3, c=self.onSmooth)
        ui.button(label="Cleanup", width=ui.width3, c=self.onCleanup)
        ui.button(label="Apply Tweak", width=ui.width3, c=self.onApplyTweak)
        ui.end_layout()

        ui.row_layout()
        ui.text(label="current ratio")
        self.slider_current_ratio = ui.float_slider(min=0.0, max=1, value=default_current_ratio, width=ui.width6, dc=self.onChangeSmoothRatioC)
        self.text_smooth_ratioC = ui.text(label=str(default_current_ratio))
        ui.end_layout()

        ui.row_layout()
        ui.text(label="smooth ratio")
        self.slider_smooth_ratio = ui.float_slider(min=0.0, max=0.2, value=default_smooth_ratio, width=ui.width6, dc=self.onChangeSmoothRatioS)
        self.text_smooth_ratioS = ui.text(label=str(default_smooth_ratio))
        ui.end_layout()

        ui.row_layout()
        ui.text(label="planer ratio")
        self.slider_planer_ratio = ui.float_slider(min=0.0, max=0.2, value=default_planer_ratio, width=ui.width6, dc=self.onChangeSmoothRatioP)
        self.text_smooth_ratioP = ui.text(label=str(default_planer_ratio))
        ui.end_layout()

        ui.separator(height=ui.height1)

        # コピー&ペースト
        ui.row_layout()
        ui.text(label="Copy & Paste")
        ui.end_layout()

        # ui.row_layout()
        # ui.button(label="Transfer (First)", c=self.onTransferNormalFirst)
        # ui.button(label="Transfer (Last)", c=self.onTransferNormalLast)
        # ui.button(label="Transfer (Prompt)", c=self.onTransferNormalPrompt)
        # ui.end_layout()

        ui.row_layout()
        ui.button(label="Copy", c=self.onCopyNormal)
        ui.button(label="Paste", c=self.onPasteNormal)
        ui.end_layout()

        ui.end_layout()

    def get_offset_mode(self, *args):
        mode = None

        if ui.get_value(self.radio_add):
            mode = OM_ADD

        elif ui.get_value(self.radio_mul):
            mode = OM_MUL

        elif ui.get_value(self.radio_overwrite):
            mode = OM_OVERWRITE

        else:
            raise(Exception("Unknown mode"))

        return mode

    def get_offset_values(self, *args):
        ui_value_x = ui.get_value(self.editbox_offset_x)
        ui_value_y = ui.get_value(self.editbox_offset_y)
        ui_value_z = ui.get_value(self.editbox_offset_z)

        return (ui_value_x, ui_value_y, ui_value_z)

    def get_offset_space(self, *args):
        space = ""

        if ui.get_value(self.checkbox_offset_world):
            space = OS_WORLD
        else:
            space = OS_LOCAL

        return space

    # イベントハンドラ
    
    # ボタン
    @deco.undo_chunk
    def onOffsetXn05(self, *args):
        mode = self.get_offset_mode()
        x = -0.5
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(x, None, None), space=space)

    @deco.undo_chunk
    def onOffsetXn01(self, *args):
        mode = self.get_offset_mode()
        x = -0.1
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(x, None, None), space=space)

    @deco.undo_chunk
    def onOffsetXp01(self, *args):
        mode = self.get_offset_mode()
        x = 0.1
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(x, None, None), space=space)

    @deco.undo_chunk
    def onOffsetXp05(self, *args):
        mode = self.get_offset_mode()
        x = 0.5
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(x, None, None), space=space)

    @deco.undo_chunk
    def onOffsetYn05(self, *args):
        mode = self.get_offset_mode()
        y = -0.5
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, y, None), space=space)

    @deco.undo_chunk
    def onOffsetYn01(self, *args):
        mode = self.get_offset_mode()
        y = -0.1
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, y, None), space=space)

    @deco.undo_chunk
    def onOffsetYp01(self, *args):
        mode = self.get_offset_mode()
        y = 0.1
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, y, None), space=space)

    @deco.undo_chunk
    def onOffsetYp05(self, *args):
        mode = self.get_offset_mode()
        y = 0.5
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, y, None), space=space)

    @deco.undo_chunk
    def onOffsetZn05(self, *args):
        mode = self.get_offset_mode()
        z = -0.5
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, None, z), space=space)

    @deco.undo_chunk
    def onOffsetZn01(self, *args):
        mode = self.get_offset_mode()
        z = -0.1
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, None, z), space=space)

    @deco.undo_chunk
    def onOffsetZp01(self, *args):
        mode = self.get_offset_mode()
        z = 0.1
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, None, z), space=space)

    @deco.undo_chunk
    def onOffsetZp05(self, *args):
        mode = self.get_offset_mode()
        z = 0.5
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, None, z), space=space)

    @deco.undo_chunk
    def onResetOffsetValue(self, *args):
        ui.set_value(self.editbox_offset_x, value=0)
        ui.set_value(self.editbox_offset_y, value=0)
        ui.set_value(self.editbox_offset_z, value=0)

        ui.set_value(self.slider_offset_x, value=0)
        ui.set_value(self.slider_offset_y, value=0)
        ui.set_value(self.slider_offset_z, value=0)

    @deco.undo_chunk
    def onApplyOffsetX(self, *args):
        mode = self.get_offset_mode()
        x, y, z = self.get_offset_values()
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(x, None, None), space=space)

    @deco.undo_chunk
    def onApplyOffsetY(self, *args):
        mode = self.get_offset_mode()
        x, y, z = self.get_offset_values()
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, y, None), space=space)

    @deco.undo_chunk
    def onApplyOffsetZ(self, *args):
        mode = self.get_offset_mode()
        x, y, z = self.get_offset_values()
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, None, z), space=space)

    @deco.undo_chunk
    def onApplyOffset(self, *args):
        mode = self.get_offset_mode()
        x, y, z = self.get_offset_values()
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(x, y, z), space=space)

    @deco.undo_chunk
    def onSpherize010(self, *args):
        ratio = 0.1
        center_position = get_center_position()
        spherize_normal(center=center_position, ratio=ratio)

    @deco.undo_chunk
    def onSpherize025(self, *args):
        ratio = 0.25
        center_position = get_center_position()
        spherize_normal(center=center_position, ratio=ratio)

    @deco.undo_chunk
    def onSpherize050(self, *args):
        ratio = 0.5
        center_position = get_center_position()
        spherize_normal(center=center_position, ratio=ratio)

    @deco.undo_chunk
    def onSpherize075(self, *args):
        ratio = 0.75
        center_position = get_center_position()
        spherize_normal(center=center_position, ratio=ratio)

    @deco.undo_chunk
    def onCreateCenter(self, *args):
        create_center_locator()

    @deco.undo_chunk
    def onApplySpherize(self, *args):
        ratio = ui.get_value(self.editbox_spherize_ratio)
        center_position = get_center_position()
        spherize_normal(center=center_position, ratio=ratio)

    @deco.undo_chunk
    def onNormalize(self, *args):
        normalize_normal()

    @deco.undo_chunk
    def onReverse(self, *args):
        reverse_normal()

    @deco.undo_chunk
    def onResetNormal(self, *args):
        reset_nromal()

    @deco.undo_chunk
    def onSmooth(self, *args):
        current_ratio = ui.get_value(self.slider_current_ratio)
        smooth_ratio = ui.get_value(self.slider_smooth_ratio)
        planer_ratio = ui.get_value(self.slider_planer_ratio)
        smooth_normal(current_ratio=current_ratio, smooth_ratio=smooth_ratio, planer_ratio=planer_ratio)

    @deco.undo_chunk
    def onCleanup(self, *args):
        cleanup_normal()

    @deco.undo_chunk
    def onApplyTweak(self, *args):
        apply_tweak()

    # スライダー･エディットボックス
    @deco.undo_chunk
    def onChangeEditboxOffsetX(self, *args):
        v = ui.get_value(self.editbox_offset_x)
        ui.set_value(self.slider_offset_x, value=v)

    @deco.undo_chunk
    def onChangeEditboxOffsetY(self, *args):
        v = ui.get_value(self.editbox_offset_y)
        ui.set_value(self.slider_offset_y, value=v)

    @deco.undo_chunk
    def onChangeEditboxOffsetZ(self, *args):
        v = ui.get_value(self.editbox_offset_z)
        ui.set_value(self.slider_offset_z, value=v)

    @deco.undo_chunk
    def onUpdateSliderOffsetX(self, *args):
        v = ui.get_value(self.slider_offset_x)

        if ui.is_shift():
            v = round(v, 1)

        ui.set_value(self.slider_offset_x, value=v)
        ui.set_value(self.editbox_offset_x, value=v)

    @deco.undo_chunk
    def onUpdateSliderOffsetY(self, *args):
        v = ui.get_value(self.slider_offset_y)

        if ui.is_shift():
            v = round(v, 1)

        ui.set_value(self.slider_offset_y, value=v)
        ui.set_value(self.editbox_offset_y, value=v)

    @deco.undo_chunk
    def onUpdateSliderOffsetZ(self, *args):
        v = ui.get_value(self.slider_offset_z)

        if ui.is_shift():
            v = round(v, 1)

        ui.set_value(self.slider_offset_z, value=v)
        ui.set_value(self.editbox_offset_z, value=v)

    @deco.undo_chunk
    def onChangeSliderOffsetX(self, *args):
        pass

    @deco.undo_chunk
    def onChangeSliderOffsetY(self, *args):
        pass

    @deco.undo_chunk
    def onChangeSliderOffsetZ(self, *args):
        pass

    @deco.undo_chunk
    def onChangeEditboxSpherizeRatio(self, *args):
        v = ui.get_value(self.editbox_spherize_ratio)
        ui.set_value(self.slider_spherize_ratio, value=v)

    @deco.undo_chunk
    def onUpdateSliderSpherizeRatio(self, *args):
        v = ui.get_value(self.slider_spherize_ratio)

        if ui.is_shift():
            v = round(v, 1)

        ui.set_value(self.slider_spherize_ratio, value=v)
        ui.set_value(self.editbox_spherize_ratio, value=v)

    @deco.undo_chunk
    def onChangeSliderSpherizeRatio(self, *args):
        pass

    @deco.undo_chunk
    def onChangeSmoothRatioC(self, *args):
        v = ui.get_value(self.slider_current_ratio)
        ui.set_value(self.text_smooth_ratioC, value=str(round(v, 3)))

    @deco.undo_chunk
    def onChangeSmoothRatioS(self, *args):
        v = ui.get_value(self.slider_smooth_ratio)
        ui.set_value(self.text_smooth_ratioS, value=str(round(v, 3)))

    @deco.undo_chunk
    def onChangeSmoothRatioP(self, *args):
        v = ui.get_value(self.slider_planer_ratio)
        ui.set_value(self.text_smooth_ratioP, value=str(round(v, 3)))

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
