from kivy.metrics import dp, sp
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFillRoundFlatButton, MDTextButton
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard

from core.m3 import S
from screens.uikit import t, spacer, field, PAD


def _logo(size=dp(100)):
    box = MDBoxLayout(size_hint=(None, None), size=(size, size),
                      pos_hint={"center_x": 0.5})
    import os
    from core.config import LOGO
    if os.path.exists(LOGO):
        from kivy.graphics import StencilPush, StencilPop
        with box.canvas.before:
            StencilPush()
        img = Image(source=LOGO, keep_ratio=True, allow_stretch=True)
        box.add_widget(img)
        with box.canvas.after:
            StencilPop()
    else:
        box.md_bg_color = S["surfaceContainerHighest"]
    return box


class SignInScreen(MDScreen):
    def __init__(self, on_goto=None, **kw):
        super().__init__(**kw)
        self._on_goto = on_goto
        self._build()

    def _build(self):
        sc = MDScrollView(size_hint=(1, 1), do_scroll_x=False)
        col = MDBoxLayout(orientation="vertical", spacing=dp(8),
                          padding=[PAD, dp(24), PAD, dp(24)],
                          size_hint_y=None)
        col.bind(minimum_height=col.setter("height"))
        sc.add_widget(col)
        self.add_widget(sc)

        col.add_widget(Widget(size_hint_y=None, height=dp(40)))
        col.add_widget(_logo())
        col.add_widget(spacer(4))
        col.add_widget(t("Made By LMT", size=12, role="onSurfaceVariant", halign="center"))
        col.add_widget(spacer(16))

        card = MDCard(style="filled", radius=[dp(24)] * 4,
                      size_hint_y=None, adaptive_height=True,
                      padding=[PAD, dp(24), PAD, dp(24)], spacing=dp(16),
                      orientation="vertical",
                      md_bg_color=S["surfaceContainerHigh"])

        card.add_widget(t("Sign In", size=28, bold=True, halign="center", role="onSurface"))
        self.uname = field("Ten dang nhap", leading="person")
        card.add_widget(self.uname)
        self.passw = field("Mat khau", leading="lock", password=True)
        card.add_widget(self.passw)
        self.status = t("", size=13, halign="center", wrap=True, role="onSurfaceVariant")
        self.status.bind(texture_size=lambda i, s: setattr(i, "height", max(dp(20), s[1])))
        card.add_widget(self.status)

        btn = MDFillRoundFlatButton(text="Sign In", size_hint=(1, None), height=dp(56),
                                    md_bg_color=S["primary"], text_color=S["onPrimary"],
                                    font_size=sp(16))
        btn.bind(on_release=lambda *a: self._on_goto("submit-signin") if self._on_goto else None)
        card.add_widget(btn)

        link = MDTextButton(text="Don't have an account? Sign Up",
                            theme_text_color="Custom", text_color=S["primary"],
                            font_size=sp(16), pos_hint={"center_x": 0.5},
                            size_hint_y=None, height=dp(36))
        link.bind(on_release=lambda *a: self._on_goto("signup") if self._on_goto else None)
        card.add_widget(link)
        col.add_widget(card)
        col.add_widget(spacer(20))

    def get_account(self):
        return (self.uname.text or "").strip()

    def get_password(self):
        return self.passw.text or ""

    def set_status(self, msg, err=False):
        self.status.text = msg or ""
        self.status.text_color = S["error"] if err else S["onSurfaceVariant"]


class SignUpScreen(MDScreen):
    def __init__(self, on_goto=None, **kw):
        super().__init__(**kw)
        self._on_goto = on_goto
        self._build()

    def _build(self):
        sc = MDScrollView(size_hint=(1, 1), do_scroll_x=False)
        col = MDBoxLayout(orientation="vertical", spacing=dp(8),
                          padding=[PAD, dp(20), PAD, dp(20)],
                          size_hint_y=None)
        col.bind(minimum_height=col.setter("height"))
        sc.add_widget(col)
        self.add_widget(sc)

        col.add_widget(Widget(size_hint_y=None, height=dp(28)))
        col.add_widget(_logo())
        col.add_widget(spacer(4))
        col.add_widget(t("Made By LMT", size=12, role="onSurfaceVariant", halign="center"))
        col.add_widget(spacer(16))

        card = MDCard(style="filled", radius=[dp(24)] * 4,
                      size_hint_y=None, adaptive_height=True,
                      padding=[PAD, dp(24), PAD, dp(24)], spacing=dp(12),
                      orientation="vertical",
                      md_bg_color=S["surfaceContainerHigh"])

        card.add_widget(t("Sign Up", size=28, bold=True, halign="center", role="onSurface"))
        self.uname = field("Ten dang nhap", leading="person")
        card.add_widget(self.uname)
        self.passw = field("Mat khau", leading="lock", password=True)
        card.add_widget(self.passw)
        self.conf = field("Nhap lai mat khau", leading="lock", password=True)
        card.add_widget(self.conf)
        self.status = t("", size=13, halign="center", wrap=True, role="onSurfaceVariant")
        self.status.bind(texture_size=lambda i, s: setattr(i, "height", max(dp(20), s[1])))
        card.add_widget(self.status)

        btn = MDFillRoundFlatButton(text="Sign Up", size_hint=(1, None), height=dp(56),
                                    md_bg_color=S["primary"], text_color=S["onPrimary"],
                                    font_size=sp(16))
        btn.bind(on_release=lambda *a: self._on_goto("submit-signup") if self._on_goto else None)
        card.add_widget(btn)

        link = MDTextButton(text="Already have an account? Sign In",
                            theme_text_color="Custom", text_color=S["primary"],
                            font_size=sp(16), pos_hint={"center_x": 0.5},
                            size_hint_y=None, height=dp(36))
        link.bind(on_release=lambda *a: self._on_goto("signin") if self._on_goto else None)
        card.add_widget(link)
        col.add_widget(card)
        col.add_widget(spacer(20))

    def get_account(self):
        return (self.uname.text or "").strip()

    def get_password(self):
        return self.passw.text or ""

    def set_status(self, msg, err=False):
        self.status.text = msg or ""
        self.status.text_color = S["error"] if err else S["onSurfaceVariant"]
