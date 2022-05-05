#! python
# coding:utf-8

class Point:
    def __init__(self, coords=None):
        if coords:
            self.x = float(coords[0])
            self.y = float(coords[1])

        else:
            self.x = 0.0
            self.y = 0.0


class Pixel:
    def __init__(self, r=0, g=0, b=0, a=1):
        self.r = r
        self.g = g
        self.b = b
        self.a = a


def draw_line(image, p1, p2, color):
    if color is None:
        color = Pixel(0, 0, 0, 255)

    x_slope = (p2.y - p1.y) / (p2.x - p1.x)  # x に対する y の変化
    y_slope = (p2.x - p1.x) / (p2.y - p1.y)  # y に対する x の変化

    if abs(x_slope) < abs(y_slope):
        for i, x in enumerate(range(int(p1.x), int(p2.x))):
            y = p1.y + x_slope * i
            image.set_pixel(x, y, color)
    else:
        for i, y in enumerate(range(int(p1.y), int(p2.y))):
            x = p1.x + y_slope * i
            image.set_pixel(x, y, color)


def draw_rect(image, p1, p2, color):
    min_x = int(min(p1.x, p2.x))
    max_x = int(max(p1.x, p2.x))
    min_y = int(min(p1.y, p2.y))
    max_y = int(max(p1.y, p2.y))

    for x in range(min_x, max_x+1):
        for y in range(min_y, max_y+1):
            image.set_pixel(x, y, color)

