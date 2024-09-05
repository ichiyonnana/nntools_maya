"""API の Undo/Redo 用プラグイン"""

import sys
import inspect

import maya.api.OpenMaya as om


# TODO: クラス名修正
class Hoge(om.MPxCommand):
    """コマンドクラス"""
    # TODO: コマンド名修正
    command_name = "hoge"

    def __init__(self):
        om.MPxCommand.__init__(self)

        # メンバ・コマンドフラグ用変数の初期化
        # TODO: 実装
        self.test_list = []
        self.is_active_test_option = False

    def doIt(self, args):
        """実行時の処理"""
        # TODO: 実装
        # 引数の解析
        self.parseArguments(args)

        pass

    def parseArguments(self, args):
        """引数の解析"""
        # TODO: 実装

        # 引数オブジェクト
        argData = om.MArgParser(self.syntax(), args)

        # リスト引数サンプル
        self.test_list = []
        num_list = argData.numberOfFlagUses('-t')
        for i in range(num_list):
            # flag_pos = argData.getFlagArgumentPosition('-t', i)
            argsList = argData.getFlagArgumentList('-t', i)
            self.test_list.append(argsList.asString(0))

        # オプションフラグサンプル
        if argData.isFlagSet('-n'):
            self.is_active_test_option = argData.flagArgumentBool('-n', 0)

    def redoIt(self):
        """Redo時の処理"""
        # 実装
        pass

    def undoIt(self):
        """Undo時の処理"""
        # 実装
        pass

    def isUndoable(self):
        """Undo可能ならTrueを返す"""
        return True

    @staticmethod
    def cmdCreator():
        """コマンドのクラスを返す"""
        # TODO: クラス名修正
        return Hoge()

    @staticmethod
    def syntaxCreator():
        """引数の構成を設定したシンタックスオブジェクトを返す"""
        # TODO: 実装

        # シンタックスオブジェクト
        syntax = om.MSyntax()

        # リスト引数サンプル
        syntax.addFlag('-t', '-targets', om.MSyntax.kString)
        syntax.makeFlagMultiUse('-t')

        # オプションフラグサンプル
        syntax.addFlag('-n', '-normal', om.MSyntax.kBoolean)

        return syntax

    @classmethod
    def register(cls, mplugin):
        try:
            mplugin.registerCommand(cls.command_name, cls.cmdCreator, cls.syntaxCreator)

        except:
            sys.stderr.write('Failed to register command: ' + cls.command_name)

    @classmethod
    def unregister(cls, mplugin):
        try:
            mplugin.deregisterCommand(cls.command_name)

        except:
            sys.stderr.write('Failed to unregister command: ' + cls.command_name)


# モジュール内のすべての MPxCommand 派生クラス
classes = [x for x in locals().copy().values() if inspect.isclass(x) and issubclass(x, om.MPxCommand) and x != om.MPxCommand]


def maya_useNewAPI():
    """プラグインを生成させるための宣言 + API2.0 ベースであることの明示"""
    pass


def initializePlugin(mobject):
    """プラグインを有効にした際の処理"""
    # プラグインオブジェクト
    mplugin = om.MFnPlugin(mobject)

    # 登録
    for c in classes:
        c.register(mplugin)


def uninitializePlugin(mobject):
    """プラグインを無効にした際の処理"""
    # プラグインオブジェクト
    mplugin = om.MFnPlugin(mobject)

    # 削除
    for c in classes:
        c.unregister(mplugin)
