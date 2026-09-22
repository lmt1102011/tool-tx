"""
config.py — Configuration for Chaquopy backend.
"""
import os

API_KEY = "AIzaSyCN8VEuBWsnXrZqSWJYrFkZd7ckdFIqbCg"
FIREBASE_DB = "https://tooltx-default-rtdb.firebaseio.com"
SESSION_PATH = os.path.join(os.environ.get("ANDROID_PRIVATE", "."), "session.json")
WEB_TOPUP = "https://lmt1102011.github.io/tool-tx/user.html"
FORK_PACKAGE = "org.lmt1102011.chromefork"
FORK_ACTIVITY = "org.chromium.chrome.browser.ChromeLauncherActivity"

def discover_server(cfg_path=None):
    import os
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
    ]
    for path in candidates:
        try:
            with open(path) as f:
                for line in f:
                    if "server-url" in line.lower() or "SERVER_URL" in line:
                        return line.split("=", 1)[1].strip()
        except Exception:
            continue
    return None
