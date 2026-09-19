# screens/uikit.py — tiện ích dựng UI đồng bộ (label wrap, thẻ glass).
from kivy.metrics import dp, sp
from kivy.graphics import Color, RoundedRectangle, Line
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel

from core.config import CARD, TXT, GOLD_DIM


def label(text, style="Body1", color=TXT, size=None, halign="left",
          markup=False, bold=False, wrap=False, adaptive=True):
    """MDLabel có chiều cao tự động theo nội dung (size_hint_y=None)."""
    l = MDLabel(
        text=text, font_style=style, theme_text_color="Custom", text_color=color,
        halign=halign, markup=markup, size_hint_y=None, size_hint_x=1,
        valign="middle", padding=(0, 0),
    )
    if size:
        l.font_size = sp(size)
    if wrap:
        l.bind(width=lambda *a: setattr(l, "text_size", (l.width * 0.98, None)))
    if adaptive:
        def _auto_height(*a):
            h = l.texture_size[1] + dp(6)
            l.height = h if h > dp(20) else dp(20)
        l.bind(texture_size=_auto_height)
        l.height = dp(22)
    else:
        l.height = dp(34)
    return l


class Column(MDBoxLayout):
    """Cột dọc tự co cao theo nội dung — dùng trong ScrollView toàn màn hình."""

    def __init__(self, **kw):
        kw.setdefault("orientation", "vertical")
        kw.setdefault("size_hint_y", None)
        super().__init__(**kw)
        self.bind(minimum_height=self.setter("height"))


class GlassCard(MDBoxLayout):
    """Thẻ nền kính (rounded rect) tự co cao theo nội dung bên trong."""

    def __init__(self, bg=CARD, radius=dp(18), border=GOLD_DIM, border_w=dp(1.2),
                 padding=[dp(18), dp(16), dp(18), dp(16)], spacing=dp(12), **kw):
        super().__init__(orientation="vertical", spacing=spacing, padding=padding, **kw)
        self.size_hint_y = None
        self.bind(minimum_height=self.setter("height"))
        self._radius = radius
        with self.canvas.before:
            Color(*bg)
            self._rect = RoundedRectangle(radius=[radius] * 4)
            if border:
                Color(*border)
                self._line = Line(rounded_rectangle=[0, 0, 0, 0, radius, 12], width=border_w)
            else:
                self._line = None
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *a):
        self._rect.pos = self.pos
        self._rect.size = self.size
        if self._line is not None:
            self._line.rounded_rectangle = [self.x, self.y, self.width, self.height,
                                            self._radius, 12]


def chip(text, color, bg, size=12, bold=True):
    """Viên nhỏ (badge) 2 dòng: chấm màu + chữ."""
    b = MDBoxLayout(orientation="horizontal", spacing=dp(6), size_hint_y=None,
                    padding=[dp(10), dp(4), dp(10), dp(4)])
    b.bind(minimum_height=b.setter("height"))
    with b.canvas.before:
        Color(*bg)
        b._rec = RoundedRectangle(radius=[dp(9)] * 4)
    b.bind(pos=_chip_draw, size=_chip_draw)
    dot_done = label("●", color=color, size=size, halign="center", adaptive=False)
    dot_done.size_hint_x = None
    dot_done.width = dp(12)
    txt = label(text, color=color, size=size, halign="left", wrap=False)
    txt.bold = bold
    b.add_widget(dot_done)
    b.add_widget(txt)
    return b


def _chip_draw(inst, *a):
    inst._rec.pos = inst.pos
    inst._rec.size = inst.size