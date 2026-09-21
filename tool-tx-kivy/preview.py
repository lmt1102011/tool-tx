"""
preview.py - Desktop simulator + crash catcher.
Mo'i lo'i (PC lo'i mobile) deu duoc bat va ghi ra preview_crash.log.

Run: .venv\\Scripts\\python.exe preview.py
     hoac: python preview.py (tu thu muc co .venv)
Phim: 1-4 chuyen tab, d-toggle dark, q-thoat.
"""
import os, sys, time, traceback, subprocess

APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(APP_DIR, "preview_crash.log")

# ── Auto-venv: tim va su dung .venv neu co ────────────────
def _ensure_venv():
    if "kivy" in sys.modules:
        return
    # Tim .venv o nhieu noi
    candidates = [
        APP_DIR,
        os.path.dirname(APP_DIR),
        r"C:\Users\Tri\Desktop\Tool\tool-tx-kivy",
    ]
    for check_dir in candidates:
        for sub in ["Scripts/python.exe", "bin/python3"]:
            venv_python = os.path.join(check_dir, ".venv", sub)
            if os.path.isfile(venv_python):
                exe = sys.executable
                if exe.lower() != os.path.abspath(venv_python).lower():
                    print("[preview] Dang chuyen sang .venv: %s" % venv_python)
                    os.execv(venv_python, [venv_python] + sys.argv)
                    sys.exit(0)
    # Kiem tra kivy co san khong
    try:
        import kivy
    except ImportError:
        msg = (
            "\n[LOI] Khong tim thay kivy!\n"
            "  Ban dang chay tu: %s\n"
            "  Can chay tu thu muc chinh: C:\\Users\\Tri\\Desktop\\Tool\\tool-tx-kivy\n\n"
            "  Cach fix:\n"
            "    cd C:\\Users\\Tri\\Desktop\\Tool\\tool-tx-kivy\n"
            "    .venv\\Scripts\\python.exe preview.py\n"
        ) % APP_DIR
        print(msg)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(msg)
        sys.exit(1)

_ensure_venv()

os.environ["KIVY_LOG_LEVEL"] = "warning"
os.environ["KIVY_WINDOW"] = "sdl2"


# ── Crash logger ──────────────────────────────────────────
_log_fh = open(LOG_PATH, "a", encoding="utf-8")

def log_write(text, level="INFO"):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = "[%s] %s: %s\n" % (ts, level, text)
    _log_fh.write(entry)
    _log_fh.flush()
    print(entry.strip())

def log_error(text):
    log_write(text, "ERROR")

def log_exception(tag=""):
    tb = traceback.format_exc()
    header = "EXCEPTION %s" % tag if tag else "EXCEPTION"
    log_error("%s\n%s" % (header, tb))
    return tb

def log_crash_to_file():
    """Ghi crash log cho mobile — cùng format với main.py."""
    from main import _crash_write
    tb = traceback.format_exc()
    _crash_write("[PREVIEW]\n%s" % tb)


# ── Global exception hooks ────────────────────────────────
_prev_excepthook = sys.excepthook
def _global_excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    log_error("UNCAUGHT\n%s" % tb)
    if _prev_excepthook:
        _prev_excepthook(exc_type, exc_value, exc_tb)
sys.excepthook = _global_excepthook

_prev_thread_hook = getattr(sys, "excepthook", None)
def _thread_excepthook(args):
    tb = "".join(traceback.format_exception(
        args.exc_type, args.exc_value, args.exc_traceback))
    log_error("THREAD [%s]\n%s" % (args.thread, tb))
sys.excepthook = _global_excepthook
import threading
threading.excepthook = _thread_excepthook


# ── Validate imports (bắt lỗi giống mobile) ──────────────
log_write("=== PREVIEW START ===")
log_write("Python %s" % sys.version)
log_write("Kivy loaded")

try:
    from kivy.core.window import Window
    Window.size = (412, 892)
    log_write("Window: 412x892")
except Exception:
    log_exception("window-init")

_validate_imports = [
    "kivy", "kivymd", "kivymd.app", "kivymd.uix.boxlayout",
    "kivymd.uix.card", "kivymd.uix.label", "kivymd.uix.button",
    "kivymd.uix.screen", "kivymd.uix.screenmanager",
    "kivymd.uix.scrollview", "kivymd.uix.selectioncontrol",
    "kivymd.uix.progressbar", "kivymd.uix.dialog",
    "core.m3", "core.config",
    "screens.uikit", "screens.login", "screens.home",
    "screens.topup", "screens.tool", "screens.settings",
    "widgets.bottomnav",
]
for mod in _validate_imports:
    try:
        __import__(mod)
        log_write("import OK: %s" % mod)
    except Exception:
        log_exception("import:%s" % mod)

log_write("=== ALL IMPORTS VALIDATED ===")


# ── App ───────────────────────────────────────────────────
try:
    import kivy
    from kivy.uix.screenmanager import ScreenManager
    from kivy.uix.widget import Widget
    from kivymd.app import MDApp
    from kivymd.uix.boxlayout import MDBoxLayout
    from core.config import FORK_PACKAGE
    from core.m3 import S, set_dark
    from screens.login import SignInScreen, SignUpScreen
    from screens.home import HomeScreen
    from screens.topup import TopUpScreen
    from screens.tool import ToolScreen
    from screens.settings import SettingsScreen
    from widgets.bottomnav import BottomNav
    log_write("All screen imports OK")
except Exception:
    tb = log_exception("screen-imports")
    SignInScreen = SignUpScreen = HomeScreen = None
    TopUpScreen = ToolScreen = SettingsScreen = BottomNav = None


class DevShell(MDApp):
    def __init__(self, **kw):
        self._going = True
        super().__init__(**kw)
        self.title = "Dev Preview"
        log_write("DevShell.__init__")

    def build(self):
        log_write("DevShell.build start")
        self.theme_cls.theme_style = "Dark"
        root = MDBoxLayout(orientation="vertical")
        self.sm = ScreenManager()
        root.add_widget(self.sm)

        def _goto(name):
            if name.startswith("submit-"):
                return
            try:
                self.sm.current = name
                log_write("nav -> %s" % name)
            except Exception:
                log_exception("nav:%s" % name)

        errors = []

        def _try_screen(cls, name, **kw):
            try:
                s = cls(name=name, **kw)
                log_write("screen OK: %s" % name)
                return s
            except Exception:
                tb = log_exception("screen:%s" % name)
                errors.append((name, tb))
                return None

        self.sigin = _try_screen(SignInScreen, "signin", on_goto=_goto)
        self.sisignup = _try_screen(SignUpScreen, "signup", on_goto=_goto)
        self.shome = _try_screen(HomeScreen, "home", on_profile=lambda: _goto("settings"))

        def _open_web():
            try:
                import webbrowser
                webbrowser.open("https://tooltx.site/topup")
            except Exception:
                log_exception("open-web")

        self.stopup = _try_screen(TopUpScreen, "topup", on_open_web=_open_web)
        self.stool = _try_screen(ToolScreen, "tool", on_open=lambda: None)
        self.sset = _try_screen(SettingsScreen, "settings", on_back=lambda: _goto("home"))

        for s in [self.sigin, self.sisignup, self.shome, self.stopup, self.stool, self.sset]:
            if s is not None:
                try:
                    self.sm.add_widget(s)
                except Exception:
                    log_exception("add_widget:%s" % s.name)

        self.sm.current = "home"

        try:
            nav = BottomNav(
                items=[("home", "Home"), ("credit-card", "Top Up"),
                       ("wrench", "Tool"), ("cog", "Settings")],
                on_select=lambda i: self._nav_select(i),
            )
            self._nav = nav
            root.add_widget(nav)
            log_write("BottomNav OK")
        except Exception:
            log_exception("bottomnav")

        Window.bind(on_key_down=self._on_key)

        try:
            self.shome.greet("Dev User")
            self.shome.credit("99")
            self.shome.server("Server: OK", ok=True)
            self.stool.prediction({"pick": "T", "pT": 65, "confidence": 78,
                                    "history": ["T", "X", "T", "X", "X", "T", "T", "T", "X"]})
            self.sset.profile("Dev User", "D", "12345", "admin", "10")
            log_write("Data populated OK")
        except Exception:
            log_exception("populate-data")

        if errors:
            log_error("=== %d SCREEN(S) FAILED ===" % len(errors))
            for name, tb in errors:
                log_error("--- %s ---\n%s" % (name, tb))

        log_write("DevShell.build done")
        return root

    def _nav_select(self, idx):
        names = ["home", "topup", "tool", "settings"]
        if idx < len(names):
            try:
                self.sm.current = names[idx]
                self._nav.select(idx)
                log_write("nav -> %s" % names[idx])
            except Exception:
                log_exception("nav-select:%s" % names[idx])

    def _on_key(self, window, key, scancode, codepoint, modifiers):
        try:
            if key == ord('d'):
                toggle_dark()
                self._nav.update_colors()
            elif key == ord('q'):
                self.stop()
                return True
            elif key in (49, 50, 51, 52):
                self._nav_select(key - 49)
        except Exception:
            log_exception("key:%d" % key)
        return False


_dark = True
def toggle_dark():
    global _dark
    _dark = not _dark
    try:
        set_dark(_dark)
        from kivymd.app import MDApp
        MDApp.get_running_app().theme_cls.theme_style = "Dark" if _dark else "Light"
        from kivy.core.window import Window
        Window.clearcolor = S["surface"]
        log_write("theme -> %s" % ("dark" if _dark else "light"))
    except Exception:
        log_exception("toggle-dark")


if __name__ == "__main__":
    try:
        set_dark(True)
        from kivy.core.window import Window
        Window.clearcolor = S["surface"]
        log_write("Starting DevShell...")
        DevShell().run()
    except Exception:
        log_exception("FATAL")
    finally:
        log_write("=== PREVIEW END ===")
        _log_fh.close()
