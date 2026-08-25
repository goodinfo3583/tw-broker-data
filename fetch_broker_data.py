# -*- coding: utf-8 -*-
"""Fetch broker branch trading data from Fubon e-Broker website.
使用 Playwright 自動化抓取富邦網站的券商分點交易數據 (已解鎖筆數限制)。
"""

import os
import re
import time
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo
import pandas as pd

TPE = ZoneInfo("Asia/Taipei")

def _resolve_trade_date(date_text: str) -> str:
    m = re.search(r"(\d{1,2})/(\d{1,2})", date_text or "")
    if not m:
        return ""
    month, day = int(m.group(1)), int(m.group(2))
    today = datetime.now(TPE).date()
    year = today.year - 1 if month > today.month else today.year
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return ""

try:
    from playwright.sync_api import sync_playwright, Browser, Page
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    print("Warning: playwright not installed. Run: pip install playwright && playwright install chromium")

BASE_URL = "https://fubon-ebrokerdj.fbs.com.tw"
BROKER_TRADING_URL = BASE_URL + "/z/zc/zco/zco_{code}.djhtm"
BROKER_HISTORY_URL = BASE_URL + "/z/zc/zco/zco0/zco0.djhtm?a={code}&b={broker_id}"

_browser: Optional["Browser"] = None
_playwright = None

def _get_browser() -> "Browser":
    global _browser, _playwright
    if not HAS_PLAYWRIGHT:
        raise RuntimeError("Playwright is not installed")
    
    if _browser is None:
        _playwright = sync_playwright().start()
        try:
            # 這裡的 headless=True 代表在背景默默執行不跳視窗
            _browser = _playwright.chromium.launch(headless=True)
        except Exception:
            _playwright.stop()
            _playwright = None
            _browser = None
            raise
    
    return _browser

def close_browser():
    global _browser, _playwright
    if _browser:
        _browser.close()
        _browser = None
    if _playwright:
        _playwright.stop()
        _playwright = None

def _parse_number(text: str) -> int:
    if not text or text.strip() in ("", "-"):
        return 0
    text = text.strip().replace(",", "").replace(" ", "")
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    try:
        return int(float(text))
    except ValueError:
        return 0

def _parse_percent(text: str) -> float:
    if not text or text.strip() in ("", "-"):
        return 0.0
    text = text.strip().replace("%", "").replace(",", "")
    try:
        return float(text)
    except ValueError:
        return 0.0

def fetch_broker_trading(stock_code: str, target_date: Optional[str] = None) -> pd.DataFrame:
    if not HAS_PLAYWRIGHT:
        raise RuntimeError("Playwright is not installed")
    
    browser = _get_browser()
    page = browser.new_page()
    
    try:
        url = BROKER_TRADING_URL.format(code=stock_code)
        page.goto(url, wait_until="networkidle", timeout=30000)
        
        # 等待主要表格出現
        page.wait_for_selector("table.t01", timeout=10000)
        

        # =========================================================
        
        if target_date:
            try:
                def _canon(s: str) -> str:
                    m = re.search(r"(\d{1,2})/(\d{1,2})", s or "")
                    return f"{int(m.group(1)):02d}/{int(m.group(2)):02d}" if m else ""

                want = _canon(target_date)
                select = page.query_selector("select")
                if select and want:
                    options = select.query_selector_all("option")
                    for opt in options:
                        val = opt.get_attribute("value") or ""
                        if _canon(val) == want:
                            select.select_option(value=val)
                            page.wait_for_load_state("networkidle")
                            break
            except Exception:
                pass
        
        records = []
        table = page.query_selector("table.t01")
        if not table:
            return pd.DataFrame()
        
        rows = table.query_selector_all("tr")
        date_text = ""
        for row in rows[:5]:
            row_text = row.inner_text()
            match = re.search(r"(\d{1,2}/\d{1,2})", row_text)
            if match:
                date_text = match.group(1)
                break

        trade_date = _resolve_trade_date(date_text)
        
        data_start_idx = 0
        for i, row in enumerate(rows):
            cells = row.query_selector_all("td")
            if len(cells) >= 10:
                cell_texts = [c.inner_text().strip() for c in cells]
                if "買超券商" in cell_texts[0] and "賣超券商" in cell_texts[5]:
                    data_start_idx = i + 1
                    break
        
        rank = 0
        for row in rows[data_start_idx:]:
            cells = row.query_selector_all("td")
            if len(cells) < 10:
                continue
            
            rank += 1
            
            # 買超方
            buy_broker_cell = cells[0]
            buy_broker_link = buy_broker_cell.query_selector("a")
            if buy_broker_link:
                buy_broker_name = buy_broker_link.inner_text().strip()
                href = buy_broker_link.get_attribute("href") or ""
                match = re.search(r"b=([^&]+)", href)
                buy_broker_id = match.group(1) if match else ""
            else:
                buy_broker_name = buy_broker_cell.inner_text().strip()
                buy_broker_id = ""
            
            if buy_broker_name and buy_broker_name != "買超券商":
                buy_vol = _parse_number(cells[1].inner_text())
                sell_vol = _parse_number(cells[2].inner_text())
                net_vol = _parse_number(cells[3].inner_text())
                pct = _parse_percent(cells[4].inner_text())
                
                records.append({
                    "date": date_text,
                    "trade_date": trade_date,
                    "stock_code": stock_code,
                    "broker_name": buy_broker_name,
                    "broker_id": buy_broker_id,
                    "buy_vol": buy_vol,
                    "sell_vol": sell_vol,
                    "net_vol": net_vol,
                    "pct": pct,
                    "rank": rank,
                    "side": "buy"
                })
            
            # 賣超方
            sell_broker_cell = cells[5]
            sell_broker_link = sell_broker_cell.query_selector("a")
            if sell_broker_link:
                sell_broker_name = sell_broker_link.inner_text().strip()
                href = sell_broker_link.get_attribute("href") or ""
                match = re.search(r"b=([^&]+)", href)
                sell_broker_id = match.group(1) if match else ""
            else:
                sell_broker_name = sell_broker_cell.inner_text().strip()
                sell_broker_id = ""
            
            if sell_broker_name and sell_broker_name != "賣超券商":
                buy_vol = _parse_number(cells[6].inner_text())
                sell_vol = _parse_number(cells[7].inner_text())
                net_vol = _parse_number(cells[8].inner_text())
                pct = _parse_percent(cells[9].inner_text())
                
                records.append({
                    "date": date_text,
                    "trade_date": trade_date,
                    "stock_code": stock_code,
                    "broker_name": sell_broker_name,
                    "broker_id": sell_broker_id,
                    "buy_vol": buy_vol,
                    "sell_vol": sell_vol,
                    "net_vol": -abs(net_vol), 
                    "pct": pct,
                    "rank": rank,
                    "side": "sell"
                })
        
        return pd.DataFrame(records)
    
    finally:
        page.close()

# Cleanup on module unload
import atexit
atexit.register(close_browser)

if __name__ == "__main__":
    # ==========================================
    # 🌟 本地端測試區塊
    # ==========================================
    # 讓程式知道存檔位置 (與腳本同目錄下的 data 資料夾)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    os.chdir(BASE_DIR)
    
    SAVE_DIR = os.path.join(BASE_DIR, "data")
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

    print("=" * 60)
    print("開始測試爬取台積電 (2330) 分點資料...")
    print("=" * 60)
    
    # 執行主爬蟲功能
    df = fetch_broker_trading("2330")
    
    if not df.empty:
        # 將抓到的資料存成 CSV，讓你親眼見證成果
        test_file = os.path.join(SAVE_DIR, "2330_test_brokers.csv")
        df.to_csv(test_file, index=False, encoding="utf-8-sig")
        
        print(f"\n✅ 測試大成功！")
        print(f"👉 總共抓取到 {len(df)} 筆分點明細 (買超+賣超)。")
        print(f"👉 檔案已經儲存到: {test_file}")
        print("💡 你現在可以去 data 資料夾打開這個檔案，確認排名是不是超過 15 名了！")
    else:
        print("❌ 抓取失敗，沒有獲取到任何資料。")
    
    close_browser()
