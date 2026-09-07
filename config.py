import os
import secrets
from pathlib import Path


# =========================================================
# BASE DIRECTORY
# =========================================================

BASE_DIR = Path(__file__).resolve().parent


# =========================================================
# SECRET KEY
# =========================================================
#
# IMPORTANT:
# On Render, ALWAYS create a SECRET_KEY environment variable.
#
# If SECRET_KEY exists, it will remain stable across
# deployments/restarts and users will stay logged in.
#
# The local .secret_key file is only a fallback for local
# development.
# =========================================================

SECRET_FILE = BASE_DIR / ".secret_key"


if os.environ.get("SECRET_KEY"):
    _SECRET_KEY = os.environ["SECRET_KEY"].strip()

else:

    if not SECRET_FILE.exists():

        SECRET_FILE.write_text(
            secrets.token_hex(32),
            encoding="utf-8"
        )

    _SECRET_KEY = SECRET_FILE.read_text(
        encoding="utf-8"
    ).strip()


# =========================================================
# CATEGORIES
# =========================================================
#
# You can change the default category names here.
#
# Example:
#
# STORE_CATEGORIES=Shoes,Clothes,Bags,Phones,Beauty,Electronics,Other
#
# On Render, STORE_CATEGORIES can be added as an
# Environment Variable so the owner can change categories
# without editing app.py.
# =========================================================

DEFAULT_CATEGORIES = [
    "Phone Accessories",
    "Watches",
    "Bags",
    "Jewelry",
    "Audio",
    "Electronics",
    "Lifestyle",
    "Other"
]


def get_categories_from_environment():

    raw = os.environ.get(
        "STORE_CATEGORIES",
        ""
    ).strip()

    if not raw:
        return DEFAULT_CATEGORIES.copy()

    categories = []

    for value in raw.split(","):

        category = value.strip()

        if not category:
            continue

        if len(category) > 80:
            category = category[:80].strip()

        if category not in categories:
            categories.append(category)

    if not categories:
        return DEFAULT_CATEGORIES.copy()

    return categories


# =========================================================
# CONFIG
# =========================================================

class Config:

    SECRET_KEY = _SECRET_KEY

    DATABASE = str(
        BASE_DIR / "bib_store.db"
    )

    UPLOAD_FOLDER = str(
        BASE_DIR / "uploads"
    )

    MAX_CONTENT_LENGTH = (
        5 * 1024 * 1024
    )

    ALLOWED_EXTENSIONS = {
        "jpg",
        "jpeg",
        "png",
        "webp"
    }

    # -----------------------------------------------------
    # SESSION
    # -----------------------------------------------------

    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = "Lax"

    # Render uses HTTPS.
    #
    # Local development can remain HTTP.
    #
    # You can explicitly override this with:
    #
    # SESSION_COOKIE_SECURE=1
    #
    # or
    #
    # SESSION_COOKIE_SECURE=0
    # -----------------------------------------------------

    SESSION_COOKIE_SECURE = (
        os.environ.get(
            "SESSION_COOKIE_SECURE",
            "1" if os.environ.get("RENDER") else "0"
        ) == "1"
    )

    SESSION_COOKIE_PATH = "/"

    # Keep customer/admin logged in for 30 days.
    PERMANENT_SESSION_LIFETIME = (
        60 * 60 * 24 * 30
    )

    SESSION_REFRESH_EACH_REQUEST = True

    # -----------------------------------------------------
    # STORE
    # -----------------------------------------------------

    STORE_CURRENCY = "₦"

    CATEGORIES = get_categories_from_environment()
