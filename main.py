import requests
from bs4 import BeautifulSoup
import PyPDF2
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from urllib.parse import urljoin
from datetime import datetime, timedelta, timezone

# --- 設定 ---
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")
GDRIVE_JSON = os.environ.get("GDRIVE_SERVICE_ACCOUNT")
FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID")

def upload_to_drive(file_path):
    """Googleドライブにアップロードして共有リンクを取得する"""
    try:
        scopes = ['https://www.googleapis.com/auth/drive']
        creds_dict = json.loads(GDRIVE_JSON)
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': f"Market_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
            'parents': [FOLDER_ID]
        }
        media = MediaFileUpload(file_path, mimetype='application/pdf')
        
        # アップロード実行
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        file_id = file.get('id')

        # 誰でも閲覧可能にする設定 (共有リンクを有効化)
        service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'viewer'}).execute()
        
        # 共有用リンクを取得
        res = service.files().get(fileId=file_id, fields='webViewLink').execute()
        return res.get('webViewLink')
    except Exception as e:
        print(f"Gドライブアップロード失敗: {e}")
        return None

def get_pdf_url(page_url, keywords):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(page_url, headers=headers, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            link_text = a.get_text(strip=True)
            link_href = a['href']
            if any(k in link_text or k in link_href for k in keywords):
                if link_href.lower().endswith('.pdf'):
                    return urljoin(page_url, link_href)
    except Exception as e:
        print(f"Error scanning {page_url}: {e}")
    return None

def download_and_merge():
    merger = PyPDF2.PdfMerger()
    downloaded_files = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst)
    yesterday = today - timedelta(days=1)
    
    targets = [
        {"name": "MUFG", "page": "https://www.bk.mufg.jp/rept_mkt/gaitame/index.html", "keys": ["FX Daily"]},
        {"name": "Mizuho", "page": "https://www.mizuhobank.co.jp/market/report.html", "keys": ["外国為替ダイジェスト"]},
        {"name": "SMBC", "page": "https://www.smbc.co.jp/market/", "keys": [today.strftime("%Y年%m月%d日"), yesterday.strftime("%Y年%m月%d日")]},
        {"name": "Resona", "page": "https://www.resonabank.co.jp/kojin/market/daily/index.html", "keys": [today.strftime("%m月%d日"), yesterday.strftime("%m月%d日"), "market_daily"]}
    ]

    for target in targets:
        pdf_url = get_pdf_url(target['page'], target['keys'])
        if pdf_url:
            try:
                res = requests.get(pdf_url, headers=headers, timeout=20)
                if res.status_code == 200 and res.content.startswith(b'%PDF'):
                    filename = f"{target['name']}.pdf"
                    with open(filename, "wb") as f:
                        f.write(res.content)
                    merger.append(filename)
                    downloaded_files.append(filename)
                    print(f"成功: {target['name']}")
            except: pass

    if downloaded_files:
        output_file = "Daily_Market_Report.pdf"
        merger.write(output_file)
        merger.close()
        return output_file
    return None

def send_line_notification(drive_link):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    msg = f"【完了】最新レポートを結合しました。\n下記リンクから直接確認できます：\n{drive_link}" if drive_link else "レポートの結合は完了しましたが、Gドライブへの保存に失敗しました。"
    payload = {"to": USER_ID, "messages": [{"type": "text", "text": msg}]}
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    merged_path = download_and_merge()
    if merged_path:
        link = upload_to_drive(merged_path)
        send_line_notification(link)
    else:
        send_line_notification("レポートが見つかりませんでした。")
