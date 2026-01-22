import requests
from bs4 import BeautifulSoup
import os
from pdf2image import convert_from_path
from urllib.parse import urljoin
from datetime import datetime, timedelta, timezone

# --- 設定 ---
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

def send_line_image(image_path, msg):
    """画像をLINEに送信する（Messaging APIの仕様上、本来はURLが必要ですが、
    今回は簡易的に『画像が生成されたこと』を通知し、GitHubのリンクを送るか、
    もし公式アカウントがMessaging APIなら画像自体をアップロードする処理になります）
    ※もっとも確実な『画像送信』はMessaging APIの画像URL指定ですが、
    ここでは一番失敗しない『GitHub通知』をベースに調整します。"""
    
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }
    
    # 画像が多すぎるとエラーになるので、まずはテキストで通知
    payload = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": msg}]
    }
    requests.post(url, headers=headers, json=payload)

def get_pdf_url(page_url, keywords):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(page_url, headers=headers, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            if any(k in a.get_text() or k in a['href'] for k in keywords):
                if a['href'].lower().endswith('.pdf'):
                    return urljoin(page_url, a['href'])
    except: return None

def process_reports():
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst)
    yesterday = today - timedelta(days=1)
    
    targets = [
        {"name": "MUFG", "page": "https://www.bk.mufg.jp/rept_mkt/gaitame/index.html", "keys": ["FX Daily"]},
        {"name": "Mizuho", "page": "https://www.mizuhobank.co.jp/market/report.html", "keys": ["外国為替ダイジェスト"]},
        {"name": "SMBC", "page": "https://www.smbc.co.jp/market/", "keys": [today.strftime("%Y年%m月%d日"), yesterday.strftime("%Y年%m月%d日")]}
    ]

    report_msg = "【朝刊】本日のマーケットレポート一報です。\n"
    
    for target in targets:
        pdf_url = get_pdf_url(target['page'], target['keys'])
        if pdf_url:
            report_msg += f"\n・{target['name']}:\n{pdf_url}\n"
            # ここで画像変換して送信する処理も可能ですが、まずは確実にURLをLINEに流します。
            
    send_line_image(None, report_msg)

if __name__ == "__main__":
    process_reports()
