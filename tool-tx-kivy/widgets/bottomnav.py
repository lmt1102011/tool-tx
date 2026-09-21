from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDIcon, MDLabel
from core.m3 import S

NAV_NAMES = ["home", "topup", "tool", "settings"]
NAV_ITEMS = [
    ("home", "home", "Home"),
    ("credit-card", "credit-card", "Top Up"),
    ("wrench", "wrench", "Tool"),
    ("cog", "cog", "Settings"),
]


class NavItem(ButtonBehavior, MDBoxLayout):
    def __init__(self, icon, label_text="", nav_name="", on_tap=None, **kw):
        super().__init__(orientation="vertical", spacing=dp(2),
                         size_hint=(1, 1), padding=[0, dp(6), 0, dp(6)], **kw)
        self._name = nav_name
        self._on_tap = on_tap
        self._sel = False

        self._pill_wrap = MDBoxLayout(size_hint=(None, None), size=(dp(64), dp(32)),
                                       pos_hint={"center_x": 0.5})
        with self._pill_wrap.canvas.before:
            self._pill_color = Color(*S["secondaryContainer"])
            self._pill = RoundedRectangle(size=self._pill_wrap.size,
                                           pos=self._pill_wrap.pos,
                                           radius=[dp(16)] * 4)
        self._pill_color.a = 0
        self._pill_wrap.bind(
            pos=lambda i, *a: setattr(self._pill, "pos", i.pos),
            size=lambda i, *a: setattr(self._pill, "size", i.size))
        self._pill_wrap.opacity = 1

        self._ic = MDIcon(icon=icon, font_size=sp(24),
                          size_hint=(1, None), height=dp(28),
                          halign="center", valign="middle")
        self._ic.theme_text_color = "Custom"
        self._ic.text_color = S["onSurfaceVariant"]
        self._pill_wrap.add_widget(self._ic)
        self.add_widget(self._pill_wrap)

        self._lbl = MDLabel(text=label_text, font_size=sp(12),
                            size_hint=(1, None), height=dp(20),
                            halign="center", valign="top")
        self._lbl.theme_text_color = "Custom"
        self._lbl.text_color = S["onSurfaceVariant"]
        self.add_widget(self._lbl)

        self.bind(on_release=lambda *a: self._on_tap(self._name) if self._on_tap else None)

    def set_selected(self, v):
        self._sel = v
        self._pill_color.a = 1 if v else 0
        c = S["onSecondaryContainer"] if v else S["onSurfaceVariant"]
        self._ic.text_color = c
        self._lbl.text_color = c
        self._lbl.bold = v


class BottomNav(MDBoxLayout):
    def __init__(self, items=None, on_select=None, **kw):
        super().__init__(orientation="horizontal", size_hint=(1, None), height=dp(80),
                         padding=[dp(8), dp(4), dp(8), dp(4)], spacing=0, **kw)
        self.md_bg_color = S["surfaceContainer"]
        with self.canvas.before:
            Color(*S["surfaceContainer"])
            self._bg = RoundedRectangle(size=self.size, pos=self.pos,
                                         radius=[dp(0)] * 4)
        self.bind(pos=lambda i, *a: setattr(self._bg, "pos", i.pos),
                  size=lambda i, *a: setattr(self._bg, "size", i.size))
        self._items = []
        self._selected = ""
        self._on_select = on_select

        for ic, _, txt in NAV_ITEMS:
            ni = NavItem(ic, txt, nav_name=NAV_ITEMS[len(self._items)][0],
                         on_tap=self._item_tap)
            self.add_widget(ni)
            self._items.append(ni)

    def _item_tap(self, name):
        if self._on_select:
            try:
                self._on_select(name)
            except Exception:
                pass

    def _highlight(self, name):
        self._selected = name
        for ni in self._items:
            ni.set_selected(ni._name == name)

    def select(self, name):
        if isinstance(name, int):
            name = NAV_NAMES[name] if name < len(NAV_NAMES) else "home"
        self._highlight(name)

    def set_active(self, name):
        if name:
            self._highlight(name)

    def show(self, v):
        self.opacity = 1 if v else 0
        self.height = dp(80) if v else dp(0)
        self.size_hint_y = 1 if v else None

    def update_colors(self):
        self._highlight(self._selected)
        with self.canvas.before:
            from kivy.graphics import Color
            Color(*S["surfaceContainer"])
            self._bg.pos = self.pos
            self._bg.size = self.size

    def set_admin(self, v):
        pass
