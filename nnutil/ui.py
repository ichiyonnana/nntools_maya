# coding:utf-8
"""
UI 操作周りのヘルパー
https://help.autodesk.com/cloudhelp/2020/JPN/Maya-Tech-Docs/CommandsPython/cat_Windows.html
http://www.not-enough.org/abe/manual/maya/pymel-quick.html
"""
import re

import pymel.core as pm
import pymel.core.nodetypes as nt

window_width = 300
header_width = 50
color_x = (1.0, 0.5, 0.5)
color_y = (0.5, 1.0, 0.5)
color_z = (0.5, 0.5, 1.0)
color_joint = (0.5, 1.0, 0.75)
color_select = (0.5, 0.75, 1.0)
bw_single = 24
bw_double = bw_single*2 + 2

button_width_auto = -1
button_width1 = 24
button_width2 = button_width1*2 + 2
button_width3 = button_width1*3 + 4
button_width4 = button_width1*4 + 6
button_width5 = button_width1*5 + 8
button_width6 = button_width1*6 + 10
button_width7 = button_width1*7 + 12


def any_handler(*args):
    """ 未指定の時に使用する何もしないハンドラ
    """
    pass


def get_component_type(component):
    """ [pm] コンポーネントの種類を取得する

    Args:
        component (PyNode): [description]

    Returns:
        type: [description]
    """
    return type(component)


def ui_func(component):
    """ [pm] UIコンポーネントの種類から操作用コマンドを取得する

    Args:
        component ([type]): [description]

    Returns:
        [type]: [description]
    """
    # TODO: クラスにする
    handle_method = {
        pm.uitypes.FloatField: [pm.floatField, "v"],
        pm.uitypes.IntField: [pm.intField, "v"],
        pm.uitypes.CheckBox: [pm.checkBox, "v"],
        pm.uitypes.Button: [pm.button, "v"],
        pm.uitypes.IntSlider: [pm.intSlider, "v"],
        pm.uitypes.FloatSlider: [pm.floatSlider, "v"],
        pm.uitypes.Text: [pm.text, "l"],
    }

    return handle_method[get_component_type(component)]


def decide_width(word):
    """ 文字列から UI コンポーネントの段階的な幅を計算する
    """
    actual_width = 0

    if len(word) <= 2:
        actual_width = button_width1
    elif len(word) <= 8:
        actual_width = button_width2
    elif len(word) < 14:
        actual_width = button_width3
    else:
        actual_width = button_width4

    return actual_width


def column_layout():
    return pm.columnLayout()


def row_layout(numberOfColumns=16):
    return pm.rowLayout(numberOfColumns=numberOfColumns)


def end_layout():
    pm.setParent("..")


def header(label):
    return pm.text(label=label, width=header_width)


def text(label="", width=button_width_auto):
    actual_width = width

    if width == button_width_auto:
        actual_width = decide_width(label)

    return pm.text(label=label, width=actual_width)


def button(label, width=button_width_auto, c=any_handler, dgc=any_handler):
    actual_width = width

    if width == button_width_auto:
        actual_width = decide_width(label)

    component = pm.button(l=label, c=c, dgc=dgc, width=actual_width)

    return component


def float_slider(min=0, max=1, value=0, step=0.1, width=bw_double, dc=any_handler, cc=any_handler):
    component = pm.floatSlider(min=min, max=max, value=value, step=step, width=width, dc=dc, cc=cc)

    return component


def int_slider(min=0, max=1, value=0, step=0.1, width=bw_double, dc=any_handler, cc=any_handler):
    component = pm.intSlider(min=min, max=max, value=value, step=step, width=width, dc=dc, cc=cc)

    return component


def eb_float(v=0, en=True, dc="", width=bw_double):
    return pm.floatField(v=v, en=en, dc=dc, width=bw_double)


def eb_int(v=0, en=True, dc="", width=bw_double):
    return pm.intField(v=v, en=en, dc=dc, width=bw_double)


def separator(width=window_width):
    return pm.separator(width=window_width)


def check_box(label="", v=False, cc=any_handler):
    return pm.checkBox(label=label, v=v, cc=cc)


def get_value(component):
    func, argname = ui_func(component)
    return func(component, q=True, **{argname: True})


def set_value(component, value):
    func, argname = ui_func(component)
    return func(component, e=True, **{argname: value})


def set_availability(component, stat):    
    func, argname = ui_func(component)

    return func(component, e=True, en=stat)


def enable_ui(component):
    set_availability(component, True)


def disable_ui(component):
    set_availability(component, False)


def hud_slider():        
    def myHudSlider(state, hud):
        val = pm.hudSlider(hud, q=True, value=True)
        print(state, val)
        
    id = pm.hudSlider('myHudSlider', 
                      section=1, 
                      block=2, 
                      visible=True, 
                      label='myHudButton', 
                      type='int', 
                      value=0, 
                      minValue=-10, maxValue=10, 
                      labelWidth=80, valueWidth=50, 
                      sliderLength=100, 
                      sliderIncrement=1, 
                      pressCommand=pm.Callback(myHudSlider, 'press', 'myHudSlider'), 
                      dragCommand=pm.Callback(myHudSlider, 'drag', 'myHudSlider'), 
                      releaseCommand=pm.Callback(myHudSlider, 'release', 'myHudSlider')
                      )
    return id