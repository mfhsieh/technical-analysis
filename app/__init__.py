"""
Flask 工廠：初始化 Flask 實例、註冊路由、Blueprint 與安全性配置。
"""

import os
import logging
from flask import Flask, Blueprint, Response, request, url_for, redirect, render_template
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
from werkzeug.exceptions import HTTPException
from config import DevelopmentConfig, ProductionConfig
from app.extensions import talisman, csrf

# from flask_compress import Compress


def create_bp(name: str) -> Blueprint:
    """建立 Blueprint 的輔助函式。

    Args:
        name (str): Blueprint 名稱。

    Returns:
        Blueprint: 建立的 Blueprint 實例。
    """
    return Blueprint(
        name,
        import_name=f"app.blueprints.{name}",
        template_folder="templates",
        static_folder="static",
    )


def register_bp(app: Flask) -> None:
    """註冊 Blueprint 子網頁。

    Args:
        app (Flask): Flask 應用程式實例。

    Returns:
        None
    """
    from app.blueprints.ta import bp as bp_ta  # pylint: disable=import-outside-toplevel

    app.register_blueprint(bp_ta, url_prefix=f"/{bp_ta.name}")
    app.logger.info("%s, 註冊 Blueprint 子網頁: %s", __name__, bp_ta.name)


def register_route(app: Flask) -> None:
    """註冊 Flask 路由。

    Args:
        app (Flask): Flask 應用程式實例。

    Returns:
        None
    """
    app.logger.info("%s, 註冊路由", __name__)

    @app.route("/")
    def index() -> Response:
        """主頁面預設路由。

        Returns:
            Response: 重定向結果。
        """
        app.logger.info("%s, index(), request.args: %s", __name__, request.args)
        return redirect(url_for("ta.index"))  # type: ignore

    @app.route("/favicon.ico")
    def favicon() -> Response:
        """favicon.ico 路由。

        Returns:
            Response: favicon.ico 的靜態檔案。
        """
        app.logger.info("%s, favicon(), request.args: %s", __name__, request.args)
        return app.send_static_file("favicon.ico")

    @app.route("/robots.txt")
    def robots() -> Response:
        """robots.txt 路由。

        Returns:
            Response: robots.txt 的靜態檔案。
        """
        app.logger.info("%s, robots(), request.args: %s", __name__, request.args)
        return app.send_static_file("robots.txt")

    @app.errorhandler(HTTPException)
    def handle_http_exception(exception: HTTPException) -> tuple[str, int]:
        """處理 HTTP 異常。

        Args:
            exception (HTTPException): HTTP 異常實例。

        Returns:
            tuple[str, int]: 返回渲染的模板和狀態碼。
        """
        code = getattr(exception, "code", 500)
        app.logger.info("%s, handle_http_exception(%s), path: %s", __name__, code, request.path)
        return render_template("http_exception.html", exception=exception), code

    @app.errorhandler(Exception)
    def handle_exception(exception: Exception) -> tuple[str, int]:
        """處理一般異常。

        Args:
            exception (Exception): 異常實例。

        Returns:
            tuple[str, int]: 返回渲染的模板和狀態碼。
        """
        code = getattr(exception, "code", 500)
        app.logger.info("%s, handle_exception(%s), path: %s", __name__, code, request.path)
        return render_template("exception.html", exception=exception), code


def create_app(config_name: str | None = None) -> Flask:
    """設定環境、主程式、日誌及註冊 Blueprint 與 Dash 子網頁。

    Args:
        config_name (str | None): 環境名稱：development, production 或 default。若為 None，則會從環境變數 FLASK_ENV 讀取，若無該環境變數則視為 production。

    Returns:
        Flask: 設定好的 Flask 應用程式實例。

    Raises:
        ValueError: 如果 config_name 不是 development, production 或 default 則抛出錯誤。
    """

    # 設定環境
    config = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "default": ProductionConfig,
    }

    if config_name is None:
        config_name = os.getenv("FLASK_ENV", default="production")

    if config_name not in config:
        raise ValueError(f"未知的 FLASK_ENV: {config_name}")

    # 設定主程式
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        instance_relative_config=True,
    )
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # https://flask.palletsprojects.com/en/stable/api/#flask.json.provider.DefaultJSONProvider.ensure_ascii
    app.json.ensure_ascii = False

    # https://flask-wtf.readthedocs.io/en/1.2.x/csrf/
    csrf.init_app(app)

    # https://github.com/GoogleCloudPlatform/flask-talisman
    # 預設 CSP。各別 Blueprint 可透過 @talisman 裝飾器覆寫。
    default_csp = {
        "default-src": ["'self'"],
        "object-src": ["'none'"],
    }
    talisman.init_app(app, content_security_policy=default_csp)

    # https://github.com/colour-science/flask-compress
    # Compress(app)

    # 設定日誌
    log_level = app.config.get("LOG_LEVEL", "ERROR").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.WARNING),
        format="%(asctime)s - %(name)s [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler()],
    )
    app.logger.setLevel(log_level)

    app.logger.info("%s, 主程式環境配置: %s", __name__, config_name)
    app.logger.info("%s, 主程式日誌級別: %s", __name__, log_level)

    # 註冊 Blueprint 及 Dash 子網頁
    register_bp(app)

    # 輸出 Flask URL Map
    # app.logger.debug("%s, Flask URL Map", __name__)
    # for rule in app.url_map.iter_rules():
    #     app.logger.debug("%s, Rule and Endpoint: %s, %s", __name__, rule.rule, rule.endpoint)

    # 註冊路由
    register_route(app)

    return app


if __name__ == "__main__":
    pass
