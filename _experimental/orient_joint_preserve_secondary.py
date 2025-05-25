import maya.cmds as cmds
import maya.api.OpenMaya as om


def orient_joint_preserve_secondary(primary="x", secondary="y"):
    """選択されたすべてのジョイントを対象に､ジョイントの補助軸を保持したままジョイントの主軸の向きを変更する｡

    Args:
        primary (str, optional): 主軸｡子を向く. Defaults to "x".
        secondary (str, optional): 補助軸｡主軸回りの方向が維持される. Defaults to "y".
    """
    # バリデーションチェック
    valid_axes = ["x", "y", "z"]
    if primary not in valid_axes or secondary not in valid_axes:
        raise ValueError("Invalid axis. Please specify 'x', 'y', or 'z'.")

    if primary == secondary:
        raise ValueError("Primary and secondary axes cannot be the same.")

    # 選択ジョイントを全て取得して､深度順にソート
    joints = cmds.ls(selection=True, type="joint", long=True)
    joints.sort(key=lambda x: x.count("|"), reverse=True)

    if not joints:
        raise ValueError("Please select a joint.")

    # 全てのジョイントに対して反復
    for joint in joints:
        # 子の取得｡無ければスキップ
        child = (cmds.listRelatives(joint) or [None])[0]

        if not child:
            continue

        # ジョイントとその子の位置を取得
        joint_pos = om.MVector(cmds.xform(joint, q=True, t=True, ws=True))
        child_pos = om.MVector(cmds.xform(child, q=True, t=True, ws=True))

        current_joint_matrix = cmds.xform(joint, q=True, m=True, ws=True)
        current_child_matrix = cmds.xform(child, q=True, m=True, ws=True)

        # 現在のジョイントの補助軸のベクトルを取得
        if secondary == "x":
            current_basis_2 = om.MVector(current_joint_matrix[0:3])

        if secondary == "y":
            current_basis_2 = om.MVector(current_joint_matrix[4:7])

        if secondary == "z":
            current_basis_2 = om.MVector(current_joint_matrix[8:11])

        # 新しい基底ベクトルを計算
        new_basis_1 = (child_pos - joint_pos).normalize()
        new_basis_3 = (new_basis_1 ^ current_basis_2).normalize()
        new_basis_2 = (new_basis_1 ^ -new_basis_3).normalize()

        # 新しいジョイントの行列を作成
        new_matrix = [0] * 16

        if primary == "x" and secondary == "y":
            new_matrix[0:3] = list(new_basis_1)
            new_matrix[4:7] = list(new_basis_2)
            new_matrix[8:11] = list(new_basis_3)

        elif primary == "x" and secondary == "z":
            new_matrix[0:3] = list(new_basis_1)
            new_matrix[4:7] = list(-new_basis_3)
            new_matrix[8:11] = list(new_basis_2)

        elif primary == "y" and secondary == "x":
            new_matrix[0:3] = list(new_basis_2)
            new_matrix[4:7] = list(new_basis_1)
            new_matrix[8:11] = list(-new_basis_3)

        elif primary == "y" and secondary == "z":
            new_matrix[0:3] = list(new_basis_3)
            new_matrix[4:7] = list(new_basis_1)
            new_matrix[8:11] = list(new_basis_2)

        elif primary == "z" and secondary == "x":
            new_matrix[0:3] = list(new_basis_2)
            new_matrix[4:7] = list(new_basis_3)
            new_matrix[8:11] = list(new_basis_1)

        elif primary == "z" and secondary == "y":
            new_matrix[0:3] = list(new_basis_3)
            new_matrix[4:7] = list(new_basis_2)
            new_matrix[8:11] = list(-new_basis_1)

        new_matrix[12:15] = list(joint_pos)
        new_matrix[15] = 1.0

        # ジョイントの行列を更新し､子の行列を復帰する
        cmds.xform(joint, m=new_matrix, ws=True)
        cmds.xform(child, m=current_child_matrix, ws=True)

        # rotation を orient に移す
        cmds.makeIdentity(joint, apply=True, t=False, r=True, s=False, n=False, pn=True)
        cmds.makeIdentity(child, apply=True, t=False, r=True, s=False, n=False, pn=True)
