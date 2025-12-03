#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
O_noderの実行ファイル
"""

__author__ = 'Muto Tao'
__version__ = '0.3.0'
__date__ = '2025.12.2'

import sys
import time
import os.path
import datetime
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from flask import Flask, render_template, jsonify
import threading

from IO import IO
from Drawer import Drawer


# ドライブ上のファイルの識別ID
IDS = {
    # フォームID(フォーム編集画面のURL https://docs.google.com/forms/d/xxxxxxxxxxxx/edit の xxxxxxxxxxxx の部分)
    'partic_form' : '1G_WnVP-tendDUTvtHpT58wkFxFyq46WjG4Lqx4S9Spw',

    # スプレッドシートID（シート編集画面のURL https://docs.google.com/spreadsheets/d/xxxxxxxxxxxx/edit の xxxxxxxxxxxx の部分）
    'raw_answers' : '1VImFfuvKOqnXYdU8mDVrmC3_-Idfp5KeG2FzIe1aCAg',
    'datasheets' : '13xKhT9Vz0Bcs2xTrIGk_0aanLmuv5eYyUODjYLE92sY',
}

# raw_answers内のシートの識別ID
RAW_SHEET = "Form_responses"

# datasheets内のシートの識別ID
SHEET_NAMES = {
    "partic" : "partic_info",
    "net" : "net_info"
    # "form" : "form_src"
}

# partic_formのフォーム構成用の質問の識別ID
QUESTIONS = {
    'name' : "0100d475",  
    'prof_image' : "6f45dcdb",
    'friends' : "6525c455"
}

# partic_formの回答用の質問の識別ID
ANSWERS = {
    'name' : "7157132c",  
    'prof_image' : "2737d529",
    'friends' : "1cfca697"
}

NETWORK_DATA_FILE_PATH = "./../src/network_data/network_data.json"  # ネットワーク情報を保存するローカルファイルのpath
FILE_PATHS = {
    'net': "./../src/network_data/network_data.json",  # ネットワーク情報を保存するローカルファイルのpath
    'prof': "./static/images/"  # プロフィール画像を保存するローカルディレクトリのpath
}
FILE_NAMES = {
    'token' : 'token.json',
    'credentials' : 'credentials.json',
    'no_friends_img' : "0_No friends / なし",  # participants_formのネットワーク情報の質問の初期選択肢
    'no_image_img' : "NoImage.jpg"
}

SCOPES = [
    'https://www.googleapis.com/auth/drive.file',  # このアプリで使用する Google ドライブ上の特定のファイルのみの参照、編集、作成、削除
    'https://www.googleapis.com/auth/drive.metadata.readonly',  # このアプリが作成したわけではないGoogle ドライブ上の特定のファイルの参照
    'https://www.googleapis.com/auth/forms.body',  # Googleフォームのすべてのフォームの参照、編集、作成、削除
    'https://www.googleapis.com/auth/forms.responses.readonly',  # Googleフォームのフォームに対するすべての回答の参照
    'https://www.googleapis.com/auth/spreadsheets'  # Googleスプレッドシートのすべてのスプレッドシートの参照、編集、作成、削除
    ]

CREDS: None

app = Flask(__name__)

drawer: Drawer = None
an_io: IO = None

background_check_interval = 10  # 新しい回答のチェックを1度行った後次の更新まで最低何秒間を開けるか。


def init():
    """
    実行環境を構築する関数。
    ・ファイル構成を整える。
    ・認証情報を取得する。
    """

    global CREDS
    CREDS = None
    
    # トークン取得
    if os.path.exists(FILE_NAMES['token']):  # すでに認証済みでトークンがある場合はそれを読み込む
        CREDS = Credentials.from_authorized_user_file(FILE_NAMES['token'], SCOPES)
    
    if not CREDS or not CREDS.valid: # 認証情報がない、または無効な場合はログイン画面を表示
        if CREDS and CREDS.expired and CREDS.refresh_token:
            try:
                CREDS.refresh(Request())
            except:
                CREDS = None
        
        else:
            flow = InstalledAppFlow.from_client_secrets_file(FILE_NAMES['credentials'], SCOPES)
            CREDS = flow.run_local_server(port=0)
        
        # 次回以降のためにトークンを保存
        with open(FILE_NAMES['token'], 'w') as token:
            token.write(CREDS.to_json())


def check_updates_loop():
    """
    バックグラウンドで常に新しい回答がないかチェックし、あればデータを更新して、Drawerを再構築する関数
    """
    global drawer
    
    while True:
        # print(f"\rCheck update: {datetime.datetime.now()}", end="") # 現在時刻表示（ログ用）。ログが多すぎると見づらいので適宜調整

        try:
            # 新規回答があるかチェック
            if an_io.call_new_answers() > 0:
                # 1. データベース（スプレッドシート・ローカルファイル）を更新
                an_io.update_databese()
                
                # 2. 更新されたローカルファイルを読み込み直す。
                with open(FILE_PATHS['net'], 'r', encoding='utf-8') as f:
                    new_data = json.load(f)
                
                # 3. Drawerを作り直して、最新のグラフデータをメモリ上に用意する（これにより、次にブラウザが /data にアクセスした時、新しいグラフが返される）。
                drawer = Drawer(new_data, FILE_PATHS)

        except Exception as e:
            print(f"\n[Error] Background loop error: {e}")

        # 待機（API制限等を考慮して少し長めに設定しても良いかもしれません）
        time.sleep(background_check_interval)


def main():
    global drawer, an_io

    # 初期化
    print("initializing data...", end="", flush=True)
    init()
    an_io = IO(IDS, RAW_SHEET, SHEET_NAMES, ANSWERS, QUESTIONS, CREDS, FILE_PATHS, FILE_NAMES)
    print(" → Done.")

    # グラフの初期描画
    if not os.path.exists(FILE_PATHS['net']):  # 該当ファイルが存在しない場合
        print(f"No such file '{FILE_PATHS['net']}'. → Recreating the file.", end="", flush=True)
        an_io.recreat_local_file()  # ファイルを作る。
        print(" → Done.")

    with open(FILE_PATHS['net'], 'r', encoding='utf-8') as f:
        data = json.load(f)
    drawer = Drawer(data, FILE_PATHS, FILE_NAMES)

    # 3. 【重要】裏方のループ処理を別スレッドで開始
    print("Starting server and background task...", end="", flush=True)
    bg_thread = threading.Thread(target=check_updates_loop, daemon=True)  # daemon=True にすると、メインプログラム（Flask）が終了した時にこのスレッドも一緒に終了する。
    bg_thread.start()

    # 4. Webサーバーを起動（これはメインスレッドで動き続け、ブロックする）
    print(" → Done.")
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)  # debug=True だとリロード機能が働きスレッドが2重起動することがあるので、本番に近い挙動確認に推奨される use_reloader=False を指定する。

    return 0


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    # ブラウザがここへアクセスするたびに、その時点での最新の drawer のデータを返す
    if drawer is not None:
        return jsonify(drawer.const_view_data())
    else:
        return jsonify({}) # データがない場合の空返し


if __name__ == '__main__':
	sys.exit(main())
