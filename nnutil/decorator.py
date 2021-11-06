# coding:utf-8

import datetime
import functools

import maya.cmds as cmds


def undo_chunk(function):
    """ Undo チャンク用デコレーター """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        cmds.undoInfo(ock=True)
        ret = function(*args, **kwargs)
        cmds.undoInfo(cck=True)
        return ret

    return wrapper


def timer(function):
    """時間計測デコレーター"""
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        start = datetime.datetime.today()
        ret = function(*args, **kwargs)
        end = datetime.datetime.today()
        delta = (end - start)
        sec = delta.seconds + delta.microseconds/1000000.0
        print('time(sec): ' + str(sec) + " " + str(function))
        return ret

    return wrapper


def no_warning(function):
    """警告抑止デコレーター"""
    def wrapper(*args, **kwargs):
        warning_flag = cmds.scriptEditorInfo(q=True, suppressWarnings=True)
        info_flag = cmds.scriptEditorInfo(q=True, suppressInfo=True)
        cmds.scriptEditorInfo(e=True, suppressWarnings=True, suppressInfo=True)
        ret = function(*args, **kwargs)
        cmds.scriptEditorInfo(e=True, suppressWarnings=warning_flag, suppressInfo=info_flag)
        return ret

    return wrapper


# リピートデコレーター用関数情報
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
