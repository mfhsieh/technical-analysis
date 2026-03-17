"""
技術指標計算服務：負責處理股票資料的頻率轉換 (Resample) 與各類技術指標 (MA, KDJ, MACD, RSI...) 的計算邏輯。
"""

# pylint: disable=too-many-lines
from typing import Literal
from flask import current_app
import numpy as np
import pandas as pd
import pandas_ta as ta


OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]  # 使用 pandas-ta 的慣例，欄位名為小寫


##
# 資料轉換相關函式
##


def stock_groupby(
    stock: pd.DataFrame,
    rule: str,
    label: Literal["right", "left"] = "right",
) -> pd.DataFrame:
    """將 DataFrame 依指定頻率分組，並計算 OHLCV。

    Args:
        stock (pd.DataFrame): 包含時間索引的原始 DataFrame，需包含 'open', 'high', 'low', 'close', 'volume' 欄位。
        rule (str): 分組頻率字串 (例如 'D' 代表日，'W' 代表週，'W-FRI' 代表週五，'MS' 代表月初，'ME' 代表月底)。
        label (Literal['right', 'left'], optional): 分組後的時間標籤位置 ('right' 或 'left')。預設為 'right'。

    Returns:
        pd.DataFrame: 依指定頻率分組後的 OHLCV DataFrame，索引為日期。失敗則返回空的 Dataframe
    """
    current_app.logger.info("%s, stock_groupby(stock, '%s', '%s'), 開始依指定頻率分組", __name__, rule, label)

    if not isinstance(stock.index, pd.DatetimeIndex):
        current_app.logger.error("%s, stock_groupby(stock, '%s', '%s'), 索引不是 DatetimeIndex", __name__, rule, label)
        raise TypeError("索引必須為 DatetimeIndex")

    if not all(col in stock.columns for col in OHLCV_COLUMNS):
        missing = [col for col in OHLCV_COLUMNS if col not in stock.columns]
        current_app.logger.error("%s, stock_groupby(stock, '%s', '%s'), 缺少必要欄位: %s", __name__, rule, label, missing)
        raise TypeError("缺少必要欄位")

    df_agg = stock.resample(rule=rule, label=label).agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    )

    original_len = len(df_agg)
    df_agg = df_agg.dropna(subset=OHLCV_COLUMNS)  # 移除 OHLC (不包含 V) 欄位中任何包含空值的列
    if len(df_agg) < original_len:
        current_app.logger.warning("%s, stock_groupby(stock, '%s', '%s'), 分組後空值列筆數: %i", __name__, rule, label, original_len - len(df_agg))

    if df_agg.empty:
        current_app.logger.warning("%s, stock_groupby(stock, '%s', '%s'), 分組後無資料", __name__, rule, label)
        return pd.DataFrame()

    return df_agg


##
# 技術指標相關函式
##


def sma(
    stock: pd.Series,
    length: int,
) -> pd.Series:
    """pandas-ta's SMA, Simple Moving Average, 簡單移動平均

    SMA = (過去 length 的總和) / length

    Args:
        stock (pd.Series): 股票值序列。
        length (int): 計算 SMA 的期數。

    Returns:
        pd.Series: SMA 值序列。
    """
    df_sma = ta.sma(
        stock,
        length=length,
    )

    if df_sma is None or df_sma.empty:
        current_app.logger.warning("%s, sma(...), 無法計算", __name__)
        return pd.Series(dtype=float)

    return df_sma


def sma_by_define(
    stock: pd.Series,
    length: int,
) -> pd.Series:
    """SMA, Simple Moving Average, 簡單移動平均

    SMA = (過去 length 的總和) / length

    註：
      很慢，慎用。

    Args:
        stock (pd.Series): 股票值序列。
        length (int): 計算 SMA 的期數。

    Returns:
        pd.Series: SMA 值序列。
    """
    df_sma = pd.Series(np.nan, index=stock.index, dtype=float)
    for i in range(len(stock)):
        window = stock.iloc[max(0, i - length + 1) : i + 1]
        df_sma.iloc[i] = window.mean()

    return df_sma


def ema(
    stock: pd.Series,
    length: int,
) -> pd.Series:
    """pandas-ta's EMA, Exponential Moving Average, 指數移動平均

    依等效期數換算 α = 2 / (length + 1)
    今日 EMA = 昨日 EMA * (1 - α) + 今日的值 * α

    Args:
        stock (pd.Series): 股票值序列。
        length (int): 計算 EMA 的期數。

    Returns:
        pd.Series: EMA 值序列。
    """
    df_ema = ta.ema(
        stock,
        length=length,
    )

    if df_ema is None or df_ema.empty:
        current_app.logger.warning("%s, ema(...), 無法計算", __name__)
        return pd.Series(dtype=float)

    return df_ema


def ema_by_define(
    stock: pd.Series,
    length: int,
) -> pd.Series:
    """EMA, Exponential Moving Average, 指數移動平均

    依等效期數換算 α = 2 / (length + 1)
    今日 EMA = 昨日 EMA * (1 - α) + 今日的值 * α

    註：
      1. 相當於期數 (length + 1) / 2 的 Wilder's Smoothing。(但兩者對於數列起始的處理方式可能不同)
      2. 很慢，慎用。

    Args:
        stock (pd.Series): 股票值序列。
        length (int): 計算 EMA 的等效期數。

    Returns:
        pd.Series: EMA 值序列。
    """
    df_ema = pd.Series(np.nan, index=stock.index, dtype=float)
    df_ema.iloc[0] = stock.iloc[0]
    alpha = 2 / (length + 1)
    for i in range(1, len(stock)):
        df_ema.iloc[i] = df_ema.iloc[i - 1] * (1 - alpha) + stock.iloc[i] * alpha

    return df_ema


def rma(
    stock: pd.Series,
    length: int,
) -> pd.Series:
    """pandas-ta's Wilder's Smoothing, Wilder 平滑法

    平滑值 = 昨日平滑值 * (1 − 1 / N) + 今日的值 * 1 / N

    註：
      相當於期數 (2 * length - 1) 的 EMA。(但兩者對於數列起始的處理方式可能不同)

    Args:
        stock (pd.Series): 值序列。
        length (int): 平滑期數。

    Returns:
        pd.Series: 平滑值序列。
    """
    df_rma = ta.rma(
        stock,
        length=length,
    )

    if df_rma is None or df_rma.empty:
        current_app.logger.warning("%s, rma(...), 無法計算", __name__)
        return pd.Series(dtype=float)

    return df_rma


def rma_by_define(
    stock: pd.Series,
    length: int,
) -> pd.Series:
    """Wilder's Smoothing, Wilder 平滑法

    平滑值 = 昨日平滑值 * (1 − 1 / N) + 今日的值 * 1 / N

    註：
      1. 相當於期數 (2 * length - 1) 的 EMA。(但兩者對於數列起始的處理方式不同)
      2. 很慢，慎用。

    Args:
        stock (pd.Series): 值序列。
        length (int): 平滑期數。

    Returns:
        pd.Series: 平滑值序列。
    """
    df_wilder = pd.Series(np.nan, index=stock.index, dtype=float)
    df_wilder.iloc[:length] = stock.iloc[0:length].mean()  # Wilder's Smoothing 使用的起始值
    alpha = 1 / length
    for i in range(length, len(stock)):
        df_wilder.iloc[i] = df_wilder.iloc[i - 1] * (1 - alpha) + stock.iloc[i] * alpha

    return df_wilder


def rsv_by_define(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    length: int = 9,
) -> pd.Series:
    """RSV, Raw Stochastic Value, 原始隨機值 (快速 %K)

    RSV = (今日收盤值 − 最近 N 日的最低值) / (最近 N 日的最高值 − 最近 N 日的最低值) * 100

    註：
      1. 以預設參數計算，相當於 Yahoo! 股市的 KD 指標所用之 RSV (快速 %K)。
      2. 很慢，慎用。

    Args:
        high (pd.Series): 每日最高值序列。
        low (pd.Series): 每日最低值序列。
        close (pd.Series): 每日收盤值序列。
        length (int, optional): 計算 RSV 的期數。預設為 9。

    Returns:
        pd.Series: RSV 值序列。
    """
    highest_high = pd.Series(np.nan, index=high.index, dtype=float)
    lowest_low = pd.Series(np.nan, index=low.index, dtype=float)
    for i in range(len(high)):
        start_idx = max(0, i - length + 1)  # 序列的開始部分，起始點最小為 0
        highest_high.iloc[i] = high.iloc[start_idx : i + 1].max()
        lowest_low.iloc[i] = low.iloc[start_idx : i + 1].min()

    denominator = highest_high - lowest_low
    denominator.replace(0, np.finfo(float).eps, inplace=True)  # 避免除以零

    df_rsv = (close - lowest_low) / denominator * 100
    return df_rsv


def kd(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k: int = 9,
    d: int = 5,
    smooth_k: int = 5,
    mamode: str = "ema",
) -> tuple[pd.Series, pd.Series]:
    """pandas-ta's KD, Stochastic Oscillator, 隨機指標

    在使用指數移動平均 (mamode = 'ema') 的狀況下，相當於：
        今日 K 值 (慢速 %K) (快線) = 昨日 K 值 * (1 - α) + 今日 RSV 值 * α
        今日 D 值 (慢速 %D) (慢線) = 昨日 D 值 * (1 - α) + 今日 K 值 * α
    其中：
        α = 2 / (smooth_window + 1)

    註：
      以預設參數計算，相當於 Yahoo! 股市的 KD 指標。

    Args:
        high (pd.Series): 每日最高值序列。
        low (pd.Series): 每日最低值序列。
        close (pd.Series): 每日收盤值序列。
        k (int, optional): 計算快速 %K (RSV) 的期數。預設為 9。
        d (int, optional): 計算慢速 %D 的期數。預設為 5。
        smooth_k (int, optional): 計算慢速 %K 的期數。預設為 5。
        mamode (str, optional): 移動平均類型。預設為 'ema'。

    Returns:
        tuple[pd.Series, pd.Series]: 包含慢速 %K 和慢速 %D。
    """
    df_stoch = ta.stoch(
        high=high,
        low=low,
        close=close,
        k=k,  # 相當於 talib.STOCH 的 fastk_period
        d=d,  # 相當於 talib.STOCH 的 slowd_period
        smooth_k=smooth_k,  # 相當於 talib.STOCH 的 slowk_period
        mamode=mamode,  # 相當於 talib.STOCH 的 slowk_matype 及 slowd_matype
    )

    if df_stoch is None or df_stoch.empty:
        current_app.logger.warning("%s, kd(...), 無法計算", __name__)
        return pd.Series(dtype=float), pd.Series(dtype=float)

    cols = df_stoch.columns.tolist()
    slowk = next((item for item in cols if item.startswith("STOCHk_")), None)
    slowd = next((item for item in cols if item.startswith("STOCHd_")), None)

    if slowk is None or slowd is None:
        current_app.logger.warning("%s, kd(...), 無法計算", __name__)
        return pd.Series(dtype=float), pd.Series(dtype=float)

    return df_stoch[slowk], df_stoch[slowd]


def kd_by_define(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k: int = 9,
    d: int = 5,
    smooth_k: int = 5,
) -> tuple[pd.Series, pd.Series]:
    """KD, Stochastic Oscillator, 隨機指標

    在使用指數移動平均 (mamode = 'ema') 的狀況下，相當於：
        今日 K 值 (慢速 %K) (快線) = 昨日 K 值 * (1 - α) + 今日 RSV 值 * α
        今日 D 值 (慢速 %D) (慢線) = 昨日 D 值 * (1 - α) + 今日 K 值 * α
    其中：
        α = 2 / (smooth_window + 1)

    註：
      1. 以預設參數計算，相當於 Yahoo! 股市的 KD 指標。
      2. 很慢，慎用。

    Args:
        high (pd.Series): 每日最高值序列。
        low (pd.Series): 每日最低值序列。
        close (pd.Series): 每日收盤值序列。
        k (int, optional): 計算快速 %K (RSV) 的期數。預設為 9。
        d (int, optional): 計算慢速 %D 的期數。預設為 5。
        smooth_k (int, optional): 計算慢速 %K 的期數。預設為 5。
        mamode (str, optional): 移動平均類型。預設為 'ema'。

    Returns:
        tuple[pd.Series, pd.Series]: 包含慢速 %K 和慢速 %D。
    """
    fastk = rsv_by_define(high, low, close, k)
    slowk = ema(fastk, smooth_k)

    if slowk is None or slowk.empty:
        current_app.logger.warning("%s, kd_by_define(...), 無法計算", __name__)
        return pd.Series(dtype=float), pd.Series(dtype=float)

    return slowk, ema(slowk, d)


def kdj(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k: int = 9,
    d: int = 5,
    smooth_k: int = 5,
    mamode: str = "ema",
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """pandas-ta's KDJ, Stochastic Oscillator, 隨機指標

    %J = 3 * %D - 2 * %K

    註：
      1. 以預設參數計算，相當於 Yahoo! 股市的 KDJ 指標。
      2. K, D 分別為慢速 %K 及慢速 %D。
      3. 很多網站都寫錯 %J 的公式。

    Args:
        high (pd.Series): 每日最高值序列。
        low (pd.Series): 每日最低值序列。
        close (pd.Series): 每日收盤值序列。
        k (int, optional): 計算快速 %K (RSV) 的期數。預設為 9。
        d (int, optional): 計算慢速 %D 的期數。預設為 5。
        smooth_k (int, optional): 計算慢速 %K 的期數。預設為 5。
        mamode (str, optional): 移動平均類型。預設為 'ema'。

    Returns:
        tuple[pd.Series, pd.Series, pd.Series]: 包含慢速 %K、慢速 %D 和 %J。
    """
    slowk, slowd = kd(
        high=high,
        low=low,
        close=close,
        k=k,
        d=d,
        smooth_k=smooth_k,
        mamode=mamode,
    )

    if slowk is None or slowd is None or slowk.empty or slowd.empty:
        current_app.logger.warning("%s, kdj(...), 無法計算", __name__)
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    return slowk, slowd, 3 * slowd - 2 * slowk


def kdj_by_define(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k: int = 9,
    d: int = 5,
    smooth_k: int = 5,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """KDJ, Stochastic Oscillator, 隨機指標

    %J = 3 * %D - 2 * %K

    註：
      1. 以預設參數計算，相當於 Yahoo! 股市的 KDJ 指標。
      2. K, D 分別為慢速 %K 及慢速 %D。
      3. 很多網站都寫錯 %J 的公式。
      4. 很慢，慎用。

    Args:
        high (pd.Series): 每日最高值序列。
        low (pd.Series): 每日最低值序列。
        close (pd.Series): 每日收盤值序列。
        k (int, optional): 計算快速 %K (RSV) 的期數。預設為 9。
        d (int, optional): 計算慢速 %D 的期數。預設為 5。
        smooth_k (int, optional): 計算慢速 %K 的期數。預設為 5。

    Returns:
        tuple[pd.Series, pd.Series, pd.Series]: 包含慢速 %K、慢速 %D 和 %J。
    """
    slowk, slowd = kd_by_define(
        high=high,
        low=low,
        close=close,
        k=k,
        d=d,
        smooth_k=smooth_k,
    )

    if slowk is None or slowd is None or slowk.empty or slowd.empty:
        current_app.logger.warning("%s, kdj_by_define(...), 無法計算", __name__)
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    return slowk, slowd, 3 * slowd - 2 * slowk


def macd(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    mamode: str = "ema",
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """pandas-ta's MACD, Moving Average Convergence / Divergence, 移動平均匯聚背離指標

    Price = (H + L + 2C) / 4
    DIF = 短期 Price 的 EMA (通常為 12 日) - 長期 Price 的 EMA (通常為 26 日)
    DEM (MACD) = DIF 的 N 日 EMA (通常為 9 日)
    OSC = DIF - DEM

    註：
      以預設參數計算，相當於 Yahoo! 股市的 MACD 指標。

    Args:
        high (pd.Series): 每日最高值序列。
        low (pd.Series): 每日最低值序列。
        close (pd.Series): 每日收盤值序列。
        fast (int, optional): 短期 EMA 的期數。預設為 12。
        slow (int, optional): 長期 EMA 的期數。預設為 26。
        signal (int, optional): DEM 線所用的 EMA 期數。預設為 9。
        mamode (str, optional): 移動平均類型。預設為 'ema'。

    Returns:
        tuple[pd.Series, pd.Series, pd.Series]: 包含 DIF, DEM, OSC。
    """
    df_macd = ta.macd(
        (high + low + 2 * close) / 4,
        fast=fast,
        slow=slow,
        signal=signal,
        mamode=mamode,
    )

    if df_macd is None or df_macd.empty:
        current_app.logger.warning("%s, macd(...), 無法計算", __name__)
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    cols = df_macd.columns.tolist()
    dif = next((item for item in cols if item.startswith("MACD_")), None)
    dem = next((item for item in cols if item.startswith("MACDs_")), None)
    osc = next((item for item in cols if item.startswith("MACDh_")), None)

    if dif is None or dem is None or osc is None:
        current_app.logger.warning("%s, macd(...), 無法計算", __name__)
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    return df_macd[dif], df_macd[dem], df_macd[osc]


def macd_by_define(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD, Moving Average Convergence / Divergence, 移動平均匯聚背離指標

    Price = (H + L + 2C) / 4
    DIF = 短期 Price 的 EMA (通常為 12 日) - 長期 Price 的 EMA (通常為 26 日)
    DEM (MACD) = DIF 的 N 日 EMA (通常為 9 日)
    OSC = DIF - DEM

    註：
      以預設參數計算，相當於 Yahoo! 股市的 MACD 指標。

    Args:
        high (pd.Series): 每日最高值序列。
        low (pd.Series): 每日最低值序列。
        close (pd.Series): 每日收盤值序列。
        fast (int, optional): 短期 EMA 的期數。預設為 12。
        slow (int, optional): 長期 EMA 的期數。預設為 26。
        signal (int, optional): DEM 線所用的 EMA 期數。預設為 9。

    Returns:
        tuple[pd.Series, pd.Series, pd.Series]: 包含 DIF, DEM, OSC。
    """
    price = (high + low + close * 2) / 4
    price_fast = ema(price, fast)
    price_slow = ema(price, slow)

    if price_fast is None or price_slow is None or price_fast.empty or price_slow.empty:
        current_app.logger.warning("%s, macd_by_define(...), 無法計算", __name__)
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    dif = price_fast - price_slow
    dem = ema(dif, signal)

    if dem is None or dem.empty:
        current_app.logger.warning("%s, macd_by_define(...), 無法計算", __name__)
        return dif, dem, pd.Series(dtype=float)

    return dif, dem, dif - dem


def rsi(
    close: pd.Series,
    length: int = 14,
    wilder: bool = True,
) -> pd.Series:
    """pandas-ta's RSI, Relative Strength Index, 相對強弱指標

    RSI = 平均上漲幅度 / (平均上漲幅度 + 平均下跌幅度) * 100

    Args:
        close (pd.Series): 每日收盤值序列。
        length (int, optional): 計算 RSI 的期數。
        rma (bool, optional): 是否使用 RMA (Wilder's Smoothing)

    Returns:
        pd.Series: RSI 值序列。
    """
    df_rsi = ta.rsi(
        close=close,
        length=length,
        talib=wilder,
    )

    if df_rsi is None or df_rsi.empty:
        current_app.logger.warning("%s, rsi(...), 無法計算", __name__)
        return pd.Series(dtype=float)

    return df_rsi  # type: ignore


def rsi_by_define(
    close: pd.Series,
    length: int = 14,
) -> pd.Series:
    """RSI, Relative Strength Index, 相對強弱指標

    RSI = 平均上漲幅度 / (平均上漲幅度 + 平均下跌幅度) * 100

    Args:
        close (pd.Series): 每日收盤值序列。
        length (int, optional): 計算 RSI 的期數。

    Returns:
        pd.Series: RSI 值序列。
    """
    delta = close.diff()  # 計算價格變化，返回的 Series 長度相同，第一個值為 NaN
    gains = delta.where(delta > 0, 0)  # 上漲  # type: ignore
    losses = -delta.where(delta < 0, 0)  # 下跌，加負號改為正值  # type: ignore

    smooth_gain = rma(gains, length)  # Wilder's Smoothing
    smooth_loss = rma(losses, length)  # Wilder's Smoothing

    if smooth_gain is None or smooth_loss is None or smooth_gain.empty or smooth_loss.empty:
        current_app.logger.warning("%s, rsi_by_define(...), 無法計算", __name__)
        return pd.Series(dtype=float)

    denominator = smooth_gain + smooth_loss
    denominator.replace(0, np.finfo(float).eps, inplace=True)  # 避免除以零
    df_rsi = smooth_gain / denominator * 100  # 計算 RSI

    return df_rsi


def bias(
    close: pd.Series,
    length: int,
    mamode: str = "sma",
) -> pd.Series:
    """pandas-ta's BIAS, Bias Ratio, 乖離率

    BIAS = (當前價格 − N 日移動平均線) / N 日移動平均線 * 100

    註：
      以預設參數計算，相當於 Yahoo! 股市的 BIAS 指標。

    Args:
        close (pd.Series): 每日收盤值序列。
        length (int): 計算移動平均的期數。
        mamode (str, optional): 移動平均類型。預設為 'sma'。

    Returns:
        pd.Series: BIAS 值序列。
    """
    df_bias = ta.bias(
        close=close,
        length=length,
        mamode=mamode,
    )

    if df_bias is None or df_bias.empty:
        current_app.logger.warning("%s, bias(...), 無法計算", __name__)
        return pd.Series(dtype=float)

    return df_bias * 100


def bias_by_define(
    close: pd.Series,
    length: int,
) -> pd.Series:
    """BIAS, Bias Ratio, 乖離率

    BIAS = (當前價格 − N 日移動平均線) / N 日移動平均線 * 100

    註：
      以預設參數計算，相當於 Yahoo! 股市的 BIAS 指標。

    Args:
        close (pd.Series): 每日收盤值序列。
        length (int): 計算移動平均的期數。

    Returns:
        pd.Series: BIAS 值序列。
    """
    df_sma = sma(
        stock=close,
        length=length,
    )

    if df_sma is None or df_sma.empty:
        current_app.logger.warning("%s, bias_by_define(...), 無法計算", __name__)
        return pd.Series(dtype=float)

    return (close - df_sma) / df_sma * 100


def willr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    length: int = 9,
) -> pd.Series:
    """pandas-ta's W%R, Williams %R, 威廉指標

    W%R = (N 日中最高價 − 收盤價) / (N 日中最高價 - N 日中最低價) * (-100)

    註：
      以預設參數計算，相當於 Yahoo! 股市的 Williams %R 指標。

    Args:
        high (pd.Series): 每日最高值序列。
        low (pd.Series): 每日最低值序列。
        close (pd.Series): 每日收盤值序列。
        length (int, optional): 計算 W%R 的期數。預設為 9。

    Returns:
        pd.Series: W%R 值序列。
    """
    df_willr = ta.willr(
        high=high,
        low=low,
        close=close,
        length=length,
    )

    if df_willr is None or df_willr.empty:
        current_app.logger.warning("%s, willr(...), 無法計算", __name__)
        return pd.Series(dtype=float)

    return df_willr


def willr_by_define(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    length: int = 9,
) -> pd.Series:
    """W%R, Williams %R, 威廉指標

    W%R = (N 日中最高價 − 收盤價) / (N 日中最高價 - N 日中最低價) * (-100)

    註：
      1. 以預設參數計算，相當於 Yahoo! 股市的 Williams %R 指標。
      2. 很慢，慎用。

    Args:
        high (pd.Series): 每日最高值序列。
        low (pd.Series): 每日最低值序列。
        close (pd.Series): 每日收盤值序列。
        length (int, optional): 計算 W%R 的期數。預設為 9。

    Returns:
        pd.Series: W%R 值序列。
    """
    df_willr = pd.Series(np.nan, index=close.index, dtype=float)
    for i in range(length - 1, len(close)):
        idx_low = i - length + 1
        idx_high = i + 1

        highest = high.iloc[idx_low:idx_high].max()
        lowest = low.iloc[idx_low:idx_high].min()

        if highest == lowest:
            df_willr.iloc[i] = 0
        else:
            df_willr.iloc[i] = (highest - close.iloc[i]) / (highest - lowest) * (-100)

    return df_willr


def bbi_by_define(
    close: pd.Series,
    fast_length: int = 3,
    slow_lengths: list[int] | None = None,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """BBI, Bull and Bear Index, 多空指標

    M3 = 短期移動平均
    BS = 數個移動平均的平均

    註：
      以預設參數計算，相當於 Yahoo! 股市的 BBI 指標。

    Args:
        close (pd.Series): 每日收盤值序列。
        fast_length (int, optional): 短期移動平均的期數。預設為 3。
        slow_lengths (list[int] | None, optional): 數個移動平均的期數列表。預設為 [3, 6, 9, 12]。

    Returns:
        tuple[pd.Series, pd.Series, pd.Series]: 包含短期移動平均 (M3), 數個移動平均的平均 (BS), 和差值 (M3-BS)。
    """
    if slow_lengths is None:
        slow_lengths = [3, 6, 9, 12]

    m3 = sma(
        stock=close,
        length=fast_length,
    )

    bs = pd.Series(0, index=close.index, dtype=float)
    count = 0
    for length in slow_lengths:
        df_sma = sma(
            stock=close,
            length=length,
        )
        if df_sma is None or df_sma.empty:
            break
        bs = bs + df_sma
        count = count + 1

    if m3 is None or m3.empty or count != len(slow_lengths):
        current_app.logger.warning("%s, bbi_by_define(...), 無法計算", __name__)
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    bs = bs / count

    return m3, bs, m3 - bs


def cdp_by_define(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """CDP, Counter Daily Potential, 逆勢操作指標

    AH (最高值之上限) = CDP + (High - Low)
    NH (近高值) = 2 * CDP - Low
    CDP (中心價格) = (High + Low + Close * 2) / 4
    NL (近低值) = 2 * CDP - High
    AL (最低值之下限) = CDP - (High - Low)

    註：
      以預設參數計算，相當於 Yahoo! 股市的 CDP 指標。

    Args:
        high (pd.Series): 每日最高值序列。
        low (pd.Series): 每日最低值序列。
        close (pd.Series): 每日收盤值序列。

    Returns:
        tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]: 包含 AH, NH, CDP, NL, AL。
    """
    cdp = (high + low + close * 2) / 4
    cdp_2 = cdp * 2
    delta = high - low

    ah = cdp + delta
    nh = cdp_2 - low
    nl = cdp_2 - high
    al = cdp - delta

    return ah, nh, cdp, nl, al


# def dmi(
#     high: pd.Series,
#     low: pd.Series,
#     close: pd.Series,
#     length: int = 14,
#     mamode: str = "rma",
# ) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
#     """pandas-ta's DMI, Directional Movement Index, 動向指標
#
#     包含 +DI (正向指標), -DI (負向指標), ADX (平均趨向指數), ADXR (平均趨向指數評估)
#     計算公式較複雜，詳 dmi_by_define 的內容。
#
#     註：
#       不清楚 Yahoo! 股市的 DMI 是如何計算，pandas-ta 計算值與 Yahoo! 股市有差異。
#
#     Args:
#         high (pd.Series): 每日最高值序列。
#         low (pd.Series): 每日最低值序列。
#         close (pd.Series): 每日收盤值序列。
#         length (int, optional): 計算 DMI 的期數。預設為 14。
#         mamode (str, optional): 移動平均類型。預設為 'rma' (Wilder's Smoothing)。
#
#     Returns:
#         tuple[pd.Series, pd.Series, pd.Series, pd.Series]: 包含 +DI, -DI, ADX, ADXR。
#     """
#     df_dmi = ta.dmi(
#         high=high,
#         low=low,
#         close=close,
#         length=length,
#         mamode=mamode,
#     )
#
#     pdi = df_dmi[f"DMP_{length}"]
#     ndi = df_dmi[f"DMN_{length}"]
#     adx = df_dmi[f"ADX_{length}"]
#
#     adxr = (adx + adx.shift(length - 1)) / 2
#
#     return pdi, ndi, adx, adxr


def dmi_by_define(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    length: int = 14,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """DMI, Directional Movement Index, 動向指標

    包含 +DI (正向指標), -DI (負向指標), ADX (平均趨向指數), ADXR (平均趨向指數評估)
    計算公式較複雜，詳程式內容。

    註：
      不清楚 Yahoo! 股市的 DMI 是如何計算，pandas-ta 計算值與 Yahoo! 股市有差異。

    Args:
        high (pd.Series): 每日最高值序列。
        low (pd.Series): 每日最低值序列。
        close (pd.Series): 每日收盤值序列。
        length (int, optional): 計算 DMI 的期數。預設為 14。

    Returns:
        tuple[pd.Series, pd.Series, pd.Series, pd.Series]: 包含 +DI, -DI, ADX, ADXR。
    """
    # TR, True Range, 真實波動：為下列三者的絕對值之最大值
    #   1. 今日高點減去今日低點
    #   2. 今日高點減去昨日收盤
    #   3. 今日低點減去昨日收盤
    close_yesterday = close.shift(1)  # 昨日收盤價
    # close_yesterday[0] = close[0]
    tr1 = (high - low).abs()
    tr2 = (high - close_yesterday).abs()
    tr3 = (low - close_yesterday).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)  # 留下最大值

    # DM, Directional Movement, 股價趨勢
    #   1. +DM: 今日高點減去昨日高點，若為負值則為 0
    #   2. -DM: 昨日低點減去今日低點，若為負值則為 0
    #   3. +DM 及 —DM 較小者為 0
    high_yesterday = high.shift(1)  # 昨日高點
    # high_yesterday[0] = high[0]
    low_yesterday = low.shift(1)  # 昨日低點
    # low_yesterday[0] = low[0]

    pdm = high - high_yesterday
    ndm = low_yesterday - low

    pdm.where(pdm > 0, 0, inplace=True)  # 負值為 0
    ndm.where(ndm > 0, 0, inplace=True)  # 負值為 0

    pdm.where(pdm > ndm, 0, inplace=True)  # 較小者為 0。依定義，若相等則同為 0
    ndm.where(ndm > pdm, 0, inplace=True)  # 較小者為 0。依定義，若相等則同為 0

    # TR, +DM, -DM 三者取移動平均 (Wilder's Smoothing)
    atr = rma(tr, length)
    apdm = rma(pdm, length)
    andm = rma(ndm, length)
    if atr.empty or apdm.empty or andm.empty:
        current_app.logger.warning("%s, dmi_by_define(...), 無法計算", __name__)
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    # DI, Directional Indicator, 方向指標：DM 與 TR 取移動平均後之比值
    atr.replace(0, np.finfo(float).eps, inplace=True)  # 避免除以零
    pdi = apdm / atr * 100
    ndi = andm / atr * 100

    # DX, Directional Movement Index, 趨向指數
    denominator = pdi + ndi
    denominator.replace(0, np.finfo(float).eps, inplace=True)  # 避免除以零
    dx = (pdi - ndi).abs() / denominator * 100

    # ADX, Average Directional Movement Index, 平均趨向指數
    adx = rma(dx, length)
    if adx.empty:
        current_app.logger.warning("%s, dmi_by_define(...), 無法計算", __name__)
        return pdi, ndi, pd.Series(dtype=float), pd.Series(dtype=float)

    # ADXR, Average Directional Movement Index Rating, 平均趨向指數評估
    adx_roll = adx.shift(length - 1)  # 經查 ta-lib 的 source code，此處 period 要減 1
    # adx_roll.iloc[0 : period - 1] = adx.iloc[0 : period - 1]
    adxr = (adx + adx_roll) / 2

    return pdi, ndi, adx, adxr


def bbands(
    close: pd.Series,
    length: int = 20,
    std: float = 2,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """pandas-ta's Bollinger Bands (BBands), 布林帶

    Consists of:
        BBL_length_std: 下軌 (Bollinger Lower Band)
        BBM_length_std: 中軌 (Bollinger Middle Band)
        BBU_length_std: 上軌 (Bollinger Upper Band)
        BBB_length_std: 布林帶寬度 (Bollinger Bandwidth)，計算公式為 (上軌−下軌)/中軌
        BBP_length_std: 布林帶百分比 (%b)，計算公式為 (收盤價−下軌)/(上軌−下軌)

    Args:
        close (pd.Series): 每日收盤值序列。
        length (int): 計算平均線和標準差的週期長度。預設為 20。
        std (float): 標準差的乘數，決定上下軌距離中軌的寬度。預設為 2。

    Returns:
        tuple[pd.Series, pd.Series, pd.Series]: 包含 Lower, Middle, Upper bands.
    """
    df_bbands = ta.bbands(
        close=close,
        length=length,
        std=std,
    )

    if df_bbands is None or df_bbands.empty:
        current_app.logger.warning("%s, bbands(...), 無法計算", __name__)
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    cols = df_bbands.columns.tolist()
    bbl = next((item for item in cols if item.startswith("BBL_")), None)
    bbm = next((item for item in cols if item.startswith("BBM_")), None)
    bbu = next((item for item in cols if item.startswith("BBU_")), None)

    if bbl is None or bbm is None or bbu is None:
        current_app.logger.warning("%s, bbands(...), 無法計算", __name__)
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    return df_bbands[bbl], df_bbands[bbm], df_bbands[bbu]


def obv(
    close: pd.Series,
    volume: pd.Series,
) -> pd.Series:
    """pandas-ta's On-Balance Volume (OBV), 能量潮指標

    Args:
        close (pd.Series): 每日收盤值序列。
        volume (pd.Series): 每日成交量序列。

    Returns:
        pd.Series: OBV 值序列。
    """
    df_obv = ta.obv(
        close=close,
        volume=volume,
    )

    if df_obv is None or df_obv.empty:
        current_app.logger.warning("%s, obv(...), 無法計算", __name__)
        return pd.Series(dtype=float)

    return df_obv


def cci(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    length: int = 20,
    scalar: float = 0.015,
) -> pd.Series:
    """pandas-ta's Commodity Channel Index (CCI), 順勢指標

    CCI = (Typical Price - SMA of Typical Price) / (scalar * Mean Deviation)
    Typical Price (TP) = (High + Low + Close) / 3
    Mean Deviation is the Mean Absolute Deviation of the Typical Price from its SMA.

    Args:
        high (pd.Series): 每日最高值序列。
        low (pd.Series): 每日最低值序列。
        close (pd.Series): 每日收盤值序列。
        length (int, optional): 計算 CCI 的期數。預設為 20。
        scalar (float, optional): 常數。預設為 0.015。

    Returns:
        pd.Series: CCI 值序列。
    """
    df_cci = ta.cci(high=high, low=low, close=close, length=length, c=scalar)

    if df_cci is None or df_cci.empty:
        current_app.logger.warning("%s, cci(...), 無法計算", __name__)
        return pd.Series(dtype=float)

    return df_cci


def calculation(  # pylint: disable=too-many-return-statements,too-many-branches
    df_stock: pd.DataFrame, indicators: list[str], groupby: str = ""
) -> pd.DataFrame:
    """計算股票資料的常用技術指標。

    Args:
        df_stock (pd.DataFrame): 包含 'open', 'high', 'low', 'close', 'volume' 欄位的股票資料 DataFrame。索引必須是日期時間類型 DatetimeIndex。
        indicators (list[str]): 要求計算的指標。
        groupby (str, optional): 用於分組計算的頻率字串 ('W' 代表週, 'ME' 或 'M' 代表月底)。如果提供，則會先依指定頻率對資料進行分組。預設為 '' (日線)。

    Returns:
        pd.DataFrame:
            1. 包含原始資料以及計算出的技術指標的新 DataFrame。
            2. 新增 'index' (數字索引) 和 'Date' (YYYY-MM-DD 字串) 欄位。
            3. 如果輸入或計算出錯，返回空 DataFrame。
    """
    current_app.logger.info("%s, calculation(df, '%s'), 開始計算技術指標...", __name__, groupby)

    if not isinstance(df_stock.index, pd.DatetimeIndex):
        current_app.logger.error("%s, calculation(df, '%s'), 索引不是 DatetimeIndex", __name__, groupby)
        return pd.DataFrame()

    if not all(col in df_stock.columns for col in OHLCV_COLUMNS):
        missing = [col for col in OHLCV_COLUMNS if col not in df_stock.columns]
        current_app.logger.error("%s, calculation(df, '%s'), 缺少必要欄位: %s", __name__, groupby, missing)
        return pd.DataFrame()

    groupby_upper = groupby.upper()
    groupby_map = {"W": "W-FRI", "M": "ME"}  # W-FRI: 週五為一周結束, ME: MonthEnd
    if groupby_upper in groupby_map:
        try:
            df = stock_groupby(df_stock, groupby_map[groupby_upper])
            if df.empty:
                current_app.logger.error("%s, calculation(df, '%s'), 分組後無資料", __name__, groupby)
                return pd.DataFrame()

        except Exception as e:  # pylint: disable=broad-exception-caught
            current_app.logger.error("%s, calculation(df, '%s'), 預期外錯誤: %s", __name__, groupby, e, exc_info=True)
            return pd.DataFrame()

    else:
        df = df_stock[OHLCV_COLUMNS].copy()  # 必要欄位創建副本進行計算

    df = df.dropna(subset=["open", "high", "low", "close"])  # 移除 volume 外的空值列
    if df.empty:
        current_app.logger.error("%s, calculation(df, '%s'), 移除空值後無資料", __name__, groupby)
        return pd.DataFrame()

    # 最小資料量檢查：視需求取消註解
    # min_period_needed = 5
    # if len(df) < min_period_needed:
    #     current_app.logger.error("%s, calculation(df, '%s'), 有效資料不足: %i", __name__, groupby, len(df))
    #     return pd.DataFrame()

    try:
        # 計算漲跌幅
        df["Change"] = df["close"] - df["close"].shift()

        # 計算移動平均線 (使用 pandas-ta 實作)
        current_app.logger.info("%s, calculation(df, '%s'), 計算移動平均線...", __name__, groupby)
        df["MA5"] = sma(df["close"], length=5)
        df["MA20"] = sma(df["close"], length=20)
        df["MA60"] = sma(df["close"], length=60)
        df["MA120"] = sma(df["close"], length=120)
        df["MA240"] = sma(df["close"], length=240)
        # 下列為自定義實作版本，保留作為邏輯參考
        # df["MA5"] = sma_by_define(df["close"], length=5)
        # df["MA20"] = sma_by_define(df["close"], length=20)
        # df["MA60"] = sma_by_define(df["close"], length=60)
        # df["MA120"] = sma_by_define(df["close"], length=120)
        # df["MA240"] = sma_by_define(df["close"], length=240)

        # 計算 KDJ 指標
        if "kdj" in indicators:
            current_app.logger.info("%s, calculation(df, '%s'), 計算 KDJ 指標...", __name__, groupby)
            df["K"], df["D"], df["J"] = kdj(df["high"], df["low"], df["close"])
            # df["K"], df["D"], df["J"] = kdj_by_define(df["high"], df["low"], df["close"])

        # 計算 MACD 指標
        if "macd" in indicators:
            current_app.logger.info("%s, calculation(df, '%s'), 計算 MACD 指標...", __name__, groupby)
            df["DIF"], df["MACD"], df["OSC"] = macd(df["high"], df["low"], df["close"])
            # df["DIF"], df["MACD"], df["OSC"] = macd_by_define(df["high"], df["low"], df["close"])

        # 計算 RSI 指標
        if "rsi" in indicators:
            current_app.logger.info("%s, calculation(df, '%s'), 計算 RSI 指標...", __name__, groupby)
            df["RSI5"] = rsi(df["close"], length=5)
            df["RSI10"] = rsi(df["close"], length=10)
            # df["RSI5"] = rsi_by_define(df["close"], length=5)
            # df["RSI10"] = rsi_by_define(df["close"], length=10)

        # 計算 BIAS 指標
        if "bias" in indicators:
            current_app.logger.info("%s, calculation(df, '%s'), 計算 BIAS 指標...", __name__, groupby)
            df["BIAS10"] = bias(df["close"], length=10)
            df["BIAS20"] = bias(df["close"], length=20)
            # df["BIAS10"] = bias_by_define(df["close"], length=10)
            # df["BIAS20"] = bias_by_define(df["close"], length=20)
            df["B10-B20"] = df["BIAS10"] - df["BIAS20"]

        # 計算 Williams %R 指標
        if "willr" in indicators:
            current_app.logger.info("%s, calculation(df, '%s'), 計算 Williams %%R 指標...", __name__, groupby)
            df["WILLR"] = willr(df["high"], df["low"], df["close"])
            # df["WILLR"] = willr_by_define(df["high"], df["low"], df["close"])

        # 計算 BBI 指標
        if "bbi" in indicators:
            current_app.logger.info("%s, calculation(df, '%s'), 計算 BBI 指標...", __name__, groupby)
            df["M3"], df["BS"], df["M3-BS"] = bbi_by_define(df["close"])

        # 計算 CDP 指標
        if "cdp" in indicators:
            current_app.logger.info("%s, calculation(df, '%s'), 計算 CDP 指標...", __name__, groupby)
            df["AH"], df["NH"], df["CDP"], df["NL"], df["AL"] = cdp_by_define(df["high"], df["low"], df["close"])

        # 計算 DMI 指標
        if "dmi" in indicators:
            current_app.logger.info("%s, calculation(df, '%s'), 計算 DMI 指標...", __name__, groupby)
            # df["PLUS_DI"], df["MINUS_DI"], df["ADX"], df["ADXR"] = dmi(df["high"], df["low"], df["close"])
            df["PLUS_DI"], df["MINUS_DI"], df["ADX"], df["ADXR"] = dmi_by_define(df["high"], df["low"], df["close"])

        # 計算 BBands 指標
        if "bbands" in indicators:
            current_app.logger.info("%s, calculation(df, '%s'), 計算 BBands 指標...", __name__, groupby)
            df["BBL"], df["BBM"], df["BBU"] = bbands(df["close"])

        # 計算 OBV 指標
        if "obv" in indicators:
            current_app.logger.info("%s, calculation(df, '%s'), 計算 OBV 指標...", __name__, groupby)
            df["OBV"] = obv(df["close"], df["volume"])

        # 計算 CCI 指標
        if "cci" in indicators:
            current_app.logger.info("%s, calculation(df, '%s'), 計算 CCI 指標...", __name__, groupby)
            df["CCI"] = cci(df["high"], df["low"], df["close"])

    except Exception as e:  # pylint: disable=broad-exception-caught
        current_app.logger.error("calculation(df, '%s'), 預期外錯誤: %s", groupby, e, exc_info=True)
        return pd.DataFrame()

    # 重置索引，方便後續處理
    df.reset_index(inplace=True)

    # 將 'Date' 欄位格式化為 'YYYY-MM-DD' 字串
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

    # 再次重置索引，以添加一個新的數字索引
    df.reset_index(inplace=True)

    current_app.logger.info("%s, calculation(df, '%s'), 技術指標計算完成", __name__, groupby)
    return df


if __name__ == "__main__":
    pass
