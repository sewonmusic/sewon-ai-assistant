import requests
from .config import (
    ECOUNT_COM_CODE, ECOUNT_USER_ID, ECOUNT_API_KEY,
    LAN_TYPE, ZONE_URL,
)

_session_cache: dict = {}  # {"zone": str, "session_id": str}


def get_zone() -> str:
    resp = requests.post(
        ZONE_URL,
        json={"COM_CODE": ECOUNT_COM_CODE},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if str(data.get("Status")) != "200" or not data.get("Data", {}).get("ZONE"):
        raise RuntimeError(f"Zone 조회 실패: {data}")
    return data["Data"]["ZONE"]


def login(zone: str) -> str:
    url = f"https://oapi{zone}.ecount.com/OAPI/V2/OAPILogin"
    resp = requests.post(
        url,
        json={
            "COM_CODE": ECOUNT_COM_CODE,
            "USER_ID": ECOUNT_USER_ID,
            "API_CERT_KEY": ECOUNT_API_KEY,
            "LAN_TYPE": LAN_TYPE,
            "ZONE": zone,
        },
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    # 응답 구조: Data.Datas.SESSION_ID
    datas = (data.get("Data") or {}).get("Datas") or {}
    session_id = datas.get("SESSION_ID") if isinstance(datas, dict) else None
    if not session_id:
        raise RuntimeError(f"로그인 실패: {data}")
    return session_id


def get_session() -> tuple[str, str]:
    """Return (zone, session_id), reusing cached values if available."""
    if _session_cache.get("zone") and _session_cache.get("session_id"):
        return _session_cache["zone"], _session_cache["session_id"]
    zone = get_zone()
    session_id = login(zone)
    _session_cache["zone"] = zone
    _session_cache["session_id"] = session_id
    return zone, session_id


def invalidate_session():
    _session_cache.clear()
