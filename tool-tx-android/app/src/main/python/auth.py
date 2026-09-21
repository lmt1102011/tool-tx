"""
auth.py — Firebase Auth wrapper for Chaquopy.
Called from Kotlin via Python.getModule("auth").
"""
import json
import os
import requests

_api_key = None
_session = {}
_session_path = None

def _get_api_key():
    global _api_key
    if _api_key:
        return _api_key
    try:
        with open("config.txt") as f:
            for line in f:
                if "API_KEY" in line:
                    _api_key = line.split("=", 1)[1].strip()
                    return _api_key
    except Exception:
        pass
    return ""

def _save_session():
    if not _session_path:
        return
    try:
        with open(_session_path, "w") as f:
            json.dump(_session, f)
    except Exception:
        pass

def _load_session():
    global _session
    if not _session_path:
        return
    try:
        with open(_session_path) as f:
            _session = json.load(f)
    except Exception:
        _session = {}

def set_session_path(path):
    global _session_path
    _session_path = path
    _load_session()

def login(username, password):
    api_key = _get_api_key()
    url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=" + api_key
    r = requests.post(url, json={
        "email": username + "@tooltx.app",
        "password": password,
        "returnSecureToken": True,
    }, timeout=30)
    data = r.json()
    if "error" in data:
        raise Exception(data["error"].get("message", "Login failed"))
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
    api_key = _get_api_key()
    url = "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=" + api_key
    r = requests.post(url, json={
        "email": username + "@tooltx.app",
        "password": password,
        "displayName": name or username,
        "returnSecureToken": True,
    }, timeout=30)
    data = r.json()
    if "error" in data:
        raise Exception(data["error"].get("message", "Register failed"))
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
    api_key = _get_api_key()
    url = "https://securetoken.googleapis.com/v1/token?key=" + api_key
    r = requests.post(url, json={
        "grant_type": "refresh_token",
        "refresh_token": _session["refreshToken"],
    }, timeout=30)
    data = r.json()
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
    url = "https://tooltx-default-rtdb.firebaseio.com/users/%s.json?auth=%s" % (uid, token)
    r = requests.get(url, timeout=30)
    data = r.json()
    if isinstance(data, dict):
        return data
    return {}

def list_users():
    token = refresh_token()
    url = "https://tooltx-default-rtdb.firebaseio.com/users.json?auth=%s" % token
    r = requests.get(url, timeout=30)
    data = r.json()
    if isinstance(data, dict):
        return data
    return {}

def get_rate():
    try:
        token = refresh_token()
        url = "https://tooltx-default-rtdb.firebaseio.com/config/rate.json?auth=%s" % token
        r = requests.get(url, timeout=30)
        return int(r.json() or 5000)
    except Exception:
        return 5000

def set_rate(rate):
    token = refresh_token()
    url = "https://tooltx-default-rtdb.firebaseio.com/config/rate.json?auth=%s" % token
    requests.put(url, json=int(rate), timeout=30)

def register_with_picks(username, password, name, picks):
    result = register(username, password, name)
    uid = result["uid"]
    token = refresh_token()
    url = "https://tooltx-default-rtdb.firebaseio.com/users/%s.json?auth=%s" % (uid, token)
    requests.patch(url, json={"balanceFields": int(picks), "username": username}, timeout=30)

def update_balance(uid, balance):
    token = refresh_token()
    url = "https://tooltx-default-rtdb.firebaseio.com/users/%s/balanceFields.json?auth=%s" % (uid, token)
    requests.put(url, json=int(balance), timeout=30)

def update_role(uid, role):
    token = refresh_token()
    url = "https://tooltx-default-rtdb.firebaseio.com/users/%s/role.json?auth=%s" % (uid, token)
    requests.put(url, json=role, timeout=30)

def delete_user(uid):
    token = refresh_token()
    url = "https://tooltx-default-rtdb.firebaseio.com/users/%s.json?auth=%s" % (uid, token)
    requests.delete(url, timeout=30)
