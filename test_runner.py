""""カレントディレクトリ以下の全ての unittest を実行する。mayapy ではなく通常の Python で実行する。"""
import os
import re
import subprocess
import winreg

MSG_MAYA_NOT_FOUND = ".ma 拡張子の関連付けから maya.exe のパスを特定することが出来ませんでした｡"


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


def main():
    # .ma の関連付けから maya.exe のパスを取得
    maya_exe_path = get_associated_exe_path(".ma")

    # Maya が見つからなかった場合は終了
    if not maya_exe_path:
        print(MSG_MAYA_NOT_FOUND)
        return

    m = re.search(r"[A-Z]:.+maya\.exe", maya_exe_path)

    # Maya のパスが特定できなかった場合は終了
    if not m:
        print(MSG_MAYA_NOT_FOUND)
        return

    # subprocess.run 用の引数構築
    maya_bin_dir = os.path.dirname(m.group(0))
    mayapy_path = maya_bin_dir + "/mayapy.exe"
    script_dir = os.path.dirname(__file__)
    run_args = [mayapy_path, "-m", "unittest", "discover", "-s", script_dir]

    # コマンドを実行
    # テスト対象コード内の外部コマンド等で 非UTF-8 の出力があるとキャプチャ結果が None になるのでいったんバイナリモードで受け取ってからエラー無視してデコードする
    result = subprocess.run(run_args, capture_output=True)
    print("StdOut:", result.stdout.decode("utf-8", errors="replace"))
    print("StdErr:", result.stderr.decode("utf-8", errors="replace"))


if __name__ == "__main__":
    main()
