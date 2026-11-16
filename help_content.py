"""Approved, versioned self-service guidance; no provider or storage access."""
from dataclasses import dataclass

FAQ_VERSION = 2


@dataclass(frozen=True)
class FAQ:
    id: str
    question: str
    answer: str
    source: str


_FAQ = (
    FAQ("cities", "Which cities can I plan?",
        "Paris, Lagos, London, New York City, Tokyo and Cape Town are the six curated cities. "
        "The catalog contains 48 sourced venues. This is not worldwide live travel search.",
        "README.md; data/destinations.json; data/places.json"),
    FAQ("allowance", "What does my allowance cover?",
        "Your allowance is the total activities and food budget per person for the whole trip, "
        "in the destination currency. It is not a payment to TripPlanner or a booking. "
        "The planner divides it across your days; rounded daily displays do not authorize overspending. "
        "Flights, accommodation, transport and missing meals are excluded. Unallocated money is not "
        "guaranteed savings or proof that your real holiday fits the budget. Currency changes require "
        "review; no exchange-rate conversion is performed.",
        "specs/phase-05-itinerary.md §5; specs/phase-08-expanded-release.md; money.py; itinerary.py"),
    FAQ("gaps", "Why are itinerary slots or meals missing?",
        "The greedy scheduler selects matching catalog ideas without repeating places, using your "
        "interests, allowance, pace and family-friendly preference. Limited coverage or combined daily "
        "costs can leave gaps. Restaurants are evening suggestions, at most one per day; an activity "
        "is not a meal. Empty slots are not free activities. Meals are not fully covered. Try changing "
        "your preferences or make independent arrangements. The schedule is not an optimal route.",
        "specs/phase-05-itinerary.md; itinerary.py"),
    FAQ("estimates", "Are prices, opening hours and time slots verified live?",
        "Costs and time slots are illustrative estimates. Check venue sources for current prices, "
        "opening hours, availability and suitability before traveling. TripPlanner does not verify "
        "live prices, routing, accessibility or dietary requirements and cannot make bookings.",
        "README.md; specs/phase-08-expanded-release.md"),
    FAQ("saving", "How do saving and browser cookies work?",
        "On the hosted website a protected signed cookie separates anonymous collections. It renews "
        "for 365 days on valid visits. Clearing cookies, private browsing, changing browser/profile/device "
        "or expiry can lose access. People sharing a browser profile share guest access. There is "
        "no account recovery or cross-device sync in this release. Cookie expiry does not delete stored "
        "rows. Avoid sensitive information in trip names. Local preview collections are shared by "
        "browsers using that same preview database.",
        "PRIVACY.md; hosted.py"),
    FAQ("snapshots", "Why did a saved estimate not update?",
        "A saved trip is an immutable historical v1/v2 snapshot: original preferences, results and "
        "estimates are kept. Editing your draft or the catalog does not rewrite it. Generate a new "
        "trip for a new calculation. An unavailable historical snapshot is not silently reset.",
        "specs/phase-06-saved-trips.md; snapshots.py"),
    FAQ("maps", "How do Google Maps links work?",
        "Maps buttons open an external Google Maps page for a public venue. Internet and service "
        "access may be needed. No API key, embedded map or booking is supplied. External services "
        "have their own privacy policies; the planner remains usable without opening those links.",
        "PRIVACY.md; maps.py"),
    FAQ("hosting", "Why does the online demo take time to open?",
        "Free hosting can sleep while idle and wake slowly. Wait and retry rather than repeatedly "
        "submitting saves. Free-service quotas may interrupt availability. There is no fixed wake-up "
        "time or continuous-uptime guarantee. Hosted saves use a separate persistent online database.",
        "specs/phase-09-free-demo.md; PRIVACY.md"),
    FAQ("native", "Why are my Windows, Android and online saved trips different?",
        "Each native device/profile and the hosted website have independent collections. The current "
        "downloadable apps do not upload or synchronize their local trips automatically. On-device "
        "planning and local saves work offline; the hosted website needs internet. An online sign-in "
        "would not by itself import an offline collection. Existing downloads are unchanged.",
        "PRIVACY.md; android_runtime.py; app_runtime.py"),
    FAQ("unavailable", "Where are accounts and the AI assistant?",
        "Accounts and cross-device account access are proposed future increments and are unavailable "
        "here. No integrated AI model is enabled in this candidate. The assistant page provides a "
        "deterministic FAQ/catalog fallback with sources. A tested server adapter is available for "
        "future verified, configured AI access; no live model call is claimed. The core planner "
        "uses explainable scoring rules and a greedy scheduler, not an LLM. Guest planning and Help "
        "need no identity or model provider. A ChatGPT subscription does not supply website "
        "API access. No paid upgrade is required to use this planner.",
        "README.md; approved Phase 10 specification"),
    FAQ("themes", "How do Light, Dark and device themes work?",
        "Choose Appearance to use Light, Dark or your device setting. The preference belongs to this "
        "browser/origin, not a cloud account. Without JavaScript the page follows the device setting. "
        "Changing appearance does not change your trip or its saved snapshot.",
        "specs/phase-07-appearance.md; static/js/appearance.js"),
    FAQ("support", "Can I contact customer support or get emergency assistance?",
        "This is self-service guidance for a student project. There is no staffed support service, "
        "support inbox, ticket queue or response-time promise. TripPlanner is not an emergency service "
        "and does not monitor emergencies. This Help page explains the project's actual limits.",
        "approved Phase 10 specification"),
)


def search_faq(query):
    """Return immutable matching records; bounded plain-text search, no regex."""
    terms = str(query)[:200].strip().casefold().split()
    return tuple(item for item in _FAQ
                 if all(term in (item.question + " " + item.answer).casefold() for term in terms))
