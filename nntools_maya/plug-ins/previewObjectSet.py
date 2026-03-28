"""指定した ObjectSet の要素をリアルタイムでプレビューするノード"""
import sys
import re

import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui
import maya.api.OpenMayaRender as omr


def node_exists(name):
    """ノードが存在するかどうか"""
    it_node = om.MItDependencyNodes()

    while not it_node.isDone():
        obj = it_node.thisNode()
        depend_fn = om.MFnDependencyNode(obj)

        if depend_fn.name() == name:
            return True

        it_node.next()

    return False


def get_inherited_visibility(obj_name):
    """指定したオブジェクトがビューに表示されているなら True を返す｡

    オブジェクト自身の visibility が True でも DAG での親に非表示オブジェクトがあれば False を返す｡
    isolate は考慮しない｡
    インスタンスは非対応｡
    """
    slist = om.MGlobal.getSelectionListByName(obj_name)
    dag = slist.getDagPath(0)
    full_path = dag.fullPathName()

    for i in range(full_path.count("|")):
        pattern = r"^(?:\|[^|]+){%s}" % str(i+1)
        parent_name = re.search(pattern, full_path).group()

        slist = om.MGlobal.getSelectionListByName(parent_name)
        node = slist.getDependNode(0)
        fn_node = om.MFnDependencyNode(node)
        visibility = fn_node.findPlug("visibility", False).asBool()

        if not visibility:
            return False

    return True


def get_isolation_visibility(obj_name):
    """isolation によって非表示になっている場合は False を返す｡
    
    すべてのパネルのうち一つでも非表示になっている場合は False
    """
    # すべての isolation 用のセット取得
    # 全ノードスキャンを避けるため名前で直接引く (パネル番号は余裕を持って 100 まで)
    all_isolateion_sets = []

    for i in range(1, 101):
        try:
            slist = om.MGlobal.getSelectionListByName(f"modelPanel{i}ViewSelectedSet")
            all_isolateion_sets.append(slist.getDependNode(0))
        except RuntimeError:
            pass

    if not all_isolateion_sets:
        return True

    # すべての親の取得
    all_parents_name = []

    slist = om.MGlobal.getSelectionListByName(obj_name)
    dag = slist.getDagPath(0)
    full_path = dag.fullPathName()

    for i in range(full_path.count("|")):
        pattern = r"^(?:\|[^|]+){%s}" % str(i+1)
        parent_name = re.search(pattern, full_path).group()
        all_parents_name.append(parent_name)

    # すべてのセットに関して､親がひとつも含まれていなければ False
    for set_node in all_isolateion_sets:
        fn_set = om.MFnSet(set_node)
        sl_members = fn_set.getMembers(False)
        all_members_name = []

        for i in range(sl_members.length()):
            member = sl_members.getDagPath(i)

            all_members_name.append(member.fullPathName())

        if not any([parent in all_members_name for parent in all_parents_name]):
            return False

    return True


def maya_useNewAPI():
    pass


class PreviewObjectSet(omui.MPxLocatorNode):
    kPluginNodeTypeName = "previewObjectSet"
    NodeId = om.MTypeId(0x0013a240)

    classification = "drawdb/geometry/previewObjectSet"
    registrantId = "previewObjectSetPlugin"

    default_set_name = "edgeSet"
    default_line_width = 4.0
    default_line_color = 0.0
    default_line_alpha = 1.0
    default_camera_offset = 0.025

    display = None
    setName = None
    lineWidth = None
    lineColor = None
    lineAlpha = None
    cameraOffset = None

    def __init__(self):
        omui.MPxLocatorNode.__init__(self)

    def draw(self, view, path, style, status):
        pass

    def isBounded(self):
        return True

    def boundingBox(self):
        size = 200

        return om.MBoundingBox(om.MPoint(size, size, size), om.MPoint(-size, -size, -size))

    @staticmethod
    def nodeCreator():
        return PreviewObjectSet()

    @staticmethod
    def nodeInitializer():
        # (bool) プレビューの表示切り替えアトリビュート
        fn_attr = om.MFnNumericAttribute()
        PreviewObjectSet.display = fn_attr.create("display", "d", om.MFnNumericData.kBoolean, 1)
        fn_attr.storable = True
        fn_attr.writable = True
        fn_attr.readable = True
        PreviewObjectSet.addAttribute(PreviewObjectSet.display)

        # (string) プレビューするエッジセット名アトリビュート
        fn_attr = om.MFnTypedAttribute()
        default_value = om.MFnStringData().create(PreviewObjectSet.default_set_name)
        PreviewObjectSet.setName = fn_attr.create("setName", "sn", om.MFnData.kString, default_value)
        fn_attr.storable = True
        fn_attr.writable = True
        fn_attr.readable = True
        PreviewObjectSet.addAttribute(PreviewObjectSet.setName)

        # (float) プレビューするラインのピクセル数
        fn_attr = om.MFnNumericAttribute()
        PreviewObjectSet.lineWidth = fn_attr.create("lineWidth", "lw", om.MFnNumericData.kFloat, PreviewObjectSet.default_line_width)
        fn_attr.storable = True
        fn_attr.writable = True
        fn_attr.readable = True
        PreviewObjectSet.addAttribute(PreviewObjectSet.lineWidth)

        # (float3) プレビューするラインの色
        fn_attr = om.MFnNumericAttribute()
        PreviewObjectSet.lineColor = fn_attr.create("lineColor", "lc", om.MFnNumericData.k3Float, PreviewObjectSet.default_line_color)
        fn_attr.storable = True
        fn_attr.writable = True
        fn_attr.readable = True
        fn_attr.usedAsColor = True
        PreviewObjectSet.addAttribute(PreviewObjectSet.lineColor)

        # (float) プレビューするラインのアルファ
        fn_attr = om.MFnNumericAttribute()
        PreviewObjectSet.lineAlpha = fn_attr.create("lineAlpha", "la", om.MFnNumericData.kFloat, PreviewObjectSet.default_line_alpha)
        fn_attr.storable = True
        fn_attr.writable = True
        fn_attr.readable = True
        PreviewObjectSet.addAttribute(PreviewObjectSet.lineAlpha)

        # (float) カメラ方向へのオフセット量
        fn_attr = om.MFnNumericAttribute()
        PreviewObjectSet.cameraOffset = fn_attr.create("cameraOffset", "co", om.MFnNumericData.kFloat, PreviewObjectSet.default_camera_offset)
        fn_attr.storable = True
        fn_attr.writable = True
        fn_attr.readable = True
        fn_attr.setMin(0.0)
        fn_attr.setMax(0.1)
        PreviewObjectSet.addAttribute(PreviewObjectSet.cameraOffset)

        return True

    @staticmethod
    def excludeAsLocator():
        return False


class UserData(om.MUserData):
    def __init__(self):
        om.MUserData.__init__(self, False)
        self.lines = []
        self.lineWidth = 1.0
        self.lineColor = om.MColor((0, 0, 0))
        self.lineAlpha = 1.0


class PreviewObjectSetOverride(omr.MPxDrawOverride):
    def __init__(self, obj):
        omr.MPxDrawOverride.__init__(self, obj, PreviewObjectSetOverride.draw)
        self._dirty = True
        # アトリビュート変更時にダーティフラグを立てる
        # ※セット内容の変更やメッシュ頂点の変化は検知しないため、それらが変わった場合は
        #   アトリビュートを一度触って手動でリフレッシュする必要がある
        self._node_cb = om.MNodeMessage.addAttributeChangedCallback(obj, self._mark_dirty)

    def __del__(self):
        om.MMessage.removeCallback(self._node_cb)

    def _mark_dirty(self, *_):
        self._dirty = True

    @staticmethod
    def draw(context, data):
        pass

    def supportedDrawAPIs(self):
        return omr.MRenderer.kDirectX11

    def hasUIDrawables(self):
        return True

    def isBounded(self, objPath, cameraPath):
        return True

    def boundingBox(self, objPath, cameraPaht):
        size = 2000

        return om.MBoundingBox(om.MPoint(size, size, size), om.MPoint(-size, -size, -size))

    def disableInternalBoundingBoxDraw(self):
        return True

    def prepareForDraw(self, objPath, cameraPath, frameContext, oldData):
        """描画の前処理関数｡ UserData を構築して返す

        Args:
            objPath (MDagPath): _description_
            cameraPath (MDagPath): _description_
            frameContext (_type_): _description_
            oldData (UserData): _description_
        """
        if objPath:
            newData = None

            if oldData:
                newData = oldData
                newData.lines = []

            else:
                newData = UserData()

            thisNode = objPath.node()
            fnNode = om.MFnDependencyNode(thisNode)
            fnDagNode = om.MFnDagNode(thisNode)

            display = fnNode.findPlug("display", False).asBool()

            if display:
                # アトリビュートの取得
                setName = fnNode.findPlug("setName", False).asString()
                lineWidth = fnNode.findPlug("lineWidth", False).asFloat()
                lineColorPlug = fnNode.findPlug("lineColor", False)
                r = lineColorPlug.child(0).asFloat()
                g = lineColorPlug.child(1).asFloat()
                b = lineColorPlug.child(2).asFloat()
                lineAlpha = fnNode.findPlug("lineAlpha", False).asFloat()
                cameraOffset = fnNode.findPlug("cameraOffset", False).asFloat()

                # UserData オブジェクト構築
                newData.lines = []

                newData.lineWidth = max(0, lineWidth)
                newData.lineColor = om.MColor((r, g, b))
                newData.lineAlpha = max(0, lineAlpha)

                # セットからエッジの始点終点を追加する
                if node_exists(setName):
                    slist = om.MGlobal.getSelectionListByName(setName)
                    set_node = slist.getDependNode(0)
                    fn_set = om.MFnSet(set_node)
                    sl_members = fn_set.getMembers(True)

                    camera_trs_path = om.MDagPath(cameraPath).pop()
                    camera_pos = om.MPoint(om.MFnTransform(camera_trs_path).translation(om.MSpace.kWorld))

                    for i in range(sl_members.length()):
                        obj, comps = sl_members.getComponent(i)
                        fn_mesh = om.MFnMesh(obj)
                        it_edge = om.MItMeshEdge(obj, comps)

                        if not get_inherited_visibility(obj.fullPathName()) or not get_isolation_visibility(obj.fullPathName()):
                            continue

                        while not it_edge.isDone():
                            ei = it_edge.index()
                            vi1, vi2 = fn_mesh.getEdgeVertices(ei)

                            p1 = fn_mesh.getPoint(vi1, om.MSpace.kWorld)
                            p2 = fn_mesh.getPoint(vi2, om.MSpace.kWorld)

                            offset1 = (camera_pos - p1).normalize()
                            offset2 = (camera_pos - p2).normalize()

                            # そのままだとポリゴンに半分埋まっているのでカメラ側に少しオフセットする
                            p1 += offset1 * cameraOffset * lineWidth
                            p2 += offset2 * cameraOffset * lineWidth

                            newData.lines.append((p1, p2))

                            it_edge.next()

            else:
                newData.lines = []

            return newData

        else:
            return None

    def addUIDrawables(self, objPath, drawManager, frameContext, data):
        """描画処理

        Args:
            objPath (_type_): _description_
            drawManager (_type_): _description_
            frameContext (_type_): _description_
            data (_type_): _description_
        """
        if data:
            if data.lines:
                points = om.MPointArray([p for line in data.lines for p in line])

                drawManager.beginDrawable()
                drawManager.setColor(data.lineColor)
                drawManager.setLineWidth(data.lineWidth)
                drawManager.lineList(points, False)
                drawManager.endDrawable()

        return True

    @staticmethod
    def creator(obj):
        return PreviewObjectSetOverride(obj)


def initializePlugin(obj):
    mplugin = om.MFnPlugin(obj, "NNPlugins", "1.0", "Any")

    try:
        mplugin.registerNode(
            PreviewObjectSet.kPluginNodeTypeName,
            PreviewObjectSet.NodeId,
            PreviewObjectSet.nodeCreator,
            PreviewObjectSet.nodeInitializer,
            om.MPxNode.kLocatorNode,
            PreviewObjectSet.classification
            )

        omr.MDrawRegistry.registerDrawOverrideCreator(
            PreviewObjectSet.classification,
            PreviewObjectSet.registrantId,
            PreviewObjectSetOverride.creator
            )

    except:
        sys.stderr.write("Failed to register node: %s" % PreviewObjectSet.kPluginNodeTypeName)
        raise


def uninitializePlugin(obj):
    mplugin = om.MFnPlugin(obj, "NNPlugins", "1.0", "Any")

    try:
        mplugin.deregisterNode(PreviewObjectSet.NodeId)

        omr.MDrawRegistry.deregisterDrawOverrideCreator(
            PreviewObjectSet.classification,
            PreviewObjectSet.registrantId
            )

    except:
        sys.stderr.write("Failed to deregister node: %s" % PreviewObjectSet.kPluginNodeTypeName)
        raise
