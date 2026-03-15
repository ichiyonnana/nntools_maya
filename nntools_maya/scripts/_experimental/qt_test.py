from PySide2 import QtWidgets, QtCore, QtGui, QtUiTools
import maya.OpenMayaUI as omui
import shiboken2

# Mayaのメインウィンドウを取得する関数
def getMayaMainWindow():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return shiboken2.wrapInstance(int(main_window_ptr), QtWidgets.QWidget)

# .uiファイルを動的に読み込み、UIを表示する関数
def showUiDialog():
    ui_file_path = r"E:\Dropbox\src\mayapython\nntools_maya\_misc\test.ui"  # .uiファイルの絶対パスを指定
    
    # QtUiTools.QUiLoader を使って .ui ファイルを読み込み
    loader = QtUiTools.QUiLoader()
    file = QtCore.QFile(ui_file_path)
    
    if not file.open(QtCore.QFile.ReadOnly):
        print(f"Error: Unable to open file {ui_file_path}")
        return
    
    # UIをロードしてウィジェットを作成
    ui_widget = loader.load(file)
    file.close()
    
    if ui_widget is None:
        print("Error: Failed to load the UI.")
        return

    # ウィジェットのスタイルや親設定を調整
    if isinstance(ui_widget, QtWidgets.QWidget):
        # ウィジェットを直接表示
        ui_widget.setParent(getMayaMainWindow())
        ui_widget.setWindowTitle("My Dynamic UI")
        ui_widget.setWindowFlags(QtCore.Qt.Window)  # タイトルバーを表示
        ui_widget.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowTitleHint | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowCloseButtonHint)
        ui_widget.setFixedSize(400, 300)  # 幅400px、高さ300pxのウィンドウに固定
        

        # listView を取得
        list_view = ui_widget.findChild(QtWidgets.QListView, 'listView')
        
        # アイテムを追加するモデルの作成
        model = QtGui.QStandardItemModel()
        for i in range(3):
            item = QtGui.QStandardItem(f"Item {i + 1}")
            model.appendRow(item)
        
        # QListView にモデルを設定
        list_view.setModel(model)

        # コンテキストメニューの作成
        def show_context_menu(point):
            index = list_view.indexAt(point)
            if not index.isValid():
                return

            menu = QtWidgets.QMenu()
            for option in ['A', 'B', 'C']:
                action = menu.addAction(option)
                # lambda 関数を引数なしに修正
                action.triggered.connect(lambda item=index.data(), opt=option: on_menu_action_triggered(item, opt))
            
            menu.exec_(list_view.viewport().mapToGlobal(point))

        # メニュー項目が選択されたときの処理
        def on_menu_action_triggered(item_text, option):
            print(f"Item right clicked: {item_text} {option}")

        # 右クリックでコンテキストメニューを表示
        list_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        list_view.customContextMenuRequested.connect(show_context_menu)

        ui_widget.show()
    else:
        print("Error: The loaded UI is not a QWidget.")

# ダイアログを表示
showUiDialog()
