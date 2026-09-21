from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDIcon, MDLabel
from core.m3 import S

NAV_NAMES = ["home", "topup", "tool", "settings"]


class NavItem(ButtonBehavior, MDBoxLayout):
    def __init__(self, icon, label_text="", index=0, on_tap=None, **kw):
        super().__init__(orientation="vertical", spacing=dp(4),
                         size_hint=(1, 1), padding=[0, dp(4), 0, dp(4)], **kw)
        self._idx = index
        self._on_tap = on_tap
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

        self.bind(on_release=lambda *a: self._on_tap(self._idx) if self._on_tap else None)

    def set_selected(self, v):
        self._sel = v
        c = S["secondaryContainer"] if v else S["onSurfaceVariant"]
        self._ic.text_color = c
        self._lbl.text_color = c


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
        self._on_select = on_select

        for i, (ic, txt) in enumerate(items or []):
            ni = NavItem(ic, txt, index=i, on_tap=self._item_tap)
            self.add_widget(ni)
            self._items.append(ni)

        self._highlight(0)

    def _item_tap(self, idx):
        self._highlight(idx)
        if self._on_select:
            try:
                self._on_select(NAV_NAMES[idx] if idx < len(NAV_NAMES) else idx)
            except Exception:
                pass

    def _highlight(self, idx):
        self._selected = idx
        for i, ni in enumerate(self._items):
            ni.set_selected(i == idx)

    def select(self, idx):
        if isinstance(idx, str):
            idx = NAV_NAMES.index(idx) if idx in NAV_NAMES else 0
        self._highlight(idx)

    def set_active(self, name):
        if name in NAV_NAMES:
            self._highlight(NAV_NAMES.index(name))

    def show(self, v):
        self.opacity = 1 if v else 0
        self.height = dp(80) if v else dp(0)

    def update_colors(self):
        self._highlight(self._selected)
        with self.canvas.before:
            from kivy.graphics import Color
            Color(*S["surfaceContainer"])
            self._bg.pos = self.pos
            self._bg.size = self.size

    def set_admin(self, v):
        pass
