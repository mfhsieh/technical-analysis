# 股票指數技術分析 (Technical Analysis)

[![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hant)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Built with Bokeh](https://img.shields.io/badge/Built%20with-Bokeh-orange.svg)](https://bokeh.org/)
[![Pandas-TA](https://img.shields.io/badge/Indicator-Pandas--TA-blue.svg)](https://www.pandas-ta.dev/)
[![yfinance](https://img.shields.io/badge/Data-yfinance-green.svg)](https://github.com/ranaroussi/yfinance)

這是基於 [bokeh](https://bokeh.org/)、[pandas-ta](https://www.pandas-ta.dev/) 及 [yfinance](https://github.com/ranaroussi/yfinance) 的股票指數技術分析應用程式，旨在提供直觀且互動性強的股票圖表與技術指標。

實際執行結果請參考 [全球股票指數技術分析](https://mfhsieh.pythonanywhere.com/ta/)。因為在使用者發出請求後才開始即時抓取資料，且使用免費方案，載入時間較長，請耐心等候。

---

## 📋 目錄

- [🌟 主要功能](#-主要功能)
- [📊 技術指標](#-技術指標)
- [🛠️ 安裝步驟](#️-安裝步驟)
- [⚙️ 環境配置](#️-環境配置)
- [🚀 啟動方式](#-啟動方式)
- [📁 專案結構](#-專案結構)
- [📄 授權條款](#-授權條款)
- [📦 版本記錄](#-版本記錄)

---

## 🌟 主要功能

- **即時資料載入**：使用 [yfinance](https://github.com/ranaroussi/yfinance) 從 [Yahoo! Finance](https://finance.yahoo.com/) 載入最新全球股票指數資料。
- **互動式圖表**：使用 [bokeh](https://bokeh.org/) 繪製高品質圖表，支援滾輪縮放、平移拖拉與工具提示 (Hover Tooltips)。
- **多指標同步**：整合 [pandas-ta](https://www.pandas-ta.dev/)，所有指標在同一垂直軸線同步呈現，利於趨勢研判。

## 📊 技術指標

| 類別 | 指標名稱 (名稱/縮寫) |
| :--- | :--- |
| **主圖指標** | K 線圖 (K Chart)、移動平均線 (MA: 5, 20, 60, 120, 240) |
| **動量指標** | 隨機指標 (KDJ)、相對強弱指標 (RSI)、威廉指標 (Williams %R)、順勢指標 (CCI) |
| **趨勢指標** | 平滑異同平均線 (MACD)、動向指標 (DMI)、多空指標 (BBI) |
| **量能指標** | 成交量 (Volume)、能量潮 (OBV) |
| **其它指標** | 乖離率 (Bias)、逆勢操作指標 (CDP)、布林帶 (BBands) |

---

## 🛠️ 安裝步驟

1. **複製專案**：

   ```bash
   git clone https://github.com/mfhsieh/technical-analysis.git
   cd technical-analysis
   ```

2. **建立虛擬環境**：建議使用 **Python 3.12**。

   ```bash
   python3.12 -m venv .venv
   # python3.12 -m venv --system-site-packages .venv  # 適用如 PythonAnywhere 免費方案空間受限的情境
   source .venv/bin/activate  # Linux/macOS
   # .venv\Scripts\activate  # Windows
   pip install --upgrade pip
   pip install build
   ```

3. **編譯 pandas-ta**：
   - 為符合 [PythonAnywhere](https://www.pythonanywhere.com/) 免費方案的 512MB 空間限制，建議使用 `pandas-ta` 的 `0.3.14b0` 版本；該版本可搭配系統已預載的 `pandas` 及相關套件，以精簡所需空間。
   - 下載原始碼：[pandas-ta 0.3.14b0](https://sourceforge.net/projects/pandas-ta.mirror/files/0.3.14/PandasTA-v0.3.14b%20source%20code.tar.gz/download)。
   - 編譯完成後的 `dist/pandas_ta-0.3.14b0-py3-none-any.whl` 可留存備用。

   ```bash
   tar zxvf "PandasTA-v0.3.14b source code.tar.gz"
   cd twopirllc-pandas-ta-bc3b292
   python -m build
   ```

4. **安裝套件**：
   - [requirements.txt](./requirements.txt) 檔案所列之版本限制，是為配合 [PythonAnywhere](https://www.pythonanywhere.com/) 免費方案的 512MB 空間限制。

   ```bash
   pip install -r requirements.txt pandas_ta-0.3.14b0-py3-none-any.whl
   ```

---

## ⚙️ 環境配置

- 本專案使用 `.flaskenv` 管理環境變數。請參考範本檔 [.flaskenv.example](./.flaskenv.example)。
- 請在 `.flaskenv` 設定自用的金鑰 `SECRET_KEY`。可參閱 [config.py](./config.py)，或直接以下列指令產生：

  ```bash
  python3.12 -c 'import secrets; print(secrets.token_hex())'
  ```

---

## 🚀 啟動方式

- **開發環境**：預設運行於 `http://127.0.0.1:5000`。

    ```bash
    python3.12 run.py
    ```

- **部署於 PythonAnywhere**：可參考以下的 WSGI 設定檔。

    ```python
    import sys
    PROJECT = "/home/USERNAME/technical-analysis"  # 請修改為實際路徑
    if PROJECT not in sys.path:
        sys.path.insert(0, PROJECT)

    try:
        from run import app as application
    except ImportError as e:
        print(f"Error importing Flask application: {e}")
        raise e
    ```

---

## 📁 專案結構

- [app/](./app/): 應用程式主目錄。
  - [services/](./app/services/): 核心邏輯（資料載入、指標計算）。
  - [blueprints/ta/](./app/blueprints/ta/): 技術分析模組（路由、圖表繪製、HTML 模板與靜態資源）。
- [run.py](./run.py): Flask 入口。
- [config.py](./config.py): 系統設定 (開發/正式環境)。
- [.flaskenv.example](./.flaskenv.example): 環境變數範本。

---

## 📄 授權條款

- 本專案採用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hant) 授權（姓名標示－非商業性－相同方式分享 4.0 國際）。

- 您可以自由重製、散布、傳輸及修改本創作，但不得用於商業目的；若您修改本作品，必須採用相同授權條款散布。

- 作者：[mfhsieh at github](https://github.com/mfhsieh)

---

## 📦 版本記錄

- 2026-03-17: v1.0.0 發佈。
