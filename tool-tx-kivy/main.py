# main.py — LIVE DIAG (ToolTX): chỉ dùng kivy base đã chứng minh chạy trên máy,
# import từng module một, hiện tiến trình lên MÀN HÌNH NGAY (lần chạy đầu).
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


def _toast(msg):
    if not _ON_ANDROID:
        return
    try:
        from jnius import autoclass
        A = autoclass("org.kivy.android.PythonActivity")
        Toast = autoclass("android.widget.Toast")
        Toast.makeText(A.mActivity, str(msg)[:220], 0).show()
    except Exception:
        pass


def _mark(step):
    _log_step(step)
    _toast("T:" + step)


def _last_step():
    try:
        with open(CRASH_PATH, encoding="utf-8") as f:
            lines = [ln.strip() for ln in f.read().splitlines() if ln.strip()]
        if lines:
            return lines[-1]
    except Exception:
        pass
    return ""


_mark("live-start")

import importlib
import threading
import traceback

# ── chỉ nhóm ĐÃ CHỨNG MINH chạy trên máy (app tối giản) ──
import kivy  # NOQA
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
_mark("base-ok")


def _inst_bg():
    from core.theme import make_bg
    return make_bg()


def _inst_screens():
    from screens.login import LoginScreen
    from screens.home import HomeScreen
    from screens.browser import BrowserScreen
    from screens.settings import SettingsScreen
    LoginScreen(name="login")
    HomeScreen(name="home")
    BrowserScreen(name="browser")
    SettingsScreen(name="settings")
    return True


def _inst_nav():
    from kivy.metrics import dp
    from widgets.bottomnav import BottomNav
    BottomNav(on_select=lambda name: None, height=dp(62))
    return True


class LiveApp(App):
    title = "TOOLTX LIVE DIAG"

    def build(self):
        sv = ScrollView()
        self.lbl = Label(text="DIAG boot...", font_size="13sp", halign="left",
                         valign="top", size_hint_y=None, padding=(14, 14),
                         color=(1, 1, 1, 1))
        self.lbl.bind(width=lambda i, w: setattr(i, "text_size", (w * 0.97, None)))
        sv.add_widget(self.lbl)
        return sv

    def on_start(self):
        prev = _last_step()
        self._base = ["LIVE DIAG (ToolTX app)",
                      "PREV RUN: " + (prev or "~ lan dau tien ~"), ""]
        self._lines = []
        self._ladder = [
            ("k1 kivy.clock",           lambda: importlib.import_module("kivy.clock")),
            ("k2 kivy.metrics",         lambda: importlib.import_module("kivy.metrics")),
            ("k3 kivy.graphics",        lambda: importlib.import_module("kivy.graphics")),
            ("k4 screenmanager",        lambda: importlib.import_module("kivy.uix.screenmanager")),
            ("k5 kivymd.app",           lambda: importlib.import_module("kivymd.app")),
            ("k6 kivymd.boxlayout",     lambda: importlib.import_module("kivymd.uix.boxlayout")),
            ("k7 kivymd.screenmgr",     lambda: importlib.import_module("kivymd.uix.screenmanager")),
            ("k8 texture",              lambda: importlib.import_module("kivy.graphics.texture")),
            ("a1 fb",                   lambda: importlib.import_module("fb")),
            ("a2 sio_client",           lambda: importlib.import_module("sio_client")),
            ("a3 core.config",          lambda: importlib.import_module("core.config")),
            ("a4 core.auth",            lambda: importlib.import_module("core.auth")),
            ("a5 core.theme",           lambda: importlib.import_module("core.theme")),
            ("a6 screens.login",        lambda: importlib.import_module("screens.login")),
            ("a7 screens.home",         lambda: importlib.import_module("screens.home")),
            ("a8 screens.browser",      lambda: importlib.import_module("screens.browser")),
            ("a9 screens.settings",     lambda: importlib.import_module("screens.settings")),
            ("a10 widgets.bottomnav",   lambda: importlib.import_module("widgets.bottomnav")),
            ("INST make_bg()",          _inst_bg),
            ("INST 4 screens",          _inst_screens),
            ("INST BottomNav",          _inst_nav),
            ("DONE",                    None),
        ]
        self._say("START", ok=True)
        Clock.schedule_once(self._next, 0.1)

    def _say(self, text, ok=False, err=False):
        self._lines.append(text)
        rendered = self._base + list(self._lines)
        colored = "\n".join(rendered)
        self.lbl.text = colored
        self.lbl.color = (1, 0.5, 0.5, 1) if err else (1, 1, 1, 1)

    def _next(self, *fdeps):
        while self._ladder:
            name, fn = self._ladder.pop(0)
            if fn is None:
                _mark("all-ok")
                self._say("ALL OK — TOOL APP SAN SANG ✓", ok=True)
                return
            _mark(name)
            self._say("RUN  " + name)
            try:
                fn()
                _mark(name + "=ok")
                self._say("OK   " + name + " ✓")
            except BaseException as e:
                _mark(name + "=fail")
                self._say("ERR  " + name + " :: " + repr(e)[:160], err=True)
                tb = traceback.format_exc().splitlines()
                for ln in tb[-6:]:
                    self._say("     " + ln[:120], err=True)
                self._write_crash(name, tb)
                return
            Clock.schedule_once(self._next, 0.02)
            return
        _mark("all-ok")
        self._say("ALL OK ✓", ok=True)

    def _write_crash(self, step, tb):
        try:
            with open(CRASH_PATH, "a", encoding="utf-8") as f:
                f.write("\n### FAIL AT " + step)
                f.write("\n" + "\n".join(tb))
        except Exception:
            pass


if __name__ == "__main__":
    threading.excepthook = lambda args: None
    LiveApp().run()