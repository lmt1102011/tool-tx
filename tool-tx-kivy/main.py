# DIAG build — màn hình chẩn đoán: hiện từng bước import TRÊN MÀN HÌNH (kivy core, đã chứng minh chạy được).
# Nếu app chết (kể cả native) → màn hình treo ở bước cuối; lỗi Python → hiện traceback.
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
    if not _ON_ANDROID:
        return
    try:
        from jnius import autoclass
        A = autoclass("org.kivy.android.PythonActivity")
        Toast = autoclass("android.widget.Toast")
        Toast.makeText(A.mActivity, str(msg)[:220], 1).show()
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
_mark("pre-kivy-ok")


from kivy.app import App
from kivy.core.window import Window
from kivy.uix.label import Label


def _show_error(tb, prev=None):
    try:
        sv_h = lambda *a: None
        class ErrApp(App):
            title = "TOOLTX — lỗi khởi động"
            def build(self):
                from kivy.uix.scrollview import ScrollView
                sv = ScrollView()
                head = "LẦN CHẠY TRƯỚC DỪNG TẠI: %s\n\n" % (prev or "") if prev else ""
                l = Label(text=head + tb, font_size="11sp", halign="left", valign="top",
                          size_hint_y=None, padding=(10, 10), color=(1, 1, 1, 1))
                l.bind(width=lambda inst, w: setattr(inst, "text_size", (w * 0.98, None)))
                sv.add_widget(l)
                return sv
        ErrApp().run()
    except Exception:
        _toast("LỖI: " + (prev or "")[:200])


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


def _thread_exc(args):
    import traceback
    try:
        tb = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
        _write_crash("[thread] " + tb)
    except Exception:
        pass


class DiagApp(App):
    title = "tooltx diag"

    def _step(self, lab, tag, fn):
        _mark(tag)
        lab.text = tag
        try:
            return fn()
        except BaseException as _e:
            import traceback
            import builtins
            tb = traceback.format_exc()
            lab.text = tag + "\n\nLOI:\n" + tb[-3000:]
            _write_crash(tb)
            builtins._diag_error = _e
            return None

    def build(self):
        import importlib
        Window.clearcolor = (0.10, 0.14, 0.22, 1)
        lab = Label(text="TOOLTX DIAG\nkhoi dong...", font_size="16sp",
                    halign="center", valign="middle", color=(1, 1, 1, 1))
        lab.bind(size=lambda inst, *a: setattr(inst, "text_size", (inst.width * 0.94, None)))
        lab.bind(size=lambda inst, *a: setattr(inst, "valign", "middle"))
        import kivy.clock

        def imp(name):
            return importlib.import_module(name)

        ok = True
        for tag, name in [
            ("b1 kivy.clock", "kivy.clock"),
            ("b2 kivy.metrics", "kivy.metrics"),
            ("b3 kivy.graphics", "kivy.graphics"),
            ("b4 kivy.graphics.texture", "kivy.graphics.texture"),
            ("b5 kivy.uix.screenmanager", "kivy.uix.screenmanager"),
            ("b6 jnius", "jnius"),
            ("b7 kivymd.app", "kivymd.app"),
            ("b8 kivymd.uix.boxlayout", "kivymd.uix.boxlayout"),
            ("b9 kivymd.uix.screenmanager", "kivymd.uix.screenmanager"),
            ("b10 fb", "fb"),
            ("b11 sio_client", "sio_client"),
            ("b12 core.config", "core.config"),
            ("b13 core.auth", "core.auth"),
            ("b14 core.theme", "core.theme"),
            ("b15 screens.login", "screens.login"),
            ("b16 screens.home", "screens.home"),
            ("b17 screens.browser", "screens.browser"),
            ("b18 screens.settings", "screens.settings"),
            ("b19 widgets.bottomnav", "widgets.bottomnav"),
        ]:
            if self._step(lab, tag, lambda m=name: imp(m)) is None:
                ok = False
                break

        if ok:
            def mk_bg():
                from core.theme import make_bg
                return make_bg()
            if self._step(lab, "b20 make_bg()", mk_bg) is None:
                ok = False

        if ok:
            def mk_screens():
                from screens.login import LoginScreen
                from screens.home import HomeScreen
                from screens.browser import BrowserScreen
                from screens.settings import SettingsScreen
                a = LoginScreen(name="login")
                b = HomeScreen(name="home")
                c = BrowserScreen(name="browser")
                d = SettingsScreen(name="settings")
                return (a, b, c, d)
            if self._step(lab, "b21 tao 4 man hinh", mk_screens) is None:
                ok = False

        if ok:
            _mark("all-ok")
            lab.text = "DIAG: TẤT CẢ BƯỚC OK ✓\n(UI chỉ để chẩn đoán)"

        return lab


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
        app = DiagApp()
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
    import threading
    threading.excepthook = _thread_exc
    _boot()