"""Android owns this process-local service; durable state lives in filesDir."""
from pathlib import Path
import threading
from app_runtime import DesktopRuntime, ProfileLock, make_desktop_app


class AndroidRuntime:
    def __init__(self):
        self.runtime = self.profile = None
        self.directory = None
        self._lock = threading.RLock()

    def start(self, private_directory):
        directory = Path(private_directory)
        if not directory.is_absolute():
            raise ValueError('Android requires an absolute app-private data directory.')
        directory = directory.resolve()
        with self._lock:
            if self.runtime is not None:
                if directory != self.directory:
                    raise ValueError('An Android service already owns a different profile.')
                return self.runtime.origin if self.runtime._bootstrap_used else self.runtime.bootstrap_url
            profile = ProfileLock(directory)
            profile.__enter__()
            try:
                app, settings = make_desktop_app(directory)
                runtime = DesktopRuntime(app, settings)
                runtime.start(timeout=15)
            except Exception:
                profile.__exit__(None, None, None)
                raise
            self.runtime, self.profile, self.directory = runtime, profile, directory
            return runtime.bootstrap_url

    def stop(self):
        with self._lock:
            if self.runtime is not None:
                self.runtime.stop()
                self.runtime = None
            if self.profile is not None:
                self.profile.__exit__(None, None, None)
                self.profile = None
            self.directory = None


_host = AndroidRuntime()

def start(private_directory):
    return _host.start(private_directory)

def stop():
    _host.stop()
