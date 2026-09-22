"""
config.py — Configuration for Chaquopy backend.
"""
import json
import os

API_KEY = "AIzaSyCN8VEuBWsnXrZqSWJYrFkZd7ckdFIqbCg"
FIREBASE_DB = "https://tool-tx-by-lmt-default-rtdb.firebaseio.com"
SESSION_PATH = os.path.join(os.environ.get("ANDROID_PRIVATE", "."), "session.json")
WEB_TOPUP = "https://lmt1102011.github.io/tool-tx/user.html"
FORK_PACKAGE = "org.lmt1102011.chromefork"
FORK_ACTIVITY = "org.chromium.chrome.browser.ChromeLauncherActivity"
SERVER_URL_JSON = "https://lmt1102011.github.io/tool-tx/server-url.json"


def discover_server(cfg_path=None):
    """Tìm địa chỉ server JSON: config.txt {"server": ...} hoặc server-url.json trên web."""
    import os
    import urllib.request
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
    try:
        with urllib.request.urlopen(SERVER_URL_JSON, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8"))
            return (data.get("url") or "").strip().rstrip("/")
    except Exception:
        return ""
