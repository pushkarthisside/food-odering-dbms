from flask import Flask, render_template, request, redirect, url_for, session, flash
import db

app = Flask(__name__)
app.secret_key = "foodapp_mvp_2026"

db.init_db()


# ── helpers ──────────────────────────────────────────────────────────────────

def login_required(f):
    """Simple decorator – redirect to login if not logged in."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "info")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        try:
            user = db.verify_login(email, password)
        except Exception:
            flash("Login is temporarily unavailable. Please try again.", "error")
            return render_template("login.html"), 503
        if user:
            session["user_id"]   = user["user_id"]
            session["user_name"] = user["name"]
            session["user_email"]= user["email"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("home"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("home"))
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip()
        phone    = request.form.get("phone", "").strip()
        address  = request.form.get("address", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not all([name, email, password]):
            flash("Name, email and password are required.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        else:
            try:
                user_id = db.create_user(name, email, phone, address, password)
            except Exception:
                flash("Signup is temporarily unavailable. Please try again.", "error")
                return render_template("signup.html"), 503
            if user_id:
                session["user_id"]    = user_id
                session["user_name"]  = name
                session["user_email"] = email
                flash(f"Account created! Welcome, {name}.", "success")
                return redirect(url_for("home"))
            flash("An account with that email already exists.", "error")
    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out.", "info")
    return redirect(url_for("login"))


# ── Browse ────────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def home():
    conn   = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM restaurants WHERE is_active = 1")
    restaurants = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("home.html", restaurants=restaurants)


@app.route("/restaurant/<int:restaurant_id>")
@login_required
def restaurant(restaurant_id):
    conn   = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
    resto = cursor.fetchone()
    if not resto:
        cursor.close()
        conn.close()
        flash("Restaurant not found.", "error")
        return redirect(url_for("home"))

    cursor.execute("""
        SELECT m.*, c.name AS category_name
        FROM menu_items m
        JOIN categories c ON m.category_id = c.category_id
        WHERE m.restaurant_id = %s AND m.is_available = 1
        ORDER BY c.category_id, m.name
    """, (restaurant_id,))
    menu_items = cursor.fetchall()

    cursor.close()
    conn.close()

    # Group by category
    from collections import defaultdict
    grouped = defaultdict(list)
    for item in menu_items:
        grouped[item["category_name"]].append(item)

    return render_template("restaurant.html", restaurant=resto, grouped_menu=grouped)


# ── Cart ──────────────────────────────────────────────────────────────────────

@app.route("/cart/add", methods=["POST"])
@login_required
def add_to_cart():
    item_id         = request.form.get("item_id")
    name            = request.form.get("name")
    raw_price       = request.form.get("price")
    restaurant_name = request.form.get("restaurant_name")
    restaurant_id   = request.form.get("restaurant_id")

    if not all([item_id, name, raw_price, restaurant_name, restaurant_id]):
        flash("Unable to add that item to cart.", "error")
        return redirect(request.referrer or url_for("home"))

    try:
        price = float(raw_price)
    except (TypeError, ValueError):
        flash("Unable to add that item to cart.", "error")
        return redirect(request.referrer or url_for("home"))

    if "cart" not in session:
        session["cart"] = {}

    cart = session["cart"]

    # Enforce single-restaurant cart
    if cart:
        existing_resto = next(iter(cart.values()))["restaurant_id"]
        if str(existing_resto) != str(restaurant_id):
            session["cart"] = {}
            cart = session["cart"]
            flash("Cart cleared — you can only order from one restaurant at a time.", "info")

    if item_id in cart:
        cart[item_id]["quantity"] += 1
    else:
        cart[item_id] = {
            "name": name,
            "price": price,
            "quantity": 1,
            "restaurant": restaurant_name,
            "restaurant_id": restaurant_id,
        }

    session["cart"] = cart
    return redirect(request.referrer or url_for("home"))


@app.route("/cart/remove/<item_id>")
@login_required
def remove_from_cart(item_id):
    cart = session.get("cart", {})
    cart.pop(item_id, None)
    session["cart"] = cart
    return redirect(url_for("view_cart"))


@app.route("/cart/update", methods=["POST"])
@login_required
def update_cart():
    item_id  = request.form.get("item_id")
    action   = request.form.get("action")
    cart     = session.get("cart", {})
    if item_id in cart:
        if action == "inc":
            cart[item_id]["quantity"] += 1
        elif action == "dec":
            cart[item_id]["quantity"] -= 1
            if cart[item_id]["quantity"] <= 0:
                del cart[item_id]
    session["cart"] = cart
    return redirect(url_for("view_cart"))


@app.route("/cart")
@login_required
def view_cart():
    cart  = session.get("cart", {})
    total = sum(item["price"] * item["quantity"] for item in cart.values())
    return render_template("cart.html", cart=cart, total=total)


# ── Checkout / Payment ────────────────────────────────────────────────────────

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart = session.get("cart", {})
    if not cart:
        return redirect(url_for("home"))
    total = sum(item["price"] * item["quantity"] for item in cart.values())

    # Pre-fill address from user profile
    conn   = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (session["user_id"],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template("checkout.html", cart=cart, total=total, user=user)


@app.route("/order/place", methods=["POST"])
@login_required
def order_place():
    cart = session.get("cart", {})
    if not cart:
        return redirect(url_for("home"))

    address = request.form.get("address", "").strip() or "Takeaway"

    try:
        order_id = db.place_order(session["user_id"], cart, address)
        session.pop("cart", None)
        # Redirect to fake payment page
        return redirect(url_for("payment", order_id=order_id))
    except Exception as e:
        flash(f"Something went wrong: {e}", "error")
        return redirect(url_for("view_cart"))


@app.route("/payment/<int:order_id>", methods=["GET", "POST"])
@login_required
def payment(order_id):
    order = db.get_order(order_id, session["user_id"])
    if not order:
        return "Order not found", 404

    conn   = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM payments WHERE order_id = %s", (order_id,))
    pay   = cursor.fetchone()
    cursor.close()
    conn.close()

    if pay and pay["status"] == "Paid":
        return redirect(url_for("order_confirmation", order_id=order_id))

    if request.method == "POST":
        method = request.form.get("method", "Card")
        payment_status = db.finalize_payment(order_id, method)
        if payment_status == "Paid":
            flash("Payment successful!", "success")
        else:
            flash("Order placed. Pay on delivery.", "success")
        return redirect(url_for("order_confirmation", order_id=order_id))

    return render_template("payment.html", order=order, payment=pay)


# ── Post-order ────────────────────────────────────────────────────────────────

@app.route("/order/confirm/<int:order_id>")
@login_required
def order_confirmation(order_id):
    order = db.get_order(order_id, session["user_id"])
    if not order:
        return "Order not found", 404

    conn   = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT oi.*, m.name AS item_name
        FROM order_items oi
        JOIN menu_items m ON oi.item_id = m.item_id
        WHERE oi.order_id = %s
    """, (order_id,))
    items  = cursor.fetchall()
    cursor.execute("SELECT * FROM payments WHERE order_id = %s", (order_id,))
    payment = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("confirmation.html", order=order, items=items, payment=payment)


@app.route("/order/status/<int:order_id>")
@login_required
def order_status(order_id):
    order = db.get_order(order_id, session["user_id"])
    if not order:
        return "Order Not Found", 404

    conn   = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT oi.*, m.name
        FROM order_items oi
        JOIN menu_items m ON oi.item_id = m.item_id
        WHERE oi.order_id = %s
    """, (order_id,))
    items = cursor.fetchall()

    cursor.execute("SELECT * FROM payments WHERE order_id = %s", (order_id,))
    payment = cursor.fetchone()

    cursor.close()
    conn.close()
    return render_template("status.html", order=order, items=items, payment=payment)


@app.route("/orders")
@login_required
def my_orders():
    orders = db.get_user_orders(session["user_id"])
    return render_template("my_orders.html", orders=orders)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
