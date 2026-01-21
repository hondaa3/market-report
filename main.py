import requests
import PyPDF2
import os
from datetime import datetime, timedelta, timezone

# --- 設定 ---
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

def get_latest_pdf(base_url_template, days_to_check=3):
    """日付が含まれるURLに対して、今日から順に遡って存在するものを返す"""
    jst = timezone(timedelta(hours=9))
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    for i in range(days_to_check):
        target_date = datetime.now(jst) - timedelta(days=i)
        target_str = target_date.strftime("%Y%m%d")
        # URLテンプレートの {date} 部分を実際の日付に置き換え
        url = base_url_template.replace("{date}", target_str)
        
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200 and res.content.startswith(b'%PDF'):
                print(f"発見 ({i}日前): {url}")
                return url, res.content
        except:
            continue
    return None, None

def download_and_merge():
    merger = PyPDF2.PdfMerger()
    downloaded_count = 0
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    # --- 1. 三菱UFJ (固定URL) ---
    res = requests.get("https://www.bk.mufg.jp/rept_mkt/gaitame/pdf/fxdaily.pdf", headers=headers)
    if res.status_code == 200:
        with open("mufg.pdf", "wb") as f: f.write(res.content)
        merger.append("mufg.pdf")
        downloaded_count += 1

    # --- 2. みずほ銀行 (固定URL) ---
    res = requests.get("https://www.mizuhobank.co.jp/market/pdf/daily/fxdigest.pdf", headers=headers)
    if res.status_code == 200:
        with open("mizuho.pdf", "wb") as f: f.write(res.content)
        merger.append("mizuho.pdf")
        downloaded_count += 1

    # --- 3. 三井住友銀行 (日付遡りチェック) ---
    smbc_url_template = "https://www.smbc.co.jp/market/pdf/marketreport_{date}.pdf"
    url, content = get_latest_pdf(smbc_url_template)
    if url:
        with open("smbc.pdf", "wb") as f: f.write(content)
        merger.append("smbc.pdf")
        downloaded_count += 1

    if downloaded_count > 0:
        output_file = "Daily_Market_Report.pdf"
        merger.write(output_file)
        merger.close()
        return output_file
    return None

def send_line_notification(msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    payload = {"to": USER_ID, "messages": [{"type": "text", "text": msg}]}
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    merged_pdf = download_and_merge()
    if merged_pdf:
        send_line_notification("【完了】本日の最新レポート（一部昨日のものを含む）を1つにまとめました。")
    else:
        send_line_notification("【エラー】レポートが1つも取得できませんでした。")
