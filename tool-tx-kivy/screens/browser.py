# screens/browser.py — màn hình trình duyệt tự động (agent/CDP).
from kivy.metrics import dp, sp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFillRoundFlatButton, MDRoundFlatButton
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.screen import MDScreen

from core.config import GOLD, GOLD_DIM, DIM, TXT, NIGHT, GREEN, WARN, IS_ANDROID
from screens.uikit import label, GlassCard, Column


class BrowserScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.md_bg_color = (0, 0, 0, 0)
        self._build()

    def _build(self):
        sc = MDScrollView(size_hint=(1, 1))
        col = Column(spacing=dp(14), padding=[dp(18), dp(24), dp(18), dp(16)])
        sc.add_widget(col)
        self.add_widget(sc)

        col.add_widget(label("Trình duyệt tự động", style="H5", color=GOLD,
                             size=24, bold=True))
        if IS_ANDROID:
            col.add_widget(label("Agent chơi game giúp bạn trong tab Chromium Fork "
                                 "trên điện thoại.",
                                 wrap=True, color=DIM, size=13))
        else:
            col.add_widget(label("Agent chạy game giúp bạn qua Chromium Fork "
                                 "(điện thoại) hoặc Chrome CDP (máy tính).",
                                 wrap=True, color=DIM, size=13))

        card = GlassCard(spacing=dp(14))
        col.add_widget(card)
        card.add_widget(label("KHỞI ĐỘNG", style="Overline", color=GOLD_DIM,
                              size=12, bold=True))

        self.btn_fork = MDFillRoundFlatButton(text="START BROWSER",
                                              size_hint=(1, None), height=dp(54),
                                              md_bg_color=GOLD, text_color=NIGHT,
                                              font_size=sp(15))
        self.btn_fork.bind(on_release=lambda *a: self._start("fork"))
        card.add_widget(self.btn_fork)

        if not IS_ANDROID:
            self.btn_chrome = MDRoundFlatButton(text="CHROME MÁY BẠN (MÁY TÍNH)",
                                                size_hint=(1, None), height=dp(50),
                                                md_bg_color=(0, 0, 0, 0),
                                                line_color=GOLD_DIM, text_color=GOLD,
                                                font_size=sp(14))
            self.btn_chrome.bind(on_release=lambda *a: self._start("chrome"))
            card.add_widget(self.btn_chrome)

        self.status = label("Trạng thái: chưa khởi động", wrap=True, size=14)
        card.add_widget(self.status)
        self.code = label("Mã liên kết: ---", wrap=True, color=DIM, size=12)
        card.add_widget(self.code)

        guide = GlassCard(spacing=dp(8), padding=[dp(16), dp(14), dp(16), dp(14)])
        col.add_widget(guide)
        guide.add_widget(label("HƯỚNG DẪN NHANH", style="Overline", color=GOLD_DIM,
                               size=12, bold=True))
        steps = [
            "1. Bấm START BROWSER để mở Chromium Fork.",
            "2. Đăng nhập tài khoản trong tab vừa mở như web.",
            "3. Agent tự chọn cửa theo dữ liệu tool, server trừ đúng lượt.",
        ]
        if not IS_ANDROID:
            steps.append("4. Trên máy tính dùng CHROME MÁY BẠN — nối CDP tại máy.")
        for line in steps:
            guide.add_widget(label(line, wrap=True, color=TXT, size=13))

        state = GlassCard(spacing=dp(10), padding=[dp(16), dp(14), dp(16), dp(14)])
        col.add_widget(state)
        state.add_widget(label("AGENT HIỆN TẠI", style="Overline", color=GOLD_DIM,
                               size=12, bold=True))
        self.agent_line = label("Chưa có agent nào chạy.", wrap=True, color=DIM, size=13)
        state.add_widget(self.agent_line)

        col.add_widget(MDBoxLayout(size_hint_y=None, height=dp(10)))

    def _start(self, which):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        if which == "fork":
            app.start_fork()
        else:
            app.start_agent()

    # ── API cho App ─────────────────────────────────────────────
    def set_status(self, text, col=DIM):
        self.status.text = text
        self.status.text_color = col

    def set_code(self, text):
        self.code.text = "Mã liên kết: " + (text or "---")

    def set_agent(self, text, col=DIM):
        self.agent_line.text = text
        self.agent_line.text_color = col