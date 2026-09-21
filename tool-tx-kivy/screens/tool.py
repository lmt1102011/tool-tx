# screens/tool.py — Màn Tool (M3): bảng phân tích dữ liệu + nút mở tool (fork).
from kivy.metrics import dp, sp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton, MDFillRoundFlatButton
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.screen import MDScreen

from core.m3 import S
from screens.uikit import label, Card, Panel, Spacer


class ToolScreen(MDScreen):
    def __init__(self, on_open=None, **kw):
        super().__init__(**kw)
        self.md_bg_color = (0, 0, 0, 0)
        self._on_open = on_open
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation="vertical")
        self.add_widget(root)

        bar = MDBoxLayout(orientation="horizontal", padding=[dp(4), dp(12), dp(12), 0],
                          size_hint_y=None, height=dp(64))
        back = MDIconButton(icon="arrow-left", icon_size=sp(28),
                            theme_icon_color="Custom", icon_color=S["onSurface"])
        back.bind(on_release=lambda *a: self.open_back())
        bar.add_widget(back)
        bar.add_widget(label("Tool", role="onSurface", size=22, bold=True))
        root.add_widget(bar)

        box = Panel(bg="surfaceContainerHighest", radius=28, padding=[dp(12), dp(14), dp(12), dp(14)],
                    width=dp(392), height=dp(684), auto=False, spacing=dp(14))
        box.size_hint_x = None
        box.pos_hint = {"center_x": 0.5}
        root.add_widget(box)

        # thẻ Data analysis table
        c1 = Card(kind="elevated", bg="surfaceContainerLow", radius=20, spacing=dp(10))
        c1.add_widget(label("Data analysis table", role="onSurface", size=16, bold=True))
        tbl = MDBoxLayout(orientation="vertical", spacing=dp(8),
                          size_hint=(None, None), width=dp(348), height=dp(212))
        from kivy.graphics import Color, RoundedRectangle
        with tbl.canvas.before:
            Color(*S["surfaceContainerHigh"])
            tbl._bg = RoundedRectangle(radius=[dp(7)] * 4)
        tbl.bind(pos=lambda *a: setattr(tbl._bg, "pos", tbl.pos),
                 size=lambda *a: setattr(tbl._bg, "size", tbl.size))
        tbl.pos_hint = {"center_x": 0.5}
        tbl.padding = [dp(14), dp(10), dp(14), dp(10)]
        tbl.spacing = dp(6)

        row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(54))
        self.big = label("--", role="onSurface", size=30, bold=True, halign="center")
        self.big.size_hint_x = 0.55
        self.pct = label("", role="onSurfaceVariant", size=13, bold=True, halign="right")
        row.add_widget(self.big)
        row.add_widget(self.pct)
        tbl.add_widget(row)

        self.pbar = MDProgressBar(value=50, size_hint_y=None, height=dp(8),
                                  color=S["primary"], back_color=(1, 1, 1, 0.1))
        tbl.add_widget(self.pbar)
        self.hist = label("chờ dữ liệu...", role="onSurfaceVariant", size=12, wrap=True)
        tbl.add_widget(self.hist)
        c1.add_widget(tbl)
        box.add_widget(c1)

        # thẻ Tool + nút mở
        c2 = Card(kind="elevated", bg="surfaceContainerLow", radius=20, spacing=dp(6))
        c2.add_widget(label("Tool", role="onSurface", size=16, bold=True))
        self.tool_body = label("open tab tool", role="onSurfaceVariant", size=13, wrap=True)
        c2.add_widget(self.tool_body)
        self.agent_lbl = label("Chưa có agent nào chạy.", role="onSurfaceVariant", size=12)
        c2.add_widget(self.agent_lbl)
        btn = MDFillRoundFlatButton(icon="power-settings-new", size_hint=(None, None),
                                    width=dp(344), height=dp(56),
                                    md_bg_color=S["primary"], text_color=S["onPrimary"],
                                    font_size=sp(15), pos_hint={"center_x": 0.5})
        btn.text = " Open Tool"
        btn.bind(on_release=lambda *a: self._open())
        c2.add_widget(btn)
        box.add_widget(c2)

        box.add_widget(Spacer(size_hint_y=(1, None), height=dp(6)))

    def open_back(self):
        try:
            from kivymd.app import MDApp
            MDApp.get_running_app().back()
        except Exception:
            pass

    def _open(self):
        if self._on_open:
            self._on_open()

    # ── API cho App ─────────────────────────────────────────────
    def prediction(self, p):
        p = p or {}
        if not p.get("pick"):
            return
        pk = str(p["pick"]).upper()
        is_t = pk == "T"
        self.big.text = "TÀI" if is_t else "XỈU"
        self.big.text_color = S["error"] if is_t else S["primary"]
        pT = float(p.get("pT") or (60 if is_t else 40))
        pX = 100 - pT
        self.pct.text = "TÀI %02.0f  /  XỈU %02.0f" % (pT, pX)
        self.pbar.value = min(100.0, max(0.0, pT))
        c = p.get("confidence", p.get("conf"))
        conf = "Độ tin cậy %02.0f%%" % float(c) if c is not None else ""
        hist = p.get("hist") or p.get("history") or []
        line = "   ".join(str(x)[:1].upper() for x in hist[-16:])
        self.hist.text = " | ".join([x for x in (conf, line) if x])

    def set_status(self, text, col=None):
        self.tool_body.text = text or "open tab tool"
        if col:
            self.tool_body.text_color = col
        else:
            self.tool_body.text_color = S["onSurfaceVariant"]

    def set_code(self, text):
        pass  # mã liên kết quá chi tiết, bỏ qua trên giao diện này

    def set_agent(self, text, col=None):
        self.agent_lbl.text = text or "Chưa có agent nào chạy."
        if col:
            self.agent_lbl.text_color = col
        else:
            self.agent_lbl.text_color = S["onSurfaceVariant"]