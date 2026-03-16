"""
Technical Analysis (TA) Blueprint：初始化 Blueprint 並匯入路由設定。
"""

from app import create_bp

bp = create_bp(__name__.rsplit(".", maxsplit=1)[-1])  # 建立 Blueprint 實例

from . import routes  # pylint: disable=wrong-import-position


if __name__ == "__main__":
    pass
