import requests
from bs4 import BeautifulSoup
import PyPDF2
import os
import re
from urllib.parse import urljoin
from datetime import datetime, timedelta, timezone

# --- 設定 ---
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

def get_pdf_url(page_url, keywords):
    """ページ内からキーワードに合致するPDFリンクを1つ抽出する"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(page_url, headers=headers, timeout=20)
        res.encoding = res.apparent_encoding # 文字化け対策
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for a in soup.find_all('a', href=True):
            link_text = a.get_text(strip=True)
            link_href = a['href']
            
            # キーワードのいずれかがリンクテキストまたはURLに含まれているか確認
            if any(k in link_text or k in link_href for k in keywords):
                if link_href.endswith('.pdf'):
                    return urljoin(page_url, link_href)
    except Exception as e:
        print(f"Error scanning {page_url}: {e}")
    return None

def download_and_merge():
    merger = PyPDF2.PdfMerger()
    downloaded_files = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    # 日本時間の日付を取得
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst)
    yesterday = today - timedelta(days=1)
    
    # ターゲット設定
    targets = [
        # 三菱UFJ: "FX Daily" というテキストのリンク
        {"name": "MUFG", "page": "https://www.bk.mufg.jp/rept_mkt/gaitame/index.html", "keys": ["FX Daily"]},
        # みずほ: "外国為替ダイジェスト" というテキスト
        {"name": "Mizuho", "page": "https://www.mizuhobank.co.jp/market/report.html", "keys": ["外国為替ダイジェスト"]},
        # 三井住友: 当日または前日の日付(PDF 104KB)のような形式
        {"name": "SMBC", "page": "https://www.smbc.co.jp/market/", "keys": [today.strftime("%Y年%m月%d日"), yesterday.strftime("%Y年%m月%d日")]},
        # りそな: 2026年1月21日号 のような日付関連
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
                    print(f"成功: {target['name']} -> {pdf_url}")
            except Exception as e:
                print(f"DL失敗: {target['name']} - {e}")

    if downloaded_files:
        output_file = "Daily_Market_Report.pdf"
        merger.write(output_file)
        merger.close()
        return output_file
    return None

def send_line_notification(msg):
    # GitHubの実行結果画面へのURL（あなたのユーザー名とリポジトリ名に合わせてください）
    artifact_url = "https://github.com/hondaa3/market-report/actions"
    
    full_msg = f"{msg}\n\n下記URLの最新の実行結果からPDFをダウンロードしてください：\n{artifact_url}"
    
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    payload = {"to": USER_ID, "messages": [{"type": "text", "text": full_msg}]}
    requests.post(url, headers=headers, json=payload)
