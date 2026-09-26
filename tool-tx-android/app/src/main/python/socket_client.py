"""
socket_client.py — Socket.IO client for Chaquopy.
Kết nối có watchdog: không bao giờ treo quá ~12s; sẽ tự disconnect nếu connect không xong.
"""
import threading
import time

_sio = None
_connected = False
_locking = False
_kick = None
_panel = {}
_superseded = False


def connect(url, token):
    """Kết nối server. Có watchdog 12s để chống treo mãi."""
    global _sio, _connected, _locking, _superseded
    if _locking:
        return
    if not url:
        raise Exception("Thiếu địa chỉ server")
    _locking = True
    _connected = False
    _superseded = False
    # Xoá panel cũ trước khi nối: nếu không, lúc mất mạng app vẫn vẽ dự đoán của
    # ván đã kết thúc như thể còn hiệu lực, người dùng tưởng tool sai.
    set_panel({})
    try:
        import applog
        applog.log("socket", "connect %s" % url)
    except Exception:
        pass
    try:
        import socketio
        # reconnection=False: socket.io tự reconnect bằng đúng token đã truyền lúc
        # connect(). Token Firebase chỉ sống ~1h nên sau đó mọi lần tự reconnect
        # đều bị server verifyIdToken fail rồi disconnect -> app kẹt "mất kết nối".
        # Việc nối lại do ToolFragment điều khiển, mỗi lần ép lấy token mới.
        _sio = socketio.Client(
            logger=False, engineio_logger=False,
            reconnection=False,
            request_timeout=8,
        )
        _sio.on("kick", _on_kick)
        _sio.on("disconnect", _on_disconnect)
        _sio.on("panel-push", _on_panel)
        _sio.on("session-replaced", _on_replaced)

        def _watchdog():
            time.sleep(12.0)
            try:
                if _sio and not _connected:
                    _sio.disconnect()
            except Exception:
                pass

        threading.Thread(target=_watchdog, daemon=True).start()
        _sio.connect(url, auth={"token": token or ""}, wait=True, wait_timeout=10)
        _connected = True
    except Exception:
        _connected = False
        try:
            import applog
            applog.log("socket", "connect FAIL: url=%s" % url)
        except Exception:
            pass
        if _sio is not None:
            try:
                _sio.disconnect()
            except Exception:
                pass
        raise
    finally:
        _locking = False


def disconnect():
    global _sio, _connected, _superseded
    try:
        if _sio:
            _sio.disconnect()
    except Exception:
        pass
    _connected = False
    _superseded = False
    _sio = None


def _on_replaced(*_args):
    # Server đã đóng socket này vì có phiên mới cùng tài khoản. Nếu không dừng,
    # app cũ tự reconnect và đẩy phiên mới -> hai app đẩy nhau vô hạn.
    global _superseded, _connected
    _superseded = True
    _connected = False
    set_panel({})
    try:
        import applog
        applog.log("socket", "session-replaced: dung reconnect, cho phep ket noi moi")
    except Exception:
        pass
    try:
        if _sio:
            _sio.disconnect()
    except Exception:
        pass


def is_superseded():
    return _superseded


def _on_disconnect(*_args):
    global _connected
    _connected = False
    # Quan trọng: xoá panel cache. Giữ lại thì UI tiếp tục hiện pick của ván đã xong.
    set_panel({})


def _on_kick(data):
    global _kick
    try:
        if isinstance(data, dict):
            _kick = data.get("message") or data.get("error") or "Đăng nhập lại."
        else:
            _kick = str(data)
    except Exception:
        _kick = "Đăng nhập lại."
    print("[socket_client] kick: " + str(_kick))
    try:
        import applog
        applog.log("socket", "kick: " + str(_kick))
    except Exception:
        pass


def _on_panel(data):
    global _panel
    try:
        import applog
        applog.log("socket", "panel-push nhan: %s" % (str(data)[:300]))
    except Exception:
        pass
    if isinstance(data, dict):
        _panel = data


def set_panel(data):
    """Panel đẩy qua agent-ws (kênh bền) dùng chung biến _panel với socket.io."""
    global _panel
    if isinstance(data, dict):
        _panel = data


def last_kick():
    return _kick


def clear_kick():
    global _kick
    _kick = None


def last_panel():
    return _panel


def is_connected():
    return _connected


def agent_pair(url):
    """Lấy mã liên kết qua event 'agent-code' (server tự emit kèm ack).
    Không dùng emit(callback=...) để tránh treo khi server không ack (vd token hết hạn)."""
    global _sio, _connected
    if not _sio or not _connected:
        return None
    result = [None]
    reason = [""]
    done = threading.Event()

    def on_code(data):
        if isinstance(data, dict):
            result[0] = data.get("code")
        elif isinstance(data, (list, tuple)) and data:
            first = data[0]
            if isinstance(first, dict):
                result[0] = first.get("code")
            else:
                result[0] = str(first)
        reason[0] = "agent-code"
        done.set()

    try:
        _sio.on("agent-code", on_code)
        _sio.emit("agent-pair", {})
        done.wait(timeout=10)
    except Exception as e:
        reason[0] = "exception:" + str(e)[:120]
    finally:
        try:
            _sio.off("agent-code", on_code)
        except Exception:
            pass
    if result[0] is None:
        try:
            import applog
            applog.log("socket", "agent_pair FAIL: " + reason[0] + " connected=" + str(_connected) + " url=" + str(url)[:60])
        except Exception:
            pass
    return result[0]