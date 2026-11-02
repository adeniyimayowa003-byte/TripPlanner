"""Owned local desktop service and per-user settings; no native GUI dependency."""
from contextlib import AbstractContextManager
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import threading
import time
from urllib.request import Request, ProxyHandler, build_opener

from flask import jsonify, redirect, request
from werkzeug.serving import WSGIRequestHandler, make_server

from app import create_app
from csrf import get_csrf_token, valid_csrf_token
from version import APP_VERSION

APPEARANCES = frozenset(("system", "light", "dark"))


def default_data_dir(environ=None):
    source = os.environ if environ is None else environ
    parent = source.get("LOCALAPPDATA", "")
    if not parent or not Path(parent).is_absolute():
        raise ValueError("Windows could not locate your local application-data folder.")
    return Path(parent) / "TripPlanner"


class ProfileSettings:
    """A small strict document, with atomic replacement rather than partial writes."""
    def __init__(self, directory):
        self.directory = Path(directory)
        if not self.directory.is_absolute():
            raise ValueError("Choose an absolute app-data folder.")
        self.path = self.directory / "settings.json"
        self._lock = threading.RLock()

    def _write(self, document):
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.directory,
                                             prefix=".settings-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(document, stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def load(self):
        with self._lock:
            if not self.path.exists():
                self._write({"version": 1, "secret_key": secrets.token_hex(32), "appearance": "system"})
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                valid = (isinstance(data, dict) and set(data) == {"version", "secret_key", "appearance"}
                         and type(data["version"]) is int and data["version"] == 1
                         and isinstance(data["secret_key"], str)
                         and re.fullmatch(r"[0-9a-f]{64}", data["secret_key"]) is not None
                         and isinstance(data["appearance"], str) and data["appearance"] in APPEARANCES)
            except (ValueError, UnicodeError):
                valid = False
            if not valid:
                raise ValueError("App settings could not be read. Keep a backup before repairing settings.json; your saved trips have not been reset.")
            return data

    def set_appearance(self, mode):
        if not isinstance(mode, str) or mode not in APPEARANCES:
            raise ValueError("Choose Light, Dark, or Use device setting.")
        with self._lock:
            self._write({**self.load(), "appearance": mode})


class ProfileLock(AbstractContextManager):
    """Hold an OS lock, automatically released if a process exits unexpectedly."""
    def __init__(self, directory):
        self.directory = Path(directory)
        self.stream = None

    def __enter__(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        self.stream = (self.directory / "app.lock").open("a+b")
        try:
            if self.stream.seek(0, 2) == 0:
                self.stream.write(b"0")
                self.stream.flush()
            self.stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            self.stream.close()
            self.stream = None
            raise RuntimeError("TripPlanner is already open for this app-data folder. Close that window before opening another.") from error
        return self

    def __exit__(self, *args):
        if self.stream is not None:
            self.stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream, fcntl.LOCK_UN)
            self.stream.close()
            self.stream = None


def make_desktop_app(directory):
    settings = ProfileSettings(directory)
    values = settings.load()
    app = create_app({"SECRET_KEY": values["secret_key"],
                      "DATABASE": str(settings.directory / "trips.sqlite3"),
                      "DEBUG": False, "TESTING": False, "TRUSTED_HOSTS": ["127.0.0.1"]})
    return app, settings


class _QuietHandler(WSGIRequestHandler):
    def log(self, *args, **kwargs):
        # Bootstrap credentials must not end up in a request log.
        pass


class DesktopRuntime:
    """Bind once on an allocated port; authenticate before any private app route."""
    def __init__(self, app, settings):
        self.app, self.settings = app, settings
        self.access_token = secrets.token_hex(32)
        self.origin = ""
        self.server = self.thread = None
        self._bootstrap_used = False
        self._bootstrap_lock = threading.Lock()
        self._install_routes()

    @property
    def bootstrap_url(self):
        return f"{self.origin}/_desktop/open?token={self.access_token}"

    def _valid_access(self, value):
        return (isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None
                and secrets.compare_digest(value, self.access_token))

    def _install_routes(self):
        def guard():
            if request.host != self.origin.removeprefix("http://"):
                return "Open TripPlanner from its app icon.", 403
            origin = request.headers.get("Origin")
            if origin and origin != self.origin:
                return "This request could not be verified.", 403
            if request.path == "/_desktop/open" and request.method == "GET":
                return None
            if not self._valid_access(request.cookies.get("tripplanner_desktop")):
                return "Open TripPlanner from its app icon.", 403

        # This must run before existing form/catalog/storage processing.
        self.app.before_request_funcs.setdefault(None, []).insert(0, guard)

        @self.app.after_request
        def private_headers(response):
            # no-referrer makes a normal HTML POST's Origin opaque ("null").
            # Protect the one-use credential URL, then preserve same-origin
            # form submissions while still omitting referrers to other sites.
            response.headers["Referrer-Policy"] = "no-referrer" if request.path == "/_desktop/open" else "same-origin"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Cache-Control"] = "no-store"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; img-src 'self'; style-src 'self'; script-src 'self'; "
                "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
            )
            return response

        @self.app.context_processor
        def native_values():
            return {"native_appearance": self.settings.load()["appearance"], "desktop_mode": True}

        @self.app.get("/_desktop/open")
        def desktop_open():
            with self._bootstrap_lock:
                if self._bootstrap_used or not self._valid_access(request.args.get("token")):
                    return "Open TripPlanner from its app icon.", 403
                self._bootstrap_used = True
            response = redirect("/", code=303)
            response.set_cookie("tripplanner_desktop", self.access_token, httponly=True, samesite="Strict")
            return response

        @self.app.get("/_desktop/health")
        def desktop_health():
            return jsonify(status="ready", version=APP_VERSION)

        @self.app.post("/_desktop/appearance")
        def desktop_appearance():
            if not valid_csrf_token(request.headers.get("X-CSRF-Token")):
                return jsonify(error="Reopen this page before changing appearance."), 400
            data = request.get_json(silent=True)
            if not isinstance(data, dict) or set(data) != {"appearance"}:
                return jsonify(error="Choose an appearance."), 400
            try:
                self.settings.set_appearance(data["appearance"])
            except ValueError:
                return jsonify(error="Choose an appearance."), 400
            except OSError:
                return jsonify(error="This choice could not be remembered."), 503
            return jsonify(appearance=data["appearance"])

    def start(self, timeout=5):
        if timeout <= 0 or self.server is not None:
            raise ValueError("Start the desktop service once with a positive timeout.")
        try:
            self.server = make_server("127.0.0.1", 0, self.app, threaded=True, request_handler=_QuietHandler)
            self.origin = f"http://127.0.0.1:{self.server.server_port}"
            self.thread = threading.Thread(target=self.server.serve_forever,
                                           kwargs={"poll_interval": .05}, daemon=True, name="TripPlanner-local")
            self.thread.start()
            deadline = time.monotonic() + timeout
            opener = build_opener(ProxyHandler({}))
            while time.monotonic() < deadline:
                try:
                    request_ready = Request(self.origin + "/_desktop/health",
                                            headers={"Cookie": f"tripplanner_desktop={self.access_token}"})
                    with opener.open(request_ready, timeout=min(.25, timeout)) as response:
                        if response.status == 200 and json.load(response).get("status") == "ready":
                            return
                except (OSError, ValueError):
                    pass
                time.sleep(.02)
            raise RuntimeError("TripPlanner could not finish starting. Close this window and try again.")
        except Exception:
            self.stop()
            raise

    def stop(self):
        if self.server is not None:
            if self.thread is not None and self.thread.is_alive():
                self.server.shutdown()
                self.thread.join(timeout=2)
            self.server.server_close()
            self.server = self.thread = None
