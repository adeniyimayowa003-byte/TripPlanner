"""Flask routes joining the form, explainable recommendations, and current draft."""

import os
from pathlib import Path
import re
import secrets

from flask import Flask, flash, g, redirect, render_template, request, session, url_for

from catalog import (
    get_supported_destinations,
    get_supported_interests,
    get_supported_paces,
    load_catalog,
    load_destinations,
    get_destination,
)
from csrf import get_csrf_token, valid_csrf_token
from currency_context import issue_currency_context, read_currency_context
from currencies import get_currency
from maps import build_maps_url
from photos import load_image_manifest, get_place_image
from version import APP_VERSION
from drafts import load_draft, serialize_draft
from money import daily_allowance, format_money
from preferences import validate_trip_preferences
from recommendations import recommend_trip_ideas
from saved_trips import (
    SavedTripUnavailableError,
    StorageUnavailableError,
    get_trip,
    list_trips,
    save_trip,
)
from snapshots import (
    build_snapshot,
    dump_snapshot,
    load_snapshot,
    normalize_trip_name,
    snapshot_fingerprint,
)


# Stable within this local process; set an environment secret to reuse signed cookies.
_LOCAL_SECRET = secrets.token_hex(32)


def create_app(test_config=None):
    """Create an independent app for the local server or pytest's test client."""
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("TRIPPLANNER_SECRET_KEY") or _LOCAL_SECRET,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        DATABASE=os.environ.get("TRIPPLANNER_DATABASE")
        or str(Path(app.instance_path) / "tripplanner.sqlite3"),
        DATABASE_TIMEOUT=5.0,
    )
    if test_config is not None:
        app.config.update(test_config)

    app.jinja_env.filters["money"] = lambda amount, currency="EUR": format_money(amount, currency=currency)
    app.jinja_env.filters["label"] = lambda value: str(value).replace("-", " ").title()
    app.jinja_env.filters["tag_label"] = app.jinja_env.filters["label"]

    def current_catalog():
        # One consistent catalog snapshot per HTTP request, not cached across edits.
        if not hasattr(g, "catalog"):
            g.catalog = load_catalog()
        return g.catalog

    def current_draft():
        if not hasattr(g, "current_draft"):
            g.current_draft = load_draft(
                session.get("trip_draft"), catalog=current_catalog(), profiles=load_destinations()
            )
            if "trip_draft" in session and g.current_draft is None:
                session.pop("trip_draft", None)
                g.recovered_draft = True
                flash(
                    "Your current draft is no longer available. Please choose your preferences again.",
                    "notice",
                )
        return g.current_draft

    def current_photos():
        # Display assets have no bearing on catalog validation or saved hashes.
        if not hasattr(g, "photo_manifest"):
            try:
                g.photo_manifest = load_image_manifest()
            except (OSError, ValueError):
                app.logger.warning("Photo metadata unavailable; showing image fallbacks.")
                g.photo_manifest = {"version": 1, "images": {}, "destinations": {}}
        return g.photo_manifest

    def photo_for_place(place_id, destination):
        return get_place_image(place_id, destination, manifest=current_photos(), static_root=app.static_folder)

    @app.context_processor
    def shared_page_values():
        # Historical pages must survive missing catalog files and stale cookies.
        # In particular, rendering a saved 404 must not validate/pop a draft.
        saved_page = request.path == "/trips" or request.path.startswith("/trips/")
        return {
            "current_draft": None if saved_page or request.endpoint in {"image_credits", "about"} else current_draft(),
            "csrf_token": get_csrf_token,
            "maps_url": build_maps_url,
            "photo_for_place": photo_for_place,
            "app_version": APP_VERSION,
            "hosted_mode": bool(app.config.get("HOSTED_MODE")),
            "free_demo": bool(app.config.get("HOSTED_FREE_DEMO")),
        }

    @app.before_request
    def protect_form_changes():
        if request.method == "POST" and request.endpoint in {"plan", "clear_draft", "save_itinerary"}:
            if not valid_csrf_token(request.form.get("csrf_token")):
                # Rendering an error must not replace or discard the existing draft.
                g.current_draft = None
                return render_template(
                    "error.html",
                    message="This form could not be verified. Open the planner and try again.",
                ), 400
            if request.endpoint == "plan":
                try:
                    g.currency_context = read_currency_context(request.form.get("currency_context"))
                except ValueError:
                    g.current_draft = None
                    return render_template("error.html", message="This form's currency could not be verified. Open the planner and try again."), 400

    @app.get("/")
    def home():
        places = current_catalog()
        return render_template(
            "index.html",
            destinations=get_supported_destinations(places),
            catalog_count=len(places),
        )

    @app.route("/plan", methods=["GET", "POST"])
    def plan():
        places = current_catalog()
        profiles = load_destinations()
        saved = current_draft()
        values = {
            "destination": "", "days": "", "budget": "", "interests": [],
            "pace": "", "family_friendly": False,
        }
        errors = {}
        display_currency = saved.get("currency", "EUR") if saved else None
        confirmation_required = False
        if request.method == "POST":
            values, errors = validate_trip_preferences(request.form, catalog=places, profiles=profiles)
            context = g.currency_context
            try:
                display_currency = get_destination(request.form.get("destination", ""), profiles=profiles)["currency"]
            except ValueError:
                display_currency = context["currency"]
            changed = (context["currency"] is not None and display_currency is not None
                       and context["currency"] != display_currency)
            confirmation_required = changed or context["confirmation_required"]
            if changed or (confirmation_required and request.form.get("confirm_currency_change") != "on"):
                errors["confirm_currency_change"] = f"Review your amount in {display_currency} and confirm this currency change. No conversion is performed."
            if not errors:
                session["trip_draft"] = serialize_draft(values)
                # A GET result page can be refreshed without repeating the form POST.
                return redirect(url_for("recommendations"), code=303)
            # Currency review is a form error too: do not replace raw answers
            # with normalized Decimal/int values before the traveler accepts.
            values = {"destination": request.form.get("destination", ""),
                      "days": request.form.get("days", ""), "budget": request.form.get("budget", ""),
                      "interests": request.form.getlist("interests"), "pace": request.form.get("pace", ""),
                      "family_friendly": request.form.get("family_friendly") == "on"}
        elif saved is not None:
            values = {**saved, "budget": format_money(saved["budget"], currency=display_currency)}

        destinations = get_supported_destinations(places)
        canonical = {
            destination.casefold(): destination for destination in destinations
        }
        option_destination = canonical.get(
            str(values["destination"]).strip().casefold(),
            destinations[0] if destinations else None,
        )
        destination_options = {
            destination: {
                "interests": get_supported_interests(places, destination=destination),
                "paces": get_supported_paces(destination, places),
                "currency": get_destination(destination, profiles=profiles)["currency"],
                "precision": get_currency(get_destination(destination, profiles=profiles)["currency"]).precision,
                "maximum_minor": int(get_currency(get_destination(destination, profiles=profiles)["currency"]).maximum
                                     / get_currency(get_destination(destination, profiles=profiles)["currency"]).quantum),
            }
            for destination in destinations if any(p["name"] == destination for p in profiles)
        }
        options = destination_options.get(
            option_destination, {"interests": [], "paces": []}
        )
        return render_template(
            "trip_preferences.html",
            values=values, errors=errors, destinations=destinations,
            interests=options["interests"], paces=options["paces"],
            destination_options=destination_options,
            interest_options=destination_options,
            currency=display_currency,
            currency_spec=get_currency(display_currency or "EUR"),
            currency_context=issue_currency_context(display_currency, confirmation_required=confirmation_required),
            confirmation_required=confirmation_required,
        )

    @app.get("/credits")
    def image_credits():
        return render_template("credits.html", photos=list(current_photos()["images"].values()))

    @app.get("/about")
    def about():
        return render_template("about.html")

    @app.get("/recommendations")
    def recommendations():
        preferences = current_draft()
        if preferences is None:
            if not getattr(g, "recovered_draft", False):
                flash(
                    "You do not have a current draft yet. Choose your preferences to get started.",
                    "notice",
                )
            return redirect(url_for("plan"))
        items, notices = recommend_trip_ideas(preferences, catalog=current_catalog())
        return render_template(
            "recommendations.html",
            preferences=preferences,
            daily_budget=daily_allowance(preferences["budget"], preferences["days"], currency=preferences["currency"]),
            items=items, notices=notices,
        )

    @app.get("/itinerary")
    def itinerary():
        preferences = current_draft()
        if preferences is None:
            return recover_missing_draft()

        # The displayed result and the hidden content hash describe one snapshot.
        payload = build_snapshot(preferences, current_catalog())
        return render_current_itinerary(payload)

    def recover_missing_draft():
        if not getattr(g, "recovered_draft", False):
            flash(
                "You do not have a current draft yet. Choose your preferences to get started.",
                "notice",
            )
        return redirect(url_for("plan"))

    def render_current_itinerary(payload, *, trip_name="", errors=None, save_error=None, status=200):
        # Loading our own JSON restores exact Decimal values for existing filters
        # and the free-versus-paid display. It never reads the catalog again.
        display = load_snapshot(dump_snapshot(payload))
        return render_template(
            "itinerary.html",
            preferences=display["preferences"],
            daily_budget=display["daily_budget"],
            itinerary=display["itinerary"],
            snapshot_fingerprint=snapshot_fingerprint(payload),
            trip_name=trip_name,
            errors=errors or {},
            save_error=save_error,
        ), status

    def saved_error(message, status):
        return render_template("saved_error.html", message=message), status

    @app.post("/itinerary/save")
    def save_itinerary():
        # CSRF has already been checked before any catalog or storage access.
        preferences = current_draft()
        if preferences is None:
            return recover_missing_draft()

        reviewed_hash = request.form.get("snapshot_fingerprint", "")
        if re.fullmatch(r"[0-9a-f]{64}", reviewed_hash) is None:
            return saved_error("This save form is incomplete. Review your itinerary and try again.", 400)
        payload = build_snapshot(preferences, current_catalog())
        if not secrets.compare_digest(reviewed_hash, snapshot_fingerprint(payload)):
            return saved_error(
                "Your trip has changed. Review the updated itinerary before saving", 409
            )

        raw_name = request.form.get("trip_name", "")
        try:
            title = normalize_trip_name(raw_name, preferences)
        except ValueError as error:
            return render_current_itinerary(
                payload, trip_name=raw_name, errors={"trip_name": str(error)}
            )

        try:
            trip, created = storage_operation("save_trip")(
                app.config["DATABASE"], title, payload,
                timeout=app.config["DATABASE_TIMEOUT"],
                **storage_owner(),
            )
        except SavedTripUnavailableError:
            return saved_error(
                "The matching saved snapshot is unavailable. No trip was changed. Return to Saved trips for recovery.",
                409,
            )
        except StorageUnavailableError:
            return render_current_itinerary(
                payload, trip_name=raw_name,
                save_error="Saved trips are temporarily unavailable. Your draft and trip name are still here. Try saving again later.",
                status=503,
            )

        flash("Your trip has been saved." if created else "This trip is already saved.", "success")
        return redirect(url_for("saved_trip", trip_id=trip["id"]), code=303)

    @app.get("/trips")
    def saved_trips():
        try:
            trips = storage_operation("list_trips")(
                app.config["DATABASE"], timeout=app.config["DATABASE_TIMEOUT"], **storage_owner()
            )
        except StorageUnavailableError:
            return saved_error("Saved trips are temporarily unavailable. Please try again later.", 503)
        return render_template("saved_trips.html", trips=trips)

    @app.get("/trips/<trip_id>")
    def saved_trip(trip_id):
        # Check length before int conversion too: arbitrarily large URLs are not
        # database IDs, and SQLite only accepts signed 64-bit integers.
        if (
            re.fullmatch(r"[0-9]{1,19}", trip_id) is None
            or not 0 < int(trip_id) <= 9223372036854775807
        ):
            return saved_error("That saved trip could not be found.", 404)
        try:
            trip = storage_operation("get_trip")(
                app.config["DATABASE"], int(trip_id), timeout=app.config["DATABASE_TIMEOUT"],
                **storage_owner(),
            )
        except StorageUnavailableError:
            return saved_error("Saved trips are temporarily unavailable. Please try again later.", 503)
        if trip is None:
            return saved_error("That saved trip could not be found.", 404)
        if not trip["available"]:
            return saved_error(
                "This saved snapshot is unavailable or uses an unsupported format. It has not been changed or deleted.",
                409,
            )
        snapshot = trip["snapshot"]
        return render_template(
            "saved_trip.html", trip=trip, snapshot=snapshot,
            preferences=snapshot["preferences"], daily_budget=snapshot["daily_budget"],
            itinerary=snapshot["itinerary"],
        )

    @app.errorhandler(404)
    def page_not_found(error):
        if request.path == "/trips" or request.path.startswith("/trips/"):
            return saved_error("That saved trip could not be found.", 404)
        return error

    @app.post("/draft/clear")
    def clear_draft():
        session.pop("trip_draft", None)
        flash("Your current draft has been cleared. Start fresh whenever you like.", "success")
        return redirect(url_for("plan"), code=303)

    def storage_operation(name):
        if app.config.get("HOSTED_MODE"):
            # Lazy import keeps native packaging independent of hosted modules.
            if app.config.get("HOSTED_STORAGE_BACKEND") == "postgres":
                import hosted_postgres
                return getattr(hosted_postgres, name)
            import hosted_saved_trips
            return getattr(hosted_saved_trips, name)
        return {"save_trip": save_trip, "list_trips": list_trips, "get_trip": get_trip}[name]

    def storage_owner():
        # This value comes only from the validated signed-cookie hook, never
        # from request query/form fields or a URL's guessed trip number.
        return {"owner": g.hosted_owner} if app.config.get("HOSTED_MODE") else {}

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
