from kivy.metrics import dp, sp
from kivy.uix.widget import Widget
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton, MDFillRoundFlatButton
from kivymd.uix.label import MDIcon
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.card import MDCard
from kivymd.uix.screen import MDScreen

from core.m3 import S
from screens.uikit import t, spacer, PAD


class ToolScreen(MDScreen):
    def __init__(self, on_open=None, **kw):
        super().__init__(**kw)
        self._on_open = on_open
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation="vertical", padding=0, spacing=0)
        self.add_widget(root)

        bar = MDBoxLayout(orientation="horizontal", padding=[dp(4), dp(12), dp(12), 0],
                          size_hint_y=None, height=dp(64), spacing=dp(8))
        back = MDIconButton(icon="arrow-left", icon_size=sp(24),
                            theme_icon_color="Custom", icon_color=S["onSurface"])
        back.bind(on_release=lambda *a: self.open_back())
        bar.add_widget(back)
        bar.add_widget(t("Tool", size=22, bold=True, role="onSurface"))
        root.add_widget(bar)

        body = MDBoxLayout(orientation="vertical", spacing=dp(16),
                           padding=[PAD, dp(8), PAD, dp(8)])
        root.add_widget(body)

        c1 = MDCard(style="elevated", radius=[dp(20)] * 4,
                    padding=[dp(16), dp(16)], spacing=dp(10),
                    orientation="vertical", size_hint_y=None, adaptive_height=True)
        c1.add_widget(t("Data analysis table", size=16, bold=True, role="onSurface"))

        tbl = MDCard(radius=[dp(12)] * 4, size_hint_y=None, height=dp(200),
                     padding=[dp(16), dp(12)], spacing=dp(8),
                     orientation="vertical",
                     md_bg_color=S["surfaceContainerHigh"])
        row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(54))
        self.big = t("--", size=30, bold=True, role="onSurface", halign="center")
        self.big.size_hint_x = 0.55
        self.pct = t("", size=13, bold=True, role="onSurfaceVariant", halign="right")
        self.pct.size_hint_x = 0.45
        row.add_widget(self.big)
        row.add_widget(self.pct)
        tbl.add_widget(row)

        self.pbar = MDProgressBar(value=50, size_hint_y=None, height=dp(8),
                                  color=S["primary"], back_color=(1, 1, 1, 0.1))
        tbl.add_widget(self.pbar)
        self.hist = t("cho du lieu...", size=12, role="onSurfaceVariant", wrap=True)
        tbl.add_widget(self.hist)
        c1.add_widget(tbl)
        body.add_widget(c1)

        c2 = MDCard(style="elevated", radius=[dp(20)] * 4,
                    padding=[dp(16), dp(16)], spacing=dp(8),
                    orientation="vertical", size_hint_y=None, adaptive_height=True)
        c2.add_widget(t("Tool", size=16, bold=True, role="onSurface"))
        self.tool_body = t("open tab tool", size=13, role="onSurfaceVariant", wrap=True)
        c2.add_widget(self.tool_body)
        self.agent_lbl = t("Chua co agent nao chay.", size=12, role="onSurfaceVariant")
        c2.add_widget(self.agent_lbl)
        c2.add_widget(spacer(4))
        btn = MDFillRoundFlatButton(text="  Open Tool", icon="power-settings-new",
                                    size_hint=(1, None), height=dp(56),
                                    md_bg_color=S["primary"], text_color=S["onPrimary"],
                                    font_size=sp(15))
        btn.bind(on_release=lambda *a: self._open())
        c2.add_widget(btn)
        body.add_widget(c2)
        body.add_widget(Widget())

    def open_back(self):
        try:
            from kivymd.app import MDApp
            MDApp.get_running_app().back()
        except Exception:
            pass

    def _open(self):
        if self._on_open:
            self._on_open()

    def prediction(self, p):
        p = p or {}
        if not p.get("pick"):
            return
        pk = str(p["pick"]).upper()
        is_t = pk == "T"
        self.big.text = "TAI" if is_t else "XIU"
        self.big.text_color = S["error"] if is_t else S["primary"]
        pT = float(p.get("pT") or (60 if is_t else 40))
        pX = 100 - pT
        self.pct.text = "TAI %02.0f  /  XIU %02.0f" % (pT, pX)
        self.pbar.value = min(100.0, max(0.0, pT))
        c = p.get("confidence", p.get("conf"))
        conf = "Do tin cay %02.0f%%" % float(c) if c is not None else ""
        hist = p.get("hist") or p.get("history") or []
        line = "   ".join(str(x)[:1].upper() for x in hist[-16:])
        self.hist.text = " | ".join([x for x in (conf, line) if x])

    def set_status(self, text, col=None):
        self.tool_body.text = text or "open tab tool"
        self.tool_body.text_color = col if col else S["onSurfaceVariant"]

    def set_agent(self, text, col=None):
        self.agent_lbl.text = text or "Chua co agent nao chay."
        self.agent_lbl.text_color = col if col else S["onSurfaceVariant"]
