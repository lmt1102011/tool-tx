# sio_client.py — kết nối tới tool server qua socket.io (giống web).
# Dùng: pip install python-socketio websocket-client
# Events: snapshot / user-status / panel-push (agent). Gọi callback trong thread socketio
# → nơi gọi phải đưa lên UI thread (Kivy dùng Clock.schedule_once).

import json
import os
import threading
import urllib.request

import socketio

DEFAULT_PAGES = "https://lmt1102011.github.io/tool-tx/server-url.json"


class SioClient:
    def __init__(self, on_status=None, on_panel=None, on_user_status=None, on_log=None,
                 on_connected=None, on_disconnected=None):
        self.on_status = on_status          # (status dict)
        self.on_panel = on_panel            # (panel dict)
        self.on_user_status = on_user_status  # (dict)
        self.on_log = on_log                # (msg, err)
        self.on_connected = on_connected    # ()
        self.on_disconnected = on_disconnected  # (reason)
        self._sio = socketio.Client(logger=False, engineio_logger=False)
        self._register()
        self.server_url = ""
        self._lock = threading.Lock()
        self._pending_pair = {}

    def _log(self, msg, err=False):
        if self.on_log:
            try:
                self.on_log(msg, err)
            except Exception:
                pass

    def _register(self):
        s = self._sio
        s.on("connect", lambda: self._fire(self.on_connected))
        s.on("disconnect", lambda r: self._fire(self.on_disconnected, r))
        s.on("snapshot", lambda d: self._fire(self.on_status, d))
        s.on("panel-push", lambda d: self._fire(self.on_panel, d))
        s.on("user-status", lambda d: self._fire(self.on_user_status, d))
        s.on("*", self._on_any)

    def _fire(self, cb, *a):
        if cb:
            try:
                cb(*a)
            except Exception as e:
                self._log("callback error: " + str(e), True)

    def _on_any(self, event, data):
        if event in ("connect", "disconnect", "snapshot", "panel-push", "user-status"):
            return
        if event != "connect_error":
            self._log("sự kiện '" + str(event) + "'")

    # ---- server URL ----
    @staticmethod
    def discover_server(config_path=""):
        ov = ""
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    ov = (json.load(f).get("server") or "").strip()
            except Exception:
                ov = ""
        if ov:
            return ov
        try:
            with urllib.request.urlopen(DEFAULT_PAGES, timeout=12) as r:
                return (json.loads(r.read().decode("utf-8")).get("url") or "").strip()
        except Exception:
            return ""

    # ---- connect ----
    def connect(self, server, id_token):
        self.server_url = (server or "").strip().rstrip("/")
        if not self.server_url:
            raise ValueError("Chưa có địa chỉ server")
        if self._sio.connected:
            self._sio.disconnect()
        self._sio.connect(self.server_url, auth={"token": id_token}, wait_timeout=15)
        self._log("Đã kết nối server: " + self.server_url)

    def disconnect(self):
        try:
            if self._sio.connected:
                self._sio.disconnect()
        except Exception:
            pass

    @property
    def connected(self):
        return bool(self._sio.connected)

    # ---- emit có ack (mã liên kết agent) ----
    def agent_pair(self, callback):
        def back(data):
            self._fire(callback, data)
            return True

        self._sio.emit("agent-pair", {}, callback=back)

    def agent_cancel(self):
        try:
            self._sio.emit("agent-cancel", {})
        except Exception:
            pass

    def launch_profile(self):
        try:
            self._sio.emit("launch-profile", {})
        except Exception:
            pass