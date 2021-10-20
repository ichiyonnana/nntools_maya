
#ラベル
  #UI
  self.l_hoge = cmds.text( label='ラベル名' )

#ボタン
  #UI
  self.bt_hoge = cmds.button(l='ラベル名', c=self.onHoge)


#実数
  #UI
  self.f_hoge = cmds.floatField(v=0.1, dc=self.onChangeLength1)

  #取得
  v =  cmds.floatField(self.f_hoge, q=True, v=True)

  #設定
  cmds.floatField(self.f_hoge, e=True, v=v)

#テキスト
  #UI
  self.ed_hoge = cmds.textField(tx='テキスト')

#チェックボックス
  #UI
  self.cb_hoge = cmds.checkBox(l='ラベル名', v=True, cc=self.onSetConst)

  #取得
  cmds.checkBox(self.cb_hoge, q=True, v=True)


#ラジオボタン


#サイズ
w  幅
h  高さ

#イベント
c   ボタンの左クリック
dgc ボタンの中クリック
dc  フィールドでドラッグしたとき
cc  フィールドが変更されたとき
ec  enter が押されたとき

#状態
ed true で有効