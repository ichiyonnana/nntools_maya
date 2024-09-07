import maya.mel as mel
import maya.cmds as cmds

def main():
    input = ""

    ret = cmds.promptDialog(
        title = "delete all custumscript",
        message = "input YES",
        tx  = "",
        button = "OK",
        cancelButton = "Cancel",
        defaultButton = "Cancel",
        dismissString = "Cancel")

    if ret == "OK":
        input = cmds.promptDialog(q=True, text=True)
        if input == "YES":
            command_list = mel.eval("runTimeCommand -q -userCommandArray")

            for cmd_name in command_list:
                print(cmd_name)
                mel.eval("runTimeCommand -e -delete %(cmd_name)s" % locals())

            print("Deleted")
    else:
        print("Canceled")