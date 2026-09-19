# agent.py — Agent Chrome CDP chạy tại máy user (desktop).
# Mở browser Chromium (Chrome/Edge/Chromium/Brave/Vivaldi/Opera) cục bộ,
# nối outbound WS tới tool server (/agent-ws), nhận lệnh eval và trả kết quả.
# Tương đương public/agent_chrome.js nhưng viết bằng Python tiêu chuẩn.
#
# Yêu cầu: pip install websocket-client
# Cách dùng:
#   from agent import Agent
#   ag = Agent(on_log=lambda s: print(s))
#   ag.start(server="http://localhost:8787", code="ABC123")

import os
import re
import json
import queue
import shutil
import subprocess
import sys
import threading
import time

import websocket  # websocket-client

BROWSER_NAMES = ["Google/Chrome", "Microsoft/Edge", "BraveSoftware/Brave-Browser",
                 "Chromium", "Vivaldi", "Opera"]


def _win_path(name):
    env = os.environ.get("PROGRAMFILES", "C:/Program Files")
    env86 = os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")
    local = os.path.join(os.environ.get("LOCALAPPDATA", ""), name, "Application")
    names = [
        os.path.join(env, name, "Application"),
        os.path.join(env86, name, "Application"),
        local,
        os.path.join(env, name, "Application", "chrome.exe"),
        os.path.join(env86, name, "Application", "chrome.exe"),
    ]
    return names


def find_browser(explicit=None):
    """Tìm executable Chromium: Chrome, Edge, Chromium, Brave, Vivaldi, Opera (fork Chromium)."""
    if explicit and os.path.isfile(explicit):
        return explicit
    env = os.environ.get("CHROME_PATH", "").strip()
    if env and os.path.isfile(env):
        return env
    if sys.platform.startswith("win"):
        cands = []
        for name in BROWSER_NAMES:
            cands += _win_path(name)
        appdata = os.environ.get("LOCALAPPDATA", "")
        for name in ["Google/Chrome", "Microsoft/Edge", "BraveSoftware/Brave-Browser"]:
            cands.append(os.path.join(appdata, name, "Application"))
        cands += [
            "C:/Program Files/Google/Chrome/Application/chrome.exe",
            "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
            "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
            "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
            "C:/Program Files/Chromium/Application/chrome.exe",
            "C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe",
        ]
        for exe in cands:
            if exe and os.path.isfile(exe):
                return exe
        return None
    # Linux / macOS
    for exe in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                "microsoft-edge", "brave-browser", "vivaldi", "opera"]:
        p = shutil.which(exe)
        if p:
            return p
    if sys.platform == "darwin":
        for name in ["Google Chrome", "Microsoft Edge", "Chromium", "Brave Browser"]:
            p = "/Applications/%s.app/Contents/MacOS/%s" % (name, name.split()[-1].lower() if name != "Google Chrome" else "Google Chrome")
            if os.path.isfile(p):
                return p
    return None


class Agent:
    def __init__(self, on_log=None, chrome_path=None, cdp_backend=None, on_stopped=None):
        self.on_log = on_log or (lambda m, e=False: None)
        self.chrome_path = chrome_path
        self.cdp_backend = cdp_backend  # ForkCdpBridge: dùng CDP của fork đang mở (không spawn)
        self.on_stopped = on_stopped    # gọi 1 lần khi agent dừng (server từ chối hết lượt, mất kết nối, ...)
        self.server = None
        self.code = None
        self.profile_dir = os.path.join(os.environ.get("TEMP") or os.path.join(os.path.expanduser("~"), "tmp"),
                                        "tx-agent-py")
        self._browser_proc = None
        self._cdp_ws = None
        self._cdp_id = 0
        self._cdp_pending = {}
        self._cdp_lock = threading.Lock()
        self._send_lock = threading.Lock()
        self._game_target = None
        self._game_session = None
        self._game_host = ""
        self._game_url = ""
        self._backend_ok = False
        self._stopping = False
        self._stopped_called = False
        self._eval_queue = queue.Queue()
        self._tab_requests = []
        self.running = False

    # ---- log ----
    def log(self, msg, err=False):
        try:
            self.on_log(msg, err)
        except Exception:
            pass

    # ---- 1) mở browser với CDP (hoặc dùng fork đã mở qua cdp_backend) ----
    def _spawn_browser(self):
        if self.cdp_backend is not None:
            # Android: fork đã tự bật CDP; chỉ cần chờ http://127.0.0.1:9222
            threading.Thread(target=self._backend_loop, daemon=True).start()
            return True
        exe = self.chrome_path or find_browser()
        if not exe:
            self.log("Không tìm thấy Chrome/Edge/Chromium trên máy. Cài 1 trình duyệt Chromium rồi thử lại.", err=True)
            return False
        os.makedirs(self.profile_dir, exist_ok=True)
        args = [
            exe,
            "--remote-debugging-port=0",
            "--remote-debugging-address=127.0.0.1",
            "--remote-allow-origins=*",
            "--user-data-dir=" + self.profile_dir,
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-breakpad",
            "--no-crash-bubble",
            "--window-size=1000,650",
            "about:blank",
        ]
        try:
            self._browser_proc = subprocess.Popen(args, stdin=None, stdout=subprocess.DEVNULL,
                                                  stderr=subprocess.PIPE)
        except Exception as e:
            self.log("Lỗi mở browser: " + str(e), err=True)
            return False
        import sys as _s
        threading.Thread(target=self._read_stderr, daemon=True).start()
        return True

    def _read_stderr(self):
        p = self._browser_proc
        if not p or not p.stderr:
            return
        chunk = b""
        while not self._stopping:
            try:
                data = p.stderr.read(1024)
            except Exception:
                break
            if not data:
                break
            chunk += data
            m = re.search(rb"ws://127\.0\.0\.1:(\d+)/devtools/browser/(\S+)", chunk)
            if m and not self._cdp_ws:
                url = "ws://127.0.0.1:%s/devtools/browser/%s" % (m.group(1).decode(), m.group(2).decode())
                threading.Thread(target=self._cdp_main, args=(url,), daemon=True).start()
                chunk = b""

    # ---- 2) CDP client ----
    def _cdp_ws_send(self, msg):
        with self._send_lock:
            if self._cdp_ws and self._cdp_ws.connected:
                self._cdp_ws.send(json.dumps(msg))
                return True
        return False

    def _cdp_call(self, method, params=None, session=None, timeout=25):
        with self._cdp_lock:
            self._cdp_id += 1
            id_ = self._cdp_id
        msg = {"id": id_, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        ev = threading.Event()
        res = {}
        with self._cdp_lock:
            self._cdp_pending[id_] = (ev, res)
        if not self._cdp_ws_send(msg):
            with self._cdp_lock:
                self._cdp_pending.pop(id_, None)
            raise RuntimeError("CDP chưa sẵn sàng")
        if not ev.wait(timeout):
            with self._cdp_lock:
                self._cdp_pending.pop(id_, None)
            raise RuntimeError("CDP timeout: " + method)
        if "error" in res:
            raise RuntimeError(res["error"].get("message", str(res["error"])))
        return res.get("result", {})

    def _cdp_main(self, url):
        try:
            self._cdp_ws = websocket.create_connection(url, timeout=20)
        except Exception as e:
            self.log("Không nối được CDP: " + str(e), err=True)
            self._cdp_ws = None
            return
        self.log("Browser CDP sẵn sàng: " + url)
        try:
            while not self._stopping:
                self._cdp_ws.settimeout(0.2)
                try:
                    raw = self._cdp_ws.recv()
                except websocket.WebSocketTimeoutException:
                    raw = None
                except Exception:
                    break
                if raw:
                    try:
                        m = json.loads(raw)
                    except Exception:
                        continue
                    if m.get("id"):
                        with self._cdp_lock:
                            ent = self._cdp_pending.pop(m["id"], None)
                        if ent:
                            ev, res = ent
                            if "error" in m:
                                res["error"] = m["error"]
                            else:
                                res["result"] = m.get("result", {})
                            ev.set()
                # xử lý hàng đợi eval + yêu cầu mở tab
                self._cdp_do(take=4)
        finally:
            try:
                self._cdp_ws.close()
            except Exception:
                pass
            self._cdp_ws = None

    def _cdp_do(self, take=4):
        try:
            for _ in range(take):
                item = self._tab_requests.pop(0)
            # mở/di chuyển đến tab game
        except IndexError:
            pass
        done = 0
        while done < take:
            try:
                req = self._eval_queue.get_nowait()
            except queue.Empty:
                break
            done += 1
            self._handle_eval(req)
        try:
            while self._tab_requests:
                self._ensure_game_tab(self._tab_requests.pop(0))
        except Exception:
            pass

    def _ensure_game_tab(self, url):
        if not url:
            return
        try:
            host = self._host_of(url)
            if host:
                self._game_host = host
            targets = self._cdp_call("Target.getTargets").get("targetInfos", [])
            t = next((x for x in targets if x.get("type") == "page" and x.get("url") and host and self._host_of(x["url"]) == host), None)
            if not t:
                created = self._cdp_call("Target.createTarget", {"url": url})
                t = {"targetId": created["targetId"], "url": url}
                time.sleep(0.4)
            self._game_target = t["targetId"]
            att = self._cdp_call("Target.attachToTarget", {"targetId": self._game_target, "flatten": True})
            self._game_session = att["sessionId"]
            if not (t.get("url") or "").strip() or self._host_of(t.get("url") or "") != host:
                try:
                    self._cdp_call("Page.navigate", {"url": url}, session=self._game_session)
                except Exception:
                    pass
            self.log("Tab game sẵn sàng: " + host)
        except Exception as e:
            self.log("Lỗi mở tab game: " + str(e), err=True)

    def _host_of(self, url):
        try:
            from urllib.parse import urlparse
            return (urlparse(url).hostname or "").replace("www.", "")
        except Exception:
            return ""

    def _eval_game(self, expr):
        if not self._game_target:
            raise RuntimeError("Chưa có tab game")
        if not self._game_session:
            att = self._cdp_call("Target.attachToTarget", {"targetId": self._game_target, "flatten": True})
            self._game_session = att["sessionId"]
        res = self._cdp_call("Runtime.evaluate", {
            "expression": expr,
            "awaitPromise": True,
            "returnByValue": True,
            "userGesture": True,
        }, session=self._game_session)
        if res.get("exceptionDetails"):
            d = res["exceptionDetails"].get("exception", {}).get("description") or "lỗi"
            raise RuntimeError("JS: " + d[:300])
        return res.get("result", {}).get("value")

    def _handle_eval(self, req):
        try:
            if self.cdp_backend is not None:
                if not self._backend_ok:
                    raise RuntimeError("CDP fork chưa sẵn sàng")
                value = self.cdp_backend.eval(req["expr"])
            else:
                value = self._eval_game(req["expr"])
            self._server_send({"t": "res", "id": req["id"], "value": value})
        except Exception as e:
            self._server_send({"t": "res", "id": req["id"], "error": str(e)[:300]})

    def _backend_loop(self):
        """Android: chờ fork mở CDP 127.0.0.1:9222 rồi xử lý eval + mở tab game."""
        b = self.cdp_backend
        try:
            b.wait_ready(timeout=120)
            self._backend_ok = True
            self.log("Browser fork CDP sẵn sàng (127.0.0.1).")
        except Exception as e:
            self.log("Chưa bật được CDP của fork: " + str(e), err=True)
            return
        while not self._stopping:
            try:
                while self._tab_requests:
                    self._backend_ensure(self._tab_requests.pop(0))
            except Exception:
                pass
            try:
                req = self._eval_queue.get(timeout=0.3)
                self._handle_eval(req)
            except queue.Empty:
                continue

    def _backend_ensure(self, url):
        if not url:
            return
        try:
            self.cdp_backend.ensure_game_tab(url)
            self.log("Tab game sẵn sàng: " + self._host_of(url))
        except Exception as e:
            self.log("Lỗi mở tab game qua fork: " + str(e), err=True)

    # ---- 3) kết nối server ----
    def _server_send(self, msg):
        with self._send_lock:
            ws = getattr(self, "_server_ws", None)
            if ws and ws.connected:
                try:
                    ws.send(json.dumps(msg))
                    return True
                except Exception:
                    pass
        return False

    def _server_main(self):
        while not self._stopping:
            url = self._ws_url()
            try:
                self.log("Nối server: %s (mã %s)" % (self.server, self.code))
                ws = websocket.create_connection(url, timeout=25)
            except Exception as e:
                self.log("Lỗi nối server: " + str(e)[:120] + " — thử lại trong 5s", err=True)
                time.sleep(5)
                continue
            self._server_ws = ws
            try:
                ws.send(json.dumps({"t": "hello", "code": self.code, "v": 1, "node": sys.version.split()[0]}))
            except Exception:
                pass
            self.log("Đã gửi mã liên kết — chờ server xác nhận...")
            try:
                while not self._stopping:
                    try:
                        ws.settimeout(0.5)
                        raw = ws.recv()
                    except websocket.WebSocketTimeoutException:
                        raw = None
                    except Exception:
                        break
                    if raw:
                        try:
                            m = json.loads(raw)
                        except Exception:
                            continue
                        if not m.get("t"):
                            continue
                        if m["t"] == "ok":
                            self.log("Server xác nhận: uid=%s — mở game..." % (str(m.get("uid", ""))[:8]))
                            self._game_url = m.get("url") or ""
                            if self._game_url:
                                self._tab_requests.append(self._game_url)
                        elif m["t"] == "err":
                            self.log("Server từ chối: %s" % (m.get("message") or ""), err=True)
                            self.stop()
                            break
                        elif m["t"] == "ping":
                            self._server_send({"t": "pong", "ts": int(time.time() * 1000)})
                        elif m["t"] == "eval":
                            self._eval_queue.put({"id": m["id"], "expr": str(m.get("expr") or "")})
            finally:
                try:
                    ws.close()
                except Exception:
                    pass
            if not self._stopping:
                self.log("Mất kết nối server — thử lại trong 5s...")
                time.sleep(5)
        self._stop_browser()
        self._call_stopped()

    def _call_stopped(self):
        if not self._stopped_called and self.on_stopped:
            self._stopped_called = True
            try:
                self.on_stopped()
            except Exception:
                pass

    def _ws_url(self):
        s = str(self.server or "").strip().rstrip("/")
        scheme = "wss://" if s.startswith("https://") else "ws://"
        return scheme + s.replace("https://", "").replace("http://", "") + "/agent-ws"

    # ---- API ----
    def start(self, server, code, on_ready=None):
        self.server = server
        self.code = str(code or "").strip().upper()
        if not self.server or not self.code:
            self.log("Thiếu server/code — không bắt đầu.", err=True)
            return False
        if not self._spawn_browser():
            return False
        self._stopping = False
        self.running = True
        threading.Thread(target=self._server_main, daemon=True).start()
        if on_ready:
            threading.Timer(1.0, lambda: on_ready(self)).start()
        self.log("Agent đang chạy. Đóng cửa sổ game để dừng.")
        return True

    def stop(self):
        self._stopping = True
        self.running = False
        self._stop_browser()
        self._call_stopped()

    def _stop_browser(self):
        try:
            if self._browser_proc and self._browser_proc.poll() is None:
                self._browser_proc.terminate()
        except Exception:
            pass