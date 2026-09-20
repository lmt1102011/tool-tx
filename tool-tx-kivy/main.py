import sys

print("HELLO-A", flush=True)
try:
    import kivy
    print("KIVY-OK " + kivy.__version__, flush=True)
    from kivy.app import App
    from kivy.uix.label import Label

    class T(App):
        title = "tooltx-mini"

        def build(self):
            return Label(text="HI")

    T().run()
    print("RAN-OK", flush=True)
except Exception:
    import traceback
    print("PY-EXC\n" + traceback.format_exc(), flush=True)