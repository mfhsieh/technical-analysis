"""
Flask 啟動腳本：初始化 Flask 實例並啟動 Web 伺服器。
"""

from flask import Flask
from app import create_app

app: Flask = create_app()  # 供 WSGI 伺服器（如 Gunicorn）直接載入


if __name__ == "__main__":
    app.logger.info("%s, FLASK PORT: %s", __name__, app.config["FLASK_PORT"])
    app.logger.info("%s, FLASK DEBUG: %s", __name__, app.config["FLASK_DEBUG"])
    app.run(host="0.0.0.0", port=app.config["FLASK_PORT"], debug=app.config["FLASK_DEBUG"])
