# fb.py — Firebase Auth (REST) + Realtime Database dùng cho app Kivy.
# Giống hệt logic web (public/fbase.js) nhưng bằng REST thuần — chạy được desktop lẫn Android.

import json
import os
import threading
import time
import urllib.parse
import urllib.request

try:
    import requests
    HAS_REQUESTS = True
except Exception:  # pragma: no cover
    HAS_REQUESTS = False

API_KEY = "AIzaSyCN8VEuBWsnXrZqSWJYrFkZd7ckdFIqbCg"
DB_URL = "https://tool-tx-by-lmt-default-rtdb.firebaseio.com"
_IDP = "https://identitytoolkit.googleapis.com/v1/accounts"
_SECT = "https://securetoken.googleapis.com/v1/token"

_lock = threading.Lock()
_session = {}            # in-memory: idToken/uid/dt
_session_path = None     # file json để nhớ refresh token


class FbError(Exception):
    pass


def _post(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8")), 200
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8")), e.code
        except Exception:
            return {"error": {"message": str(e)}}, e.code
    except Exception as e:
        raise FbError("Mất kết nối Firebase: " + str(e))


def _http_get(url):
    try:
        req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8")), r.status
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8")), e.code
        except Exception:
            return None, e.code
    except Exception as e:
        raise FbError("Mất kết nối Firebase: " + str(e))


def _http_write(url, payload, method="PATCH"):
    """PATCH/DELETE/DELETE dữ liệu (admin cập nhật user / settings)."""
    if method == "DELETE":
        req = urllib.request.Request(url, method="DELETE")
        body = None
    else:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, method=method,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8")
            return (json.loads(raw) if raw.strip() else {}), r.status
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8")), e.code
        except Exception:
            return {"error": {"message": str(e)}}, e.code
    except Exception as e:
        raise FbError("Mất kết nối Firebase: " + str(e))


def _msg(code_or_text):
    m = str(code_or_text or "")
    if "email-already-in-use" in m or "EMAIL_EXISTS" in m:
        return "Email đã được sử dụng"
    if "wrong-password" in m or "invalid-credential" in m or "INVALID_LOGIN_CREDENTIALS" in m:
        return "Sai mật khẩu"
    if "user-not-found" in m:
        return "Tài khoản không tồn tại"
    if "invalid-email" in m:
        return "Địa chỉ email không hợp lệ"
    if "weak-password" in m:
        return "Mật khẩu quá yếu"
    if "too-many-requests" in m:
        return "Quá nhiều lần thử, hãy đợi vài phút"
    if "EMAIL_NOT_FOUND" in m or "INVALID_PASSWORD" in m:
        return "Sai tài khoản hoặc mật khẩu"
    if "INVALID_REFRESH_TOKEN" in m or "TOKEN_EXPIRED" in m:
        return "Phiên đã hết hạn — đăng nhập lại"
    if "operation-not-allowed" in m:
        return "Đăng ký đang tạm tắt"
    return m or "Có lỗi xảy ra"


def email_for(username):
    return str(username or "").strip().lower().replace(" ", "") + "@tooltx.app"


def set_session_path(path):
    global _session_path
    _session_path = path


def load_session():
    global _session
    _session = {}
    if not _session_path or not os.path.exists(_session_path):
        return _session
    try:
        with open(_session_path, "r", encoding="utf-8") as f:
            _session = json.load(f)
    except Exception:
        _session = {}
    return _session


def save_session():
    if not _session_path:
        return
    try:
        os.makedirs(os.path.dirname(_session_path) or ".", exist_ok=True)
        with open(_session_path, "w", encoding="utf-8") as f:
            json.dump(_session, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def refresh_id_token():
    """Lấy idToken mới từ refreshToken đã lưu (server cứ 1h yêu cầu token mới)."""
    with _lock:
        rt = _session.get("refreshToken")
        if not rt:
            raise FbError("Chưa đăng nhập")
    j, code = _post(_SECT + "?key=" + API_KEY, {"grant_type": "refresh_token", "refresh_token": rt})
    if code != 200 or not j.get("id_token"):
        raise FbError(_msg(j.get("error", {}).get("message", "")))
    with _lock:
        _session["idToken"] = j["id_token"]
        _session["uid"] = j.get("user_id", _session.get("uid", ""))
        save_session()
    return j["id_token"]


def id_token():
    with _lock:
        tok = _session.get("idToken")
    if not tok:
        raise FbError("Chưa đăng nhập")
    return tok


def get_user_data(uid, tok):
    j, code = _http_get(DB_URL + "/users/" + urllib.parse.quote(uid) + ".json?auth=" + urllib.parse.quote(tok))
    if code != 200:
        return None
    return j  # None nếu chưa tồn tại


def login(username, password):
    uname = str(username or "").strip().lower()
    if not uname or not password:
        raise FbError("Nhập đầy đủ tài khoản và mật khẩu")
    j, code = _post(_IDP + ":signInWithPassword?key=" + API_KEY, {
        "email": email_for(uname),
        "password": password,
        "returnSecureToken": True,
    })
    if code != 200 or not j.get("idToken"):
        raise FbError(_msg(((j.get("error") or {}).get("message")) or json.dumps(j)))
    uid = j["localId"]
    data = get_user_data(uid, j["idToken"])
    if data is None:
        raise FbError("Tài khoản không tồn tại")
    if data.get("role") == "disabled":
        raise FbError("Tài khoản đã bị khóa")
    with _lock:
        _session.update({
            "idToken": j["idToken"],
            "uid": uid,
            "refreshToken": j.get("refreshToken", ""),
            "username": uname,
            "displayName": data.get("displayName") or uname,
            "role": data.get("role", "user"),
            "email": data.get("email") or email_for(uname),
        })
        save_session()
    return {"uid": uid, "data": data, "idToken": j["idToken"]}


def register(username, password, display_name="", balance_fields=0):
    uname = str(username or "").strip().lower()
    if not (len(uname) >= 3 and len(uname) <= 20 and all(c.isalnum() or c in "._-" for c in uname)):
        raise FbError("Username chỉ gồm chữ thường/số, 3–20 ký tự")
    if len(str(password or "")) < 6:
        raise FbError("Mật khẩu ít nhất 6 ký tự")
    email = email_for(uname)
    j, code = _post(_IDP + ":signUp?key=" + API_KEY, {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    })
    if code != 200 or not j.get("idToken"):
        raise FbError(_msg(((j.get("error") or {}).get("message")) or json.dumps(j)))
    uid = j["localId"]
    tok = j["idToken"]
    now = int(time.time() * 1000)
    data = {
        "username": uname,
        "email": email,
        "displayName": (display_name or "").strip() or uname,
        "role": "user",
        "balanceFields": max(0, int(balance_fields or 0)),
        "createdAt": now,
        "lastSeen": now,
    }
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        DB_URL + "/users/" + urllib.parse.quote(uid) + ".json?auth=" + urllib.parse.quote(tok),
        data=body, method="PUT", headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            if r.status >= 300:
                raise FbError("Ghi dữ liệu thất bại: " + str(r.status))
    except urllib.error.HTTPError as e:
        raise FbError("Ghi dữ liệu thất bại (kiểm tra rules Realtime Database)")
    except FbError:
        raise
    except Exception as e:
        raise FbError("Ghi dữ liệu thất bại: " + str(e))
    with _lock:
        _session.update({"idToken": tok, "uid": uid, "refreshToken": j.get("refreshToken", ""),
                         "username": uname, "displayName": data["displayName"], "role": data["role"]})
        save_session()
    return {"uid": uid}


def logout():
    with _lock:
        _session.clear()
        save_session()


def picks(data):
    c = data.get("balanceFields") if data else None
    if c is not None:
        return max(0, int(float(c or 0)))
    sec = int(float((data or {}).get("balanceSeconds") or 0))
    if sec > 0:
        return max(1, int(sec // 60))
    return 0


def logged_in():
    load_session()
    with _lock:
        return bool(_session.get("uid") and _session.get("refreshToken"))


# ────────────────── admin (giống admin.html trên web) ──────────────────
def _auth_url(path, tok):
    return DB_URL + "/" + path + "?auth=" + urllib.parse.quote(tok)


def _with_token(tok=None):
    """Ưu tiên token truyền vào, fallback token phiên hiện tại (idToken hoặc refresh mới)."""
    if tok:
        return tok
    return id_token()


def list_users(tok=None):
    """Toàn bộ /users.json → {uid: user}."""
    j, code = _http_get(_auth_url("users.json", _with_token(tok)))
    if code != 200:
        raise FbError("Không đọc được danh sách user: " + str(j))
    return j or {}


def update_balance(uid, new_value, tok=None):
    if new_value < 0:
        raise FbError("Số lượt không được âm")
    j, code = _http_write(_auth_url("users/" + urllib.parse.quote(uid) + ".json",
                                    _with_token(tok)),
                          {"balanceFields": int(new_value), "lastSeen": {".sv": "timestamp"}})
    if code != 200:
        raise FbError("Cập nhật lượt thất bại: " + str(j))
    return j


def update_role(uid, role, tok=None):
    j, code = _http_write(_auth_url("users/" + urllib.parse.quote(uid) + ".json",
                                    _with_token(tok)), {"role": str(role)})
    if code != 200:
        raise FbError("Đổi quyền thất bại: " + str(j))
    return j


def delete_user(uid, tok=None):
    j, code = _http_write(_auth_url("users/" + urllib.parse.quote(uid) + ".json",
                                    _with_token(tok)), None, method="DELETE")
    if code != 200 and code != 204:
        raise FbError("Xóa user thất bại: " + str(j))
    return j


def get_settings(tok=None):
    """/settings/config.json → {vndPerPick} (mặc định 5000)."""
    j, code = _http_get(_auth_url("settings/config.json", _with_token(tok)))
    if code == 200 and j:
        return j
    return {}


def set_rate(vnd_per_pick, tok=None):
    v = max(1, int(vnd_per_pick or 0))
    j, code = _http_write(_auth_url("settings/config.json", _with_token(tok)),
                          {"vndPerPick": v})
    if code != 200:
        raise FbError("Lưu giá thất bại: " + str(j))
    return v


if HAS_REQUESTS:
    # fallback dùng requests nếu urllib gặp vấn đề trên một số thiết bị
    def _post(url, payload):  # noqa: F811
        r = requests.post(url, json=payload, timeout=20)
        try:
            return r.json(), r.status_code
        except Exception:
            return {"error": {"message": str(r.text)}}, r.status_code

    def _http_get(url):  # noqa: F811
        r = requests.get(url, timeout=20)
        try:
            return r.json(), r.status_code
        except Exception:
            return None, r.status_code