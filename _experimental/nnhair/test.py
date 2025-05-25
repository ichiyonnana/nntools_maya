import maya.cmds as cmds
import maya.api.OpenMaya as om


def main():
    inner_mesh = "NNHM_inner"
    slist = om.MGlobal.getSelectionListByName(inner_mesh)
    obj, comp = slist.getComponent(0)
    fn_inner_mesh = om.MFnMesh(obj)

    outer_mesh = "NNHM_outer"
    slist = om.MGlobal.getSelectionListByName(outer_mesh)
    obj, comp = slist.getComponent(0)
    fn_outer_mesh = om.MFnMesh(obj)

    curves = cmds.ls("NNHC_*", type="nurbsCurve")

    for curve in curves:
        slist = om.MGlobal.getSelectionListByName(curve)
        obj, comp = slist.getComponent(0)
        fn_curve = om.MFnNurbsCurve(obj)

        num_cv = fn_curve.numCVs
        positions = fn_curve.cvPositions()

        # 現在のカーブ始点の最近傍点の座標とそのUV
        inner_position, fid = fn_inner_mesh.getClosestPoint(positions[0])
        u, v, fid = fn_inner_mesh.getUVAtPoint(inner_position)
        u %= 1.0
        v %= 1.0

        # 外側メッシュで UV が一致する点の座標
        num_face = fn_outer_mesh.numPolygons

        outer_position = None

        for fi in range(num_face):
            try:
                outer_position = fn_outer_mesh.getPointAtUV(fi, u, v, space=om.MSpace.kWorld, tolerance=1e-5)
                break

            except RuntimeError:
                pass

        if outer_position:
            new_positions = [None] * num_cv

            for i in range(num_cv):
                alpha = i / (num_cv-1)
                new_positions[i] = om.MPoint(om.MVector(inner_position) * (1-alpha) + om.MVector(outer_position) * alpha)

            fn_curve.setCVPositions(new_positions)

            fn_curve.updateCurve()
        else:
            print(f"{curve}: not found point corresponding")
