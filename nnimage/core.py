#! python
# coding:utf-8

import struct
import sys
import decimal


def quantize(r):
    return int((r * 2 + 1) // 2)


class Point:
    def __init__(self, coords=None):
        if coords:
            self.x = float(coords[0])
            self.y = float(coords[1])

        else:
            self.x = 0.0
            self.y = 0.0

    def __add__(self, p):
        return Point((self.x + p.x, self.y + p.y))

    def __sub__(self, p):
        return Point((self.x - p.x, self.y - p.y))

    def __neg__(self):
        return Point((-self.x, -self.y))

    def __str__(self):
        return "(%s, %s)" % (self.x, self.y)

    def x_slope(self):
        # x に対する y の変化
        if self.x == 0:
            return sys.float_info.max
        else:
            return self.y / self.x

    def y_slope(self):
        # y に対する x の変化
        if self.y == 0:
            return sys.float_info.max
        else:
            return self.x / self.y


class Pixel:

    def __init__(self, r=0, g=0, b=0, a=1):
        self.r = r
        self.g = g
        self.b = b
        self.a = a


black = Pixel(0, 0, 0, 255)
white = Pixel(255, 255, 255, 255)
red = Pixel(255, 0, 0, 255)
yellow = Pixel(255, 255, 0, 255)
green = Pixel(0, 255, 0, 255)
cyan = Pixel(0, 255, 255, 255)
blue = Pixel(0, 0, 255, 255)
magenta = Pixel(255, 0, 255, 255)


class Image:
    def __init__(self, width, height, r=0, g=0, b=0, a=255):
        self.width = int(width)
        self.height = int(height)
        self.pixels = [None] * self.width * self.height

        for i in range(len(self.pixels)):
            self.pixels[i] = Pixel(r=r, g=g, b=b, a=a)

    def get_pixel(self, x, y):
        qx = quantize(x)
        qy = quantize(y)
        if qx < 0 or self.width <= qx or qy < 0 or self.height <= qy:
            return None
        else:
            return self.pixels[qy * self.width + qx]

    def set_pixel(self, x, y, pixel):
        qx = quantize(x)
        qy = quantize(y)
        if qx < 0 or self.width <= qx or qy < 0 or self.height <= qy:
            pass
        else:
            self.pixels[qy * self.width + qx] = pixel

    def save_bmp(self, filepath):
        with open(filepath, "wb") as f:
            # ファイルヘッダ 14B
            f.write(b"BM")  # type 2B
            f.write(struct.pack("<I", 54 + self.width * self.height * 4))  # size 4B
            f.write(struct.pack("<H", 0))  # reserved1 2B
            f.write(struct.pack("<H", 0))  # reserved2 2B
            f.write(struct.pack("<I", 54))  # offset 4B

            # 情報ヘッダ 40B
            f.write(struct.pack("<I", 40))  # 情報ヘッダサイズ 4B
            f.write(struct.pack("<I", self.width))  # 幅 4B
            f.write(struct.pack("<I", self.height))  # 高さ 4B
            f.write(struct.pack("<H", 1))  # プレーン数 2B
            f.write(struct.pack("<H", 32))  # 色ビット深度 2B
            f.write(struct.pack("<I", 0))  # 圧縮形式 4B
            f.write(struct.pack("<I", self.width * self.height * 4))  # 画像データサイズ 4B
            f.write(struct.pack("<I", 0))  # 水平解像度 4B
            f.write(struct.pack("<I", 0))  # 垂直解像度 4B
            f.write(struct.pack("<I", 0))  # 格納パレット数 4B
            f.write(struct.pack("<I", 0))  # 重要色数 4B

            # 画像データ
            for p in self.pixels:
                f.write(struct.pack("<B", p.b))
                f.write(struct.pack("<B", p.g))
                f.write(struct.pack("<B", p.r))
                f.write(struct.pack("<B", p.a))

            # ファイルが 4 の倍数バイトになるようパディング
            f.write(struct.pack("<B", 0))
            f.write(struct.pack("<B", 0))


def draw_line(image, p1, p2, color):
    if color is None:
        color = Pixel(0, 0, 0, 255)

    # x に対する y の変化
    x_slope = (p2 - p1).x_slope()

    # y に対する x の変化
    y_slope = (p2 - p1).y_slope()

    if abs(x_slope) < abs(y_slope):
        less = min(int(p1.x), int(p2.x))
        greater = max(int(p1.x), int(p2.x))
        for i, x in enumerate(range(less, greater)):
            y = p1.y + x_slope * i
            image.set_pixel(x, y, color)
    else:
        less = min(int(p1.y), int(p2.y))
        greater = max(int(p1.y), int(p2.y))
        for i, y in enumerate(range(less, greater)):
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
