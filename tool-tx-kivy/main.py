# main.py — App KivyMD: đăng nhập/đăng ký (Firebase Auth REST) + kết nối tool server
#                       + agent trình duyệt (Chromium Fork / Chrome CDP).
#
# Kiến trúc theo mẫu module:
#   ToolApp(MDApp).build()  →  MDScreenManager + LoginScreen/HomeScreen/BrowserScreen/SettingsScreen
#   core/auth.py            →  AuthManager (Firebase)
#   core/theme.py, config.py→  màu brand + nền gradient
#   widgets/bottomnav.py    →  thanh điều hướng dưới
#
# Chạy desktop:   python main.py
# Build APK:      xem README (buildozer — chạy trên Linux/WSL).

import os
import sys
import threading

from functools import partial

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle
from kivy.uix.screenmanager import FadeTransition
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.screenmanager import MDScreenManager

import fb
import sio_client
from core import config as C
from core.auth import AuthManager
from core.theme import make_bg
from screens.login import LoginScreen
from screens.home import HomeScreen
from screens.browser import BrowserScreen
from screens.settings import SettingsScreen
from widgets.bottomnav import BottomNav


class ToolApp(MDApp):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.auth = AuthManager()
        self.sio = sio_client.SioClient(
            on_status=self._on_snapshot,
            on_panel=self._on_panel,
            on_user_status=self._on_user_status,
            on_log=self._log_ui,
            on_connected=lambda: (self._log_ui("Socket đã kết nối."),
                                  self._set_conn("ONLINE", ok=True)),
            on_disconnected=lambda r: (self._log_ui("Mất kết nối socket: %s" % r, err=True),
                                       self._set_conn("OFFLINE", warn=True)),
        )
        self.agent = None
        self.agent_code = None
        self.agent_running = False
        self.is_agent_mode = False
        self.picks = -1
        self.role = ""
        self._tick_handle = None
        self._logs = []
        self.admin = None
        self.admin_users = {}
        self._admin_tick = None

    # ────────────────── build ──────────────────
    def build(self):
        _log_step("build")
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Amber"
        self.theme_cls.accent_palette = "Amber"
        self.theme_cls.primary_hue = "700"
        Window.clearcolor = (0.10, 0.14, 0.22, 1)

        self.bg_texture = make_bg()
        _log_step("build-bg")

        self.root_box = MDBoxLayout(orientation="vertical", md_bg_color=(0, 0, 0, 0))
        self._apply_bg(self.root_box)

        self.sm = MDScreenManager(transition=FadeTransition(duration=0.22))
        self.login = LoginScreen(name="login")
        _log_step("build-login")
        self.home = HomeScreen(name="home")
        _log_step("build-home")
        self.browser = BrowserScreen(name="browser")
        _log_step("build-browser")
        self.settings = SettingsScreen(name="settings")
        _log_step("build-settings")
        for s in (self.login, self.home, self.browser, self.settings):
            self.sm.add_widget(s)
        self.root_box.add_widget(self.sm)

        self.nav = BottomNav(on_select=self.goto, height=dp(62))
        self.root_box.add_widget(self.nav)

        self.goto("login")
        _log_step("build-done")
        return self.root_box

    def _apply_bg(self, w):
        """Nền gradient + lớp nền đậm dự phòng (tránh ô trắng nếu thiếu texture)."""
        with w.canvas.before:
            self._bg_solid = Color(0.10, 0.14, 0.22, 1)
            self._bg_solid_r = Rectangle()
            self._bg_tex = Color(1, 1, 1, 1)
            self._bg_tex_r = Rectangle(texture=self.bg_texture)
        w.bind(pos=self._bg_draw, size=self._bg_draw)
        self._bg_draw(w)

    def _bg_draw(self, inst, *a):
        self._bg_solid_r.pos = inst.pos
        self._bg_solid_r.size = inst.size
        self._bg_tex_r.pos = inst.pos
        self._bg_tex_r.size = inst.size

    def on_start(self):
        super().on_start()
        _log_step("on_start")
        Window.clearcolor = (0.10, 0.14, 0.22, 1)
        self.auth.set_session_path(C.SESSION_PATH)
        if self.auth.logged_in():
            self.goto("home")
            self.recheck()
        else:
            self.goto("login")

    # ────────────────── điều hướng ──────────────────
    def goto(self, name):
        try:
            self.sm.current = name
        except Exception:
            return
        show = name != "login"
        self.nav.show(show)
        self.nav.set_active(name if show else "")
        if name == "admin":
            threading.Thread(
                target=lambda: Clock.schedule_once(lambda dt: self.admin_refresh()),
                daemon=True,
            ).start()

    # ────────────────── admin (role=admin) ──────────────────
    def ensure_admin(self):
        """Khi đăng nhập admin: thêm màn Quản trị + tab nav, bật auto-refresh."""
        if self.role != "admin":
            return
        if getattr(self, "admin", None) is not None:
            return
        from screens.admin import AdminScreen
        self.admin = AdminScreen(name="admin")
        try:
            self.sm.add_widget(self.admin)
            self.nav.set_admin(True)
        except Exception:
            pass
        self.admin_users = {}
        self.admin_refresh()
        if getattr(self, "_admin_tick", None) is None:
            self._admin_tick = Clock.schedule_interval(
                lambda dt: threading.Thread(target=self.admin_refresh, daemon=True).start(),
                20,
            )

    def discard_admin(self):
        """Khi thoát phiên admin: gỡ màn + tab + auto-refresh."""
        if getattr(self, "_admin_tick", None) is not None:
            try:
                Clock.unschedule(self._admin_tick)
            except Exception:
                pass
            self._admin_tick = None
        try:
            self.nav.set_admin(False)
        except Exception:
            pass
        if getattr(self, "admin", None) is not None:
            try:
                self.sm.remove_widget(self.admin)
            except Exception:
                pass
            self.admin = None

    def admin_refresh(self):
        try:
            users = self.auth.list_users()
            rate = self.auth.get_rate()
            self.admin_users = users or {}
            if getattr(self, "admin", None) is not None:
                Clock.schedule_once(lambda dt: self.admin.load(users or {}, rate))
        except Exception as e:
            self._log_ui("Không đọc được dữ liệu quản trị: " + str(e), err=True)

    # ────────────────── đăng nhập / đăng ký ──────────────────
    def _run(self, fn, ok, err):
        def _w():
            try:
                v = fn()
                Clock.schedule_once(lambda dt: ok(v))
            except Exception as e:
                Clock.schedule_once(lambda dt: err(e))
        threading.Thread(target=_w, daemon=True).start()

    def do_login(self, user, password):
        self._run(
            lambda: self.auth.login(user, password),
            lambda v: self._login_ok(v),
            lambda e: self.login.set_status("Lỗi: " + str(e), err=True),
        )

    def _login_ok(self, res):
        self._set_user(self.auth.current())
        self._log_ui("Đã đăng nhập: " + str(res["data"].get("displayName", res["uid"])))
        self.goto("home")
        threading.Thread(target=self._connect_socket, daemon=True).start()

    def do_register(self, user, password, name):
        self._run(
            lambda: self.auth.register(user, password, name),
            lambda v: self._reg_ok(v, user, password),
            lambda e: self.login.set_status("Lỗi: " + str(e), err=True),
        )

    def _reg_ok(self, res, user, password):
        self.login.set_status("Đăng ký thành công — tự động đăng nhập")
        Clock.schedule_once(lambda dt: self._run(
            lambda: self.auth.login(user, password),
            lambda v: self._login_ok(v),
            lambda e: self.login.set_status("Đã tạo tài khoản, đăng nhập lại.", err=True),
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
        self.auth.logout()
        self.discard_admin()

    # ────────────────── hiển thị ──────────────────
    def _set_user(self, sess):
        d = sess or {}
        name = d.get("displayName") or d.get("username") or "Khách"
        letter = (name or "K")[:1].upper()
        self.home.greet(name)
        self.settings.profile(name, letter, d.get("uid"), d.get("role"), "--")
        self.refresh_picks()

    def refresh_picks(self):
        """Đọc số lượt đoán còn lại từ RTDB (giống tool web) để quản lý lượt cho từng user."""
        sess = self.auth.current()
        uid = sess.get("uid")
        if not uid:
            self.picks, self.role = -1, ""
            return
        try:
            data = self.auth.user_data()
            self.picks = int(fb.picks(data))
            self.role = (data or {}).get("role") or ""
        except Exception as e:
            self._log_ui("Không đọc được số lượt: " + str(e), err=True)
            return
        Clock.schedule_once(lambda dt: self.ensure_admin())

        def upd(dt):
            try:
                if self.role == "admin":
                    txt = "∞"
                    warn = False
                else:
                    txt = str(self.picks)
                    warn = self._check_gate()
                self.home.picks_text("Lượt: " + txt, warn=warn)
                self.settings.picks_text(txt)
                if self._check_gate():
                    self.home.gate("BẠN ĐÃ HẾT LƯỢT ĐOÁN — nạp thêm tại trang web để tiếp tục.")
                else:
                    self.home.gate(None)
            except Exception:
                pass
        Clock.schedule_once(upd)

    def _check_gate(self):
        return self.picks <= 0 and self.role != "admin"

    def _tick_picks(self, dt=None):
        threading.Thread(target=self.refresh_picks, daemon=True).start()

    def _picks_ok(self):
        if self._check_gate():
            self._log_ui("Hết lượt đoán — nạp thêm tại trang web rồi thử lại.", err=True)
            self.refresh_picks()
            return False
        return True

    def _agent_stopped(self):
        """Server từ chối (hết lượt) hoặc mất kết nối → reset UI + đọc lại lượt."""
        self.agent_running = False
        Clock.schedule_once(
            lambda dt: (self._log_ui("Agent đã dừng — kiểm tra số lượt đoán."),
                        self.browser.set_agent("Agent đã dừng.")),
        )
        threading.Thread(target=self.refresh_picks, daemon=True).start()

    def _log_ui(self, msg, err=False):
        self._logs.append((str(msg), err))
        self._logs = self._logs[-80:]
        text = "\n".join("⚠ " + m if e else m for m, e in self._logs)
        Clock.schedule_once(partial(self._apply_log, text))

    def _apply_log(self, text, dt):
        try:
            self.settings.set_log(text)
        except Exception:
            pass

    # ────────────────── socket server ──────────────────
    def _connect_socket(self, attempts=0):
        try:
            tok = self.auth.refresh_id_token()
            srv = sio_client.SioClient.discover_server(C.CFG_PATH)
            if not srv:
                self._log_ui("Không tìm thấy server (server-url.json).", err=True)
                return
            self._log_ui("Server: " + srv)
            self.sio.connect(srv, tok)
        except Exception as e:
            if attempts < 2:
                threading.Timer(5, lambda: self._connect_socket(attempts + 1)).start()
            self._log_ui("Lỗi kết nối server: " + str(e), err=True)
            self._set_conn("OFFLINE", warn=True)

    def _on_snapshot(self, d):
        snap = d or {}
        self._set_conn("ONLINE", ok=True)
        self._log_ui("Đã kết nối — %s ván" % (len((snap.get("history") or []))))
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
            msg = (d.get("msg") or "")[:60]
            if self.is_agent_mode:
                self._set_conn("AGENT", ok=True)
                self.home.agent(msg, col=(0.35, 0.85, 0.55, 1))
                self.browser.set_agent("Đang chạy agent: " + msg, col=(0.35, 0.85, 0.55, 1))
            else:
                self._set_conn("ONLINE")
                self.home.agent("")
                self.browser.set_agent("Chưa có agent nào chạy.")
        except Exception:
            pass

    def _update_pred(self, p, last=None):
        def upd(dt):
            try:
                self.home.prediction(p)
            except Exception:
                pass
        Clock.schedule_once(upd)

    def _set_conn(self, text, ok=False, warn=False):
        col = (0.35, 0.85, 0.55, 1) if ok else ((0.97, 0.62, 0.24, 1) if warn else (0.60, 0.66, 0.78, 1))
        try:
            self.home.conn(text, col)
        except Exception:
            pass

    def recheck(self):
        self._set_user(self.auth.current())
        threading.Thread(target=self._connect_socket, daemon=True).start()

    # ────────────────── agent Chrome/CDP (máy tính) ──────────────────
    def start_agent(self):
        if self.agent_running:
            self._log_ui("Agent đang chạy — dừng trước khi khởi động lại.", err=True)
            return
        if C.IS_ANDROID:
            self._log_ui("Trên Android không mở được Chrome CDP. Dùng START BROWSER.", err=True)
            return
        if self.is_agent_mode:
            self._log_ui("Bạn đang ở chế độ agent — ngắt để quay lại máy chủ.", err=True)
            return

        def on_code(r):
            code = (r or {}).get("code")
            if not code:
                self._log_ui("Chưa lấy được mã liên kết.", err=True)
                return
            self.agent_code = code
            self.browser.set_code(code)
            srv = self.sio.server_url or "http://localhost:8787"
            self._log_ui("Mã liên kết: %s — mở Chrome và nối server..." % code)
            self.browser.set_status("Đang mở Chrome và nối server...", col=(0.97, 0.62, 0.24, 1))
            try:
                from agent import Agent
                self.agent = Agent(on_log=self._log_ui, on_stopped=self._agent_stopped)
                ok = self.agent.start(server=srv, code=code)
                self.agent_running = ok
                self.browser.set_agent("Agent Chrome đang chạy." if ok else "Khởi động agent thất bại.",
                                   col=(0.35, 0.85, 0.55, 1) if ok else (0.96, 0.42, 0.46, 1))
            except Exception as e:
                self._log_ui("Lỗi agent: " + str(e), err=True)
                self.browser.set_status("Lỗi agent: " + str(e), col=(0.96, 0.42, 0.46, 1))

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
        if not C.IS_ANDROID:
            self._log_ui("START BROWSER dành cho Android. Trên máy tính dùng CHROME MÁY BẠN.", err=True)
            return
        if not self.sio.connected:
            self._log_ui("Chưa kết nối server. Đang nối lại...", err=True)
            threading.Thread(target=self._connect_socket, daemon=True).start()
            return
        if self.is_agent_mode:
            self._log_ui("Đang ở chế độ agent — ngắt trước khi khởi động lại.", err=True)
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
            self.browser.set_code(code)
            try:
                hcdp.start_browser(url="", package=C.FORK_PACKAGE, activity=C.FORK_ACTIVITY)
                self._log_ui("Đã mở Chromium Fork — kết nối CDP 127.0.0.1:9222...")
                self.browser.set_status("Đã mở Chromium Fork — kết nối CDP...",
                                    col=(0.97, 0.62, 0.24, 1))
                from agent import Agent
                bridge = hcdp.ForkCdpBridge(on_log=self._log_ui)
                self.agent = Agent(on_log=self._log_ui, cdp_backend=bridge,
                                   on_stopped=self._agent_stopped)
                ok = self.agent.start(server=srv, code=code)
                self.agent_running = ok
                if ok:
                    self._log_ui("Agent fork đang chạy — vào game đăng nhập trên tab vừa mở.")
                    self.browser.set_agent("Agent fork đang chạy trên điện thoại.",
                                       col=(0.35, 0.85, 0.55, 1))
                    if self._tick_handle is None:
                        self._tick_handle = Clock.schedule_interval(self._tick_picks, 30)
                else:
                    self.browser.set_agent("Khởi động agent fork thất bại.",
                                       col=(0.96, 0.42, 0.46, 1))
            except Exception as e:
                self._log_ui("Lỗi start fork: " + str(e), err=True)
                self.browser.set_status("Lỗi start fork: " + str(e), col=(0.96, 0.42, 0.46, 1))

        self.sio.agent_pair(on_code)


CRASH_PATH = os.path.join(C.BASE_DIR, "crash.log")


def _last_step():
    try:
        with open(CRASH_PATH, encoding="utf-8") as f:
            return (f.read() or "").strip()[:300]
    except Exception:
        return "(chưa có)"


def _log_step(step):
    """Ghi lại BƯỚC khởi động hiện tại (ghi đè) — nếu app chết giữa chừng,
    lần mở sau sẽ đọc được nơi app dừng."""
    try:
        os.makedirs(C.BASE_DIR, exist_ok=True)
        with open(CRASH_PATH, "w", encoding="utf-8") as f:
            f.write("STEP " + step)
    except Exception:
        pass


def _write_crash(tb):
    try:
        with open(CRASH_PATH, "a", encoding="utf-8") as f:
            f.write("\n" + tb + "\n")
    except Exception:
        pass


def _show_error(tb, prev=None):
    """Hiện traceback trên màn hình xám đen để chụp ảnh gửi lại."""
    from kivy.app import App
    from kivy.uix.label import Label
    from kivy.uix.scrollview import ScrollView

    head = ""
    if prev:
        head = "LẦN CHẠY TRƯỚC DỪNG TẠI: %s\n\n" % prev

    class ErrApp(App):
        title = "TOOLTX — lỗi khởi động"

        def build(self):
            sv = ScrollView()
            l = Label(text=head + tb, font_size="11sp", halign="left", valign="top",
                      size_hint_y=None, padding=(10, 10), color=(1, 1, 1, 1))
            l.bind(width=lambda inst, w: setattr(inst, "text_size", (w * 0.98, None)))
            sv.add_widget(l)
            return sv

    ErrApp().run()


def _thread_exc(args):
    import traceback
    try:
        tb = "".join(traceback.format_exception(
            args.exc_type, args.exc_value, args.exc_traceback))
        _write_crash("[thread] " + tb)
    except Exception:
        pass


def _boot():
    prev = _last_step()
    if prev and "STEP app-exited" not in prev:
        _show_error("", prev=prev)
        try:
            os.remove(CRASH_PATH)
        except Exception:
            pass
        return
    _log_step("boot")
    try:
        app = ToolApp()
        _log_step("app-created")
        app.run()
    except Exception:
        import traceback
        tb = traceback.format_exc()
        _write_crash(tb)
        try:
            _show_error(tb, prev=_last_step())
        except Exception:
            pass
    _log_step("app-exited")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--find-browser":
            from agent import find_browser
            print("Browser: " + str(find_browser(sys.argv[2] if len(sys.argv) > 2 else None)))
            sys.exit(0)
    threading.excepthook = _thread_exc
    _boot()