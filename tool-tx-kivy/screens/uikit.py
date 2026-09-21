from kivy.metrics import dp, sp
from kivy.uix.widget import Widget
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.card import MDCard
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle
from core.m3 import S

PAD = dp(16)


def t(text, size=14, bold=False, role="onSurface", halign="left", wrap=False,
      no_scale=False, **kw):
    l = MDLabel(text=text, font_size=sp(size), bold=bold, halign=halign,
                size_hint_y=None, valign="middle", **kw)
    l.bind(texture_size=lambda i, s: setattr(i, "height", max(dp(20), s[1] * 1.3)))
    if wrap:
        l.bind(width=lambda i, w: setattr(i, "text_size", (w * 0.97, None)))
    l.theme_text_color = "Custom"
    l.text_color = S[role]
    return l


def spacer(h=8):
    return Widget(size_hint_y=None, height=dp(h))


def field(hint="", leading="", password=False, ref=None):
    box = MDBoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(56),
                      padding=[dp(8), dp(8), dp(8), dp(8)], spacing=dp(4))
    with box.canvas.before:
        Color(*S["surfaceContainerHighest"])
        box._bg = RoundedRectangle(radius=[dp(12)] * 4)
    box.bind(pos=lambda i, *a: setattr(box._bg, "pos", i.pos),
             size=lambda i, *a: setattr(box._bg, "size", i.size))
    if leading:
        ic = MDIcon(icon=leading, font_size=sp(20), size_hint_x=None, width=dp(36),
                    pos_hint={"center_y": 0.5})
        ic.theme_text_color = "Custom"
        ic.text_color = S["onSurfaceVariant"]
        box.add_widget(ic)
    ti = TextInput(
        hint_text=hint, hint_text_color=[0.55, 0.55, 0.6, 1],
        password=password, password_mask="\u2022",
        background_normal="", background_active="",
        background_color=[0, 0, 0, 0], foreground_color=S["onSurface"],
        cursor_color=S["primary"], font_size=sp(16), size_hint=(1, 1),
        padding=[0, dp(8), 0, dp(4)], multiline=False,
    )
    box.add_widget(ti)
    box._ti = ti
    if ref is not None:
        ref.append(ti)
    return box


def pill_btn(text, icon="", on_release=None, **kw):
    from kivymd.uix.button import MDFillRoundFlatButton
    btn = MDFillRoundFlatButton(text=("  " + text) if icon else text,
                                icon=icon if icon else None,
                                size_hint=(1, None), height=dp(56),
                                font_size=sp(15), **kw)
    if on_release:
        btn.bind(on_release=on_release)
    return btn


def section_title(text):
    return t(text, size=13, bold=True, role="onSurfaceVariant")


label = t
Chip = MDBoxLayout
Column = MDBoxLayout
GlassCard = MDCard


def chip(text="", text_color=None, bg_color=None, **kw):
    box = MDBoxLayout(size_hint_y=None, height=dp(32), **kw)
    if bg_color:
        box.md_bg_color = bg_color
    if text:
        lbl = t(text, size=kw.get("size", 12), role="onSurface")
        if text_color:
            lbl.text_color = text_color
        box.add_widget(lbl)
    return box
