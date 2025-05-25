import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

def get_weight():
    # 選択オブジェクトの取得
    selections = cmds.ls(selection=True, type="transform")

    # オブジェクト毎の処理
    for obj in selections:
        # メッシュとスキンクラスター取得
        mesh_name = cmds.listRelatives(obj, shapes=True)[0]
        skincluster_name = cmds.listConnections(mesh_name, destination=True, type="skinCluster")[0]

        # API 用オブジェクト
        skincluster = om.MGlobal.getSelectionListByName(skincluster_name).getDependNode(0)
        fn_skincluster = oma.MFnSkinCluster(skincluster)
        obj = om.MGlobal.getSelectionListByName(mesh_name).getDagPath(0)
        comp = om.MObject.kNullObj

        # ウェイトの取得
        da_weights, num_influence = fn_skincluster.getWeights(obj, comp)

        # ウェイトをインフルエンス毎にリスト分割 (このコードでは未使用)
        influence_names = [x.partialPathName() for x in fn_skincluster.influenceObjects()]
        weight_list_each_influence = dict()
        for influence_index in range(num_influence):
            weight_list_each_influence[influence_names[influence_index]] = []

        for i in range(0, len(da_weights), num_influence):
            for influence_index in range(num_influence):
                weight_list_each_influence[influence_names[influence_index]].append(da_weights[i+influence_index])

        print(weight_list_each_influence)

        # 頂点コンポーネントMObject. 要素追加なしで全要素
        # setWeights は om.MObject.kNullObj 不可
        fn_single_idx_comp = om.MFnSingleIndexedComponent()
        vtx_components = fn_single_idx_comp.create(om.MFn.kMeshVertComponent)

        # 全頂点･特定インフルエンス上書き
        fn_skincluster.setWeights(obj, vtx_components, 0, 1.0, normalize=True)

        # 全頂点･全インフルエンス再設定
        influences = om.MIntArray(list(range(num_influence)))  # list だとシグネチャ誤判定するので MIntArray 必須
        fn_skincluster.setWeights(obj, vtx_components, influences, da_weights, normalize=True)


def store_weight_with_position(vtx_comps):
    obj_name = cmds.polyListComponentConversion(vtx_comps[0])

    positions = get_positions(obj_name)
    weights = get_weights(obj_name)

    return positions, weights


def restore_weight_with_position(vtx_comps, stored_positions, stored_weights, min_threshold):
    obj_name = cmds.polyListComponentConversion(vtx_comps[0])

    # インフルエンスに差があれば追加する


    current_positions
    current_weight
    new_weights

    #頂点毎の処理
        # 近い頂点を探索しインデックス取得
        nearest_index
        nearest_weight

        # ウェイトの上書き
        new_weights[i:i+num_influence] = weights[i:i+num_influence]

        
    set_weights(obj_name, new_weight)
