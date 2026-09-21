"""
socket_client.py — Socket.IO client for Chaquopy.
Minimal implementation — real logic comes from the existing sio_client.py.
"""
import threading

_sio = None
_connected = False

def connect(url, token):
    global _sio, _connected
    try:
        import socketio
        _sio = socketio.Client()
        _sio.connect(url, auth={"token": token})
        _connected = True
    except Exception as e:
        _connected = False
        raise e

def disconnect():
    global _sio, _connected
    try:
        if _sio:
            _sio.disconnect()
    except Exception:
        pass
    _connected = False
    _sio = None

def is_connected():
    return _connected

def agent_pair(url):
    global _sio
    if not _sio:
        return None
    result = [None]
    done = threading.Event()

    def on_code(data):
        result[0] = data.get("code") if isinstance(data, dict) else None
        done.set()

    try:
        _sio.emit("agent:pair", callback=on_code)
        done.wait(timeout=10)
    except Exception:
        pass
    return result[0]
