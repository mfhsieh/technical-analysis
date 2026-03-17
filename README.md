# 股票指數技術分析 (Technical Analysis)

這是基於 [bokeh](https://bokeh.org/)、[pandas-ta](https://www.pandas-ta.dev/) 及 [yfinance](https://github.com/ranaroussi/yfinance) 的股票指數技術分析應用程式，旨在提供直觀且互動性強的股票圖表與技術指標。

實際執行畫面請參考 [全球股票指數技術分析](https://mfhsieh.pythonanywhere.com/ta/)。

## 🌟 主要功能

- **資料來源**：使用 [yfinance](https://github.com/ranaroussi/yfinance) 自 [Yahoo! Finance](https://finance.yahoo.com/) 載入股票歷史資料。

- **技術指標**：整合 [pandas-ta](https://www.pandas-ta.dev/)，自動計算多種指標。
  - K 線圖 (K Chart) 及移動平均線 (MA5, MA20, MA60, MA120, MA240)
  - 成交量 (Volume)
  - 隨機指標 (KDJ, Stochastic Oscillator)
  - 移動平均匯聚背離指標 (MACD, Moving Average Convergence / Divergence)
  - 相對強弱指標 (RSI, Relative Strength Index)
  - 乖離率 (Bias, Bias Ratio)
  - 威廉指標 (Williams %R)
  - 多空指標 (BBI, Bull and Bear Index)
  - 逆勢操作指標 (CDP, Counter Daily Potential)
  - 動向指標 (DMI, Directional Movement Index)
  - 布林帶 (BBands, Bollinger Bands)
  - 能量潮 (OBV, On-Balance Volume)
  - 順勢指標 (CCI, Commodity Channel Index)
  
- **互動圖表**：使用 [bokeh](https://bokeh.org/) 繪製高品質的技術指標。

## 🛠️ 安裝步驟

1. **複製專案**：

   ```bash
   git clone https://github.com/mfhsieh/technical-analysis.git
   cd technical-analysis
   ```

2. **虛擬環境**：建議使用 python 3.12 版本。

   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate  # for Linux/macOS，其它作業系統請自行調整
   pip install --upgrade pip  # 升級 pip 到最新版本
   pip install build  # 安裝編譯工具
   ```

3. **編譯 pandas-ta**
   - 為能在 [PythonAnywhere](https://www.pythonanywhere.com/) 上安裝使用，受限其免費環境，pandas-ta 建議使用 0.3.14b0 版本，可大幅減少空間需求。
   - 下載原始碼：[pandas-ta 0.3.14b0](https://sourceforge.net/projects/pandas-ta.mirror/files/0.3.14/PandasTA-v0.3.14b%20source%20code.tar.gz/download)。
   - 編譯完成後，可將 `dist/pandas_ta-0.3.14b0-py3-none-any.whl` 檔案複製到專案目錄下，以利後續使用。

   ```bash
   tar zxvf "PandasTA-v0.3.14b source code.tar.gz"
   cd twopirllc-pandas-ta-bc3b292
   python -m build
   ```

4. **安裝套件**：

   ```bash
   pip install -r requirements.txt pandas_ta-0.3.14b0-py3-none-any.whl
   ```

## ⚙️ 環境配置

- 本專案使用 `.flaskenv` 管理環境變數，因包含敏感資料（如 `SECRET_KEY`），此檔案已列入 `.gitignore`。
- 請參考範本檔 [.flaskenv.example](./.flaskenv.example) 建立您自己的 `.flaskenv` 檔案。
- 請設定適當的 `SECRET_KEY` (可參閱 [config.py](./config.py) 檔案內的說明)。

## 🚀 啟動方式

- 於 Flask 開發環境下執行：應用程式預設在 `http://127.0.0.1:5000` 運行。

   ```bash
   python3.12 run.py
   ```

- 安裝至 [PythonAnywhere](https://www.pythonanywhere.com/) 者，可使用下列程式經 WSGI 啟動。

   ```python
   import sys

   PROJECT = "/home/USERNAME/technical-analysis"  # 請替換為實際路徑
   if PROJECT not in sys.path:
      sys.path.insert(0, PROJECT)

   try:
      from run import app as application  # PythonAnywhere expects "application"

   except ImportError as e:
      print(f"Error importing Flask application: {e}")
      raise e  # Re-raise the error
   ```

## 📁 專案結構

- [app/](./app/): 應用程式主目錄。
  - [services/](./app/services/): 核心邏輯，包括資料載入 [data_loader.py](./app/services/data_loader.py) 與技術指標計算 [stock_indicators.py](./app/services/stock_indicators.py)。
  - [blueprints/ta/](./app/blueprints/ta/): 前站動態網頁，包含路由 [routes.py](./app/blueprints/ta/routes.py) 與圖表繪製 [chart_plotting.py](./app/blueprints/ta/chart_plotting.py)。
  - [templates/](./app/blueprints/ta/templates/) & [static/](./app/blueprints/ta/static/): 前端 HTML 與靜態檔案。
- [.flaskenv](./.flaskenv.example): 環境變數設定檔。
- [config.py](./config.py): Flask 設定模組，包含開發環境與正式環境設定。
- [run.py](./run.py): Flask 啟動腳本，初始化 Flask 實例並啟動 Web 伺服器。
- [requirements.txt](./requirements.txt): 套件依賴清單。

## 📄 授權條款

本專案採用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh_TW) 授權（姓名標示－非商業性－相同方式分享 4.0 國際）。

您可以自由重製、散布、傳輸及修改本創作，但不得用於商業目的；若您修改本作品，必須採用相同授權條款散布您的貢獻。

作者：[mfhsieh at github](https://github.com/mfhsieh)

## 📦 Release Notes

- 2026-03-17：1.00 版發佈。
