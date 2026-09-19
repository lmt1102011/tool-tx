# core/theme.py — nền gradient xanh đen → xanh dương (Pillow), các màu brand.
from kivy.graphics.texture import Texture


def make_bg(top=(12, 17, 30), bottom=(25, 38, 66)):
    """Texture gradient dọc 2x384 — nhờ Pillow vẽ sẵn, không cần shader."""
    try:
        from PIL import Image
        w, h = 2, 384
        img = Image.new("RGB", (w, h))
        px = img.load()
        for y in range(h):
            t = y / (h - 1)
            c = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
            for x in range(w):
                px[x, y] = c
        tex = Texture.create(size=(w, h), colorfmt="rgb")
        tex.blit_buffer(img.tobytes(), colorfmt="rgb", bufferfmt="ubyte")
        tex.wrap = "clamp_to_edge"
        return tex
    except Exception:
        return None