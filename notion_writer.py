"""
Notion API 寫入模組
負責查詢現有數據（防重複寫入）、寫入新數據、錯誤處理與重試

環境變數需求：
    NOTION_TOKEN       — Notion Integration Token（ntn_ 開頭）
    NOTION_DATABASE_ID — Notion 資料庫 ID（32 位英數字串）
"""

import os
import time
import logging
from notion_client import Client, APIResponseError

from config import NOTION_WRITE_DELAY

logger = logging.getLogger(__name__)

# ── 初始化 Notion 客戶端 ──────────────────────────────────────
notion      = Client(auth=os.environ["NOTION_TOKEN"])
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]


# ─────────────────────────────────────────────────────────────────
# 查詢函式
# ─────────────────────────────────────────────────────────────────

def get_existing_latest_date(series_id: str) -> str | None:
    """
    查詢 Notion DB 中某 Series ID 已存在的最新 Observation Date。
    用於判斷 FRED 最新數據是否已寫入，避免重複。

    Returns:
        'YYYY-MM-DD' 字串，或 None（代表尚無資料）
    """
    try:
        results = notion.databases.query(
            database_id=DATABASE_ID,
            filter={
                "property": "Series ID",
                "rich_text": {"equals": series_id}
            },
            sorts=[{
                "property": "Observation Date",
                "direction": "descending"
            }],
            page_size=1
        )

        if results["results"]:
            date_prop = results["results"][0]["properties"].get("Observation Date", {})
            if date_prop.get("date"):
                return date_prop["date"]["start"]

    except APIResponseError as e:
        logger.error(f"[Notion Query] {series_id} 查詢失敗：{e}")

    return None


def is_new_data(series_id: str, fred_latest_date: str) -> bool:
    """
    比對 FRED 最新觀測日期 vs Notion 已存在的最新日期。
    若 FRED 日期較新或 Notion 中無此 series，回傳 True。
    """
    existing_date = get_existing_latest_date(series_id)

    if existing_date is None:
        logger.info(f"  [{series_id}] Notion 中無歷史資料 → 視為新數據")
        return True

    if fred_latest_date > existing_date:
        logger.info(f"  [{series_id}] 發現新數據：{existing_date} → {fred_latest_date}")
        return True

    logger.info(f"  [{series_id}] 已是最新（{existing_date}），跳過")
    return False


# ─────────────────────────────────────────────────────────────────
# 寫入函式
# ─────────────────────────────────────────────────────────────────

def _build_properties(data: dict) -> dict:
    """將指標資料 dict 轉換為 Notion API 的 properties 格式。"""
    props = {
        "Indicator": {
            "title": [{"text": {"content": data["display_name"]}}]
        },
        "Series ID": {
            "rich_text": [{"text": {"content": data["series_id"]}}]
        },
        "Value": {
            "number": data["latest_value"]
        },
        "Observation Date": {
            "date": {"start": data["latest_date"]}
        },
        "Category": {
            "select": {"name": data["category"]}
        },
        "Frequency": {
            "select": {"name": data["frequency_label"]}
        },
        "Is new": {
            "checkbox": True
        },
    }

    # 選填欄位
    if data.get("prev_value") is not None:
        props["Previous Value"] = {"number": data["prev_value"]}

    if data.get("change") is not None:
        props["Change"] = {"number": round(data["change"], 4)}

    if data.get("source_url"):
        props["Source URL"] = {"url": data["source_url"]}

    if data.get("notes"):
        props["Notes"] = {
            "rich_text": [{"text": {"content": data["notes"][:2000]}}]
        }

    if data.get("signal"):
        props["Signal"] = {"select": {"name": data["signal"]}}

    return props


def write_indicator(data: dict, max_retries: int = 3) -> str | None:
    """
    將一筆指標數據寫入 Notion 資料庫（含指數退避重試）。

    Returns:
        新建頁面的 page_id，失敗回傳 None
    """
    props = _build_properties(data)

    for attempt in range(max_retries):
        try:
            response = notion.pages.create(
                parent={"database_id": DATABASE_ID},
                properties=props
            )
            logger.info(
                f"  ✅ [{data['series_id']}] 寫入成功："
                f"{data['display_name']} = {data['latest_value']}"
            )
            return response["id"]

        except APIResponseError as e:
            if "rate_limited" in str(e).lower() and attempt < max_retries - 1:
                wait = 2 ** attempt   # 1s → 2s → 4s
                logger.warning(f"  ⏳ Notion 速率限制，等待 {wait}s 後重試...")
                time.sleep(wait)
                continue
            logger.error(f"  ❌ [{data['series_id']}] 寫入失敗：{e}")
            return None

        except Exception as e:
            logger.error(f"  ❌ [{data['series_id']}] 未預期錯誤：{e}")
            return None

    return None


# ─────────────────────────────────────────────────────────────────
# 批次寫入
# ─────────────────────────────────────────────────────────────────

def batch_write(indicators: list[dict]) -> dict:
    """
    批次寫入多筆指標數據，自動跳過已存在的最新數據。

    Returns:
        {"new": int, "skipped": int, "failed": int}
    """
    stats = {"new": 0, "skipped": 0, "failed": 0}

    for data in indicators:
        sid = data["series_id"]

        if not is_new_data(sid, data["latest_date"]):
            stats["skipped"] += 1
            continue

        page_id = write_indicator(data)
        if page_id:
            stats["new"] += 1
        else:
            stats["failed"] += 1

        time.sleep(NOTION_WRITE_DELAY)

    return stats
