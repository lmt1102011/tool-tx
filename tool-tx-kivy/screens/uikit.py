# screens/uikit.py — tiện ích dựng UI M3 (label theo role, Panel, card, chip, field).
from kivy.metrics import dp, sp
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.graphics import StencilPush, StencilPop
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel, MDIcon

from core.m3 import S


def Spacer(size_hint_y=(1, None), height=None, **kw):
    b = MDBoxLayout(size_hint_y=size_hint_y, **kw)
    if height is not None:
        b.height = height
        b.size_hint_y = None
    return b


def round_clip(w, radius=dp(20)):
    """Bọc widget bằng stencil tròn để bo góc nội dung (ảnh...)."""
    from kivy.graphics import StencilUse, StencilUnUse
    with w.canvas.before:
        StencilPush()
        r = RoundedRectangle(pos=w.pos, size=w.size, radius=[radius] * 4)
        StencilUse()
        w._clip_r = r
    with w.canvas.after:
        StencilUnUse()
        StencilPop()
    w.bind(pos=_clip_draw, size=_clip_draw)


def _clip_draw(inst, *a):
    if hasattr(inst, "_clip_r"):
        inst._clip_r.pos = inst.pos
        inst._clip_r.size = inst.size


def label(text, role="onSurface", size=14, bold=False, halign="left", wrap=False,
          color=None, markup=False, line_h=1.35):
    """MDLabel chiều cao tự động theo nội dung; màu lấy qua role."""
    l = MDLabel(
        text=text, theme_text_color="Custom",
        text_color=color if color is not None else S[role],
        halign=halign, markup=markup, size_hint_y=None, size_hint_x=1,
        valign="middle", padding=(0, 0),
        font_size=sp(size), bold=bold,
    )
    if wrap:
        l.bind(width=lambda *a: setattr(l, "text_size", (l.width * 0.96, None)))
    l._lh = line_h

    def _auto_height(*a):
        h = l.texture_size[1] * line_h + dp(6)
        l.height = h if h > dp(20) else dp(20)
    l.bind(texture_size=_auto_height)
    l.height = dp(22)
    return l


def rcolor(rgba):
    return tuple(rgba)


class Column(MDBoxLayout):
    """Cột dọc tự co cao — dùng trong ScrollView toàn màn hình."""

    def __init__(self, **kw):
        kw.setdefault("orientation", "vertical")
        kw.setdefault("size_hint_y", None)
        kw.setdefault("spacing", dp(14))
        super().__init__(**kw)
        self.bind(minimum_height=self.setter("height"))


class Panel(MDBoxLayout):
    """Hộp nền phẳng (plain container) theo role bg + bán kính góc."""

    def __init__(self, bg="surfaceContainerHighest", radius=28, padding=(dp(24), dp(24)),
                 spacing=dp(12), auto=True, **kw):
        super().__init__(orientation="vertical", spacing=spacing, padding=padding, **kw)
        self.size_hint_y = None
        if auto:
            self.bind(minimum_height=self.setter("height"))
        self._radius = radius
        with self.canvas.before:
            Color(*S[bg])
            self._rect = RoundedRectangle(radius=[radius] * 4)
        self.bind(pos=_panel_draw, size=_panel_draw)

    # cho phép sửa bg role khi đổi theme
    def set_bg(self, bg):
        pass


class Card(MDBoxLayout):
    """Thẻ M3 20dp: filled / outlined / elevated (bóng đơn giản phía sau)."""

    def __init__(self, kind="filled", bg="surfaceContainerLow", radius=20,
                 padding=(dp(20), dp(20)), spacing=dp(12), auto=True, **kw):
        super().__init__(orientation="vertical", spacing=spacing, padding=padding, **kw)
        self.size_hint_y = None
        if auto:
            self.bind(minimum_height=self.setter("height"))
        if kind == "elevated":
            with self.canvas.before:
                Color(0, 0, 0, 0.25)
                self._sh = RoundedRectangle(radius=[radius] * 4, pos=(0, -dp(3)))
            self._shd = True
        else:
            self._shd = False
        with self.canvas:
            Color(*S[bg])
            self._rect = RoundedRectangle(radius=[radius] * 4)
        if kind == "outlined":
            with self.canvas.after:
                Color(*S["outlineVariant"], 1)
                self._line = Line(rounded_rectangle=[0, 0, 0, 0, radius, 12], width=1)
        else:
            self._line = None
        self._radius = radius
        self.bind(pos=_card_draw, size=_card_draw)

    def set_bg(self, bg):
        pass


class Chip(MDBoxLayout):
    """Chip 32dp, bo 8dp; selected = secondaryContainer."""

    def __init__(self, text="", height=32, selected=False, color=None,
                 icon=None, **kw):
        super().__init__(orientation="horizontal", spacing=dp(6), size_hint_y=None,
                         height=dp(height), padding=[dp(14), 0, dp(14), 0], **kw)
        self._selected = selected
        with self.canvas.before:
            Color(*self._bg())
            self._rect = RoundedRectangle(radius=[dp(8)] * 4)
        self.bind(pos=_chip_draw, size=_chip_draw)

        def _recolor(*a):
            self._rect.pos = self.pos
            self._rect.size = self.size
        self.bind(pos=_recolor, size=_recolor)
        self._t = label(text, role="onSurface", size=13, halign="center", wrap=False)
        self._t.bold = True
        self.add_widget(self._t)

    def _bg(self):
        return S["secondaryContainer"] if self._selected else S["surface"]


def _panel_draw(inst, *a):
    inst._rect.pos = inst.pos
    inst._rect.size = inst.size


def _card_draw(inst, *a):
    if inst._shd:
        inst._sh.pos = (inst.x, inst.y - dp(3))
        inst._sh.size = inst.size
    inst._rect.pos = inst.pos
    inst._rect.size = inst.size
    if inst._line is not None:
        inst._line.rounded_rectangle = [inst.x, inst.y, inst.width, inst.height,
                                        inst._radius, 12]


def _chip_draw(inst, *a):
    inst._rect.pos = inst.pos
    inst._rect.size = inst.size


class M3Field(MDBoxLayout):
    """Ô nhập M3 filled: canvas filled bg + TextInput + hint浮标 + leading icon."""

    def __init__(self, hint="", leading="", password=False, **kw):
        super().__init__(orientation="horizontal", size_hint=(1, None), height=dp(56),
                         padding=[dp(16), dp(8), dp(12), dp(8)], spacing=dp(8), **kw)
        with self.canvas.before:
            Color(*S["surfaceContainerHighest"])
            self._bg = RoundedRectangle(radius=[dp(16), dp(16), 0, 0])
        self.bind(pos=_field_bg, size=_field_bg)

        if leading:
            ic = MDIcon(icon=leading, theme_text_color="Custom",
                        text_color=S["onSurfaceVariant"], font_size=sp(24),
                        size_hint_x=None, width=dp(40),
                        pos_hint={"center_y": 0.5})
            self.add_widget(ic)

        from kivy.uix.textinput import TextInput
        self._ti = TextInput(
            hint_text=hint, hint_text_color=[0, 0, 0, 0],
            password=password, password_mask="\u2022",
            background_normal="", background_active="",
            background_color=[0, 0, 0, 0],
            foreground_color=S["onSurface"],
            cursor_color=S["primary"],
            font_size=sp(16), size_hint=(1, 1),
            padding=[0, dp(12), 0, dp(4)],
            multiline=False,
        )
        self.add_widget(self._ti)

        self._hint = label(hint, role="onSurfaceVariant", size=12,
                           halign="left", wrap=False)
        self._hint.opacity = 1.0

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

    def bind(self, **kw):
        if "text" in kw:
            cb = kw.pop("text")
            self._ti.bind(text=cb)
        if "on_text" in kw:
            cb = kw.pop("on_text")
            self._ti.bind(on_text_validate=cb)
        if kw:
            super().bind(**kw)


def _field_bg(inst, *a):
    inst._bg.pos = inst.pos
    inst._bg.size = inst.size


def field(hint="", leading="", password=False, height=56, outline=True):
    """Ô nhập M3: 56dp, filled, có leading icon."""
    return M3Field(hint=hint, leading=leading, password=password)