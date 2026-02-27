"""
FRED API 數據抓取模組
負責從 FRED 取得最新數據、計算衍生指標（YoY%、NFP月增量）

環境變數需求：
    FRED_API_KEY  — 從 https://research.stlouisfed.org/useraccount/apikeys 取得
"""

import os
import time
import logging
from fredapi import Fred

from config import (
    INDICATORS,
    NFP_SERIES_ID,
    YOY_CALC_SERIES,
    FRED_URL_TEMPLATE,
    FRED_REQUEST_DELAY,
)

logger = logging.getLogger(__name__)

# ── 初始化 FRED 客戶端 ─────────────────────────────────────────
fred = Fred(api_key=os.environ["FRED_API_KEY"])


# ─────────────────────────────────────────────────────────────────
# 核心抓取函式
# ─────────────────────────────────────────────────────────────────

def fetch_latest(series_id: str) -> dict | None:
    """
    抓取單一 series 的最新觀測值。

    Returns:
        dict  — 包含 series_id、latest_date、latest_value 等欄位
        None  — 抓取失敗或數據為空
    """
    try:
        data = fred.get_series(series_id).dropna()
        info = fred.get_series_info(series_id)

        if data.empty:
            logger.warning(f"[{series_id}] 數據為空，跳過")
            return None

        latest_val  = float(data.iloc[-1])
        latest_date = data.index[-1].strftime("%Y-%m-%d")
        prev_val    = float(data.iloc[-2]) if len(data) >= 2 else None
        change      = round(latest_val - prev_val, 6) if prev_val is not None else None

        return {
            "series_id":       series_id,
            "latest_date":     latest_date,
            "latest_value":    round(latest_val, 4),
            "prev_value":      round(prev_val, 4) if prev_val is not None else None,
            "change":          change,
            "last_updated":    str(info["last_updated"]),
            "fred_title":      str(info["title"]),
            "frequency_short": str(info["frequency_short"]),
        }

    except Exception as e:
        logger.error(f"[{series_id}] FRED 抓取錯誤：{e}")
        return None


def fetch_nfp_change() -> dict | None:
    """
    計算非農就業月增量（千人）。
    PAYEMS 是就業人數水準值，需對它做 diff() 得到月增量。
    """
    try:
        data = fred.get_series(NFP_SERIES_ID).dropna()
        info = fred.get_series_info(NFP_SERIES_ID)

        nfp_chg     = data.diff()
        latest_chg  = float(nfp_chg.iloc[-1])
        latest_date = data.index[-1].strftime("%Y-%m-%d")
        prev_chg    = float(nfp_chg.iloc[-2]) if len(nfp_chg) >= 2 else None

        return {
            "series_id":       f"{NFP_SERIES_ID}_CHANGE",
            "latest_date":     latest_date,
            "latest_value":    round(latest_chg, 1),
            "prev_value":      round(prev_chg, 1) if prev_chg is not None else None,
            "change":          round(latest_chg - prev_chg, 1) if prev_chg else None,
            "last_updated":    str(info["last_updated"]),
            "fred_title":      "Nonfarm Payrolls MoM Change (thousands)",
            "frequency_short": "M",
        }

    except Exception as e:
        logger.error(f"[NFP Change] 計算錯誤：{e}")
        return None


def fetch_yoy_pct(series_id: str) -> dict | None:
    """
    計算月度 series 的 YoY 年增率（%）。
    使用 pct_change(12) 計算 12 個月前後的百分比變化。
    """
    try:
        data = fred.get_series(series_id).dropna()
        info = fred.get_series_info(series_id)

        periods = 4 if str(info["frequency_short"]) == "Q" else 12
        yoy = (data.pct_change(periods=periods) * 100).dropna()

        if yoy.empty:
            return None

        latest_yoy  = float(yoy.iloc[-1])
        latest_date = yoy.index[-1].strftime("%Y-%m-%d")
        prev_yoy    = float(yoy.iloc[-2]) if len(yoy) >= 2 else None

        return {
            "series_id":       f"{series_id}_YOY",
            "latest_date":     latest_date,
            "latest_value":    round(latest_yoy, 2),
            "prev_value":      round(prev_yoy, 2) if prev_yoy is not None else None,
            "change":          round(latest_yoy - prev_yoy, 2) if prev_yoy else None,
            "last_updated":    str(info["last_updated"]),
            "fred_title":      f"{info['title']} YoY %",
            "frequency_short": str(info["frequency_short"]),
        }

    except Exception as e:
        logger.error(f"[{series_id}_YOY] 計算錯誤：{e}")
        return None


# ─────────────────────────────────────────────────────────────────
# 分析輔助函式
# ─────────────────────────────────────────────────────────────────

def generate_analysis(data: dict) -> str:
    """根據數據變化自動生成簡短分析文字，寫入 Notion Notes 欄位。"""
    name   = data.get("display_name", data["series_id"])
    val    = data["latest_value"]
    prev   = data.get("prev_value")
    change = data.get("change")

    if prev is None or change is None:
        return f"{name}: {val}"

    direction  = "上升" if change > 0 else "下降" if change < 0 else "持平"
    pct_change = abs(change / prev * 100) if prev != 0 else 0

    text = f"{name} 最新值 {val}，較前值 {prev} {direction} {abs(change):.4f}"

    if pct_change > 10:
        text += f"（變動幅度 {pct_change:.1f}%，顯著異常⚠️）"
    elif pct_change > 5:
        text += f"（變動幅度 {pct_change:.1f}%，值得關注）"

    return text


def determine_signal(data: dict) -> str:
    """根據指標類型與變化方向判斷 Signal 標記。"""
    change   = data.get("change") or 0
    category = data.get("category", "")
    sid      = data.get("series_id", "")

    # 通膨：上升 → 負面（Fed 可能升息壓力）
    if category == "Inflation":
        return "🔴 Negative" if change > 0 else "🟢 Positive" if change < 0 else "⚪ Neutral"

    # 失業率：上升 → 負面
    if "UNRATE" in sid:
        return "🔴 Negative" if change > 0 else "🟢 Positive" if change < 0 else "⚪ Neutral"

    # 利差：負值（倒掛）→ 負面
    if "T10Y2Y" in sid:
        val = data.get("latest_value", 0)
        return "🔴 Negative" if val < 0 else "🟢 Positive" if val > 0.5 else "⚪ Neutral"

    # 其餘（GDP、零售、製造業、就業人數）：上升 → 正面
    if category in ("Growth", "Consumer", "Manufacturing", "Employment", "Housing"):
        return "🟢 Positive" if change > 0 else "🔴 Negative" if change < 0 else "⚪ Neutral"

    return "⚪ Neutral"


# ─────────────────────────────────────────────────────────────────
# 主要彙整函式
# ─────────────────────────────────────────────────────────────────

def fetch_all_indicators() -> list[dict]:
    """
    抓取所有設定中的指標，回傳結構化資料清單。
    包含原始值 + YoY 衍生指標 + NFP 月增量。
    """
    results = []

    for series_id, display_name, category, freq_label, calc_yoy in INDICATORS:
        logger.info(f"  抓取 {display_name} ({series_id})...")

        # 原始值
        obs = fetch_latest(series_id)
        if obs:
            obs["display_name"]    = display_name
            obs["category"]        = category
            obs["frequency_label"] = freq_label
            obs["source_url"]      = FRED_URL_TEMPLATE.format(series_id=series_id)
            obs["notes"]           = generate_analysis(obs)
            obs["signal"]          = determine_signal(obs)
            results.append(obs)

        # YoY 衍生指標
        if calc_yoy and series_id in YOY_CALC_SERIES:
            yoy_obs = fetch_yoy_pct(series_id)
            if yoy_obs:
                yoy_obs["display_name"]    = f"{display_name} YoY %"
                yoy_obs["category"]        = category
                yoy_obs["frequency_label"] = freq_label
                yoy_obs["source_url"]      = FRED_URL_TEMPLATE.format(series_id=series_id)
                yoy_obs["notes"]           = generate_analysis(yoy_obs)
                yoy_obs["signal"]          = determine_signal(yoy_obs)
                results.append(yoy_obs)

        time.sleep(FRED_REQUEST_DELAY)

    # NFP 月增量（特殊計算）
    nfp = fetch_nfp_change()
    if nfp:
        nfp["display_name"]    = "Nonfarm Payrolls MoM Change (K)"
        nfp["category"]        = "Employment"
        nfp["frequency_label"] = "Monthly"
        nfp["source_url"]      = FRED_URL_TEMPLATE.format(series_id=NFP_SERIES_ID)
        nfp["notes"]           = generate_analysis(nfp)
        nfp["signal"]          = determine_signal(nfp)
        results.append(nfp)

    logger.info(f"共取得 {len(results)} 筆指標數據")
    return results
