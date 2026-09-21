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
from screens.uikit import t, spacer


class BankRow(ButtonBehavior, MDBoxLayout):
    def __init__(self, bank_key, bank_name, on_pick=None, **kw):
        super().__init__(orientation="horizontal", spacing=dp(16),
                         size_hint_y=None, height=dp(72),
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

        panel = MDCard(radius=[dp(28)] * 4, size_hint=(None, None),
                       size=(dp(392), dp(684)),
                       pos_hint={"center_x": 0.5},
                       padding=[dp(12), dp(16), dp(12), dp(16)],
                       spacing=dp(14), orientation="vertical",
                       md_bg_color=S["surfaceContainerHighest"])
        root.add_widget(panel)

        for key, name in BANKS:
            r = BankRow(key, name, on_pick=lambda k=key, n=name: self._pick(k, n))
            panel.add_widget(r)

        info = MDCard(style="elevated", radius=[dp(20)] * 4,
                      padding=[dp(16), dp(20), dp(16), dp(20)],
                      spacing=dp(10), orientation="vertical", size_hint_y=None, height=dp(280))
        info.add_widget(spacer(6))
        info.add_widget(t("Nạp tiền qua ngân hàng", size=16, bold=True, role="onSurface"))
        info.add_widget(t("Chọn ngân hàng bên trên, nhận số tài khoản và "
                          "chuyển khoản đúng nội dung. Credit được cộng sau khi "
                          "server xác nhận.", size=13, role="onSurfaceVariant", wrap=True))
        btn = MDFillRoundFlatButton(text="  Mở trang nạp tiền", icon="add",
                                    size_hint=(1, None), height=dp(56),
                                    md_bg_color=S["primary"], text_color=S["onPrimary"],
                                    font_size=sp(15))
        btn.bind(on_release=lambda *a: self.open_web())
        info.add_widget(btn)
        panel.add_widget(info)
        panel.add_widget(spacer(6))
        panel.add_widget(t("© ToolTX - Gold edition", size=11, role="onSurfaceVariant",
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
            title="CHUYỂN KHOẢN",
            text=("%s\n\nChuyển khoản tới tài khoản máy chủ, nội dung ghi rõ "
                  "số điện thoại/tài khoản của bạn để server xác nhận.\n\n"
                  "Mở trang nạp tiền để xem số tài khoản và bảng giá." % name),
            buttons=[
                MDTextButton(text="HỦY", on_release=lambda *a: self._dlg(False)),
                MDTextButton(text="MỞ WEB NẠP", bold=True,
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
