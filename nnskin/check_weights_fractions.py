import maya.cmds as cmds
import maya.mel as mel


# 修正処理
def fix_command():
    print("dummy_fix_command")


def main(model_root_grp=None, min_unit=0.01, fast_mode=True):

    selections = cmds.ls(selection=True, flatten=True)
    objects = None

    if len(selections) != 0:
        objects = selections
    else:
        if model_root_grp:
            objects = cmds.listRelatives(model_root_grp)
        else:
            print("no target")

    fraction_objs = []
    fraction_comp = []

    for obj in objects:
        sc = mel.eval('findRelatedSkinCluster %(obj)s' % locals())
        if sc == "":
            next
        else:
            print("check %s" % obj)

            cmds.select(obj)
            cmds.ConvertSelectionToVertices()
            vertices = cmds.ls(selection=True, flatten=True)

            has_fraction = False

            for vtx in vertices:
                weights = cmds.skinPercent(sc, vtx, q=True, v=True)

                for w in weights:
                    f1 = (w % min_unit)
                    f2 = min_unit - f1
                    f = min(f1, f2)
                    t = 0.00000000000001  # 無視する浮動小数誤差
                    fraction_is_too_small = (f < t)

                    if not fraction_is_too_small:
                        has_fraction = True
                        fraction_comp.append(vtx)

                if fast_mode and has_fraction:
                    break

            if has_fraction:
                fraction_objs.append(obj)

    message = ""

    if len(fraction_objs) == 0:
        message = "OK"
        cmds.select(clear=True)
        cmds.SelectToggleMode()
        cmds.confirmDialog(title='has weight fractions', message=message)

    else:
        cmds.SelectToggleMode()
        cmds.select(fraction_comp)
        message = u"ウェイトに%(min_unit)s以下の値が使われています\n\n" % locals() + ", ".join(fraction_objs)
        ret = cmds.confirmDialog(title=u"ウェイト少数チェック", message=message, button=["Fix","Cancel"], defaultButton="Fix", cancelButton="Cancel", dismissString="Cancel")

        if (ret == "Fix"):
            fix_command()


if __name__ == "__main__":
    main()
