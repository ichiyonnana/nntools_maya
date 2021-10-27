# coding:utf-8

import maya.cmds as cmds
import functools


# 実際にリピート呼び出される関数情報
_function_to_repeat = None
_args = None
_kwargs = None


def _do_repeat():
    """ リピート用コールバック関数 """
    if _function_to_repeat:
        _function_to_repeat(*_args, **_kwargs)


def repeatable(function):
    """ リピート用デコレーター """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        global _function_to_repeat
        global _args
        global _kwargs
        _function_to_repeat = function
        _args = args
        _kwargs = kwargs
        python_code = "import %s as repeatable_decorator;repeatable_decorator._do_repeat();" % __name__
        callback_command = 'python("' + python_code + '")'

        ret = function(*args, **kwargs)

        try:
            cmds.repeatLast(addCommand=callback_command, addCommandLabel=function.__name__)

        except:
            print("repeatLast failure")
        
        return ret

    return wrapper
