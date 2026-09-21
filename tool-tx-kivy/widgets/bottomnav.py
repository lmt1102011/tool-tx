# widgets/bottomnav.py — Navigation bar M3: 80dp, surfaceContainer, pill chủ động 64x32.
from kivy.metrics import dp, sp
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.behaviors.button import ButtonBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDIcon

from core.m3 import S
from screens.uikit import label


class NavItem(ButtonBehavior, MDBoxLayout):
    def __init__(self, key, icon, text, on_select=None, **kw):
        super().__init__(orientation="vertical", spacing=dp(1), size_hint=(1, 1), **kw)
        self.key = key
        self._cb = on_select

        cell = MDBoxLayout(size_hint_y=None, height=dp(38), pos_hint={"center_y": 0.42})
        self._cell = cell
        self.icon = MDIcon(icon=icon, theme_text_color="Custom",
                           text_color=S["onSurfaceVariant"], font_size=sp(24),
                           pos_hint={"center_x": 0.5, "center_y": 0.5})
        cell.add_widget(self.icon)
        self.add_widget(cell)

        self.txt = label(text, role="onSurfaceVariant", size=11, halign="center", wrap=False)
        self.txt.size_hint_y = None
        self.txt.height = dp(20)
        self.add_widget(self.txt)

        with self.canvas.before:
            Color(*S["secondaryContainer"])
            self._pill = RoundedRectangle(radius=[dp(16)] * 4, size=(dp(64), dp(32)))
            self._pill_size = (dp(64), dp(32))
        self._active = False
        self.bind(on_release=self._fire)
        self.bind(pos=self._draw, size=self._draw)

    def _fire(self, *a):
        if self._cb:
            self._cb(self.key)

    def _draw(self, *a):
        if hasattr(self, "_pill"):
            cx = self.center_x
            cy = self._cell.center_y if hasattr(self, "_cell") else self.center_y
            self._pill.pos = (cx - self._pill_size[0] / 2, cy - self._pill_size[1] / 2)

    def set_active(self, active):
        self._active = bool(active)
        c_on = S["onSecondaryContainer"]
        c_off = S["onSurfaceVariant"]
        self.icon.text_color = c_on if active else c_off
        self.txt.text_color = c_on if active else c_off
        self.txt.bold = bool(active)
        self._pill.pos = self._pill.pos if not active else self._pill.pos


class BottomNav(MDBoxLayout):
    ITEMS = [
        ("home", "home", "Home"),
        ("topup", "payments", "Top up"),
        ("tool", "language", "Tool"),
        ("settings", "settings", "Settings"),
    ]
    ADMIN_ITEM = ("admin", "shield-account", "Quản trị")

    def __init__(self, on_select=None, **kw):
        kw.setdefault("orientation", "horizontal")
        kw.setdefault("spacing", dp(4))
        super().__init__(**kw)
        self.size_hint_y = None
        self.height = dp(80)
        self._bottom_inset = 0
        self._on_select = on_select
        self._tabs = {}
        self._admin_tab = None
        for key, icon, text in self.ITEMS:
            self._add_tab(key, icon, text)
        with self.canvas.before:
            Color(*S["surfaceContainer"])
            self._bg = RoundedRectangle(radius=[dp(28), dp(28), 0, 0])
        self.bind(pos=self._draw, size=self._draw)
        self.bind(height=self._draw)
        self._draw()
        try:
            from kivy.core.window import Window
            Window.bind(safe_area=self._on_safe)
            self._on_safe(Window, Window.safe_area)
        except Exception:
            pass

    def _on_safe(self, win, safe):
        s = safe or [0, 0, 0, 0]
        # safe = [x, y, w, h]; chân nhúng = khoảng cách đáy cửa sổ tới đáy hệ điều hành
        bottom = 0
        if isinstance(s, (list, tuple)) and len(s) == 4:
            bottom = int(s[3]) if s[3] > 0 else int(s[1]) if s[1] > 0 else 0
        self._bottom_inset = bottom
        self.height = dp(80) + bottom

    def _add_tab(self, key, icon, text):
        t = NavItem(key, icon, text, on_select=self._on_select)
        self._tabs[key] = t
        self.add_widget(t)
        return t

    def set_admin(self, visible):
        if visible and self._admin_tab is None:
            self._admin_tab = self._add_tab(*self.ADMIN_ITEM)
        elif not visible and self._admin_tab is not None:
            try:
                self.remove_widget(self._admin_tab)
            except Exception:
                pass
            self._tabs.pop("admin", None)
            self._admin_tab = None

    def _draw(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def set_active(self, key):
        for k, t in self._tabs.items():
            t.set_active(k == key)

    def show(self, visible):
        self.height = (dp(80) + self._bottom_inset) if visible else 0
        self.opacity = 1.0 if visible else 0.0
        self.disabled = not visible