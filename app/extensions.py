"""
Flask 擴充套件實例：用於避免循環引用。
"""

from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect

talisman = Talisman()
csrf = CSRFProtect()
