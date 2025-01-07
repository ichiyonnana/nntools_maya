"""プラグインを作成せずに API 経由でのデータ編集を Undo/Redo するためのモジュール。

snapshotStatePlugin.py のユーティリティモジュール｡コマンドを呼び出す関数とプラグインをロードする関数｡
API による Undo 不可能な編集の前後で snapshot() を呼び、必要な情報を保存する。
"""
import os
import maya.cmds as cmds

# undo/redo 用のプラグインロード
plugin_name = "snapshotStatePlugin.py"
cmds.loadPlugin(plugin_name)


class SnapshotStateWith(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        cmds.snapshotState(*self.args, **self.kwargs)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        cmds.snapshotState(*self.args, **self.kwargs)


def snapshot_state(*args, **kwargs):
    """指定したオブジェクトの法線や頂点座標を保存する。Undo/Redo 時は復元を行う。

    Args:
        targets (lsit[str]): 情報を保存するオブジェクトの名前
        normal (bool, option): True で法線を保存する
        position (bool, option): True で頂点座標を保存する
        color (bool, option): True で頂点カラーを保存する
        smooth (bool, option): True でソフトエッジ/ハードエッジを保存する
        weight (bool, option): True でウェイトを保存する
    """
    return SnapshotStateWith(*args, **kwargs)
