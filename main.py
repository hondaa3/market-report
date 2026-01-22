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
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    payload = {"to": USER_ID, "messages": [{"type": "text", "text": msg}]}
    requests.post(url, headers=headers, json=payload)

def get_resona_url():
    """りそな：iPhone偽装で最新PDFを取得"""
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"}
    url = "https://www.resonabank.co.jp/kojin/market/daily/index.html"
    try:
        res = requests.get(url, headers=headers, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            if "market_daily" in a['href'].lower() and a['href'].endswith('.pdf'):
                return urljoin(url, a['href'])
    except: pass
    return None

def get_pdf_url(page_url, keywords, find_first_pdf=False):
    """汎用（MUFG, みずほ, SMBC）"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(page_url, headers=headers, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            if a['href'].lower().endswith('.pdf'):
                if find_first_pdf: return urljoin(page_url, a['href'])
                if any(k in a.get_text() or k in a['href'] for k in keywords):
                    return urljoin(page_url, a['href'])
    except: pass
    return None

def process_reports():
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst)
    date_keys = [today.strftime("%Y%m%d"), today.strftime("%m%d")]

    report_msg = f"【{today.strftime('%m/%d')} レポート速報】\n"
    found_any = False

    banks = {
        "三菱UFJ": get_pdf_url("https://www.bk.mufg.jp/rept_mkt/gaitame/index.html", ["FX Daily"]),
        "みずほ": get_pdf_url("https://www.mizuhobank.co.jp/market/report.html", [], find_first_pdf=True),
        "三井住友": get_pdf_url("https://www.smbc.co.jp/market/", date_keys),
        "りそな": get_resona_url()
    }

    for name, url in banks.items():
        if url:
            report_msg += f"\n■{name}\n{url}\n"
            found_any = True

    if found_any:
        send_line_notification(report_msg)

if __name__ == "__main__":
    process_reports()
