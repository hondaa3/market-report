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

def get_resona_final(page_url):
    """りそな専用：日付テキストとPDFリンクの距離が近くても遠くても捕まえるロジック"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(page_url, headers=headers, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')
        
        jst = timezone(timedelta(hours=9))
        today_str = datetime.now(jst).strftime("%Y年%m月%d日")
        yesterday_str = (datetime.now(jst) - timedelta(days=1)).strftime("%Y年%m月%d日")
        
        # 1. ページ内の全アンカータグを取得
        links = soup.find_all('a', href=True)
        
        # 2. 最新の日付（今日または昨日）を探す
        target_dates = [today_str, yesterday_str]
        
        for date_text in target_dates:
            # ページ全体からその日付の文字列を探す
            date_element = soup.find(string=lambda t: t and date_text in t)
            if date_element:
                # 日付が見つかった場所から、下方向に向かって最初に見つかるPDFリンクを返す
                # これにより、日付とリンクが別々のタグでも捕まえられます
                current = date_element.parent
                while current:
                    # 同じ親の中、またはその後の要素からaタグを探す
                    next_a = current.find_next('a', href=True)
                    if next_a and next_a['href'].lower().endswith('.pdf'):
                        return urljoin(page_url, next_a['href'])
                    current = current.parent # 見つからなければさらに親階層から探す
        
        # 3. 万が一上記で失敗した場合、全リンクから 'market_daily' を含む最新っぽいものを探す
        for a in links:
            if "market_daily" in a['href'].lower() and a['href'].endswith('.pdf'):
                return urljoin(page_url, a['href'])
                
    except: pass
    return None

def get_pdf_url(page_url, keywords, find_first_pdf=False):
    headers = {"User-Agent": "Mozilla/5.0"}
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

    # MUFG
    mufg = get_pdf_url("https://www.bk.mufg.jp/rept_mkt/gaitame/index.html", ["FX Daily"])
    if mufg:
        report_msg += f"\n■三菱UFJ\n{mufg}\n"
        found_any = True

    # Mizuho
    mizuho = get_pdf_url("https://www.mizuhobank.co.jp/market/report.html", [], find_first_pdf=True)
    if mizuho:
        report_msg += f"\n■みずほ\n{mizuho}\n"
        found_any = True

    # SMBC
    smbc = get_pdf_url("https://www.smbc.co.jp/market/", date_keys)
    if smbc:
        report_msg += f"\n■三井住友\n{smbc}\n"
        found_any = True

    # Resona (Final Attempt)
    resona = get_resona_final("https://www.resonabank.co.jp/kojin/market/daily/index.html")
    if resona:
        report_msg += f"\n■りそな\n{resona}\n"
        found_any = True

    if found_any:
        send_line_notification(report_msg)
    else:
        send_line_notification("レポートがまだ更新されていないようです。")

if __name__ == "__main__":
    process_reports()
