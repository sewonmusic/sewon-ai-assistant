from pathlib import Path
from dotenv import load_dotenv
import os

_BASE = Path(__file__).parent.parent.parent

load_dotenv(_BASE / ".env")

DB_PATH = _BASE / "database" / "sewon_mapping.db"

ECOUNT_COM_CODE = os.environ["ECOUNT_COM_CODE"]
ECOUNT_USER_ID = os.environ["ECOUNT_USER_ID"]
ECOUNT_API_KEY = os.environ["ECOUNT_API_KEY"]

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

ZONE_URL = "https://oapi.ecount.com/OAPI/V2/Zone"
LAN_TYPE = "ko-KR"

MAX_RETRY = 3
