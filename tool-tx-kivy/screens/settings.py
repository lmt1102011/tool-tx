# screens/settings.py — tài khoản, số lượt, danh sách thao tác + đăng xuất.
from kivy.metrics import dp, sp
from kivy.graphics import Color, Ellipse
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRectangleFlatButton
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.screen import MDScreen

from core.config import GOLD, GOLD_DIM, DIM, TXT, RED_T
from screens.uikit import label, GlassCard, Column


class SettingsScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.md_bg_color = (0, 0, 0, 0)
        self._build()

    def _build(self):
        sc = MDScrollView(size_hint=(1, 1))
        col = Column(spacing=dp(14), padding=[dp(18), dp(24), dp(18), dp(16)])
        sc.add_widget(col)
        self.add_widget(sc)

        col.add_widget(label("Tài khoản", style="H5", color=GOLD, size=24, bold=True))

        prof = GlassCard(spacing=dp(16))
        col.add_widget(prof)
        row = MDBoxLayout(orientation="horizontal", spacing=dp(16), size_hint_y=None,
                          height=dp(72))
        self.avatar = MDBoxLayout(size_hint=(None, None), size=(dp(64), dp(64)),
                                  pos_hint={"center_y": 0.5})
        with self.avatar.canvas.before:
            self.avatar._c = Color(*GOLD)
            self.avatar._e = Ellipse(pos=self.avatar.pos, size=self.avatar.size)
        self.avatar.bind(pos=self._av_draw, size=self._av_draw)
        self.av_lbl = label("K", halign="center", bold=True)
        self.av_lbl.font_size = sp(30)
        self.av_lbl.text_color = (0.04, 0.05, 0.09, 1)
        self.avatar.add_widget(self.av_lbl)
        row.add_widget(self.avatar)
        inf = MDBoxLayout(orientation="vertical", spacing=dp(2), size_hint_y=None,
                          height=dp(72), pos_hint={"center_y": 0.5})
        self.p_name = label("Chưa đăng nhập", size=19, bold=True)
        self.p_uid = label("", color=DIM, size=12)
        self.p_role = label("", color=DIM, size=11)
        inf.add_widget(self.p_name)
        inf.add_widget(self.p_uid)
        inf.add_widget(self.p_role)
        row.add_widget(inf)
        prof.add_widget(row)

        info = GlassCard(spacing=dp(10), padding=[dp(16), dp(14), dp(16), dp(14)])
        col.add_widget(info)
        info.add_widget(label("THÔNG TIN", style="Overline", color=GOLD_DIM, size=12,
                              bold=True))
        r1 = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28))
        r1.add_widget(label("Số lượt đoán còn lại", color=DIM, size=14))
        self.a_picks = label("--", halign="right", bold=True, size=16)
        self.a_picks.size_hint_x = None
        self.a_picks.width = dp(220)
        r1.add_widget(self.a_picks)
        info.add_widget(r1)

        log_card = GlassCard(spacing=dp(8), padding=[dp(16), dp(14), dp(16), dp(14)])
        col.add_widget(log_card)
        log_card.add_widget(label("NHẬT KÝ HOẠT ĐỘNG", style="Overline", color=GOLD_DIM,
                                  size=12, bold=True))
        ls = MDScrollView(size_hint=(1, None), height=dp(220))
        self.log = label("Chưa có hoạt động.", wrap=True, markup=True, size=12)
        self.log.text_color = DIM
        ls.add_widget(self.log)
        log_card.add_widget(ls)

        self.btn_logout = MDRectangleFlatButton(text="ĐĂNG XUẤT", size_hint=(1, None),
                                                height=dp(50),
                                                md_bg_color=(0, 0, 0, 0),
                                                line_color=RED_T, text_color=RED_T,
                                                font_size=sp(14))
        self.btn_logout.bind(on_release=lambda *a: self._logout())
        col.add_widget(self.btn_logout)

        col.add_widget(label("ToolTX · Gold edition · v1.0", halign="center",
                             color=DIM, size=11))
        col.add_widget(MDBoxLayout(size_hint_y=None, height=dp(10)))

    def _logout(self):
        from kivymd.app import MDApp
        MDApp.get_running_app().do_logout()

    # ── API cho App ─────────────────────────────────────────────
    def profile(self, name, letter, uid, role, picks_text):
        self.p_name.text = name or "Chưa đăng nhập"
        self.av_lbl.text = letter or "K"
        self.p_uid.text = uid or "chưa có tài khoản"
        self.p_role.text = role or ""
        self.a_picks.text = picks_text or "--"

    def picks_text(self, txt):
        self.a_picks.text = txt

    def set_log(self, text):
        self.log.text = text

    def _av_draw(self, inst, *a):
        inst._e.pos = inst.pos
        inst._e.size = inst.size