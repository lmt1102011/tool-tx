from kivy.metrics import dp, sp
from kivy.uix.widget import Widget
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.card import MDCard
from core.m3 import S


def t(text, size=14, bold=False, role="onSurface", halign="left", wrap=False, **kw):
    l = MDLabel(text=text, font_size=sp(size), bold=bold, halign=halign,
                size_hint_y=None, valign="middle", **kw)
    l.bind(texture_size=lambda i, s: setattr(i, "height", max(dp(20), s[1] * 1.3)))
    if wrap:
        l.bind(width=lambda i, w: setattr(i, "text_size", (w * 0.97, None)))
    l.theme_text_color = "Custom"
    l.text_color = S[role]
    return l


def spacer(h=None):
    w = Widget(size_hint_y=None)
    if h is not None:
        w.height = dp(h)
    return w


def gap(h=14):
    return spacer(h)


def field(hint="", leading="", password=False):
    box = MDBoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(56),
                      padding=[dp(4), dp(4)], spacing=dp(4))
    with box.canvas.before:
        from kivy.graphics import Color, RoundedRectangle
        Color(*S["surfaceContainerHighest"])
        box._bg = RoundedRectangle(radius=[dp(12)] * 4)
    box.bind(pos=lambda i, *a: setattr(box._bg, "pos", i.pos),
             size=lambda i, *a: setattr(box._bg, "size", i.size))
    if leading:
        ic = MDIcon(icon=leading, font_size=sp(22),
                    size_hint_x=None, width=dp(40),
                    pos_hint={"center_y": 0.5})
        ic.theme_text_color = "Custom"
        ic.text_color = S["onSurfaceVariant"]
        box.add_widget(ic)
    from kivy.uix.textinput import TextInput
    ti = TextInput(
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
    box.add_widget(ti)
    box._ti = ti

    @property
    def text(self):
        return self._ti.text

    @text.setter
    def text(self, v):
        self._ti.text = v

    return box


def pill_btn(text, icon="", **kw):
    btn_kw = dict(
        style="filled",
        radius=[dp(28)] * 4,
        size_hint=(1, None),
        height=dp(56),
        md_bg_color=S["primary"],
        text_color=S["onPrimary"],
        font_size=sp(16),
        halign="center",
    )
    btn_kw.update(kw)
    btn = MDCard(**btn_kw)
    row = MDBoxLayout(orientation="horizontal", spacing=dp(8),
                      pos_hint={"center_x": 0.5, "center_y": 0.5})
    if icon:
        ic = MDIcon(icon=icon, font_size=sp(20),
                    theme_text_color="Custom", text_color=S["onPrimary"])
        row.add_widget(ic)
    lbl = MDLabel(text=text, font_size=sp(16), bold=True,
                  halign="center", theme_text_color="Custom",
                  text_color=S["onPrimary"])
    row.add_widget(lbl)
    btn.add_widget(row)
    return btn


# ── compat aliases (admin.py / browser.py use old names) ──
label = t
Chip = MDBoxLayout
Column = MDBoxLayout
GlassCard = MDCard


def chip(text="", **kw):
    return MDBoxLayout(**kw)
