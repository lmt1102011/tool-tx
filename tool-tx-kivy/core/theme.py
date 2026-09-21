# core/theme.py — nền gradient (kivy Texture, không cần Pillow), đổi màu theo light/dark.
from kivy.graphics.texture import Texture


def make_bg(dark=True):
    """Texture gradient dọc 8x384 — dựng byte trực tiếp, không phụ thuộc Pillow."""
    try:
        if dark:
            top = (9, 13, 17)
            bottom = (13, 25, 42)
        else:
            top = (238, 245, 248)
            bottom = (186, 219, 234)
        w, h = 8, 384
        buf = bytearray()
        for y in range(h):
            t = y / (h - 1)
            c = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
            buf += bytes(c) * w
        tex = Texture.create(size=(w, h), colorfmt="rgb")
        tex.blit_buffer(bytes(buf), colorfmt="rgb", bufferfmt="ubyte")
        tex.wrap = "clamp_to_edge"
        return tex
    except Exception:
        return None