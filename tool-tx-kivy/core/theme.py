# core/theme.py — nền gradient xanh đen → xanh dương (kivy Texture, không cần Pillow), các màu brand.
from kivy.graphics.texture import Texture


def make_bg(top=(18, 30, 52), bottom=(54, 98, 165)):
    """Texture gradient dọc 2x384 — tự dựng byte, không phụ thuộc Pillow (tránh build jpeg)."""
    try:
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