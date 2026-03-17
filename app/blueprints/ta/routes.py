"""
Technical Analysis (TA) 路由：處理技術分析頁面請求、資料抓取與圖表生成。
"""

import os
from flask import render_template, request, flash, current_app
from bokeh.embed import components
from app.services.data_loader import fetch, yf_read_history
from app.services.stock_indicators import calculation
from . import bp
from .chart_plotting import draw


# 指數及時間週期選項：tuple 中的三項分別為 (股票代號, 股票名稱, 時區)
TICKER_OPTIONS = [
    ("^TWII", "台灣: 台灣加權指數", "Asia/Taipei"),
    ("^DJI", "美國: 道瓊工業平均指數", "America/New_York"),
    ("^GSPC", "美國: 標準普爾 500 指數", "America/New_York"),
    ("^IXIC", "美國: 那斯達克綜合指數", "America/New_York"),
    ("^SOX", "美國: 費城半導體指數", "America/New_York"),
    ("^FTSE", "英國: 富時 100 指數", "Europe/London"),
    ("^N225", "日本: 日經 225 指數", "Asia/Tokyo"),
    ("^HSI", "香港: 恆生指數", "Asia/Hong_Kong"),
    ("^GDAXI", "德國: DAX 指數", "Europe/Berlin"),
    ("^FCHI", "法國: CAC 40 指數", "Europe/Paris"),
    ("^GSPTSE", "加拿大: S&P/TSX 綜合指數", "America/Toronto"),
    ("^AXJO", "澳洲: S&P/ASX 200 指數", "Australia/Sydney"),
    ("^STOXX50E", "歐洲: 歐洲 Stoxx 50 指數", "Europe/Berlin"),
    ("^KS11", "南韓: KOSPI 綜合指數", "Asia/Seoul"),
    ("^BSESN", "印度: S&P BSE Sensex 指數", "Asia/Kolkata"),
    ("^BVSP", "巴西: 巴西 Bovespa 指數", "America/Sao_Paulo"),
    # ("000001.SS", "中國: 上海綜合指數", "Asia/Shanghai"),  # yfinance 資料來源易有缺漏
    # ("399001.SZ", "中國: 深證成份指數", "Asia/Shanghai"),  # yfinance 資料來源易有缺漏
    ("2330.TW", "台灣: 台積電", "Asia/Taipei"),
    ("TSM", "美國: 台積電 (ADR)", "America/New_York"),
    ("USDTWD=X", "美元兌台幣匯率", "Europe/London"),
    ("USDJPY=X", "美元兌日幣匯率", "Europe/London"),
    ("USDKRW=X", "美元兌韓元匯率", "Europe/London"),
    ("JPYTWD=X", "日幣兌台幣匯率", "Europe/London"),
]
INDICATOR_OPTIONS = [
    ("volume", "成交量"),
    ("kdj", "KDJ"),
    ("macd", "MACD"),
    ("rsi", "RSI"),
    ("bias", "BIAS"),
    ("willr", "威廉指標"),
    ("bbi", "多空指標"),
    ("cdp", "逆勢操作指標"),
    ("dmi", "動向指標"),
    ("bbands", "布林帶"),
    ("obv", "能量潮"),
    ("cci", "順勢指標"),
]
TIMEFRAME_OPTIONS = [
    ("D", "日線"),
    ("W", "週線"),
    ("M", "月線"),
]
TICKER_DICT = {ticker: (name, tz) for ticker, name, tz in TICKER_OPTIONS}
TIMEFRAME_DICT = dict(TIMEFRAME_OPTIONS)
INDICATOR_DICT = dict(INDICATOR_OPTIONS)


def _generate_components(ticker: str, timeframe: str, indicators: list[str]) -> tuple[str | None, str | None, str]:
    """嘗試獲取數據、計算指標並生成 Bokeh 圖表。

    Args:
        ticker (str): 股票指數代碼。
        timeframe (str): 時間週期代碼。
        indicators (list[str]): 要求顯示的指標。

    Returns:
        tuple[str | None, str | None, str]: 成功 (script, div, title);失敗則 flash 錯誤訊息並返回 (None, None, '')。
    """
    current_app.logger.info("%s, _generate_components('%s', '%s', %s), 開始生成圖表...", __name__, ticker, timeframe, indicators)

    try:

        def _log_and_return(msg: str) -> tuple[str | None, str | None, str]:
            current_app.logger.error("%s, _generate_components('%s', '%s', %s), %s", __name__, ticker, timeframe, indicators, msg)
            return None, None, ""

        ticker_name, ticker_tz = TICKER_DICT[ticker]
        timeframe_name = TIMEFRAME_DICT[timeframe]
        title = f"{ticker_name} ({timeframe_name})"

        path_csv = os.path.join(current_app.config["TA_CACHE_DIR_YF"], f"{ticker}.csv")
        path_ts = os.path.join(current_app.config["TA_CACHE_DIR_YF_TS"], f"{ticker}.ts")
        delta_min = current_app.config["TA_CACHE_DELTA_YF_MIN"]
        cached = fetch(ticker, path_csv, path_ts, delta_min=delta_min, period="max", interval="1d")
        if not cached:
            flash(f"錯誤：無法取得 '{ticker_name}' 的資料。", "danger")
            return _log_and_return("無法取得資料")

        df_ticker = yf_read_history(path_csv, ticker_tz)
        if df_ticker.empty:
            flash(f"錯誤：無法讀取或解析 '{ticker_name}' 的資料。", "danger")
            return _log_and_return("無法讀取或解析資料")

        df_calculated = calculation(df_ticker, indicators, timeframe)
        if df_calculated.empty:
            flash(f"錯誤：無法計算 '{ticker_name} ({timeframe_name})' 的技術指標。", "danger")
            return _log_and_return("無法計算技術指標")

        layout = draw(df_calculated, indicators)
        if layout is None:
            flash(f"錯誤：無法生成 '{ticker_name} ({timeframe_name})' 的圖表。", "danger")
            return _log_and_return("無法生成圖表")

        script, div = components(layout)
        return script, div, title

    except Exception as e:  # pylint: disable=broad-exception-caught
        flash(f"錯誤：處理 '{ticker_name or ticker}' 時，發生未預期的錯誤。", "danger")
        current_app.logger.error("%s, _generate_components('%s', '%s', %s), 預期外錯誤: %s", __name__, ticker, timeframe, indicators, e, exc_info=True)
        return None, None, ""


@bp.route("/")
def index() -> str:
    """主頁面路由，處理表單並顯示圖表。

    Args:
        None

    Returns:
        str: 渲染後的 HTML。
    """
    current_app.logger.info("%s, index(), 主頁面: %s", __name__, request.args)

    ticker = request.args.get("ticker", None)
    timeframe = request.args.get("timeframe", None)
    indicators = request.args.get("indicators", None)
    indicators = indicators.split(",") if indicators else []
    indicators = [x.strip() for x in indicators if x.strip()]

    script = None
    div = None
    title = ""

    if ticker and timeframe:
        if ticker not in TICKER_DICT:
            flash(f"錯誤：無效的股票指數 '{ticker}'。", "danger")
            current_app.logger.error("%s, index(), 無效的股票指數: %s", __name__, ticker)
        elif timeframe not in TIMEFRAME_DICT:
            flash(f"錯誤：無效的時間週期 '{timeframe}'。", "danger")
            current_app.logger.error("%s, index(), 無效的時間週期: %s", __name__, timeframe)
        elif not all(x in INDICATOR_DICT for x in indicators):
            undefined_indicators = [x for x in indicators if x not in INDICATOR_DICT]
            flash(f"錯誤：無效的技術指標 {undefined_indicators}。", "danger")
            current_app.logger.error("%s, index(), 無效的技術指標: %s", __name__, undefined_indicators)
        else:
            script, div, title = _generate_components(ticker, timeframe, indicators)

    return render_template(
        "ta/index.html",
        ticker_options=TICKER_OPTIONS,
        timeframe_options=TIMEFRAME_OPTIONS,
        indicator_options=INDICATOR_OPTIONS,
        script=script,
        div=div,
        title=title,
        current_ticker=ticker,  # 用於更新下拉式選單
        current_timeframe=timeframe,  # 用於更新下拉式選單
        selected_indicators=indicators,  # 用於更新 checkbox
    )


if __name__ == "__main__":
    pass
