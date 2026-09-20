# screens/home.py — màn hình chính: dự đoán Tài/Xỉu theo thời gian thực.
from kivy.metrics import dp, sp
from kivy.graphics import Color, RoundedRectangle
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRoundFlatButton
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.screen import MDScreen

from core.config import GOLD, GOLD_DIM, DIM, TXT, RED_T, BLUE_X, GREEN, WARN, IS_ANDROID
from screens.uikit import label, GlassCard, Column, chip


class HomeScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.md_bg_color = (0, 0, 0, 0)
        self._build()

    def _build(self):
        sc = MDScrollView(size_hint=(1, 1))
        col = Column(spacing=dp(14), padding=[dp(18), dp(24), dp(18), dp(16)])
        sc.add_widget(col)
        self.add_widget(sc)

        # header: lời chào + lượt đoán
        head = MDBoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None,
                           height=dp(40))
        self.h_user = label("Xin chào", size=20, bold=True)
        self.pick_badge = chip("Lượt: --", GREEN, (0.16, 0.45, 0.30, 0.35))
        self.pick_badge.size_hint_x = None
        self.pick_badge.width = dp(150)
        head.add_widget(self.h_user)
        head.add_widget(self.pick_badge)
        col.add_widget(head)

        # status: LIVE / kết nối / agent
        st = MDBoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None,
                         height=dp(30))
        self.live_badge = chip("LIVE", RED_T, (0.35, 0.08, 0.10, 0.5), size=12)
        self.live_badge.size_hint_x = None
        self.live_badge.width = dp(72)
        self.conn_badge = chip("OFFLINE", DIM, (0.15, 0.19, 0.28, 0.9), size=12)
        self.conn_badge.size_hint_x = None
        self.conn_badge.width = dp(90)
        self.agent_badge = chip("", DIM, (0, 0, 0, 0), size=12)
        self.agent_badge.size_hint_x = None
        self.agent_badge.width = dp(96)
        self.agent_badge.opacity = 0
        st.add_widget(self.live_badge)
        st.add_widget(self.conn_badge)
        st.add_widget(self.agent_badge)
        col.add_widget(st)

        # thẻ dự đoán
        card = GlassCard(spacing=dp(10))
        col.add_widget(card)
        card.add_widget(label("DỰ ĐOÁN HIỆN TẠI", style="Overline", color=GOLD_DIM,
                              size=12, halign="left", bold=True))
        prow = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(60))
        self.big = label("--", halign="center", bold=True)
        self.big.size_hint_x = 0.52
        self.big.font_size = sp(46)
        self.pct = label("", halign="right", size=15, bold=True)
        prow.add_widget(self.big)
        prow.add_widget(self.pct)
        card.add_widget(prow)

        self.pbar = MDProgressBar(value=0, size_hint_y=None, height=dp(8),
                                  color=GOLD, back_color=(1, 1, 1, 0.08))
        card.add_widget(self.pbar)

        self.conf = label("Đang chờ dữ liệu...", halign="center", color=DIM, size=13)
        card.add_widget(self.conf)

        # kết quả gần đây: dải ô màu T/X + dòng thống kê
        res = GlassCard(spacing=dp(10), padding=[dp(14), dp(12), dp(14), dp(12)])
        col.add_widget(res)
        res.add_widget(label("KẾT QUẢ GẦN NHẤT", style="Overline", color=GOLD_DIM,
                             size=11, halign="left", bold=True))
        self.hist_boxes = MDBoxLayout(orientation="horizontal", spacing=dp(6),
                                      size_hint_y=None, height=dp(34))
        res.add_widget(self.hist_boxes)
        self.hist_sum = label("chờ dữ liệu", wrap=True, color=DIM, size=13)
        res.add_widget(self.hist_sum)

        # cổng lượt
        self.gate_card = GlassCard(bg=(0.36, 0.06, 0.08, 0.55), border=RED_T,
                                   padding=[dp(16), dp(12), dp(16), dp(12)])
        col.add_widget(self.gate_card)
        self.gate_text = label("", wrap=True, color=RED_T, size=14, halign="left")
        self.gate_card.add_widget(self.gate_text)
        self.gate_card.opacity = 0
        self.gate_card.disabled = True

        # lối tắt trình duyệt
        action = GlassCard(spacing=dp(10), padding=[dp(16), dp(14), dp(16), dp(14)])
        col.add_widget(action)
        action.add_widget(label("TRÌNH DUYỆT TỰ ĐỘNG", style="Overline", color=GOLD_DIM,
                                size=12, bold=True))
        if IS_ANDROID:
            desc = "Mở Chromium Fork trên điện thoại để agent chơi giúp bạn."
        else:
            desc = "Mở Chromium Fork trên điện thoại, hoặc Chrome CDP trên máy tính."
        action.add_widget(label(desc, wrap=True, color=DIM, size=13))
        b = MDRoundFlatButton(text="MỞ TRÌNH DUYỆT", size_hint=(1, None), height=dp(48),
                              md_bg_color=(0, 0, 0, 0), line_color=GOLD_DIM,
                              text_color=GOLD, font_size=sp(14))
        b.bind(on_release=self._open_browser)
        action.add_widget(b)

        col.add_widget(MDBoxLayout(size_hint_y=None, height=dp(10)))

    def _open_browser(self, *a):
        from kivymd.app import MDApp
        MDApp.get_running_app().goto("browser")

    # ── API cho App ─────────────────────────────────────────────
    def greet(self, name):
        self.h_user.text = "Xin chào, " + name

    def picks_text(self, txt, warn=False):
        c = WARN if warn else GREEN
        self.pick_badge.children[0].text = txt
        self.pick_badge.children[0].text_color = c
        self.pick_badge.children[1].text_color = c

    def conn(self, text, col):
        self.conn_badge.children[0].text = text
        self.conn_badge.children[0].text_color = col
        self.conn_badge.children[1].text_color = col

    def agent(self, text, col=DIM):
        if text:
            self.agent_badge.opacity = 1
            self.agent_badge.children[0].text = text
            self.agent_badge.children[0].text_color = col
            self.agent_badge.children[1].text_color = col
            self.agent_badge.width = dp(96 + 9 * len(text))
        else:
            self.agent_badge.opacity = 0

    def gate(self, msg):
        if msg:
            self.gate_text.text = msg
            self.gate_card.opacity = 1
            self.gate_card.disabled = False
        else:
            self.gate_card.opacity = 0
            self.gate_card.disabled = True

    def prediction(self, p):
        p = p or {}
        if p.get("pick"):
            pk = str(p["pick"]).upper()
            is_t = pk == "T"
            self.big.text = "TÀI" if is_t else "XỈU"
            self.big.text_color = RED_T if is_t else BLUE_X
            pT = float(p.get("pT") or (60 if is_t else 40))
            pX = 100 - pT
            self.pct.text = "TÀI %02.0f%%  /  XỈU %02.0f%%" % (pT, pX)
            self.pct.text_color = GOLD
            self.pbar.value = min(100.0, max(0.0, pT))
            c = p.get("confidence", p.get("conf"))
            self.conf.text = "Độ tin cậy %02.0f%%" % float(c) if c is not None \
                else "Tỷ lệ TÀI chiếm ưu thế"
            self.conf.text_color = TXT
        self._render_hist(p.get("hist") or p.get("history") or [])

    def _render_hist(self, hist):
        """Dựng dải ô T/X gần nhất + dòng thống kê."""
        self.hist_boxes.clear_widgets()
        self.hist_sum.text = "chờ dữ liệu"
        items = [str(x).upper()[:1] for x in hist[-10:]]
        if not items:
            return
        counts = {"T": 0, "X": 0}
        for s in items:
            counts[s] = counts.get(s, 0) + 1
            color = RED_T if s == "T" else (BLUE_X if s == "X" else (0.16, 0.21, 0.31, 1))
            bg = (0.35, 0.08, 0.10, 0.9) if s == "T" else (
                (0.08, 0.15, 0.32, 0.9) if s == "X" else (0.13, 0.17, 0.26, 0.9))
            self.hist_boxes.add_widget(self._res_box(s, color, bg))
        rest = len(hist) - len(items)
        tail = ("  ... thêm %d ván" % rest) if rest > 0 else ""
        self.hist_sum.text = ("TÀI %d  -  XỈU %d" % (counts.get("T", 0), counts.get("X", 0))) + tail
        self.hist_sum.text_color = TXT

    def _res_box(self, text, color, bg):
        b = MDBoxLayout(size_hint=(None, None), size=(dp(30), dp(30)))
        with b.canvas.before:
            Color(*bg)
            b._r = RoundedRectangle(radius=[dp(8)] * 4)
        b.bind(pos=_res_draw, size=_res_draw)
        t = label(text, color=color, size=15, halign="center", bold=True)
        b.add_widget(t)
        return b


def _div_draw(inst, *a):
    if inst._r is not None:
        inst._r.pos = inst.pos
        inst._r.size = inst.size


def _res_draw(inst, *a):
    if inst._r is not None:
        inst._r.pos = inst.pos
        inst._r.size = inst.size