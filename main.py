import requests
from bs4 import BeautifulSoup
import PyPDF2
import os
from urllib.parse import urljoin

# --- 設定 ---
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

def get_latest_pdf_from_page(page_url, search_text):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(page_url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        # リンクの中で指定したテキスト（例: "FX Daily"）を含むものを探す
        for a in soup.find_all('a', href=True):
            if search_text in a.text or search_text in a['href']:
                if a['href'].endswith('.pdf'):
                    return urljoin(page_url, a['href'])
    except Exception as e:
        print(f"Error scanning {page_url}: {e}")
    return None

def download_and_merge():
    merger = PyPDF2.PdfMerger()
    downloaded_files = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    # 各銀行の「レポート一覧ページ」と「探すキーワード」
    targets = [
        {"name": "MUFG", "page": "https://www.bk.mufg.jp/rept_mkt/gaitame/index.html", "key": "fxdaily.pdf"},
        {"name": "Mizuho", "page": "https://www.mizuhobank.co.jp/market/report.html", "key": "fxdigest.pdf"},
        {"name": "SMBC", "page": "https://www.smbc.co.jp/market/", "key": "marketreport"},
    ]

    for target in targets:
        pdf_url = get_latest_pdf_from_page(target['page'], target['key'])
        if pdf_url:
            try:
                res = requests.get(pdf_url, headers=headers, timeout=20)
                if res.status_code == 200:
                    filename = f"{target['name']}.pdf"
                    with open(filename, "wb") as f:
                        f.write(res.content)
                    merger.append(filename)
                    downloaded_files.append(filename)
                    print(f"成功: {target['name']} -> {pdf_url}")
            except:
                print(f"失敗: {target['name']}")

    if downloaded_files:
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
        send_line_notification("【成功】サイトから最新のレポートリンクを探して結合しました。")
    else:
        send_line_notification("【失敗】ページ内にレポートが見つかりませんでした。")
