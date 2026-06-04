import mysql.connector

# --- UPDATE YOUR MYSQL CREDENTIALS HERE ---
DB_USER = "root"
DB_PASS = "" # Change this to your MySQL password 
DB_HOST = "localhost"
DB_NAME = "food_ordering"

def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

def init_db():
    # 1. Connect to MySQL server (without a specific DB) to create it if it's missing
    server_conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS)
    server_cursor = server_conn.cursor()
    server_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    server_conn.close()

    # 2. Connect directly to our database
    conn = get_db_connection()
    cursor = conn.cursor()

    # 3. Create Tables (MySQL syntax)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
      user_id INT AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      email VARCHAR(255) UNIQUE NOT NULL,
      phone VARCHAR(50),
      address TEXT
    );""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurants (
      restaurant_id INT AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      address TEXT,
      phone VARCHAR(50),
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

    # 4. Create Triggers (Drop them first to avoid errors if they already exist)
    cursor.execute("DROP TRIGGER IF EXISTS after_order_insert")
    cursor.execute("""
    CREATE TRIGGER after_order_insert
    AFTER INSERT ON orders
    FOR EACH ROW
    BEGIN
        INSERT INTO payments (order_id, method, status)
        VALUES (NEW.order_id, 'Cash on Delivery', 'Pending');
    END;
    """)

    cursor.execute("DROP TRIGGER IF EXISTS after_payment_update")
    cursor.execute("""
    CREATE TRIGGER after_payment_update
    AFTER UPDATE ON payments
    FOR EACH ROW
    BEGIN
        IF NEW.status = 'Paid' THEN
            UPDATE orders SET status = 'Confirmed' WHERE order_id = NEW.order_id;
        END IF;
    END;
    """)

    # 5. Seed Data (Only if empty)
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        print("Seeding MySQL Database with new UI data...")
        
        cursor.execute("INSERT INTO users (name, email, phone, address) VALUES ('Guest', 'guest@food.com', '555-0199', '123 Main St')")
        
        categories = [("Starters",), ("Main Course",), ("Drinks",)]
        cursor.executemany("INSERT INTO categories (name) VALUES (%s)", categories)
        
        # ADDED MORE RESTAURANTS FOR UI
        restaurants = [
            ("Burger Bistro", "456 Grill Ave", "555-1122"),
            ("Pizza Paradise", "789 Oven Blvd", "555-3344"),
            ("Wok & Roll", "101 Soy St", "555-5566"),
            ("Sushi Station", "202 Ocean Dr", "555-7788"),
            ("Taco Fiesta", "303 Spicy Ln", "555-9900")
        ]
        cursor.executemany("INSERT INTO restaurants (name, address, phone) VALUES (%s, %s, %s)", restaurants)
        
        menu_items = [
            (1, 1, "Garlic Parmesan Fries", 5.99), (1, 2, "Bacon Cheeseburger", 11.49), (1, 3, "Vanilla Shake", 4.50),
            (2, 1, "Mozzarella Sticks", 6.99), (2, 2, "Pepperoni Feast Pizza", 14.99), (2, 3, "Iced Lemon Tea", 2.50),
            (3, 1, "Crispy Spring Rolls", 4.99), (3, 2, "Kung Pao Noodles", 12.99), (3, 3, "Matcha Tea", 3.00),
            (4, 1, "Edamame", 4.50), (4, 2, "Spicy Tuna Roll", 13.50), (4, 3, "Sake (Non-Alc)", 5.00),
            (5, 1, "Nachos Supreme", 7.99), (5, 2, "Birria Tacos (3x)", 12.00), (5, 3, "Horchata", 3.50)
        ]
        cursor.executemany("INSERT INTO menu_items (restaurant_id, category_id, name, price) VALUES (%s, %s, %s, %s)", menu_items)
        
    conn.commit()
    cursor.close()
    conn.close()

def place_order(user_id, cart_items, delivery_address):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        total_amount = sum(item['price'] * item['quantity'] for item in cart_items.values())
        
        cursor.execute("""
            INSERT INTO orders (user_id, total_amount, delivery_address) 
            VALUES (%s, %s, %s)
        """, (user_id, total_amount, delivery_address))
        
        order_id = cursor.lastrowid
        
        for item_id, details in cart_items.items():
            cursor.execute("""
                INSERT INTO order_items (order_id, item_id, quantity, price_at_order)
                VALUES (%s, %s, %s, %s)
            """, (order_id, int(item_id), details['quantity'], details['price']))
            
        conn.commit()
        return order_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()