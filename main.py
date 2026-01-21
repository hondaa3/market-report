import requests
from bs4 import BeautifulSoup
import PyPDF2
import os
from datetime import datetime

def get_mufg_url():
    # 三菱UFJ: FX Daily
    return "https://www.bk.mufg.jp/rept_mkt/gaitame/pdf/fxdaily.pdf"

def get_mizuho_url():
    # みずほ: 外国為替ダイジェスト
    return "https://www.mizuhobank.co.jp/market/pdf/daily/fxdigest.pdf"

def get_smbc_url():
    # 三井住友: 日付からURLを推測（例: 20260121.pdf）
    today = datetime.now().strftime("%Y%m%d")
    return f"https://www.smbc.co.jp/market/pdf/marketreport_{today}.pdf"

def download_and_merge():
    urls = [get_mufg_url(), get_mizuho_url(), get_smbc_url()]
    merger = PyPDF2.PdfMerger()
    files = []
    
    for i, url in enumerate(urls):
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                fname = f"tmp_{i}.pdf"
                with open(fname, "wb") as f:
                    f.write(r.content)
                merger.append(fname)
                files.append(fname)
        except:
            print(f"Skip: {url}")
            
    output = "Daily_Report.pdf"
    merger.write(output)
    merger.close()
    return output

def send_line_message(msg):
    token = os.environ["LINE_TOKEN"]
    user_id = os.environ["USER_ID"]
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = {"to": user_id, "messages": [{"type": "text", "text": msg}]}
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    try:
        pdf_path = download_and_merge()
        # 本来はPDFファイルを送信するが、まずは通知が届くかテスト
        send_line_message("【自動通知】本日の為替レポートのまとめが完了しました。")
    except Exception as e:
        send_line_message(f"エラーが発生しました: {str(e)}")
