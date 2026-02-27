"""
美國總經數據自動化追蹤系統 — 主程式
整合 FRED API 抓取 + Notion 寫入的完整流程

執行方式：
    python macro_tracker.py

必要環境變數（可放在 .env 檔案或 GitHub Secrets）：
    FRED_API_KEY       — FRED API 金鑰
    NOTION_TOKEN       — Notion Integration Token
    NOTION_DATABASE_ID — Notion 資料庫 ID
"""

import logging
import sys
from datetime import datetime, timezone

# 本地開發支援 .env 檔案，GitHub Actions 環境不需要
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fred_fetcher import fetch_all_indicators
from notion_writer import batch_write

# ── 設定 Logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

DIVIDER = "=" * 60


def main() -> None:
    start_time = datetime.now(timezone.utc)

    logger.info(DIVIDER)
    logger.info("🚀 美國總經數據追蹤系統啟動")
    logger.info(f"⏰ 執行時間（UTC）：{start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(DIVIDER)

    # ── Step 1：從 FRED 抓取所有指標最新數據 ─────────────────
    logger.info("📡 Step 1：正在從 FRED API 抓取數據...")
    indicators = fetch_all_indicators()

    if not indicators:
        logger.warning("⚠️  未取得任何指標數據，程式結束")
        sys.exit(0)

    logger.info(f"📊 成功取得 {len(indicators)} 筆指標數據")
    logger.info(DIVIDER)

    # ── Step 2：寫入 Notion（含重複檢查）────────────────────
    logger.info("📝 Step 2：正在寫入 Notion 資料庫...")
    stats = batch_write(indicators)

    # ── Step 3：輸出執行摘要 ──────────────────────────────────
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(DIVIDER)
    logger.info("📋 執行摘要")
    logger.info(f"   ✅ 新增寫入：{stats['new']} 筆")
    logger.info(f"   ⏭️  已是最新跳過：{stats['skipped']} 筆")
    logger.info(f"   ❌ 寫入失敗：{stats['failed']} 筆")
    logger.info(f"   ⏱️  總耗時：{elapsed:.1f} 秒")
    logger.info(DIVIDER)

    # 若有失敗，以非零 exit code 結束（GitHub Actions 會標記為 failed）
    if stats["failed"] > 0:
        logger.error(f"有 {stats['failed']} 筆數據寫入失敗，請檢查上方 log")
        sys.exit(1)


if __name__ == "__main__":
    main()
