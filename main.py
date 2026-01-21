import requests
from bs4 import BeautifulSoup
import PyPDF2
import os
from datetime import datetime

# --- 設定 ---
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

def get_pdf_urls():
    urls = []
    today_str = datetime.now().strftime("%Y%m%d") # 20260122形式
    
    # 1. 三菱UFJ (固定URLが多い)
    urls.append("https://www.bk.mufg.jp/rept_mkt/gaitame/pdf/fxdaily.pdf")
    
    # 2. みずほ銀行 (固定URL)
    urls.append("https://www.mizuhobank.co.jp/market/pdf/daily/fxdigest.pdf")
    
    # 3. 三井住友銀行 (日付がURLに含まれる)
    urls.append(f"https://www.smbc.co.jp/market/pdf/marketreport_{today_str}.pdf")
    
    # 4. りそな銀行 (HTMLページなので今回はテキストリンクとして扱うか、
    # もしPDF版のURLが特定できれば追加。一旦は上記3つを優先)
    
    return urls

def download_and_merge(pdf_urls):
    merger = PyPDF2.PdfMerger()
    downloaded_count = 0
    
    for i, url in enumerate(pdf_urls):
        try:
            res = requests.get(url, timeout=15)
            if res.status_code == 200 and b'%PDF' in res.content[:100]:
                filename = f"tmp_{i}.pdf"
                with open(filename, "wb") as f:
                    f.write(res.content)
                merger.append(filename)
                downloaded_count += 1
                print(f"成功: {url}")
            else:
                print(f"取得失敗(PDFなし): {url}")
        except Exception as e:
            print(f"エラー: {url} - {e}")
            
    if downloaded_count > 0:
        output_file = "Daily_Market_Report.pdf"
        merger.write(output_file)
        merger.close()
        return output_file
    return None

def send_line_notification(file_path):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }
    
    # PDF本体を直接送るにはサーバーが必要なため、
    # まずは「結合完了」の報告と、どの銀行が取れたかを送ります。
    msg = f"【自動通知】{datetime.now().strftime('%m/%d')}のレポートをまとめました！\n"
    msg += "※GitHubのActionsタブから成果物(Artifacts)をダウンロードできます。"
    
    payload = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": msg}]
    }
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    urls = get_pdf_urls()
    merged_pdf = download_and_merge(urls)
    if merged_pdf:
        send_line_notification(merged_pdf)
    else:
        print("PDFが一つも取得できませんでした。")
