from kivy.metrics import dp, sp
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton, MDFillRoundFlatButton, MDTextButton
from kivymd.uix.label import MDIcon
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.screen import MDScreen

from core.config import BANKS
from core.m3 import S
from screens.uikit import t, spacer, PAD


class BankRow(ButtonBehavior, MDBoxLayout):
    def __init__(self, bank_key, bank_name, on_pick=None, **kw):
        super().__init__(orientation="horizontal", spacing=dp(16),
                         size_hint_y=None, height=dp(64),
                         padding=[dp(16), dp(8), dp(16), dp(8)], **kw)
        self._cb = on_pick

        circle = MDCard(style="filled", radius=[dp(20)] * 4,
                        size_hint=(None, None), size=(dp(40), dp(40)),
                        md_bg_color=S["primaryContainer"])
        ic = MDIcon(icon="account-balance", font_size=sp(20),
                    pos_hint={"center_x": 0.5, "center_y": 0.5})
        ic.theme_text_color = "Custom"
        ic.text_color = S["onPrimaryContainer"]
        circle.add_widget(ic)
        self.add_widget(circle)

        self.add_widget(t(bank_name, size=16, role="onSurface"))
        self.add_widget(Widget())

        ic2 = MDIcon(icon="keyboard-arrow-down", font_size=sp(28),
                     size_hint_x=None, width=dp(40),
                     pos_hint={"center_y": 0.5})
        ic2.theme_text_color = "Custom"
        ic2.text_color = S["onSurfaceVariant"]
        self.add_widget(ic2)

        self.bind(on_release=lambda *a: self._cb() if self._cb else None)


class TopUpScreen(MDScreen):
    def __init__(self, on_open_web=None, on_done=None, **kw):
        super().__init__(**kw)
        self._on_open_web = on_open_web
        self._on_done = on_done
        self._dialog = None
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation="vertical", padding=0, spacing=0)
        self.add_widget(root)

        bar = MDBoxLayout(orientation="horizontal", padding=[dp(4), dp(12), dp(12), 0],
                          size_hint_y=None, height=dp(64), spacing=dp(8))
        back = MDIconButton(icon="arrow-left", icon_size=sp(24),
                            theme_icon_color="Custom", icon_color=S["onSurface"])
        back.bind(on_release=lambda *a: self.open_back())
        bar.add_widget(back)
        bar.add_widget(t("Top Up", size=22, bold=True, role="onSurface"))
        root.add_widget(bar)

        body = MDBoxLayout(orientation="vertical", spacing=dp(16),
                           padding=[dp(12), dp(8), dp(12), dp(8)])
        root.add_widget(body)

        bank_card = MDCard(style="filled", radius=[dp(20)] * 4,
                           size_hint_y=None, adaptive_height=True,
                           padding=[dp(4), dp(8)], spacing=dp(2),
                           orientation="vertical",
                           md_bg_color=S["surfaceContainerHigh"])
        for key, name in BANKS:
            r = BankRow(key, name, on_pick=lambda k=key, n=name: self._pick(k, n))
            bank_card.add_widget(r)
        body.add_widget(bank_card)

        info = MDCard(style="elevated", radius=[dp(20)] * 4,
                      padding=[dp(20), dp(20)], spacing=dp(12),
                      orientation="vertical", size_hint_y=None, height=dp(240))
        info.add_widget(t("Nap tien qua ngan hang", size=16, bold=True, role="onSurface"))
        info.add_widget(t("Chon ngan hang ben tren, nhan so tai khoan va "
                          "chuyen khoan dung noi dung. Credit duoc cong sau khi "
                          "server xac nhan.", size=13, role="onSurfaceVariant", wrap=True))
        btn = MDFillRoundFlatButton(text="  Mo trang nap tien", icon="add",
                                    size_hint=(1, None), height=dp(56),
                                    md_bg_color=S["primary"], text_color=S["onPrimary"],
                                    font_size=sp(15))
        btn.bind(on_release=lambda *a: self.open_web())
        info.add_widget(btn)
        body.add_widget(info)

        body.add_widget(Widget())
        body.add_widget(t("ToolTX - Gold edition", size=11, role="onSurfaceVariant",
                           halign="center"))

    def open_back(self):
        try:
            from kivymd.app import MDApp
            MDApp.get_running_app().back()
        except Exception:
            pass

    def open_web(self):
        if self._on_open_web:
            self._on_open_web()

    def _pick(self, key, name):
        if self._dialog:
            try:
                self._dialog.dismiss()
            except Exception:
                pass
        self._dialog = MDDialog(
            title="CHUYEN KHOAN",
            text=("%s\n\nChuyen khoan toi tai khoan may chu, noi dung ghi ro "
                  "so dien thoai/tai khoan cua ban de server xac nhan.\n\n"
                  "Mo trang nap tien de xem so tai khoan va bang gia." % name),
            buttons=[
                MDTextButton(text="HUY", on_release=lambda *a: self._dlg(False)),
                MDTextButton(text="MO WEB NAP", bold=True,
                             on_release=lambda *a: self._dlg(True)),
            ],
        )
        self._dialog.open()

    def _dlg(self, do_web):
        try:
            self._dialog.dismiss()
        except Exception:
            pass
        if do_web and self._on_open_web:
            self._on_open_web()
        elif self._on_done:
            self._on_done()
