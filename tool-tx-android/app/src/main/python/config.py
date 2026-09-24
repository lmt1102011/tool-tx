"""
config.py — Configuration for Chaquopy backend.
"""
import json
import os

API_KEY = "AIzaSyCN8VEuBWsnXrZqSWJYrFkZd7ckdFIqbCg"
FIREBASE_DB = "https://tool-tx-by-lmt-default-rtdb.firebaseio.com"
SESSION_PATH = os.path.join(os.environ.get("ANDROID_PRIVATE", "."), "session.json")
WEB_TOPUP = "https://lmt1102011.github.io/tool-tx/user.html"
FORK_PACKAGE = "org.cromite.cromite"
FORK_ACTIVITY = "org.chromium.chrome.browser.ChromeTabbedActivity"
SERVER_URL_JSON = "https://lmt1102011.github.io/tool-tx/server-url.json"

# Nguồn fallback: đọc trực tiếp từ repo (không qua CDN GitHub Pages → URL mới hiện ngay
# khi launcher publish, không bị cache lâu).
SERVER_URL_RAW = [
    "https://raw.githubusercontent.com/lmt1102011/tool-tx/gh-pages/server-url.json",
    "https://raw.githubusercontent.com/lmt1102011/tool-tx/main/server-url.json",
]

# Cache địa chỉ server đã tìm được (tránh gọi mạng lại mỗi lần kết nối -> treo kéo dài).
_CACHED_SERVER = ""
_CACHE_FRESH_S = 15


def _read_config_files(cfg_path=None):
    base = os.environ.get("ANDROID_PRIVATE", "/data/data/com.lmt.tooltx")
    candidates = []
    if cfg_path:
        candidates.append(cfg_path)
    candidates += [
        os.path.join(base, "config.txt"),
        os.path.join(base, "files", "config.txt"),
        "/storage/emulated/0/Download/config.txt",
        "/storage/emulated/0/config.txt",
        os.path.join(os.path.expanduser("~"), "Download", "config.txt"),
        os.path.join(base, "config", "config.txt"),
    ]
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read().strip()
            if not text:
                continue
            if text.startswith("{"):
                v = json.loads(text).get("server") or ""
            else:
                v = ""
                for line in text.splitlines():
                    if "server-url" in line.lower() or "SERVER_URL" in line:
                        v = line.split("=", 1)[1].strip()
                        break
            v = v.strip().rstrip("/")
            if v:
                return v
        except Exception:
            continue
    return ""


def discover_server(cfg_path=None, force=False):
    """Tìm địa chỉ server JSON: config.txt {"server": ...} hoặc server-url.json trên web.
    Có cache ngắn hạn để kết nối lại nhanh, không gọi mạng mỗi lần."""
    import time
    global _CACHED_SERVER
    v = _read_config_files(cfg_path)
    if v:
        _CACHED_SERVER = v
        return v
    if not force and _CACHED_SERVER:
        return _CACHED_SERVER
    try:
        import urllib.request
        v = _fetch_server_json(SERVER_URL_JSON)
        if not v:
            for src in SERVER_URL_RAW:
                v = _fetch_server_json(src)
                if v:
                    break
        if v:
            _CACHED_SERVER = v
            return v
    except Exception:
        pass
    _CACHED_SERVER = ""
    return ""


def _fetch_server_json(src):
    """Tải server-url.json, trả URL server hoặc chuỗi rỗng."""
    try:
        import json
        import urllib.request
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.loads(r.read().decode("utf-8"))
            return (data.get("url") or "").strip().rstrip("/")
    except Exception:
        return ""


def forget_server():
    """Xoá cache địa chỉ server (dùng khi Reset mã)."""
    global _CACHED_SERVER
    _CACHED_SERVER = ""