# core/config.py — hằng số cấu hình + màu brand (dark navy + vàng kim).
import os

IS_ANDROID = bool(os.environ.get("ANDROID_ARGUMENT"))

# Thư mục app: desktop = thư mục dự án; Android = thư mục người dùng của app.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SESSION_PATH = os.path.join(BASE_DIR, "session.json")
CFG_PATH = os.path.join(BASE_DIR, "config.txt")

# nơi chứa file dữ liệu đóng gói trong APK (p4a đặt cúng chỗ với source).
ASSET_ROOT = os.getcwd()
LOGO = os.path.join(ASSET_ROOT, "logo.png")

# Chromium Fork APK (build riêng theo fork/build.sh) — UI riêng, "1 tab riêng trên đth".
FORK_PACKAGE = "org.lmt1102011.chromefork"
FORK_ACTIVITY = "org.chromium.chrome.browser.ChromeLauncherActivity"

# palette
GOLD = (1.0, 0.79, 0.34, 1)
GOLD_DEEP = (0.86, 0.63, 0.20, 1)
GOLD_DIM = (1.0, 0.81, 0.40, 0.18)
NIGHT = (0.04, 0.06, 0.10, 1)
CARD = (0.075, 0.10, 0.17, 0.94)
TXT = (0.93, 0.96, 1.0, 1)
DIM = (0.53, 0.61, 0.76, 1)
RED_T = (0.96, 0.42, 0.46, 1)
BLUE_X = (0.42, 0.67, 0.98, 1)
GREEN = (0.35, 0.85, 0.55, 1)
WARN = (0.97, 0.62, 0.24, 1)