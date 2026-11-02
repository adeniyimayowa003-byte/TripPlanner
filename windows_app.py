"""Windows entry point; the planner stays in ordinary, independently tested Python."""
import argparse
import ipaddress
import os
from pathlib import Path
import threading
from urllib.parse import urlsplit
import webbrowser

from app_runtime import default_data_dir, ProfileLock, make_desktop_app, DesktopRuntime
from version import APP_VERSION


def navigation_action(url, origin):
    if not isinstance(url, str) or not url or "\\" in url or any(c.isspace() for c in url):
        return "blocked"
    try:
        parts, local = urlsplit(url), urlsplit(origin)
        if not parts.hostname or parts.username is not None or parts.password is not None:
            return "blocked"
        if (parts.scheme, parts.hostname, parts.port) == (local.scheme, local.hostname, local.port):
            return "internal"
        if parts.scheme != "https" or parts.hostname.casefold() == "localhost":
            return "blocked"
        try:
            if not ipaddress.ip_address(parts.hostname).is_global:
                return "blocked"
        except ValueError:
            pass  # Public DNS names are handed to the ordinary system browser.
        return "external"
    except ValueError:
        return "blocked"


def _open_external(url):
    threading.Thread(target=webbrowser.open, args=(url,), kwargs={"new": 2}, daemon=True).start()


def _restrict_window(window, runtime):
    """Attach before showing the pinned pywebview 6.2.1 EdgeChromium control."""
    browser = window.native.browser
    control = browser.webview

    def navigating(sender, args):
        decision = navigation_action(str(args.Uri), runtime.origin)
        if decision != "internal":
            args.Cancel = True
            if decision == "external":
                _open_external(str(args.Uri))

    def popup(sender, args):
        args.Handled = True
        url = str(args.Uri)
        decision = navigation_action(url, runtime.origin)
        if decision == "external":
            _open_external(url)
        elif decision == "internal":
            control.CoreWebView2.Navigate(url)

    def ready(sender, args):
        if not args.IsSuccess:
            window.native.Close()
            return
        core = control.CoreWebView2
        # Replace the library's general popup handler with the same URL policy.
        core.NewWindowRequested -= browser.on_new_window_request
        core.NewWindowRequested += popup

    control.NavigationStarting += navigating
    control.CoreWebView2InitializationCompleted += ready
    # Keep Python callbacks alive for the whole native window lifetime.
    window._tripplanner_navigation_handlers = (navigating, popup, ready)


def _show_startup_error(message):
    # Normal application UI, never an instruction to weaken OS protections.
    if os.name == "nt":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, "TripPlanner could not start", 0x10)
    else:
        print(message)


def main(argv=None):
    parser = argparse.ArgumentParser(description="TripPlanner local Windows demo")
    parser.add_argument("--data-dir", type=Path, help="Absolute isolated profile folder (advanced/QA use).")
    options = parser.parse_args(argv)
    runtime = None
    try:
        if os.name != "nt":
            raise RuntimeError("This downloadable app targets Windows x64. Use the web instructions on other systems.")
        directory = options.data_dir if options.data_dir is not None else default_data_dir()
        if not directory.is_absolute():
            raise ValueError("Choose an absolute app-data folder.")
        with ProfileLock(directory):
            app, settings = make_desktop_app(directory)
            runtime = DesktopRuntime(app, settings)
            runtime.start(timeout=8)
            import webview
            webview.settings["ALLOW_DOWNLOADS"] = False
            webview.settings["ALLOW_FILE_URLS"] = False
            webview.settings["IGNORE_SSL_ERRORS"] = False
            window = webview.create_window(f"TripPlanner {APP_VERSION}", runtime.bootstrap_url,
                                           width=1160, height=820, min_size=(360, 560),
                                           background_color="#faf9f3", js_api=None)

            def before_show():
                try:
                    _restrict_window(window, runtime)
                except Exception:
                    window.native.Close()
                    raise RuntimeError("The trusted app window could not initialize. Check the required WebView2 runtime.")

            window.events.before_show += before_show
            webview.start(gui="edgechromium", debug=False, private_mode=False,
                          storage_path=str(directory / "browser"))
        return 0
    except Exception as error:
        _show_startup_error(str(error) + "\n\nTripPlanner requires the Microsoft Edge WebView2 runtime. Your saved trips have not been reset.")
        return 1
    finally:
        if runtime is not None:
            runtime.stop()


if __name__ == "__main__":
    raise SystemExit(main())
