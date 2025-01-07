"""プラグインを作成せずに API 経由でのデータ編集を Undo/Redo するためのモジュール。

API による Undo 不可能な編集の前後で snapshot() を呼び、必要な情報を保存する。
"""
import os
import maya.cmds as cmds


def snapshot(*args, **kwargs):
    """指定したオブジェクトの法線や頂点座標を保存する。Undo/Redo 時は復元を行う。

    Args:
        targets (lsit[str]): 情報を保存するオブジェクトの名前
        normal (bool, option): True で法線を保存する
        position (bool, option): True で頂点座標を保存する
        color (bool, option): True で頂点カラーを保存する
        smooth (bool, option): True でソフトエッジ/ハードエッジを保存する
    """
    cmds.snapshotState(*args, **kwargs)
