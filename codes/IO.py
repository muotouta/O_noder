#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
O_noderにおける、入出力を司るクラスを扱うコード
"""

__author__ = 'Muto Tao'
__version__ = '0.1.1'
__date__ = '2025.12.1'


import sys
import time
from datetime import datetime, timedelta, timezone
import googleapiclient.discovery


class  IO:
    """
    入出力を司るクラス
    """

    IDS: dict
    RAW_SHEET: str
    SHEET_NAMES: dict
    QUESTIONS : dict
    ANSWERS: dict

    DRIVE_SERVICE: googleapiclient.discovery 
    FORM_SERVICE: googleapiclient.discovery
    SHEET_SERVICE: googleapiclient.discovery

    partic_form_meta_info = {
        "all_answers_num": 0,
        "new_answers_num": 0,
        "last_timestamp": None  # フォームの形式
    }
    new_answers: list  # 取得した未処理の回答を保存するリスト。キューとして利用。

    NO_FRIENDS_NAME = "0_No friends / なし"  # participants_formのネットワーク情報の質問の初期選択肢
    ADDITIONAL_COLUMN = 30  # スプレッドシートの列を増やすときに、一度に増やす列の数

    # APIの制限で1分間に60回までしか書き込みリクエストができず、それを超えるとエラーになるので、リクエストのレートに制限をかけるための、書き込み状況を監視する変数
    timer = time.time()
    write_count = 0  # 書き込み回数を記録
    COUNT_THRESHOLD = 56  # 連続書き込み回数の上限
    LIMIT = 60  # 連続書き込み回数の上限を考える時間の長さ
    

    def __init__(self, IDS, RAW_SHEET, SHEET_NAMES, ANSWERS, QUESTIONS, CREDS):
        """
        コンストラクタ
        """

        # 通信用情報を保存
        self.IDS = IDS
        self.RAW_SHEET = RAW_SHEET
        self.SHEET_NAMES = SHEET_NAMES
        self.QUESTIONS = QUESTIONS
        self.ANSWERS = ANSWERS

        # APIサービスを構築
        self.DRIVE_SERVICE = googleapiclient.discovery.build('drive', 'v3', credentials=CREDS)  # Google Drive APIサービスの構築
        self.FORM_SERVICE = googleapiclient.discovery.build('forms', 'v1', credentials=CREDS)  # Google Forms APIサービスの構築
        self.SHEET_SERVICE = googleapiclient.discovery.build('sheets', 'v4', credentials=CREDS)  # Google Sheet APIサービスの構築

        # 回答情報を初期設定
        self.new_answers = []
        try:  # raw_answerのタイムスタンプ情報のみを取得する。
            sheet_raw_answer = self.SHEET_SERVICE.spreadsheets()
            response = sheet_raw_answer.values().get(
                spreadsheetId=self.IDS['raw_answers'],
                range=f"{self.RAW_SHEET}!A:B"  # 名前と日付の情報を取れる範囲を取得する。
                ).execute()
            
            if not response.get('values', []):
                print("Error in \"IO.init()\": sheet \"raw_answer\" not found.")
                sys.exit(1)

            sheet_raw_answer_values = response.get('values', [])[1:]  # 第1要素はヘッダなので取り除く
            if len(sheet_raw_answer_values) > 0:  # 回答がある場合
                self.partic_form_meta_info['all_answers_num'] = len(sheet_raw_answer_values)
                
                ## フォーム上の日時情報がミリ秒単位であるのに対し、スプレッドシート上の日時情報は秒単位であり低精度で、このズレから不具合（ミリ秒単位では回答順序の判断がつく回答に正しい判断を下せないなど）が生じうるので、call_new_answers()でフォームの日時情報を用いていることから、それを用いる方に統一する。
                # raw_answers上の日時情報を取得
                latest_answer = sorted(sheet_raw_answer_values, key=lambda x: x[0])[-1]  # 第0要素=タイムスタンプでソートし、そのうち最大のもの=最新の回答を取得。タイムスタンプが無い回答がある場合は考えない。
                low_latest_timestamp = self.convert_timedata(latest_answer[0], "StoF")  # 低精度のタイムスタンプに変換

                # participants_formから回答を取得し、名前と低精度タイムスタンプが一致する回答を探してきて、そこから正確なタイムスタンプを得る。
                try:
                    response = self.FORM_SERVICE.forms().responses().list(
                        formId=self.IDS['partic_form'],
                        filter=f"timestamp >= {low_latest_timestamp}"
                    ).execute()  # low_latest_timestamp以降の回答を得る。

                    candidates = []
                    for each in response.get('responses', []):
                        each_name = each.get('answers', {}).get(self.ANSWERS['name'], {}).get('textAnswers', {}).get('answers', [{}])[0].get('value')  # 候補の名前を取得
                        raw_time = each.get('lastSubmittedTime') or each.get('createTime')
                        each_time = self.convert_timedata(self.convert_timedata(raw_time, "FtoS"), "StoF")  # 一度スプレッドシートの形式にすることで精度を落とし、その上でフォームの日時形式にする。
                        if each_name == latest_answer[1] and each_time == low_latest_timestamp:
                            candidates.append(raw_time)
                    
                    if candidates:
                        self.partic_form_meta_info['last_timestamp'] = max(candidates)
                    else:  # 名前で一致が見つからない場合は、最初の低精度のタイムスタンプを採用（重複のリスクがあるが動作はする）
                        self.partic_form_meta_info['last_timestamp'] = low_latest_timestamp

                except Exception as e:
                    print(f"Error in \"IO.init()\": {e}")

            else:  # 回答がない場合
                self.partic_form_meta_info['all_answers_num'] = 0
                sheet_raw_answer_metadata = self.DRIVE_SERVICE.files().get(
                    fileId=self.IDS['raw_answers'],
                    fields='createdTime'
                    ).execute()  # raw_answerの作成日時情報を得る。
                self.partic_form_meta_info['last_timestamp'] = sheet_raw_answer_metadata.get('createdTime')

        except Exception as e:
            print(f"Error in \"IO.init()\": {e}")


    def call_new_answers(self):
        """
        呼び出すと、pratic_formに新規追加された回答を取得し、インスタンスのフィールドself.new_answersに保存するメソッド。
        取得された回答数を返す。
        """

        new_answer_nums = 0
        try:
            response = self.FORM_SERVICE.forms().responses().list(
                formId=self.IDS['partic_form'],
                filter=f"timestamp >= {self.partic_form_meta_info['last_timestamp']}"
                ).execute()  # last_timestamp以後の回答のみを取得する。

            raw_responses = response.get('responses', [])
            self.new_answers = []
            for resp in raw_responses:
                resp_time = resp.get('lastSubmittedTime') or resp.get('createTime')
                if resp_time > self.partic_form_meta_info['last_timestamp']:
                    self.new_answers.append(resp)

            if self.new_answers:  # 新しい回答がない場合には、self.new_answersは空リストになっている。
                new_answer_nums = len(self.new_answers)
                self.partic_form_meta_info["new_answers_num"] = new_answer_nums
                self.partic_form_meta_info["all_answers_num"] += new_answer_nums
        except Exception as e:
            print(f"Error in \"IO.call_new_answers()\": {e}")

        return new_answer_nums


    def update_databese(self):
        """
        datasheetsとparticipants_formを更新するメソッド
        双方の更新後、new_answersにある回答をフラッシュする。
        """
        
        self.update_datasheets()
        self.update_form()

        # 参加者フォームのメタ情報を更新
        if self.new_answers:
            new_timestamps = [x.get('lastSubmittedTime') for x in self.new_answers]
            if new_timestamps:  # new_answers が空でない場合のみ更新
                self.partic_form_meta_info['last_timestamp'] = max(new_timestamps)

        # 処理した新しい回答のキューを削除
        self.new_answers.clear()
        self.partic_form_meta_info['new_answers_num'] = 0


    def update_datasheets(self):
        """
        datasheetsを更新するメソッド
        self.new_answersの回答をdatasheetsに追加する。
        """

        self.writing_keeper("set")
        self.add_column_if_needed('datasheets', 'net_info', self.ADDITIONAL_COLUMN)
        self.writing_keeper("check")

        for counter, a_new_answer in enumerate(self.new_answers, start=0):  # 未処理の回答を一つずつ処理する。
            # 現在の最終列を確認するために、1行目(ヘッダー行)だけを取得
            try:  
                response = self.SHEET_SERVICE.spreadsheets().values().get(
                    spreadsheetId=self.IDS['datasheets'],
                    range=f"{self.SHEET_NAMES["net"]}!1:1"  # 1行目全体
                ).execute()

            except Exception as e:
                print(f"Error while making a column for the datasheets in \"IO.update_datasheets()\": {e}")
            
            next_col_num = self.partic_form_meta_info["all_answers_num"] + counter + 2  # データがある列数 + 1 が書き込み開始位置
            start_col_letter = self.col_num_to_letter(next_col_num)  # 列番号をアルファベットに変換
            target_range = f"{self.SHEET_NAMES["net"]}!{start_col_letter}1"  # 書き込む範囲を指定

            # 末尾の行までの行列の、末尾の列を0で埋める。
            new_column_data = [f"{self.partic_form_meta_info["all_answers_num"]+counter}_{a_new_answer.get('answers', {}).get(self.ANSWERS["name"], {}).get('textAnswers', {}).get('answers', [{}])[0].get('value')}"]  # ヘッダ（第1行）に名前を追加
            for i in range(self.partic_form_meta_info["all_answers_num"] + counter - 1):
                new_column_data.append(0)
            body = {
                "majorDimension": "COLUMNS",
                'values' : [new_column_data]
            }

            # 末尾の列に追加する。
            try:
                self.SHEET_SERVICE.spreadsheets().values().update(
                    spreadsheetId=self.IDS['datasheets'], # 対象のスプレッドシートID
                    range=target_range,
                    valueInputOption="USER_ENTERED",      # 自動フォーマット（日付や数値の認識）
                    body=body
                ).execute()
                self.writing_keeper("check")

            except Exception as e:
                print(f"Error while adding a column to the datasheets in \"IO.update_datasheets()\": {e}")

            # 各シートに順番に、最新の1行を書き込む。
            a_body = self.make_body(a_new_answer, counter)
            for a_sheet in list(self.SHEET_NAMES.keys()):
                try:
                    self.SHEET_SERVICE.spreadsheets().values().append(
                        spreadsheetId=self.IDS['datasheets'],
                        range=f"{self.SHEET_NAMES[a_sheet]}!A1",  # シート名を指定し、末尾に追加
                        valueInputOption='USER_ENTERED',  # スプレッドシート上で入力したのと同じ挙動（日付などが自動変換される）
                        insertDataOption='INSERT_ROWS',  # 必要に応じて新しい行を作成して挿入
                        body={'values' : [a_body[a_sheet]]}
                    ).execute()
                    self.writing_keeper("check")


                except Exception as e:
                    print(f"Error while adding a row to the datasheets in \"IO.update_datasheets()\": {e}")


    def update_form(self):
        """
        participants_formの知り合いの質問を更新するメソッド
        self.new_answersの回答を知り合いの選択肢として追加する。
        """

        targe_item_id = self.QUESTIONS['friends']
        url_base = "https://drive.google.com/uc?export=view&id="
        no_friends_img = url_base + "1JeCihM9JrBho6ZHnP9MY6aL8ngEGAFhB"
        no_image_url = url_base + "1hVD7XBwRcpp46XvQSl-hjW70JgfKsKfU"

        try:
            # 現在のフォーム情報を取得
            current_form = self.FORM_SERVICE.forms().get(formId=self.IDS['partic_form']).execute()

            # 対象のアイテム(質問)を探す。
            current_item = None
            target_index = -1
            for i, item in enumerate(current_form.get('items', [])):  # enumerateでインデックスを取得
                if item.get('itemId') == targe_item_id:
                    current_item = item
                    target_index = i
                    break            
            if not current_item:
                print("Error in \"IO.update_form()\": No proper question in the form.")
                return
            options = current_item['questionItem']['question']['choiceQuestion']['options']  # 現在の選択肢リストと「インデックス(場所)」を抽出

            # 既存の投稿のプロフィール情報を反映
            sheet_raw_answer = self.SHEET_SERVICE.spreadsheets()
            response = sheet_raw_answer.values().get(
                spreadsheetId=self.IDS['raw_answers'],
                range=f"{self.RAW_SHEET}!A:D"  # 名前とプロフィール画像の情報が取れる範囲を取得する。
                ).execute()
            sheet_raw_answer_values = response.get('values', [])[1:]  # 第1要素はヘッダなので取り除く
            if not response.get('values', []):  # participants_formが無い場合
                print("Error in \"IO.init()\": sheet \"participants_form\" not found.")
                sys.exit(1)

            for an_option in options:
                register_num = int(an_option['value'].split("_")[0])  # 登録番号=名前の先頭の番号を取得

                if register_num == 0:
                    img = no_friends_img
                else:
                    if sheet_raw_answer_values[register_num-1][2] == "":  # 画像が選択されていない場合
                        img = no_image_url
                    else:
                        img = url_base + sheet_raw_answer_values[register_num-1][2].split("=")[1]

                if 'image' in an_option:  # 画像情報を削除してエラーを回避（画像URL問題を避けるため）
                    an_option['image'] = {'sourceUri': img}

            # 新しい投稿を反映
            for counter, an_answer in enumerate(self.new_answers):
                # 回答情報を取得
                name = f"{self.partic_form_meta_info['all_answers_num']+counter}_{an_answer.get('answers', {}).get(self.ANSWERS['name'], {}).get('textAnswers', {}).get('answers', [{}])[0].get('value')}"
                prof_img_id = an_answer.get('answers', {}).get(self.ANSWERS['prof_image'], {}).get('fileUploadAnswers', {}).get('answers', [{}])[0].get('fileId')

                # 採用する画像を選ぶ
                if name == self.NO_FRIENDS_NAME:
                    img = no_friends_img
                elif prof_img_id == None:  # 画像が選択されていない場合
                    img = no_image_url
                else:
                    img = url_base + prof_img_id

                # 新しい選択肢の追加
                new_option = {
                    "value": name,
                    "image": {
                        "sourceUri": img
                    }
                }
                options.append(new_option)

            # 更新リクエストの作成
            update_body = {
                "requests": [
                    {
                        "updateItem": {
                            "item": {
                                "itemId": targe_item_id,
                                "questionItem": {
                                    "question": {
                                        "choiceQuestion": {
                                            "type": "CHECKBOX",
                                            "options": options
                                        }
                                    }
                                }
                            },
                            "location": {"index": target_index},
                            "updateMask": "questionItem.question.choiceQuestion.options"
                        }
                    }
                ]
            }

            # API実行
            self.FORM_SERVICE.forms().batchUpdate(formId=self.IDS['partic_form'], body=update_body).execute()

        except Exception as e:
            print(f"Error in \"IO.update_form()\": {e}")


    def set_datasheets(self):
        """
        datasheetsを更新するメソッド
        self.new_answersの回答からdatasheetsを構築する。
        """

        self.writing_keeper("set")
        self.add_column_if_needed('datasheets', 'net_info', self.ADDITIONAL_COLUMN)
        self.writing_keeper("check")

        # 本処理
        num = 1 if self.partic_form_meta_info['all_answers_num'] - 1 <= 0 else 0  # 回答が0件のときと1件以上のときで、新しい回答をdatasheetsに追加する際の回答番号の振る舞いを変えなければいけないから。これがないと、番号がズレる。
        line_counter = 2
        for counter, a_new_answer in enumerate(self.new_answers, start=num):  # 未処理の回答を一つずつ処理する。
            # 各シートに順番に、最新の1行を書き込む。
            a_body = self.make_body(a_new_answer, counter)
            for a_sheet in list(self.SHEET_NAMES.keys()):
                try:
                    self.SHEET_SERVICE.spreadsheets().values().append(
                        spreadsheetId=self.IDS['datasheets'],
                        range=f"{self.SHEET_NAMES[a_sheet]}!A1",  # シート名を指定し、末尾に追加
                        valueInputOption='USER_ENTERED',  # スプレッドシート上で入力したのと同じ挙動（日付などが自動変換される）
                        insertDataOption='INSERT_ROWS',  # 必要に応じて新しい行を作成して挿入
                        body={'values' : [a_body[a_sheet]]}
                    ).execute()
                    self.writing_keeper("check")

                except Exception as e:
                    print(f"Error while adding a row to the datasheets in \"IO.update_datasheets()\": {e}")

            # ヘッダを書き込む。
            try:  # 現在の最終列を確認するために、1行目(ヘッダー行)だけを取得
                response = self.SHEET_SERVICE.spreadsheets().values().get(
                    spreadsheetId=self.IDS['datasheets'],
                    range=f"{self.SHEET_NAMES['net']}!1:1"  # 1行目全体
                ).execute()

            except Exception as e:
                print(f"Error while making a column for the datasheets in \"IO.update_datasheets()\": {e}")
            
            next_col_num = self.partic_form_meta_info["all_answers_num"] + counter + 2  # データがある列数 + 1 が書き込み開始位置
            start_col_letter = self.col_num_to_letter(next_col_num)  # 列番号をアルファベットに変換
            target_range = f"{self.SHEET_NAMES['net']}!{start_col_letter}1"  # 書き込む範囲を指定

            new_column_data = [f"{self.partic_form_meta_info['all_answers_num']+counter}_{a_new_answer.get('answers', {}).get(self.ANSWERS['name'], {}).get('textAnswers', {}).get('answers', [{}])[0].get('value')}"]  # ヘッダ（第1行）に名前を追加            
            body = {
                'majorDimension': 'COLUMNS',
                'values' : [new_column_data]
            }
            try:
                self.SHEET_SERVICE.spreadsheets().values().update(
                    spreadsheetId=self.IDS['datasheets'],  # 対象のスプレッドシートID
                    range=target_range,
                    valueInputOption="USER_ENTERED",  # 自動フォーマット（日付や数値の認識）
                    body=body
                ).execute()
                self.writing_keeper("check")

            except Exception as e:
                print(f"Error while adding a column to the datasheets in \"IO.update_datasheets()\": {e}")

            # 空欄に0を挿入していく。
            try:
                # 行ごとに足りない部分を0で埋めたリストを作る。
                response = self.SHEET_SERVICE.spreadsheets().values().get(
                    spreadsheetId=self.IDS['datasheets'],
                    range=f"{self.SHEET_NAMES['net']}!{line_counter}:{line_counter}"  # line_counter行目全体を取得
                ).execute()
                a_row = response.get('values', [])[0]  # 二重リストなので、内側のリストを取り出す。
                for i in range(self.partic_form_meta_info["all_answers_num"] + self.partic_form_meta_info["new_answers_num"] - len(a_row) + 2):
                    a_row.append(0)

                # 作成したリストをnet_infoに反映する。
                target_cell = f"{self.SHEET_NAMES['net']}!A{line_counter}"  # 書き込む場所を指定
                self.SHEET_SERVICE.spreadsheets().values().update(
                    spreadsheetId=self.IDS['datasheets'],  # 対象のスプレッドシートID
                    range=target_cell,
                    valueInputOption="USER_ENTERED",  # 自動フォーマット（日付や数値の認識）
                    body={'values' : [a_row]}
                ).execute()
                self.writing_keeper("check")

                # 処理する行を次に進める
                line_counter += 1
            except Exception as e:
                print(f"Error while filling up the datasheets in \"IO.update_datasheets()\": {e}")
                

    def recreate_databese(self):
        """
        datasheetsとparticipants_formのネットワーク情報の選択肢を、既存のものを破壊した後にparticipants_formから作り直すメソッド
        """

        # datasheetsの内容と、 participants_formのネットワーク情報の選択肢を「0_No friends / なし」以外すべて消去する。

        # datasheetsとparticipants_formの最初のフォーマットを整える。


        self.set_all_answers_as_new()
        self.set_datasheets()
        self.update_form

        # 処理した新しい回答のキューを削除
        self.partic_form_meta_info['all_answers_num'] = len(self.new_answers)
        self.new_answers.clear()
        self.partic_form_meta_info['new_answers_num'] = 0


    def recreate_datasheets(self):
        """
        datasheetsを、既存のものを破壊した後にparticipants_formから作り直すメソッド
        """

        # datasheetsの内容をすべて消去する。
        for a_sheet in list(self.SHEET_NAMES.keys()):
            try:
                self.SHEET_SERVICE.spreadsheets().values().clear(
                    spreadsheetId=self.IDS['datasheets'],
                    range=self.SHEET_NAMES[a_sheet]
                ).execute()
            except Exception as e:
                print(f"Error while deleting datasheets in \"recreate_datasheets()\": {e}")

        # partic_infoの最初のフォーマットを整える。


        # net_infoの最初のフォーマットを整える。
        try:
            self.SHEET_SERVICE.spreadsheets().values().update(
                spreadsheetId=self.IDS['datasheets'],  # 対象のスプレッドシートID
                range=f"{self.SHEET_NAMES['net']}!A1",  # 1行1列成分から書き込む。
                valueInputOption="USER_ENTERED",  # 自動フォーマット（日付や数値の認識）
                body={'values' : [["-", self.NO_FRIENDS_NAME]]}
            ).execute()
        except Exception as e:
            print(f"Error while writing first format to the datasheets in \"IO.recreate_datasheets()\": {e}")

        # 書き込む。
        self.set_all_answers_as_new()
        self.set_datasheets()

        # 処理した新しい回答のキューを削除
        self.partic_form_meta_info['all_answers_num'] = len(self.new_answers)
        self.new_answers.clear()
        self.partic_form_meta_info['new_answers_num'] = 0

    
    def recreate_form(self):
        """
        participants_formのネットワーク情報の選択肢を、既存のものを破壊した後にraw_answersから作り直すメソッド
        """

        # participants_formのネットワーク情報の選択肢を「0_No friends / なし」以外すべて消去する。
        # 最初のフォーマットを整える。

        self.set_all_answers_as_new()
        self.update_form()

        # 処理した新しい回答のキューを削除
        self.partic_form_meta_info['all_answers_num'] = len(self.new_answers)
        self.new_answers.clear()
        self.partic_form_meta_info['new_answers_num'] = 0

    
    def call_datasheets(self, name: str, range: str):
        """
        datasheetsのデータをローカルに落とすメソッド
        name: どのシートか
            ・partic_info
            ・net_info
            ・form_src
        range: 取得するデータの範囲
            ・all: シート全体
            ・line: 最後の行
        """


    def convert_timedata(self, input_str: str, method: str):
        """
        日時データの形式を変換するヘルパー関数
            method
                ・StoF: スプレッドシートの日時データ形式の文字列を、フォームの日時データ形式の文字列に変換
                ・FtoS: 文字列フォームの日時データ形式の文字列を、スプレッドシートの日時データ形式に変換
                (
                フォームの日時データ形式 : ISO 8601 UTC / 例: 2025-11-29T14:24:59.984Z または 2025-11-29T14:24:59Z
                スプレッドシートの日時データ形式 : 
                )
            変換ができないデータ形式が渡された場合には、現在の最後のタイムスタンプ情報を用いて変換後のデータを作り、返す。
        """

        output_str = None
        
        if method == "StoF":
            try:
                dt = datetime.strptime(input_str, '%Y/%m/%d %H:%M:%S')  # 文字列を datetime オブジェクトに変換（%Y=年, %m=月, %d=日, %H=時, %M=分, %S=秒）
                dt_jst = dt.replace(tzinfo=timezone(timedelta(hours=9)))  # このデータは日本時間(JST)であると設定
                dt_utc = dt_jst.astimezone(timezone.utc)  # UTC(世界標準時)に変換 (-9時間)
                output_str = dt_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'  # 指定の形式（ミリ秒3桁 + Z）の文字列にする
            except ValueError:
                output_str = self.partic_form_meta_info["last_timestamp"]
                
        elif method == "FtoS":
            try:
                if input_str.endswith('Z'):  # Zを+00:00に置換してパース可能にする
                    input_str = input_str.replace('Z', '+00:00')
                dt_utc = datetime.fromisoformat(input_str)
                dt_jst = dt_utc.astimezone(timezone(timedelta(hours=9)))  # JST (+09:00) に変換
                output_str = dt_jst.strftime('%Y/%m/%d %H:%M:%S')  # スプレッドシート形式 (YYYY/MM/DD HH:MM:SS) にフォーマット
            except ValueError:
                output_str = self.convert_timedata(self.partic_form_meta_info["last_timestamp"], "FtoS")
            
        return output_str
    

    def make_body(self, answer, counter: int):
        """
        未処理の回答の情報を、datasheetsの各シート用の文字列に変換するメソッド
        一つの未処理の回答answerに対して、datasheetsの各シートそれぞれ用の文字列をバリューとする辞書を返す。
        """

        time = answer.get('lastSubmittedTime')
        name = f"{self.partic_form_meta_info['all_answers_num']+counter}_{answer.get('answers', {}).get(self.ANSWERS['name'], {}).get('textAnswers', {}).get('answers', [{}])[0].get('value')}"
        prof_img_id = answer.get('answers', {}).get(self.ANSWERS['prof_image'], {}).get('fileUploadAnswers', {}).get('answers', [{}])[0].get('fileId')
        friends = [x.get('value') for x in answer.get('answers', {}).get(self.ANSWERS['friends'], {}).get('textAnswers', {}).get('answers', [])]

        # partic_info用のデータを作成
        partic_line = [
            name,
            time,
            prof_img_id
        ]

        # net_info用のデータを作成
        net_line = [name]
        counter = 0
        if friends:
            while counter <= self.partic_form_meta_info["all_answers_num"]:
                for each in friends:
                    friend_number = int(each.split("_")[0])  # 先頭の数字を取り出す。
                    while counter < friend_number:
                        net_line.append(0)  # 繋がりがない場合は0
                        counter += 1

                    net_line.append(1)  # 繋がりがある場合は1
                    counter += 1
                friends.clear()

                net_line.append(0)  # 繋がりがない場合は0
                counter += 1
        else:
            while counter <= self.partic_form_meta_info["all_answers_num"]:
                net_line.append(0)  # 繋がりがない場合は0
                counter += 1

        # form_src用のデータを作成
        # form_line = [1, 1, 1]

        result = {
            "partic" : partic_line,
            "net" : net_line
            # "form" : form_line
        }
        
        return result


    def col_num_to_letter(self, num):
        """
        整数numをExcel風のアルファベット列名に変換する関数
        例: 1->A, 26->Z, 27->AA, 52->AZ, 53->BA ...
        """
        if num <= 0:
            raise ValueError("1以上の整数を指定してください")

        result = ""
        while num > 0:
            num -= 1  # 1始まり(1-26)を0始まり(0-25)に補正して計算しやすくする
            remainder = num % 26
            result = chr(65 + remainder) + result  # chr(65) は 'A' 。remainder(0~25) を足して文字に変換。先頭に追加していくことで桁上がりを表現。
            num //= 26  # 次の桁へ

        return result


    def set_all_answers_as_new(self):
        """
        participants_formから、すべての回答を読み取り、self.new_answersに格納するヘルパー関数
        self.partic_form_meta_infoも更新する。
        もし現在の未処理の回答がある場合、関数の処理の一番最初にそれらを放棄する。
        """

        # 現在の未処理の回答を放棄する
        if self.new_answers:
            self.new_answers.clear()

        # すべての回答を取得し、self.new_answersに保存する。
        try:
            response = self.FORM_SERVICE.forms().responses().list(
                formId=self.IDS['partic_form'],
                ).execute()
            tmp = response.get('responses', [])

        except Exception as e:
            print(f"Error while getting all answers in \"IO.set_all_answers_as_new()\": {e}")

        self.new_answers = sorted(tmp, key=lambda x: x.get('lastSubmittedTime'))  # 投稿日時でソート

        # self.partic_form_meta_infoの回答数を更新
        new_answer_nums = len(self.new_answers)
        if new_answer_nums > 0:  # 新しい回答がない場合には、self.new_answersは空リストになっている。
            self.partic_form_meta_info["all_answers_num"] = 0 
            self.partic_form_meta_info["new_answers_num"] = new_answer_nums
        else:
            new_answer_nums = 0

        # self.partic_form_meta_infoのタイムスタンプを更新
        new_timestamps = [x.get('lastSubmittedTime') for x in self.new_answers]
        if new_timestamps:  # new_answers が空でない場合のみ更新
            self.partic_form_meta_info['last_timestamp'] = max(new_timestamps)
        else:  # new_answers が空である場合には、raw_answersの作成日時をタイムスタンプにする。
            try:
                sheet_raw_answer_metadata = self.DRIVE_SERVICE.files().get(
                        fileId=self.IDS['raw_answers'],
                        fields='createdTime'
                        ).execute()  # raw_answerの作成日時情報を得る。
                self.partic_form_meta_info['last_timestamp'] = sheet_raw_answer_metadata.get('createdTime')
            except Exception as e:
                print(f"Error while setting timestamp in \"IO.set_all_answers_as_new()\": {e}")
            
        return new_answer_nums


    def add_column_if_needed(self, sheet_id, sheet_name, num):
        """
        sheet_nameで指定されるスプレッドシートの列数が足りなくなったら、引数で指定された数だけ列を増やすヘルパー関数
        """

        threshold = 10  # 現在の列数とこれからの列数の差が何以下なら列を追加するかの閾値

        # スプレッドシートの現在の列数を取得
        current_num = 0
        try:
            # スプレッドシート全体のメタデータを取得（データの中身は取得しないので軽量）
            spreadsheet_meta = self.SHEET_SERVICE.spreadsheets().get(
                spreadsheetId=self.IDS[sheet_id],
                includeGridData=False  # データ自体は不要
            ).execute()

            for sheet in spreadsheet_meta.get('sheets', []):  # 指定されたシート名を探す
                props = sheet.get('properties', {})
                if props.get('title') == sheet_name:
                    current_num = props.get('gridProperties', {}).get('columnCount', 26)  # 新規作成直後などで未定義の場合はデフォルトの26(A-Z)を返す安全策

        except Exception as e:
            print(f"Error in \"IO.add_column_if_needed()\": {e}")
        
        # これから追加される列の数を算出
        future_num = self.partic_form_meta_info["all_answers_num"] + self.partic_form_meta_info["new_answers_num"] + 2

        # 追加の必要性の有無を判定し、必要なら追加する。
        if future_num - current_num <= threshold:
            try:
                body = {
                    "requests": [
                        {
                            "appendDimension": {
                                "sheetId": self.get_sheet_id(sheet_name=sheet_name),
                                "dimension": "COLUMNS", # 列を増やす
                                "length": num        # 増やす数
                            }
                        }
                    ]
                }
                
                self.SHEET_SERVICE.spreadsheets().batchUpdate(
                    spreadsheetId=self.IDS[sheet_id],
                    body=body
                ).execute()
            except Exception as e:
                print(f"Error in \"IO.add_column_if_needed()\": {e}")


    def writing_keeper(self, order: str):
        """
        スプレッドシートへの書き込みがAPIの制限ないに収まる用に管理するヘルパー関数
        使い方
            orderが "set" なら、タイマーを起動
            orderが "check" なら、条件を逸脱していないか確認する。
        """

        if order == "set":
            self.timer = time.time()
        elif order == "check":
            self.write_count += 1
            if self.write_count > self.COUNT_THRESHOLD:
                diff = time.time() - self.timer
                if diff < self.LIMIT:  # 数え始めから60秒以内なら、書き込みを停止する。
                    time.sleep(self.LIMIT - diff + 1)  # バッファ用に1秒おまけで待つ。
                    self.timer = time.time()  # タイマーをリセット
                    self.write_count = 0  # 書き込み回数


    def get_sheet_id(self, sheet_name):
        """
        シート名(例: "net_info")から、そのシート固有の整数ID(SheetId)を取得するヘルパー関数
        """
        try:
            spreadsheet = self.SHEET_SERVICE.spreadsheets().get(
                spreadsheetId=self.IDS['datasheets']
            ).execute()
            
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']  # これが整数のID
            return None
        except Exception as e:
            print(f"Error getting sheet ID: {e}")
            return None
