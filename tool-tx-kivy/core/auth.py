# core/auth.py — AuthManager: lớp mỏng bọc fb.py (Firebase Auth REST + RTDB),
# để màn hình/controller dùng chung một interface rõ ràng.
import fb


class AuthManager:
    def login(self, username, password):
        return fb.login(username, password)

    def register(self, username, password, display_name=""):
        return fb.register(username, password, display_name)

    def logout(self):
        fb.logout()

    def current(self):
        return dict(fb._session or {})

    def logged_in(self):
        return fb.logged_in()

    def user_data(self):
        sess = fb._session or {}
        uid = sess.get("uid")
        if not uid:
            return None
        return fb.get_user_data(uid, sess.get("idToken"))

    def picks(self):
        return fb.picks(self.user_data())

    def refresh_id_token(self):
        return fb.refresh_id_token()

    def set_session_path(self, path):
        fb.set_session_path(path)
        fb.load_session()