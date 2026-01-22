import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin
from datetime import datetime, timedelta, timezone

# --- 設定 ---
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

def send_line(msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    payload = {"to": USER_ID, "messages": [{"type": "text", "text": msg}]}
    requests.post(url, headers=headers, json=payload)

def get_resona_url():
    """りそな：西暦4桁の直撃URL ＋ HTML解析の2段構え"""
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    
    # 形式: 20260122.pdf (HTMLから判明した新ルール)
    date_str = now.strftime("%Y%m%d")
    direct_url = f"https://www.resonabank.co.jp/kojin/market/daily/pdf/{date_str}.pdf"
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # 1. 直接URLが存在するか確認（これが一番速くて確実）
    try:
        res = requests.head(direct_url, headers=headers, timeout=10)
        if res.status_code == 200:
            return direct_url
    except: pass
    
    # 2. ダメならHTMLを解析（最新号ブロックを狙う）
    try:
        page_url = "https://www.resonabank.co.jp/kojin/market/daily/index.html"
        res = requests.get(page_url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 「最新号」という文字の近くにあるPDFリンクを探す
        for a in soup.find_all('a', href=True):
            if "/pdf/" in a['href'] and a['href'].endswith('.pdf'):
                return urljoin(page_url, a['href'])
    except: pass
    return None

def get_smbc_daily():
    """三井住友：『日次更新』リンク"""
    url = "https://www.smbc.co.jp/market/"
    try:
        res = requests.get(url, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            if "日次更新" in a.get_text() and a['href'].endswith('.pdf'):
                return urljoin(url, a['href'])
    except: pass
    return None

def get_simple_pdf(page_url, keyword=None, first=False):
    """三菱UFJ・みずほ"""
    try:
        res = requests.get(page_url, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            if a['href'].lower().endswith('.pdf'):
                if first or (keyword and keyword in a.get_text()):
                    return urljoin(page_url, a['href'])
    except: pass
    return None

def process_reports():
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst)
    
    report_msg = f"【{today.strftime('%m/%d')} レポート速報】\n"
    found_any = False

    banks = {
        "三菱UFJ": get_simple_pdf("https://www.bk.mufg.jp/rept_mkt/gaitame/index.html", "FX Daily"),
        "みずほ": get_simple_pdf("https://www.mizuhobank.co.jp/market/report.html", first=True),
        "三井住友": get_smbc_daily(),
        "りそな": get_resona_url()
    }

    for name, url in banks.items():
        if url:
            report_msg += f"\n■{name}\n{url}\n"
            found_any = True

    if found_any:
        send_line(report_msg)

if __name__ == "__main__":
    process_reports()
