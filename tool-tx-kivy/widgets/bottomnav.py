# widgets/bottomnav.py — thanh điều hướng dưới (3 tab, gold khi active).
from kivy.metrics import dp, sp
from kivy.graphics import Color, Rectangle, Line
from kivy.uix.behaviors.button import ButtonBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDIcon

from core.config import GOLD, DIM, NIGHT, GOLD_DIM
from screens.uikit import label


class NavTab(ButtonBehavior, MDBoxLayout):
    def __init__(self, key, icon, text, on_select=None, **kw):
        super().__init__(orientation="vertical", spacing=dp(2), size_hint=(1, 1), **kw)
        self.key = key
        self._cb = on_select
        dot = MDIcon(icon=icon, font_size=sp(20), theme_text_color="Custom",
                     text_color=DIM, size_hint=(None, None), size=(dp(24), dp(26)),
                     pos_hint={"center_x": 0.5})
        dot.text_size = (dp(24), None)
        txt = label(text, style="Caption", color=DIM, size=11, halign="center")
        self.icon = dot
        self.txt = txt
        self.add_widget(dot)
        self.add_widget(txt)
        self.bind(on_release=self._fire)

    def _fire(self, *a):
        if self._cb:
            self._cb(self.key)

    def set_active(self, active):
        c = GOLD if active else DIM
        self.icon.text_color = c
        self.txt.text_color = c
        self.txt.bold = bool(active)


class BottomNav(MDBoxLayout):
    ITEMS = [
        ("home", "home", "Trang chủ"),
        ("browser", "web", "Trình duyệt"),
        ("settings", "cog", "Cài đặt"),
    ]

    def __init__(self, on_select=None, height=dp(62), **kw):
        super().__init__(orientation="horizontal", spacing=dp(6), padding=[dp(10), dp(8), dp(10), dp(6)], **kw)
        self.size_hint_y = None
        self.height = height
        self._tabs = {}
        for key, icon, text in self.ITEMS:
            t = NavTab(key, icon, text, on_select=on_select)
            self._tabs[key] = t
            self.add_widget(t)
        with self.canvas.before:
            Color(*NIGHT)
            self._bg = Rectangle()
            Color(*GOLD_DIM)
            self._top = Line(points=[], width=dp(1.2))
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    def _draw(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        if hasattr(self, "_top"):
            self._top.points = [self.x, self.top, self.right, self.top]

    def set_active(self, key):
        for k, t in self._tabs.items():
            t.set_active(k == key)

    def show(self, visible):
        self.height = dp(62) if visible else 0
        self.opacity = 1.0 if visible else 0.0
        self.disabled = not visible