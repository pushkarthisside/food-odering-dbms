import hashlib
import os
import mysql.connector
from dotenv import load_dotenv

# Load variables from .env file into os.environ
load_dotenv()

# Access them safely using os.getenv()
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS")  # Pulls directly from your hidden .env
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "food_ordering")

def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )


def hash_password(password):
    """Simple SHA-256 hash for MVP. Not for production use."""
    return hashlib.sha256(password.encode()).hexdigest()


def column_exists(cursor, table_name, column_name):
    cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s", (column_name,))
    return cursor.fetchone() is not None


def ensure_column(cursor, table_name, column_name, definition):
    if not column_exists(cursor, table_name, column_name):
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def ensure_user(cursor, name, email, phone, address, password):
    password_hash = hash_password(password)
    cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
    existing = cursor.fetchone()
    if existing:
        cursor.execute(
            """
            UPDATE users
            SET name = %s, phone = %s, address = %s, password_hash = %s
            WHERE email = %s
            """,
            (name, phone, address, password_hash, email),
        )
        return existing[0]

    cursor.execute(
        """
        INSERT INTO users (name, email, phone, address, password_hash)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (name, email, phone, address, password_hash),
    )
    return cursor.lastrowid


def recreate_trigger(cursor, trigger_name, trigger_sql):
    cursor.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")
    try:
        cursor.execute(trigger_sql)
    except mysql.connector.Error as exc:
        if getattr(exc, "errno", None) != 1359:
            raise


def init_db():
    # 1. Connect to MySQL server (without a specific DB) to create it if missing
    server_conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS)
    server_cursor = server_conn.cursor()
    server_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    server_conn.close()

    # 2. Connect directly to our database
    conn = get_db_connection()
    cursor = conn.cursor()

    # 3. Create Tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
      user_id INT AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      email VARCHAR(255) UNIQUE NOT NULL,
      phone VARCHAR(50),
      address TEXT,
      password_hash VARCHAR(64) NOT NULL DEFAULT ''
    );""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurants (
      restaurant_id INT AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      address TEXT,
      phone VARCHAR(50),
      cuisine VARCHAR(100),
      rating DECIMAL(2,1) DEFAULT 4.0,
      delivery_time VARCHAR(30) DEFAULT '30-40 min',
      is_active BOOLEAN DEFAULT 1
    );""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
      category_id INT AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(100) NOT NULL
    );""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS menu_items (
      item_id INT AUTO_INCREMENT PRIMARY KEY,
      restaurant_id INT,
      category_id INT,
      name VARCHAR(255) NOT NULL,
      description VARCHAR(255) DEFAULT '',
      price DECIMAL(10,2) NOT NULL,
      is_available BOOLEAN DEFAULT 1,
      FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id),
      FOREIGN KEY (category_id) REFERENCES categories(category_id)
    );""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
      order_id INT AUTO_INCREMENT PRIMARY KEY,
      user_id INT,
      order_time DATETIME DEFAULT CURRENT_TIMESTAMP,
      status VARCHAR(50) DEFAULT 'Pending',
      total_amount DECIMAL(10,2),
      delivery_address TEXT,
      FOREIGN KEY (user_id) REFERENCES users(user_id)
    );""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
      order_item_id INT AUTO_INCREMENT PRIMARY KEY,
      order_id INT,
      item_id INT,
      quantity INT,
      price_at_order DECIMAL(10,2),
      FOREIGN KEY (order_id) REFERENCES orders(order_id),
      FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
    );""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
      payment_id INT AUTO_INCREMENT PRIMARY KEY,
      order_id INT UNIQUE,
      method VARCHAR(50) DEFAULT 'Cash on Delivery',
      status VARCHAR(50) DEFAULT 'Pending',
      paid_at DATETIME,
      FOREIGN KEY (order_id) REFERENCES orders(order_id)
    );""")

    # 4. Safe schema migrations for older databases
    ensure_column(cursor, "users", "password_hash", "VARCHAR(64) NOT NULL DEFAULT ''")

    # 5. Triggers
    recreate_trigger(cursor, "after_order_insert", """
    CREATE TRIGGER after_order_insert
    AFTER INSERT ON orders
    FOR EACH ROW
    BEGIN
        INSERT INTO payments (order_id, method, status)
        VALUES (NEW.order_id, 'Cash on Delivery', 'Pending');
    END;
    """)

    recreate_trigger(cursor, "after_payment_update", """
    CREATE TRIGGER after_payment_update
    AFTER UPDATE ON payments
    FOR EACH ROW
    BEGIN
        IF NEW.status = 'Paid' THEN
            UPDATE orders SET status = 'Confirmed' WHERE order_id = NEW.order_id;
        END IF;
    END;
    """)

    # 6. Seed users and catalog data
    ensure_user(cursor, "Guest", "guest@food.com", "555-0199", "123 Main St", "guest123")
    ensure_user(cursor, "Demo User", "demo@food.com", "555-0100", "456 Demo Lane", "demo123")

    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        categories = [("Starters",), ("Main Course",), ("Drinks",)]
        cursor.executemany("INSERT INTO categories (name) VALUES (%s)", categories)

    cursor.execute("SELECT COUNT(*) FROM restaurants")
    if cursor.fetchone()[0] == 0:
        restaurants = [
            ("Burger Bistro",   "456 Grill Ave",   "555-1122", "American",  4.3, "20-30 min"),
            ("Pizza Paradise",  "789 Oven Blvd",   "555-3344", "Italian",   4.5, "25-35 min"),
            ("Wok & Roll",      "101 Soy St",       "555-5566", "Chinese",   4.1, "30-40 min"),
            ("Sushi Station",   "202 Ocean Dr",     "555-7788", "Japanese",  4.7, "35-45 min"),
            ("Taco Fiesta",     "303 Spicy Ln",     "555-9900", "Mexican",   4.2, "20-30 min"),
        ]
        cursor.executemany(
            "INSERT INTO restaurants (name, address, phone, cuisine, rating, delivery_time) VALUES (%s, %s, %s, %s, %s, %s)",
            restaurants
        )

    cursor.execute("SELECT COUNT(*) FROM menu_items")
    if cursor.fetchone()[0] == 0:
        menu_items = [
            (1, 1, "Garlic Parmesan Fries",    "Crispy fries tossed in garlic butter",          5.99),
            (1, 2, "Bacon Cheeseburger",        "Double patty, cheddar, crispy bacon",           11.49),
            (1, 3, "Vanilla Shake",             "Thick creamy vanilla milkshake",                4.50),
            (2, 1, "Mozzarella Sticks",         "Golden fried, served with marinara",            6.99),
            (2, 2, "Pepperoni Feast Pizza",     "Loaded with pepperoni & mozzarella",            14.99),
            (2, 3, "Iced Lemon Tea",            "Freshly brewed, lightly sweetened",             2.50),
            (3, 1, "Crispy Spring Rolls",       "Vegetable filled, served with sweet chili",     4.99),
            (3, 2, "Kung Pao Noodles",          "Spicy wok-tossed noodles with peanuts",         12.99),
            (3, 3, "Matcha Tea",                "Traditional Japanese green tea",                3.00),
            (4, 1, "Edamame",                   "Steamed salted soybeans",                       4.50),
            (4, 2, "Spicy Tuna Roll",           "Fresh tuna, sriracha mayo, cucumber",           13.50),
            (4, 3, "Sake (Non-Alc)",            "Sparkling rice-based beverage",                 5.00),
            (5, 1, "Nachos Supreme",            "Loaded with cheese, jalapeños & salsa",         7.99),
            (5, 2, "Birria Tacos (3x)",         "Slow-cooked beef, consomé for dipping",         12.00),
            (5, 3, "Horchata",                  "Sweet cinnamon rice drink",                     3.50),
        ]
        cursor.executemany(
            "INSERT INTO menu_items (restaurant_id, category_id, name, description, price) VALUES (%s, %s, %s, %s, %s)",
            menu_items
        )

    conn.commit()
    cursor.close()
    conn.close()


# ---------- Auth ----------

def create_user(name, email, phone, address, password):
    """Returns user_id on success, None if email already exists."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email, phone, address, password_hash) VALUES (%s, %s, %s, %s, %s)",
            (name, email, phone, address, hash_password(password))
        )
        conn.commit()
        return cursor.lastrowid
    except mysql.connector.errors.IntegrityError:
        return None  # duplicate email
    finally:
        cursor.close()
        conn.close()


def verify_login(email, password):
    """Returns user dict on success, None on failure."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM users WHERE email = %s AND password_hash = %s",
        (email, hash_password(password))
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


# ---------- Orders ----------

def place_order(user_id, cart_items, delivery_address):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        total_amount = sum(item['price'] * item['quantity'] for item in cart_items.values())

        cursor.execute(
            "INSERT INTO orders (user_id, total_amount, delivery_address) VALUES (%s, %s, %s)",
            (user_id, total_amount, delivery_address)
        )
        order_id = cursor.lastrowid

        for item_id, details in cart_items.items():
            cursor.execute(
                "INSERT INTO order_items (order_id, item_id, quantity, price_at_order) VALUES (%s, %s, %s, %s)",
                (order_id, int(item_id), details['quantity'], details['price'])
            )

        conn.commit()
        return order_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()


def mark_payment_paid(order_id, method):
    """Mark a payment as paid — trigger will update order to Confirmed."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        from datetime import datetime
        cursor.execute(
            "UPDATE payments SET status = 'Paid', method = %s, paid_at = %s WHERE order_id = %s",
            (method, datetime.now(), order_id)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def finalize_payment(order_id, method):
    """Finalize checkout with method-specific payment behavior."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT payment_id, status FROM payments WHERE order_id = %s", (order_id,))
        payment = cursor.fetchone()
        if not payment:
            raise ValueError("Payment record not found for this order.")

        if payment["status"] == "Paid":
            return "Paid"

        if method == "Cash on Delivery":
            cursor.execute(
                "UPDATE payments SET method = %s, status = 'Pending', paid_at = NULL WHERE order_id = %s",
                (method, order_id),
            )
            cursor.execute(
                "UPDATE orders SET status = 'Confirmed' WHERE order_id = %s",
                (order_id,),
            )
            conn.commit()
            return "Pending"

        from datetime import datetime

        cursor.execute(
            "UPDATE payments SET status = 'Paid', method = %s, paid_at = %s WHERE order_id = %s",
            (method, datetime.now(), order_id)
        )
        conn.commit()
        return "Paid"
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def get_order(order_id, user_id=None):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if user_id is None:
            cursor.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
        else:
            cursor.execute(
                "SELECT * FROM orders WHERE order_id = %s AND user_id = %s",
                (order_id, user_id),
            )
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()


def get_user_orders(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM orders WHERE user_id = %s ORDER BY order_time DESC",
        (user_id,)
    )
    orders = cursor.fetchall()
    cursor.close()
    conn.close()
    return orders
