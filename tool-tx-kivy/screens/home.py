# screens/home.py — Màn Home (M3): top app bar, chip Credit, box 392, 2 thẻ.
import os
from kivy.metrics import dp, sp
from kivy.uix.image import Image
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.screen import MDScreen

from core.config import LOGO
from core.m3 import S
from screens.uikit import (label, Card, Panel, Chip, Spacer, round_clip)


class HomeScreen(MDScreen):
    def __init__(self, on_profile=None, **kw):
        super().__init__(**kw)
        self.md_bg_color = (0, 0, 0, 0)
        self._on_profile = on_profile
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation="vertical")
        sc = MDScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=False)
        sc.add_widget(root)
        self.add_widget(sc)

        # top app bar 64dp: account_circle + tiêu đề "Name"; chip Credit phải
        top = MDBoxLayout(orientation="horizontal", padding=[dp(8), dp(14), dp(8), 0],
                          size_hint_y=None, height=dp(64))
        self.btn_profile = MDIconButton(icon="account-circle", icon_size=sp(30),
                                        theme_icon_color="Custom",
                                        icon_color=S["onSurfaceVariant"])
        self.btn_profile.bind(on_release=lambda *a: self._on_profile() if self._on_profile else None)
        top.add_widget(self.btn_profile)
        self.name_lbl = label("Name", role="onSurface", size=22, bold=True)
        top.add_widget(self.name_lbl)

        row = MDBoxLayout(orientation="vertical", padding=[0, dp(6), dp(16), 0],
                          size_hint_x=None, width=dp(190))
        row.add_widget(self._credit_chip())
        top.add_widget(row)
        root.add_widget(top)

        # box trung tâm 392 + 2 thẻ
        box = Panel(bg="surfaceContainerHighest", radius=28, padding=[dp(10), dp(16), dp(10), dp(16)],
                    width=dp(392), height=dp(648), auto=False, spacing=dp(14))
        box.size_hint_x = None
        box.pos_hint = {"center_x": 0.5}
        root.add_widget(box)

        card1 = Card(kind="elevated", bg="surfaceContainerLow", radius=20,
                     padding=[0, 0, 0, dp(16)], spacing=dp(4))
        self._hero_pic = MDBoxLayout(size_hint=(1, None), height=dp(218))
        if os.path.exists(LOGO):
            img = Image(source=LOGO, keep_ratio=True, allow_stretch=True)
            round_clip(self._hero_pic, radius=dp(20))
            self._hero_pic.add_widget(img)
        else:
            self._hero_pic.md_bg_color = S["surfaceContainerHighest"]
        card1.add_widget(self._hero_pic)
        hp = MDBoxLayout(orientation="vertical", padding=[dp(20), 0, dp(20), 0], spacing=dp(4))
        hp.add_widget(label("Tool Made By LMT", role="onSurface", size=16, bold=True))
        hp.add_widget(label("A tool specifically designed for in-depth probabilistic data analysis.",
                            role="onSurfaceVariant", size=14, wrap=True, line_h=1.4))
        card1.add_widget(hp)
        box.add_widget(card1)

        card2 = Card(kind="elevated", bg="surfaceContainerLow", radius=20,
                     height=dp(96), auto=False, spacing=dp(4))
        card2.add_widget(label("Server", role="onSurface", size=16, bold=True))
        self.server_lbl = label("Server is off", role="onSurfaceVariant", size=14, wrap=True)
        card2.add_widget(self.server_lbl)
        box.add_widget(card2)

        # cảnh báo hết lượt (nếu có)
        self.gate_txt = label("", role="error", size=13, wrap=True, halign="center")
        self.gate_txt.opacity = 0
        self.gate_txt.height = dp(0)
        box.add_widget(self.gate_txt)
        box.add_widget(Spacer(size_hint_y=(1, None), height=dp(6)))

    def _credit_chip(self):
        c = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(36),
                        padding=[dp(8), 0, dp(12), 0], spacing=dp(6),
                        pos_hint={"center_x": 1.0})
        from kivy.graphics import Color, RoundedRectangle
        with c.canvas.before:
            Color(*S["secondaryContainer"])
            c._bg = RoundedRectangle(radius=[dp(18)] * 4)
        c.bind(pos=lambda *a: setattr(c._bg, "pos", c.pos),
               size=lambda *a: setattr(c._bg, "size", c.size))
        from kivymd.uix.label import MDIcon
        ic = MDIcon(icon="credit-card", theme_text_color="Custom",
                    text_color=S["onSecondaryContainer"], font_size=sp(18),
                    size_hint_x=None, width=dp(24))
        c.add_widget(ic)
        self.credit_lbl = label("Credit: --", role="onSecondaryContainer", size=13,
                                bold=True, halign="left")
        c.add_widget(self.credit_lbl)
        return c

    # ── API cho App ─────────────────────────────────────────────
    def greet(self, name):
        self.name_lbl.text = name or "Name"

    def credit(self, txt, warn=False):
        self.credit_lbl.text = "Credit: " + (txt or "--")
        self.credit_lbl.text_color = S["error"] if warn else S["onSecondaryContainer"]

    def server(self, text, ok=False, warn=False):
        self.server_lbl.text = text or "Server is off"
        self.server_lbl.text_color = S["primary"] if ok else (
            S["onSurfaceVariant"] if not warn else S["error"])

    def agent(self, text, col=None):
        pass  # hiện thị agent nằm ở màn Tool

    def gate(self, msg):
        if msg:
            self.gate_txt.text = msg
            self.gate_txt.opacity = 1
            self.gate_txt.height = dp(48)
        else:
            self.gate_txt.text = ""
            self.gate_txt.opacity = 0
            self.gate_txt.height = dp(0)

    def prediction(self, p):
        pass  # bảng dữ liệu nằm ở màn Tool (screens/tool.py)