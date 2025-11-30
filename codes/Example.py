#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
O_noderの実行ファイル
"""

__author__ = 'Muto Tao'
__version__ = '0.1.0'
__date__ = '2025.12.1'

import sys
import os.path
import datetime
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from IO import IO


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

SCOPES = [
    'https://www.googleapis.com/auth/drive.file',  # このアプリで使用する Google ドライブ上の特定のファイルのみの参照、編集、作成、削除
    'https://www.googleapis.com/auth/drive.metadata.readonly',  # このアプリが作成したわけではないGoogle ドライブ上の特定のファイルの参照
    'https://www.googleapis.com/auth/forms.body',  # Googleフォームのすべてのフォームの参照、編集、作成、削除
    'https://www.googleapis.com/auth/forms.responses.readonly',  # Googleフォームのフォームに対するすべての回答の参照
    'https://www.googleapis.com/auth/spreadsheets'  # Googleスプレッドシートのすべてのスプレッドシートの参照、編集、作成、削除
    ]

CREDS: None
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'


def main():
    # 初期化
    init()

    an_io = IO(IDS, RAW_SHEET, SHEET_NAMES, ANSWERS, QUESTIONS, CREDS)

    # an_io.recreate_datasheets()
    # an_io.recreate_form()

    while True:
        print(datetime.datetime.now())

        if an_io.call_new_answers() > 0:
            an_io.update_databese()  # 新規の回答に合わせてデータベース（ネット上のスプレッドシートとフォーム）上のデータを更新

            # an_io.call_datasheets()  # 新規の回答に合わせてローカルの情報を更新


        
        print()
        time.sleep(1)



    return 0


def init():
    """
    実行環境を構築する関数。
    ・ファイル構成を整える。
    ・認証情報を取得する。
    """

    global CREDS
    CREDS = None
    
    # トークン取得
    if os.path.exists(TOKEN_FILE):  # すでに認証済みでトークンがある場合はそれを読み込む
        CREDS = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not CREDS or not CREDS.valid: # 認証情報がない、または無効な場合はログイン画面を表示
        if CREDS and CREDS.expired and CREDS.refresh_token:
            try:
                CREDS.refresh(Request())
            except:
                CREDS = None
        
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            CREDS = flow.run_local_server(port=0)
        
        # 次回以降のためにトークンを保存
        with open(TOKEN_FILE, 'w') as token:
            token.write(CREDS.to_json())


if __name__ == '__main__':
	sys.exit(main())
