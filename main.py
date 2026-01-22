import requests
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

def check_url_exists(url):
    """URLが実際に存在するか（PDFがあるか）確認する"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.head(url, headers=headers, timeout=10)
        return response.status_code == 200
    except:
        return False

def get_resona_direct():
    """りそな専用：URLの規則性から直接ファイルを特定する"""
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    
    # 候補1: 今日 (例: 260122)
    # 候補2: 昨日 (土日の場合などを考慮)
    for i in range(3):
        target_date = now - timedelta(days=i)
        # りそなの命名規則: YYMMDD.pdf
        file_name = target_date.strftime("%y%m%d") + ".pdf"
        url = f"https://www.resonabank.co.jp/kojin/market/daily/pdf/{file_name}"
        
        if check_url_exists(url):
            return url
    return None

def get_pdf_url(page_url, keywords, find_first_pdf=False):
    """汎用 (MUFG, みずほ, SMBC用)"""
    from bs4 import BeautifulSoup
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

    # 1. 三菱UFJ
    mufg = get_pdf_url("https://www.bk.mufg.jp/rept_mkt/gaitame/index.html", ["FX Daily"])
    if mufg:
        report_msg += f"\n■三菱UFJ\n{mufg}\n"
        found_any = True

    # 2. みずほ
    mizuho = get_pdf_url("https://www.mizuhobank.co.jp/market/report.html", [], find_first_pdf=True)
    if mizuho:
        report_msg += f"\n■みずほ\n{mizuho}\n"
        found_any = True

    # 3. 三井住友
    smbc = get_pdf_url("https://www.smbc.co.jp/market/", date_keys)
    if smbc:
        report_msg += f"\n■三井住友\n{smbc}\n"
        found_any = True

    # 4. りそな (直接アタック)
    resona = get_resona_direct()
    if resona:
        report_msg += f"\n■りそな\n{resona}\n"
        found_any = True

    if found_any:
        send_line_notification(report_msg)
    else:
        send_line_notification("レポートが更新されていません。")

if __name__ == "__main__":
    process_reports()
