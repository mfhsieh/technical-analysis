"""
資料載入服務：負責從 yFinance 獲取股票歷史資料，並處理快取與時區轉換。
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from flask import current_app
import pandas as pd
import yfinance as yf


STANDARD_COLUMNS = ["open", "high", "low", "close", "volume"]


def yf_get_history(ticker: str, period: str = "max", interval: str = "1d") -> pd.DataFrame:
    """使用 yFinance 取得股票歷史資料。

    Args:
        ticker (str): 股票代碼 (例如 '2330.TW', '^TWII')。
        period (str, optional): 歷史資料期間 (例如 '1d', '5d', '1mo', '1y', 'max')。預設為 'max'。
        interval (str, optional): 歷史資料間隔 (例如 '1m', '5m', '1h', '1d', '1wk', '1mo')。預設為 '1d'。

    Returns:
        pd.DataFrame:
            1. 只包含標準 'open', 'high', 'low', 'close', 'volume' 欄位的 DataFrame。
            2. 移除 OHLC (不包含 V) 欄位中任何包含非數值的行。
            3. 如果失敗，返回空的 DataFrame。
    """
    current_app.logger.info("%s, yf_get_history('%s', '%s', '%s'), 開始取得資料", __name__, ticker, period, interval)

    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval)

        if df.empty:
            current_app.logger.warning("%s, yf_get_history('%s', '%s', '%s'), 未取得資料", __name__, ticker, period, interval)
            return pd.DataFrame()

        df.rename(columns={col: col.lower() for col in df.columns}, inplace=True)  # 轉成 pandas-ta 所需的小寫欄位名

        missing_cols = [col for col in STANDARD_COLUMNS if col not in df.columns]  # 檢查是否包含所有標準欄位
        if missing_cols:
            current_app.logger.warning("%s, yf_get_history('%s', '%s', '%s'), 缺少欄位: %s", __name__, ticker, period, interval, missing_cols)
            if len(missing_cols) == len(STANDARD_COLUMNS):  # 不含標準欄位，返回空值
                current_app.logger.warning("%s, yf_get_history('%s', '%s', '%s'), 不包含 OHLCV 欄位", __name__, ticker, period, interval)
                return pd.DataFrame()

        # 保留標準欄位，轉換為數字，並移除 OHLC (不包含 V) 欄位中任何包含非數值的列
        valid_cols = [col for col in STANDARD_COLUMNS if col in df.columns]
        df = df[valid_cols]
        for col in valid_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["open", "high", "low", "close"])

        if df.empty:
            current_app.logger.warning("%s, yf_get_history('%s', '%s', '%s'), 移除非數值後無資料", __name__, ticker, period, interval)
            return pd.DataFrame()

        current_app.logger.info("%s, yf_get_history('%s', '%s', '%s'), 資料列數: %i", __name__, ticker, period, interval, len(df))
        return df

    except Exception as e:  # pylint: disable=broad-exception-caught
        current_app.logger.error("%s, yf_get_history('%s', '%s', '%s'), 預期外錯誤: %s", __name__, ticker, period, interval, e, exc_info=True)
        return pd.DataFrame()


def yf_write_history(df: pd.DataFrame, fname: str) -> bool:
    """將股票歷史資料的 DataFrame 寫入檔案。

    Args:
        df (pd.DataFrame): 要寫入的 DataFrame (應包含 DatetimeIndex)。
        fname (str): 檔案的完整路徑。

    Returns:
        bool: 寫入成功返回 True；否則返回 False。
    """
    current_app.logger.info("%s, yf_write_history(df, '%s'), 開始寫入檔案", __name__, fname)

    if df.empty:
        current_app.logger.warning("%s, yf_write_history(df, '%s'), 嘗試寫入空的歷史資料", __name__, fname)
        return False

    try:
        dir_name = os.path.dirname(fname)  # 確保目標檔案的目錄存在
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        df.to_csv(fname, encoding="utf-8", index=True)  # 將 DataFrame 寫入 CSV，包含索引 (Date)
        current_app.logger.info("%s, yf_write_history(df, '%s'), 已成功寫入", __name__, fname)

        return True

    except OSError as e:
        current_app.logger.error("%s, yf_write_history(df, '%s'), 作業系統錯誤: %s", __name__, fname, e, exc_info=True)
        return False

    except Exception as e:  # pylint: disable=broad-exception-caught
        current_app.logger.error("%s, yf_write_history(df, '%s'), 預期外錯誤: %s", __name__, fname, e, exc_info=True)
        return False


def yf_read_history(fname: str, timezone: str) -> pd.DataFrame:  # pylint: disable=too-many-return-statements
    """從檔案讀取股票歷史資料，並處理索引和時區。

    Args:
        fname (str): 檔案完整路徑。
        timezone (str): 目標時區字串 (例如 'Asia/Taipei', 'America/New_York')。

    Returns:
        pd.DataFrame:
            1. 包含標準欄位和轉換時區的 DatetimeIndex。
            2. 如果失敗，返回空的 DataFrame。
    """
    current_app.logger.info("%s, yf_read_history('%s', '%s'), 開始讀取檔案", __name__, fname, timezone)

    def _log_and_return(msg: str, e: Exception) -> pd.DataFrame:
        current_app.logger.error("%s, yf_read_history('%s', '%s'), %s: %s", __name__, fname, timezone, msg, e, exc_info=True)
        return pd.DataFrame()

    try:
        df = pd.read_csv(fname, index_col=0, encoding="utf-8", parse_dates=True)  # 將第一欄作為索引，並嘗試解析日期

        if df.empty:
            current_app.logger.warning("%s, yf_read_history('%s', '%s'), 檔案內無資料", __name__, fname, timezone)
            return pd.DataFrame()

        try:
            target_tz = ZoneInfo(timezone)
            df.index = pd.to_datetime(df.index, utc=True).tz_convert(target_tz)  # 轉換時區

        except ZoneInfoNotFoundError as e:
            return _log_and_return("轉換時區錯誤", e)

        except Exception as e:  # pylint: disable=broad-exception-caught
            return _log_and_return("轉換時區發生預期外錯誤", e)

        valid_cols = [col for col in STANDARD_COLUMNS if col in df.columns]  # 只保留標準欄位
        if not valid_cols:
            current_app.logger.warning("%s, yf_read_history('%s', '%s'), 不包含任何標準 OHLCV 欄位", __name__, fname, timezone)
            return pd.DataFrame()
        df = df[valid_cols]

        current_app.logger.info("%s, yf_read_history('%s', '%s'), 讀取資料列數: %i", __name__, fname, timezone, len(df))
        return df

    except FileNotFoundError as e:
        return _log_and_return("找不到文件", e)

    except pd.errors.EmptyDataError as e:
        return _log_and_return("檔案內無資料", e)

    except Exception as e:  # pylint: disable=broad-exception-caught
        return _log_and_return("預期外錯誤", e)


def write_timestamp(fname: str) -> float | None:
    """將目前的 Unix 時間戳記 (秒) 寫入指定的檔案。

    Args:
        fname (str): 檔案完整路徑。

    Returns:
        float | None: 成功寫入則返回 Unix 時間戳記；否則返回 None。
    """
    current_app.logger.info("%s, write_timestamp('%s'), 開始寫入時間戳記", __name__, fname)

    timestamp = datetime.now().timestamp()
    try:
        dir_name = os.path.dirname(fname)  # 確保目標檔案的目錄存在
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        with open(fname, "w", encoding="utf-8") as f:
            f.write(str(timestamp))

        current_app.logger.info("%s, write_timestamp('%s'), 已寫入時間戳記: %f", __name__, fname, timestamp)
        return timestamp

    except OSError as e:
        current_app.logger.error("%s, write_timestamp('%s'), 作業系統錯誤: %s", __name__, fname, e, exc_info=True)
        return None

    except Exception as e:  # pylint: disable=broad-exception-caught
        current_app.logger.error("%s, write_timestamp('%s'), 預期外錯誤: %s", __name__, fname, e, exc_info=True)
        return None


def check_timestamp_delta(fname: str, default_delta: float) -> float:
    """檢查檔案中儲存的時間戳記與目前時間的差值 (秒)。

    Args:
        fname (str): 包含時間戳記的檔案完整路徑。
        default_delta (float): 如果檔案不存在或讀取/解析失敗，返回此預設差值。

    Returns:
        float: 目前時間與檔案中時間戳記的實際差值 (秒)，或預設差值。
    """
    current_app.logger.info("%s, check_timestamp_delta('%s', '%f'), 開始檢查時間戳記", __name__, fname, default_delta)

    try:
        with open(fname, "r", encoding="utf-8") as f:
            timestamp = float(f.read().strip())
            delta = datetime.now().timestamp() - timestamp

    except FileNotFoundError as e:
        current_app.logger.warning("%s, check_timestamp_delta('%s', '%f'), 檔案不存在: %s", __name__, fname, default_delta, e)
        delta = default_delta

    except (ValueError, TypeError) as e:
        current_app.logger.warning("%s, check_timestamp_delta('%s', '%f'), 無法解析時間戳記: %s", __name__, fname, default_delta, e)
        delta = default_delta

    except Exception as e:  # pylint: disable=broad-exception-caught
        current_app.logger.warning("%s, check_timestamp_delta('%s', '%f'), 預期外錯誤: %s", __name__, fname, default_delta, e)
        delta = default_delta

    return delta


def fetch(ticker: str, path_csv: str, path_ts: str, delta_min: int = 3600, period: str = "max", interval: str = "1d") -> bool:
    """檢查時間戳記，如果快取過期或不存在，則從 yFinance 獲取新數據，並將其存檔和更新時間戳記。

    Args:
        ticker (str): 股票代碼。
        path_csv (str): 快取檔案的完整路徑。
        path_ts (str): 時間戳記檔案的完整路徑。
        delta_min (int, optional): 快取的有效期限 (秒)。預設為 3600 秒 (1 小時)。
        period (str, optional): 傳遞給 yf_get_history 的期間參數。預設為 "max"。
        interval (str, optional): 傳遞給 yf_get_history 的間隔參數。預設為 "1d"。

    Returns:
        bool: 快取仍然有效或成功更新快取，返回 True；更新快取失敗，返回 False。
    """
    current_app.logger.info("%s, fetch('%s', ...), 開始取得或更新快取資料", __name__, ticker)

    delta = check_timestamp_delta(path_ts, delta_min)
    if delta >= delta_min:
        current_app.logger.info("%s, fetch('%s', ...), 快取過期或不存在", __name__, ticker)
        df_new = yf_get_history(ticker, period=period, interval=interval)
        if not df_new.empty:  # 有取得資料
            is_writed = yf_write_history(df_new, path_csv)
            if is_writed:  # 資料寫入成功
                is_writed_ts = write_timestamp(path_ts) is not None
                if is_writed_ts:  # 時間戳記寫入成功
                    current_app.logger.info("%s, fetch('%s', ...), 快取更新成功", __name__, ticker)
                    return True

        current_app.logger.error("%s, fetch('%s', ...), 無法更新快取", __name__, ticker)
        return False

    current_app.logger.info("%s, fetch('%s', ...), 快取未過期", __name__, ticker)
    return True


if __name__ == "__main__":
    pass
