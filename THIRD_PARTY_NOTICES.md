# Third-party components and photographs

TripPlanner uses third-party components under their own terms. The Windows build copies installed distributions' supplied license/copyright files and metadata into `licenses/` and records actual versions in `build-info.json`. Preserve that folder when redistributing the entire portable app.

| Component | Purpose | License/source |
| --- | --- | --- |
| CPython | Bundled Python runtime | [Python license](https://docs.python.org/3/license.html) |
| Flask, Werkzeug, Jinja2, MarkupSafe | Local web pages and WSGI service | [Pallets projects](https://palletsprojects.com/) — BSD-3-Clause |
| itsdangerous, blinker, click | Signing, events, and Flask support | Respective installed distribution notices |
| pywebview | Native Windows window | [pywebview](https://github.com/r0x0r/pywebview) — BSD-3-Clause |
| Python.NET, clr-loader | Windows/.NET integration | [Python.NET](https://github.com/pythonnet/pythonnet), [clr-loader](https://github.com/pythonnet/clr-loader) — MIT |
| cffi, pycparser | Native interoperability | Respective installed distribution notices |
| bottle, proxy-tools, typing-extensions | pywebview dependencies | Respective installed distribution notices |
| PyInstaller | Build-time packaging and bootloader | [License with application-distribution exception](https://pyinstaller.org/en/stable/license.html) |
| Microsoft WebView2 SDK/loader | Native browser integration supplied with pywebview | [Microsoft WebView2 redistribution terms](https://www.nuget.org/packages/Microsoft.Web.WebView2/) |

Microsoft Edge WebView2 Runtime is a separately installed Windows prerequisite, not an installer bundled by this project. Do not remove its OS/runtime protections. The portable demo is unsigned and has no trusted-publisher certificate.

The included WebView2 SDK DLLs are version **1.0.3856.49**. The unmodified `LICENSE.txt` and `NOTICE.txt` from Microsoft's exact-version NuGet package are preserved in [third_party/webview2/](third_party/webview2/) and copied into the download's `licenses/Microsoft.Web.WebView2/` folder. This does not install or bundle the separate Evergreen browser runtime. Build-included setuptools, packaging, and PyInstaller bootloader/hook notices are also preserved.

Photographs keep their individual CC BY, CC BY-SA, or CC0 terms. See [PHOTO_CREDITS.md](PHOTO_CREDITS.md), `data/images.json`, and the in-app photo credits. The photo licenses do not automatically license TripPlanner's original code. See [CODE_LICENSE.md](CODE_LICENSE.md).

## Hosted website preparation

The separate hosted runtime uses **Waitress 3.0.2**, under **Zope Public License 2.1**, in addition to the existing Flask/Pallets dependencies. Its exact installed upstream license is preserved in [third_party/waitress/LICENSE.txt](third_party/waitress/LICENSE.txt). Hosted dependency versions are pinned in `requirements-hosted.lock.txt`. Waitress is not added to the delivered Windows/Android packages. A hosting provider's infrastructure and terms are separate from these code licenses.

The selected free-demo PostgreSQL adapter adds **Psycopg/psycopg-binary 3.3.6** (LGPL-3.0), **Certifi 2026.10.23** (MPL-2.0 public CA bundle), and Windows-only **tzdata 2026.6** (upstream database/code notices). Exact supplied license files and versions are preserved in [third_party/hosted-postgres/](third_party/hosted-postgres/). These web/development dependencies are not included in the delivered native packages. No third-party dependency code is modified; its licenses remain separate from original TripPlanner code's MIT license.

## Android demo

The Android host embeds Chaquopy **17.2.0** under its MIT license, with CPython **3.14.8**. Unmodified upstream Chaquopy, CPython, and OpenSSL license texts are preserved in `packaging/android/app/src/main/assets/third_party/` and embedded as APK assets. The Python requirements archives retain each installed distribution's metadata and supplied license files. Exact resolved versions are pinned in `requirements-android.lock.txt`: Flask 3.1.3, Werkzeug 3.1.9, Jinja2 3.1.6, MarkupSafe 3.0.4, itsdangerous 2.2.0, click 8.5.0, and blinker 1.9.0. Android framework/System WebView belong to the operating system and are not bundled browser installers.

Upstream texts: [Chaquopy 17.2.0](https://github.com/chaquo/chaquopy/blob/17.2.0/LICENSE.txt), [CPython 3.14.8](https://github.com/python/cpython/blob/v3.14.8/LICENSE), and [OpenSSL](https://github.com/openssl/openssl/blob/openssl-3.0/LICENSE.txt). Keep the APK notices, photo credits, and companion source notices when redistributing. The Android SDK and Gradle/JDK are build tools rather than files copied into the APK.
