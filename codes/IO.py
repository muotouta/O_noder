#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
O_noderにおける、入出力を司るクラスを扱うコード
"""

__author__ = 'Muto Tao'
__version__ = '0.0.3'
__date__ = '2025.11.30'


import sys
from datetime import datetime, timedelta, timezone
import googleapiclient.discovery


class  IO:
    """
    入出力を司るクラス
    """

    IDS: dict
    RAW_SHEET: str
    SHEET_NAMES: dict
    QUESTIONS: dict

    DRIVE_SERVICE: googleapiclient.discovery 
    FORM_SERVICE: googleapiclient.discovery
    SHEET_SERVICE: googleapiclient.discovery

    partic_form_meta_info = {
        "all_answers_num": 0,
        "new_answers_num": 0,
        "last_timestamp": None  # フォームの形式
    }
    new_answers: list  # 取得した未処理の回答を保存するリスト。キューとして利用。
    

    def __init__(self, IDS, RAW_SHEET, SHEET_NAMES, QUESTIONS, CREDS):
        """
        コンストラクタ
        """

        # 通信用情報を保存
        self.IDS = IDS
        self.RAW_SHEET = RAW_SHEET
        self.SHEET_NAMES = SHEET_NAMES
        self.QUESTIONS = QUESTIONS

        # APIサービスを構築
        self.DRIVE_SERVICE = googleapiclient.discovery.build('drive', 'v3', credentials=CREDS)  # Google Drive APIサービスの構築
        self.FORM_SERVICE = googleapiclient.discovery.build('forms', 'v1', credentials=CREDS)  # Google Forms APIサービスの構築
        self.SHEET_SERVICE = googleapiclient.discovery.build('sheets', 'v4', credentials=CREDS)  # Google Sheet APIサービスの構築

        # 回答情報を初期設定
        try:  # raw_answerのタイムスタンプ情報のみを取得する。
            sheet_raw_answer = self.SHEET_SERVICE.spreadsheets()
            response = sheet_raw_answer.values().get(
                spreadsheetId=self.IDS['raw_answers'],
                range=f"{RAW_SHEET}!A:B"  # 名前
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
                        each_name = each.get('answers', {}).get(self.QUESTIONS['name'], {}).get('textAnswers', {}).get('answers', [{}])[0].get('value')  # 候補の名前を取得
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
        呼び出すと、pratic_formに新規追加された回答を取得し、インスタンスのフィールドに保存するメソッド。
        取得された回答数を返す。
        """

        new_answer_nums = 0
        # print(f"before → all: {self.partic_form_meta_info["all_answers_num"]}, new: {self.partic_form_meta_info["new_answers_num"]}")  # デバッグ用
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
        
        # print(f"before → all: {self.partic_form_meta_info["all_answers_num"]}, new: {self.partic_form_meta_info["new_answers_num"]}")  # デバッグ用

        return new_answer_nums


    def recreate_datasheets(self):
        """
        datasheetsを、既存のものを破壊した後にparticipants_formから作り直すメソッド
        """


    def update_datasheets(self):
        """
        datasheetを更新するメソッド
        new_answersにある回答を一つずつ処理し、new_answersを更新する。
        """

        #  datasheetsに保存
        for a_new_answer in self.new_answers:  # 未処理の回答を一つずつ処理する。
            a_body = self.make_body(a_new_answer)
            for a_sheet in list(self.SHEET_NAMES.keys()):  # 各シートに順番に書き込む。
                try:
                    self.SHEET_SERVICE.spreadsheets().values().append(
                        spreadsheetId=self.IDS['datasheets'],
                        range=f"{self.SHEET_NAMES[a_sheet]}!A1",  # シート名を指定し、末尾に追加
                        valueInputOption='USER_ENTERED',  # スプレッドシート上で入力したのと同じ挙動（日付などが自動変換される）
                        insertDataOption='INSERT_ROWS',  # 必要に応じて新しい行を作成して挿入
                        body={'values' : [a_body[a_sheet]]}
                    ).execute()

                except Exception as e:
                    print(f"Error in \"IO.update_datasheets()\": {e}")
        
        # 回答者フォームのメタ情報を更新
        if self.new_answers:
            new_timestamps = [x.get('lastSubmittedTime') for x in self.new_answers]
            if new_timestamps:  # new_answers が空でない場合のみ更新
                self.partic_form_meta_info['last_timestamp'] = max(new_timestamps)

        # 処理した新しい回答のキューを削除
        self.new_answers.clear()
        self.partic_form_meta_info['new_answers_num'] = 0

    
    def recreate_form(self):
        """
        participants_formの知り合いの質問を、既存のものを破壊した後にraw_answersから作り直すメソッド
        """

    
    def uppdate_form(self):
        """
        participants_formの知り合いの質問を更新するメソッド
        new_answersにある回答を一つずつ処理し、new_answersを更新する。
        """

    
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
        日時データの形式を変換する関数
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
    

    def make_body(self, answer):
        """
        未処理の回答の情報を、datasheetsの各シート用の文字列に変換するメソッド
        一つの未処理の回答answerに対して、datasheetsの各シートそれぞれ用の文字列をバリューとする辞書を返す。
        """

        time = answer.get('lastSubmittedTime')
        name = f"{self.partic_form_meta_info["all_answers_num"]}_{answer.get('answers', {}).get(self.QUESTIONS["name"], {}).get('textAnswers', {}).get('answers', [{}])[0].get('value')}"
        prof_img_id = answer.get('answers', {}).get(self.QUESTIONS["prof_image"], {}).get('fileUploadAnswers', {}).get('answers', [{}])[0].get('fileId')
        friends = [x.get('value') for x in answer.get('answers', {}).get(self.QUESTIONS["friends"], {}).get('textAnswers', {}).get('answers', [])]

        # partic_info用のデータを作成
        partic_line = [
            name,
            time,
            prof_img_id
        ]

        # net_info用のデータを作成
        net_line = [name]
        counter = 1
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
        form_line = [1, 1, 1]

        result = {
            "partic" : partic_line,
            "net" : net_line,
            "form" : form_line
        }
        
        return result
