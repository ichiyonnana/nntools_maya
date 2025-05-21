import os

try:
    # プラグインパスの追加
    new_path = os.path.dirname(__file__) + "/plug-ins"
    current_paths = os.getenv("MAYA_PLUG_IN_PATH", "")
    os.environ["MAYA_PLUG_IN_PATH"] = current_paths + ";" + new_path

except Exception as e:
    print(e)
