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

def get_pdf_url(page_url, keywords, find_first_pdf=False):
    """
    find_first_pdf=True にすると、キーワードに拘らずそのページで最初に見つかったPDFを返す
    (みずほ等、最新が一番上にあるサイト用)
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(page_url, headers=headers, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for a in soup.find_all('a', href=True):
            link_text = a.get_text(strip=True)
            link_href = a['href']
            
            # PDFリンクかチェック
            if link_href.lower().endswith('.pdf'):
                # モード1: 最初のPDFを拾う (みずほ用)
                if find_first_pdf:
                    return urljoin(page_url, link_href)
                # モード2: キーワードで探す (MUFG, SMBC用)
                if any(k in link_text or k in link_href for k in keywords):
                    return urljoin(page_url, link_href)
    except Exception as e:
        print(f"Error scanning {page_url}: {e}")
    return None

def process_reports():
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst)
    yesterday = today - timedelta(days=1)
    
    # 検索キーワードのバリエーションを増やす
    date_keys = [
        today.strftime("%Y%m%d"), 
        today.strftime("%Y年%m月%d日"),
        today.strftime("%m%d"),
        yesterday.strftime("%Y%m%d"),
        yesterday.strftime("%Y年%m月%d日")
    ]

    targets = [
        {"name": "三菱UFJ (FX Daily)", "page": "https://www.bk.mufg.jp/rept_mkt/gaitame/index.html", "keys": ["FX Daily"], "first": False},
        {"name": "みずほ (為替)", "page": "https://www.mizuhobank.co.jp/market/report.html", "keys": [], "first": True},
        {"name": "三井住友 (マーケット)", "page": "https://www.smbc.co.jp/market/", "keys": date_keys, "first": False},
        {"name": "りそな (デイリー)", "page": "https://www.resonabank.co.jp/kojin/market/daily/index.html", "keys": ["market_daily"] + date_keys, "first": False}
    ]

    report_msg = f"【{today.strftime('%m/%d')} レポート速報】\n"
    found_any = False

    for target in targets:
        pdf_url = get_pdf_url(target['page'], target['keys'], find_first_pdf=target['first'])
        if pdf_url:
            report_msg += f"\n■{target['name']}\n{pdf_url}\n"
            found_any = True
            print(f"成功: {target['name']}")
        else:
            print(f"未発見: {target['name']}")

    if found_any:
        send_line_notification(report_msg)
    else:
        send_line_notification("本日のレポートはまだ更新されていないか、見つかりませんでした。")

if __name__ == "__main__":
    process_reports()
