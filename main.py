import requests
from bs4 import BeautifulSoup
import os
import re
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

def get_resona_ultra(page_url):
    """りそな専用：日付が見つからなくてもPDFのURL規則性から抜き出す"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
    }
    try:
        res = requests.get(page_url, headers=headers, timeout=30)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')
        
        jst = timezone(timedelta(hours=9))
        today = datetime.now(jst)
        
        # 探したいキーワード（日付のバリエーション）
        date_patterns = [
            today.strftime("%Y年%m月%d日"),
            today.strftime("%-m月%-d日"), # 1月22日
            today.strftime("%Y%m%d")      # 20260122
        ]

        # 1. まずは日付テキストを足がかりに探す
        for dp in date_patterns:
            target = soup.find(string=re.compile(dp))
            if target:
                print(f"DEBUG: りそな日付発見 -> {dp}")
                curr = target.parent
                for _ in range(5):
                    nxt = curr.find_next('a', href=True)
                    if nxt and nxt['href'].lower().endswith('.pdf'):
                        return urljoin(page_url, nxt['href'])
                    curr = curr.parent

        # 2. ダメなら「market_daily」が含まれるPDFリンクをすべて取得して、最新（一番上）を出す
        print("DEBUG: 日付で見つからないためURLパターンで検索します")
        all_links = soup.find_all('a', href=True)
        for a in all_links:
            href = a['href'].lower()
            if "market_daily" in href and href.endswith('.pdf'):
                print(f"DEBUG: りそなURLパターン発見 -> {href}")
                return urljoin(page_url, a['href'])
                
    except Exception as e:
        print(f"DEBUG: りそな取得中にエラー -> {e}")
    return None

def get_pdf_url(page_url, keywords, find_first_pdf=False):
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

    # 各行の処理
    results = {
        "三菱UFJ": get_pdf_url("https://www.bk.mufg.jp/rept_mkt/gaitame/index.html", ["FX Daily"]),
        "みずほ": get_pdf_url("https://www.mizuhobank.co.jp/market/report.html", [], find_first_pdf=True),
        "三井住友": get_pdf_url("https://www.smbc.co.jp/market/", date_keys),
        "りそな": get_resona_ultra("https://www.resonabank.co.jp/kojin/market/daily/index.html")
    }

    for bank, url in results.items():
        if url:
            report_msg += f"\n■{bank}\n{url}\n"
            found_any = True
        else:
            print(f"DEBUG: {bank} が見つかりませんでした")

    if found_any:
        send_line_notification(report_msg)
    else:
        send_line_notification("本日のレポートはまだ見つかりません。")

if __name__ == "__main__":
    process_reports()
