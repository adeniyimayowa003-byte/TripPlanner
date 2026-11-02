"""Explicit public-site factory. Local/native factories never opt in via env."""
import hashlib
import os
from pathlib import Path
import re
import secrets

from flask import g, jsonify, request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app import create_app
import hosted_saved_trips
from saved_trips import StorageUnavailableError

VISITOR_COOKIE = "__Host-tripplanner_visitor"
VISITOR_MAX_AGE = 365 * 24 * 60 * 60


def _configuration(environ):
    secret = environ.get("TRIPPLANNER_SECRET_KEY", "")
    if not isinstance(secret, str) or re.fullmatch(r"[0-9a-fA-F]{64,}", secret) is None:
        raise ValueError("Set a private TRIPPLANNER_SECRET_KEY of at least 64 hexadecimal characters.")
    hostname = environ.get("TRIPPLANNER_PUBLIC_HOST", "")
    label = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    if (not isinstance(hostname, str) or len(hostname) > 253
            or re.fullmatch(rf"(?:{label}\.)+[a-z](?:[a-z0-9-]{{0,61}}[a-z0-9])?", hostname) is None):
        raise ValueError("Set TRIPPLANNER_PUBLIC_HOST to one public DNS hostname.")
    backend = environ.get("TRIPPLANNER_STORAGE_BACKEND", "sqlite")
    if backend not in {"sqlite", "postgres"}:
        raise ValueError("Choose the configured sqlite or postgres storage backend.")
    if backend == "postgres":
        if environ.get("TRIPPLANNER_STORAGE_DIR"):
            raise ValueError("Configure one storage backend; PostgreSQL does not use a local directory.")
        from hosted_postgres import validate_database_url
        database = validate_database_url(environ.get("TRIPPLANNER_DATABASE_URL", ""))
        return secret, hostname, database, backend
    if environ.get("TRIPPLANNER_DATABASE_URL"):
        raise ValueError("A remote database URL requires the explicit postgres storage backend.")
    raw_directory = environ.get("TRIPPLANNER_STORAGE_DIR", "")
    if not isinstance(raw_directory, str) or not raw_directory:
        raise ValueError("Set TRIPPLANNER_STORAGE_DIR to the existing durable mount directory.")
    directory = Path(raw_directory)
    root = Path(__file__).resolve().parent
    if not directory.is_absolute() or not directory.is_dir() or directory.resolve().is_relative_to(root):
        raise ValueError("Storage must be an existing absolute durable directory outside the application source.")
    return secret, hostname, directory.resolve() / "hosted-trips.sqlite3", backend


def _serializer(application):
    # Use the live secret so a deliberate rotation cannot validate old owners.
    return URLSafeTimedSerializer(application.secret_key, salt="tripplanner-hosted-visitor-v1")


def create_hosted_app(environ=None):
    settings = os.environ if environ is None else environ
    secret, hostname, database, backend = _configuration(settings)
    if backend == "postgres":
        import hosted_postgres
        repository = hosted_postgres
    else:
        repository = hosted_saved_trips
    repository.initialize_store(database)
    application = create_app({
        "HOSTED_MODE": True, "SECRET_KEY": secret, "DATABASE": str(database),
        "HOSTED_STORAGE_BACKEND": backend, "HOSTED_FREE_DEMO": backend == "postgres",
        "DEBUG": False, "TESTING": False, "TRUSTED_HOSTS": [hostname],
        "SERVER_NAME": hostname, "PREFERRED_URL_SCHEME": "https",
        "SESSION_COOKIE_NAME": "__Host-tripplanner_session", "SESSION_COOKIE_SECURE": True,
        "SESSION_COOKIE_HTTPONLY": True, "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_PATH": "/", "SESSION_COOKIE_DOMAIN": None,
        "MAX_CONTENT_LENGTH": 65536, "MAX_FORM_MEMORY_SIZE": 65536,
        "MAX_FORM_PARTS": 32,
    })

    @application.before_request
    def identify_visitor():
        if request.endpoint in {"static", "healthz"}:
            return None
        token = None
        try:
            token = _serializer(application).loads(request.cookies.get(VISITOR_COOKIE, ""), max_age=VISITOR_MAX_AGE)
        except (BadSignature, TypeError, ValueError):
            pass
        if not isinstance(token, str) or re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is None:
            token = secrets.token_urlsafe(32)
        g.hosted_visitor_token = token
        g.hosted_owner = hashlib.sha256(token.encode("ascii")).hexdigest()

    @application.after_request
    def protect_responses(response):
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "private, no-store"
            response.vary.add("Cookie")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        response.headers["X-Frame-Options"] = "DENY"
        if hasattr(g, "hosted_visitor_token"):
            response.set_cookie(VISITOR_COOKIE, _serializer(application).dumps(g.hosted_visitor_token),
                                max_age=VISITOR_MAX_AGE, secure=True, httponly=True,
                                samesite="Lax", path="/")
        return response

    @application.get("/healthz")
    def healthz():
        try:
            repository.check_store(application.config["DATABASE"], timeout=application.config["DATABASE_TIMEOUT"])
        except StorageUnavailableError:
            return jsonify(status="unavailable"), 503
        return jsonify(status="ok")

    @application.errorhandler(500)
    def unavailable(error):
        return "TripPlanner is temporarily unavailable. Please try again later.", 500

    # Flask's default exception logger includes a full URL/trace. Log a fixed
    # operational event only; form values, cookies and query strings stay out.
    def log_exception(exc_info):
        application.logger.error("Hosted request failed; no request contents were logged.")
    application.log_exception = log_exception
    return application
