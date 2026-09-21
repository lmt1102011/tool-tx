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
    try:
        path = cfg_path or os.path.join(os.environ.get("ANDROID_PRIVATE", "."), "config.txt")
        with open(path) as f:
            for line in f:
                if "server-url" in line.lower() or "SERVER_URL" in line:
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return None
