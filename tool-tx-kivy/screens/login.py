# screens/login.py — đăng nhập / đăng ký (Firebase Auth REST qua AuthManager).
from kivy.metrics import dp, sp
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDFillRoundFlatButton, MDTextButton
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.screen import MDScreen

from core.config import GOLD, DIM, NIGHT, TXT, RED_T
from screens.uikit import label, GlassCard, Column


class LoginScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.md_bg_color = (0, 0, 0, 0)
        self.mode = "login"
        self._build()

    def _build(self):
        sc = MDScrollView(size_hint=(1, 1))
        col = Column(spacing=dp(16), padding=[dp(24), dp(52), dp(24), dp(24)])
        sc.add_widget(col)
        self.add_widget(sc)

        col.add_widget(label("TOOLTX", style="H4", color=GOLD, size=34,
                             halign="center", bold=True))
        col.add_widget(label("Dự đoán Tài/Xỉu tự động · Gold edition",
                             color=DIM, size=13, halign="center"))

        card = GlassCard(spacing=dp(14), padding=[dp(18), dp(22), dp(18), dp(18)])
        col.add_widget(card)

        self.title = label("ĐĂNG NHẬP", style="H6", color=GOLD, halign="center", bold=True)
        card.add_widget(self.title)

        self.name_field = MDTextField(hint_text="Tên hiển thị", mode="rectangle",
                                      size_hint=(1, None), height=dp(54),
                                      font_size=sp(16), hint_text_color_normal=DIM)
        card.add_widget(self.name_field)

        self.uname_field = MDTextField(hint_text="Tên đăng nhập", mode="rectangle",
                                       size_hint=(1, None), height=dp(54),
                                       font_size=sp(16), hint_text_color_normal=DIM)
        card.add_widget(self.uname_field)

        self.pass_field = MDTextField(hint_text="Mật khẩu", mode="rectangle",
                                      password=True, size_hint=(1, None),
                                      height=dp(54), font_size=sp(16),
                                      hint_text_color_normal=DIM)
        card.add_widget(self.pass_field)

        self.status = label("", wrap=True)
        self.status.text_color = DIM
        card.add_widget(self.status)

        self.btn = MDFillRoundFlatButton(text="VÀO TOOLTX", size_hint=(1, None),
                                         height=dp(52), md_bg_color=GOLD,
                                         text_color=NIGHT, font_size=sp(16))
        self.btn.bind(on_release=lambda *a: self._submit())
        card.add_widget(self.btn)

        self.toggle = MDTextButton(text="Chưa có tài khoản? Đăng ký",
                                   theme_text_color="Custom", text_color=GOLD,
                                   font_size=sp(13), pos_hint={"center_x": 0.5},
                                   size_hint_y=None, height=dp(30))
        self.toggle.bind(on_release=lambda *a: self._toggle_mode())
        card.add_widget(self.toggle)

        self._apply_mode()
        self.set_status("")

    def _apply_mode(self):
        reg = self.mode == "register"
        self.title.text = "ĐĂNG KÝ TÀI KHOẢN" if reg else "ĐĂNG NHẬP"
        self.name_field.height = dp(54) if reg else 0
        self.name_field.opacity = 1 if reg else 0
        self.name_field.disabled = not reg
        self.btn.text = "TẠO TÀI KHOẢN" if reg else "VÀO TOOLTX"
        self.toggle.text = "Đã có tài khoản? Đăng nhập" if reg else "Chưa có tài khoản? Đăng ký"
        self.status.text = ""

    def _toggle_mode(self):
        self.mode = "register" if self.mode == "login" else "login"
        self._apply_mode()

    def _submit(self):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        u = (self.uname_field.text or "").strip()
        p = self.pass_field.text or ""
        if self.mode == "login":
            self.set_status("Đang đăng nhập...")
            app.do_login(u, p)
        else:
            d = (self.name_field.text or "").strip()
            self.set_status("Đang tạo tài khoản...")
            app.do_register(u, p, d)

    def set_status(self, msg, err=False):
        self.status.text = msg
        self.status.text_color = RED_T if err else DIM