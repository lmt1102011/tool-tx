from kivy.metrics import dp, sp
from kivy.properties import StringProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.card import MDCard
from kivy.uix.widget import Widget
from core.m3 import S


def t(text, size=14, bold=False, role="onSurface", halign="left", wrap=False, **kw):
    l = MDLabel(text=text, font_size=sp(size), bold=bold, halign=halign,
                size_hint_y=None, valign="middle", **kw)
    l.bind(texture_size=lambda i, s: setattr(i, "height", max(dp(20), s[1] * 1.25)))
    if wrap:
        l.bind(width=lambda i, w: setattr(i, "text_size", (w * 0.97, None)))
    l.theme_text_color = "Custom"
    l.text_color = S[role]
    return l


def icon_label(ic, text="", size=14, role="onSurface", icon_role="onSurfaceVariant",
               icon_sz=24, halign="left"):
    b = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(12), padding=[0, 0])
    i = MDIcon(icon=ic, font_size=sp(icon_sz), size_hint_x=None, width=dp(32),
               pos_hint={"center_y": 0.5})
    i.theme_text_color = "Custom"
    i.text_color = S[icon_role]
    b.add_widget(i)
    if text:
        b.add_widget(t(text, size=size, role=role, halign=halign))
    return b


def gap(h=14):
    return Widget(size_hint_y=None, height=dp(h))


def spacer(h=None):
    w = Widget(size_hint_y=None)
    if h is not None:
        w.height = dp(h)
    return w


def card_elevated(**kw):
    kw.setdefault("style", "elevated")
    kw.setdefault("radius", [dp(20)] * 4)
    kw.setdefault("padding", [dp(16), dp(16)])
    kw.setdefault("spacing", dp(8))
    kw.setdefault("size_hint_y", None)
    kw.setdefault("adaptive_height", True)
    return MDCard(**kw)


def card_filled(**kw):
    kw.setdefault("style", "filled")
    kw.setdefault("radius", [dp(20)] * 4)
    kw.setdefault("padding", [dp(16), dp(16)])
    kw.setdefault("spacing", dp(8))
    kw.setdefault("size_hint_y", None)
    kw.setdefault("adaptive_height", True)
    return MDCard(**kw)


class M3Field(MDBoxLayout):
    def __init__(self, hint="", leading="", password=False, **kw):
        super().__init__(orientation="horizontal", size_hint=(1, None), height=dp(56),
                         padding=[dp(4), dp(4), dp(4), dp(4)], spacing=dp(4), **kw)
        with self.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(*S["surfaceContainerHighest"])
            self._bg = RoundedRectangle(radius=[dp(16), dp(16), dp(0), dp(0)])
        self.bind(pos=lambda i, *a: setattr(self._bg, "pos", i.pos),
                  size=lambda i, *a: setattr(self._bg, "size", i.size))
        if leading:
            ic = MDIcon(icon=leading, font_size=sp(22),
                        size_hint_x=None, width=dp(40),
                        pos_hint={"center_y": 0.5})
            ic.theme_text_color = "Custom"
            ic.text_color = S["onSurfaceVariant"]
            self.add_widget(ic)
        from kivy.uix.textinput import TextInput
        self._ti = TextInput(
            hint_text=hint, hint_text_color=[0.55, 0.55, 0.6, 1],
            password=password, password_mask="\u2022",
            background_normal="", background_active="",
            background_color=[0, 0, 0, 0],
            foreground_color=S["onSurface"],
            cursor_color=S["primary"],
            font_size=sp(16), size_hint=(1, 1),
            padding=[0, dp(10), 0, dp(4)],
            multiline=False,
        )
        self.add_widget(self._ti)

    @property
    def text(self):
        return self._ti.text

    @text.setter
    def text(self, v):
        self._ti.text = v

    @property
    def focus(self):
        return self._ti.focus

    @focus.setter
    def focus(self, v):
        self._ti.focus = v


def field(hint="", leading="", password=False):
    return M3Field(hint=hint, leading=leading, password=password)
