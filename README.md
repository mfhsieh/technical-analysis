# 股票指數技術分析 (Technical Analysis)

這是基於 [Flask](https://flask.palletsprojects.com/) 及 [Bokeh](https://bokeh.org/) 的股票指數技術分析應用程式，旨在提供直觀且互動性強的股票圖表與技術指標分析。

## 🌟 主要功能

- **多樣化資料來源**：支援從 Google Sheets、Google Drive 以及 Yahoo Finance (`yfinance`) 載入股票歷史資料。
- **豐富的技術指標**：整合 `pandas-ta`，自動計算多種技術指標，包括：
  - 移動平均線 (SMA, EMA, WMA)
  - 布林通道 (Bollinger Bands)
  - 相對強弱指標 (RSI)
  - MACD、KD 等。
- **互動式圖表**：使用 `Bokeh` 繪製高品質的 K 線圖與指標圖，支援縮放、平移與數值查看。
- **環境設定靈活**：透過 `.flaskenv` 與 `config.py` 輕鬆管理開發與生產環境的設定。

## 🛠️ 安裝步驟

1. **複製專案**：

   ```bash
   git clone https://github.com/mfhsieh/technical-analysis.git
   cd technical-analysis
   ```

2. **建立虛擬環境**：

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   ```

3. **安裝依賴套件**：

   ```bash
   pip install -r requirements.txt
   ```

### 🔧 `pandas-ta` 手動安裝說明

由於 `pandas-ta 0.3.14b0` 可能需要手動編譯安裝（特別是在 Python 3.12+ 環境下），若 `pip install` 失敗，請參考以下步驟（詳見 [`.memo/pandas-ta/memo.md`](.memo/pandas-ta/memo.md)）：

1. **下載來源碼**：從 [SourceForge](https://sourceforge.net/projects/pandas-ta.mirror/files/0.3.14/) 下載 `Pandas TA` 檔案。
2. **安裝編譯工具**：

   ```bash
   pip install build
   ```

3. **進行編譯**：在解壓後的目錄中執行：

   ```bash
   python -m build
   ```

   這將產生一個 `dist` 目錄。

4. **安裝 Wheel 檔案**：

   ```bash
   pip install dist/pandas_ta-0.3.14b0-py3-none-any.whl
   ```

## ⚙️ 環境配置

本專案使用 `.flaskenv` 管理開發環境變數。請確保設定適當的 `SECRET_KEY` 以保證應用程式安全（尤其是在生產環境）。

主要設定項目位於 `config.py` 中，包括：

- `TA_CACHE_DIR`: 快取資料夾目錄。
- `TA_CACHE_DELTA_YF_MIN`: Yahoo Finance 資料快取時效（預設為 3600 秒）。

## 🚀 啟動方式

執行以下指令啟動 Flask 開發伺服器：

```bash
python run.py
```

預設情況下，應用程式將在 `http://127.0.0.1:5000` 運行。

## 📁 專案結構

- `app/`: 應用程式主目錄。
  - `services/`: 核心邏輯，包括資料載入 (`data_loader.py`) 與指標計算 (`stock_indicators.py`)。
  - `blueprints/ta/`: 技術分析模組，包含路由 (`routes.py`) 與圖表繪製 (`chart_plotting.py`)。
  - `templates/` & `static/`: 前端範本與靜態檔案。
- `config.py`: Flask 設定檔案。
- `run.py`: 應用程式入口啟動程式。
- `requirements.txt`: 專案依賴清單。

## 📝 備註

- 本專案針對 Python 3.12 環境（如 PythonAnywhere）進行了最佳化。
- 確保 `yfinance` 版本大於 1.0 以確保資料抓取正常。
