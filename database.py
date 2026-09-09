import os

import psycopg2
from psycopg2.extras import RealDictCursor


# ============================================================
# DEFAULT STORE SETTINGS
# ============================================================

DEFAULT_SETTINGS = {
    "store_name": "BIB-STORE",
    "store_email": "",
    "phone": "",
    "whatsapp": "",
    "address": "",
    "logo": "",
    "currency": "₦",
    "description": "A modern online store for accessories, electronics and lifestyle products.",
    "primary_color": "#6d4aff",
    "announcement_text": "Fast & secure shopping • Easy ordering",
    "show_announcement": "1",
    "show_whatsapp": "1",
    "whatsapp_message": "Hello {{store_name}}, I need help with my order #{{order_id}}.",
    "footer_text": "Quality products, great prices and dependable customer service.",
    "nav_home": "1",
    "nav_shop": "1",
    "nav_categories": "1",
    "nav_about": "1",
    "nav_contact": "1",
}


# ============================================================
# DEFAULT CATEGORIES
# ============================================================

DEFAULT_CATEGORIES = [
    "Phone Accessories",
    "Watches",
    "Bags",
    "Jewelry",
    "Audio",
    "Electronics",
    "Lifestyle",
    "Other",
]


# ============================================================
# DATABASE SCHEMA
# ============================================================

TABLES = [

    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price DOUBLE PRECISION NOT NULL CHECK (price >= 0),
        stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
        description TEXT NOT NULL DEFAULT '',
        image TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        customer_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        address TEXT NOT NULL,
        note TEXT NOT NULL DEFAULT '',
        total DOUBLE PRECISION NOT NULL CHECK (total >= 0),
        status TEXT NOT NULL DEFAULT 'Pending',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

        CONSTRAINT fk_orders_user
            FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE RESTRICT
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS order_items (
        id SERIAL PRIMARY KEY,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        price DOUBLE PRECISION NOT NULL CHECK (price >= 0),
        quantity INTEGER NOT NULL CHECK (quantity > 0),

        CONSTRAINT fk_order_items_order
            FOREIGN KEY (order_id)
            REFERENCES orders(id)
            ON DELETE CASCADE,

        CONSTRAINT fk_order_items_product
            FOREIGN KEY (product_id)
            REFERENCES products(id)
            ON DELETE RESTRICT
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL DEFAULT ''
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS categories (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE UNIQUE INDEX IF NOT EXISTS categories_name_lower_unique
    ON categories (LOWER(TRIM(name)))
    """,
]


# ============================================================
# DATABASE URL
# ============================================================

def get_database_url():
    database_url = os.environ.get("DATABASE_URL", "").strip()

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing. "
            "Add your Supabase PostgreSQL connection string "
            "to Render Environment Variables."
        )

    return database_url


# ============================================================
# CONNECTION COMPATIBILITY LAYER
# ============================================================

class CompatConnection:
    """
    Allows app.py to continue using SQLite-style '?' placeholders
    while the actual database is PostgreSQL.
    """

    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, params=()):
        query = query.replace("?", "%s")

        cursor = self.connection.cursor(
            cursor_factory=RealDictCursor
        )

        cursor.execute(query, params)

        return CompatCursor(cursor, self.connection)

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            self.connection.rollback()
        else:
            self.connection.commit()

        self.connection.close()


class CompatCursor:

    def __init__(self, cursor, connection):
        self.cursor = cursor
        self.connection = connection

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    @property
    def rowcount(self):
        return self.cursor.rowcount

    @property
    def lastrowid(self):
        return None


# ============================================================
# GET CONNECTION
# ============================================================

def get_connection():

    connection = psycopg2.connect(
        get_database_url(),
        sslmode="require",
    )

    return CompatConnection(connection)


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():

    database_url = get_database_url()

    connection = None

    try:

        connection = psycopg2.connect(
            database_url,
            sslmode="require",
        )

        cursor = connection.cursor(
            cursor_factory=RealDictCursor
        )

        # ----------------------------------------------------
        # CREATE TABLES ONE BY ONE
        # ----------------------------------------------------

        for table_sql in TABLES:
            cursor.execute(table_sql)

        # ----------------------------------------------------
        # IMPORT CATEGORIES FROM EXISTING PRODUCTS
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO categories (name)
            SELECT DISTINCT TRIM(category)
            FROM products
            WHERE category IS NOT NULL
              AND TRIM(category) <> ''
            ON CONFLICT DO NOTHING
            """
        )

        # ----------------------------------------------------
        # INSERT DEFAULT CATEGORIES
        # ----------------------------------------------------

        for category in DEFAULT_CATEGORIES:

            category = str(category).strip()

            if not category:
                continue

            cursor.execute(
                """
                INSERT INTO categories (name)
                VALUES (%s)
                ON CONFLICT DO NOTHING
                """,
                (category,),
            )

        # ----------------------------------------------------
        # INSERT DEFAULT SETTINGS
        # ----------------------------------------------------

        for key, value in DEFAULT_SETTINGS.items():

            cursor.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO NOTHING
                """,
                (key, value),
            )

        # ----------------------------------------------------
        # FIX OLD ANNOUNCEMENT
        # ----------------------------------------------------

        cursor.execute(
            """
            UPDATE settings
            SET value = %s
            WHERE key = 'announcement_text'
              AND value LIKE 'Free delivery on orders over ₦50,000%%'
            """,
            (
                DEFAULT_SETTINGS["announcement_text"],
            ),
        )

        # ----------------------------------------------------
        # KEEP ONLY ONE ADMIN ACCOUNT
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE is_admin = 1
            ORDER BY id ASC
            """
        )

        admins = cursor.fetchall()

        if len(admins) > 1:

            keep_id = admins[0]["id"]

            cursor.execute(
                """
                UPDATE users
                SET is_admin = 0
                WHERE is_admin = 1
                  AND id != %s
                """,
                (keep_id,),
            )

        # ----------------------------------------------------
        # COMMIT EVERYTHING
        # ----------------------------------------------------

        connection.commit()

        print("========================================")
        print("BIB-STORE DATABASE INITIALIZED")
        print("========================================")
        print("Tables checked/created successfully.")
        print("Categories checked/created successfully.")
        print("Settings checked/created successfully.")
        print("========================================")

    except Exception as error:

        if connection:
            connection.rollback()

        print("========================================")
        print("DATABASE INITIALIZATION FAILED")
        print("========================================")
        print(type(error).__name__)
        print(str(error))
        print("========================================")

        raise

    finally:

        if connection:
            connection.close()


# ============================================================
# FETCH ONE
# ============================================================

def fetch_one(query, params=()):

    query = query.replace("?", "%s")

    connection = psycopg2.connect(
        get_database_url(),
        sslmode="require",
        cursor_factory=RealDictCursor,
    )

    try:

        cursor = connection.cursor()

        cursor.execute(
            query,
            params
        )

        return cursor.fetchone()

    finally:

        connection.close()


# ============================================================
# FETCH ALL
# ============================================================

def fetch_all(query, params=()):

    query = query.replace("?", "%s")

    connection = psycopg2.connect(
        get_database_url(),
        sslmode="require",
        cursor_factory=RealDictCursor,
    )

    try:

        cursor = connection.cursor()

        cursor.execute(
            query,
            params
        )

        return cursor.fetchall()

    finally:

        connection.close()


# ============================================================
# GET SETTINGS
# ============================================================

def get_settings():

    rows = fetch_all(
        "SELECT key, value FROM settings"
    )

    settings = DEFAULT_SETTINGS.copy()

    settings.update(
        {
            row["key"]: row["value"]
            for row in rows
        }
    )

    return settings


# ============================================================
# UPDATE SETTINGS
# ============================================================

def update_settings(values):

    connection = psycopg2.connect(
        get_database_url(),
        sslmode="require",
    )

    try:

        cursor = connection.cursor()

        for key, value in values.items():

            cursor.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (%s, %s)

                ON CONFLICT (key)
                DO UPDATE SET value = EXCLUDED.value
                """,
                (
                    key,
                    value,
                ),
            )

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()
