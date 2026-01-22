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

def test_smbc():
    """三井住友の『日次更新』リンクを徹底捜索"""
    url = "https://www.smbc.co.jp/market/"
    try:
        res = requests.get(url, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')
        
        links = soup.find_all('a', href=True)
        for a in links:
            txt = a.get_text().strip()
            # 「日次更新」という文字が入っているリンクをすべてチェック
            if "日次更新" in txt:
                pdf_url = urljoin(url, a['href'])
                return f"✅発見: {txt}\n{pdf_url}"
        return f"❌『日次更新』という文字のリンクが見つかりません (全{len(links)}件中)"
    except Exception as e:
        return f"⚠️通信エラー: {str(e)}"

def test_resona():
    """りそなのURL直接アタックをテスト"""
    jst = timezone(timedelta(hours=9))
    date_str = datetime.now(jst).strftime("%y%m%d")
    target = f"https://www.resonabank.co.jp/kojin/market/daily/pdf/{date_str}.pdf"
    
    try:
        res = requests.head(target, timeout=10, allow_redirects=True)
        if res.status_code == 200:
            return f"✅直接発見: {target}"
        else:
            return f"❌直接URLなし (Status:{res.status_code})\nURL: {target}"
    except Exception as e:
        return f"⚠️エラー: {str(e)}"

def test_others(name, url, keyword=None, first=False):
    """三菱・みずほの簡易テスト"""
    try:
        res = requests.get(url, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            if a['href'].endswith('.pdf'):
                if first or (keyword and keyword in a.get_text()):
                    return f"✅発見: {urljoin(url, a['href'])}"
        return "❌PDFリンクが見つかりません"
    except:
        return "⚠️サイトにアクセスできません"

def process_reports():
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    
    msg = f"【接続テスト中：{now.strftime('%H:%M:%S')}】\n"
    
    msg += f"\n■三井住友 (日次狙い)\n{test_smbc()}\n"
    msg += f"\n■りそな (URL直接狙い)\n{test_resona()}\n"
    msg += f"\n■三菱UFJ\n{test_others('三菱', 'https://www.bk.mufg.jp/rept_mkt/gaitame/index.html', 'FX Daily')}\n"
    msg += f"\n■みずほ\n{test_others('みずほ', 'https://www.mizuhobank.co.jp/market/report.html', first=True)}\n"

    send_line(msg)

if __name__ == "__main__":
    process_reports()
