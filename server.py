from __future__ import annotations

import json
import re
import math
import urllib.parse
import urllib.request
from pathlib import Path
from uuid import uuid4

from flask import Flask, abort, jsonify, redirect, request, send_from_directory


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
UPLOADS_DIR = BASE_DIR / "uploads"
STATE_PATH = BASE_DIR / "clock_state.json"
HOME_LOCATION_PATH = BASE_DIR / "home_location.json"
CITIES_PATH = BASE_DIR / "cities.json"
INDEX_PATH = BASE_DIR / "index.html"
MANAGE_PATH = BASE_DIR / "manage.html"

ALLOWED_EXTENSIONS = {".gif", ".webp", ".png", ".jpg", ".jpeg", ".avif"}
DISPLAY_MODES = ["graphic", "simple", "world-daylight", "airport-board", "lichtzeitpegel", "word-clock", "event-clock"]
ROTATION_MODES = ["landscape", "portrait", "landscape-flipped", "portrait-flipped"]
AIRPORT_UNIT_MODES = ["imperial", "metric"]
LICHTZEITPEGEL_COLOR_MODES = ["amber", "red", "green", "blue", "purple", "white"]
WORD_CLOCK_LANGUAGES = ["english", "german", "french", "spanish", "czech", "russian", "portuguese", "japanese", "arabic", "chinese"]
WORD_CLOCK_STYLES = ["direct", "relative"]
WORD_CLOCK_FONTS = ["classic-sans", "urw-gothic-demi", "cursive-italic"]
EVENT_CLOCK_TYPES = ["events", "selected", "births", "deaths", "holidays"]
EVENT_CLOCK_COUNTS = [1, 2, 3, 4]
MAX_AIRPORT_DESTINATIONS = 12
MIN_AIRPORT_ROTATE_SECONDS = 15
MAX_AIRPORT_ROTATE_SECONDS = 3600
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
DEFAULT_STATE = {
    "displayMode": "graphic",
    "defaultPhoto": "assets/bg1.webp",
    "showAnalog": True,
    "mode24": True,
    "rotation": "portrait",
    "airportUnits": "imperial",
    "airportRotateSeconds": 60,
    "wordClockLanguage": "english",
    "wordClockStyle": "direct",
    "wordClockFont": "classic-sans",
    "eventClockLanguage": "english",
    "eventClockFont": "classic-sans",
    "eventClockType": "events",
    "eventClockCount": 3,
    "lichtzeitpegelColors": {
        "H": "amber",
        "h": "amber",
        "M": "amber",
        "m": "amber",
        "S": "amber",
        "s": "amber",
    },
    "airportDestinations": ["nyc-us"],
    "homeLocation": None,
    "customPlaces": [],
}

app = Flask(__name__)
GEOCODE_CACHE: dict[str, dict | None] = {}


def ensure_state() -> None:
    UPLOADS_DIR.mkdir(exist_ok=True)
    if not STATE_PATH.exists():
        STATE_PATH.write_text(json.dumps(DEFAULT_STATE, indent=2), encoding="utf-8")


def load_cities() -> list[dict]:
    return json.loads(CITIES_PATH.read_text(encoding="utf-8"))


def city_exists(city_id: str) -> bool:
    return any(city["id"] == city_id for city in load_cities())


def normalized_text(value) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def normalized_address_key(location: dict) -> str:
    return "|".join([
        normalized_text(location.get("street")),
        normalized_text(location.get("city")),
        normalized_text(location.get("country")),
    ])


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_miles = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * radius_miles * math.asin(math.sqrt(a))


def find_city_match(city_name: str, country_name: str = "") -> dict | None:
    city_key = normalized_text(city_name)
    country_key = normalized_text(country_name)
    if not city_key:
        return None

    cities = load_cities()
    exact = [city for city in cities if normalized_text(city.get("city")) == city_key]
    if country_key:
        country_exact = [city for city in exact if normalized_text(city.get("country")) == country_key]
        if country_exact:
            return country_exact[0]
    if len(exact) == 1:
        return exact[0]
    return None


def nearest_city_for_coords(lat: float, lon: float) -> dict | None:
    cities = load_cities()
    if not cities:
        return None
    return min(cities, key=lambda city: haversine_miles(lat, lon, city["lat"], city["lon"]))


def geocode_location(location: dict) -> dict | None:
    cache_key = normalized_address_key(location)
    if not cache_key.strip("|"):
        return None
    if cache_key in GEOCODE_CACHE:
        return GEOCODE_CACHE[cache_key]

    street = str(location.get("street") or "").strip()
    city = str(location.get("city") or "").strip()
    country = str(location.get("country") or "").strip()
    query = ", ".join(part for part in [street, city, country] if part)
    if not query:
        return None

    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 1,
        "addressdetails": 1,
    }
    request = urllib.request.Request(
        f"{NOMINATIM_SEARCH_URL}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": "ClockDisplay/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        GEOCODE_CACHE[cache_key] = None
        return None

    if not isinstance(payload, list) or not payload:
        GEOCODE_CACHE[cache_key] = None
        return None

    entry = payload[0]
    address = entry.get("address", {}) if isinstance(entry, dict) else {}
    try:
        result = {
            "street": street,
            "city": city or str(address.get("city") or address.get("town") or address.get("village") or "").strip(),
            "country": country or str(address.get("country") or "").strip(),
            "lat": float(entry["lat"]),
            "lon": float(entry["lon"]),
        }
    except (KeyError, TypeError, ValueError):
        GEOCODE_CACHE[cache_key] = None
        return None

    GEOCODE_CACHE[cache_key] = result
    return result


def resolve_location_fields(location: dict) -> dict | None:
    label = str(location.get("label") or "Home").strip() or "Home"
    street_name = str(location.get("street") or "").strip()
    city_name = str(location.get("city") or "").strip()
    country_name = str(location.get("country") or "").strip()
    timezone_name = str(location.get("timezone") or "").strip()
    lat_value = location.get("lat")
    lon_value = location.get("lon")

    matched_city = find_city_match(city_name, country_name) if city_name else None
    if matched_city is None and label and not city_name:
        matched_city = find_city_match(label, country_name)

    lat = None
    lon = None
    try:
        if lat_value is not None and lon_value is not None:
            lat = float(lat_value)
            lon = float(lon_value)
    except (TypeError, ValueError):
        lat = None
        lon = None

    if (lat is None or lon is None) and (street_name or city_name):
        geocoded = geocode_location(location)
        if geocoded:
            street_name = street_name or geocoded.get("street", "")
            city_name = city_name or geocoded.get("city", "")
            country_name = country_name or geocoded.get("country", "")
            lat = geocoded["lat"]
            lon = geocoded["lon"]

    if matched_city:
        city_name = city_name or matched_city["city"]
        country_name = country_name or matched_city["country"]
        timezone_name = timezone_name or matched_city["timezone"]
        if lat is None or lon is None:
            lat = float(matched_city["lat"])
            lon = float(matched_city["lon"])

    if (timezone_name == "" or country_name == "") and lat is not None and lon is not None:
        nearest = nearest_city_for_coords(lat, lon)
        if nearest:
            country_name = country_name or nearest["country"]
            timezone_name = timezone_name or nearest["timezone"]

    if lat is None or lon is None:
        return None

    return {
        "label": label,
        "street": street_name,
        "city": city_name or label,
        "country": country_name,
        "timezone": timezone_name,
        "lat": lat,
        "lon": lon,
    }


def load_state() -> dict:
    ensure_state()
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {}
    state = DEFAULT_STATE.copy()
    state.update(data)
    if state.get("displayMode") not in DISPLAY_MODES:
        state["displayMode"] = DEFAULT_STATE["displayMode"]
    if state.get("rotation") not in ROTATION_MODES:
        state["rotation"] = DEFAULT_STATE["rotation"]
    if state.get("airportUnits") not in AIRPORT_UNIT_MODES:
        state["airportUnits"] = DEFAULT_STATE["airportUnits"]
    if state.get("wordClockLanguage") not in WORD_CLOCK_LANGUAGES:
        state["wordClockLanguage"] = DEFAULT_STATE["wordClockLanguage"]
    if state.get("wordClockStyle") not in WORD_CLOCK_STYLES:
        state["wordClockStyle"] = DEFAULT_STATE["wordClockStyle"]
    if state.get("wordClockFont") not in WORD_CLOCK_FONTS:
        state["wordClockFont"] = DEFAULT_STATE["wordClockFont"]
    if state.get("eventClockLanguage") not in WORD_CLOCK_LANGUAGES:
        state["eventClockLanguage"] = DEFAULT_STATE["eventClockLanguage"]
    if state.get("eventClockFont") not in WORD_CLOCK_FONTS:
        state["eventClockFont"] = DEFAULT_STATE["eventClockFont"]
    if state.get("eventClockType") not in EVENT_CLOCK_TYPES:
        state["eventClockType"] = DEFAULT_STATE["eventClockType"]
    try:
        event_count = int(state.get("eventClockCount", DEFAULT_STATE["eventClockCount"]))
    except (TypeError, ValueError):
        event_count = DEFAULT_STATE["eventClockCount"]
    state["eventClockCount"] = event_count if event_count in EVENT_CLOCK_COUNTS else DEFAULT_STATE["eventClockCount"]
    colors = state.get("lichtzeitpegelColors")
    normalized_colors = DEFAULT_STATE["lichtzeitpegelColors"].copy()
    if isinstance(colors, dict):
        for key in normalized_colors:
            value = str(colors.get(key, normalized_colors[key])).lower()
            if value in LICHTZEITPEGEL_COLOR_MODES:
                normalized_colors[key] = value
    state["lichtzeitpegelColors"] = normalized_colors
    try:
        rotate_seconds = int(state.get("airportRotateSeconds", DEFAULT_STATE["airportRotateSeconds"]))
    except (TypeError, ValueError):
        rotate_seconds = DEFAULT_STATE["airportRotateSeconds"]
    state["airportRotateSeconds"] = max(MIN_AIRPORT_ROTATE_SECONDS, min(MAX_AIRPORT_ROTATE_SECONDS, rotate_seconds))
    state["airportDestinations"] = [
        destination for destination in list(state.get("airportDestinations") or [])[:MAX_AIRPORT_DESTINATIONS]
        if isinstance(destination, str) and city_exists(destination)
    ] or DEFAULT_STATE["airportDestinations"][:]
    state["customPlaces"] = [place for place in state.get("customPlaces") or [] if isinstance(place, dict)]
    state["homeLocation"] = load_persistent_home_location() or normalize_home_location(state.get("homeLocation"))
    return state


def save_state(state: dict) -> None:
    save_persistent_home_location(state.get("homeLocation"))
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    return cleaned or f"upload-{uuid4().hex}.bin"


def classify_photo(path: Path, root: Path, source: str) -> dict:
    relative = path.relative_to(root).as_posix()
    url = f"/{relative}?v={int(path.stat().st_mtime)}"
    return {
        "name": path.name,
        "path": relative,
        "url": url,
        "source": source,
        "size": path.stat().st_size,
    }


def list_photos() -> list[dict]:
    items: list[dict] = []
    if ASSETS_DIR.exists():
        for path in sorted(ASSETS_DIR.iterdir()):
            if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
                items.append(classify_photo(path, BASE_DIR, "assets"))
    if UPLOADS_DIR.exists():
        for path in sorted(UPLOADS_DIR.iterdir()):
            if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
                items.append(classify_photo(path, BASE_DIR, "upload"))
    return items


def photo_exists(photo_path: str) -> bool:
    candidate = (BASE_DIR / photo_path).resolve()
    try:
        candidate.relative_to(BASE_DIR.resolve())
    except ValueError:
        return False
    return candidate.exists() and candidate.is_file()


def normalize_home_location(value):
    if not isinstance(value, dict):
        return None
    return resolve_location_fields(value)


def load_persistent_home_location() -> dict | None:
    if not HOME_LOCATION_PATH.exists():
        return None
    try:
        payload = json.loads(HOME_LOCATION_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return normalize_home_location(payload)


def save_persistent_home_location(home_location: dict | None) -> None:
    normalized = normalize_home_location(home_location)
    if normalized is None:
        if HOME_LOCATION_PATH.exists():
            HOME_LOCATION_PATH.unlink()
        return
    HOME_LOCATION_PATH.write_text(json.dumps(normalized, indent=2), encoding="utf-8")


def normalize_custom_place(place: dict):
    if not isinstance(place, dict):
        return None
    resolved = resolve_location_fields({
        "label": place.get("label") or "Custom place",
        "street": place.get("street") or "",
        "city": place.get("city") or "",
        "country": place.get("country") or "",
        "timezone": place.get("timezone") or "",
        "lat": place.get("lat"),
        "lon": place.get("lon"),
    })
    if resolved is None:
        return None
    resolved["id"] = str(place.get("id") or f"custom-{uuid4().hex[:8]}")
    return resolved


@app.get("/")
def home():
    return redirect("/manage")


@app.get("/display")
def display_page():
    return INDEX_PATH.read_text(encoding="utf-8")


@app.get("/manage")
def manage_page():
    return MANAGE_PATH.read_text(encoding="utf-8")


@app.get("/app.js")
def app_js():
    return send_from_directory(BASE_DIR, "app.js", mimetype="application/javascript")


@app.get("/manage.js")
def manage_js():
    return send_from_directory(BASE_DIR, "manage.js", mimetype="application/javascript")


@app.get("/api/state")
def api_state():
    state = load_state()
    photos = list_photos()
    if not any(item["path"] == state["defaultPhoto"] for item in photos) and photos:
        state["defaultPhoto"] = photos[0]["path"]
        save_state(state)
    return jsonify({
        "state": state,
        "photos": photos,
        "cities": load_cities(),
        "displayModes": DISPLAY_MODES,
        "rotationModes": ROTATION_MODES,
        "airportUnitModes": AIRPORT_UNIT_MODES,
        "lichtzeitpegelColorModes": LICHTZEITPEGEL_COLOR_MODES,
        "wordClockLanguages": WORD_CLOCK_LANGUAGES,
        "wordClockStyles": WORD_CLOCK_STYLES,
        "wordClockFonts": WORD_CLOCK_FONTS,
        "eventClockTypes": EVENT_CLOCK_TYPES,
        "eventClockCounts": EVENT_CLOCK_COUNTS,
        "maxAirportDestinations": MAX_AIRPORT_DESTINATIONS,
        "airportRotateSecondsRange": {
            "min": MIN_AIRPORT_ROTATE_SECONDS,
            "max": MAX_AIRPORT_ROTATE_SECONDS,
        },
    })


@app.post("/api/state")
def update_state():
    payload = request.get_json(silent=True) or {}
    state = load_state()

    if "displayMode" in payload:
        mode = str(payload["displayMode"])
        if mode not in DISPLAY_MODES:
            return jsonify({"error": "Unsupported display mode"}), 400
        state["displayMode"] = mode

    if "defaultPhoto" in payload:
        value = str(payload["defaultPhoto"])
        if not photo_exists(value):
            return jsonify({"error": "Photo not found"}), 404
        state["defaultPhoto"] = value

    if "rotation" in payload:
        rotation = str(payload["rotation"])
        if rotation not in ROTATION_MODES:
            return jsonify({"error": "Unsupported rotation mode"}), 400
        state["rotation"] = rotation

    if "airportUnits" in payload:
        airport_units = str(payload["airportUnits"])
        if airport_units not in AIRPORT_UNIT_MODES:
            return jsonify({"error": "Unsupported airport unit mode"}), 400
        state["airportUnits"] = airport_units

    if "airportRotateSeconds" in payload:
        try:
            rotate_seconds = int(payload["airportRotateSeconds"])
        except (TypeError, ValueError):
            return jsonify({"error": "airportRotateSeconds must be an integer"}), 400
        if not MIN_AIRPORT_ROTATE_SECONDS <= rotate_seconds <= MAX_AIRPORT_ROTATE_SECONDS:
            return jsonify({"error": "airportRotateSeconds out of range"}), 400
        state["airportRotateSeconds"] = rotate_seconds

    if "wordClockLanguage" in payload:
        word_clock_language = str(payload["wordClockLanguage"])
        if word_clock_language not in WORD_CLOCK_LANGUAGES:
            return jsonify({"error": "Unsupported word clock language"}), 400
        state["wordClockLanguage"] = word_clock_language

    if "wordClockStyle" in payload:
        word_clock_style = str(payload["wordClockStyle"])
        if word_clock_style not in WORD_CLOCK_STYLES:
            return jsonify({"error": "Unsupported word clock style"}), 400
        state["wordClockStyle"] = word_clock_style

    if "wordClockFont" in payload:
        word_clock_font = str(payload["wordClockFont"])
        if word_clock_font not in WORD_CLOCK_FONTS:
            return jsonify({"error": "Unsupported word clock font"}), 400
        state["wordClockFont"] = word_clock_font

    if "eventClockLanguage" in payload:
        event_clock_language = str(payload["eventClockLanguage"])
        if event_clock_language not in WORD_CLOCK_LANGUAGES:
            return jsonify({"error": "Unsupported event clock language"}), 400
        state["eventClockLanguage"] = event_clock_language

    if "eventClockFont" in payload:
        event_clock_font = str(payload["eventClockFont"])
        if event_clock_font not in WORD_CLOCK_FONTS:
            return jsonify({"error": "Unsupported event clock font"}), 400
        state["eventClockFont"] = event_clock_font

    if "eventClockType" in payload:
        event_clock_type = str(payload["eventClockType"])
        if event_clock_type not in EVENT_CLOCK_TYPES:
            return jsonify({"error": "Unsupported event clock type"}), 400
        state["eventClockType"] = event_clock_type

    if "eventClockCount" in payload:
        try:
            event_clock_count = int(payload["eventClockCount"])
        except (TypeError, ValueError):
            return jsonify({"error": "eventClockCount must be an integer"}), 400
        if event_clock_count not in EVENT_CLOCK_COUNTS:
            return jsonify({"error": "Unsupported event clock count"}), 400
        state["eventClockCount"] = event_clock_count

    if "lichtzeitpegelColors" in payload:
        incoming_colors = payload["lichtzeitpegelColors"]
        if not isinstance(incoming_colors, dict):
            return jsonify({"error": "lichtzeitpegelColors must be an object"}), 400
        normalized_colors = DEFAULT_STATE["lichtzeitpegelColors"].copy()
        for key in normalized_colors:
            value = str(incoming_colors.get(key, normalized_colors[key])).lower()
            if value not in LICHTZEITPEGEL_COLOR_MODES:
                return jsonify({"error": f"Unsupported LichtZeitPegel color: {value}"}), 400
            normalized_colors[key] = value
        state["lichtzeitpegelColors"] = normalized_colors

    if "airportDestinations" in payload:
        incoming = payload["airportDestinations"]
        if not isinstance(incoming, list):
            return jsonify({"error": "airportDestinations must be a list"}), 400
        normalized = []
        for item in incoming[:MAX_AIRPORT_DESTINATIONS]:
            destination = str(item)
            if not city_exists(destination):
                return jsonify({"error": f"Destination not found: {destination}"}), 404
            if destination not in normalized:
                normalized.append(destination)
        state["airportDestinations"] = normalized or DEFAULT_STATE["airportDestinations"][:]

    if "homeLocation" in payload:
        home = payload["homeLocation"]
        if home in (None, ""):
            state["homeLocation"] = None
        else:
            normalized_home = normalize_home_location(home)
            if normalized_home is None:
                return jsonify({"error": "Could not resolve home location from the provided address or city."}), 400
            state["homeLocation"] = normalized_home

    if "customPlaces" in payload:
        incoming_places = payload["customPlaces"]
        if not isinstance(incoming_places, list):
            return jsonify({"error": "customPlaces must be a list"}), 400
        normalized_places = []
        for place in incoming_places:
            normalized_place = normalize_custom_place(place)
            if normalized_place is None:
                return jsonify({"error": "Could not resolve one of the custom places from the provided address or city."}), 400
            normalized_places.append(normalized_place)
        state["customPlaces"] = normalized_places

    for field in ("showAnalog", "mode24"):
        if field in payload:
            state[field] = bool(payload[field])

    save_state(state)
    return jsonify({"state": state})


@app.get("/api/photos")
def api_photos():
    return jsonify({"photos": list_photos(), "state": load_state()})


@app.post("/api/photos")
def upload_photos():
    ensure_state()
    files = request.files.getlist("photos")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    uploaded = []
    for file in files:
        if not file.filename:
            continue
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            continue
        target_name = safe_filename(Path(file.filename).stem) + ext
        target_path = UPLOADS_DIR / target_name
        if target_path.exists():
            target_path = UPLOADS_DIR / f"{Path(target_name).stem}-{uuid4().hex[:6]}{ext}"
        file.save(target_path)
        uploaded.append(target_path.name)

    if not uploaded:
        return jsonify({"error": "No supported files uploaded"}), 400

    state = load_state()
    if not photo_exists(state.get("defaultPhoto", "")):
        state["defaultPhoto"] = f"uploads/{uploaded[0]}"
        save_state(state)

    return jsonify({"uploaded": uploaded, "photos": list_photos(), "state": state})


@app.delete("/api/photos/<path:photo_name>")
def delete_photo(photo_name: str):
    target = (UPLOADS_DIR / photo_name).resolve()
    try:
        target.relative_to(UPLOADS_DIR.resolve())
    except ValueError:
        abort(400)

    if not target.exists() or not target.is_file():
        abort(404)

    target.unlink()

    state = load_state()
    if state.get("defaultPhoto") == f"uploads/{target.name}":
        photos = list_photos()
        state["defaultPhoto"] = photos[0]["path"] if photos else DEFAULT_STATE["defaultPhoto"]
        save_state(state)

    return jsonify({"deleted": target.name, "photos": list_photos(), "state": load_state()})


@app.get("/assets/<path:filename>")
def assets(filename: str):
    return send_from_directory(ASSETS_DIR, filename)


@app.get("/uploads/<path:filename>")
def uploads(filename: str):
    return send_from_directory(UPLOADS_DIR, filename)


if __name__ == "__main__":
    ensure_state()
    app.run(host="0.0.0.0", port=8000)
