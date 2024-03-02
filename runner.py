#! python
# coding:utf-8
""""カレントディレクトリ以下の全ての unittest を実行する"""
import os
import re
import subprocess
import winreg

MSG_MAYA_NOT_FOUND = ".ma 拡張子の関連付けから maya.exe を特定することが出来ませんでした｡"


def get_associated_exe_path(extension):
    """拡張子に関連付けられた実行コマンドを取得する"""
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, extension) as key:
            file_type, _ = winreg.QueryValueEx(key, "")

            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{file_type}\\shell\\open\\command") as exe_key:
                exe_path, _ = winreg.QueryValueEx(exe_key, "")

                return exe_path

    except Exception as e:
        print(f"Error: {e}")

        return None


# .ma の関連付けから maya.exe のパスを取得
maya_exe_path = get_associated_exe_path(".ma")

if maya_exe_path:
    m = re.search(r"[A-Z]:.+maya\.exe", maya_exe_path)

    if m:
        # subprocess.run 用の引数構築
        maya_bin_dir = os.path.dirname(m.group(0))
        mayapy_path = maya_bin_dir + "/mayapy.exe"
        script_dir = os.path.dirname(__file__)
        run_args = [mayapy_path, "-m", "unittest", "discover", "-s", script_dir]

        # コマンドを実行
        result = subprocess.run(run_args, capture_output=True, text=True)
        print("StdOut:", result.stdout)
        print("StdErr:", result.stderr)

    else:
        print(MSG_MAYA_NOT_FOUND)

else:
    print(MSG_MAYA_NOT_FOUND)
