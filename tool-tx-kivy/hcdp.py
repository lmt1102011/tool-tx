# hcdp.py — CDP Controller chạy trong APK Kivy, điều khiển Chromium fork
# ngay trên cùng điện thoại Android (không PC, không ADB, không server trung gian).
#
# Flow:
#   1) start_browser()  — startActivity mở Chromium fork (đã được build có DevTools TCP 9222 built-in)
#   2) wait_until_ready(9222) — requests GET http://127.0.0.1:9222/json/version
#                              -> lấy webSocketDebuggerUrl
#   3) CdpClient(webSocketDebuggerUrl) — Page.navigate / Runtime.evaluate / Page.reload / ...
#
# Yêu cầu APK:
#   - INTERNET permission
#   - cho phép cleartext tới 127.0.0.1 (usesCleartextTraffic=true hoặc network_security_config.xml)
#     vì browser fork phục vụ http://127.0.0.1 (không có TLS).

import json
import threading
import time

try:
    import websocket  # websocket-client
except Exception:  # pragma: no cover
    websocket = None

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

DEFAULT_PORT = 9222
_VER_URL = "http://127.0.0.1:{port}/json/version"


class CdpError(RuntimeError):
    pass


# ────────────────────── HTTP probe (/json/version) ──────────────────────
def http_json(path="/json/version", port=DEFAULT_PORT, timeout=5):
    """GET http://127.0.0.1:{port}{path} -> dict (raise CdpError nếu không đến)."""
    if requests is None:
        import urllib.request

        url = "http://127.0.0.1:%d%s" % (port, path)
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    url = "http://127.0.0.1:%d%s" % (port, path)
    r = requests.get(url, timeout=timeout)
    if r.status_code >= 300:
        raise CdpError("HTTP %d %s" % (r.status_code, path))
    return r.json()


def probe(port=DEFAULT_PORT, timeout=5):
    """Lấy webSocketDebuggerUrl từ /json/version."""
    v = http_json("/json/version", port, timeout)
    if not (v or {}).get("webSocketDebuggerUrl"):
        raise CdpError("/json/version không có webSocketDebuggerUrl: %r" % v)
    return v


def wait_until_ready(port=DEFAULT_PORT, timeout=90):
    """Poll /json/version cho tới khi browser fork mở CDP xong (trả dict /json/version)."""
    t0 = time.time()
    err = None
    while time.time() - t0 < timeout:
        try:
            return probe(port, 3)
        except Exception as e:
            err = e
            time.sleep(1.5)
    raise CdpError("Chromium fork chưa mở CDP sau %ss: %s" % (timeout, err))


# ────────────────────── WebSocket CDP ──────────────────────
class CdpClient:
    """Client WebSocket đến webSocketDebuggerUrl. Gửi lệnh đồng bộ, nhận events async."""

    def __init__(self, ws_url, on_event=None):
        if websocket is None:
            raise CdpError("thiếu websocket-client")
        self.ws_url = ws_url
        self.on_event = on_event  # (method, params)
        self._ws = None
        self._seq = 0
        self._lock = threading.Lock()
        self._pending = {}  # id -> threading.Event with result
        self._closed = False

    def connect(self):
        try:
            self._ws = websocket.create_connection(self.ws_url, timeout=30)
        except Exception as e:
            raise CdpError("không nối CDP ws: %s" % e)
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        ws = self._ws
        try:
            while not self._closed:
                ws.settimeout(0.2)
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                except Exception:
                    break
                m = json.loads(raw) if raw else None
                if not m:
                    continue
                if m.get("id"):
                    ent = self._pending.pop(m.get("id"), None)
                    if ent:
                        ent["m"] = m  # {'result'|'error'}
                        ent["ev"].set()
                elif m.get("method") and self.on_event:
                    try:
                        self.on_event(m.get("method"), m.get("params"))
                    except Exception:
                        pass
        finally:
            self._closed = True

    def call(self, method, params=None, timeout=30):
        with self._lock:
            self._seq += 1
            _id = self._seq
            ent = {"ev": threading.Event(), "m": None}
            self._pending[_id] = ent
        msg = {"id": _id, "method": method, "params": params or {}}
        try:
            self._ws.send(json.dumps(msg))
        except Exception as e:
            self._pending.pop(_id, None)
            raise CdpError("gửi lệnh %s thất bại: %s" % (method, e))
        if not ent["ev"].wait(timeout):
            self._pending.pop(_id, None)
            raise CdpError("timeout CDP: %s" % method)
        m = ent["m"]
        if "error" in m:
            raise CdpError("%s -> %s" % (method, m["error"].get("message")))
        return m.get("result", {})

    # ── các lệnh yêu cầu ──
    def navigate(self, url):
        return self.call("Page.navigate", {"url": url})

    def reload(self, ignore_cache=False):
        return self.call("Page.reload", {"ignoreCache": ignore_cache})

    def evaluate(self, expr, await_promise=True):
        r = self.call("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": bool(await_promise),
            "userGesture": True,
        })
        if r.get("exceptionDetails"):
            d = (r["exceptionDetails"].get("exception") or {}).get("description") or "lỗi JS"
            raise CdpError(str(d)[:400])
        return (r.get("result") or {}).get("value")

    def enable_runtime(self):
        return self.call("Runtime.enable")

    def get_document(self):
        return self.call("DOM.getDocument")

    def close(self):
        self._closed = True
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass


# ────────────────────── Start Browser (Android) ──────────────────────
def start_browser(url="about:blank", package=None, activity=None, port=DEFAULT_PORT):
    """Mở Chromium fork bằng startActivity (phải gọi khi app ở foreground).

    package/activity: ví dụ fork đã ký là:
        package="org.lmt1102011.chromefork", activity="org.chromium.chrome.browser.ChromeTabbedActivity"
    Nếu để None: gửi ACTION_VIEW (hệ thống sẽ chọn trình duyệt — nhưng MUỐN fork,
    hãy truyền package để chọn đúng app, tránh Chrome/WebView chặn CDP).
    Không trả về lỗi một cách thầm lặng: app gọi nó trong luồng riêng, rồi wait_until_ready().
    """
    try:
        from jnius import autoclass  # android_runtime của python-for-android
    except Exception as e:
        raise CdpError("start_browser chỉ chạy trong APK Android: %s" % e)
    Intent = autoclass("android.content.Intent")
    Uri = autoclass("android.net.Uri")
    from android import mActivity  # noqa: E402

    if package:
        i = Intent()
        i.setClassName(package, activity or "<activity-class-missing>")
    else:
        i = Intent(Intent.ACTION_VIEW, Uri.parse(url))
    i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    mActivity.startActivity(i)


# ────────────────────── Tiện ích điều khiển tab game ──────────────────────
def simple_browser_session(port=DEFAULT_PORT, on_event=None, timeout=90):
    """wait_until_ready -> CdpClient nối sẵn. Trả về (client, version)."""
    v = wait_until_ready(port, timeout)
    ws_url = v["webSocketDebuggerUrl"]
    c = CdpClient(ws_url, on_event=on_event)
    c.connect()
    return c, v


class ForkCdpBridge:
    """Backend CDP cho agent.py — điều khiển Chromium Fork chạy trên cùng điện thoại.

    wait_ready(timeout) / ensure_game_tab(url) / eval(expr) / reload().
    Dùng 2 connection:
      - browser-level: Target.getTargets / createTarget (quản lý tab).
      - page-level (ws của tab): Runtime.evaluate trực tiếp trong tab game
        -> "một tab riêng trên điện thoại" do fork hiển thị.
    """

    def __init__(self, port=DEFAULT_PORT, on_log=None):
        self.port = port
        self.on_log = on_log or (lambda m: None)
        self._browser = None      # CdpClient (browser ws)
        self._page = None         # CdpClient (page ws)
        self._page_url = ""

    def _log(self, m):
        try:
            self.on_log(m)
        except Exception:
            pass

    def wait_ready(self, timeout=120):
        v = wait_until_ready(self.port, timeout)          # http://127.0.0.1:9222/json/version
        self._log("CDP fork: " + v["webSocketDebuggerUrl"][:48] + "...")
        self._browser = CdpClient(v["webSocketDebuggerUrl"])
        self._browser.connect()
        try:
            self._browser.enable_runtime()
        except Exception:
            pass

    @staticmethod
    def _host_of(url):
        try:
            from urllib.parse import urlparse
            return (urlparse(url).hostname or "").replace("www.", "")
        except Exception:
            return ""

    def _connect_page(self, target_id):
        """Nối CdpClient vào đúng tab (qua /json) để evaluate trong trang đó."""
        try:
            data = http_json("/json", self.port)
            tabs = data if isinstance(data, list) else data.get("tabs", [])
            for t in tabs:
                if t.get("id") == target_id or t.get("type") == "page":
                    ws = t.get("webSocketDebuggerUrl")
                    if ws:
                        old = self._page
                        self._page = CdpClient(ws)
                        self._page.connect()
                        if old:
                            try:
                                old.close()
                            except Exception:
                                pass
                        return True
        except Exception:
            pass
        return False

    def ensure_game_tab(self, url):
        """Đưa 1 tab (mặc định tab hiện có) về trang game => fork hiện đúng tab Sunwin."""
        if not self._browser or not url:
            return
        host = self._host_of(url)
        if host:
            self._host = host
        targets = self._browser.call("Target.getTargets").get("targetInfos", [])
        pages = [x for x in targets if x.get("type") == "page"]
        t = pages[0] if pages else None
        if not t:
            created = self._browser.call("Target.createTarget", {"url": url})
            t = {"targetId": created["targetId"], "url": url}
            time.sleep(0.4)
        tid = t["targetId"]
        cur = t.get("url") or ""
        if not self._connect_page(tid):
            raise RuntimeError("không nối được CDP page cho tab game")
        if not cur or self._host_of(cur) != host:
            self._page.navigate(url)
            self._log("Đã mở tab game: " + host)
        self._page_url = url

    def eval(self, expr, await_promise=True):
        """Runtime.evaluate ngay trong tab game (page-level ws, không cần sessionId)."""
        if not self._page:
            raise RuntimeError("Chưa có tab game")
        return self._page.evaluate(expr, await_promise=await_promise)

    def reload(self, ignore_cache=False):
        if self._page:
            try:
                self._page.reload(ignore_cache)
            except Exception:
                pass


# Demo minh hoạ (chạy thử trên desktop bằng Chromium desktop nếu cần xem format).
if __name__ == "__main__":
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    print("probe:", probe(port))
    print("done")