# main.py ΓÇö App KivyMD: ─æ─âng nhß║¡p/─æ─âng k├╜ (Firebase Auth REST) + kß║┐t nß╗æi tool server
#                       + agent tr├¼nh duyß╗çt (Chromium Fork / Chrome CDP).
#
# Kiß║┐n tr├║c theo mß║½u module:
#   ToolApp(MDApp).build()  ΓåÆ  MDScreenManager + LoginScreen/HomeScreen/BrowserScreen/SettingsScreen
#   core/auth.py            ΓåÆ  AuthManager (Firebase)
#   core/theme.py, config.pyΓåÆ  m├áu brand + nß╗ün gradient
#   widgets/bottomnav.py    ΓåÆ  thanh ─æiß╗üu h╞░ß╗¢ng d╞░ß╗¢i
#
# Chß║íy desktop:   python main.py
# Build APK:      xem README (buildozer ΓÇö chß║íy tr├¬n Linux/WSL).

import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CRASH_PATH = os.path.join(APP_DIR, "crash.log")
_ON_ANDROID = bool(os.environ.get("ANDROID_ARGUMENT"))

import faulthandler
try:
    _FAULT_FH = open(os.path.join(APP_DIR, "fault.log"), "a")
    faulthandler.enable(_FAULT_FH, all_threads=True)
except Exception:
    pass


def _toast(msg):
    """Popup Android nhß╗Å ΓÇö k├¬nh chß║⌐n ─æo├ín kh├┤ng phß╗Ñ thuß╗Öc ghi file/kivy."""
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


_mark("main-start")

import threading

from functools import partial

try:
    _mark("k1-clock")
    from kivy.clock import Clock
    _mark("k2-metrics")
    from kivy.metrics import dp
    _mark("k3-graphics")
    from kivy.graphics import Color, Rectangle
    _mark("k4-screenmgr")
    from kivy.uix.screenmanager import FadeTransition
    _mark("k5-mdapp")
    from kivymd.app import MDApp
    _mark("k6-mdbox")
    from kivymd.uix.boxlayout import MDBoxLayout
    _mark("k7-mdsm")
    from kivymd.uix.screenmanager import MDScreenManager
    _mark("kivy-ok")
except BaseException as _e:
    _log_step("kivy-import-fail")
    _toast("KIVY FAIL: " + repr(_e)[:200])
    raise

try:
    _mark("a1-fb")
    import fb
    _mark("a2-sio")
    import sio_client
    _mark("a3-config")
    from core import config as C
    _mark("a4-auth")
    from core.auth import AuthManager
    _mark("a5-theme")
    from core.theme import make_bg
    _mark("a6-login")
    from screens.login import LoginScreen
    _mark("a7-home")
    from screens.home import HomeScreen
    _mark("a8-browser")
    from screens.browser import BrowserScreen
    _mark("a9-settings")
    from screens.settings import SettingsScreen
    _mark("a10-nav")
    from widgets.bottomnav import BottomNav
    _mark("a11-tex")
    from kivy.graphics.texture import Texture
    _mark("app-imports-ok")
except BaseException as _e:
    _log_step("app-imports-fail")
    _toast("IMPORT FAIL: " + repr(_e)[:200])
    raise


class ToolApp(MDApp):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.auth = AuthManager()
        self.sio = sio_client.SioClient(
            on_status=self._on_snapshot,
            on_panel=self._on_panel,
            on_user_status=self._on_user_status,
            on_log=self._log_ui,
            on_connected=lambda: (self._log_ui("Socket ─æ├ú kß║┐t nß╗æi."),
                                  self._set_conn("ONLINE", ok=True)),
            on_disconnected=lambda r: (self._log_ui("Mß║Ñt kß║┐t nß╗æi socket: %s" % r, err=True),
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

    # ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ build ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    def build(self):
        _mark("build")
        from kivy.core.window import Window
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Amber"
        self.theme_cls.accent_palette = "Amber"
        self.theme_cls.primary_hue = "700"
        Window.clearcolor = (0.10, 0.14, 0.22, 1)

        self.bg_texture = make_bg()
        _mark("build-bg")

        self.root_box = MDBoxLayout(orientation="vertical", md_bg_color=(0, 0, 0, 0))
        self._apply_bg(self.root_box)

        self.sm = MDScreenManager(transition=FadeTransition(duration=0.22))
        self.login = LoginScreen(name="login")
        _mark("build-login")
        self.home = HomeScreen(name="home")
        _mark("build-home")
        self.browser = BrowserScreen(name="browser")
        _mark("build-browser")
        self.settings = SettingsScreen(name="settings")
        _mark("build-settings")
        for s in (self.login, self.home, self.browser, self.settings):
            self.sm.add_widget(s)
        self.root_box.add_widget(self.sm)

        self.nav = BottomNav(on_select=self.goto, height=dp(62))
        self.root_box.add_widget(self.nav)

        self.goto("login")
        _mark("build-done")
        return self.root_box

    def _apply_bg(self, w):
        """Nß╗ün gradient + lß╗¢p nß╗ün ─æß║¡m dß╗▒ ph├▓ng (tr├ính ├┤ trß║»ng nß║┐u thiß║┐u texture)."""
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
        from kivy.core.window import Window
        _mark("on_start")
        Window.clearcolor = (0.10, 0.14, 0.22, 1)
        self.auth.set_session_path(C.SESSION_PATH)
        if self.auth.logged_in():
            self.goto("home")
            self.recheck()
        else:
            self.goto("login")

    # ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ ─æiß╗üu h╞░ß╗¢ng ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
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

    # ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ admin (role=admin) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    def ensure_admin(self):
        """Khi ─æ─âng nhß║¡p admin: th├¬m m├án Quß║ún trß╗ï + tab nav, bß║¡t auto-refresh."""
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
        """Khi tho├ít phi├¬n admin: gß╗í m├án + tab + auto-refresh."""
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
            self._log_ui("Kh├┤ng ─æß╗ìc ─æ╞░ß╗úc dß╗» liß╗çu quß║ún trß╗ï: " + str(e), err=True)

    # ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ ─æ─âng nhß║¡p / ─æ─âng k├╜ ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
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
            lambda e: self.login.set_status("Lß╗ùi: " + str(e), err=True),
        )

    def _login_ok(self, res):
        self._set_user(self.auth.current())
        self._log_ui("─É├ú ─æ─âng nhß║¡p: " + str(res["data"].get("displayName", res["uid"])))
        self.goto("home")
        threading.Thread(target=self._connect_socket, daemon=True).start()

    def do_register(self, user, password, name):
        self._run(
            lambda: self.auth.register(user, password, name),
            lambda v: self._reg_ok(v, user, password),
            lambda e: self.login.set_status("Lß╗ùi: " + str(e), err=True),
        )

    def _reg_ok(self, res, user, password):
        self.login.set_status("─É─âng k├╜ th├ánh c├┤ng ΓÇö tß╗▒ ─æß╗Öng ─æ─âng nhß║¡p")
        Clock.schedule_once(lambda dt: self._run(
            lambda: self.auth.login(user, password),
            lambda v: self._login_ok(v),
            lambda e: self.login.set_status("─É├ú tß║ío t├ái khoß║ún, ─æ─âng nhß║¡p lß║íi.", err=True),
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

    # ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ hiß╗ân thß╗ï ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    def _set_user(self, sess):
        d = sess or {}
        name = d.get("displayName") or d.get("username") or "Kh├ích"
        letter = (name or "K")[:1].upper()
        self.home.greet(name)
        self.settings.profile(name, letter, d.get("uid"), d.get("role"), "--")
        self.refresh_picks()

    def refresh_picks(self):
        """─Éß╗ìc sß╗æ l╞░ß╗út ─æo├ín c├▓n lß║íi tß╗½ RTDB (giß╗æng tool web) ─æß╗â quß║ún l├╜ l╞░ß╗út cho tß╗½ng user."""
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
            self._log_ui("Kh├┤ng ─æß╗ìc ─æ╞░ß╗úc sß╗æ l╞░ß╗út: " + str(e), err=True)
            return
        Clock.schedule_once(lambda dt: self.ensure_admin())

        def upd(dt):
            try:
                if self.role == "admin":
                    txt = "Γê₧"
                    warn = False
                else:
                    txt = str(self.picks)
                    warn = self._check_gate()
                self.home.picks_text("L╞░ß╗út: " + txt, warn=warn)
                self.settings.picks_text(txt)
                if self._check_gate():
                    self.home.gate("Bß║áN ─É├â Hß║╛T L╞»ß╗óT ─ÉO├üN ΓÇö nß║íp th├¬m tß║íi trang web ─æß╗â tiß║┐p tß╗Ñc.")
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
            self._log_ui("Hß║┐t l╞░ß╗út ─æo├ín ΓÇö nß║íp th├¬m tß║íi trang web rß╗ôi thß╗¡ lß║íi.", err=True)
            self.refresh_picks()
            return False
        return True

    def _agent_stopped(self):
        """Server tß╗½ chß╗æi (hß║┐t l╞░ß╗út) hoß║╖c mß║Ñt kß║┐t nß╗æi ΓåÆ reset UI + ─æß╗ìc lß║íi l╞░ß╗út."""
        self.agent_running = False
        Clock.schedule_once(
            lambda dt: (self._log_ui("Agent ─æ├ú dß╗½ng ΓÇö kiß╗âm tra sß╗æ l╞░ß╗út ─æo├ín."),
                        self.browser.set_agent("Agent ─æ├ú dß╗½ng.")),
        )
        threading.Thread(target=self.refresh_picks, daemon=True).start()

    def _log_ui(self, msg, err=False):
        self._logs.append((str(msg), err))
        self._logs = self._logs[-80:]
        text = "\n".join("ΓÜá " + m if e else m for m, e in self._logs)
        Clock.schedule_once(partial(self._apply_log, text))

    def _apply_log(self, text, dt):
        try:
            self.settings.set_log(text)
        except Exception:
            pass

    # ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ socket server ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    def _connect_socket(self, attempts=0):
        try:
            tok = self.auth.refresh_id_token()
            srv = sio_client.SioClient.discover_server(C.CFG_PATH)
            if not srv:
                self._log_ui("Kh├┤ng t├¼m thß║Ñy server (server-url.json).", err=True)
                return
            self._log_ui("Server: " + srv)
            self.sio.connect(srv, tok)
        except Exception as e:
            if attempts < 2:
                threading.Timer(5, lambda: self._connect_socket(attempts + 1)).start()
            self._log_ui("Lß╗ùi kß║┐t nß╗æi server: " + str(e), err=True)
            self._set_conn("OFFLINE", warn=True)

    def _on_snapshot(self, d):
        snap = d or {}
        self._set_conn("ONLINE", ok=True)
        self._log_ui("─É├ú kß║┐t nß╗æi ΓÇö %s v├ín" % (len((snap.get("history") or []))))
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
                self.browser.set_agent("─Éang chß║íy agent: " + msg, col=(0.35, 0.85, 0.55, 1))
            else:
                self._set_conn("ONLINE")
                self.home.agent("")
                self.browser.set_agent("Ch╞░a c├│ agent n├áo chß║íy.")
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

    # ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ agent Chrome/CDP (m├íy t├¡nh) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    def start_agent(self):
        if self.agent_running:
            self._log_ui("Agent ─æang chß║íy ΓÇö dß╗½ng tr╞░ß╗¢c khi khß╗ƒi ─æß╗Öng lß║íi.", err=True)
            return
        if C.IS_ANDROID:
            self._log_ui("Tr├¬n Android kh├┤ng mß╗ƒ ─æ╞░ß╗úc Chrome CDP. D├╣ng START BROWSER.", err=True)
            return
        if self.is_agent_mode:
            self._log_ui("Bß║ín ─æang ß╗ƒ chß║┐ ─æß╗Ö agent ΓÇö ngß║»t ─æß╗â quay lß║íi m├íy chß╗º.", err=True)
            return

        def on_code(r):
            code = (r or {}).get("code")
            if not code:
                self._log_ui("Ch╞░a lß║Ñy ─æ╞░ß╗úc m├ú li├¬n kß║┐t.", err=True)
                return
            self.agent_code = code
            self.browser.set_code(code)
            srv = self.sio.server_url or "http://localhost:8787"
            self._log_ui("M├ú li├¬n kß║┐t: %s ΓÇö mß╗ƒ Chrome v├á nß╗æi server..." % code)
            self.browser.set_status("─Éang mß╗ƒ Chrome v├á nß╗æi server...", col=(0.97, 0.62, 0.24, 1))
            try:
                from agent import Agent
                self.agent = Agent(on_log=self._log_ui, on_stopped=self._agent_stopped)
                ok = self.agent.start(server=srv, code=code)
                self.agent_running = ok
                self.browser.set_agent("Agent Chrome ─æang chß║íy." if ok else "Khß╗ƒi ─æß╗Öng agent thß║Ñt bß║íi.",
                                   col=(0.35, 0.85, 0.55, 1) if ok else (0.96, 0.42, 0.46, 1))
            except Exception as e:
                self._log_ui("Lß╗ùi agent: " + str(e), err=True)
                self.browser.set_status("Lß╗ùi agent: " + str(e), col=(0.96, 0.42, 0.46, 1))

        self.sio.agent_pair(on_code)

    # ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ START BROWSER ΓÇö Chromium Fork tr├¬n Android ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    def start_fork(self):
        """Mß╗ƒ Chromium Fork (APK tß╗▒ build) th├ánh 1 tab ri├¬ng tr├¬n ─æiß╗çn thoß║íi,
        rß╗ôi nß╗æi CDP 127.0.0.1:9222 l├ám agent cho server.
        Sß╗æ l╞░ß╗út vß║½n do server quß║ún l├╜ nh╞░ web."""
        if self.agent_running:
            self._log_ui("Agent ─æang chß║íy ΓÇö dß╗½ng tr╞░ß╗¢c khi khß╗ƒi ─æß╗Öng lß║íi.", err=True)
            return
        if not self._picks_ok():
            return
        if not C.IS_ANDROID:
            self._log_ui("START BROWSER d├ánh cho Android. Tr├¬n m├íy t├¡nh d├╣ng CHROME M├üY Bß║áN.", err=True)
            return
        if not self.sio.connected:
            self._log_ui("Ch╞░a kß║┐t nß╗æi server. ─Éang nß╗æi lß║íi...", err=True)
            threading.Thread(target=self._connect_socket, daemon=True).start()
            return
        if self.is_agent_mode:
            self._log_ui("─Éang ß╗ƒ chß║┐ ─æß╗Ö agent ΓÇö ngß║»t tr╞░ß╗¢c khi khß╗ƒi ─æß╗Öng lß║íi.", err=True)
            return
        try:
            import hcdp
        except Exception as e:
            self._log_ui("Kh├┤ng tß║úi ─æ╞░ß╗úc hcdp: " + str(e), err=True)
            return
        srv = self.sio.server_url or "http://localhost:8787"

        def on_code(r):
            code = (r or {}).get("code")
            if not code:
                self._log_ui("Ch╞░a lß║Ñy ─æ╞░ß╗úc m├ú li├¬n kß║┐t.", err=True)
                return
            self.agent_code = code
            self.browser.set_code(code)
            try:
                hcdp.start_browser(url="", package=C.FORK_PACKAGE, activity=C.FORK_ACTIVITY)
                self._log_ui("─É├ú mß╗ƒ Chromium Fork ΓÇö kß║┐t nß╗æi CDP 127.0.0.1:9222...")
                self.browser.set_status("─É├ú mß╗ƒ Chromium Fork ΓÇö kß║┐t nß╗æi CDP...",
                                    col=(0.97, 0.62, 0.24, 1))
                from agent import Agent
                bridge = hcdp.ForkCdpBridge(on_log=self._log_ui)
                self.agent = Agent(on_log=self._log_ui, cdp_backend=bridge,
                                   on_stopped=self._agent_stopped)
                ok = self.agent.start(server=srv, code=code)
                self.agent_running = ok
                if ok:
                    self._log_ui("Agent fork ─æang chß║íy ΓÇö v├áo game ─æ─âng nhß║¡p tr├¬n tab vß╗½a mß╗ƒ.")
                    self.browser.set_agent("Agent fork ─æang chß║íy tr├¬n ─æiß╗çn thoß║íi.",
                                       col=(0.35, 0.85, 0.55, 1))
                    if self._tick_handle is None:
                        self._tick_handle = Clock.schedule_interval(self._tick_picks, 30)
                else:
                    self.browser.set_agent("Khß╗ƒi ─æß╗Öng agent fork thß║Ñt bß║íi.",
                                       col=(0.96, 0.42, 0.46, 1))
            except Exception as e:
                self._log_ui("Lß╗ùi start fork: " + str(e), err=True)
                self.browser.set_status("Lß╗ùi start fork: " + str(e), col=(0.96, 0.42, 0.46, 1))

        self.sio.agent_pair(on_code)


def _last_step():
    try:
        with open(CRASH_PATH, encoding="utf-8") as f:
            lines = [ln.strip() for ln in f.read().splitlines() if ln.strip()]
            return (lines[-1] if lines else "")[:300]
    except Exception:
        return ""


def _write_crash(tb):
    try:
        with open(CRASH_PATH, "a", encoding="utf-8") as f:
            f.write("\n" + tb + "\n")
    except Exception:
        pass


def _show_error(tb, prev=None):
    """Hiß╗çn traceback tr├¬n m├án h├¼nh x├ím ─æen ─æß╗â chß╗Ñp ß║únh gß╗¡i lß║íi."""
    try:
        from kivy.app import App
        from kivy.uix.label import Label
        from kivy.uix.scrollview import ScrollView
    except Exception:
        _toast("Lß╗ûI: " + (prev or "")[:200])
        return

    head = ""
    if prev:
        head = "Lß║ªN CHß║áY TR╞»ß╗ÜC Dß╗¬NG Tß║áI: %s\n\n" % prev

    class ErrApp(App):
        title = "TOOLTX ΓÇö lß╗ùi khß╗ƒi ─æß╗Öng"

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
    if prev and prev != "STEP app-exited":
        _show_error("", prev=prev)
        try:
            os.remove(CRASH_PATH)
        except Exception:
            pass
        return
    _mark("boot")
    try:
        app = ToolApp()
        _mark("app-created")
        app.run()
    except Exception:
        import traceback
        tb = traceback.format_exc()
        _write_crash(tb)
        _toast("EXC: " + tb.splitlines()[-1][:180])
        try:
            _show_error(tb, prev=_last_step())
        except Exception:
            pass
    _mark("app-exited")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--find-browser":
            from agent import find_browser
            print("Browser: " + str(find_browser(sys.argv[2] if len(sys.argv) > 2 else None)))
            sys.exit(0)
    threading.excepthook = _thread_exc
    _boot()
