"""
socket_client.py — Socket.IO client for Chaquopy.
Minimal implementation — real logic comes from the existing sio_client.py.
"""
import threading

_sio = None
_connected = False
_locking = False
_kick = None

def connect(url, token):
    global _sio, _connected, _locking
    if _locking:
        return
    _locking = True
    try:
        import socketio
        _sio = socketio.Client(
            logger=False, engineio_logger=False,
            reconnection=True, reconnection_attempts=5, reconnection_delay=2,
        )
        _sio.on("kick", _on_kick)
        _sio.connect(url, auth={"token": token or ""}, wait_timeout=20, retry=True)
        _connected = True
    except Exception as e:
        _connected = False
        if _sio is not None:
            try:
                _sio.disconnect()
            except Exception:
                pass
        raise e
    finally:
        _locking = False

def disconnect():
    global _sio, _connected
    try:
        if _sio:
            _sio.disconnect()
    except Exception:
        pass
    _connected = False
    _sio = None

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

def last_kick():
    return _kick

def clear_kick():
    global _kick
    _kick = None

def is_connected():
    return _connected

def agent_pair(url):
    global _sio, _connected
    if not _sio or not _connected:
        return None
    result = [None]
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
        done.set()

    try:
        _sio.emit("agent-pair", {}, callback=on_code)
        done.wait(timeout=10)
    except Exception:
        pass
    return result[0]
