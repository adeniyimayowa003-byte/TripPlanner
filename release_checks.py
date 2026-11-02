"""Small pre-publication source audit. Findings name paths, never secret values."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
REQUIRED = ("README.md", "CONTRIBUTING.md", "LICENSE", "CODE_LICENSE.md", "PHOTO_CREDITS.md", "PRIVACY.md",
            "THIRD_PARTY_NOTICES.md", ".env.example", ".gitignore", ".github/workflows/tests.yml")
EXCLUDED = {".git", ".tmp", "instance", "profile", "profiles", "build", "dist", "__pycache__",
            ".pytest_cache", "node_modules", ".mypy_cache", ".ruff_cache"}
PRIVATE_SUFFIXES = {".sqlite", ".sqlite3", ".db", ".pem", ".key", ".p12", ".pfx", ".jks", ".keystore"}


def source_candidates(root):
    root = Path(root)
    pending = [root]
    while pending:
        directory = pending.pop()
        for path in sorted(directory.iterdir()):
            if path.name in EXCLUDED or path.name.startswith((".venv", "venv", ".env")) and path.name != ".env.example":
                continue
            if path.is_symlink():
                yield path
            elif path.is_dir():
                pending.append(path)
            else:
                yield path


def check_source_tree(root):
    root = Path(root).resolve()
    findings = [f"Missing publication file: {name}" for name in REQUIRED if not (root / name).is_file()]
    patterns = (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
                re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
                re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{30,}\b"))
    for path in source_candidates(root):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            findings.append(f"Review source symlink: {relative}")
            continue
        if path.suffix.lower() in PRIVATE_SUFFIXES or path.name in {"settings.json", "Cookies", "Login Data"}:
            findings.append(f"Private/local file in source candidates: {relative}")
            continue
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".ico", ".woff2", ".mp4"}:
            continue
        if path.stat().st_size > 2_000_000:
            findings.append(f"Review oversized non-image source: {relative}")
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeError:
            findings.append(f"Review unexpected binary source: {relative}")
            continue
        if any(pattern.search(content) for pattern in patterns):
            findings.append(f"Possible credential in: {relative} (value redacted)")
    return findings


if __name__ == "__main__":
    issues = check_source_tree(ROOT)
    for issue in issues:
        print(issue)
    print(f"Source review: {len(issues)} finding(s). Ignored local data and build folders were not read.")
    raise SystemExit(bool(issues))
