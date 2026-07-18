import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlencode, urlparse


DEFAULT_METRICS = {
    "steps": 0,
    "heart_rate": "N/A",
    "sleep_hours": "N/A",
    "calories": "N/A",
}


def build_health_dashboard(metrics=None):
    """Build a simple health dashboard message for Telegram."""
    values = dict(DEFAULT_METRICS)
    if metrics:
        values.update(metrics)

    return (
        "Health Dashboard\n"
        f"Steps: {values['steps']}\n"
        f"Heart Rate: {values['heart_rate']}\n"
        f"Sleep: {values['sleep_hours']}\n"
        f"Calories: {values['calories']}\n\n"
        "Connect your Google Health account to view live data."
    )


def build_google_health_auth_url(user_id):
    """Build a Google OAuth URL for the first-step health login flow."""
    client_id = os.getenv("GOOGLE_HEALTH_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_HEALTH_REDIRECT_URI") or "http://localhost:8081/health/callback"
    scopes = [
        "https://www.googleapis.com/auth/fitness.activity.read",
        "https://www.googleapis.com/auth/fitness.heart_rate.read",
        "https://www.googleapis.com/auth/fitness.sleep.read",
        "openid",
        "email",
        "profile",
    ]

    params = {
        "client_id": client_id or "",
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
        "state": str(user_id),
    }

    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def parse_health_callback_params(query_string):
    """Parse OAuth callback query parameters into a friendly dictionary."""
    if not query_string:
        return {}

    if query_string.startswith("?"):
        query_string = query_string[1:]

    parsed = parse_qs(query_string, keep_blank_values=True)
    return {
        key: value[0] if isinstance(value, list) and len(value) == 1 else value
        for key, value in parsed.items()
    }


def _get_connection_store_path():
    return os.path.join(os.path.dirname(__file__), "health_connections.json")


def _get_token_store_path():
    return os.path.join(os.path.dirname(__file__), "health_tokens.json")


def load_connected_users():
    """Load the set of users that have completed the health connection flow."""
    path = _get_connection_store_path()
    if not os.path.exists(path):
        return set()

    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        users = data.get("connected_users", [])
        return {str(user_id) for user_id in users}
    except Exception:
        return set()


def save_connected_users(user_ids):
    """Persist the connected users set to disk."""
    path = _get_connection_store_path()
    payload = {"connected_users": sorted(str(user_id) for user_id in user_ids)}
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def load_health_tokens():
    """Load stored Google OAuth tokens by Telegram user ID."""
    path = _get_token_store_path()
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}


def save_health_tokens(tokens_by_user):
    """Persist Google OAuth tokens by Telegram user ID."""
    path = _get_token_store_path()
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(tokens_by_user, handle, indent=2)


def store_health_token(user_id, token_payload):
    """Persist the OAuth token payload for a Telegram user."""
    tokens = load_health_tokens()
    tokens[str(user_id)] = token_payload
    save_health_tokens(tokens)
    return True


def get_health_token(user_id):
    return load_health_tokens().get(str(user_id))


def is_health_connected(user_id):
    return str(user_id) in load_connected_users()


def mark_health_connected(user_id):
    user_ids = load_connected_users()
    user_ids.add(str(user_id))
    save_connected_users(user_ids)
    return True


def exchange_google_code_for_token(code, redirect_uri, user_id):
    """Exchange an OAuth code for a token payload and store it for later use."""
    client_id = os.getenv("GOOGLE_HEALTH_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_HEALTH_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET")
    token_uri = "https://oauth2.googleapis.com/token"

    if not code or not client_id:
        payload = {"error": "missing_google_credentials"}
        store_health_token(user_id, payload)
        mark_health_connected(user_id)
        return payload

    request_data = urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret or "",
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode("utf-8")

    request = urllib.request.Request(
        token_uri,
        data=request_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except Exception as exc:
        payload = {"error": str(exc)}

    store_health_token(user_id, payload)
    mark_health_connected(user_id)
    return payload


def handle_health_callback(query_string, bot=None):
    """Handle the Google OAuth callback and mark the user as connected."""
    params = parse_health_callback_params(query_string)
    code = params.get("code")
    state = params.get("state")

    if not code:
        return {"status": "error", "message": "No Google OAuth code was returned."}

    redirect_uri = os.getenv("GOOGLE_HEALTH_REDIRECT_URI") or "http://localhost:8081/health/callback"
    payload = exchange_google_code_for_token(code, redirect_uri, state)

    if bot and state:
        try:
            bot.send_message(chat_id=int(state), text="Health connected successfully. Tap Health again to view your dashboard.")
        except Exception:
            pass

    return {
        "status": "ok",
        "message": "Health connected successfully.",
        "payload": payload,
    }


def fetch_health_metrics(user_id, token_payload=None):
    """Fetch real health metrics from Google Fit API for a given user."""
    if token_payload is None and user_id is not None:
        token_payload = get_health_token(user_id)

    if not token_payload or "access_token" not in token_payload:
        return {
            "steps": 0,
            "heart_rate": "N/A",
            "sleep_hours": "N/A",
            "calories": "N/A",
        }

    access_token = token_payload.get("access_token")
    metrics = {}

    try:
        metrics["steps"] = _fetch_steps_from_google(access_token)
    except Exception as exc:
        print(f"Error fetching steps: {exc}")
        metrics["steps"] = "N/A"

    try:
        metrics["heart_rate"] = _fetch_heart_rate_from_google(access_token)
    except Exception as exc:
        print(f"Error fetching heart rate: {exc}")
        metrics["heart_rate"] = "N/A"

    try:
        metrics["sleep_hours"] = _fetch_sleep_from_google(access_token)
    except Exception as exc:
        print(f"Error fetching sleep: {exc}")
        metrics["sleep_hours"] = "N/A"

    try:
        metrics["calories"] = _fetch_calories_from_google(access_token)
    except Exception as exc:
        print(f"Error fetching calories: {exc}")
        metrics["calories"] = "N/A"

    return metrics


def _fetch_steps_from_google(access_token):
    """Fetch step count for today from Google Fit API."""
    now_ms = int(__import__("time").time() * 1000)
    start_of_day_ms = int(
        __import__("datetime").datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000
    )

    body = {
        "aggregateBy": [
            {
                "dataTypeName": "com.google.step_count.delta",
            }
        ],
        "bucketByTime": {"durationMillis": 86400000},
        "startTimeMillis": start_of_day_ms,
        "endTimeMillis": now_ms,
    }

    response_data = _make_google_fit_request(
        access_token,
        "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate",
        method="POST",
        body=json.dumps(body),
    )

    if not response_data or "bucket" not in response_data:
        return 0

    total_steps = 0
    for bucket in response_data.get("bucket", []):
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                value = point.get("value", [{}])[0]
                total_steps += value.get("intVal", 0)

    return total_steps


def _fetch_heart_rate_from_google(access_token):
    """Fetch recent heart rate from Google Fit API."""
    now_ms = int(__import__("time").time() * 1000)
    start_time_ms = int((now_ms - 3600000) / 1000)

    response_data = _make_google_fit_request(
        access_token,
        f"https://www.googleapis.com/fitness/v1/users/me/dataset/com.google.heart_rate.bpm/range"
        f"?startTime={start_time_ms}s&endTime={now_ms // 1000}s",
    )

    if not response_data or "point" not in response_data:
        return "N/A"

    points = response_data.get("point", [])
    if not points:
        return "N/A"

    latest_value = points[-1].get("value", [{}])[0].get("fpVal", "N/A")
    return f"{int(latest_value)} bpm" if isinstance(latest_value, (int, float)) else "N/A"


def _fetch_sleep_from_google(access_token):
    """Fetch sleep duration for last night from Google Fit API."""
    now_ms = int(__import__("time").time() * 1000)
    yesterday_start_ms = int((now_ms - 86400000) / 1000)

    body = {
        "aggregateBy": [
            {
                "dataTypeName": "com.google.sleep.segment",
            }
        ],
        "bucketByTime": {"durationMillis": 86400000},
        "startTimeMillis": yesterday_start_ms * 1000,
        "endTimeMillis": now_ms,
    }

    response_data = _make_google_fit_request(
        access_token,
        "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate",
        method="POST",
        body=json.dumps(body),
    )

    if not response_data or "bucket" not in response_data:
        return "N/A"

    total_sleep_ms = 0
    for bucket in response_data.get("bucket", []):
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                duration_ms = point.get("endTimeNanos", 0) - point.get("startTimeNanos", 0)
                total_sleep_ms += duration_ms // 1000000

    sleep_hours = total_sleep_ms / 3600000
    return f"{sleep_hours:.1f} hrs" if sleep_hours > 0 else "N/A"


def _fetch_calories_from_google(access_token):
    """Fetch calories burned today from Google Fit API."""
    now_ms = int(__import__("time").time() * 1000)
    start_of_day_ms = int(
        __import__("datetime").datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000
    )

    body = {
        "aggregateBy": [
            {
                "dataTypeName": "com.google.calories.expended",
            }
        ],
        "bucketByTime": {"durationMillis": 86400000},
        "startTimeMillis": start_of_day_ms,
        "endTimeMillis": now_ms,
    }

    response_data = _make_google_fit_request(
        access_token,
        "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate",
        method="POST",
        body=json.dumps(body),
    )

    if not response_data or "bucket" not in response_data:
        return "N/A"

    total_calories = 0
    for bucket in response_data.get("bucket", []):
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                value = point.get("value", [{}])[0]
                total_calories += value.get("fpVal", 0)

    return f"{int(total_calories)} kcal" if total_calories > 0 else "N/A"


def _make_google_fit_request(access_token, url, method="GET", body=None):
    """Make an authenticated request to the Google Fit API."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    request = urllib.request.Request(
        url,
        data=body.encode("utf-8") if body else None,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except Exception as exc:
        print(f"Google Fit API error: {exc}")
        return None


def start_health_callback_server(host="0.0.0.0", port=None, bot=None):
    """Start a lightweight HTTP callback server for the Google Health login flow."""
    if getattr(start_health_callback_server, "_thread", None) and start_health_callback_server._thread.is_alive():
        return start_health_callback_server._thread

    if port is None:
        port = int(os.getenv("HEALTH_CALLBACK_PORT", "8081"))

    class HealthCallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed_path = urlparse(self.path)
            if parsed_path.path != "/health/callback":
                self.send_response(404)
                self.end_headers()
                return

            response = handle_health_callback(parsed_path.query, bot=bot)
            status_code = 200 if response.get("status") == "ok" else 400
            self.send_response(status_code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(response["message"].encode("utf-8"))

        def log_message(self, format, *args):
            return

    try:
        server = ThreadingHTTPServer((host, port), HealthCallbackHandler)
    except OSError as exc:
        print(f"Health callback server could not start on port {port}: {exc}")
        return None

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    start_health_callback_server._thread = thread
    start_health_callback_server._server = server
    return thread
urce .venv/bin/activate && python -m py_compile messaging.py health.py intents.py reminders.py