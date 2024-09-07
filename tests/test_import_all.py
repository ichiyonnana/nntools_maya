"""パッケージ内の全てのモジュールをインポートするテスト。mayapy.exe で実行する。"""
import importlib
from pathlib import Path
import sys
import unittest


class TestNNTools(unittest.TestCase):
    def test_import_all(self):
        """サブパッケージ含めて全てのモジュールをインポートする"""

        # テスト対象パス
        test_path = Path(__file__).absolute().parent.parent

        # 環境パス追加
        sys.path.append(str(test_path))

        # 全pyファイル
        python_files = [x for x in test_path.rglob('*.py') if "__init__.py" not in x.name]

        # インポートの成功失敗の統計
        for file_path in python_files:
            relative_path = file_path.relative_to(test_path)
            module_name = str(relative_path).replace("\\", ".").replace(".py", "")

            with self.subTest(module_name=module_name):
                try:
                    importlib.import_module(module_name)
                    self.assertTrue(True)

                except Exception:
                    self.assertTrue(False, f"Module '{module_name}' failed to import")


if __name__ == "__main__":
    # Maya の初期化
    import maya.standalone
    maya.standalone.initialize("python")

    # テスト実行
    unittest.main()
