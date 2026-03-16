"""
Flask 設定模組：包含基本設定、開發環境設定及生產環境設定類別。
"""

import os
from dotenv import load_dotenv
from flask import Flask


basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".flaskenv"), override=True)


class Config:
    """Flask 應用程式設定的基本類別。"""

    BASEDIR = basedir

    FLASK_APP = os.getenv("FLASK_APP", default="run.py")
    FLASK_ENV = os.getenv("FLASK_ENV", default="production")
    FLASK_PORT = int(os.getenv("FLASK_PORT", default="5000"))
    FLASK_DEBUG = bool(int(os.getenv("FLASK_DEBUG", default="0")))  # https://flask.palletsprojects.com/en/stable/config/#DEBUG
    TESTING = bool(int(os.getenv("TESTING", default="0")))  # https://flask.palletsprojects.com/en/stable/config/#TESTING

    # https://flask.palletsprojects.com/en/stable/config/#SECRET_KEY
    # 可用於產生 secret key 的方式：
    #   1. openssl rand -hex 32
    #   2. python -c 'import secrets; print(secrets.token_hex())'
    #   3. python -c 'import binascii; import os; print(binascii.hexlify(os.urandom(32)).decode("utf-8"))'
    INSECURE_DEFAULT_SECRET_KEY = "!!!_CHANGE_ME_IN_PRODUCTION_!!!"
    SECRET_KEY = os.getenv("SECRET_KEY", default=INSECURE_DEFAULT_SECRET_KEY)

    LOG_LEVEL = os.getenv("LOG_LEVEL", default="ERROR").upper()

    TA_CACHE_DIR = os.path.join(basedir, os.getenv("TA_CACHE_DIR", default="cache"))
    TA_CACHE_DIR_YF = os.path.join(TA_CACHE_DIR, os.getenv("TA_CACHE_SUBDIR_YF", default="yf"))
    TA_CACHE_DIR_YF_TS = os.path.join(TA_CACHE_DIR, os.getenv("TA_CACHE_SUBDIR_YF_TS", default="yf/ts"))
    TA_CACHE_DELTA_YF_MIN = int(os.getenv("TA_CACHE_DELTA_YF_MIN", default="3600"))

    # https://flask.palletsprojects.com/en/stable/config/#SESSION_COOKIE_HTTPONLY
    SESSION_COOKIE_HTTPONLY = bool(int(os.getenv("SESSION_COOKIE_HTTPONLY", default="1")))
    # https://flask.palletsprojects.com/en/stable/config/#SESSION_COOKIE_SECURE
    SESSION_COOKIE_SECURE = bool(int(os.getenv("SESSION_COOKIE_SECURE", default="1")))
    # https://flask.palletsprojects.com/en/stable/config/#SESSION_COOKIE_SAMESITE
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", default="Strict")
    # https://flask-wtf.readthedocs.io/en/1.2.x/config/
    WTF_CSRF_TIME_LIMIT = int(os.getenv("WTF_CSRF_TIME_LIMIT", default="86400"))  # 24 小時

    @staticmethod
    def init_app(app: Flask) -> None:
        """初始化 Flask 應用程式實例。

        Args:
            app (Flask): Flask 應用程式實例。

        Returns:
            None

        Raises:
            ValueError: 如果無法建立快取目錄，則拋出錯誤。
        """
        try:
            os.makedirs(app.config["TA_CACHE_DIR_YF"], exist_ok=True)
            os.makedirs(app.config["TA_CACHE_DIR_YF_TS"], exist_ok=True)
        except OSError as e:
            app.logger.error("%s, Config.init_app(...), 無法建立快取目錄: %s", __name__, e, exc_info=True)
            raise ValueError("無法建立快取目錄") from e


class DevelopmentConfig(Config):
    """Flask 應用程式開發環境設定類別。"""

    FLASK_ENV = os.getenv("FLASK_ENV", default="development")
    FLASK_DEBUG = bool(int(os.getenv("FLASK_DEBUG", default="1")))
    LOG_LEVEL = os.getenv("LOG_LEVEL", default="DEBUG").upper()
    TESTING = bool(int(os.getenv("TESTING", default="1")))


class ProductionConfig(Config):
    """Flask 應用程式生產環境設定類別。"""

    @staticmethod
    def init_app(app: Flask) -> None:
        """初始化 Flask 應用程式生產環境實例。

        Args:
            app (Flask): Flask 應用程式生產環境實例。

        Returns:
            None

        Raises:
            ValueError: 如果無法建立快取目錄、缺少 SECRET_KEY、啟用 FLASK_DEBUG，則拋出錯誤。
        """
        Config.init_app(app)

        secret_key = app.config.get("SECRET_KEY")
        if not secret_key or secret_key == Config.INSECURE_DEFAULT_SECRET_KEY:
            raise ValueError("正式環境缺少 SECRET_KEY")

        if app.config.get("FLASK_DEBUG"):
            raise ValueError("正式環境不應該啟用 FLASK_DEBUG")


if __name__ == "__main__":
    pass
