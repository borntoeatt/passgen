"""
===============================================================
 ADVANCED PASSWORD GENERATOR BACKEND (Flask)
---------------------------------------------------------------
 Features:
 - Generate 1–100 passwords at once
 - Supports uppercase, numbers, special characters
 - Ensures at least one char from each selected group
 - Per-IP rate limiting
 - Optional API key (premium / trusted clients)
 - Request logging
 - Stats endpoint
===============================================================
"""

from flask import Flask, request, jsonify, render_template
import random
import string
import time
import logging
from collections import deque

app = Flask(__name__)


# ===============================================================
#  RATE LIMITING SETTINGS
# ===============================================================
"""
The rate limit uses a simple in-memory sliding window per IP.

PUBLIC traffic limit:   60 requests per minute
Trusted key traffic:    300 requests per minute

These values keep your API safe from spam or abuse.
"""

RATE_LIMIT_WINDOW = 60          # seconds
PUBLIC_RATE_LIMIT = 60          # per IP per window
TRUSTED_RATE_LIMIT = 300        # higher limit for API key users
API_KEY = "CHANGE_ME_API_KEY"   # optional — set your own key

# Per-IP request timestamps
rate_buckets = {}  # { ip: deque([timestamps]) }


# ===============================================================
#  APPLICATION STATS
# ===============================================================
"""
These stats reset when the server restarts.
For persistent analytics, you'd store them in a DB.
"""

stats = {
    "total_requests": 0,
    "total_passwords_generated": 0,
    "last_request_ts": None,
}


# ===============================================================
#  LOGGING SETUP
# ===============================================================
"""
Logs go to your terminal. In production, you'd send this to:
 - CloudWatch
 - Logstash
 - Papertrail
 - Elasticsearch
etc.
"""

logging.basicConfig(level=logging.INFO)



# ===============================================================
#  RATE LIMIT FUNCTION
# ===============================================================
def check_rate_limit(ip: str, is_trusted: bool):
    """
    Implements a sliding-window rate limit:
    - Clean out timestamps older than the window
    - Reject if too many requests remain inside the window
    - Otherwise allow request and record timestamp
    """
    now = time.time()
    limit = TRUSTED_RATE_LIMIT if is_trusted else PUBLIC_RATE_LIMIT

    if ip not in rate_buckets:
        rate_buckets[ip] = deque()

    bucket = rate_buckets[ip]

    # Remove timestamps older than window
    while bucket and now - bucket[0] > RATE_LIMIT_WINDOW:
        bucket.popleft()

    # Check if allowed
    if len(bucket) >= limit:
        retry_after = int(RATE_LIMIT_WINDOW - (now - bucket[0]))
        return False, retry_after

    # Record this request
    bucket.append(now)
    return True, None



# ===============================================================
#  PASSWORD GENERATION LOGIC
# ===============================================================
def generate_password(length, upper, nums, special):
    """
    Generates a secure random password.
    Ensures at least one character from each selected character group.
    """

    # Base set: lowercase always included
    chars = string.ascii_lowercase

    required_groups = []  # we guarantee at least one from each

    if upper:
        chars += string.ascii_uppercase
        required_groups.append(string.ascii_uppercase)

    if nums:
        chars += string.digits
        required_groups.append(string.digits)

    if special:
        chars += string.punctuation
        required_groups.append(string.punctuation)

    if not chars:
        raise ValueError("No character sets selected")

    # Build password components
    password_chars = []

    # Guarantee at least one character from each required group
    for group in required_groups:
        password_chars.append(random.choice(group))

    # Fill remaining characters
    for _ in range(len(password_chars), length):
        password_chars.append(random.choice(chars))

    # Randomize order
    random.shuffle(password_chars)

    return "".join(password_chars)



# ===============================================================
#  ROUTES
# ===============================================================

@app.route("/")
def home():
    """
    Serves the front-end (index.html).
    Flask automatically looks inside the /templates directory.
    """
    return render_template("index.html")



# ---------------------------------------------------------------
#  /api/generate — MAIN PASSWORD GENERATION ENDPOINT
# ---------------------------------------------------------------
@app.route("/api/generate")
def api_generate():
    client_ip = request.remote_addr or "unknown"

    # Check API key
    provided_key = request.args.get("api_key")
    is_trusted = provided_key == API_KEY

    # Rate limit check
    allowed, retry_after = check_rate_limit(client_ip, is_trusted)
    if not allowed:
        return jsonify({
            "error": "Rate limit exceeded",
            "retry_after": retry_after
        }), 429

    # Get input params
    try:
        length = int(request.args.get("length", 16))
    except ValueError:
        return jsonify({"error": "Invalid length"}), 400

    if not 8 <= length <= 128:
        return jsonify({"error": "Length must be between 8 and 128"}), 400

    try:
        count = int(request.args.get("count", 1))
    except ValueError:
        return jsonify({"error": "Invalid count"}), 400

    if count < 1:
        count = 1
    if count > 100:
        count = 100  # maximum bulk limit

    upper = request.args.get("upper", "true").lower() == "true"
    nums = request.args.get("numbers", "true").lower() == "true"
    special = request.args.get("special", "true").lower() == "true"

    # Generate passwords
    try:
        passwords = [
            generate_password(length, upper, nums, special)
            for _ in range(count)
        ]
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Update stats
    stats["total_requests"] += 1
    stats["total_passwords_generated"] += len(passwords)
    stats["last_request_ts"] = time.time()

    # Log generation request
    app.logger.info(
        "Generated %s password(s) | ip=%s | length=%s | upper=%s | nums=%s | special=%s",
        len(passwords), client_ip, length, upper, nums, special
    )

    return jsonify({"passwords": passwords})



# ---------------------------------------------------------------
#  /api/stats — INTERNAL DIAGNOSTICS ENDPOINT
# ---------------------------------------------------------------
@app.route("/api/stats")
def api_stats():
    """
    Exposes the internal counters:
    - Total requests
    - Total passwords generated
    - Timestamp of last request
    """
    return jsonify(stats)



# ===============================================================
#  FLASK APP ENTRY POINT
# ===============================================================
if __name__ == "__main__":
    """
    debug=True enables:
     - Hot code reloading
     - Debug tracebacks
    """
    app.run(debug=True)
