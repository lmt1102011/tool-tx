"""
auth.py — Firebase Auth wrapper for Chaquopy.
Called from Kotlin via Python.getModule("auth").
"""
import json
import os
import requests
from requests.exceptions import (RequestException, ConnectionError as _ConnError,
                                 Timeout as _Timeout, SSLError as _SSLError)

try:
    from config import API_KEY, FIREBASE_DB, SESSION_PATH
except ImportError:
    API_KEY = ""
    FIREBASE_DB = ""
    SESSION_PATH = ""

if not SESSION_PATH:
    SESSION_PATH = os.path.join(
        os.environ.get("ANDROID_PRIVATE", "/data/data/com.lmt.tooltx"), "session.json"
    )

_FIREBASE_ERRORS = {
    "INVALID_LOGIN_CREDENTIALS": "Sai tên đăng nhập hoặc mật khẩu",
    "INVALID_EMAIL": "Tên đăng nhập không hợp lệ",
    "EMAIL_NOT_FOUND": "Không tìm thấy tài khoản",
    "INVALID_PASSWORD": "Sai mật khẩu",
    "USER_DISABLED": "Tài khoản đã bị khóa",
    "EMAIL_EXISTS": "Tài khoản đã tồn tại",
    "WEAK_PASSWORD": "Mật khẩu quá yếu (≥ 6 ký tự)",
    "OPERATION_NOT_ALLOWED": "Đăng nhập đang bị tạm khóa, vui lòng thử lại sau",
    "TOO_MANY_ATTEMPTS_TRY_LATER": "Quá nhiều lần thử sai — hãy đợi một lúc rồi thử lại",
}

def _firebase_message(data, default="Đăng nhập thất bại"):
    code = (data.get("error") or {}).get("message", "")
    return _FIREBASE_ERRORS.get(code, default)


def _http_json(method, url, **kw):
    """Thực hiện HTTP và chuyển lỗi mạng/http thành thông báo tiếng Việt rõ ràng."""
    try:
        r = requests.request(method, url, timeout=30, **kw)
    except _ConnError:
        raise Exception("Không có kết nối mạng. Kiểm tra Wi-Fi hoặc dữ liệu di động rồi thử lại.")
    except _Timeout:
        raise Exception("Kết nối máy chủ bị quá thời gian chờ. Kiểm tra mạng và thử lại.")
    except _SSLError:
        raise Exception("Lỗi bảo mật khi kết nối máy chủ.")
    except RequestException as e:
        raise Exception("Lỗi mạng: %s" % e)
    if r.status_code != 200:
        try:
            data = r.json()
        except Exception:
            raise Exception("Máy chủ trả lỗi HTTP %s — thử lại sau." % r.status_code)
        code = (data.get("error") or {}).get("message", "")
        raise Exception(_FIREBASE_ERRORS.get(code, "Máy chủ trả lỗi HTTP %s — thử lại sau." % r.status_code))
    return r.json()

_session = {}

def _save_session():
    if not SESSION_PATH:
        return
    try:
        with open(SESSION_PATH, "w") as f:
            json.dump(_session, f)
    except Exception:
        pass

def _load_session():
    global _session
    if not SESSION_PATH:
        return
    try:
        with open(SESSION_PATH) as f:
            _session = json.load(f)
    except Exception:
        _session = {}

def set_session_path(path):
    global _session, SESSION_PATH
    SESSION_PATH = path
    try:
        with open(path) as f:
            _session = json.load(f)
    except Exception:
        _session = {}

def login(username, password):
    url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=" + API_KEY
    data = _http_json("POST", url, json={
        "email": username + "@tooltx.app",
        "password": password,
        "returnSecureToken": True,
    })
    if "error" in data:
        raise Exception(_firebase_message(data))
    global _session
    _session = {
        "uid": data["localId"],
        "idToken": data["idToken"],
        "refreshToken": data["refreshToken"],
        "displayName": username,
    }
    _save_session()
    return {"uid": data["localId"], "data": {"displayName": username}}

def register(username, password, name):
    url = "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=" + API_KEY
    data = _http_json("POST", url, json={
        "email": username + "@tooltx.app",
        "password": password,
        "displayName": name or username,
        "returnSecureToken": True,
    })
    if "error" in data:
        raise Exception(_firebase_message(data, default="Đăng ký thất bại"))
    global _session
    _session = {
        "uid": data["localId"],
        "idToken": data["idToken"],
        "refreshToken": data["refreshToken"],
        "displayName": name or username,
    }
    _save_session()
    return {"uid": data["localId"]}

def logout():
    global _session
    _session = {}
    _save_session()

def get_session():
    _load_session()
    if not _session or not _session.get("uid"):
        return None
    return _session

def is_logged_in():
    s = get_session()
    return s is not None and bool(s.get("uid"))

def current():
    return _session or {}

def refresh_token():
    if not _session.get("refreshToken"):
        raise Exception("No refresh token")
    url = "https://securetoken.googleapis.com/v1/token?key=" + API_KEY
    data = _http_json("POST", url, json={
        "grant_type": "refresh_token",
        "refresh_token": _session["refreshToken"],
    })
    if "error" in data:
        raise Exception(data["error"].get("message", "Token refresh failed"))
    _session["idToken"] = data["id_token"]
    _session["refreshToken"] = data["refresh_token"]
    _save_session()
    return _session["idToken"]

def user_data():
    if not _session.get("uid"):
        return {}
    token = refresh_token()
    uid = _session["uid"]
    url = "%s/users/%s.json?auth=%s" % (FIREBASE_DB, uid, token)
    r = _http_json("GET", url)
    if isinstance(r, dict):
        return r
    return {}

def list_users():
    token = refresh_token()
    url = "%s/users.json?auth=%s" % (FIREBASE_DB, token)
    r = _http_json("GET", url)
    if isinstance(r, dict):
        return r
    return {}

def get_rate():
    try:
        token = refresh_token()
        url = "%s/config/rate.json?auth=%s" % (FIREBASE_DB, token)
        r = _http_json("GET", url)
        return int(r or 5000)
    except Exception:
        return 5000

def set_rate(rate):
    token = refresh_token()
    url = "%s/config/rate.json?auth=%s" % (FIREBASE_DB, token)
    _http_json("PUT", url, json=int(rate))

def register_with_picks(username, password, name, picks):
    result = register(username, password, name)
    uid = result["uid"]
    token = refresh_token()
    url = "%s/users/%s.json?auth=%s" % (FIREBASE_DB, uid, token)
    _http_json("PATCH", url, json={"balanceFields": int(picks), "username": username})

def update_balance(uid, balance):
    token = refresh_token()
    url = "%s/users/%s/balanceFields.json?auth=%s" % (FIREBASE_DB, uid, token)
    _http_json("PUT", url, json=int(balance))

def update_role(uid, role):
    token = refresh_token()
    url = "%s/users/%s/role.json?auth=%s" % (FIREBASE_DB, uid, token)
    _http_json("PUT", url, json=role)

def delete_user(uid):
    token = refresh_token()
    url = "%s/users/%s.json?auth=%s" % (FIREBASE_DB, uid, token)
    _http_json("DELETE", url)