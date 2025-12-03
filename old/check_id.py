# -*- coding: utf-8 -*-
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ==========================================
# ここにフォームIDを入力してください
FORM_ID = '1G_WnVP-tendDUTvtHpT58wkFxFyq46WjG4Lqx4S9Spw'
# ==========================================

SCOPES = ['https://www.googleapis.com/auth/forms.body.readonly']
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'

def main():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    service = build('forms', 'v1', credentials=creds)

    try:
        res = service.forms().get(formId=FORM_ID).execute()
        print(f"フォームタイトル: {res.get('info', {}).get('title')}")
        print("-" * 60)
        print(f"{'TITLE':<20} | {'ITEM ID (構造ID)':<20} | {'QUESTION ID (回答ID)'}")
        print("-" * 60)

        for item in res.get('items', []):
            title = item.get('title', '(No Title)')
            item_id = item.get('itemId')
            
            # 質問IDを取りに行く
            question = item.get('questionItem', {}).get('question', {})
            question_id = question.get('questionId', 'N/A')
            
            # グリッドなどの場合
            if not question_id or question_id == 'N/A':
                group = item.get('questionGroupItem', {})
                if group:
                    question_id = "Group (See below)"

            print(f"{title[:18]:<20} | {item_id:<20} | {question_id}")

            # グループ内の質問があれば表示
            if 'questionGroupItem' in item:
                for q in item['questionGroupItem'].get('questions', []):
                    q_id = q.get('questionId')
                    print(f"  -> Sub Question    | {'(in group)':<20} | {q_id}")

    except Exception as e:
        print(f"エラー: {e}")

if __name__ == '__main__':
    main()
