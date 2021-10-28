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
button_width1_5 = int(button_width1*1.5 + 1)
button_width2 = button_width1*2 + 2
button_width3 = button_width1*3 + 4
button_width4 = button_width1*4 + 6
button_width5 = button_width1*5 + 8
button_width6 = button_width1*6 + 10
button_width7 = button_width1*7 + 12

width_auto = -1

width0 = 0
width0_5 = 12
width1 = 24
width1_5 = int(width1*1.5 + 1)
width2 = width1*2 + 2
width3 = width1*3 + 4
width4 = width1*4 + 6
width5 = width1*5 + 8
width6 = width1*6 + 10
width7 = width1*7 + 12

height0 = 0
height0_5 = 12
height1 = 24
height1_5 = int(height1*1.5 + 1)
height2 = height1*2 + 2
height3 = height1*3 + 4
height4 = height1*4 + 6
height5 = height1*5 + 8
height6 = height1*6 + 10
height7 = height1*7 + 12


def any_handler(*args):
    """ 未指定の時に使用する何もしないハンドラ
    """
    pass


def get_component_type(component):
    """ [pm] コンポーネントの種類を取得する

    現状は type() を返すだけ｡

    Args:
        component (PyNode): 種類を調べる UI コンポーネントオブジェクト

    Returns:
        type: component の型
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
        pm.uitypes.RadioButton: [pm.radioButton, "sl"],
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


def column_layout(*args, **kwargs):
    return pm.columnLayout(*args, **kwargs)


def row_layout(numberOfColumns=16, *args, **kwargs):
    return pm.rowLayout(numberOfColumns=numberOfColumns, *args, **kwargs)


def end_layout():
    pm.setParent("..")


def header(label, *args, **kwargs):
    return pm.text(label=label, width=header_width, *args, **kwargs)


def text(label="", width=button_width_auto, *args, **kwargs):
    actual_width = width

    if width == button_width_auto:
        actual_width = decide_width(label)

    return pm.text(label=label, width=actual_width, *args, **kwargs)


def button(label, width=button_width_auto, c=any_handler, dgc=any_handler, *args, **kwargs):
    actual_width = width

    if width == button_width_auto:
        actual_width = decide_width(label)

    component = pm.button(l=label, c=c, dgc=dgc, width=actual_width, *args, **kwargs)

    return component


def float_slider(min=0, max=1, value=0, step=0.1, width=button_width2, dc=any_handler, cc=any_handler, *args, **kwargs):
    """[summary]

    Args:
        min (int, optional): [description]. Defaults to 0.
        max (int, optional): [description]. Defaults to 1.
        value (int, optional): [description]. Defaults to 0.
        step (float, optional): [description]. Defaults to 0.1.
        width ([type], optional): [description]. Defaults to button_width2.
        dc (function, optional): スライド操作した際のハンドラー. Defaults to any_handler.
        cc (function, optional): 値を変更した際のハンドラー. Defaults to any_handler.

    Returns:
        [type]: [description]
    """
    component = pm.floatSlider(min=min, max=max, value=value, step=step, width=width, dc=dc, cc=cc, *args, **kwargs)

    return component


def int_slider(min=0, max=1, value=0, step=0.1, width=button_width2, dc=any_handler, cc=any_handler, *args, **kwargs):
    """[summary]

    Args:
        min (int, optional): [description]. Defaults to 0.
        max (int, optional): [description]. Defaults to 1.
        value (int, optional): [description]. Defaults to 0.
        step (float, optional): [description]. Defaults to 0.1.
        width ([type], optional): [description]. Defaults to button_width2.
        dc (function, optional): スライド操作した際のハンドラー. Defaults to any_handler.
        cc (function, optional): 値を変更した際のハンドラー. Defaults to any_handler.

    Returns:
        [type]: [description]
    """
    component = pm.intSlider(min=min, max=max, value=value, step=step, width=width, dc=dc, cc=cc, *args, **kwargs)

    return component


def eb_float(v=0, en=True, cc=any_handler, dc=any_handler, width=button_width2, *args, **kwargs):
    """[summary]

    Args:
        v (int, optional): [description]. Defaults to 0.
        en (bool, optional): [description]. Defaults to True.
        cc (function, optional): 値を変更した際のハンドラー. Defaults to any_handler.
        dc (function, optional): スライド操作した際のハンドラー. Defaults to any_handler.
        width ([type], optional): [description]. Defaults to button_width2.

    Returns:
        [type]: [description]
    """
    return pm.floatField(v=v, en=en, cc=cc, dc=dc, width=width, *args, **kwargs)


def eb_int(v=0, en=True, cc=any_handler, dc=any_handler, width=button_width2, *args, **kwargs):
    """[summary]

    Args:
        v (int, optional): [description]. Defaults to 0.
        en (bool, optional): [description]. Defaults to True.
        cc (function, optional): 値を変更した際のハンドラー. Defaults to any_handler.
        dc (function, optional): スライド操作した際のハンドラー. Defaults to any_handler.
        width ([type], optional): [description]. Defaults to button_width2.

    Returns:
        [type]: [description]
    """
    return pm.intField(v=v, en=en, cc=cc, dc=dc, width=width, *args, **kwargs)


def separator(width=window_width, *args, **kwargs):
    return pm.separator(width=width, *args, **kwargs)


def spacer(width=width1, *args, **kwargs):
    return pm.text(label="", width=width, *args, **kwargs)


def spacer_v(height=3, *args, **kwargs):
    row_layout()
    comp = pm.text(label="", height=height, *args, **kwargs)
    end_layout()

    return comp


def check_box(label="", v=False, cc=any_handler, *args, **kwargs):
    return pm.checkBox(label=label, v=v, cc=cc, *args, **kwargs)


def radio_collection(*args, **kwargs):
    return pm.radioCollection(*args, **kwargs)


def radio_button(label, width=button_width2, *args, **kwargs):
    return pm.radioButton(label=label, width=width, *args, **kwargs)


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


def is_shift():
    """ Shift キーが押されているときに True """
    return bool(pm.getModifiers() & 1)


def is_ctrl():
    """ Ctrl キーが押されているときに True """
    return bool(pm.getModifiers() & 4)


def is_alt():
    """ Alt キーが押されているときに True """
    return bool(pm.getModifiers() & 8)
