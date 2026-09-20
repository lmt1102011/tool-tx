# screens/admin.py — bảng quản trị (giống admin.html trên web):
# thống kê + giá mỗi lượt, thêm user, danh sách user (cộng/trừ lượt, đổi quyền, xóa).
from functools import partial

from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRoundFlatButton, MDRaisedButton, MDTextButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField

from core.config import GOLD, GOLD_DIM, DIM, TXT, RED_T, GREEN, WARN
from screens.uikit import label, GlassCard, Column, chip


def _fmt_money(v):
    return "{:,}".format(int(v or 0)).replace(",", ".") + " VNĐ"


class AdminScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.md_bg_color = (0, 0, 0, 0)
        self.users = []
        self.rate = 5000
        self._dlg = None
        self._dlg_mode = "pick"
        self._dlg_uid = None
        self._build()

    def _build(self):
        sc = MDScrollView(size_hint=(1, 1))
        col = Column(spacing=dp(12), padding=[dp(16), dp(20), dp(16), dp(16)])
        sc.add_widget(col)
        self.add_widget(sc)

        col.add_widget(label("Quản trị", style="H5", color=GOLD, size=24, bold=True))
        self.sub = label("Chào admin — quản lý tài khoản, lượt đoán và giá mỗi lượt.",
                         wrap=True, color=DIM, size=12)
        col.add_widget(self.sub)

        # thống kê
        stats = GlassCard(spacing=dp(10), padding=[dp(16), dp(14), dp(16), dp(14)])
        col.add_widget(stats)
        r1 = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28))
        r1.add_widget(label("Tổng người dùng (không admin)", color=DIM, size=13))
        self.stat_users = label("--", halign="right", bold=True)
        self.stat_users.size_hint_x = None
        self.stat_users.width = dp(90)
        r1.add_widget(self.stat_users)
        stats.add_widget(r1)
        r2 = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28))
        r2.add_widget(label("Tổng lượt đoán đã cấp", color=DIM, size=13))
        self.stat_picks = label("--", halign="right", bold=True)
        self.stat_picks.size_hint_x = None
        self.stat_picks.width = dp(110)
        r2.add_widget(self.stat_picks)
        stats.add_widget(r2)
        r3 = MDBoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None,
                         height=dp(44))
        r3.add_widget(label("Giá / lượt đoán (VNĐ)", color=DIM, size=13))
        self.rate_field = MDTextField(hint_text="VNĐ", input_filter="int",
                                      size_hint=(None, None), width=dp(110),
                                      height=dp(44), font_size=sp(15))
        self.rate_field.text = "5000"
        b_rate = MDRoundFlatButton(text="Lưu", size_hint=(None, None),
                                   width=dp(64), height=dp(40),
                                   md_bg_color=(0, 0, 0, 0), line_color=GOLD_DIM,
                                   text_color=GOLD, font_size=sp(12))
        b_rate.bind(on_release=lambda *a: self._save_rate())
        r3.add_widget(self.rate_field)
        r3.add_widget(b_rate)
        stats.add_widget(r3)

        # thêm user
        add_card = GlassCard(spacing=dp(10), padding=[dp(16), dp(14), dp(16), dp(14)])
        col.add_widget(add_card)
        add_card.add_widget(label("THÊM USER MỚI", style="Overline", color=GOLD_DIM,
                                  size=12, bold=True))
        self.nu_user = MDTextField(hint_text="Username (3–20 ký tự)",
                                   size_hint=(1, None), height=dp(44), font_size=sp(14))
        self.nu_pass = MDTextField(hint_text="Mật khẩu (≥ 6 ký tự)", password=True,
                                   size_hint=(1, None), height=dp(44), font_size=sp(14))
        self.nu_picks = MDTextField(hint_text="Số lượt đoán cấp", input_filter="int",
                                    size_hint=(1, None), height=dp(44), font_size=sp(14))
        self.nu_picks.text = "10"
        b_add = MDRaisedButton(text="TẠO TÀI KHOẢN", size_hint=(1, None), height=dp(44),
                               md_bg_color=GOLD, text_color=(0.04, 0.05, 0.09, 1),
                               font_size=sp(13))
        b_add.bind(on_release=lambda *a: self._add_user())
        add_card.add_widget(self.nu_user)
        add_card.add_widget(self.nu_pass)
        add_card.add_widget(self.nu_picks)
        add_card.add_widget(b_add)

        # tìm kiếm
        self.search_field = MDTextField(hint_text="Tìm theo username...",
                                        size_hint=(1, None), height=dp(44),
                                        font_size=sp(14))
        self.search_field.bind(text=lambda *a: self.rebuild_rows())
        col.add_widget(self.search_field)

        # danh sách user
        list_card = GlassCard(spacing=dp(6), padding=[dp(12), dp(10), dp(12), dp(10)])
        col.add_widget(list_card)
        list_card.add_widget(label("DANH SÁCH USER", style="Overline", color=GOLD_DIM,
                                   size=12, bold=True))
        self.list_box = Column(spacing=dp(6))
        list_card.add_widget(self.list_box)

        col.add_widget(MDBoxLayout(size_hint_y=None, height=dp(8)))

    # ── dữ liệu ────────────────────────────────────────────────
    def load(self, users, rate):
        self.users = users or {}
        self.rate = int(rate or 5000)
        self.rate_field.text = str(self.rate)
        non_admin = [u for u in self.users.values() if (u or {}).get("role") != "admin"]
        self.stat_users.text = str(len(self.users))
        self.stat_picks.text = str(sum(int((u or {}).get("balanceFields") or 0)
                                       for u in non_admin))
        self.rebuild_rows()

    def rebuild_rows(self):
        q = (self.search_field.text or "").strip().lower()
        self.list_box.clear_widgets()
        items = [u for u in self.users.values()
                 if (u or {}).get("role") != "admin"
                 and q in str((u or {}).get("username") or "").lower()]
        if not items:
            self.list_box.add_widget(label("Chưa có user nào.", color=DIM, size=12))
            return
        seen = {}
        for u in sorted(items, key=lambda x: (x or {}).get("lastSeen") or 0,
                        reverse=True):
            uid = None
            for k, v in self.users.items():
                if v is u:
                    uid = k
                    break
            if not uid or uid in seen:
                continue
            seen[uid] = True
            self.list_box.add_widget(self._make_row(uid, u))

    def _make_row(self, uid, u):
        row = MDBoxLayout(orientation="horizontal", spacing=dp(6), size_hint_y=None,
                          height=dp(54))
        name = MDBoxLayout(orientation="vertical", size_hint_y=None, height=dp(54))
        nm = label(str(u.get("username") or "?"), size=15, bold=True)
        dn = label(str(u.get("displayName") or ""), color=DIM, size=10)
        name.add_widget(nm)
        name.add_widget(dn)
        picks = int(u.get("balanceFields") or 0)
        pill = chip(("vô hạn" if u.get("role") == "admin" else str(picks)),
                    RED_T if picks <= 0 else GREEN,
                    (0.35, 0.08, 0.10, 0.5) if picks <= 0 else (0.16, 0.45, 0.30, 0.35),
                    size=12)
        pill.size_hint_x = None
        pill.width = dp(64)
        row.add_widget(name)
        row.add_widget(pill)
        b1 = MDRoundFlatButton(text="Lượt", size_hint=(None, None), width=dp(58),
                               height=dp(34), md_bg_color=(0, 0, 0, 0),
                               line_color=GOLD_DIM, text_color=GOLD, font_size=sp(11))
        b1.bind(on_release=partial(self._dlg_balance, uid, u))
        b2 = MDRoundFlatButton(text="Quyền", size_hint=(None, None), width=dp(58),
                               height=dp(34), md_bg_color=(0, 0, 0, 0),
                               line_color=(0.44, 0.55, 0.75, 0.5), text_color=(0.75, 0.83, 0.98, 1),
                               font_size=sp(11))
        b2.bind(on_release=partial(self._dlg_role, uid, u))
        b3 = MDRoundFlatButton(text="Xóa", size_hint=(None, None), width=dp(52),
                               height=dp(34), md_bg_color=(0, 0, 0, 0),
                               line_color=RED_T, text_color=RED_T, font_size=sp(11))
        b3.bind(on_release=partial(self._dlg_del, uid, u))
        row.add_widget(b1)
        row.add_widget(b2)
        row.add_widget(b3)
        return row

    # ── hành động ──────────────────────────────────────────────
    def _exec(self, fn, ok_msg):
        app = MDApp.get_running_app()
        app._run(
            fn,
            lambda v: Clock.schedule_once(lambda dt: self._after(ok_msg)),
            lambda e: Clock.schedule_once(lambda dt: self._after("Lỗi: " + str(e), err=True)),
        )

    def _after(self, msg, err=False):
        if msg:
            self.sub.text = msg
            self.sub.text_color = RED_T if err else DIM
        if not err:
            self.reload()

    def reload(self):
        MDApp.get_running_app().admin_refresh()

    def _save_rate(self):
        v = self.rate_field.text.strip()
        if not v.isdigit() or int(v) < 1:
            self.sub.text = "Giá phải là số >= 1"
            return
        self._exec(lambda: MDApp.get_running_app().auth.set_rate(int(v)),
                   "Đã lưu giá " + _fmt_money(v) + " / lượt")

    def _add_user(self):
        u = (self.nu_user.text or "").strip().lower()
        p = self.nu_pass.text or ""
        pk = self.nu_picks.text.strip()
        if not u or len(p) < 6:
            self.sub.text = "Username + mật khẩu ≥ 6 ký tự"
            return
        pk = int(pk) if pk.isdigit() else 0
        self._exec(lambda: MDApp.get_running_app().auth.register_with_picks(u, p, "", pk),
                   "Đã tạo %s + %d lượt" % (u, pk))
        self.nu_user.text, self.nu_pass.text, self.nu_picks.text = "", "", "10"

    def _dlg_balance(self, uid, u, *a):
        self._dlg_uid = uid
        self._dlg_user = str(u.get("username") or "?")
        self._dlg_mode = "pick"
        box = MDBoxLayout(orientation="vertical", spacing=dp(10), adaptive_size=True)
        box.add_widget(label("Người dùng: " + self._dlg_user, halign="left", size=14))
        tabs = MDBoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None,
                           height=dp(34))
        t_money = MDTextButton(text="Bằng tiền", theme_text_color="Custom",
                               text_color=DIM, on_release=lambda *_x: self._set_mode(box, "money"))
        t_pick = MDTextButton(text="Số lượt", theme_text_color="Custom",
                              text_color=DIM, on_release=lambda *_x: self._set_mode(box, "pick"))
        tabs.add_widget(t_money)
        tabs.add_widget(t_pick)
        box.add_widget(tabs)
        self._bal_field = MDTextField(hint_text="vd: 5000 (hoặc -5000)", input_filter="float",
                                      size_hint=(1, None), height=dp(46), font_size=sp(14))
        box.add_widget(self._bal_field)
        self._bal_mode_lbl = label("Số lượt đoán (dấu - để trừ), mỗi lượt = " +
                                   _fmt_money(self.rate), wrap=True, color=DIM, size=11)
        box.add_widget(self._bal_mode_lbl)
        self._open_dlg("Cộng / trừ lượt đoán", box,
                       [self._ok_balance, self._cancel_dlg])

    def _set_mode(self, box, mode):
        self._dlg_mode = mode
        if mode == "money":
            self._bal_field.input_filter = "float"
            self._bal_field.hint_text = "vd: 5000 (hoặc -5000)"
            self._bal_mode_lbl.text = ("Quy đổi theo giá %s / lượt. "
                                       "Số tiền âm sẽ trừ tương ứng." % _fmt_money(self.rate))
        else:
            self._bal_field.input_filter = "int"
            self._bal_field.hint_text = "vd: 10 hoặc -3"
            self._bal_mode_lbl.text = "Lượt đoán (dấu - để trừ)"

    def _ok_balance(self, *a):
        raw = (self._bal_field.text or "").strip()
        if not raw:
            return
        app = MDApp.get_running_app()
        try:
            v = -abs(float(raw)) if raw.startswith("-") else abs(float(raw))
        except Exception:
            self.sub.text = "Số nhập không hợp lệ"
            return
        if self._dlg_mode == "money":
            add = int(v // self.rate) if v >= 0 else -int(abs(v) // self.rate)
            note = _fmt_money(round(add * self.rate, 0))
        else:
            add = int(v)
            note = str(add) + " lượt"
        if add == 0:
            self.sub.text = "Giá trị quá nhỏ (< 1 lượt)"
            return
        self._close_dlg()
        self._exec(lambda: self._apply_balance(app, add), "Đã cập nhật: " + note)

    def _apply_balance(self, app, add):
        cur = 0
        for k, v in (app.admin_users or {}).items():
            if k == self._dlg_uid:
                cur = int(v.get("balanceFields") or 0)
                break
        return app.auth.update_balance(self._dlg_uid, max(0, cur + add))

    def _dlg_role(self, uid, u, *a):
        next_role = "user" if u.get("role") == "admin" else "admin"
        box = MDBoxLayout(orientation="vertical", spacing=dp(8), adaptive_size=True)
        box.add_widget(label("Đổi quyền cho %s thành %s?" % (u.get("username"), next_role.upper()),
                             wrap=True, size=14, halign="left"))
        self._role_uid = uid
        self._role_next = next_role
        self._open_dlg("Đổi quyền", box, [self._ok_role, self._cancel_dlg])

    def _ok_role(self, *a):
        self._close_dlg()
        self._exec(lambda: MDApp.get_running_app().auth.update_role(self._role_uid,
                                                                    self._role_next),
                   "Đã đổi quyền thành " + self._role_next.upper())

    def _dlg_del(self, uid, u, *a):
        box = MDBoxLayout(orientation="vertical", spacing=dp(8), adaptive_size=True)
        box.add_widget(label("Xóa tài khoản \"%s\"? Người này sẽ không đăng nhập được nữa." % u.get("username"),
                             wrap=True, size=14, halign="left"))
        self._del_uid = uid
        self._open_dlg("Xóa user", box, [self._ok_del, self._cancel_dlg])

    def _ok_del(self, *a):
        self._close_dlg()
        self._exec(lambda: MDApp.get_running_app().auth.delete_user(self._del_uid),
                   "Đã xóa user")

    # ── dialog chung ────────────────────────────────────────────
    def _open_dlg(self, title, content, actions):
        self._cancel_dlg()
        dlg = MDDialog(title=title, type="custom", content_cls=content,
                       size_hint=(0.92, None), auto_dismiss=False)
        dlg.buttons = [
            MDRaisedButton(text="Hủy", text_color=DIM,
                           on_release=lambda *a: self._cancel_dlg()),
            MDRaisedButton(text="Áp dụng", md_bg_color=GOLD, text_color=(0.04, 0.05, 0.09, 1),
                           on_release=actions[0]),
        ]
        dlg.open()
        self._dlg = dlg

    def _cancel_dlg(self, *a):
        if self._dlg is not None:
            try:
                self._dlg.dismiss()
            except Exception:
                pass
            self._dlg = None

    def _close_dlg(self):
        self._cancel_dlg()