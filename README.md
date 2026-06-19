# QuickBite Food Ordering System - DBMS Project

A comprehensive, Python-based multi-restaurant food ordering application utilizing Flask, Jinja2 templating, and a fully normalized MySQL database with built-in transactional triggers.

---

## ✨ Key Features

* **Modern, Responsive UI**: Built with a custom CSS token system (`--surface`, `--accent`) for a clean, immersive experience across all devices.
* **Secure User Authentication**: Complete login and signup workflows with SHA-256 password hashing and secure session management.
* **Atomic Cart System**: Enforces single-restaurant ordering logic with real-time total calculations.
* **Simulated Payment Engine**: Features an interactive payment terminal (Card, UPI, Cash on Delivery) that seamlessly triggers backend state updates.
* **Live Order Tracking**: Dynamic status page (`status.html`) with CSS keyframe pulse animations to track orders from "Placed" to "Delivered".
* **Database Triggers**: Uses robust MySQL triggers (`after_order_insert`, `after_payment_update`) to instantly synchronize payment logs with parent order states.

---

## 🚀 Quick Start Guide

### 1. Clone the Repository

```bash
# Clone the project
git clone <https://github.com/pushkarthisside/food-odering-dbms/>
cd food-odering-dbms

# (Optional) Create a virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # macOS/Linux
```

### 2. Set Up Environment Variables (Security Update)

Do **not** hardcode your passwords! We use a `.env` file to keep credentials secure.

1. Create a file named `.env` in the root folder.
2. Add your MySQL credentials and a Flask secret key:

```text
DB_USER=root
DB_PASS=your_mysql_password_here
DB_HOST=localhost
DB_NAME=food_ordering
FLASK_SECRET_KEY=super_secret_dev_key
```

### 3. Install Dependencies

```bash
pip install flask mysql-connector-python python-dotenv
```

### 4. Initialize Database

```bash
python db.py
```

*This automatically generates the schema, sets up triggers, and seeds the initial restaurants, menu items, and demo users.*

### 5. Run the Application

```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

*(Demo Account: `demo@food.com` / `demo123`)*

---

## 📊 Database Schema & Triggers

The application uses the following 3NF-normalized tables:

* **users** - Cryptographic profiles and contact routing
* **restaurants** - Active vendor kitchens
* **categories** - Menu classification tags
* **menu_items** - Independent inventory pricing items
* **orders** - Parent transaction ledger
* **order_items** - Individual line items (locks historical price at checkout)
* **payments** - Financial tracking logs

**Active MySQL Triggers:**

* `after_order_insert`: Auto-generates a pending payment log when an order is created.
* `after_payment_update`: Auto-promotes the parent order status to "Confirmed" once a payment is marked as "Paid".

---

## 💾 Live Demo SQL Commands

Use these commands in your MySQL terminal during presentations to prove real-time database state changes.

### The "All-in-One" Verification Query (JOIN)

*Run this before and after making a payment to show the database triggers working instantly.*

```sql
SELECT 
    o.order_id, 
    o.status AS order_status, 
    p.method AS payment_method, 
    p.status AS payment_status,
    o.total_amount
FROM orders o
JOIN payments p ON o.order_id = p.order_id
ORDER BY o.order_time DESC;
```

### Check Specific Order Breakdown

```sql
SELECT 
    oi.order_id, 
    m.name AS item_name, 
    oi.quantity, 
    oi.price_at_order,
    (oi.quantity * oi.price_at_order) AS subtotal
FROM order_items oi
JOIN menu_items m ON oi.item_id = m.item_id
WHERE oi.order_id = 1;
```

### Total Revenue Earned (Business Analytics)

```sql
SELECT SUM(total_amount) AS total_revenue 
FROM orders 
WHERE status = 'Confirmed' OR status = 'Delivered';
```

### ⏩ Simulate Order Completion

*Run this to manually force an order to "Delivered" and watch the frontend tracking UI update.*

```sql
UPDATE orders SET status = 'Delivered' WHERE order_id = 1;
```

---

## 📝 Project Structure

```text
.
├── app.py              # Flask application & routing logic
├── db.py               # Database setup, trigger init, & core SQL functions
├── templates/          # Jinja2 HTML templates
│   ├── base.html       # Master layout & responsive navbar
│   ├── home.html       # Restaurant catalog dashboard
│   ├── login.html      # Secure user authentication
│   ├── signup.html     # New user registration
│   ├── restaurant.html # Categorized menus & add-to-cart actions
│   ├── cart.html       # Persistent session cart & totals
│   ├── checkout.html   # Shipping logistics
│   ├── payment.html    # Interactive simulated payment terminal
│   ├── confirmation.html # Post-order success screen
│   ├── my_orders.html  # Historical transaction archive
│   └── status.html     # Live order tracking with CSS animations
├── .env.example        # Template for environment variables
├── .gitignore          # Ignores sensitive keys (.env) and caches
└── README.md           # This file
```

---

## 🔧 Troubleshooting

**MySQL Connection Error?**

* Ensure your MySQL server service is actively running.
* Check that your `.env` file variables exactly match your local MySQL credentials.

**ModuleNotFoundError: No module named 'dotenv'?**

* Ensure you activated your virtual environment and ran `pip install python-dotenv`.

**Changes Not Saving to GitHub?**

* If your terminal warns about LF/CRLF line endings, it is normal cross-platform conversion behavior.

---

## 📄 License

This project was developed for educational and demonstration purposes as part of a Database Management Systems (DBMS) curriculum.
