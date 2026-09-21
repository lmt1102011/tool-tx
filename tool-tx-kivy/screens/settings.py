from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton, MDTextButton, MDFillRoundFlatButton
from kivymd.uix.label import MDIcon
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.screen import MDScreen

from core.m3 import S
from screens.uikit import t, spacer, PAD


class SwRow(MDBoxLayout):
    def __init__(self, text, active=False, on_change=None, sub="", **kw):
        super().__init__(orientation="horizontal", spacing=dp(12),
                         padding=[dp(4), 0, dp(4), 0],
                         size_hint_y=None, height=dp(56), **kw)
        box = MDBoxLayout(orientation="vertical", spacing=dp(0))
        box.add_widget(t(text, size=16, role="onSurface"))
        if sub:
            box.add_widget(t(sub, size=12, role="onSurfaceVariant"))
        self.add_widget(box)
        sw = MDSwitch(size_hint_x=None, width=dp(52))
        sw.bind(on_active=lambda inst, v: on_change(bool(v)) if on_change else None)
        self.sw = sw
        self.add_widget(sw)
        Clock.schedule_once(lambda dt: setattr(self.sw, "active", active), 0)


class SettingsScreen(MDScreen):
    def __init__(self, on_back=None, on_theme=None, on_log=None, on_auto=None,
                 on_logout=None, prefs=None, **kw):
        super().__init__(**kw)
        self._on_back = on_back
        self._on_theme = on_theme
        self._on_log = on_log
        self._on_auto = on_auto
        self._on_logout = on_logout
        self._prefs = prefs or {}
        self._dialog = None
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation="vertical", padding=0, spacing=0)
        self.add_widget(root)

        bar = MDBoxLayout(orientation="horizontal", padding=[dp(4), dp(12), dp(12), 0],
                          size_hint_y=None, height=dp(64), spacing=dp(8))
        back = MDIconButton(icon="arrow-left", icon_size=sp(24),
                            theme_icon_color="Custom", icon_color=S["onSurface"])
        back.bind(on_release=lambda *a: self._on_back() if self._on_back else None)
        bar.add_widget(back)
        bar.add_widget(t("Settings", size=22, bold=True, role="onSurface"))
        root.add_widget(bar)

        sc = MDBoxLayout(orientation="vertical", spacing=dp(16),
                         padding=[dp(12), dp(8), dp(12), dp(8)])
        root.add_widget(sc)

        profile = MDCard(style="elevated", radius=[dp(20)] * 4,
                         size_hint_y=None, height=dp(72),
                         padding=[dp(16), dp(8)], spacing=dp(8),
                         orientation="horizontal")
        ic = MDIconButton(icon="account-circle", icon_size=sp(26),
                          theme_icon_color="Custom", icon_color=S["onSurfaceVariant"])
        profile.add_widget(ic)
        inner = MDBoxLayout(orientation="vertical", spacing=dp(0))
        self.name_lbl = t("Name", size=18, bold=True, role="onSurface")
        inner.add_widget(self.name_lbl)
        self.uid_lbl = t("", size=12, role="onSurfaceVariant")
        inner.add_widget(self.uid_lbl)
        profile.add_widget(inner)
        out = MDIconButton(icon="logout", icon_size=sp(26),
                           theme_icon_color="Custom", icon_color=S["error"])
        out.bind(on_release=lambda *a: self._ask_logout())
        profile.add_widget(out)
        sc.add_widget(profile)

        prefs_card = MDCard(style="filled", radius=[dp(20)] * 4,
                            size_hint_y=None, adaptive_height=True,
                            padding=[dp(8), dp(4)], spacing=dp(2),
                            orientation="vertical",
                            md_bg_color=S["surfaceContainerHigh"])
        self.row_theme = SwRow("Sang / Toi", active=bool(self._prefs.get("dark", True)),
                               on_change=lambda v: self._on_theme(v) if self._on_theme else None)
        prefs_card.add_widget(self.row_theme)
        self.row_log = SwRow("Nhat ky hoat dong", active=bool(self._prefs.get("log", True)),
                             on_change=lambda v: self._on_log(v) if self._on_log else None)
        prefs_card.add_widget(self.row_log)
        self.row_auto = SwRow("Tu ket noi server", active=bool(self._prefs.get("auto", True)),
                              on_change=lambda v: self._on_auto(v) if self._on_auto else None)
        prefs_card.add_widget(self.row_auto)
        sc.add_widget(prefs_card)

        picks_card = MDCard(style="filled", radius=[dp(20)] * 4,
                            size_hint_y=None, height=dp(56),
                            padding=[dp(16), dp(8)],
                            orientation="horizontal",
                            md_bg_color=S["surfaceContainerLow"])
        picks_card.add_widget(t("So luong du doan con lai", size=13, role="onSurfaceVariant"))
        self.a_picks = t("--", size=15, bold=True, role="onSurface", halign="right")
        self.a_picks.size_hint_x = None
        self.a_picks.width = dp(120)
        picks_card.add_widget(self.a_picks)
        sc.add_widget(picks_card)

        log_card = MDCard(style="filled", radius=[dp(20)] * 4,
                          size_hint_y=None, adaptive_height=True,
                          padding=[dp(16), dp(12)], spacing=dp(4),
                          md_bg_color=S["surfaceContainerLow"])
        self.log = t("Chua co hoat dong.", size=12, role="onSurfaceVariant", wrap=True)
        log_card.add_widget(self.log)
        self._log_card = log_card
        sc.add_widget(log_card)

        btn_crash = MDFillRoundFlatButton(
            text="  Gui crash log", icon="bug",
            size_hint=(1, None), height=dp(48),
            md_bg_color=S["tertiaryContainer"], text_color=S["onTertiaryContainer"],
            font_size=sp(14))
        btn_crash.bind(on_release=lambda *a: self._share_crash())
        sc.add_widget(btn_crash)

        sc.add_widget(t("ToolTX - Gold edition - v1.2", size=11, role="onSurfaceVariant",
                         halign="center"))

    def _ask_logout(self):
        if self._dialog:
            try:
                self._dialog.dismiss()
            except Exception:
                pass
        self._dialog = MDDialog(
            title="Log out",
            text="Do you want to log out?",
            buttons=[
                MDTextButton(text="Cancel", on_release=lambda *a: self._dlg(False)),
                MDTextButton(text="OK", bold=True, on_release=lambda *a: self._dlg(True)),
            ],
        )
        self._dialog.open()

    def _dlg(self, ok):
        try:
            self._dialog.dismiss()
        except Exception:
            pass
        if ok and self._on_logout:
            self._on_logout()

    def profile(self, name, letter, uid, role, picks_text):
        self.name_lbl.text = name or "Name"
        role_txt = (" . " + role) if role else ""
        self.uid_lbl.text = (uid or "chua co tai khoan") + role_txt
        self.a_picks.text = picks_text or "--"

    def picks_text(self, txt):
        self.a_picks.text = txt or "--"

    def set_log(self, text):
        if self._prefs.get("log", True):
            self.log.text = text or "Chua co hoat dong."
        self._log_card.opacity = 1.0 if self._prefs.get("log", True) else 0.0

    def _share_crash(self):
        import os
        from core.config import IS_ANDROID
        paths = [
            "/sdcard/Download/crash.log",
            "/storage/emulated/0/Download/crash.log",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "crash.log"),
        ]
        found = ""
        for p in paths:
            if os.path.isfile(p) and os.path.getsize(p) > 0:
                found = p
                break
        if not found:
            self.log.text = "Khong co crash log."
            return
        if not IS_ANDROID:
            self.log.text = "Crash log: " + found
            return
        try:
            from jnius import autoclass
            PyA = autoclass("org.kivy.android.PythonActivity")
            File = autoclass("java.io.File")
            Uri = autoclass("android.net.Uri")
            Intent = autoclass("android.content.Intent")
            act = PyA.mActivity
            f = File(found)
            uri = Uri.fromFile(f)
            i = Intent(Intent.ACTION_SEND)
            i.setType("text/plain")
            i.putExtra(Intent.EXTRA_STREAM, uri)
            i.putExtra(Intent.EXTRA_SUBJECT, "ToolTX Crash Log")
            i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            act.startActivity(Intent.createChooser(i, "Gui crash log"))
        except Exception as e:
            self.log.text = "Loi gui crash log: " + str(e)[:80]
