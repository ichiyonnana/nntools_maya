"""フリルの先端形状を定義するカーブを作成するツール."""
import json
import math

import maya.cmds as cmds
import maya.api.OpenMaya as om

import nnutil.ui as ui


WINDOW_NAME = "frillCurveWindow"

# 最終カーブの分割数。ベースカーブの分割数とは無関係に等間隔で割る
SAMPLE_COUNT = 200

DEFAULT_AMPLITUDE = 1.0

DEFAULT_TOTAL_OFFSET = 0.0

DEFAULT_TOTAL_WAVELENGTH_SCALE = 0.0

TOTAL_WAVELENGTH_SCALE_MIN = -10.0

TOTAL_WAVELENGTH_SCALE_MAX = 10.0

DEFAULT_FACTOR = 0.4

DEFAULT_WAVELENGTHS = (5.0, 2.5, 1.25)

DEFAULT_OFFSETS = (0.0, 0.5, 1.0)

WAVELENGTH_MIN = 0.1

WAVELENGTH_MAX = 10.0

# 全体オフセットの基準となる仮想の波長。全体オフセット 1.0 がこの波長の半周期分の弧長移動に相当する
TOTAL_OFFSET_WAVELENGTH = 5.0

# 同期状態ラベルの背景色。同期中は暗赤色、停止中はライトグレー
SYNC_ON_COLOR = (0.5, 0.1, 0.1)

SYNC_OFF_COLOR = (0.7, 0.7, 0.7)

# 最終カーブに付ける、ベースカーブのシェイプ名を保持するアトリビュート
BASE_CURVE_ATTR = "baseCurve"

# 最終カーブに付ける、UI のパラメーターを JSON 文字列で保持するアトリビュート
PARAMS_ATTR = "frillParams"

# ベースカーブに付ける、そこから作られた最終カーブ名のリストを JSON 文字列で保持するアトリビュート
FRILL_CURVES_ATTR = "frillCurves"

# 最終カーブに付ける、エイムカーブのシェイプ名を保持するアトリビュート
AIM_CURVE_ATTR = "aimCurve"

# カスタムアトリビュートを付けたノードに、その時点での自身の UUID を保持するアトリビュート。
# ノードを複製するとカスタムアトリビュートごと複製されてしまうので、これで複製を見分ける
OWNER_ATTR = "ownerUuid"

# このツールが付けるカスタムアトリビュート。OWNER_ATTR は判定に使うので最後に置く
CUSTOM_ATTRS = (BASE_CURVE_ATTR, PARAMS_ATTR, FRILL_CURVES_ATTR, AIM_CURVE_ATTR, OWNER_ATTR)

_tool = None

# 再計算が自分自身の発火で多重に走るのを防ぐフラグ
_rebuilding = False


def get_dag_path(name):
    """名前から MDagPath を得る."""
    selection = om.MSelectionList()
    selection.add(name)

    return selection.getDagPath(0)


def get_curve_shapes(node):
    """ノード以下の nurbsCurve シェイプを返す.

    シェイプ・トランスフォーム・その上位グループのいずれを渡しても拾える。
    """
    shapes = cmds.ls(node, dagObjects=True, long=True, type="nurbsCurve") or []

    return [s for s in shapes if not cmds.getAttr(s + ".intermediateObject")]


def store_owner(node):
    """カスタムアトリビュートの持ち主として、現在の UUID を記録する."""
    attr = node + "." + OWNER_ATTR
    if not cmds.objExists(attr):
        cmds.addAttr(node, longName=OWNER_ATTR, dataType="string")
    cmds.setAttr(attr, cmds.ls(node, uuid=True)[0], type="string")


def owner_matches(node):
    """記録された持ち主の UUID が現在のノードの UUID と一致するか返す.

    カスタムアトリビュートを付ける経路は必ず store_owner() を通るので、OWNER_ATTR を
    持たないノードはこのツールが一度も触っていないカーブに限られる。一致扱いにする。
    """
    attr = node + "." + OWNER_ATTR
    if not cmds.objExists(attr):

        return True

    return cmds.getAttr(attr) == cmds.ls(node, uuid=True)[0]


def owner_attr_nodes():
    """処理対象のうち OWNER_ATTR を持つノードを返す.

    選択があればその配下の DAG オブジェクト、選択が無ければシーン中の全 DAG オブジェクトが対象。
    """
    nodes = cmds.ls(selection=True, dagObjects=True, long=True) or cmds.ls(dagObjects=True, long=True) or []

    return [node for node in nodes if cmds.objExists(node + "." + OWNER_ATTR)]


def get_frill_curves(base_curve_shape):
    """ベースカーブに登録されている、実在する最終カーブ名のリストを返す."""
    attr = base_curve_shape + "." + FRILL_CURVES_ATTR
    if not cmds.objExists(attr):

        return []

    names = json.loads(cmds.getAttr(attr) or "[]")

    return [name for name in names if cmds.objExists(name)]


def register_frill_curve(base_curve_shape, frill_curve):
    """ベースカーブに最終カーブ名を登録する."""
    attr = base_curve_shape + "." + FRILL_CURVES_ATTR
    if not cmds.objExists(attr):
        cmds.addAttr(base_curve_shape, longName=FRILL_CURVES_ATTR, dataType="string")
    names = get_frill_curves(base_curve_shape)
    if frill_curve not in names:
        names.append(frill_curve)
    cmds.setAttr(attr, json.dumps(names), type="string")
    store_owner(base_curve_shape)


def stored_aim_curve(frill_curve):
    """フリルカーブに記録されたエイムカーブ名を返す. 無ければ None."""
    attr = frill_curve + "." + AIM_CURVE_ATTR
    if not cmds.objExists(attr):

        return None

    name = cmds.getAttr(attr)

    return name if name and cmds.objExists(name) else None


def edit_targets(node):
    """選択ノード以下のカーブから、編集対象となる最終カーブのリストを返す.

    フリルカーブはそれ自身、ベースカーブはそこに登録された最終カーブに読み替える。
    複数の最終カーブが登録されたベースカーブは、編集対象が定まらないのでエラーにする。
    """
    targets = []
    for shape in get_curve_shapes(node):
        transform = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
        if cmds.objExists(transform + "." + BASE_CURVE_ATTR):
            if not owner_matches(transform):
                raise RuntimeError("%s はアトリビュート作成時と UUID が違います。複製された可能性があります" % transform)
            targets.append(transform)
            continue
        frill_curves = get_frill_curves(shape)
        if frill_curves and not owner_matches(shape):
            raise RuntimeError("%s はアトリビュート作成時と UUID が違います。複製された可能性があります" % shape)
        if len(frill_curves) > 1:
            raise RuntimeError("%s には複数のフリルカーブが登録されています。編集するフリルカーブを選択してください" % transform)
        targets.extend(frill_curves)

    return targets


def sample_curve(curve_shape, count):
    """カーブを弧長で等間隔にサンプリングした MPoint のリストを返す."""
    fn = om.MFnNurbsCurve(get_dag_path(curve_shape))
    total_length = fn.length()
    points = []
    for i in range(count):
        length = total_length * float(i) / (count - 1)
        param = fn.findParamFromLength(length)
        points.append(fn.getPointAtParam(param, om.MSpace.kWorld))

    return points


def average_normal(points):
    """点列が乗るおおよその平面の法線を Newell 法で求める."""
    normal = om.MVector()
    count = len(points)
    for i in range(count):
        cur = points[i]
        nxt = points[(i + 1) % count]
        normal.x += (cur.y - nxt.y) * (cur.z + nxt.z)
        normal.y += (cur.z - nxt.z) * (cur.x + nxt.x)
        normal.z += (cur.x - nxt.x) * (cur.y + nxt.y)

    if normal.length() > 1e-6:

        return normal.normal()

    # 直線に近く平面が定まらない場合は弦に直交する適当な軸を法線とする
    chord = om.MVector(points[-1] - points[0])
    if chord.length() < 1e-9:
        chord = om.MVector(1.0, 0.0, 0.0)
    chord.normalize()
    axes = [om.MVector(1.0, 0.0, 0.0), om.MVector(0.0, 1.0, 0.0), om.MVector(0.0, 0.0, 1.0)]
    axis = min(axes, key=lambda v: abs(v * chord))

    return (chord ^ axis).normal()


def closest_directions(points, aim_curve_shape):
    """各点から、エイムカーブ上の最も近い点へ向かう単位ベクトルを返す.

    エイムカーブとベースカーブが交わる点では向きが決まらないので零ベクトルを返し、
    その点は apply_wave 側で変形しない点として扱われる。
    """
    fn = om.MFnNurbsCurve(get_dag_path(aim_curve_shape))
    result = []
    for point in points:
        closest = fn.closestPoint(point, space=om.MSpace.kWorld)[0]
        vector = om.MVector(closest - point)
        result.append(vector.normal() if vector.length() > 1e-9 else om.MVector())

    return result


def curve_signature(curve_shape):
    """カーブが変化したかを判定するための CV 位置の指紋を返す.

    ワールド空間で取るので、CV の編集だけでなくトランスフォームの移動でも変わる。
    """
    fn = om.MFnNurbsCurve(get_dag_path(curve_shape))

    return tuple((p.x, p.y, p.z) for p in fn.cvPositions(om.MSpace.kWorld))


def polyline_length(points):
    """点列を折れ線とみなした全長を返す."""

    return sum(om.MVector(points[i + 1] - points[i]).length() for i in range(len(points) - 1))


def tangents(points):
    """各点における中央差分の接線を返す."""
    count = len(points)
    result = []
    for i in range(count):
        prev = points[max(i - 1, 0)]
        nxt = points[min(i + 1, count - 1)]
        vector = om.MVector(nxt - prev)
        if vector.length() < 1e-9:
            vector = om.MVector(1.0, 0.0, 0.0)
        result.append(vector.normal())

    return result


def sine(phase):
    """サイン波."""

    return math.sin(phase)


def triangle(phase):
    """頂点が ±1 になる三角波."""

    return 2.0 / math.pi * math.asin(math.sin(phase))


def square(phase):
    """矩形波."""

    return math.copysign(1.0, math.sin(phase))


# ドロップダウンに並べる波形名と、位相 (ラジアン) から振幅に対する比を返す関数の対応。
# 絶対値版は片側にしか振れないので、値域が 0.0 - 1.0 になる
WAVEFORMS = {
    "サイン波": sine,
    "三角波": triangle,
    "矩形波": square,
    "サイン波 (絶対値)": lambda phase: abs(sine(phase)),
    "三角波 (絶対値)": lambda phase: abs(triangle(phase)),
    "矩形波 (絶対値)": lambda phase: abs(square(phase)),
}

DEFAULT_WAVEFORM = "サイン波"

# 波の変位方向。水平はカーブの横方向、垂直はそれと接線の両方に直交する方向、進行方向は接線そのもの
DIRECTION_HORIZONTAL = "水平"

DIRECTION_VERTICAL = "垂直"

DIRECTION_TANGENT = "進行方向"

DIRECTIONS = (DIRECTION_HORIZONTAL, DIRECTION_VERTICAL, DIRECTION_TANGENT)

DEFAULT_DIRECTION = DIRECTION_HORIZONTAL


def default_params():
    """UI の初期値をまとめた辞書を返す."""
    waves = []
    for wavelength, offset in zip(DEFAULT_WAVELENGTHS, DEFAULT_OFFSETS):
        wave = {}
        wave["direction"] = DEFAULT_DIRECTION
        wave["waveform"] = DEFAULT_WAVEFORM
        wave["factor"] = DEFAULT_FACTOR
        wave["wavelength"] = wavelength
        wave["offset"] = offset
        waves.append(wave)

    params = {}
    params["amplitude"] = DEFAULT_AMPLITUDE
    params["total_offset"] = DEFAULT_TOTAL_OFFSET
    params["total_wavelength_scale"] = DEFAULT_TOTAL_WAVELENGTH_SCALE
    params["waves"] = waves

    return params


def apply_wave(points, base_length, plane_normal, aim_directions, amplitude, wavelength, offset, waveform, direction):
    """現在の点列の接線から求めた横方向に波を加算する.

    位相はベースカーブ上の弧長で決まり、方向だけが変形の度に更新される。
    これにより波が前段の波の傾きに追従し、オーバーハングが表現できる。
    wavelength は 1 周期分がベースカーブ上で占める弧長、
    offset は開始位相の π 単位でのずれ量で、-1.0 - 1.0 が -π - +π に対応する。
    waveform は WAVEFORMS のキー。
    aim_directions が None なら横方向は接線と平面法線の外積、
    そうでなければエイムカーブへ向かう方向から接線成分を除いたものになる。
    direction が DIRECTION_VERTICAL の場合は、その横方向と接線の両方に直交する向きへ変位する。
    エイムカーブが無ければこれは平面法線そのものになる。
    DIRECTION_TANGENT の場合は接線方向へ変位し、点が弧長方向に寄ったり伸びたりする。
    """
    if amplitude == 0.0 or wavelength <= 0.0:

        return points

    count = len(points)
    tangent_list = tangents(points)
    shape = WAVEFORMS[waveform]
    result = []
    for i in range(count):
        arc_length = base_length * float(i) / (count - 1)
        phase = arc_length / wavelength * 2.0 * math.pi + offset * math.pi
        if aim_directions is None:
            side = tangent_list[i] ^ plane_normal
        else:
            aim = aim_directions[i]
            side = aim - tangent_list[i] * (aim * tangent_list[i])
        if side.length() < 1e-9:
            result.append(points[i])
            continue
        side = side.normal()
        if direction == DIRECTION_VERTICAL:
            side = (side ^ tangent_list[i]).normal()
        elif direction == DIRECTION_TANGENT:
            side = tangent_list[i]
        result.append(points[i] + side * amplitude * shape(phase))

    return result


def wavelength_multiplier(value):
    """全体波長スケールの値を、各段の波長に掛ける倍率に変換する.

    +n で n 倍、-n で 1/n 倍になり、-1.0 - 1.0 の間はすべて 1 倍。
    """
    if value >= 1.0:

        return value

    if value <= -1.0:

        return -1.0 / value

    return 1.0


def build_points(base_points, base_length, plane_normal, aim_directions, params):
    """パラメーターの各波を順に適用した点列を返す."""
    total_offset = params["total_offset"]
    multiplier = wavelength_multiplier(params["total_wavelength_scale"])
    points = base_points
    for wave in params["waves"]:
        wavelength = wave["wavelength"] * multiplier
        offset = wave["offset"] + total_offset * TOTAL_OFFSET_WAVELENGTH / wavelength
        points = apply_wave(points, base_length, plane_normal, aim_directions, params["amplitude"] * wave["factor"], wavelength, offset, wave["waveform"], wave["direction"])

    return points


def set_curve_points(curve, points):
    """カーブの CV 位置を点列で置き換える."""
    fn = om.MFnNurbsCurve(get_dag_path(curve))
    fn.setCVPositions(om.MPointArray(points), om.MSpace.kWorld)
    fn.updateCurve()


def rebuild_frill_curve(frill_curve):
    """フリルカーブに記録された情報だけを使って形状を再計算する."""
    base_curve_shape = cmds.getAttr(frill_curve + "." + BASE_CURVE_ATTR)
    params_attr = frill_curve + "." + PARAMS_ATTR
    if not base_curve_shape or not cmds.objExists(base_curve_shape) or not cmds.objExists(params_attr):

        return

    base_points = sample_curve(base_curve_shape, SAMPLE_COUNT)
    aim_curve_shape = stored_aim_curve(frill_curve)
    aim_directions = closest_directions(base_points, aim_curve_shape) if aim_curve_shape else None
    params = json.loads(cmds.getAttr(params_attr))
    points = build_points(base_points, polyline_length(base_points), average_normal(base_points), aim_directions, params)
    set_curve_points(frill_curve, points)


def rebuild_frill_curves(frill_curves):
    """複数のフリルカーブをまとめて再計算する.

    CV の書き換えが監視中のカーブを動かして再発火することがあるので、
    多重に走らないようフラグで止める。
    """
    global _rebuilding

    if _rebuilding:

        return

    _rebuilding = True
    try:
        for frill_curve in frill_curves:
            if cmds.objExists(frill_curve):
                rebuild_frill_curve(frill_curve)
    finally:
        _rebuilding = False


class FrillCurveTool(object):
    """ベースカーブにサイン波を重ねた最終カーブを対話的に編集する."""

    def __init__(self):
        self.base_curve_shape = None
        self.base_points = None
        self.base_length = 0.0
        self.plane_normal = None
        self.aim_curve_shape = None
        self.aim_directions = None
        self.out_curve = None
        self.amplitude_field = None
        self.total_offset_slider = None
        self.total_offset_label = None
        self.total_wavelength_scale_slider = None
        self.total_wavelength_scale_label = None
        self.out_curve_label = None
        self.aim_curve_label = None
        self.cb_edit_directly = None
        self.span_field = None
        self.sync_label = None
        self.jobs = []
        self.targets = []
        self.watched_shapes = []
        self.signatures = []
        self.direction_menus = []
        self.waveform_menus = []
        self.sliders = []
        self.wavelength_sliders = []
        self.wavelength_labels = []
        self.offset_sliders = []

    def create_out_curve(self, base_curve_shape):
        """ベースカーブと同形状の最終カーブを新規に作成する."""
        transform = cmds.curve(point=[(p.x, p.y, p.z) for p in self.base_points], degree=3)
        base_name = cmds.listRelatives(base_curve_shape, parent=True)[0]
        out_curve = cmds.ls(cmds.rename(transform, base_name + "_frill#"), long=True)[0]
        cmds.addAttr(out_curve, longName=BASE_CURVE_ATTR, dataType="string")
        cmds.setAttr(out_curve + "." + BASE_CURVE_ATTR, base_curve_shape, type="string")
        store_owner(out_curve)
        register_frill_curve(base_curve_shape, out_curve)

        return out_curve

    def create_base_curve(self, curve_shape):
        """カーブを複製して新しいベースカーブを作り、そのシェイプ名を返す."""
        transform = cmds.listRelatives(curve_shape, parent=True, fullPath=True)[0]
        short_name = transform.split("|")[-1]
        base_transform = cmds.ls(cmds.rename(cmds.duplicate(transform)[0], short_name + "_base#"), long=True)[0]

        # 複製元が持っていたエクストラアトリビュートは持ち越さない
        for node in [base_transform] + get_curve_shapes(base_transform):
            for attr_name in cmds.listAttr(node, userDefined=True) or []:
                if not cmds.objExists(node + "." + attr_name):
                    continue
                cmds.setAttr(node + "." + attr_name, lock=False)
                cmds.deleteAttr(node + "." + attr_name)

        return get_curve_shapes(base_transform)[0]

    def convert_to_out_curve(self, curve_shape, base_curve_shape):
        """既存のカーブを最終カーブと同じ CV 数に再分割し、最終カーブとして登録する."""
        out_curve = cmds.listRelatives(curve_shape, parent=True, fullPath=True)[0]

        # 次数 3 の開いたカーブの CV 数は スパン数 + 3
        cmds.rebuildCurve(
            out_curve,
            constructionHistory=False,
            replaceOriginal=True,
            rebuildType=0,
            endKnots=1,
            keepRange=0,
            keepControlPoints=False,
            keepEndPoints=True,
            keepTangents=False,
            spans=SAMPLE_COUNT - 3,
            degree=3,
        )
        cmds.addAttr(out_curve, longName=BASE_CURVE_ATTR, dataType="string")
        cmds.setAttr(out_curve + "." + BASE_CURVE_ATTR, base_curve_shape, type="string")
        store_owner(out_curve)
        register_frill_curve(base_curve_shape, out_curve)

        return out_curve

    def execute(self, *args):
        """選択中のカーブから最終カーブを作り、以降の編集対象として記憶する.

        選択カーブを直接編集する場合は選択カーブを複製して新しいベースカーブを作り、選択カーブ自身を最終カーブとして変形する。
        直接編集しない場合は選択カーブをベースカーブにして新しい最終カーブを作る。
        """
        selection = cmds.ls(selection=True, long=True) or []
        shapes = []
        for node in selection:
            shapes.extend(get_curve_shapes(node))
        if len(shapes) != 1:
            raise RuntimeError("ベースカーブを1本選択してください (選択から見つかったカーブ: %d)" % len(shapes))

        if not owner_matches(shapes[0]):
            raise RuntimeError("%s はアトリビュート作成時と UUID が違います。複製された可能性があります" % shapes[0])

        if cmds.checkBox(self.cb_edit_directly, q=True, value=True):
            transform = cmds.listRelatives(shapes[0], parent=True, fullPath=True)[0]
            if cmds.objExists(transform + "." + BASE_CURVE_ATTR):
                raise RuntimeError("%s は既にフリルカーブです。[編集] を使ってください" % transform)

            self.base_curve_shape = self.create_base_curve(shapes[0])
            self.sample_base()
            self.out_curve = self.convert_to_out_curve(shapes[0], self.base_curve_shape)

        else:
            self.base_curve_shape = shapes[0]
            self.sample_base()
            self.out_curve = self.create_out_curve(self.base_curve_shape)

        self.update()

    def edit(self, *args):
        """選択中のフリルカーブ、またはベースカーブから辿った1本を編集対象として読み込む."""
        selection = cmds.ls(selection=True, long=True) or []
        transforms = []
        for node in selection:
            for transform in edit_targets(node):
                if transform not in transforms:
                    transforms.append(transform)
        if len(transforms) != 1:
            raise RuntimeError("フリルカーブ、またはそれを登録したベースカーブを1本選択してください (選択から見つかったフリルカーブ: %d)" % len(transforms))

        base_curve_shape = cmds.getAttr(transforms[0] + "." + BASE_CURVE_ATTR)
        if not base_curve_shape or not cmds.objExists(base_curve_shape):
            raise RuntimeError("記録されたベースカーブが見つかりません: %s" % base_curve_shape)

        self.base_curve_shape = base_curve_shape
        self.out_curve = transforms[0]
        self.aim_curve_shape = stored_aim_curve(self.out_curve)
        params_attr = self.out_curve + "." + PARAMS_ATTR
        if cmds.objExists(params_attr):
            self.apply_params(json.loads(cmds.getAttr(params_attr)))
        self.sample_base()
        self.update()

    def finish(self, *args):
        """編集対象を解放し、以降のパラメーター変更がどのカーブにも影響しないようにする."""
        self.base_curve_shape = None
        self.base_points = None
        self.out_curve = None
        self.update_labels()

    def reset(self, *args):
        """パラメーターを初期値に戻す."""
        self.apply_params(default_params())
        self.update()

    def set_aim_curve(self, *args):
        """選択中のカーブをエイムカーブとして登録する.

        以降、波の向きはベースカーブ上の点からエイムカーブへ向かう方向で決まる。
        """
        selection = cmds.ls(selection=True, long=True) or []
        shapes = []
        for node in selection:
            shapes.extend(get_curve_shapes(node))
        if len(shapes) != 1:
            raise RuntimeError("エイムカーブを1本選択してください (選択から見つかったカーブ: %d)" % len(shapes))

        self.aim_curve_shape = shapes[0]
        self.update()

        # 同期中なら新しいエイムカーブも監視対象に加える
        if self.jobs and self.aim_curve_shape not in self.watched_shapes:
            self.watched_shapes.append(self.aim_curve_shape)
            self.signatures = self.current_signatures()

    def remove_invalid_attrs(self, *args):
        """作成時と UUID が食い違うノードから、このツールのカスタムアトリビュートを削除する."""
        removed = []
        for node in owner_attr_nodes():
            if owner_matches(node):
                continue
            for attr_name in CUSTOM_ATTRS:
                if cmds.objExists(node + "." + attr_name):
                    cmds.deleteAttr(node + "." + attr_name)
            removed.append(node)
        print("不正アトリビュートを削除: %d 件 %s" % (len(removed), removed))

    def bake_attrs(self, *args):
        """カスタムアトリビュートの作成時 UUID を、現在の UUID で上書きする."""
        nodes = owner_attr_nodes()
        for node in nodes:
            store_owner(node)
        print("アトリビュートをベイク: %d 件 %s" % (len(nodes), nodes))

    def loft(self, *args):
        """選択中のカーブ間をロフトしてポリゴンを作る."""
        cmds.loft(constructionHistory=True, uniform=True, close=False, autoReverse=True, degree=1, sectionSpans=1, range=False, polygon=1, reverseSurfaceNormals=True)

    def reverse_curve(self, *args):
        """選択中のカーブの向きを反転する."""
        cmds.reverseCurve(constructionHistory=True, replaceOriginal=True)

    def make_curve(self, *args):
        """選択中のエッジ列から、指定スパン数でリビルドしたカーブを作る."""
        curve = cmds.polyToCurve(form=2, degree=3, conformToSmoothMeshPreview=1)[0]
        cmds.delete(curve, constructionHistory=True)
        cmds.select(curve, replace=True)

    def kill_jobs(self):
        """張ってある scriptJob をすべて止める."""
        for job in self.jobs:
            if cmds.scriptJob(exists=job):
                cmds.scriptJob(kill=job, force=True)
        self.jobs = []

    def stop_sync(self, *args):
        """監視を止める."""
        self.kill_jobs()
        self.targets = []
        self.watched_shapes = []
        self.signatures = []
        self.update_sync_label()

    def update_sync_label(self):
        """同期中かどうかをラベルに表示する."""
        if self.jobs:
            cmds.text(self.sync_label, e=True, label="同期中", backgroundColor=SYNC_ON_COLOR)
        else:
            cmds.text(self.sync_label, e=True, label="同期停止中", backgroundColor=SYNC_OFF_COLOR)

    def start_sync(self, *args):
        """編集対象に関わるカーブの形状変更を監視する scriptJob を張る.

        更新対象はベースカーブに登録された全フリルカーブ。監視するのはベースカーブと、
        それらのフリルカーブが参照するエイムカーブ。ジョブはウィンドウに紐付けるので
        ウィンドウを閉じれば自動で止まる。

        CV の編集は attributeChange を発火させないため、アイドルごとに指紋を比べる。
        """
        self.stop_sync()
        if not self.out_curve or not self.base_curve_shape or not cmds.objExists(self.base_curve_shape):
            raise RuntimeError("編集対象がありません。[実行] か [編集] でフリルカーブを指定してから開始してください")

        self.targets = get_frill_curves(self.base_curve_shape) or [self.out_curve]
        self.watched_shapes = [self.base_curve_shape]
        for target in self.targets:
            aim_curve_shape = stored_aim_curve(target)
            if aim_curve_shape and aim_curve_shape not in self.watched_shapes:
                self.watched_shapes.append(aim_curve_shape)

        self.signatures = self.current_signatures()
        self.jobs.append(cmds.scriptJob(event=["idle", self.watch], parent=WINDOW_NAME))
        self.update_sync_label()

    def current_signatures(self):
        """監視中のカーブの現在の指紋をまとめて返す."""

        return [curve_signature(shape) for shape in self.watched_shapes if cmds.objExists(shape)]

    def watch(self):
        """監視中のカーブが変化していたらフリルカーブを再計算する."""
        signatures = self.current_signatures()
        if signatures == self.signatures:

            return

        self.signatures = signatures
        rebuild_frill_curves(self.targets)

    def sample_base(self):
        """ベースカーブの現在の形状をサンプリングし直す."""
        self.base_points = sample_curve(self.base_curve_shape, SAMPLE_COUNT)
        self.base_length = polyline_length(self.base_points)
        self.plane_normal = average_normal(self.base_points)
        if self.aim_curve_shape and cmds.objExists(self.aim_curve_shape):
            self.aim_directions = closest_directions(self.base_points, self.aim_curve_shape)
        else:
            self.aim_directions = None

    def get_params(self):
        """UI の値を辞書にまとめる."""
        waves = []
        for direction_menu, menu, slider, wavelength_slider, offset_slider in zip(self.direction_menus, self.waveform_menus, self.sliders, self.wavelength_sliders, self.offset_sliders):
            wave = {}
            wave["direction"] = cmds.optionMenu(direction_menu, q=True, value=True)
            wave["waveform"] = cmds.optionMenu(menu, q=True, value=True)
            wave["factor"] = cmds.floatSlider(slider, q=True, value=True)
            wave["wavelength"] = cmds.floatSlider(wavelength_slider, q=True, value=True)
            wave["offset"] = cmds.floatSlider(offset_slider, q=True, value=True)
            waves.append(wave)

        params = {}
        params["amplitude"] = cmds.floatField(self.amplitude_field, q=True, value=True)
        params["total_offset"] = cmds.floatSlider(self.total_offset_slider, q=True, value=True)
        # デッドゾーン内の値はどれも 1 倍なので、記録上は 1.0 に丸める
        scale = cmds.floatSlider(self.total_wavelength_scale_slider, q=True, value=True)
        params["total_wavelength_scale"] = scale if abs(scale) >= 1.0 else 1.0
        params["waves"] = waves

        return params

    def apply_params(self, params):
        """辞書の値を UI に反映する."""
        cmds.floatField(self.amplitude_field, e=True, value=params["amplitude"])
        cmds.floatSlider(self.total_offset_slider, e=True, value=params["total_offset"])
        # 記録上の 1 倍は 1.0 だが、スライダーはデッドゾーンの中央に戻す
        scale = params["total_wavelength_scale"]
        cmds.floatSlider(self.total_wavelength_scale_slider, e=True, value=0.0 if scale == 1.0 else scale)
        for wave, direction_menu, menu, slider, wavelength_slider, offset_slider in zip(
            params["waves"],
            self.direction_menus,
            self.waveform_menus,
            self.sliders,
            self.wavelength_sliders,
            self.offset_sliders,
        ):
            cmds.optionMenu(direction_menu, e=True, value=wave["direction"])
            cmds.optionMenu(menu, e=True, value=wave["waveform"])
            cmds.floatSlider(slider, e=True, value=wave["factor"])
            cmds.floatSlider(wavelength_slider, e=True, value=wave["wavelength"])
            cmds.floatSlider(offset_slider, e=True, value=wave["offset"])

    def store_params(self):
        """現在の UI の値を JSON 文字列として最終カーブに保存する."""
        attr = self.out_curve + "." + PARAMS_ATTR
        if not cmds.objExists(attr):
            cmds.addAttr(self.out_curve, longName=PARAMS_ATTR, dataType="string")
        cmds.setAttr(attr, json.dumps(self.get_params()), type="string")

    def store_aim_curve(self):
        """現在のエイムカーブ名を最終カーブに保存する."""
        attr = self.out_curve + "." + AIM_CURVE_ATTR
        if not cmds.objExists(attr):
            cmds.addAttr(self.out_curve, longName=AIM_CURVE_ATTR, dataType="string")
        cmds.setAttr(attr, self.aim_curve_shape or "", type="string")

    def update_labels(self):
        """スライダーの現在値と編集対象・エイムカーブのカーブ名をラベルに表示する."""
        cmds.text(self.out_curve_label, e=True, label=self.out_curve.split("|")[-1] if self.out_curve else "")
        # エイムカーブはシェイプ名で保持しているので、親のトランスフォーム名を表示する
        cmds.text(self.aim_curve_label, e=True, label=self.aim_curve_shape.split("|")[-2] if self.aim_curve_shape else "")
        cmds.text(self.total_offset_label, e=True, label="%.2f" % cmds.floatSlider(self.total_offset_slider, q=True, value=True))
        cmds.text(self.total_wavelength_scale_label, e=True, label="x%.2f" % wavelength_multiplier(cmds.floatSlider(self.total_wavelength_scale_slider, q=True, value=True)))
        for wavelength_slider, wavelength_label in zip(self.wavelength_sliders, self.wavelength_labels):
            cmds.text(wavelength_label, e=True, label="%.2f" % cmds.floatSlider(wavelength_slider, q=True, value=True))

    def update(self, *args):
        """UI の値から最終カーブの CV を再計算して流し込む."""
        self.update_labels()
        if not self.out_curve or not cmds.objExists(self.out_curve):

            return

        # ベースカーブが消えている場合は最後にサンプリングした形状をそのまま使う
        if cmds.objExists(self.base_curve_shape):
            self.sample_base()

        set_curve_points(self.out_curve, build_points(self.base_points, self.base_length, self.plane_normal, self.aim_directions, self.get_params()))
        self.store_params()
        self.store_aim_curve()

    def show(self):
        """ウィンドウを表示する."""
        if cmds.window(WINDOW_NAME, exists=True):
            cmds.deleteUI(WINDOW_NAME)

        cmds.window(WINDOW_NAME, title="Frill Curve", widthHeight=(1030, 200), maximizeButton=False, minimizeButton=False)

        columnWidth = [(1, ui.width(4)), (2, ui.width(4)), (3, ui.width(4)), (4, ui.width(8)), (5, ui.width(2)), (6, ui.width(6))]
        separator_width = ui.width(28)

        with ui.column_layout():
            with ui.row_layout():
                ui.button(label="実行", width=ui.width(3), c=self.execute)
                ui.button(label="編集", width=ui.width(3), c=self.edit)
                ui.button(label="確定", width=ui.width(3), c=self.finish)
                self.cb_edit_directly = ui.check_box(label="選択カーブを直接編集", width=ui.width(6), cc=self.update, v=True)
                
            with ui.row_layout():
                ui.button(label="同期開始", width=ui.width(3), c=self.start_sync)
                ui.button(label="同期停止", width=ui.width(3), c=self.stop_sync)
                ui.button(label="不正アトリビュートの削除", width=ui.width(6), c=self.remove_invalid_attrs)
                ui.button(label="アトリビュートのベイク", width=ui.width(6), c=self.bake_attrs)

            with ui.row_layout():
                self.sync_label = ui.text(label="同期停止中", width=ui.width(3), backgroundColor=SYNC_OFF_COLOR)

            ui.separator(height=ui.height(1), style="in", width=separator_width)

            with ui.row_layout():
                ui.text(label="編集中カーブ:", width=ui.width(4))
                self.out_curve_label = ui.text(label="", width=ui.width(6))
                ui.button(label="エイムカーブ指定", width=ui.width(3), c=self.set_aim_curve)
                self.aim_curve_label = ui.text(label="", width=ui.width(6))

            with ui.row_layout(numberOfColumns=8, columnWidth=columnWidth):
                ui.text(label="方向")
                ui.text(label="形状")
                ui.text(label="強さ")
                ui.text(label="波長")
                ui.text(label="")
                ui.text(label="オフセット")

            for i, (wavelength, offset) in enumerate(zip(DEFAULT_WAVELENGTHS, DEFAULT_OFFSETS)):
                with ui.row_layout(numberOfColumns=8, columnWidth=columnWidth):
                    direction_menu = ui.option_menu(label="", items=DIRECTIONS, cc=self.update)
                    cmds.optionMenu(direction_menu, e=True, value=DEFAULT_DIRECTION, width=ui.width(4))
                    waveform_menu = ui.option_menu(label="", items=WAVEFORMS, cc=self.update)
                    cmds.optionMenu(waveform_menu, e=True, value=DEFAULT_WAVEFORM, width=ui.width(4))
                    slider = ui.float_slider(min=0.0, max=1.0, value=DEFAULT_FACTOR, width=ui.width(4), dc=self.update, cc=self.update)
                    wavelength_slider = ui.float_slider(min=WAVELENGTH_MIN, max=WAVELENGTH_MAX, value=wavelength, width=ui.width(8), dc=self.update, cc=self.update)
                    wavelength_label = ui.text(label="%.2f" % wavelength, width=ui.width(2), align="left")
                    offset_slider = ui.float_slider(min=-1.0, max=1.0, value=offset, width=ui.width(6), dc=self.update, cc=self.update)

                self.direction_menus.append(direction_menu)
                self.waveform_menus.append(waveform_menu)
                self.sliders.append(slider)
                self.wavelength_sliders.append(wavelength_slider)
                self.wavelength_labels.append(wavelength_label)
                self.offset_sliders.append(offset_slider)

            with ui.row_layout():
                ui.button(label="パラメーターリセット", width=ui.width(6), c=self.reset)

            ui.separator(height=ui.height(1), style="in", width=separator_width)

            with ui.row_layout(numberOfColumns=10, columnWidth=columnWidth):
                ui.text(label="", width=ui.width(2))

                ui.text(label="全体振幅", width=ui.width(2))
                self.amplitude_field = ui.eb_float(v=DEFAULT_AMPLITUDE, width=ui.width(4), cc=self.update, precision=3)

                with ui.row_layout(numberOfColumns=2):
                    ui.text(label="波長スケール", width=ui.width(2))
                    self.total_wavelength_scale_slider = ui.float_slider(
                        min=TOTAL_WAVELENGTH_SCALE_MIN,
                        max=TOTAL_WAVELENGTH_SCALE_MAX,
                        value=DEFAULT_TOTAL_WAVELENGTH_SCALE,
                        width=ui.width(4),
                        dc=self.update,
                        cc=self.update,
                    )

                self.total_wavelength_scale_label = ui.text(label="x%.2f" % wavelength_multiplier(DEFAULT_TOTAL_WAVELENGTH_SCALE), width=ui.width(2), align="left")

                with ui.row_layout(numberOfColumns=3):
                    ui.text(label="全体オフセット", width=ui.width(2))
                    self.total_offset_slider = ui.float_slider(min=-1.0, max=1.0, value=DEFAULT_TOTAL_OFFSET, width=ui.width(4), dc=self.update, cc=self.update)
                    self.total_offset_label = ui.text(label="%.2f" % DEFAULT_TOTAL_OFFSET, width=ui.width(2), align="left")

            ui.separator(height=ui.height(1), style="in", width=separator_width)

            with ui.row_layout():
                ui.button(label="Loft", width=ui.width(3), c=self.loft)
                ui.button(label="Reverse Curve", width=ui.width(3), c=self.reverse_curve)
                ui.button(label="Make Curve", width=ui.width(3), c=self.make_curve)

        cmds.showWindow(WINDOW_NAME)


def main():
    """最終カーブを作るための編集 UI を表示する."""
    global _tool

    _tool = FrillCurveTool()
    _tool.show()

    return _tool


if __name__ == "__main__":
    main()
