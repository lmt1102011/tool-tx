from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDIcon, MDLabel
from core.m3 import S


class NavItem(ButtonBehavior, MDBoxLayout):
    def __init__(self, icon, label_text="", index=0, on_select=None, **kw):
        super().__init__(orientation="vertical", spacing=dp(4),
                         size_hint=(1, 1), padding=[0, dp(4), 0, dp(4)], **kw)
        self._idx = index
        self._cb = on_select
        self._sel = False

        self._ic = MDIcon(icon=icon, font_size=sp(26),
                          size_hint=(1, None), height=dp(28),
                          halign="center", valign="top")
        self._ic.theme_text_color = "Custom"
        self._ic.text_color = S["onSurfaceVariant"]
        self.add_widget(self._ic)

        self._lbl = MDLabel(text=label_text, font_size=sp(12),
                            size_hint=(1, None), height=dp(20),
                            halign="center", valign="top")
        self._lbl.theme_text_color = "Custom"
        self._lbl.text_color = S["onSurfaceVariant"]
        self.add_widget(self._lbl)

        self.bind(on_release=lambda *a: self._cb() if self._cb else None)

    def set_selected(self, v):
        self._sel = v
        ic_color = S["secondaryContainer"] if v else S["onSurfaceVariant"]
        lbl_color = S["secondaryContainer"] if v else S["onSurfaceVariant"]
        self._ic.icon = self._ic.icon  # force refresh
        self._ic.text_color = ic_color
        self._lbl.text_color = lbl_color

    def update_colors(self):
        self._ic.text_color = S["secondaryContainer"] if self._sel else S["onSurfaceVariant"]
        self._lbl.text_color = S["secondaryContainer"] if self._sel else S["onSurfaceVariant"]


class BottomNav(MDBoxLayout):
    def __init__(self, items=None, on_select=None, **kw):
        super().__init__(orientation="horizontal", size_hint=(1, None), height=dp(80),
                         padding=[dp(12), dp(8), dp(12), dp(8)], spacing=dp(8), **kw)
        self.md_bg_color = S["surfaceContainer"]
        with self.canvas.before:
            Color(*S["surfaceContainer"])
            self._bg = RoundedRectangle(size=self.size, pos=self.pos,
                                         radius=[dp(0)] * 4)
        self.bind(pos=lambda i, *a: setattr(self._bg, "pos", i.pos),
                  size=lambda i, *a: setattr(self._bg, "size", i.size))
        self._items = []
        self._selected = 0

        for i, (ic, txt) in enumerate(items or []):
            ni = NavItem(ic, txt, index=i, on_select=lambda idx=i: self.select(idx))
            self.add_widget(ni)
            self._items.append(ni)

        self.select(0)

    def select(self, idx):
        self._selected = idx
        for i, ni in enumerate(self._items):
            ni.set_selected(i == idx)

    def update_colors(self):
        for ni in self._items:
            ni.update_colors()
        with self.canvas.before:
            from kivy.graphics import Color
            Color(*S["surfaceContainer"])
            self._bg.pos = self.pos
            self._bg.size = self.size
