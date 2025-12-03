import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# 権限のスコープ（今回は回答の読み取りのみ）
SCOPES = ['https://www.googleapis.com/auth/forms.responses.readonly']

# ここに取得したいフォームのIDを入力してください
FORM_ID = '1G_WnVP-tendDUTvtHpT58wkFxFyq46WjG4Lqx4S9Spw' 

def main():
    creds = None
    # すでに認証済みでトークンがある場合はそれを読み込む
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # 認証情報がない、または無効な場合はログイン画面を表示
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # 次回のためにトークンを保存
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    # Google Forms APIサービスの構築
    service = build('forms', 'v1', credentials=creds)

    try:
        # 回答を取得するAPIリクエスト
        result = service.forms().responses().list(formId=FORM_ID).execute()
        responses = result.get('responses', [])

        if not responses:
            print('回答が見つかりませんでした。')
            return

        print(f"合計 {len(responses)} 件の回答を取得しました。\n")

        # 回答データをループして表示
        for i, resp in enumerate(responses):
            print(f"--- 回答 {i + 1} ---")
            print(f"回答ID: {resp.get('responseId')}")
            print(f"作成日時: {resp.get('createTime')}")
            
            # 各質問への回答詳細（answers）を表示
            answers = resp.get('answers', {})
            for question_id, answer_content in answers.items():
                # テキスト回答の場合の処理
                text_answers = answer_content.get('textAnswers', {}).get('answers', [])
                values = [a.get('value') for a in text_answers]
                print(f"  質問ID: {question_id} -> 回答: {', '.join(values)}")
            print("\n")

    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == '__main__':
    main()
