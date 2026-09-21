"""
preview.py — Desktop simulator for KivyMD screens.
Run: python preview.py
Phone-sized window 412×892. Navigate with bottom tabs or 't' key.
Dark mode toggle: press 'd'.
"""
import os, sys, time
os.environ["KIVY_LOG_LEVEL"] = "warning"
os.environ["KIVY_WINDOW"] = "sdl2"

from kivy.core.window import Window
Window.size = (412, 892)

import kivy
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout

from core.config import FB as _fb, FORK_PACKAGE
from core.m3 import S, set_dark
from screens.login import SignInScreen, SignUpScreen
from screens.home import HomeScreen
from screens.topup import TopUpScreen
from screens.tool import ToolScreen
from screens.settings import SettingsScreen
from widgets.bottomnav import BottomNav


class DevShell(MDApp):
    def __init__(self, **kw):
        self._going = True
        super().__init__(**kw)
        self.title = "Dev Preview"
        self.theme_cls.theme_style = "Dark"

    def build(self):
        root = MDBoxLayout(orientation="vertical")
        self.sm = ScreenManager()
        root.add_widget(self.sm)

        def _goto(name):
            if name.startswith("submit-"):
                return
            try:
                self.sm.current = name
            except Exception:
                pass

        self.sigin = SignInScreen(name="signin", on_goto=_goto)
        self.sisignup = SignUpScreen(name="signup", on_goto=_goto)
        self.shome = HomeScreen(name="home", on_profile=lambda: _goto("settings"))

        def _open_web():
            try:
                import webbrowser
                webbrowser.open("https://tooltx.site/topup")
            except Exception:
                pass

        self.stopup = TopUpScreen(name="topup", on_open_web=_open_web)
        self.stool = ToolScreen(name="tool", on_open=lambda: None)
        self.sset = SettingsScreen(name="settings", on_back=lambda: _goto("home"))

        for s in [self.sigin, self.sisignup, self.shome, self.stopup, self.stool, self.sset]:
            self.sm.add_widget(s)

        self.sm.current = "home"

        nav = BottomNav(
            items=[("home", "Home"), ("home", "Top Up"), ("home", "Tool"),
                   ("cog", "Settings")],
            on_select=lambda i: self._nav_select(i),
        )
        self._nav = nav
        root.add_widget(nav)

        Window.bind(on_key_down=self._on_key)
        self.shome.greet("Dev User")
        self.shome.credit("99")
        self.shome.server("Server: OK", ok=True)
        self.stool.prediction({"pick": "T", "pT": 65, "confidence": 78,
                                "history": ["T", "X", "T", "X", "X", "T", "T", "T", "X"]})
        self.sset.profile("Dev User", "D", "12345", "admin", "10")
        return root

    def _nav_select(self, idx):
        names = ["home", "topup", "tool", "settings"]
        if idx < len(names):
            self.sm.current = names[idx]
            self._nav.select(idx)

    def _on_key(self, window, key, scancode, codepoint, modifiers):
        if key == ord('d'):
            toggle_dark()
            self._nav.update_colors()
        elif key == ord('1'):
            self._nav_select(0)
        elif key == ord('2'):
            self._nav_select(1)
        elif key == ord('3'):
            self._nav_select(2)
        elif key == ord('4'):
            self._nav_select(3)
        return False


_dark = True
def toggle_dark():
    global _dark
    _dark = not _dark
    set_dark(_dark)
    try:
        from kivymd.app import MDApp
        MDApp.get_running_app().theme_cls.theme_style = "Dark" if _dark else "Light"
    except Exception:
        pass
    from kivy.core.window import Window
    Window.clearcolor = S["background"]


if __name__ == "__main__":
    set_dark(True)
    from kivy.core.window import Window
    Window.clearcolor = S["background"]
    DevShell().run()
