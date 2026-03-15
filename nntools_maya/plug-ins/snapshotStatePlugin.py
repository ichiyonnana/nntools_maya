"""API の Undo/Redo 用プラグイン"""

import sys

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma


# コマンド名
kPluginCmdName = "snapshotState"


def maya_useNewAPI():
    """プラグインが API2.0 ベースであることの明示"""
    pass


class SnapshotState(om.MPxCommand):
    """コマンドクラス"""
    def __init__(self):
        om.MPxCommand.__init__(self)

        self.targets = []
        self.to_store_normals = False
        self.to_store_positions = False
        self.to_store_colors = False
        self.to_store_smooths = False
        self.to_store_weights = False

    def doIt(self, args):
        """実行時の処理"""
        # 引数の解析
        self.parseArguments(args)

        # オブジェクトの状態を保存
        for target in self.targets:
            slist = om.MSelectionList()
            slist.add(target)
            dag = slist.getDagPath(0)
            fn_mesh = om.MFnMesh(dag)

            if self.to_store_smooths or self.to_store_normals:
                all_edge_ids = range(fn_mesh.numEdges)
                self.smooths = [fn_mesh.isEdgeSmooth(ei) for ei in all_edge_ids]

            if self.to_store_normals:
                self.normals = fn_mesh.getNormals()

            if self.to_store_positions:
                self.positions = fn_mesh.getPoints()

            if self.to_store_colors:
                self.colors = fn_mesh.getFaceVertexColors()

            if self.to_store_weights:
                slist = om.MGlobal.getSelectionListByName(target)
                dp_obj, comp = slist.getComponent(0)
                fn_mesh = om.MFnMesh(dp_obj)

                skin_cluster = mel.eval(f"findRelatedSkinCluster {target}")
                dg_skincluster = om.MGlobal.getSelectionListByName(skin_cluster).getDependNode(0)
                fn_skin = oma.MFnSkinCluster(dg_skincluster)

                self.weights = fn_skin.getWeights(dp_obj, om.MObject.kNullObj)[0]

    def parseArguments(self, args):
        """引数の解析"""

        # 引数オブジェクト
        argData = om.MArgParser(self.syntax(), args)

        # スナップショット対象オブジェクトの名前
        self.targets = []
        num_targets = argData.numberOfFlagUses('-t')
        for i in range(num_targets):
            # flag_pos = argData.getFlagArgumentPosition('-t', i)
            argsList = argData.getFlagArgumentList('-t', i)
            self.targets.append(argsList.asString(0))

        # スナップショットに含めるデータ
        if argData.isFlagSet('-n'):
            self.to_store_normals = argData.flagArgumentBool('-n', 0)

        if argData.isFlagSet('-p'):
            self.to_store_positions = argData.flagArgumentBool('-p', 0)

        if argData.isFlagSet('-c'):
            self.to_store_colors = argData.flagArgumentBool('-c', 0)

        if argData.isFlagSet('-sm'):
            self.to_store_smooths = argData.flagArgumentBool('-sm', 0)

        if argData.isFlagSet('-w'):
            self.to_store_weights = argData.flagArgumentBool('-w', 0)

    def _undo_redo(self):
        """Undo/Redo時の処理"""
        # オブジェクトの状態を復帰
        for target in self.targets:
            slist = om.MSelectionList()
            slist.add(target)
            dag = slist.getDagPath(0)
            fn_mesh = om.MFnMesh(dag)

            if self.to_store_smooths or self.to_store_normals:
                all_edge_ids = range(fn_mesh.numEdges)
                fn_mesh.setEdgeSmoothings(all_edge_ids, self.smooths)

            if self.to_store_normals:
                fn_mesh.setNormals(self.normals)

            if self.to_store_positions:
                fn_mesh.setPoints(self.positions)

            if self.to_store_colors:
                face_indices = om.MIntArray()
                vertex_indices = om.MIntArray()

                for i in range(fn_mesh.numPolygons):
                    polygon_vertices = fn_mesh.getPolygonVertices(i)
                    for j in polygon_vertices:
                        face_indices.append(i)
                        vertex_indices.append(j)

                fn_mesh.setFaceVertexColors(self.colors, face_indices, vertex_indices)

            if self.to_store_weights:
                skin_cluster = mel.eval(f"findRelatedSkinCluster {target}")
                dg_skincluster = om.MGlobal.getSelectionListByName(skin_cluster).getDependNode(0)
                fn_skin = oma.MFnSkinCluster(dg_skincluster)

                all_influences = om.MIntArray(list(range(len(fn_skin.influenceObjects()))))
                fn_comp = om.MFnSingleIndexedComponent()
                all_vtx_comp = fn_comp.create(om.MFn.kMeshVertComponent)
                fn_comp.addElements(list(range(fn_mesh.numVertices)))

                fn_skin.setWeights(dag, all_vtx_comp, all_influences, self.weights)

            fn_mesh.updateSurface()

    def redoIt(self):
        """Redo時の処理"""
        self._undo_redo()

    def undoIt(self):
        """Undo時の処理"""
        self._undo_redo()

    def isUndoable(self):
        """Undo可能ならTrueを返す"""
        return True


def cmdCreator():
    """コマンドのクラスを返す"""
    return SnapshotState()


def syntaxCreator():
    """引数の構成を設定したシンタックスオブジェクトを返す"""
    # TODO: 実装

    # シンタックスオブジェクト
    syntax = om.MSyntax()

    # 対象オブジェクト
    syntax.addFlag('-t', '-targets', om.MSyntax.kString)
    syntax.makeFlagMultiUse('-t')

    # ブール
    syntax.addFlag('-n', '-normal', om.MSyntax.kBoolean)
    syntax.addFlag('-p', '-position', om.MSyntax.kBoolean)
    syntax.addFlag('-c', '-color', om.MSyntax.kBoolean)
    syntax.addFlag('-sm', '-smooth', om.MSyntax.kBoolean)
    syntax.addFlag('-w', '-weight', om.MSyntax.kBoolean)

    return syntax


def initializePlugin(mobject):
    """プラグインを有効にした際の処理"""
    # プラグインオブジェクト
    mplugin = om.MFnPlugin(mobject)

    # 登録
    try:
        mplugin.registerCommand(kPluginCmdName, cmdCreator, syntaxCreator)

    except Exception:
        sys.stderr.write('Failed to register command: ' + kPluginCmdName)


def uninitializePlugin(mobject):
    """プラグインを無効にした際の処理"""
    # プラグインオブジェクト
    mplugin = om.MFnPlugin(mobject)

    # 削除
    try:
        mplugin.deregisterCommand(kPluginCmdName)

    except Exception:
        sys.stderr.write('Failed to unregister command: ' + kPluginCmdName)
