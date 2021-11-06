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


# nnutilへ
def get_position(comp, space):
    # TODO: ひととおり型毎の分岐書く
    if isinstance(comp, pm.MeshVertex):
        return comp.getPosition(space=space)
    else:
        return nu.to_vtx(comp)[0].getPosition(space=space)


def get_center_point(targets):

    if not targets:
        raise(Exception())
    
    points = [x.getPosition(space="object") for x in nu.to_vtx(targets)]

    min_x = points[0].x
    min_y = points[0].y
    min_z = points[0].z
    max_x = points[0].x
    max_y = points[0].y
    max_z = points[0].z

    for p in points:
        
        if p.x < min_x:
            min_x = p.x

        if p.x > max_x:
            max_x = p.x

        if p.y < min_y:
            min_y = p.y

        if p.y > max_y:
            max_y = p.y

        if p.z < min_z:
            min_z = p.z

        if p.z > max_z:
            max_z = p.z

    return dt.Point((max_x+min_x)/2, (max_y+min_y)/2, (max_z+min_z)/2)

# nnutilへ


OM_ADD = "add"
OM_MUL = "mul"
OM_OVERWRITE = "overwrite"
OS_WORLD = "world"
OS_LOCAL = "local"
center_locator_name = "altunt_center_loc"
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
    # 引数が無効なら終了
    if not targets:
        print("no targets")
        return

    # 編集対象コンポーネントの決定とソフトエッジの保存
    target_components = decide_targets(targets)
    softedges = [e for e in nu.to_edge(target_components) if not nu.is_hardedge(e)]

    # 球状化処理

    # 中心の設定
    # center 未指定ならバウンディングボックスの中心を使用する
    center_point = None

    if center:
        center_point = dt.Point(center)

    else:
        center_point = get_center_point(targets)

    for comp in target_components:
        # 法線と球状ベクトル取得
        current_normal = sum(nu.coords_to_vector(pm.polyNormalPerVertex(comp, q=True, xyz=True)))
        current_normal.normalize()
        radial_vector = dt.Vector(get_position(comp, space="object") - center_point)
        # 比率で合成して上書き
        new_normal = current_normal * (1.0-ratio) + radial_vector * ratio
        # 法線上書き
        pm.polyNormalPerVertex(comp, xyz=tuple(new_normal))

    # ソフトエッジの復帰
    if softedges:
        pm.polySoftEdge(softedges, a=180, ch=1)


def create_center_locator():
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
    # TODO: 実装
    raise(Exception("not impl"))
    pass


def reverse_normal(targets=None):
    offset_normal(targets, mode=OM_MUL, values=(-1, -1, -1), add_one=False)


def reset_nromal(targets=None):
    # 引数が無効なら選択オブジェクト取得
    targets = pm.selected(flatten=True) if not targets else targets

    if not targets:
        print("no targets")
        return

    # 編集対象コンポーネントの決定とソフトエッジの保存
    target_components = decide_targets(targets)
    softedges = [e for e in nu.to_edge(target_components) if not nu.is_hardedge(e)]

    # スムース処理
    pm.polyNormalPerVertex(target_components, ufn=True)

    # ソフトエッジの復帰
    if softedges:
        pm.polySoftEdge(softedges, a=180, ch=1)

    pm.select(targets)


def smooth_normal(targets=None, current_ratio=default_current_ratio, smooth_ratio=default_smooth_ratio, planer_ratio=default_planer_ratio, outer=True, keep_vtxface=False):
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


def fix_normals(shape, protect_split_normal=False):    
    if protect_split_normal:
        vtx = shape.verts[0]
        softedges = [e for e in vtx.connectedEdges() if not nu.is_hardedge(e)]

        vtxfaces = nu.to_vtxface(vtx)
        vf_normals = nu.coords_to_vector(pm.polyNormalPerVertex(vtxfaces, q=True, xyz=True))

        pm.polyAverageNormal(vtx, prenormalize=1, allowZeroNormal=1, postnormalize=0, distance=0)

        pm.polyNormalPerVertex(vtxfaces, e=True, xyz=vf_normals)

        if softedges:
            pm.polySoftEdge(softedges, a=180, ch=1)
    else:
        pm.polyAverageNormal(shape, prenormalize=1, allowZeroNormal=1, postnormalize=0, distance=0)

    # ノンデフォーマーヒストリー削除
    pm.bakePartialHistory(shape, ppt=True)


def cleanup_normal(targets=None, force_locking=True):
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

    # ノンデフォーマーヒストリー削除
    # skincluster が接続されている場合はヒストリ削除前に fix_normals する必要があるのでこのタイミングでは削除しない
    skined = any([isinstance(x, nt.SkinCluster) for x in shape.inputs()])
    if not skined:
        pm.bakePartialHistory(obj, ppt=True)

    fix_normals(shape)

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
    def onOffsetXn05(self, *args):
        mode = self.get_offset_mode()
        x = -0.5
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(x, None, None), space=space)

    def onOffsetXn01(self, *args):
        mode = self.get_offset_mode()
        x = -0.1
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(x, None, None), space=space)

    def onOffsetXp01(self, *args):
        mode = self.get_offset_mode()
        x = 0.1
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(x, None, None), space=space)

    def onOffsetXp05(self, *args):
        mode = self.get_offset_mode()
        x = 0.5
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(x, None, None), space=space)

    def onOffsetYn05(self, *args):
        mode = self.get_offset_mode()
        y = -0.5
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, y, None), space=space)

    def onOffsetYn01(self, *args):
        mode = self.get_offset_mode()
        y = -0.1
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, y, None), space=space)

    def onOffsetYp01(self, *args):
        mode = self.get_offset_mode()
        y = 0.1
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, y, None), space=space)

    def onOffsetYp05(self, *args):
        mode = self.get_offset_mode()
        y = 0.5
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, y, None), space=space)

    def onOffsetZn05(self, *args):
        mode = self.get_offset_mode()
        z = -0.5
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, None, z), space=space)

    def onOffsetZn01(self, *args):
        mode = self.get_offset_mode()
        z = -0.1
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, None, z), space=space)

    def onOffsetZp01(self, *args):
        mode = self.get_offset_mode()
        z = 0.1
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, None, z), space=space)

    def onOffsetZp05(self, *args):
        mode = self.get_offset_mode()
        z = 0.5
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, None, z), space=space)

    def onResetOffsetValue(self, *args):
        ui.set_value(self.editbox_offset_x, value=0)
        ui.set_value(self.editbox_offset_y, value=0)
        ui.set_value(self.editbox_offset_z, value=0)

        ui.set_value(self.slider_offset_x, value=0)
        ui.set_value(self.slider_offset_y, value=0)
        ui.set_value(self.slider_offset_z, value=0)

    def onApplyOffsetX(self, *args):
        mode = self.get_offset_mode()
        x, y, z = self.get_offset_values()
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(x, None, None), space=space)

    def onApplyOffsetY(self, *args):
        mode = self.get_offset_mode()
        x, y, z = self.get_offset_values()
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, y, None), space=space)

    def onApplyOffsetZ(self, *args):
        mode = self.get_offset_mode()
        x, y, z = self.get_offset_values()
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(None, None, z), space=space)

    def onApplyOffset(self, *args):
        mode = self.get_offset_mode()
        x, y, z = self.get_offset_values()
        space = self.get_offset_space()
        offset_normal(mode=mode, values=(x, y, z), space=space)

    def onSpherize010(self, *args):
        ratio = 0.1
        center_position = get_center_position()
        spherize_normal(center=center_position, ratio=ratio)

    def onSpherize025(self, *args):
        ratio = 0.25
        center_position = get_center_position()
        spherize_normal(center=center_position, ratio=ratio)

    def onSpherize050(self, *args):
        ratio = 0.5
        center_position = get_center_position()
        spherize_normal(center=center_position, ratio=ratio)

    def onSpherize075(self, *args):
        ratio = 0.75
        center_position = get_center_position()
        spherize_normal(center=center_position, ratio=ratio)

    def onCreateCenter(self, *args):
        create_center_locator()

    def onApplySpherize(self, *args):
        ratio = ui.get_value(self.editbox_spherize_ratio)
        center_position = get_center_position()
        spherize_normal(center=center_position, ratio=ratio)

    def onNormalize(self, *args):
        normalize_normal()

    def onReverse(self, *args):
        reverse_normal()

    def onResetNormal(self, *args):
        reset_nromal()

    def onSmooth(self, *args):
        current_ratio = ui.get_value(self.slider_current_ratio)
        smooth_ratio = ui.get_value(self.slider_smooth_ratio)
        planer_ratio = ui.get_value(self.slider_planer_ratio)
        smooth_normal(current_ratio=current_ratio, smooth_ratio=smooth_ratio, planer_ratio=planer_ratio)

    def onCleanup(self, *args):
        cleanup_normal()

    def onApplyTweak(self, *args):
        apply_tweak()

    # スライダー･エディットボックス
    def onChangeEditboxOffsetX(self, *args):
        v = ui.get_value(self.editbox_offset_x)
        ui.set_value(self.slider_offset_x, value=v)

    def onChangeEditboxOffsetY(self, *args):
        v = ui.get_value(self.editbox_offset_y)
        ui.set_value(self.slider_offset_y, value=v)

    def onChangeEditboxOffsetZ(self, *args):
        v = ui.get_value(self.editbox_offset_z)
        ui.set_value(self.slider_offset_z, value=v)

    def onUpdateSliderOffsetX(self, *args):
        v = ui.get_value(self.slider_offset_x)

        if ui.is_shift():
            v = round(v, 1)

        ui.set_value(self.slider_offset_x, value=v)
        ui.set_value(self.editbox_offset_x, value=v)

    def onUpdateSliderOffsetY(self, *args):
        v = ui.get_value(self.slider_offset_y)

        if ui.is_shift():
            v = round(v, 1)

        ui.set_value(self.slider_offset_y, value=v)
        ui.set_value(self.editbox_offset_y, value=v)

    def onUpdateSliderOffsetZ(self, *args):
        v = ui.get_value(self.slider_offset_z)

        if ui.is_shift():
            v = round(v, 1)

        ui.set_value(self.slider_offset_z, value=v)
        ui.set_value(self.editbox_offset_z, value=v)

    def onChangeSliderOffsetX(self, *args):
        pass

    def onChangeSliderOffsetY(self, *args):
        pass

    def onChangeSliderOffsetZ(self, *args):
        pass

    def onChangeEditboxSpherizeRatio(self, *args):
        v = ui.get_value(self.editbox_spherize_ratio)
        ui.set_value(self.slider_spherize_ratio, value=v)

    def onUpdateSliderSpherizeRatio(self, *args):
        v = ui.get_value(self.slider_spherize_ratio)

        if ui.is_shift():
            v = round(v, 1)
            
        ui.set_value(self.slider_spherize_ratio, value=v)
        ui.set_value(self.editbox_spherize_ratio, value=v)

    def onChangeSliderSpherizeRatio(self, *args):
        pass
    
    def onChangeSmoothRatioC(self, *args):
        v = ui.get_value(self.slider_current_ratio)
        ui.set_value(self.text_smooth_ratioC, value=str(round(v, 3)))

    def onChangeSmoothRatioS(self, *args):
        v = ui.get_value(self.slider_smooth_ratio)
        ui.set_value(self.text_smooth_ratioS, value=str(round(v, 3)))

    def onChangeSmoothRatioP(self, *args):
        v = ui.get_value(self.slider_planer_ratio)
        ui.set_value(self.text_smooth_ratioP, value=str(round(v, 3)))


def showNNToolWindow():
    NN_ToolWindow().create()


def main():
    showNNToolWindow()


if __name__ == "__main__":
    main()
