# test_logic.py — kiểm tra fb / sio / agent KHÔNG cần Kivy.
import sys, time, threading, os
sys.path.insert(0, 'C:/Users/Tri/Desktop/Tool/tool-tx-kivy')

import fb
import sio_client
from agent import Agent, find_browser

def section(t):
    print("\n== " + t + " ==")

# 1) Browser detect
section("find_browser")
print("Browser:", find_browser())

# 2) Firebase
section("fb.email_for")
print("email_for('tinhyeu') =", fb.email_for('tinhyeu'))

section("fb.login wrong password")
try:
    fb.login('tinhyeu', 'sai-mat-khau')
    print("FAIL: không báo lỗi")
except fb.FbError as e:
    print("OK expect lỗi:", e)

section("fb.register + login")
uname = "pykivy" + str(int(time.time()) % 100000)
print("tạo user:", uname)
try:
    r = fb.register(uname, "test123456", "Py Test")
    print("registered uid:", r["uid"])
    res = fb.login(uname, "test123456")
    print("login ok uid:", res["uid"], "picks:", fb.picks(res["data"]))
    fb.save_session()
except Exception as e:
    print("FAIL (có thể username trùng/rule):", e)

# 3) Socket.io -> server local
section("sio connect localhost:8787")
try:
    tok = fb.refresh_id_token()
    sio = sio_client.SioClient(on_log=lambda m, e=False: print("   [sio]", m),
                               on_connected=lambda: print("   [sio] CONNECTED"))
    srv = srv = sio.client.discover_server('C:/Users/Tri/Desktop/Tool/tool-tx-kivy/config.txt') if False else sio_client.SioClient.discover_server('')
    print("discover:", srv)
    if not srv:
        srv = "http://localhost:8787"
    sio.connect(srv, tok)
    print("connected:", sio.connected)
    got = {}
    ev = threading.Event()
    sio.agent_pair(lambda r: (got.update(r or {}), ev.set()))
    ev.wait(8)
    print("agent-pair code:", got.get("code"))
    sio.disconnect()
except Exception as e:
    print("FAIL:", e)

# 4) Agent python -> WS /agent-ws trên server local = mở Chrome CDP thật
section("agent.py (Chrome CDP) -> server localhost")
code = got.get("code")
if code:
    logs = []
    ag = Agent(on_log=lambda m, e=False: (print("   [agent]", "ERR " if e else "", m), logs.append(m)))
    ag.start(server="http://localhost:8787", code=code)
    t0 = time.time()
    ok = False
    while time.time() - t0 < 25:
        if any("Server xác nhận" in l for l in logs):
            ok = True
            break
        time.sleep(1)
    print("agent connect server:", "OK" if ok else "KHÔNG (chờ thêm 15s)")
    time.sleep(6)
    ag.stop()
else:
    print("skip — không có code")

print("\nDONE")