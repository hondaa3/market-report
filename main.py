import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin
from datetime import datetime, timedelta, timezone

# --- 設定 ---
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

def send_line_notification(msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }
    payload = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": msg}]
    }
    res = requests.post(url, headers=headers, json=payload)
    print(f"LINE送信結果: {res.status_code}")

def get_resona_pdf(page_url):
    """りそな専用：テーブル内の最初のPDFを抽出"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(page_url, headers=headers, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')
        # 最新号が入っているテーブル（sp-fmt01）を探す
        table = soup.find('table', class_='sp-fmt01')
        if table:
            a = table.find('a', href=True)
            if a and a['href'].lower().endswith('.pdf'):
                return urljoin(page_url, a['href'])
    except: pass
    return None

def get_pdf_url(page_url, keywords, find_first_pdf=False):
    """汎用取得ロジック"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(page_url, headers=headers, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            link_text = a.get_text(strip=True)
            link_href = a['href']
            if link_href.lower().endswith('.pdf'):
                if find_first_pdf:
                    return urljoin(page_url, link_href)
                if any(k in link_text or k in link_href for k in keywords):
                    return urljoin(page_url, link_href)
    except: pass
    return None

def process_reports():
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst)
    yesterday = today - timedelta(days=1)
    
    date_keys = [
        today.strftime("%Y%m%d"), 
        today.strftime("%Y年%m月%d日"),
        today.strftime("%m%d"),
        yesterday.strftime("%Y%m%d"),
        yesterday.strftime("%Y年%m月%d日")
    ]

    report_msg = f"【{today.strftime('%m/%d')} レポート速報】\n"
    found_any = False

    # 各行の取得処理
    # 1. MUFG
    mufg = get_pdf_url("https://www.bk.mufg.jp/rept_mkt/gaitame/index.html", ["FX Daily"])
    if mufg:
        report_msg += f"\n■三菱UFJ (FX Daily)\n{mufg}\n"
        found_any = True

    # 2. みずほ
    mizuho = get_pdf_url("https://www.mizuhobank.co.jp/market/report.html", [], find_first_pdf=True)
    if mizuho:
        report_msg += f"\n■みずほ (為替ダイジェスト)\n{mizuho}\n"
        found_any = True

    # 3. 三井住友
    smbc = get_pdf_url("https://www.smbc.co.jp/market/", date_keys)
    if smbc:
        report_msg += f"\n■三井住友 (マーケット)\n{smbc}\n"
        found_any = True

    # 4. りそな (専用ロジック)
    resona = get_resona_pdf("https://www.resonabank.co.jp/kojin/market/daily/index.html")
    if resona:
        report_msg += f"\n■りそな (デイリー)\n{resona}\n"
        found_any = True

    if found_any:
        send_line_notification(report_msg)
    else:
        send_line_notification("レポートがまだ更新されていないようです。")

if __name__ == "__main__":
    process_reports()
