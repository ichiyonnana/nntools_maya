#! python
# coding:utf-8

import struct

from . import pixel as ni


class Bitmap:
    def __init__(self, width, height, r=0, g=0, b=0, a=255):
        self.width = int(width)
        self.height = int(height)
        self.pixels = [None] * self.width * self.height

        for i in range(len(self.pixels)):
            self.pixels[i] = ni.Pixel(r=r, g=g, b=b, a=a)

    def get_pixel(self, x, y):
        return self.pixels[int(y) * self.width + int(x)]

    def set_pixel(self, x, y, pixel):
        self.pixels[int(y) * self.width + int(x)] = pixel

    def save(self, filepath):
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
