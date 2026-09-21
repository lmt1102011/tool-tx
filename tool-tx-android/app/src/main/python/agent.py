"""
agent.py — Agent control for Chaquopy.
Minimal stub — real agent logic lives in the Kivy codebase.
"""

_running = False

def start_fork(server_url, code):
    global _running
    try:
        import subprocess
        subprocess.Popen(
            ["am", "start", "-n",
             "org.lmt1102011.chromefork/org.chromium.chrome.browser.ChromeLauncherActivity"],
        )
        _running = True
        return True
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
