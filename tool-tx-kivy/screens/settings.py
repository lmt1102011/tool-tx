# screens/settings.py — Màn Settings (M3): top bar Name + switch + dialog đăng xuất.
from kivy.metrics import dp, sp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton, MDTextButton
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.dialog import MDDialog
from kivymd.uix.screen import MDScreen

from core.m3 import S
from screens.uikit import label, Panel, Spacer


class SwRow(MDBoxLayout):
    def __init__(self, text, active=False, on_change=None, sub="", **kw):
        super().__init__(orientation="horizontal", spacing=dp(12), padding=[dp(4), 0, dp(4), 0],
                         size_hint_y=None, height=dp(56), **kw)
        box = MDBoxLayout(orientation="vertical", spacing=dp(0))
        box.add_widget(label(text, role="onSurface", size=16))
        if sub:
            box.add_widget(label(sub, role="onSurfaceVariant", size=12))
        self.add_widget(box)
        sw = MDSwitch(size_hint_x=None, width=dp(52))
        sw.bind(on_active=lambda inst, v: on_change(bool(v)) if on_change else None)
        self.sw = sw
        self.add_widget(sw)
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self._deferred_init(active), 0)

    def _deferred_init(self, active):
        self.sw.active = active


def _switch(text, sub="", active=True, on_change=None):
    return SwRow(text, active=active, on_change=on_change, sub=sub)


class SettingsScreen(MDScreen):
    def __init__(self, on_back=None, on_theme=None, on_log=None, on_auto=None,
                 on_logout=None, prefs=None, **kw):
        super().__init__(**kw)
        self.md_bg_color = (0, 0, 0, 0)
        self._on_back = on_back
        self._on_theme = on_theme
        self._on_log = on_log
        self._on_auto = on_auto
        self._on_logout = on_logout
        self._prefs = prefs or {}
        self._dialog = None
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation="vertical")
        self.add_widget(root)

        bar = MDBoxLayout(orientation="horizontal", padding=[dp(4), dp(12), dp(12), 0],
                          size_hint_y=None, height=dp(64))
        back = MDIconButton(icon="arrow-left", icon_size=sp(28),
                            theme_icon_color="Custom", icon_color=S["onSurface"])
        back.bind(on_release=lambda *a: self._back())
        bar.add_widget(back)
        bar.add_widget(label("Settings", role="onSurface", size=22, bold=True))
        root.add_widget(bar)

        box = Panel(bg="surfaceContainerHighest", radius=28, padding=[dp(14), dp(10), dp(14), dp(16)],
                    width=dp(392), height=dp(684), auto=False, spacing=dp(10))
        box.size_hint_x = None
        box.pos_hint = {"center_x": 0.5}
        root.add_widget(box)

        # top app bar "Name" với account_circle trái + logout phải
        inner_bar = MDBoxLayout(orientation="horizontal", padding=[dp(4), 0, dp(4), 0],
                                size_hint_y=None, height=dp(56))
        ac = MDIconButton(icon="account-circle", icon_size=sp(26),
                          theme_icon_color="Custom", icon_color=S["onSurfaceVariant"])
        inner_bar.add_widget(ac)
        self.name_lbl = label("Name", role="onSurface", size=20, bold=True)
        inner_bar.add_widget(self.name_lbl)
        out = MDIconButton(icon="logout", icon_size=sp(26),
                           theme_icon_color="Custom", icon_color=S["error"])
        out.bind(on_release=lambda *a: self._ask_logout())
        inner_bar.add_widget(out)
        box.add_widget(inner_bar)

        self.uid_lbl = label("", role="onSurfaceVariant", size=12)
        box.add_widget(self.uid_lbl)
        box.add_widget(Spacer(height=dp(6), size_hint_y=None))

        # switch chế độ sáng/tối + 2 switch chức năng
        self.row_theme = _switch("Sáng / Tối", active=bool(self._prefs.get("dark", True)),
                                 on_change=lambda v: self._on_theme(bool(v)) if self._on_theme else None)
        box.add_widget(self.row_theme)

        self.row_log = _switch("Nhật ký hoạt động", active=bool(self._prefs.get("log", True)),
                               on_change=lambda v: self._on_log(bool(v)) if self._on_log else None)
        box.add_widget(self.row_log)

        self.row_auto = _switch("Tự kết nối server", active=bool(self._prefs.get("auto", True)),
                                on_change=lambda v: self._on_auto(bool(v)) if self._on_auto else None)
        box.add_widget(self.row_auto)

        # thông tin tài khoản
        info = Panel(bg="surfaceContainerLow", radius=20, padding=[dp(14), dp(12), dp(14), dp(12)],
                     spacing=dp(4))
        r1 = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(30))
        r1.add_widget(label("Số lượng dự đoán còn lại", role="onSurfaceVariant", size=13))
        self.a_picks = label("--", role="onSurface", size=15, halign="right", bold=True)
        self.a_picks.size_hint_x = None
        self.a_picks.width = dp(120)
        r1.add_widget(self.a_picks)
        info.add_widget(r1)
        box.add_widget(info)

        # nhật ký
        log_card = Panel(bg="surfaceContainerLow", radius=20, padding=[dp(14), dp(12), dp(14), dp(12)],
                         spacing=dp(4))
        self.log = label("Chưa có hoạt động.", role="onSurfaceVariant", size=12, wrap=True)
        log_card.add_widget(self.log)
        self._log_card = log_card
        box.add_widget(log_card)

        box.add_widget(Spacer(size_hint_y=(1, None), height=dp(6)))
        box.add_widget(label("ToolTX - Gold edition - v1.2", role="onSurfaceVariant",
                             size=11, halign="center"))

    def _back(self):
        if self._on_back:
            self._on_back()
        else:
            try:
                from kivymd.app import MDApp
                MDApp.get_running_app().back()
            except Exception:
                pass

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

    # ── API cho App ─────────────────────────────────────────────
    def profile(self, name, letter, uid, role, picks_text):
        self.name_lbl.text = name or "Name"
        role_txt = (" · " + role) if role else ""
        self.uid_lbl.text = (uid or "chưa có tài khoản") + role_txt
        self.a_picks.text = picks_text or "--"

    def picks_text(self, txt):
        self.a_picks.text = txt or "--"

    def set_log(self, text):
        if self._prefs.get("log", True):
            self.log.text = text or "Chưa có hoạt động."
        self._log_card.opacity = 1.0 if self._prefs.get("log", True) else 0.0