import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin
from datetime import datetime, timedelta, timezone

# --- 設定 ---
LINE_TOKEN = os.environ.get("LINE_TOKEN")
USER_ID = os.environ.get("USER_ID")

def send_line_notification(msg):
    """LINE Messaging APIを使用してプッシュ通知を送信"""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }
    payload = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": msg}]
    }
    try:
        res = requests.post(url, headers=headers, json=payload)
        print(f"LINE送信結果: {res.status_code}")
    except Exception as e:
        print(f"LINE送信失敗: {e}")

def get_resona_special(page_url):
    """
    りそな専用ロジック:
    日付テキスト（例：2026年1月22日号）を探し、その直後にあるPDFリンクを抽出する
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(page_url, headers=headers, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')
        
        jst = timezone(timedelta(hours=9))
        today_str = datetime.now(jst).strftime("%Y年%m月%d日")
        yesterday_str = (datetime.now(jst) - timedelta(days=1)).strftime("%Y年%m月%d日")

        # 1. まず今日、なければ昨日の日付を探す
        target_dates = [today_str, yesterday_str]
        
        for date_text in target_dates:
            # ページ内の全テキストから日付が含まれる要素を探す
            element = soup.find(string=lambda t: t and date_text in t)
            if element:
                # 日付が見つかった場所から、その次以降にある最初の <a> タグ（リンク）を探す
                # parentから辿ることで、同じ階層や隣の階層のリンクを確実に拾う
                current = element.parent
                for _ in range(5): # 最大5階層上まで遡って探索
                    next_link = current.find_next('a', href=True)
                    if next_link and next_link['href'].lower().endswith('.pdf'):
                        full_url = urljoin(page_url, next_link['href'])
                        print(f"りそな発見: {date_text} -> {full_url}")
                        return full_url
                    current = current.parent
    except Exception as e:
        print(f"りそな取得エラー: {e}")
    return None

def get_pdf_url(page_url, keywords, find_first_pdf=False):
    """
    汎用ロジック（MUFG, みずほ, SMBC用）:
    キーワード合致、またはページ内最初のPDFリンクを取得
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(page_url, headers=headers, timeout=20)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text(strip=True)
            
            if href.lower().endswith('.pdf'):
                # みずほ等、最新が一番上の場合
                if find_first_pdf:
                    return urljoin(page_url, href)
                
                # キーワード（日付やレポート名）に合致する場合
                if any(k in text or k in href for k in keywords):
                    return urljoin(page_url, href)
    except Exception as e:
        print(f"取得エラー ({page_url}): {e}")
    return None

def process_reports():
    """全銀行を巡回してレポートをまとめ、LINEへ送る"""
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst)
    
    # 検索用キーワード（今日の日付パターン）
    date_keys = [today.strftime("%Y%m%d"), today.strftime("%m%d")]

    report_msg = f"【{today.strftime('%m/%d')} レポート速報】\n"
    found_any = False

    # 1. 三菱UFJ (MUFG)
    mufg = get_pdf_url("https://www.bk.mufg.jp/rept_mkt/gaitame/index.html", ["FX Daily"])
    if mufg:
        report_msg += f"\n■三菱UFJ (FX Daily)\n{mufg}\n"
        found_any = True

    # 2. みずほ (Mizuho) - ページ内最初のPDFを最新とみなす
    mizuho = get_pdf_url("https://www.mizuhobank.co.jp/market/report.html", [], find_first_pdf=True)
    if mizuho:
        report_msg += f"\n■みずほ (為替)\n{mizuho}\n"
        found_any = True

    # 3. 三井住友 (SMBC)
    smbc = get_pdf_url("https://www.smbc.co.jp/market/", date_keys)
    if smbc:
        report_msg += f"\n■三井住友 (マーケット)\n{smbc}\n"
        found_any = True

    # 4. りそな (Resona) - 特殊ロジック
    resona = get_resona_special("https://www.resonabank.co.jp/kojin/market/daily/index.html")
    if resona:
        report_msg += f"\n■りそな (デイリー)\n{resona}\n"
        found_any = True

    # 結果の送信
    if found_any:
        send_line_notification(report_msg)
        print("LINE通知を送信しました。")
    else:
        # どこも見つからなかった場合
        send_line_notification("本日のレポートはまだ更新されていないようです。")
        print("レポートが見つかりませんでした。")

if __name__ == "__main__":
    process_reports()
