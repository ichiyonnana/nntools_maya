"""Maya 内から pip でパッケージをユーザーインストールするスクリプト。"""
import sys
import subprocess
import os

import nnutil.ui as ui


def pip_user_install(package_name):
    # 実行中の Maya が使用する mayapy.exe のパスを取得
    maya_path = sys.executable
    maya_dir = os.path.dirname(maya_path)
    mayapy_path = os.path.join(maya_dir, "mayapy.exe")

    # numpy をユーザーインストール
    install_command = [mayapy_path, "-m", "pip", "install", "--user", package_name]
    result = subprocess.run(install_command, capture_output=True, text=True)

    print("Standard Output:")
    print(result.stdout)

    print("Standard Error:")
    print(result.stderr)


def main():
    package_name = ui.input_dialog(title="pip install", message="パッケージ名を入力してください")

    if package_name:
        pip_user_install(package_name)


if __name__ == "__main__":
    main()
