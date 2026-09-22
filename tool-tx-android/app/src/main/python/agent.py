"""
agent.py — Agent control for Chaquopy.
Minimal stub — real agent logic lives in the Kivy codebase.
"""

_running = False

def start_fork(server_url, code):
    global _running
    try:
        import subprocess
        r = subprocess.run(
            ["am", "start", "-n",
             "org.lmt1102011.chromefork/org.chromium.chrome.browser.ChromeLauncherActivity"],
            capture_output=True, text=True, timeout=30,
        )
        out = (r.stdout or "") + " " + (r.stderr or "")
        ok = r.returncode == 0 and "Error" not in out and "Exception" not in out
        _running = ok
        return ok
    except Exception:
        return False

def start_agent(server_url, code):
    global _running
    _running = True
    return True

def stop():
    global _running
    _running = False

def is_running():
    return _running