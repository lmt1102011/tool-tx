import os
from kivy.metrics import dp, sp
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.label import MDIcon
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard

from core.m3 import S
from core.config import LOGO
from screens.uikit import t, spacer, PAD


class HomeScreen(MDScreen):
    def __init__(self, on_profile=None, **kw):
        super().__init__(**kw)
        self._on_profile = on_profile
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation="vertical", padding=0, spacing=0)
        self.add_widget(root)

        bar = MDBoxLayout(orientation="horizontal", padding=[dp(12), dp(14), dp(16), dp(8)],
                          size_hint_y=None, height=dp(64), spacing=dp(8))
        btn = MDIconButton(icon="account-circle", icon_size=sp(30),
                           theme_icon_color="Custom", icon_color=S["onSurfaceVariant"])
        btn.bind(on_release=lambda *a: self._on_profile() if self._on_profile else None)
        bar.add_widget(btn)
        self.name_lbl = t("Name", size=22, bold=True, role="onSurface")
        bar.add_widget(self.name_lbl)
        bar.add_widget(Widget())

        chip = MDCard(style="filled", radius=[dp(18)] * 4,
                      size_hint=(None, None), size=(dp(140), dp(36)),
                      padding=[dp(8), dp(4)], spacing=dp(4),
                      md_bg_color=S["secondaryContainer"],
                      orientation="horizontal")
        ic = MDIcon(icon="credit-card", font_size=sp(16), size_hint_x=None, width=dp(22),
                    pos_hint={"center_y": 0.5})
        ic.theme_text_color = "Custom"
        ic.text_color = S["onSecondaryContainer"]
        chip.add_widget(ic)
        self.credit_lbl = t("Credit: --", size=13, bold=True, role="onSecondaryContainer")
        chip.add_widget(self.credit_lbl)
        bar.add_widget(chip)
        root.add_widget(bar)

        body = MDBoxLayout(orientation="vertical", spacing=dp(16),
                           padding=[PAD, dp(8), PAD, dp(8)])
        root.add_widget(body)

        c1 = MDCard(style="elevated", radius=[dp(20)] * 4,
                    size_hint_y=None, height=dp(300),
                    padding=0, spacing=0, orientation="vertical")
        hero = MDBoxLayout(size_hint_y=None, height=dp(200))
        if os.path.exists(LOGO):
            hero.add_widget(Image(source=LOGO, keep_ratio=True, allow_stretch=True))
        else:
            hero.md_bg_color = S["surfaceContainerHighest"]
        c1.add_widget(hero)
        txt_box = MDBoxLayout(orientation="vertical", padding=[dp(20), dp(16)],
                              spacing=dp(4), size_hint_y=None, height=dp(100))
        txt_box.add_widget(t("Tool Made By LMT", size=16, bold=True, role="onSurface"))
        txt_box.add_widget(t("A tool specifically designed for in-depth probabilistic data analysis.",
                             size=13, role="onSurfaceVariant", wrap=True))
        c1.add_widget(txt_box)
        body.add_widget(c1)

        c2 = MDCard(style="elevated", radius=[dp(20)] * 4,
                    size_hint_y=None, height=dp(80),
                    padding=[dp(20), dp(16)], spacing=dp(4),
                    orientation="vertical")
        c2.add_widget(t("Server", size=16, bold=True, role="onSurface"))
        self.server_lbl = t("Server is off", size=13, role="onSurfaceVariant")
        c2.add_widget(self.server_lbl)
        body.add_widget(c2)

        self.gate_txt = t("", size=13, role="error", halign="center", wrap=True)
        self.gate_txt.opacity = 0
        self.gate_txt.size_hint_y = None
        self.gate_txt.height = 0
        body.add_widget(self.gate_txt)

        body.add_widget(Widget())

    def greet(self, name):
        self.name_lbl.text = name or "Name"

    def credit(self, txt, warn=False):
        self.credit_lbl.text = "Credit: " + (txt or "--")
        self.credit_lbl.text_color = S["error"] if warn else S["onSecondaryContainer"]

    def server(self, text, ok=False, warn=False):
        self.server_lbl.text = text or "Server is off"
        self.server_lbl.text_color = S["primary"] if ok else (
            S["onSurfaceVariant"] if not warn else S["error"])

    def gate(self, msg):
        if msg:
            self.gate_txt.text = msg
            self.gate_txt.opacity = 1
            self.gate_txt.height = dp(48)
        else:
            self.gate_txt.text = ""
            self.gate_txt.opacity = 0
            self.gate_txt.height = 0
