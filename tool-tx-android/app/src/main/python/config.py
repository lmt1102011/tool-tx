"""
config.py — Configuration for Chaquopy backend.
"""
import os

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_PATH = os.path.join(APP_DIR, "session.json")
CFG_PATH = os.path.join(APP_DIR, "config.txt")
WEB_TOPUP = "https://lmt1102011.github.io/tool-tx/user.html"
FORK_PACKAGE = "org.lmt1102011.chromefork"
FORK_ACTIVITY = "org.chromium.chrome.browser.ChromeLauncherActivity"

def discover_server(cfg_path=None):
    path = cfg_path or CFG_PATH
    try:
        with open(path) as f:
            for line in f:
                if "server-url" in line.lower() or "SERVER_URL" in line:
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return None
