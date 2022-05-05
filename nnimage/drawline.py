#! python
# coding:utf-8

import math

import nnimage.pixel as ni
import nnimage.bmp as bmp

reload(ni)
reload(bmp)

black = ni.Pixel(0, 0, 0, 255)
red = ni.Pixel(255, 0, 0, 255)

image = bmp.Bitmap(width=1024, height=1024, r=255, g=255, b=255, a=255)

p1 = ni.Point((100, 100))
p2 = ni.Point((300, 200))

r1 = ni.Point((500,500))
r2 = ni.Point((501,501))

for i in range(5000):
    ni.draw_rect(image, r1, r2, red)
    ni.draw_line(image, p1, p2, red)

image.save("E:/_temp/test.bmp")

print("finish")
