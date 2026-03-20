#!/usr/bin/env python3
from __future__ import annotations

import signal
import sys

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")

from gi.repository import Gdk, GLib, Gtk, WebKit2


DISPLAY_URL = "http://127.0.0.1:8000/display"


def build_fallback_html(message: str) -> str:
    safe = GLib.markup_escape_text(message)
    return f"""
    <html>
      <body style=\"margin:0;background:#000;color:#fff;display:flex;align-items:center;justify-content:center;font-family:Georgia,serif;\">
        <div style=\"text-align:center;max-width:32rem;padding:2rem;\">
          <h1 style=\"margin:0 0 1rem;\">Clock display is waiting for the local server.</h1>
          <p style=\"margin:0;opacity:0.75;\">{safe}</p>
        </div>
      </body>
    </html>
    """


class ClockWindow(Gtk.Window):
    def __init__(self) -> None:
        super().__init__(title="Clock Display")
        self.set_decorated(False)
        self.fullscreen()
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self.on_key_press)

        settings = WebKit2.Settings()
        settings.set_enable_back_forward_navigation_gestures(False)
        settings.set_enable_developer_extras(False)
        settings.set_enable_webgl(False)
        settings.set_hardware_acceleration_policy(WebKit2.HardwareAccelerationPolicy.NEVER)
        settings.set_javascript_can_open_windows_automatically(False)

        self.webview = WebKit2.WebView()
        self.webview.set_settings(settings)
        self.webview.connect("load-failed", self.on_load_failed)
        self.webview.connect("create", self.on_create)
        self.webview.load_uri(DISPLAY_URL)

        self.add(self.webview)
        self.show_all()

    def on_key_press(self, _window: Gtk.Window, event: Gdk.EventKey) -> bool:
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
            return True
        return True

    def on_create(self, _webview: WebKit2.WebView, _navigation_action: WebKit2.NavigationAction):
        return None

    def on_load_failed(self, webview, _event, failing_uri, error):
        message = f"{failing_uri} :: {error.message}"
        webview.load_html(build_fallback_html(message), "http://127.0.0.1:8000/")
        GLib.timeout_add_seconds(3, self.retry_load)
        return True

    def retry_load(self):
        self.webview.load_uri(DISPLAY_URL)
        return False


def main() -> int:
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    ok, _args = Gtk.init_check(sys.argv)
    if not ok:
        print("Could not initialize GTK display", file=sys.stderr)
        return 1

    ClockWindow()
    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
