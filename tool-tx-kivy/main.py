# main.py — App KivyMD restyle M3 Expressive: Sign In/Sign Up/Home/Top Up/Tool/Settings.
# QUAN TRỌNG (bug Android đã bắt được):
#   Import kivymd/kivy.core.window/... ở module-top là chết native lặng lẽ.
#   Toàn bộ import nặng phải nằm TRONG build()/ladder sau frame đầu.

import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CRASH_PATH = os.path.join(APP_DIR, "crash.log")
GATE_PATH = os.path.join(APP_DIR, "boot_state")
_ON_ANDROID = bool(os.environ.get("ANDROID_ARGUMENT"))

import faulthandler  # noqa: E402
try:
    _FAULT_FH = open(os.path.join(APP_DIR, "fault.log"), "a")
    faulthandler.enable(_FAULT_FH, all_threads=True)
except Exception:
    pass


def _toast(msg):
    """Popup Android nhỏ — kênh chẩn đoán không phụ thuộc ghi file/kivy."""
    if not _ON_ANDROID:
        return
    try:
        from jnius import autoclass
        A = autoclass("org.kivy.android.PythonActivity")
        Toast = autoclass("android.widget.Toast")
        Toast.makeText(A.mActivity, str(msg)[:220], 0).show()
    except Exception:
        pass


def _log_step(step):
    try:
        with open(CRASH_PATH, "a", encoding="utf-8") as f:
            f.write("\nSTEP " + step)
    except Exception:
        pass
    try:
        print("STEP " + step, flush=True)
    except Exception:
        pass


def _mark(step):
    _log_step(step)
    _toast("T:" + step)


def _last_step():
    try:
        with open(CRASH_PATH, encoding="utf-8") as f:
            lines = [ln.strip() for ln in f.read().splitlines() if ln.strip()]
            return (lines[-1] if lines else "")[:300]
    except Exception:
        return ""


def _gate_read():
    try:
        with open(GATE_PATH, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _gate_write(v):
    try:
        with open(GATE_PATH, "w", encoding="utf-8") as f:
            f.write(v)
    except Exception:
        pass


# BẮT prev TRƯỚC khi ghi marker lần này.
_PREV_STEP = _last_step()

_mark("main-start")

import threading  # noqa: E402
from functools import partial  # noqa: E402
import traceback  # noqa: E402

# ── CHỈ import nhóm ĐÃ CHỨNG MINH chạy ở module-top.
import kivy  # noqa: E402
from kivy.app import App  # noqa: E402
from kivy.uix.label import Label  # noqa: E402
from kivy.uix.scrollview import ScrollView  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.properties import ObjectProperty  # noqa: E402
_mark("base-ok")


class ToolApp(App):
    theme_cls = ObjectProperty(None)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.theme_cls = None
        self.auth = None
        self.sio = None
        self.agent = None
        self.agent_code = None
        self.agent_running = False
        self.is_agent_mode = False
        self.picks = -1
        self.role = ""
        self._tick_handle = None
        self._logs = []
        self._last_log = ""
        self.admin = None
        self.admin_users = {}
        self._admin_tick = None
        self._stack = []
        self._dark = None
        self._prefs = {}

    # ────────────────── build: CHỈ nhóm kivy đã chứng minh ──────────────────
    def build(self):
        _mark("build")
        sv = ScrollView(do_scroll_x=False, do_scroll_y=False)
        lbl = Label(text="TOOLTX\nLoading app...", font_size="13sp", halign="left",
                    valign="top", size_hint_y=None, padding=(14, 14), color=(1, 1, 1, 1))
        lbl.bind(width=lambda i, w: setattr(i, "text_size", (w * 0.97, None)))
        sv.add_widget(lbl)
        self._lines = ["TOOLTX", "Loading app...", ""]
        self._loading = lbl
        return sv

    def _say(self, text, err=False):
        self._lines.append(text)
        self._lines = self._lines[-40:]
        self._loading.text = "\n".join(self._lines)
        self._loading.color = (1, 0.5, 0.5, 1) if err else (1, 1, 1, 1)

    def on_start(self):
        try:
            super().on_start()
        except Exception:
            pass
        _mark("on_start")
        self._say("Đang tải dữ liệu...")
        self._ladder = [
            ("import nang",       self._st_imports),
            ("theme+window",      self._st_theme),
            ("services fb/sio",   self._st_services),
            ("nen gradient",      self._st_bg),
            ("6 man hinh",        self._st_screens),
            ("nav+load UI",       self._st_finish),
            ("DONE",              None),
        ]
        Clock.schedule_once(self._next, 0.1)

    def _next(self, *fdeps):
        while self._ladder:
            name, fn = self._ladder.pop(0)
            if fn is None:
                _mark("all-ok")
                try:
                    self._loading.text = "TOOLTX\nSẵn sàng!"
                except Exception:
                    pass
                return
            _mark(name)
            try:
                fn()
                _mark(name + "=ok")
            except BaseException as e:
                _mark(name + "=fail")
                self._say("LỖI KHỞI ĐỘNG\n" + name + " :: " + repr(e)[:160], err=True)
                tb = traceback.format_exc().splitlines()
                for ln in tb[-8:]:
                    self._say("     " + ln[:120], err=True)
                try:
                    with open(CRASH_PATH, "a", encoding="utf-8") as f:
                        f.write("\n### FAIL AT " + name)
                        f.write("\n" + "\n".join(tb))
                except Exception:
                    pass
                return
            if self._ladder:
                Clock.schedule_once(self._next, 0.02)
            return
        _mark("all-ok")
        try:
            self._loading.text = "TOOLTX\nSẵn sàng!"
        except Exception:
            pass

    # ────────────────── ladder ──────────────────
    def _load_prefs(self):
        import json
        from core import config as C
        try:
            with open(C.PREF_PATH, encoding="utf-8") as f:
                self._prefs = json.load(f)
        except Exception:
            self._prefs = {}
        default_dark = self._prefs.get("dark")
        if default_dark is None:
            from core import m3
            default_dark = m3.is_dark_default()
        self._dark = bool(default_dark)

    def _save_prefs(self):
        import json
        from core import config as C
        try:
            with open(C.PREF_PATH, "w", encoding="utf-8") as f:
                json.dump(self._prefs, f)
        except Exception:
            pass

    def _st_imports(self):
        global fb, sio_client, C
        import fb
        import sio_client
        from core import config as C
        from core.auth import AuthManager
        from core.theme import make_bg
        from core import m3
        from kivymd.theming import ThemeManager
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.screenmanager import MDScreenManager
        from screens.login import SignInScreen, SignUpScreen
        from screens.home import HomeScreen
        from screens.topup import TopUpScreen
        from screens.tool import ToolScreen
        from screens.settings import SettingsScreen
        from widgets.bottomnav import BottomNav
        # áp theme (đọc cả hệ thống) TRƯỚC khi dựng màn
        self._load_prefs()
        m3.set_dark(self._dark)

    def _st_theme(self):
        from kivy.core.window import Window
        from kivymd.theming import ThemeManager
        from core.m3 import S
        self.theme_cls = ThemeManager()
        self.theme_cls.theme_style = "Dark" if self._dark else "Light"
        self.theme_cls.primary_palette = "LightBlue"
        self.theme_cls.primary_hue = "400"
        Window.clearcolor = S["surface"]
        try:
            Window.softinput_mode = "below_target"
        except Exception:
            pass
        Clock.schedule_once(lambda dt: self._immersive(), 1.2)

    def _st_services(self):
        from core.auth import AuthManager
        self.auth = AuthManager()
        self.sio = sio_client.SioClient(
            on_status=self._on_snapshot,
            on_panel=self._on_panel,
            on_user_status=self._on_user_status,
            on_log=self._log_ui,
            on_connected=lambda: (self._log_ui("Socket đã kết nối."),
                                  self._set_conn("ONLINE", ok=True)),
            on_disconnected=lambda r: (self._log_ui("Mất kết nối socket: " + str(r), err=True),
                                       self._set_conn("OFFLINE", warn=True)),
        )

    def _st_bg(self):
        from core.theme import make_bg
        from core.m3 import S
        self.bg_texture = make_bg(self._dark)
        from kivymd.uix.boxlayout import MDBoxLayout
        self.root_box = MDBoxLayout(orientation="vertical", md_bg_color=(0, 0, 0, 0))
        self._apply_bg(self.root_box)

    def _apply_bg(self, w):
        from kivy.graphics import Color, Rectangle
        with w.canvas.before:
            self._bg_solid = Color(*(0, 0, 0, 1))
            self._bg_solid_r = Rectangle()
            self._bg_tex = Color(1, 1, 1, 1)
            self._bg_tex_r = Rectangle(texture=self.bg_texture)
        w.bind(pos=self._bg_draw, size=self._bg_draw)
        self._bg_draw(w)

    def _refresh_bg(self):
        from core.theme import make_bg
        from core.m3 import S
        try:
            self.bg_texture = make_bg(self._dark)
            self._bg_solid.rgba = S["surface"]
            self._bg_tex_r.texture = self.bg_texture
        except Exception:
            pass

    def _bg_draw(self, inst, *a):
        self._bg_solid_r.pos = inst.pos
        self._bg_solid_r.size = inst.size
        self._bg_tex_r.pos = inst.pos
        self._bg_tex_r.size = inst.size

    def _st_screens(self):
        from kivy.uix.screenmanager import FadeTransition, SlideTransition
        from kivymd.uix.screenmanager import MDScreenManager
        from screens.login import SignInScreen, SignUpScreen
        from screens.home import HomeScreen
        from screens.topup import TopUpScreen
        from screens.tool import ToolScreen
        from screens.settings import SettingsScreen
        self.sm = MDScreenManager(transition=FadeTransition(duration=0.25))
        self.signin = SignInScreen(name="signin", on_goto=self._auth_nav)
        self.signup = SignUpScreen(name="signup", on_goto=self._auth_nav)
        self.home = HomeScreen(name="home", on_profile=lambda: self.goto("settings"))
        self.topup = TopUpScreen(name="topup", on_open_web=self._open_web,
                                 on_done=self.refresh_picks)
        self.tool = ToolScreen(name="tool", on_open=self.start_fork)
        self.settings = SettingsScreen(name="settings", on_back=self.back,
                                       on_theme=self.apply_theme,
                                       on_log=self.set_log_pref,
                                       on_auto=self.set_auto_pref,
                                       on_logout=self.do_logout,
                                       prefs=self._prefs)
        for s in (self.signin, self.signup, self.home, self.topup, self.tool, self.settings):
            self.sm.add_widget(s)
        self.root_box.add_widget(self.sm)

    def _st_finish(self):
        from kivy.core.window import Window
        from widgets.bottomnav import BottomNav
        from core.m3 import S
        self.nav = BottomNav(on_select=self.goto)
        self.root_box.add_widget(self.nav)

        # gắn UI thật vào gốc (thay màn loading).
        try:
            self.root.clear_widgets()
            self.root_box.size_hint = (1, 1)
            self.root.add_widget(self.root_box)
        except Exception:
            pass

        # back hệ thống: không thoát app
        try:
            Window.bind(on_keyboard=self._on_key)
        except Exception:
            pass

        try:
            self.auth.set_session_path(C.SESSION_PATH)
            if self.auth.logged_in():
                self.goto("home", push=False)
                self._set_user(self.auth.current())
                self.recheck()
            else:
                self.goto("signin", push=False)
        except BaseException as e:
            _mark("session-fail:" + repr(e)[:80])

    # ────────────────── điều hướng M3 ──────────────────
    def _set_trans(self, to, via_back=False):
        from kivy.uix.screenmanager import SlideTransition, FadeTransition
        if to == "signup":
            self.sm.transition = SlideTransition(duration=0.2, direction="right")
        elif to == "signin":
            self.sm.transition = SlideTransition(duration=0.2, direction="left")
        elif to == "home":
            if via_back:
                self.sm.transition = SlideTransition(duration=0.2, direction="right")
            else:
                self.sm.transition = FadeTransition(duration=0.25)
        else:
            self.sm.transition = SlideTransition(duration=0.2, direction="left")

    def goto(self, name, push=True, via_back=False):
        try:
            cur = self.sm.current
        except Exception:
            cur = ""
        if name == cur:
            return
        if name not in {w.name for w in self.sm.screens}:
            return
        if push and cur in ("signin", "signup") and name not in ("signin", "signup"):
            self._stack = []
        if push and name != self.sm.current_name:
            self._stack.append(cur)
        self._set_trans(name, via_back=via_back)
        try:
            self.sm.current = name
        except Exception:
            return
        show = name not in ("signin", "signup")
        self.nav.show(show)
        self.nav.set_active(name if show else "")
        if name == "admin" and getattr(self, "admin", None) is not None:
            self.admin_refresh()

    def goto_settings(self, *a):
        self.goto("settings")

    def back(self):
        if self._stack:
            prev = self._stack.pop()
            try:
                self.goto(prev, push=False, via_back=True)
            except Exception:
                pass

    def _auth_nav(self, action):
        if action in ("signin", "signup"):
            self.goto(action)
            return
        if action == "submit-signin":
            u = self.signin.get_account()
            p = self.signin.get_password()
            if not u or not p:
                self.signin.set_status("Nhập tên đăng nhập và mật khẩu.", True)
                return
            self.signin.set_status("Đang đăng nhập...")
            self.do_login(u, p)
        elif action == "submit-signup":
            u = self.signup.get_account()
            p = self.signup.get_password()
            cf = getattr(self.signup, "conf", None)
            c = (cf.text or "") if cf is not None else p
            if not u or not p:
                self.signup.set_status("Nhập tên đăng nhập và mật khẩu.", True)
                return
            if p != c:
                self.signup.set_status("Mật khẩu nhập lại không khớp.", True)
                return
            self.signup.set_status("Đang tạo tài khoản...")
            self.do_register(u, p, u)

    def _focused_field(self):
        try:
            cur = self.sm.current_screen
            if cur is None:
                return None
            from kivymd.uix.textfield import MDTextField
            found = []

            def walk(w):
                if isinstance(w, MDTextField) and w.focus:
                    found.append(w)
                for ch in w.children:
                    walk(ch)
            walk(cur)
            return found[0] if found else None
        except Exception:
            return None

    def _on_key(self, window, key, scancode, codepoint, modifiers):
        if key in (27, 4, "escape"):
            f = self._focused_field()
            if f is not None:
                f.focus = False
            else:
                self.back()
            return True  # luôn nuốt: nút back không thoát app
        return True

    # ────────────────── immersive + mở web ──────────────────
    def _immersive(self):
        if not _ON_ANDROID:
            return
        try:
            from jnius import autoclass
            PyA = autoclass("org.kivy.android.PythonActivity")
            act = PyA.mActivity
            View = autoclass("android.view.View")
            decor = act.getWindow().getDecorView()
            flags = (View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY |
                     View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
                     View.SYSTEM_UI_FLAG_FULLSCREEN |
                     View.SYSTEM_UI_FLAG_LAYOUT_STABLE |
                     View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION |
                     View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN)
            decor.setSystemUiVisibility(flags)
        except Exception:
            pass

    def _open_web(self):
        from core.config import WEB_TOPUP
        if not _ON_ANDROID:
            try:
                import webbrowser
                webbrowser.open(WEB_TOPUP)
                return
            except Exception:
                pass
        try:
            from jnius import autoclass
            PyA = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            act = PyA.mActivity
            i = Intent(Intent.ACTION_VIEW, Uri.parse(WEB_TOPUP))
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            act.startActivity(i)
        except Exception:
            self._log_ui("Không mở được trang nạp tiền: " + WEB_TOPUP, err=True)

    # ────────────────── theme & tuỳ chọn ──────────────────
    def apply_theme(self, dark):
        self._dark = bool(dark)
        self._prefs["dark"] = self._dark
        self._save_prefs()
        from core import m3
        from kivy.core.window import Window
        m3.set_dark(self._dark)
        try:
            Window.clearcolor = m3.S["surface"]
        except Exception:
            pass
        self._rebuild_ui()

    def _rebuild_ui(self):
        """Dựng lại sm + nav theo scheme mới (giữ phiên đăng nhập)."""
        try:
            self._stack = []
            self._refresh_bg()
            if getattr(self, "nav", None) is not None:
                try:
                    self.root_box.remove_widget(self.nav)
                except Exception:
                    pass
            self.nav = None
            try:
                self.root_box.remove_widget(self.sm)
            except Exception:
                pass
            self._st_screens()
            from widgets.bottomnav import BottomNav
            self.nav = BottomNav(on_select=self.goto)
            self.root_box.add_widget(self.nav)
            if getattr(self, "auth", None) is not None and self.auth.logged_in():
                self.goto("home", push=False)
                self._set_user(self.auth.current())
                if self.role == "admin":
                    self.ensure_admin()
            else:
                self.goto("signin", push=False)
        except BaseException:
            pass

    def set_log_pref(self, v):
        self._prefs["log"] = bool(v)
        self._save_prefs()
        try:
            self.settings.set_log(self._last_log)
        except Exception:
            pass

    def set_auto_pref(self, v):
        self._prefs["auto"] = bool(v)
        self._save_prefs()

    # ────────────────── admin (role=admin) ──────────────────
    def ensure_admin(self):
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
            lambda e: self.signin.set_status("Lỗi: " + str(e), err=True),
        )

    def _login_ok(self, res):
        self._set_user(self.auth.current())
        self._log_ui("Đã đăng nhập: " + str(res["data"].get("displayName", res["uid"])))
        self.goto("home", push=False)
        threading.Thread(target=self._connect_socket, daemon=True).start()

    def do_register(self, user, password, name):
        self._run(
            lambda: self.auth.register(user, password, name),
            lambda v: self._reg_ok(v, user, password),
            lambda e: self.signup.set_status("Lỗi: " + str(e), err=True),
        )

    def _reg_ok(self, res, user, password):
        self.signup.set_status("Đăng ký thành công — tự động đăng nhập")
        Clock.schedule_once(lambda dt: self._run(
            lambda: self.auth.login(user, password),
            lambda v: self._login_ok(v),
            lambda e: self.signup.set_status("Đã tạo tài khoản, đăng nhập lại.", err=True),
        ), 0.6)

    def do_logout(self):
        threading.Thread(target=self._shutdown, daemon=True).start()
        self._stack = []
        self.goto("signin", push=False)

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

    # ────────────────── hiển thị dữ liệu ──────────────────
    def _pick_str(self):
        if self.role == "admin":
            return "vô hạn"
        return str(self.picks) if self.picks >= 0 else "--"

    def _set_user(self, sess):
        d = sess or {}
        name = d.get("displayName") or d.get("username") or "Khách"
        letter = (name or "K")[:1].upper()
        self.home.greet(name)
        self.settings.profile(name, letter, d.get("uid"), d.get("role"), self._pick_str())
        self.refresh_picks()

    def refresh_picks(self):
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
                txt = "vô hạn" if self.role == "admin" else str(self.picks)
                warn = self._check_gate()
                self.home.credit(txt, warn=warn)
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
        self.agent_running = False
        Clock.schedule_once(
            lambda dt: (self._log_ui("Agent đã dừng — kiểm tra số lượt đoán."),
                        self.tool.set_agent("Agent đã dừng.")),
        )
        threading.Thread(target=self.refresh_picks, daemon=True).start()

    def _log_ui(self, msg, err=False):
        self._logs.append((str(msg), err))
        self._logs = self._logs[-80:]
        text = "\n".join("- " + m if e else m for m, e in self._logs)
        self._last_log = text
        Clock.schedule_once(partial(self._apply_log, text))

    def _apply_log(self, text, dt):
        try:
            self.settings.set_log(text)
        except Exception:
            pass

    # ────────────────── socket server ──────────────────
    def _connect_socket(self, attempts=0):
        if not self._prefs.get("auto", True):
            self._log_ui("Đã tắt 'Tự kết nối server' trong Cài đặt.")
            return
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
                self.tool.set_agent("Đang chạy agent: " + msg,
                                    col=self._mk(0.35, 0.85, 0.55, 1))
            else:
                self._set_conn("ONLINE")
                self.tool.set_agent("Chưa có agent nào chạy.")
        except Exception:
            pass

    @staticmethod
    def _mk(r, g, b, a):
        return (r, g, b, a)

    def _update_pred(self, p, last=None):
        def upd(dt):
            try:
                self.tool.prediction(p)
            except Exception:
                pass
        Clock.schedule_once(upd)

    def _set_conn(self, text, ok=False, warn=False):
        if text == "ONLINE":
            self.home.server("Server is on", ok=True)
        elif text == "AGENT":
            self.home.server("Server is on - agent", ok=True)
        else:
            self.home.server("Server is off", warn=warn)

    def recheck(self):
        self._set_user(self.auth.current())
        threading.Thread(target=self._connect_socket, daemon=True).start()

    # ────────────────── agent Chrome/CDP (máy tính) ──────────────────
    def start_agent(self):
        if self.agent_running:
            self._log_ui("Agent đang chạy — dừng trước khi khởi động lại.", err=True)
            return
        if C.IS_ANDROID:
            self._log_ui("Trên Android không mở được Chrome CDP. Dùng Open Tool.", err=True)
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
            srv = self.sio.server_url or "http://localhost:8787"
            self._log_ui("Mã liên kết: %s — mở Chrome và nối server..." % code)
            try:
                from agent import Agent
                self.agent = Agent(on_log=self._log_ui, on_stopped=self._agent_stopped)
                ok = self.agent.start(server=srv, code=code)
                self.agent_running = ok
                self.tool.set_agent("Agent Chrome đang chạy." if ok else "Khởi động agent thất bại.",
                                    col=(0.35, 0.85, 0.55, 1) if ok else (0.96, 0.42, 0.46, 1))
            except Exception as e:
                self._log_ui("Lỗi agent: " + str(e), err=True)

        self.sio.agent_pair(on_code)

    # ────────────────── Open Tool — Chromium Fork trên Android ──────────────────
    def start_fork(self):
        if self.agent_running:
            self._log_ui("Agent đang chạy — dừng trước khi khởi động lại.", err=True)
            return
        if not self._picks_ok():
            return
        if not C.IS_ANDROID:
            self._log_ui("Open Tool dành cho Android. Trên máy tính dùng agent_tx.", err=True)
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
            try:
                hcdp.start_browser(url="", package=C.FORK_PACKAGE, activity=C.FORK_ACTIVITY)
                self._log_ui("Đã mở Chromium Fork — kết nối CDP 127.0.0.1:9222...")
                self.tool.set_status("Đang kết nối Chromium Fork...",
                                     col=(0.97, 0.62, 0.24, 1))
                from agent import Agent
                bridge = hcdp.ForkCdpBridge(on_log=self._log_ui)
                self.agent = Agent(on_log=self._log_ui, cdp_backend=bridge,
                                   on_stopped=self._agent_stopped)
                ok = self.agent.start(server=srv, code=code)
                self.agent_running = ok
                if ok:
                    self._log_ui("Agent fork đang chạy — vào game đăng nhập trên tab vừa mở.")
                    self.tool.set_agent("Agent fork đang chạy trên điện thoại.",
                                        col=(0.35, 0.85, 0.55, 1))
                    if self._tick_handle is None:
                        self._tick_handle = Clock.schedule_interval(self._tick_picks, 30)
                else:
                    self.tool.set_agent("Khởi động agent fork thất bại.",
                                        col=(0.96, 0.42, 0.46, 1))
            except Exception as e:
                self._log_ui("Lỗi start fork: " + str(e), err=True)
                self.tool.set_status("Lỗi mở tool: " + str(e),
                                     col=(0.96, 0.42, 0.46, 1))

        self.sio.agent_pair(on_code)

    def on_stop(self):
        try:
            super().on_stop()
        except Exception:
            pass
        _gate_write("OK")


def _write_crash(tb):
    try:
        with open(CRASH_PATH, "a", encoding="utf-8") as f:
            f.write("\n" + tb + "\n")
    except Exception:
        pass


def _show_error(tb, prev=None):
    """Hiện traceback trên màn hình xám để chụp ảnh gửi lại."""
    try:
        from kivy.app import App
        from kivy.uix.label import Label
        from kivy.uix.scrollview import ScrollView
    except Exception:
        _toast("LỖI: " + (prev or "")[:200])
        return

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
    try:
        tb = "".join(traceback.format_exception(
            args.exc_type, args.exc_value, args.exc_traceback))
        _write_crash("[thread] " + tb)
    except Exception:
        pass


def _boot():
    prev = _PREV_STEP
    if _gate_read() == "START":
        # chết sau khi ladder xong → tự hồi phục, không kẹt màn xám.
        died_after_ok = prev.startswith("all-ok") or prev.endswith("=ok")
        if not died_after_ok:
            _show_error("", prev=prev)
            _gate_write("OK")
            try:
                os.remove(CRASH_PATH)
            except Exception:
                pass
            return
    _mark("boot")
    app = ToolApp()
    _mark("app-created")
    _gate_write("START")
    try:
        app.run()
    except BaseException:
        tb = traceback.format_exc()
        _write_crash(tb)
        _toast("EXC: " + tb.splitlines()[-1][:180])
        try:
            _show_error(tb, prev=prev)
        except Exception:
            pass
    _gate_write("OK")
    _mark("app-exited")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--find-browser":
            from agent import find_browser
            print("Browser: " + str(find_browser(sys.argv[2] if len(sys.argv) > 2 else None)))
            sys.exit(0)
    threading.excepthook = _thread_exc
    _boot()