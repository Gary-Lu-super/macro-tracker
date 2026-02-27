# 🇺🇸 US Macro Economic Tracker

自動從 FRED API 抓取美國總體經濟數據，並透過 Notion API 寫入 Notion 資料庫。使用 GitHub Actions 免費雲端排程，無需伺服器，完全自動化。

---

## 📁 檔案結構

```
macro-tracker/
├── .github/
│   └── workflows/
│       ├── macro_tracker.yml   # 主排程（週一至週五自動執行）
│       └── keepalive.yml       # 防止 GitHub 停用排程
├── config.py                   # 所有指標的設定（Series ID、分類等）
├── fred_fetcher.py             # FRED API 數據抓取邏輯
├── notion_writer.py            # Notion API 寫入邏輯（含防重複）
├── macro_tracker.py            # 主程式入口
├── requirements.txt            # Python 套件依賴
├── .env.example                # 環境變數範本
├── .gitignore
└── README.md
```

---

## 🚀 快速部署步驟

### 1. 申請 API 金鑰

| 金鑰 | 申請網址 |
|------|---------|
| FRED API Key | https://research.stlouisfed.org/useraccount/apikeys |
| Notion Token | https://www.notion.so/my-integrations |
| Notion DB ID | 從資料庫 URL 取得（`/` 與 `?` 之間的 32 位字串） |

### 2. 設定環境變數（本地開發）

```bash
cp .env.example .env
# 編輯 .env，填入你的三組金鑰
```

### 3. 安裝套件並本地測試

```bash
pip install -r requirements.txt
python macro_tracker.py
```

### 4. 推送到 GitHub 並設定 Secrets

前往 GitHub Repo → **Settings → Secrets and variables → Actions** → 新增：

| Secret Name | 值 |
|---|---|
| `FRED_API_KEY` | 你的 FRED API 金鑰 |
| `NOTION_TOKEN` | 你的 Notion Integration Token |
| `NOTION_DATABASE_ID` | 你的 Notion 資料庫 ID |

### 5. 手動觸發測試

前往 GitHub → **Actions → US Macro Data Tracker → Run workflow**，確認執行成功。

---

## ⏰ 排程時間

| 排程 | 時間（UTC） | 說明 |
|------|-----------|------|
| 主排程 | 週一至週五 14:00 UTC | 美東 9:00 AM（大多數指標 8:30 AM ET 發布） |
| FOMC | 每週三 19:00 UTC | 聯準會決議通常 2:00 PM ET 公布 |

---

## 📊 追蹤指標清單

| 類別 | 指標 | FRED Series ID |
|------|------|---------------|
| Interest Rate | Fed Funds Target Upper/Lower | DFEDTARU / DFEDTARL |
| Interest Rate | 10Y / 2Y Treasury Yield | DGS10 / DGS2 |
| Interest Rate | 10Y-2Y Yield Spread | T10Y2Y |
| Inflation | CPI / Core CPI | CPIAUCSL / CPILFESL |
| Inflation | PCE / Core PCE | PCEPI / PCEPILFE |
| Employment | Nonfarm Payrolls | PAYEMS |
| Employment | Unemployment Rate | UNRATE |
| Employment | Initial Jobless Claims | ICSA |
| Growth | Real GDP | GDPC1 |
| Consumer | Retail Sales | RSAFS |
| Consumer | Michigan Sentiment | UMCSENT |
| Manufacturing | Industrial Production | INDPRO |
| Housing | Housing Starts | HOUST |

---

## 🛠️ 自訂指標

在 `config.py` 的 `INDICATORS` 清單中新增一行：

```python
("SERIES_ID", "顯示名稱", "分類", "頻率", 是否計算YoY),
```

例如新增 ISM 製造業 PMI：

```python
("NAPM", "ISM Manufacturing PMI", "Manufacturing", "Monthly", False),
```

---

## ⚠️ 注意事項

- **絕對不要** commit `.env` 檔案或在程式碼中寫死金鑰
- FRED API 速率限制：120 req/min（程式已自動處理）
- Notion API 速率限制：~3 req/sec（程式已自動處理）
- GitHub Actions 免費方案：公開 repo 無限分鐘，私有 repo 2,000 分鐘/月
