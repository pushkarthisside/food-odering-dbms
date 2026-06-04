# Food Ordering System - DBMS Project

A Python-based food ordering application with MySQL database integration.

---

## 🚀 Quick Start Guide

### 1. Clone the Repository

```bash
# Clone the project
git clone <your-repo-url>
cd dbms

# (Optional) Create a virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # macOS/Linux
```

### 2. Set Up MySQL Password

Edit `db.py` and update your MySQL credentials:

```python
# --- UPDATE YOUR MYSQL CREDENTIALS HERE ---
DB_USER = "root"
DB_PASS = "your_password_here"  # Change this to your MySQL password
DB_HOST = "localhost"
DB_NAME = "food_ordering"
```

### 3. Install Dependencies

```bash
pip install flask mysql-connector-python
```

### 4. Initialize Database

```bash
python db.py
```

### 5. Run the Application

```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

---

## 📊 Database Schema

The application uses the following tables:

- **users** - Customer information
- **restaurants** - Restaurant details
- **categories** - Food categories (Starters, Main Course, Drinks, etc.)
- **menu_items** - Food items with prices
- **orders** - Customer orders
- **order_items** - Items in each order
- **payments** - Payment information

---

## 💾 Sample SQL Commands

### View All Users
```sql
SELECT * FROM users;
```

### View All Restaurants
```sql
SELECT restaurant_id, name, address, phone, is_active FROM restaurants;
```

### View Menu Items with Restaurant Names
```sql
SELECT 
    m.name AS item_name, 
    r.name AS restaurant, 
    c.name AS category, 
    m.price
FROM menu_items m
JOIN restaurants r ON m.restaurant_id = r.restaurant_id
JOIN categories c ON m.category_id = c.category_id;
```

### View All Orders
```sql
SELECT order_id, user_id, order_time, status, total_amount FROM orders;
```

### View Order Details (What items in each order)
```sql
SELECT 
    o.order_id, 
    u.name AS customer, 
    oi.item_id, 
    m.name AS item_name, 
    oi.quantity, 
    oi.price_at_order
FROM orders o
JOIN users u ON o.user_id = u.user_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN menu_items m ON oi.item_id = m.item_id;
```

### View Payment Status
```sql
SELECT 
    p.payment_id, 
    o.order_id, 
    u.name AS customer, 
    p.method, 
    p.status, 
    o.total_amount
FROM payments p
JOIN orders o ON p.order_id = o.order_id
JOIN users u ON o.user_id = u.user_id;
```

### Count Orders by Restaurant
```sql
SELECT 
    r.name, 
    COUNT(o.order_id) AS total_orders
FROM restaurants r
LEFT JOIN menu_items m ON r.restaurant_id = m.restaurant_id
LEFT JOIN order_items oi ON m.item_id = oi.item_id
LEFT JOIN orders o ON oi.order_id = o.order_id
GROUP BY r.restaurant_id, r.name;
```

### Find Most Popular Items
```sql
SELECT 
    m.name, 
    r.name AS restaurant, 
    COUNT(oi.order_item_id) AS times_ordered,
    SUM(oi.quantity) AS total_quantity
FROM menu_items m
JOIN restaurants r ON m.restaurant_id = r.restaurant_id
LEFT JOIN order_items oi ON m.item_id = oi.item_id
GROUP BY m.item_id
ORDER BY times_ordered DESC;
```

---

## 📝 Project Structure

```
.
├── app.py              # Flask application
├── db.py               # Database setup & initialization
├── templates/          # HTML templates
│   ├── base.html
│   ├── home.html
│   ├── restaurant.html
│   ├── cart.html
│   ├── confirmation.html
│   └── status.html
├── .gitignore          # Ignore database files
└── README.md           # This file
```

---

## ⚙️ Database Initialization

When you run `python db.py`, it automatically:
1. Creates the MySQL database (if it doesn't exist)
2. Creates all necessary tables
3. Sets up database triggers for orders & payments
4. Seeds sample data (restaurants, menu items, users)

---

## 🔧 Troubleshooting

**MySQL Connection Error?**
- Ensure MySQL is running
- Check your credentials in `db.py`
- Verify database name exists

**Port Already in Use?**
- Change the port in `app.py`: `app.run(port=5001)`

**Missing Dependencies?**
- Run: `pip install -r requirements.txt`

---

## 📄 License

This project is for educational purposes.
