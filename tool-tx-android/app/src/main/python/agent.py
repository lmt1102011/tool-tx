"""
agent.py — Agent control for Chaquopy (APK).

Hướng A: mở fork Cromite bằng flag CDP dùng chung stack 9222/vs hcdp.
- force-stop Cromite cũ (ngoài flag flag không có hiệu lực nếu process cũ còn chạy)
- am start với intent extra args "--remote-debugging-port=9222"
- poll http://127.0.0.1:9222/json/version tới khi CDP sẵn sàng mới trả True
- trả False kèm lý do nếu không connect được (app hiện "khởi động chrome fork thất bại")
"""

import json
import subprocess
import threading
import time

from config import FORK_PACKAGE, FORK_ACTIVITY

_running = False
_started_at = 0.0
_lock = threading.Lock()

CDP_PORT = 9222
START_TIMEOUT = 35          # tổng thời gian đợi CDP sau khi am start
POLL_INTERVAL = 1.5
CDP_WAIT_BEFORE_START = 2.0  # để process fork kịp init

_CDP_JSON = None


def log(msg):
    try:
        import logging
        logging.getLogger("agent").info(msg)
    except Exception:
        pass
    try:
        print("[agent] " + msg)
    except Exception:
        pass


def _cromite_running():
    try:
        out = subprocess.check_output(
            ["pidof", FORK_PACKAGE],
            shell=False, timeout=5,
        ).decode("utf-8", "replace").strip()
        return bool(out)
    except Exception:
        return False


def _cdp_version():
    """Trả dict JSON từ http://127.0.0.1:9222/json/version hoặc None."""
    global _CDP_JSON
    try:
        import urllib.request
        req = urllib.request.Request(
            "http://127.0.0.1:%d/json/version" % CDP_PORT,
            headers={"User-Agent": "tooltx-agent/1.0"},
        )
        with urllib.request.urlopen(req, timeout=2.0) as r:
            raw = r.read(4096)
        data = json.loads(raw.decode("utf-8", "replace"))
        _CDP_JSON = data
        return data
    except Exception:
        return None


def wait_cdp(timeout=START_TIMEOUT):
    """Poll http://127.0.0.1:9222/json/version cho tới khi có kết quả."""
    deadline = time.time() + timeout
    first = None
    while time.time() < deadline:
        data = _cdp_version()
        if data and data.get("webSocketDebuggerUrl"):
            return data
        if first is None:
            first = time.time()
        time.sleep(POLL_INTERVAL)
    return None


def start_fork(server_url, code):
    """Mở Cromite với CDP TCP 9222, chờ connect được thì trả True."""
    global _running, _started_at
    with _lock:
        # 1) force-stop process cũ — flag mới chỉ có hiệu lực khi fork khởi động lại từ đầu
        try:
            subprocess.run(["am", "force-stop", FORK_PACKAGE],
                           capture_output=True, timeout=15)
        except Exception:
            pass
        time.sleep(1.0)

        # 2) mở Cromite kèm args flag CDP
        args = "--remote-debugging-port=%d --remote-debugging-address=127.0.0.1 --remote-allow-origins=*" % CDP_PORT
        cmd = ["am", "start", "-n",
               "%s/%s" % (FORK_PACKAGE, FORK_ACTIVITY),
               "--es", "args", args]
        log("am start: " + " ".join(cmd))
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            out = (r.stdout or "") + (r.stderr or "")
            if r.returncode != 0 or "Error" in out or "Exception" in out:
                log("am start fail: " + out)
                return False
        except Exception as e:
            log("am start exception: " + repr(e))
            return False

        # 3) chờ CDP sẵn sàng
        time.sleep(CDP_WAIT_BEFORE_START)
        data = wait_cdp()
        if data is None:
            log("CDP khong bat duoc tren port %d — dang thu lai..." % CDP_PORT)
            time.sleep(2.0)
            data = wait_cdp(START_TIMEOUT - 8)
        if data is None:
            log("CDP 9222 van khong connect (fork mo nhung khong listen TCP).")
            if _cromite_running():
                log("Cromite dang chay nhung khong mo CDP — co the bo qua intent args, can fallback localabstract:chrome_devtools_remote.")
            _running = False
            return False

        _running = True
        _started_at = time.time()
        log("CDP OK: " + (data.get("Browser") or data.get("browser") or "?"))
        return True


def start_agent(server_url, code):
    """Bật agent thật: = mở fork + kết nối CDP. Trả True khi CDP connect OK."""
    return start_fork(server_url, code)


def stop():
    global _running
    with _lock:
        _running = False


def is_running():
    return _running


def cdp_json():
    return _CDP_JSON