import os

import psycopg2
from psycopg2.extras import RealDictCursor

from config import Config


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price DOUBLE PRECISION NOT NULL CHECK(price >= 0),
    stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
    description TEXT NOT NULL DEFAULT '',
    image TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    customer_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    total DOUBLE PRECISION NOT NULL CHECK(total >= 0),
    status TEXT NOT NULL DEFAULT 'Pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    price DOUBLE PRECISION NOT NULL CHECK(price >= 0),
    quantity INTEGER NOT NULL CHECK(quantity > 0),

    FOREIGN KEY(order_id)
        REFERENCES orders(id)
        ON DELETE CASCADE,

    FOREIGN KEY(product_id)
        REFERENCES products(id)
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);
"""


DEFAULT_SETTINGS = {
    "store_name": "BIB-STORE",
    "store_email": "",
    "phone": "",
    "whatsapp": "",
    "address": "",
    "logo": "",
    "currency": "₦",

    "description":
        "A modern online store for accessories, electronics and lifestyle products.",

    "primary_color": "#6d4aff",

    "announcement_text":
        "Fast & secure shopping • Easy ordering",

    "show_announcement": "1",

    "show_whatsapp": "1",

    "whatsapp_message":
        "Hello {{store_name}}, I need help with my order #{{order_id}}.",

    "footer_text":
        "Quality products, great prices and dependable customer service.",

    "nav_home": "1",
    "nav_shop": "1",
    "nav_categories": "1",
    "nav_about": "1",
    "nav_contact": "1",
}


def get_database_url():
    database_url = os.environ.get("DATABASE_URL", "").strip()

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Add your Supabase PostgreSQL connection string "
            "to Render Environment Variables."
        )

    return database_url


def get_connection():
    return psycopg2.connect(
        get_database_url(),
        cursor_factory=RealDictCursor,
        sslmode="require",
    )


def init_db():

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(SCHEMA)

            for key, value in DEFAULT_SETTINGS.items():

                cur.execute(
                    """
                    INSERT INTO settings(key, value)
                    VALUES (%s, %s)
                    ON CONFLICT (key) DO NOTHING
                    """,
                    (key, value)
                )

            cur.execute(
                """
                UPDATE settings
                SET value = %s
                WHERE key = 'announcement_text'
                AND value LIKE 'Free delivery on orders over ₦50,000%%'
                """,
                (
                    DEFAULT_SETTINGS["announcement_text"],
                )
            )

            cur.execute(
                """
                SELECT id
                FROM users
                WHERE is_admin = 1
                ORDER BY id ASC
                """
            )

            admins = cur.fetchall()

            if len(admins) > 1:

                keep_id = admins[0]["id"]

                cur.execute(
                    """
                    UPDATE users
                    SET is_admin = 0
                    WHERE is_admin = 1
                    AND id != %s
                    """,
                    (keep_id,)
                )

        conn.commit()


def fetch_one(query, params=()):

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(query, params)

            return cur.fetchone()


def fetch_all(query, params=()):

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(query, params)

            return cur.fetchall()


def get_settings():

    rows = fetch_all(
        "SELECT key, value FROM settings"
    )

    data = DEFAULT_SETTINGS.copy()

    data.update(
        {
            row["key"]: row["value"]
            for row in rows
        }
    )

    return data


def update_settings(values):

    with get_connection() as conn:

        with conn.cursor() as cur:

            for key, value in values.items():

                cur.execute(
                    """
                    INSERT INTO settings(key, value)
                    VALUES (%s, %s)

                    ON CONFLICT (key)
                    DO UPDATE SET value = EXCLUDED.value
                    """,
                    (key, value)
                )

        conn.commit()
