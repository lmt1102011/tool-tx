# screens/topup.py — Màn Top Up (M3): chọn ngân hàng + popup dưới để chuyển khoản.
from kivy.metrics import dp, sp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton, MDFillRoundFlatButton, MDTextButton
from kivymd.uix.label import MDIcon
from kivymd.uix.dialog import MDDialog
from kivy.uix.behaviors import ButtonBehavior
from kivymd.uix.behaviors import RectangularRippleBehavior
from kivymd.uix.screen import MDScreen

from core.config import BANKS, WEB_TOPUP
from core.m3 import S
from screens.uikit import label, Panel, Spacer


class BankRow(RectangularRippleBehavior, ButtonBehavior, MDBoxLayout):
    """List item 72dp: icon tròn primaryContainer + tên bank + mũi tên xuống."""

    def __init__(self, bank_key, bank_name, on_pick=None, **kw):
        super().__init__(orientation="horizontal", spacing=dp(16), size_hint_y=None,
                         height=dp(72), padding=[dp(8), 0, dp(8), 0], **kw)
        self._cb = on_pick
        circle = MDBoxLayout(size_hint=(None, None), size=(dp(40), dp(40)),
                             pos_hint={"center_y": 0.5})
        with circle.canvas.before:
            from kivy.graphics import Color, Ellipse
            Color(*S["primaryContainer"])
            self._e = Ellipse(pos=circle.pos, size=circle.size)
        circle.bind(pos=self._sync, size=self._sync)
        ic = MDIcon(icon="account-balance", theme_text_color="Custom",
                    text_color=S["onPrimaryContainer"], font_size=sp(24),
                    pos_hint={"center_x": 0.5, "center_y": 0.5})
        circle.add_widget(ic)
        self.add_widget(circle)
        self.add_widget(label(bank_name, role="onSurface", size=16))
        md = MDIcon(icon="keyboard-arrow-down", theme_text_color="Custom",
                    text_color=S["onSurfaceVariant"], font_size=sp(28),
                    size_hint_x=None, width=dp(40))
        self.add_widget(md)
        self.bind(on_release=self._fire)
        self._circle = circle

    def _sync(self, inst, *a):
        self._e.pos = inst.pos
        self._e.size = inst.size

    def _fire(self, *a):
        if self._cb:
            self._cb()


class TopUpScreen(MDScreen):
    def __init__(self, on_open_web=None, on_done=None, **kw):
        super().__init__(**kw)
        self.md_bg_color = (0, 0, 0, 0)
        self._on_open_web = on_open_web
        self._on_done = on_done
        self._dialog = None
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation="vertical")
        self.add_widget(root)

        # top app bar: back + title
        bar = MDBoxLayout(orientation="horizontal", padding=[dp(4), dp(12), dp(12), 0],
                          size_hint_y=None, height=dp(64))
        back = MDIconButton(icon="arrow-left", icon_size=sp(28),
                            theme_icon_color="Custom", icon_color=S["onSurface"])
        back.bind(on_release=lambda *a: self.open_back())
        bar.add_widget(back)
        bar.add_widget(label("Top Up", role="onSurface", size=22, bold=True))
        root.add_widget(bar)

        box = Panel(bg="surfaceContainerHighest", radius=28, padding=[dp(12), dp(16), dp(12), dp(16)],
                    width=dp(392), height=dp(684), auto=False, spacing=dp(14))
        box.size_hint_x = None
        box.pos_hint = {"center_x": 0.5}
        root.add_widget(box)

        self._bank_rows = []
        for key, name in BANKS:
            r = BankRow(key, name, on_pick=lambda k=key, n=name: self._pick(k, n))
            box.add_widget(r)
            self._bank_rows.append(r)

        inner = Panel(bg="surfaceContainerLow", radius=20, padding=[dp(16), dp(20), dp(16), dp(20)],
                      height=dp(320), auto=False, spacing=dp(10))
        inner.add_widget(Spacer(height=dp(6), size_hint_y=None))
        inner.add_widget(label("Nạp tiền qua ngân hàng", role="onSurface", size=16, bold=True))
        inner.add_widget(label("Chọn ngân hàng bên trên, nhận số tài khoản và "
                               "chuyển khoản đúng nội dung. Credit được cộng sau khi "
                               "server xác nhận.", role="onSurfaceVariant", size=13,
                               wrap=True, line_h=1.4))
        add = MDFillRoundFlatButton(icon="add", size_hint=(1, None), height=dp(56),
                                    md_bg_color=S["primary"], text_color=S["onPrimary"])
        add.bind(on_release=lambda *a: self.open_web())
        inner.add_widget(add)
        box.add_widget(inner)

        box.add_widget(Spacer(size_hint_y=(1, None), height=dp(6)))
        box.add_widget(label("© ToolTX - Gold edition", role="onSurfaceVariant",
                             size=11, halign="center"))

    def open_back(self):
        # main đăng ký handler back; nếu chưa thì tự back qua stack
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

    def get_web(self):
        return WEB_TOPUP