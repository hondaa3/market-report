import requests
import PyPDF2
import os
from datetime import datetime, timedelta, timezone

# --- 設定 ---
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

def get_pdf_urls():
    urls = []
    # 日本時間 (JST) を取得
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    
    # サイトによっては更新が遅いので、10時前なら昨日の日付にするなどの調整も可能
    # ここでは実行時点の「今日」の日付を使用
    today_str = now.strftime("%Y%m%d")
    
    # 1. 三菱UFJ (固定URL: 更新されると中身が書き換わる)
    urls.append("https://www.bk.mufg.jp/rept_mkt/gaitame/pdf/fxdaily.pdf")
    
    # 2. みずほ銀行 (固定URL)
    urls.append("https://www.mizuhobank.co.jp/market/pdf/daily/fxdigest.pdf")
    
    # 3. 三井住友銀行 (日付が含まれるタイプ)
    urls.append(f"https://www.smbc.co.jp/market/pdf/marketreport_{today_str}.pdf")
    
    return urls

def download_and_merge(pdf_urls):
    merger = PyPDF2.PdfMerger()
    downloaded_count = 0
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    for i, url in enumerate(pdf_urls):
        try:
            res = requests.get(url, headers=headers, timeout=20)
            # ステータスコードが200(成功)かつ、中身がPDFであることを確認
            if res.status_code == 200 and res.content.startswith(b'%PDF'):
                filename = f"tmp_{i}.pdf"
                with open(filename, "wb") as f:
                    f.write(res.content)
                merger.append(filename)
                downloaded_count += 1
                print(f"成功: {url}")
            else:
                print(f"スキップ(未更新または不在): {url} (Status: {res.status_code})")
        except Exception as e:
            print(f"エラー: {url} - {e}")
            
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
    urls = get_pdf_urls()
    merged_pdf = download_and_merge(urls)
    
    if merged_pdf:
        send_line_notification(f"【成功】レポートをまとめました。")
    else:
        # 1つも取れなかった場合は、まだ更新されていない可能性が高い
        send_line_notification("【通知】まだ本日のレポートが更新されていないようです。後ほど再試行します。")
