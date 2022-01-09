#! python
# coding:utf-8

import sys
import maya.api.OpenMaya as om2


# コマンド名
kPluginCmdName = "userCommand1"


def maya_useNewAPI():
    """プラグインが API2.0 ベースであることの明示"""
    pass


class TestCommandClass(om2.MPxCommand):
    """コマンドクラス"""
    def __init__(self):
        om2.MPxCommand.__init__(self)

    def doIt(self, args):
        """実行時の処理"""
        self.parseArguments(args)
        self.redoIt()

    def parseArguments(self, args):
        """引数の解析"""
        # TODO: 実装

        # 引数オブジェクト
        argData = om2.MArgParser(self.syntax(), args)

        # リスト引数の処理
        weights = []
        num = argData.numberOfFlagUses('-w')
        for i in range(num):
            pos = argData.getFlagArgumentPosition('-w', i)
            argsList = argData.getFlagArgumentList('-w', i)
            weights.append(argsList.asDouble(0))

        # 単一引数の処理
        if argData.isFlagSet('-nm'):
            normalize = argData.flagArgumentBool('-nm', 0)

        # メンバ変数に保持
        self.weights = weights
        self.normalize = normalize

    def redoIt(self):
        """Redo時の処理"""
        pass

    def undoIt(self):
        """Undo時の処理"""
        pass

    def isUndoable(self):
        """Undo可能ならTrueを返す"""
        return True


def cmdCreator():
    """コマンドのクラスを返す"""
    return TestCommandClass()


def syntaxCreator():
    """引数の構成を設定したシンタックスオブジェクトを返す"""
    # TODO: 実装

    # シンタックスオブジェクト
    syntax = om2.MSyntax()

    # 単一整数
    syntax.addFlag('-v', '-value', om2.MSyntax.kInt)

    # 実数配列
    syntax.addFlag('-w', '-weights', om2.MSyntax.kDouble)
    syntax.makeFlagMultiUse('-w')

    # ブール
    syntax.addFlag('-nm', '-normalize', om2.MSyntax.kBoolean)

    return syntax


def initializePlugin(mobject):
    """プラグインを有効にした際の処理"""
    # プラグインオブジェクト
    mplugin = om2.MFnPlugin(mobject)

    # 登録
    try:
        mplugin.registerCommand(kPluginCmdName, cmdCreator, syntaxCreator)

    except:
        sys.stderr.write('Failed to register command: ' + kPluginCmdName)


def uninitializePlugin(mobject):
    """プラグインを無効にした際の処理"""
    # プラグインオブジェクト
    mplugin = om2.MFnPlugin(mobject)

    # 削除
    try:
        mplugin.deregisterCommand(kPluginCmdName)

    except:
        sys.stderr.write('Failed to unregister command: ' + kPluginCmdName)
