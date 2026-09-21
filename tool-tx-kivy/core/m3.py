# core/m3.py — Material 3 Expressive: bảng màu roles (light/dark) + phát hiện sáng/tối hệ thống.
# Tham chiếu toàn bộ màu qua roles ở đây, không hard-code ở màn hình.

import os


def _mode_default():
    try:
        import android  # noqa: F401
    except Exception:
        return False
    try:
        from jnius import autoclass
        A = autoclass("org.kivy.android.PythonActivity")
        act = A.mActivity
        conf = act.getResources().getConfiguration()
        mask = conf.getResources().getConfiguration().UI_MODE_NIGHT_MASK
        return conf.getResources().getConfiguration().uiMode & mask == \
            conf.getResources().getConfiguration().UI_MODE_NIGHT_YES
    except Exception:
        return False


_DETECTED_DARK = _mode_default()

# ── roles light ──────────────────────────────────────────────
LIGHT = {
    "primary": (0.220, 0.741, 0.973, 1),
    "onPrimary": (0.016, 0.118, 0.169, 1),
    "primaryContainer": (0.047, 0.290, 0.431, 1),
    "onPrimaryContainer": (1.000, 1.000, 1.000, 1),
    "secondary": (0.286, 0.384, 0.435, 1),
    "secondaryContainer": (0.118, 0.227, 0.373, 1),
    "onSecondaryContainer": (1.000, 1.000, 1.000, 1),
    "tertiaryContainer": (0.153, 0.208, 0.286, 1),
    "onTertiaryContainer": (1.000, 1.000, 1.000, 1),
    "surface": (0.957, 0.980, 0.996, 1),
    "surfaceContainerLow": (0.933, 0.961, 0.973, 1),
    "surfaceContainer": (0.910, 0.937, 0.953, 1),
    "surfaceContainerHigh": (0.890, 0.914, 0.929, 1),
    "surfaceContainerHighest": (0.867, 0.890, 0.906, 1),
    "onSurface": (0.090, 0.110, 0.122, 1),
    "onSurfaceVariant": (0.231, 0.286, 0.314, 1),
    "outline": (0.420, 0.475, 0.506, 1),
    "outlineVariant": (0.729, 0.788, 0.824, 1),
    "inverseSurface": (0.173, 0.192, 0.204, 1),
    "inverseOnSurface": (1.000, 1.000, 1.000, 1),
    "inversePrimary": (0.486, 0.820, 0.980, 1),
    "error": (0.702, 0.149, 0.118, 1),
    "onError": (1.000, 1.000, 1.000, 1),
    "errorContainer": (0.976, 0.871, 0.863, 1),
    "onErrorContainer": (0.255, 0.055, 0.043, 1),
}

# ── roles dark ───────────────────────────────────────────────
DARK = {
    "primary": (0.486, 0.820, 0.980, 1),
    "onPrimary": (0.027, 0.208, 0.275, 1),
    "primaryContainer": (0.043, 0.302, 0.392, 1),
    "onPrimaryContainer": (0.757, 0.910, 0.996, 1),
    "secondary": (0.690, 0.792, 0.855, 1),
    "secondaryContainer": (0.192, 0.290, 0.341, 1),
    "onSecondaryContainer": (0.796, 0.906, 0.965, 1),
    "tertiaryContainer": (0.286, 0.263, 0.369, 1),
    "onTertiaryContainer": (0.906, 0.871, 0.988, 1),
    "surface": (0.059, 0.078, 0.090, 1),
    "surfaceContainerLow": (0.090, 0.110, 0.122, 1),
    "surfaceContainer": (0.106, 0.125, 0.137, 1),
    "surfaceContainerHigh": (0.149, 0.169, 0.180, 1),
    "surfaceContainerHighest": (0.188, 0.208, 0.220, 1),
    "onSurface": (0.867, 0.890, 0.906, 1),
    "onSurfaceVariant": (0.729, 0.788, 0.824, 1),
    "outline": (0.518, 0.576, 0.608, 1),
    "outlineVariant": (0.231, 0.286, 0.314, 1),
    "inverseSurface": (0.867, 0.890, 0.906, 1),
    "inverseOnSurface": (0.173, 0.192, 0.204, 1),
    "inversePrimary": (0.122, 0.396, 0.506, 1),
    "error": (0.949, 0.722, 0.710, 1),
    "onError": (0.376, 0.078, 0.063, 1),
    "errorContainer": (0.549, 0.114, 0.094, 1),
    "onErrorContainer": (0.976, 0.871, 0.863, 1),
}

# Bảng đang dùng — screens đọc qua `S["primary"]`, ... Đổi nội dung khi bật/tắt theme.
S = dict(DARK)


def set_dark(dark):
    S.clear()
    S.update(DARK if dark else LIGHT)


def is_dark_default():
    """Mặc định theo hệ thống (chỉ Android). Trên desktop trả về dark."""
    return _DETECTED_DARK or not _android()


def _android():
    return bool(os.environ.get("ANDROID_ARGUMENT"))