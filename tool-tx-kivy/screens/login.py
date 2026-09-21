# screens/login.py — Màn Sign In / Sign Up (M3): ảnh 124dp, panel bo 29dp, 2 field.
import os
from kivy.metrics import dp, sp
from kivy.uix.image import Image
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFillRoundFlatButton, MDTextButton
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.screen import MDScreen

from core.config import LOGO
from core.m3 import S
from screens.uikit import label, field, round_clip, Spacer


def _logo(size=dp(124)):
    b = MDBoxLayout(size_hint=(None, None), size=(size, size),
                    pos_hint={"center_x": 0.5})
    if os.path.exists(LOGO):
        img = Image(source=LOGO, keep_ratio=True, allow_stretch=True)
        round_clip(b, radius=dp(20))
        b.add_widget(img)
    else:
        b.md_bg_color = S["surfaceContainerHighest"]
    return b


class _AuthBase(MDScreen):
    """Chung: logo + 'Made By LMT' + panel giữa + liên kết đổi màn."""

    def __init__(self, on_goto=None, **kw):
        super().__init__(**kw)
        self.md_bg_color = (0, 0, 0, 0)
        self._on_goto = on_goto
        self._build()

    def _head(self, root):
        root.add_widget(Spacer(height=dp(8), size_hint_y=None))
        root.add_widget(_logo())
        root.add_widget(label("Made By LMT", role="onSurfaceVariant", size=12,
                              halign="center"))
        root.add_widget(Spacer(height=dp(18), size_hint_y=None))

    def _panel(self, root, title, width=dp(380), radius=dp(29)):
        p = MDBoxLayout(orientation="vertical", size_hint=(None, None),
                        width=width, pos_hint={"center_x": 0.5})
        self._panel = p
        self._radius = radius
        self._bg_role = "surfaceContainerHigh"
        self._panel_layout = None
        root.add_widget(p)
        return p

    def get_account(self):
        return (self.uname.text or "").strip()

    def get_password(self):
        return self.passw.text or ""

    def set_status(self, msg, err=False):
        if getattr(self, "status", None) is None:
            return
        self.status.text = msg or ""
        self.status.text_color = S["error"] if err else S["onSurfaceVariant"]

    def focus_first(self):
        try:
            self.uname.focus = True
        except Exception:
            pass


class SignInScreen(_AuthBase):
    def _build(self):
        from screens.uikit import Panel
        sc = MDScrollView(size_hint=(1, 1))
        col = MDBoxLayout(orientation="vertical", spacing=dp(6),
                          padding=[dp(16), dp(28), dp(16), dp(24)], size_hint_y=None)
        col.bind(minimum_height=col.setter("height"))
        sc.add_widget(col)
        self.add_widget(sc)

        self._head(col)
        p = Panel(bg="surfaceContainerHigh", radius=29, padding=[dp(20), dp(24), dp(20), dp(24)],
                  width=dp(380), spacing=dp(16))
        p.size_hint_x = None
        p.pos_hint = {"center_x": 0.5}
        col.add_widget(p)

        p.add_widget(label("Sign In", role="onSurface", size=28, bold=True, halign="center"))
        self.uname = field("Tên đăng nhập", leading="person")
        p.add_widget(self.uname)
        self.passw = field("Mật khẩu", leading="lock", password=True)
        p.add_widget(self.passw)
        self.status = label("", role="onSurfaceVariant", size=13, halign="center", wrap=True)
        p.add_widget(self.status)

        btn = MDFillRoundFlatButton(text="Sign In", size_hint=(1, None), height=dp(56),
                                    md_bg_color=S["primary"], text_color=S["onPrimary"],
                                    font_size=sp(16))
        btn.bind(on_release=lambda *a: self._submit())
        p.add_widget(btn)

        link = MDTextButton(text="Don't have an account? Sign Up",
                            theme_text_color="Custom", text_color=S["primary"],
                            font_size=sp(16), pos_hint={"center_x": 0.5},
                            size_hint_y=None, height=dp(32))
        link.bind(on_release=lambda *a: self._to("signup"))
        p.add_widget(link)

        col.add_widget(Spacer(height=dp(20), size_hint_y=None))

    def _to(self, name):
        if self._on_goto:
            self._on_goto(name)

    def _submit(self):
        if self._on_goto:
            self._on_goto("submit-signin")


class SignUpScreen(_AuthBase):
    def _build(self):
        from screens.uikit import Panel
        sc = MDScrollView(size_hint=(1, 1))
        col = MDBoxLayout(orientation="vertical", spacing=dp(6),
                          padding=[dp(16), dp(20), dp(16), dp(16)], size_hint_y=None)
        col.bind(minimum_height=col.setter("height"))
        sc.add_widget(col)
        self.add_widget(sc)

        self._head(col)
        p = Panel(bg="surfaceContainerHigh", radius=29, padding=[dp(20), dp(24), dp(20), dp(24)],
                  width=dp(380), spacing=dp(14))
        p.size_hint_x = None
        p.pos_hint = {"center_x": 0.5}
        col.add_widget(p)

        p.add_widget(label("Sign Up", role="onSurface", size=28, bold=True, halign="center"))
        self.uname = field("Tên đăng nhập", leading="person")
        p.add_widget(self.uname)
        self.passw = field("Mật khẩu", leading="lock", password=True)
        p.add_widget(self.passw)
        self.conf = field("Nhập lại mật khẩu", leading="lock", password=True)
        p.add_widget(self.conf)
        self.status = label("", role="onSurfaceVariant", size=13, halign="center", wrap=True)
        p.add_widget(self.status)

        btn = MDFillRoundFlatButton(text="Sign Up", size_hint=(1, None), height=dp(56),
                                    md_bg_color=S["primary"], text_color=S["onPrimary"],
                                    font_size=sp(16))
        btn.bind(on_release=lambda *a: self._submit())
        p.add_widget(btn)

        link = MDTextButton(text="Already have an account? Sign In",
                            theme_text_color="Custom", text_color=S["primary"],
                            font_size=sp(16), pos_hint={"center_x": 0.5},
                            size_hint_y=None, height=dp(32))
        link.bind(on_release=lambda *a: self._to("signin"))
        p.add_widget(link)

        col.add_widget(Spacer(height=dp(20), size_hint_y=None))

    def _to(self, name):
        if self._on_goto:
            self._on_goto(name)

    def _submit(self):
        if self._on_goto:
            self._on_goto("submit-signup")