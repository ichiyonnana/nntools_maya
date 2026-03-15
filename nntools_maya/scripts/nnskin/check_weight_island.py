"""ウェイトが非ゼロの領域が連続しているかを調べるスクリプト"""
import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma


def delete_non_deformer_history(mesh):
    """
    指定されたメッシュのノンデフォーマーヒストリーを削除する

    Args:
        mesh (str): 対象メッシュ名
    """
    try:
        cmds.bakePartialHistory(mesh, prePostDeformers=True)
    except Exception as e:
        print(f"ノンデフォーマーヒストリー削除エラー ({mesh}): {e}")


def check_weight_islands_for_mesh(mesh, target_influences=None):
    """
    指定されたメッシュの各インフルエンスについて、
    ウェイトが非ゼロの領域が連続しているかどうかを調べる

    Args:
        mesh (str): 調べるメッシュ名
        target_influences (list, optional): チェック対象のインフルエンスリスト（Noneの場合は全て）

    Returns:
        dict: {influence_name: island_count} の辞書
    """
    # 開始時にノンデフォーマーヒストリーを削除
    delete_non_deformer_history(mesh)

    # スキンクラスターを取得
    skin_clusters = cmds.ls(cmds.listHistory(mesh), type="skinCluster")
    if not skin_clusters:
        cmds.warning(f"{mesh} にスキンクラスターが見つかりません。")
        return {}

    skin_cluster = skin_clusters[0]
    influences = cmds.skinCluster(skin_cluster, query=True, influence=True)

    if not influences:
        cmds.warning(f"{mesh} にインフルエンスが見つかりません。")
        return {}

    # 対象インフルエンスの絞り込み
    if target_influences:
        influences = [inf for inf in influences if inf in target_influences]
        if not influences:
            cmds.warning("指定されたインフルエンスがスキンクラスターに存在しません。")
            return {}

    # APIオブジェクトを取得
    sel_list = om.MSelectionList()
    sel_list.add(skin_cluster)
    skin_cluster_obj = sel_list.getDependNode(0)
    skin_fn = oma.MFnSkinCluster(skin_cluster_obj)

    sel_list.clear()
    sel_list.add(mesh)
    mesh_dag_path = sel_list.getDagPath(0)

    # 全ウェイトを一括取得
    weights, influence_indices = skin_fn.getWeights(mesh_dag_path, om.MObject.kNullObj)
    all_influences = cmds.skinCluster(skin_cluster, query=True, influence=True)
    num_all_influences = len(all_influences)
    num_vertices = len(weights) // num_all_influences

    results = {}

    # 各インフルエンスについて調べる
    for inf_idx, influence in enumerate(influences):
        print(f"({inf_idx + 1}/{len(influences)}) {influence}")  # プログレス表示

        # 全インフルエンス中のインデックスを取得
        all_inf_idx = all_influences.index(influence)

        # このインフルエンスでウェイトが非ゼロの頂点インデックスを取得
        weighted_vertex_indices = []
        for vtx_idx in range(num_vertices):
            weight_idx = vtx_idx * num_all_influences + all_inf_idx
            if weights[weight_idx] > 0.0:
                weighted_vertex_indices.append(vtx_idx)

        if not weighted_vertex_indices:
            results[influence] = 0
            continue

        # ウェイトのある頂点をフェースに変換
        weighted_faces = []
        for vtx_idx in weighted_vertex_indices:
            vtx_component = f"{mesh}.vtx[{vtx_idx}]"
            faces = cmds.polyListComponentConversion(vtx_component, toFace=True)
            if faces:
                faces = cmds.filterExpand(faces, sm=34)
                if faces:
                    weighted_faces.extend(faces)

        # 重複を除去
        weighted_faces = list(set(weighted_faces))

        if not weighted_faces:
            results[influence] = 0
            continue

        # 専用UVセットを作成
        temp_uv_set = f"temp_weight_check_{inf_idx}"
        cmds.polyUVSet(mesh, create=True, uvSet=temp_uv_set)

        try:
            # フェースを選択してUVプロジェクション
            cmds.select(weighted_faces, replace=True)
            cmds.polyProjection(
                type='Planar',
                uvSetName=temp_uv_set,
                md='y'  # Y軸投影
            )

            # UVシェル数をカウント
            cmds.select(weighted_faces, replace=True)
            shells = cmds.polyEvaluate(uvShell=True, uvSetName=temp_uv_set)
            results[influence] = shells

        except Exception as e:
            print(f"エラー: {influence} の処理中にエラーが発生しました: {e}")
            results[influence] = 1

        finally:
            # UVセットを削除
            try:
                cmds.polyUVSet(mesh, delete=True, uvSet=temp_uv_set)

            except:
                pass

    # 終了時にノンデフォーマーヒストリーを削除
    delete_non_deformer_history(mesh)

    return results


def check_weight_islands(target_influences=None):
    """
    選択されたメッシュの各インフルエンスについて、
    ウェイトが非ゼロの領域が連続しているかを調べて結果を表示する

    Args:
        target_influences (list[str], optional): チェック対象のインフルエンスリスト（Noneの場合は全て）
    """
    selection = cmds.ls(selection=True, transforms=True)

    if not selection:
        cmds.warning("メッシュを選択してください。")
        return

    for obj in selection:
        # メッシュかどうか確認
        shapes = cmds.listRelatives(obj, shapes=True, type="mesh")
        if not shapes:
            cmds.warning(f"{obj} はメッシュではありません。")
            continue

        print(f"\n=== {obj} のウェイト島チェック ===")
        results = check_weight_islands_for_mesh(obj, target_influences)

        if not results:
            print("スキンクラスターまたはインフルエンスが見つかりません。")
            continue

        # 複数領域があるインフルエンスを収集
        problematic_influences = []
        for influence, island_count in results.items():
            if island_count > 1:
                problematic_influences.append(influence)

        # 結果を表示
        if problematic_influences:
            print("\n複数領域があるインフルエンス:")
            for influence in problematic_influences:
                print(influence)
        else:
            print("\n全てのインフルエンスで連続領域です。")

    cmds.select(selection, replace=True)  # 元の選択状態に戻す


if __name__ == "__main__":
    check_weight_islands()
