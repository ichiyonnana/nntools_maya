
"距離加重平均のウェイトスムース"
import re

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma


def smooth_weights(protect_zero=True, protect_one=False, distance_weighted=True, average_targets=None, normalize_targets=None):
    """ウェイトを隣接頂点のウェイトの平均に設定する

    Args:
        protect_zero (bool, optional): True で現在 0 のウェイトを 0 のまま維持する. Defaults to True.
        protect_one (bool, optional): True で現在 1 のウェイトを 1 のまま維持する. Defaults to False.
        distance_weighted (bool, optional): True で隣接エッジ長による加重平均にする. Defaults to True.
        average_targets (list[str], optional): 平均化するインフルエンスの名前のリスト. None なら全て.
        normalize_targets (list[str], optional): 正規化に使用するインフルエンスの名前のリスト. None なら全て.
    """
    selections = cmds.ls(selection=True, flatten=True)

    if not selections:
        return

    # スムース対象オブジェクトとそのコンポーネント
    target_objects = []
    target_vids = []

    # 選択モードにより対象オブジェクトとコンポーネントを取得
    if cmds.selectMode(q=True, object=True):
        for sel in selections:
            if cmds.objectType(sel, isType="transform") or cmds.objectType(sel, isType="mesh"):
                target_objects.append(sel)
                target_vids.append(None)

    elif cmds.selectMode(q=True, component=True):
        vertices = []
        if cmds.selectType(q=True, polymeshVertex=True):
            vertices = selections

        elif (cmds.selectType(q=True, polymeshEdge=True)
              or cmds.selectType(q=True, polymeshFace=True)
              or cmds.selectType(q=True, polymeshUV=True)):
            vertices = cmds.filterExpand(cmds.polyListComponentConversion(selections, toVertex=True), sm=31)

        # コンポーネントをオブジェクト毎に分類
        object_dict = dict()
        for vtx in sorted(vertices):
            obj, compstr = vtx.split(".")
            comp = int(re.search(r"\d+", compstr).group(0))
            object_dict[obj] = object_dict.get(obj, []) + [comp]

        for obj, comps in object_dict.items():
            target_objects.append(obj)
            target_vids.append(comps)

    # スムース処理
    for target_object, target_vids in zip(target_objects, target_vids):
        slist = om.MGlobal.getSelectionListByName(target_object)
        dag, comp = slist.getComponent(0)
        fn_mesh = om.MFnMesh(dag)

        skin_cluster = mel.eval(f"findRelatedSkinCluster {target_object}")

        if not skin_cluster:
            continue

        dg_skincluster = om.MGlobal.getSelectionListByName(skin_cluster).getDependNode(0)
        fn_skin = oma.MFnSkinCluster(dg_skincluster)

        # ウェイトの取得
        influences = fn_skin.influenceObjects()
        num_influences = len(influences)
        current_weights = fn_skin.getWeights(dag, om.MObject.kNullObj)[0]  # ウェイトのリスト｡ 頂点で全インフルエンスのウェイトがまとまっている [v1w1, v1w2, v1w3, v2w1, v2w2, v2w3] の形

        new_weights = om.MDoubleArray(current_weights)  # スムース後のウェイトを格納するリスト

        # 頂点 ID ペア -> エッジ長 の辞書を作成
        positions = fn_mesh.getPoints()
        edge_length_dict = dict()
        for eid in range(fn_mesh.numEdges):
            vid_pair = fn_mesh.getEdgeVertices(eid)
            length = (positions[vid_pair[0]] - positions[vid_pair[1]]).length()
            key = tuple(sorted(vid_pair))
            edge_length_dict[key] = length

        # 頂点毎の処理
        vitr = om.MItMeshVertex(dag)
        while not vitr.isDone():
            vid = vitr.index()

            if target_vids and vid not in target_vids:
                vitr.next()
                continue

            weight_slice = slice(num_influences*vid, num_influences*(vid+1))  # 該当頂点のウェイトを取得するスライス
            neighbor_vids = vitr.getConnectedVertices()  # 隣接頂点ID

            total_edge_length = sum([edge_length_dict[tuple(sorted([vid, nvid]))] for nvid in neighbor_vids])

            # 隣接頂点のウェイトを取得して加算
            for neighbor_vid in neighbor_vids:
                neighbor_weight_slice = slice(num_influences*neighbor_vid, num_influences*(neighbor_vid+1))  # 隣接頂点のウェイトを取得するスライス

                # エッジ長による重み付け
                if distance_weighted:
                    key = tuple(sorted([vid, neighbor_vid]))
                    distance_weight = total_edge_length / edge_length_dict[key]
                else:
                    distance_weight = 1.0

                # 隣接ウェイトの加算
                new_weights[weight_slice] = [nw + cw * distance_weight for nw, cw in zip(new_weights[weight_slice], current_weights[neighbor_weight_slice])]

            # ゼロ保護用のインフルエンスのマスク
            influence_zero_mask = [1.0 if w > 0.0 else 0.0 for w in current_weights[weight_slice]]
            influence_one_mask = [1.0 if w >= 0.9999 else 0.0 for w in current_weights[weight_slice]]

            if protect_zero:
                new_weights[weight_slice] = [nw * m for nw, m in zip(new_weights[weight_slice], influence_zero_mask)]

            # 平均化ターゲット以外のウェイトを元に戻す
            if average_targets is not None:
                # インフルエンス名からインデックス取得
                inf_names = [cmds.ls(inf, shortNames=True)[0] for inf in influences]
                avg_indices = [ii for ii, name in enumerate(inf_names) if name in average_targets]
                for ii, name in enumerate(inf_names):
                    if ii not in avg_indices:
                        # 平均化対象外は元のウェイトで上書き
                        for ii, name in enumerate(inf_names):
                            if ii not in avg_indices:
                                # 平均化対象外は元のウェイトで上書き
                                idx = num_influences * vid + ii
                                new_weights[idx] = current_weights[idx]

            # ウェイトの正規化
            total_weight = sum(new_weights[weight_slice])
            new_weights[weight_slice] = [w / total_weight for w in new_weights[weight_slice]]

            if protect_one:
                if any(influence_one_mask):
                    new_weights[weight_slice] = influence_one_mask

            vitr.next()

        # ウェイトの設定
        all_influences = om.MIntArray(list(range(len(fn_skin.influenceObjects()))))
        fn_comp = om.MFnSingleIndexedComponent()
        all_vtx_comp = fn_comp.create(om.MFn.kMeshVertComponent)
        fn_comp.addElements(list(range(fn_mesh.numVertices)))
        da_weights = om.MDoubleArray(new_weights)

        # ウェイトの設定
        # TODO: API用にスナップショット
        fn_skin.setWeights(dag, all_vtx_comp, all_influences, da_weights)
        # TODO: API用にスナップショット
