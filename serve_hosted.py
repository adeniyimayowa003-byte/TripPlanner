"""Production web entry point; no Flask development server or native runtime."""
import logging
import os
import re

from hosted import create_hosted_app


def validate_port(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{1,5}", value) is None or not 1 <= int(value) <= 65535:
        raise ValueError("PORT must be an integer from 1 to 65535.")
    return int(value)


def main():
    port = validate_port(os.environ.get("PORT", ""))
    application = create_hosted_app()
    from waitress import serve
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    # Waitress has no access log by default. Trust no forwarded host/IP headers.
    serve(application, host="0.0.0.0", port=port, threads=4,
          clear_untrusted_proxy_headers=True, max_request_body_size=65536,
          max_request_header_size=16384, channel_timeout=60,
          expose_tracebacks=False, ident="TripPlanner")


if __name__ == "__main__":
    main()
