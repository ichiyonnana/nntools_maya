import subprocess


def main():
    encoding = "sjis"
    cmd = """wmic process where "name = 'Photoshop.exe'" get commandline"""
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)

    if result:
        ps_path = result.stdout.decode(encoding).split("\r\r\n")[1].replace('"', '')

    else:
        raise

    jsx_path = r"E:\Dropbox\src\mayapython\nntools_maya\nnps\test.jsx"

    cmd = f'''"{ps_path}" -r "{jsx_path}"'''

    print(cmd)
    subprocess.run(cmd)
