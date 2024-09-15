import maya.cmds as cmds
import maya.mel as mel

import nnutil.core as nu


class BoundingBox():
    def init(self, x=0, y=0, z=0, w=0, h=0, d=0):
        self.x = x
        self.y = y
        self.z = z
        self.w = w
        self.h = h
        self.d = d

        return self

    def from_obj(self, obj):
        self.w = obj.boundingBoxMaxX.get() - obj.boundingBoxMinX.get()
        self.h = obj.boundingBoxMaxY.get() - obj.boundingBoxMinY.get()
        self.d = obj.boundingBoxMaxZ.get() - obj.boundingBoxMinZ.get()

        self.x = (obj.boundingBoxMaxX.get() + obj.boundingBoxMinX.get())/2
        self.y = (obj.boundingBoxMaxY.get() + obj.boundingBoxMinY.get())/2
        self.z = (obj.boundingBoxMaxZ.get() + obj.boundingBoxMinZ.get())/2

        return self

    def from_obj_ws(self, obj):
        dup = cmds.duplicate(obj)[0]
        cmds.parent(dup, None)

        self.w = dup.boundingBoxMaxX.get() - dup.boundingBoxMinX.get()
        self.h = dup.boundingBoxMaxY.get() - dup.boundingBoxMinY.get()
        self.d = dup.boundingBoxMaxZ.get() - dup.boundingBoxMinZ.get()

        self.x = (dup.boundingBoxMaxX.get() + dup.boundingBoxMinX.get())/2
        self.y = (dup.boundingBoxMaxY.get() + dup.boundingBoxMinY.get())/2
        self.z = (dup.boundingBoxMaxZ.get() + dup.boundingBoxMinZ.get())/2

        cmds.delete(dup)

        return self

    def __str__(self):
        return "{} {} {} {} {} {}".format(self.x, self.y, self.z, self.w, self.h, self.d)


axis_x = (1, 0, 0)
axis_y = (0, 1, 0)
axis_z = (0, 0, 1)


def unit_cube(axis=axis_y):
    return cmds.polyCube(w=1, h=1, d=1, sx=1, sy=1, sz=1, ax=axis, cuv=4, ch=1)[0]


def unit_cylinder(axis=axis_y):
    return cmds.polyCylinder(r=0.5, h=1, sx=8, sy=1, sz=1, ax=axis, rcp=0, cuv=3, ch=1)[0]


def unit_sphere(axis=axis_y):
    return cmds.polySphere(r=0.5, sx=8, sy=8, ax=axis, cuv=2, ch=1)[0]


def unit_plane(axis=axis_y):
    return cmds.polyPlane(w=1, h=1, sx=1, sy=1, ax=axis, cuv=2, ch=1)[0]


def replace_cube(obj, axis=axis_y):
    replace_obj(obj, unit_cube(axis=axis))


def replace_cylinder(obj, axis=axis_y):
    replace_obj(obj, unit_cylinder(axis=axis))


def replace_sphere(obj, axis=axis_y):
    replace_obj(obj, unit_sphere(axis=axis))


def replace_plane(obj, axis=axis_y):
    replace_obj(obj, unit_plane(axis=axis))


def replace_obj(obj1, obj2):
    b1 = BoundingBox().from_obj_ws(obj1)
    b2 = BoundingBox().from_obj_ws(obj2)

    sx = None
    sy = None
    sz = None

    if b1.w != 0:
        sx = b1.w / b2.w

    if b1.h != 0:
        sy = b1.h / b2.h

    if b1.d != 0:
        sz = b1.d / b2.d

    if not sx:
        if sy and sz:
            sx = min(sy, sz)
        else:
            sx = 1

    if not sy:
        if sx and sz:
            sy = min(sx, sz)
        else:
            sy = 1

    if not sz:
        if sx and sy:
            sz = min(sx, sy)
        else:
            sz = 1

    name = obj1.name()
    parent = obj1.getParent()

    cmds.delete(obj1)

    obj2.translate.set((b1.x, b1.y, b1.z))
    obj2.scale.set((sx, sy, sz))

    cmds.rename(obj2, name)
    cmds.parent(obj2, parent)


selections = cmds.ls(selection=True)

if selections:
    for obj in selections:
        replace_cube(obj, axis=axis_x)
else:
    mel.eval("PencilCurveTool")
