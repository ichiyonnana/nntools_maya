"""
UI 操作周りのヘルパー
https://help.autodesk.com/cloudhelp/2020/JPN/Maya-Tech-Docs/CommandsPython/cat_Windows.html
http://www.not-enough.org/abe/manual/maya/pymel-quick.html
"""
import re
import ctypes

from . import windows_vk as vk

import pymel.core as pm
import pymel.core.nodetypes as nt


window_width = 300
header_width = 50
color_default = (0.35, 0.35, 0.35)
color_x = (1.0, 0.5, 0.5)
color_y = (0.5, 1.0, 0.5)
color_z = (0.5, 0.5, 1.0)
color_u = (1.0, 0.6, 0.7)
color_v = (0.7, 0.6, 1.0)
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


def width(n):
    return width1 * n + 2 * (n-1)


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


def height(n):
    return height1 * n + 2 * (n-1)


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
        pm.uitypes.TextField: [pm.textField, "text"],
        pm.uitypes.OptionMenu: [pm.optionMenu, "v"],
    }

    return handle_method[get_component_type(component)]


def decide_width(word, with_icon=False):
    """ 文字列から UI コンポーネントの段階的な幅を計算する
    """
    actual_width = 0

    if with_icon:
        if len(word) <= 2:
            actual_width = button_width2
        elif len(word) <= 8:
            actual_width = button_width3
        elif len(word) < 14:
            actual_width = button_width4
        else:
            actual_width = button_width5

    else:
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


def header(label="", *args, **kwargs):
    return pm.text(label=label, width=header_width, *args, **kwargs)


def text(label="", width=button_width_auto, *args, **kwargs):
    actual_width = width

    if width == button_width_auto:
        actual_width = decide_width(label)

    return pm.text(label=label, width=actual_width, *args, **kwargs)


def button(label, icon=None, width=button_width_auto, height=height1, bgc=color_default, c=any_handler, dgc=any_handler, *args, **kwargs):
    actual_width = width

    if width == button_width_auto:
        actual_width = decide_width(label, with_icon=bool(icon))

    if icon:
        component = pm.iconTextButton(l=label, image1=icon, style="iconAndTextHorizontal", bgc=bgc, c=c, dgc=dgc, width=actual_width, height=height, *args, **kwargs)
    else:
        component = pm.button(l=label, c=c, dgc=dgc, width=actual_width, height=height, bgc=bgc, *args, **kwargs)

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


def int_slider(min=0, max=1, value=0, step=1, width=button_width2, dc=any_handler, cc=any_handler, *args, **kwargs):
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


def eb_text(text="", en=True, cc=any_handler, width=width2, *args, **kwargs):
    """[summary]

    Args:
        text (str, optional): [description]. Defaults to "".
        en (bool, optional): [description]. Defaults to True.
        cc ([type], optional): [description]. Defaults to any_handler.
        width ([type], optional): [description]. Defaults to width2.
    """
    return pm.textField(text=text, en=en, cc=cc, width=width, *args, **kwargs)


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


def option_menu(label, items, bsp=any_handler, cc=any_handler, width=button_width2, *args, **kwargs):
    component = pm.optionMenu(label=label, bsp=bsp, cc=cc)
    
    for item in items:
        pm.menuItem(label=item)

    return component


def delete_all_items(ui_object):
    """optionMenu のアイテムを全て削除する."""
    pm.optionMenu(ui_object, e=True, deleteAllItems=True)


def add_items(ui_object, items):
    """指定の optionMenu にアイテムを追加する."""
    for item in items:
        pm.menuItem(label=item, parent=ui_object)

def replace_items(ui_object, items, keep_selection=True):
    """指定の optionMenu のアイテムを全て置き換える.
    
    置き換え後のアイテムに置き換え前に選択されていたアイテムと同一の物があれば選択を維持する｡
    """
    selected_value = pm.optionMenu(ui_object, q=True, value=True)

    delete_all_items(ui_object=ui_object)
    add_items(ui_object=ui_object, items=items)

    if keep_selection and selected_value in items:
        pm.optionMenu(option_menu, e=True, value=selected_value)


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


def is_key_pressed(keycode):
    """キーが押し下げられているかどうか｡

    仮想キーの定数はこのモジュールに定義されている｡ A キーは vk.VK_A

    Args:
        keycode (int): Windows の仮想キーコード
    """
    GetAsyncKeyState = ctypes.windll.user32.GetAsyncKeyState
    return bool(GetAsyncKeyState(keycode) & 0x8000)


def input_dialog(title="title", message=""):
    """インプットダイアログの表示

    Args:
        title (str, optional): タイトルの文字列. Defaults to "".
        message (str, optional): ダイアログのメッセージ. Defaults to "".

    Returns:
        str or None: ユーザーが入力した文字列を返す｡未入力やキャンセル時は None を返す
    """
    BTL_OK = "OK"
    BTL_CANCEL = "Cancel"

    result = pm.promptDialog(
            title=title,
            message=message,
            button=[BTL_OK, BTL_CANCEL],
            defaultButton=BTL_OK,
            cancelButton=BTL_CANCEL,
            dismissString=BTL_CANCEL)

    if result == BTL_OK:
        text = pm.promptDialog(query=True, text=True)

        if text == "":
            return None
        else:
            return text
    else:
        return None


def yes_no_dialog(title="title", message=""):
    """Yes/No ダイアログの表示

    Args:
        title (str, optional): タイトルの文字列. Defaults to "".
        message (str, optional): ダイアログのメッセージ. Defaults to "".

    Returns:
        bool or None: Yes が押されたら True, No が押されたら False, ダイアログがキャンセルされたら None を返す
    """
    BTL_YES = "Yes"
    BTL_NO = "No"
    BTL_CANCEL = "Cancel"

    result = pm.confirmDialog(title=title, message=message, button=[BTL_YES, BTL_NO, BTL_CANCEL])

    if result == BTL_YES:
        return True
    elif result == BTL_NO:
        return False
    else:
        return None


def ok_dialog(title="title", message=""):
    """メッセージダイアログの表示

    Args:
        title (str, optional): タイトルの文字列. Defaults to "".
        message (str, optional): ダイアログのメッセージ. Defaults to "".
    """
    pm.confirmDialog(title=title, message=message, button="OK")


class ListDialog:
    """リストアイテムを選択するダイアログ

    以下のように使用する
    ret = ListDialog.create(title="list dialog", message="select item", items=text_list)
    """
    list_ui = None

    def __init__(self):
        pass

    @classmethod
    def return_index(cls, *args):
        """"""

        indices = pm.textScrollList(ListDialog.list_ui, q=True, selectIndexedItem=True)

        if indices:
            pm.layoutDialog(dismiss=str(indices[0]-1))
        else:
            pm.layoutDialog(dismiss="Cancel")

    @classmethod
    def create(cls, title="", message="", items=None):
        """引数で指定したリストの要素を textScrollList として表示し"""

        def checkboxPrompt(title=title, message=message, items=items):
            form = pm.setParent(q=True)
            pm.formLayout(form, e=True, width=300)

            # UIコントロール作成
            label_message_text = pm.text(l=message)
            list_ui = pm.textScrollList(append=items, height=200)
            button_ok = pm.button(l='OK', c=ListDialog.return_index)
            button_cancel = pm.button(l='Cancel', c='pm.layoutDialog(dismiss="Cancel")')

            ListDialog.list_ui = list_ui

            # オフセット量
            spacer = 5
            top = 5
            edge = 5

            # ダイアログへのアンカー配置
            attachForm = [
                (label_message_text, 'top', top),
                (label_message_text, 'left', edge),
                (label_message_text, 'right', edge),
                (list_ui, 'left', edge),
                (list_ui, 'right', edge),
                (button_ok, 'left', edge),
                (button_cancel, 'right', edge),
                ]

            # アンカー配置せずフリーになる方向
            attachNone = [
                (label_message_text, 'bottom'),
                (list_ui, 'bottom'),
                (button_ok, 'bottom'),
                (button_cancel, 'bottom'),
                ]

            # コントロールにアタッチするUIと方向
            attachControl = [
                (list_ui, 'top', spacer, label_message_text),
                (button_ok, 'top', spacer, list_ui),
                (button_cancel, 'top', spacer, list_ui),
                ]

            # 指定したアンカーからの距離
            attachPosition = [
                (button_ok, 'right', spacer, 33),
                (button_cancel, 'left', spacer, 33),
                ]

            pm.formLayout(
                form,
                edit=True,
                attachForm=attachForm,
                attachNone=attachNone,
                attachControl=attachControl,
                attachPosition=attachPosition)

        ret = pm.layoutDialog(ui=checkboxPrompt)

        if ret != "Cancel":
            return int(ret)

        else:
            return None
