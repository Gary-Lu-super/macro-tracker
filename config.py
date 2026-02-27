"""
總經指標設定檔
定義所有追蹤的 FRED Series ID、分類、頻率與顯示名稱

欄說明：(Series ID, 顯示名稱, 分類, 頻率標籤, 是否計算YoY%)
"""

INDICATORS = [
    # ── 利率與貨幣政策 ──────────────────────────────────────────
    ("DFEDTARU",  "Fed Funds Target Upper",    "Interest Rate",  "Daily",     False),
    ("DFEDTARL",  "Fed Funds Target Lower",    "Interest Rate",  "Daily",     False),
    ("FEDFUNDS",  "Fed Funds Effective Rate",  "Interest Rate",  "Monthly",   False),
    ("DGS10",     "10Y Treasury Yield",         "Interest Rate",  "Daily",     False),
    ("DGS2",      "2Y Treasury Yield",          "Interest Rate",  "Daily",     False),
    ("T10Y2Y",    "10Y-2Y Yield Spread",        "Interest Rate",  "Daily",     False),

    # ── 通膨指標 ────────────────────────────────────────────────
    ("CPIAUCSL",  "CPI All Urban (Index)",      "Inflation",      "Monthly",   True),
    ("CPILFESL",  "Core CPI (Index)",           "Inflation",      "Monthly",   True),
    ("PCEPI",     "PCE Price Index",            "Inflation",      "Monthly",   True),
    ("PCEPILFE",  "Core PCE Price Index",       "Inflation",      "Monthly",   True),

    # ── 就業市場 ────────────────────────────────────────────────
    ("PAYEMS",    "Nonfarm Payrolls (Level)",   "Employment",     "Monthly",   False),
    ("UNRATE",    "Unemployment Rate",          "Employment",     "Monthly",   False),
    ("ICSA",      "Initial Jobless Claims",     "Employment",     "Weekly",    False),

    # ── 經濟成長 ────────────────────────────────────────────────
    ("GDPC1",     "Real GDP",                   "Growth",         "Quarterly", True),

    # ── 消費者 ──────────────────────────────────────────────────
    ("RSAFS",     "Retail Sales",               "Consumer",       "Monthly",   True),
    ("UMCSENT",   "Michigan Consumer Sentiment","Consumer",       "Monthly",   False),

    # ── 製造業 ──────────────────────────────────────────────────
    ("INDPRO",    "Industrial Production",      "Manufacturing",  "Monthly",   True),

    # ── 住房 ────────────────────────────────────────────────────
    ("HOUST",     "Housing Starts",             "Housing",        "Monthly",   False),
]

# NFP 需要特殊處理（計算月增量而非原始水準值）
NFP_SERIES_ID = "PAYEMS"

# 需要計算 YoY% 的 Series
YOY_CALC_SERIES = ["CPIAUCSL", "CPILFESL", "PCEPI", "PCEPILFE", "GDPC1", "RSAFS", "INDPRO"]

# FRED 頁面連結模板
FRED_URL_TEMPLATE = "https://fred.stlouisfed.org/series/{series_id}"

# 每次 FRED API 請求之間的間隔（秒），避免超出速率限制（120 req/min）
FRED_REQUEST_DELAY = 0.6

# Notion API 每次寫入之間的間隔（秒），遵守 ~3 req/sec 限制
NOTION_WRITE_DELAY = 0.4
