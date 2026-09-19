# main.py — App KivyMD: đăng nhập/đăng ký (Firebase Auth như web) + kết nối tool server
#                       + (desktop) mở Chrome/Chromium CDP tại máy user để chơi mượt tuyệt đối.
#
# Chạy desktop:   pip install kivy kivymd python-socketio websocket-client requests
#                 python main.py
# Build APK:      xem README (buildozer — chạy trên Linux/WSL).

import os
import sys
import threading

from functools import partial

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp

try:
    from kivymd.app import MDApp
    from kivymd.uix.snackbar import Snackbar
except Exception:  # pragma: no cover
    from kivymd.app import MDApp  # thử lại
    Snackbar = None

import fb
import sio_client

IS_ANDROID = sys.platform == "linux" and "ANDROID" in os.environ.get("ANDROID_ARGUMENT", "")

if IS_ANDROID:
    from android.storage import app_storage_dir
    BASE_DIR = app_storage_dir() or os.path.expanduser("~")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SESSION_PATH = os.path.join(BASE_DIR, "session.json")
CFG_PATH = os.path.join(BASE_DIR, "config.txt")

# Chromium Fork APK (bạn tự build theo fork/build.sh) — UI riêng, "1 tab riêng trên đth".
FORK_PACKAGE = "org.lmt1102011.chromefork"
FORK_ACTIVITY = "org.chromium.chrome.browser.ChromeLauncherActivity"

KV = os.path.join(BASE_DIR, "ui.kv")
if not os.path.exists(KV):
    KV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui.kv")


class ToolApp(MDApp):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.sio = sio_client.SioClient(
            on_status=self._on_snapshot,
            on_panel=self._on_panel,
            on_user_status=self._on_user_status,
            on_log=self._log_ui,
            on_connected=lambda: self._log_ui("Socket đã kết nối."),
            on_disconnected=lambda r: self._log_ui("Mất kết nối socket: %s" % r, err=True),
        )
        self.agent = None
        self.agent_code = None
        self.agent_running = False
        self.is_agent_mode = False
        self.picks = -1
        self.role = ""
        self._tick_handle = None
        self._logs = []

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Indigo"
        self.theme_cls.accent_palette = "Amber"
        return Builder.load_file(KV)

    def on_start(self):
        fb.set_session_path(SESSION_PATH)
        fb.load_session()
        if fb.logged_in():
            self.goto("home")
            self.recheck()
        else:
            self.goto("login")

    # ────────────────── điều hướng ──────────────────
    def goto(self, name, skip_auth=False):
        sm = self.root
        if not hasattr(sm, "current"):  # root có thể không phải ScreenManager
            try:
                sm = self.root.ids.sm
            except Exception:
                sm = self.root.ids["sm"]
        if name == "home" and skip_auth:
            self._set_user(None)
        sm.current = name

    # ────────────────── đăng nhập / đăng ký ──────────────────
    def _run(self, fn, ok, err):
        def _w():
            try:
                v = fn()
                Clock.schedule_once(lambda dt: ok(v))
            except Exception as e:
                Clock.schedule_once(lambda dt: err(e))
        threading.Thread(target=_w, daemon=True).start()

    def do_login(self):
        uname = self.root.ids.l_uname.text.strip()
        upass = self.root.ids.l_pass.text
        self._log_ui("Đang đăng nhập...")
        self._run(
            lambda: fb.login(uname, upass),
            lambda v: self._login_ok(v),
            lambda e: self._set_status("login_status", "Lỗi: " + str(e), err=True),
        )

    def _login_ok(self, res):
        self._set_user(fb._session)
        self._log_ui("Đã đăng nhập: " + str(res["data"].get("displayName", res["uid"])))
        self.goto("home")
        threading.Thread(target=self._connect_socket, daemon=True).start()

    def do_register(self):
        uname = self.root.ids.r_uname.text.strip()
        upass = self.root.ids.r_pass.text
        dname = self.root.ids.r_name.text.strip()
        self._set_status("reg_status", "Đang đăng ký...")
        self._run(
            lambda: fb.register(uname, upass, dname),
            lambda v: self._reg_ok(v, uname, upass),
            lambda e: self._set_status("reg_status", "Lỗi: " + str(e), err=True),
        )

    def _reg_ok(self, res, uname, upass):
        self._set_status("reg_status", "Đăng ký thành công — tự động đăng nhập", err=False)
        Clock.schedule_once(lambda dt: self._run(
            lambda: fb.login(uname, upass),
            lambda v: self._login_ok(v),
            lambda e: self._set_status("login_status", "Đã tạo tài khoản, đăng nhập lại.", err=True),
        ), 0.6)

    def do_logout(self):
        threading.Thread(target=self._shutdown, daemon=True).start()
        self.goto("login")

    def _shutdown(self):
        if self._tick_handle is not None:
            try:
                Clock.unschedule(self._tick_handle)
            except Exception:
                pass
            self._tick_handle = None
        try:
            self.sio.disconnect()
        except Exception:
            pass
        try:
            if self.agent:
                self.agent.stop()
        except Exception:
            pass
        fb.logout()

    # ────────────────── hiển thị ──────────────────
    def _set_user(self, sess):
        d = sess or {}
        name = d.get("displayName") or d.get("username") or "Khách"
        self.root.ids.h_user.text = "Xin chào, " + name
        self.root.ids.a_user.text = name
        self.root.ids.a_uid.text = (d.get("uid") or "").strip()
        try:
            data = fb.get_user_data(d.get("uid"), d.get("idToken")) if d.get("uid") else None
            self.root.ids.a_picks.text = "Lượt đoán: " + str(fb.picks(data))
        except Exception:
            self.root.ids.a_picks.text = "Lượt đoán: --"
        self.refresh_picks()

    def refresh_picks(self):
        """Đọc số lượt đoán còn lại từ RTDB (giống tool web) để quản lý lượt cho từng user."""
        sess = fb._session or {}
        uid = sess.get("uid")
        if not uid:
            self.picks, self.role = -1, ""
            return
        try:
            data = fb.get_user_data(uid, sess.get("idToken"))
            self.picks = int(fb.picks(data))
            self.role = (data or {}).get("role") or ""
        except Exception as e:
            self._log_ui("Không đọc được số lượt: " + str(e), err=True)
            return
        def upd(dt):
            try:
                self.root.ids.h_picks.text = "Lượt đoán: %s" % ("∞" if self.role == "admin" else self.picks)
                g = self.root.ids.h_gate
                if self._check_gate():
                    g.text = "HẾT LƯỢT ĐOÁN — nạp thêm tại trang web để tiếp tục."
                else:
                    g.text = ""
            except Exception:
                pass
        Clock.schedule_once(upd)

    def _check_gate(self):
        return self.picks <= 0 and self.role != "admin"

    def _tick_picks(self, dt=None):
        threading.Thread(target=self.refresh_picks, daemon=True).start()

    def _gate_or_refresh(self):
        """Trước khi chạy: gate số lượt giống tool.web. Nếu còn lượt, đủ avatar."""

    def _picks_ok(self):
        if self._check_gate():
            self._log_ui("Hết lượt đoán — nạp thêm tại trang web rồi thử lại.", err=True)
            self.refresh_picks()
            return False
        return True

    def _agent_stopped(self):
        """Server từ chối (hết lượt) hoặc mất kết nối → reset UI + đọc lại lượt."""
        self.agent_running = False
        Clock.schedule_once(lambda dt: self._log_ui("Agent đã dừng — kiểm tra số lượt đoán."))
        threading.Thread(target=self.refresh_picks, daemon=True).start()

    def _set_status(self, id_, msg, err=False):
        lbl = self.root.ids[id_]
        lbl.text = str(msg)
        lbl.theme_text_color = "Error" if err else "Secondary"

    def _log_ui(self, msg, err=False):
        self._logs.append((str(msg), err))
        self._logs = self._logs[-60:]
        text = "\n".join("⚠ " + m if e else m for m, e in self._logs)
        Clock.schedule_once(partial(self._apply_log, text))

    def _apply_log(self, text, dt):
        try:
            self.root.ids.h_log.text = text
        except Exception:
            pass

    # ────────────────── socket server ──────────────────
    def _connect_socket(self, attempts=0):
        try:
            tok = fb.refresh_id_token()
            srv = sio_client.SioClient.discover_server(CFG_PATH)
            if not srv:
                self._log_ui("Không tìm thấy server (server-url.json).", err=True)
                return
            self._log_ui("Server: " + srv)
            self.sio.connect(srv, tok)
        except Exception as e:
            if attempts < 2:
                threading.Timer(5, lambda: self._connect_socket(attempts + 1)).start()
            self._log_ui("Lỗi kết nối server: " + str(e), err=True)

    def _on_snapshot(self, d):
        snap = d or {}
        st = snap.get("status") or {}
        self._log_ui("Đã kết nối — %s ván" % (len(snap.get("history") or [])))
        self._update_pred(snap.get("prediction"), snap.get("lastResult"))

    def _on_panel(self, p):
        p = p or {}
        if self.is_agent_mode and p.get("pick"):
            self._update_pred(p, p.get("lastResult"))

    def _on_user_status(self, d):
        d = d or {}
        self.is_agent_mode = bool(d.get("agent"))
        Clock.schedule_once(partial(self._apply_user_status, d))

    def _apply_user_status(self, d, dt):
        try:
            self.root.ids.h_agent.text = (d.get("msg") or "")[:80]
        except Exception:
            pass

    def _update_pred(self, p, last=None):
        p = p or {}
        def upd(dt):
            try:
                if p.get("pick"):
                    pk = str(p["pick"]).upper()
                    t = ("TÀI" if pk == "T" else "XỈU")
                    self.root.ids.h_pick.text = t
                    self.root.ids.h_pct.text = "T %.0f%% · X %.0f%%" % (
                        float(p.get("pT") or 50), float(p.get("pX") or 50))
                    c = p.get("confidence", p.get("conf"))
                    self.root.ids.h_conf.text = "Độ tin cậy %.0f%%" % float(c) if c is not None else "chờ dữ liệu"
                hist = p.get("hist") or p.get("history") or []
                short = "".join(str(x)[0] if str(x).lower() in ("t", "x") else ("T" if str(x)[0].lower() == "t" else "X") for x in hist[-30:])
                self.root.ids.h_hist.text = short or ""
            except Exception:
                pass
        Clock.schedule_once(upd)

    def recheck(self):
        self._set_user(fb._session)
        threading.Thread(target=self._connect_socket, daemon=True).start()

    # ────────────────── agent Chrome/CDP ──────────────────
    def start_agent(self):
        if self.agent_running:
            self._log_ui("Agent đang chạy — dừng trước khi khởi động lại.", err=True)
            return
        if IS_ANDROID:
            self._log_ui("Trên Android không mở được Chrome CDP. Dùng máy tính cho chức năng này.", err=True)
            if self.sio.connected and not self.agent_code:
                self._get_code()
            return

        def on_code(r):
            code = (r or {}).get("code")
            if not code:
                self._log_ui("Chưa lấy được mã liên kết.", err=True)
                return
            self.agent_code = code
            srv = self.sio.server_url or "http://localhost:8787"
            self._log_ui("Mã liên kết: %s — mở Chrome và nối server..." % code)
            try:
                from agent import Agent
                self.agent = Agent(on_log=self._log_ui, on_stopped=self._agent_stopped)
                ok = self.agent.start(server=srv, code=code)
                self.agent_running = ok
            except Exception as e:
                self._log_ui("Lỗi agent: " + str(e), err=True)

        if self.is_agent_mode:
            self._log_ui("Bạn đang ở chế độ agent — ngắt để quay lại máy chủ.", err=True)
            return
        self.sio.agent_pair(on_code)

    def _get_code(self):
        def on_code(r):
            code = (r or {}).get("code")
            self.agent_code = code
            if code:
                self._log_ui("Mã liên kết: %s — chạy agent_chrome.js trên máy tính." % code)
        self.sio.agent_pair(on_code)

    # ────────────────── START BROWSER — Chromium Fork trên Android ──────────────────
    def start_fork(self):
        """Mở Chromium Fork (APK tự build) thành 1 tab riêng trên điện thoại,
        rồi nối CDP 127.0.0.1:9222 làm agent cho server.
        Số lượt vẫn do server quản lý như web."""
        if self.agent_running:
            self._log_ui("Agent đang chạy — dừng trước khi khởi động lại.", err=True)
            return
        if not self._picks_ok():
            return
        if not IS_ANDROID:
            self._log_ui("START BROWSER dành cho Android. Trên máy tính dùng nút CHROME MÁY BẠN.", err=True)
            return
        if not self.sio.connected:
            self._log_ui("Chưa kết nối server. Đang nối lại...", err=True)
            threading.Thread(target=self._connect_socket, daemon=True).start()
            return
        try:
            import hcdp
        except Exception as e:
            self._log_ui("Không tải được hcdp: " + str(e), err=True)
            return
        srv = self.sio.server_url or "http://localhost:8787"

        def on_code(r):
            code = (r or {}).get("code")
            if not code:
                self._log_ui("Chưa lấy được mã liên kết.", err=True)
                return
            self.agent_code = code
            try:
                # 1) mở fork thành app riêng (1 tab nền) trên điện thoại
                hcdp.start_browser(url="", package=FORK_PACKAGE, activity=FORK_ACTIVITY)
                self._log_ui("Đã mở Chromium Fork — kết nối CDP 127.0.0.1:9222...")
                # 2) agent dùng chính fork đó (không spawn browser)
                from agent import Agent
                bridge = hcdp.ForkCdpBridge(on_log=self._log_ui)
                self.agent = Agent(on_log=self._log_ui, cdp_backend=bridge, on_stopped=self._agent_stopped)
                ok = self.agent.start(server=srv, code=code)
                self.agent_running = ok
                if ok:
                    self._log_ui("Agent fork đang chạy — vào game đăng nhập trên tab vừa mở.")
                    if self._tick_handle is None:
                        self._tick_handle = Clock.schedule_interval(self._tick_picks, 30)
            except Exception as e:
                self._log_ui("Lỗi start fork: " + str(e), err=True)

        if self.is_agent_mode:
            self._log_ui("Đang ở chế độ agent — ngắt trước khi khởi động lại.", err=True)
            return
        self.sio.agent_pair(on_code)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--find-browser":
            from agent import find_browser
            print("Browser: " + str(find_browser(sys.argv[2] if len(sys.argv) > 2 else None)))
            sys.exit(0)
    ToolApp().run()