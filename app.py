from flask import Flask, render_template, request, redirect, url_for, session
import db

app = Flask(__name__)
app.secret_key = "foodapp123"

db.init_db()

@app.route("/")
def home():
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM restaurants WHERE is_active = 1")
    restaurants = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("home.html", restaurants=restaurants)

@app.route("/restaurant/<int:restaurant_id>")
def restaurant(restaurant_id):
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
    restaurant = cursor.fetchone()
    
    cursor.execute("""
        SELECT m.*, c.name AS category_name 
        FROM menu_items m 
        JOIN categories c ON m.category_id = c.category_id
        WHERE m.restaurant_id = %s AND m.is_available = 1
    """, (restaurant_id,))
    menu_items = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template("restaurant.html", restaurant=restaurant, menu_items=menu_items)

@app.route("/cart/add", methods=["POST"])
def add_to_cart():
    item_id = request.form.get("item_id")
    name = request.form.get("name")
    price = float(request.form.get("price"))
    restaurant_name = request.form.get("restaurant_name")
    
    if "cart" not in session:
        session["cart"] = {}
        
    cart = session["cart"]
    if item_id in cart:
        cart[item_id]["quantity"] += 1
    else:
        cart[item_id] = {"name": name, "price": price, "quantity": 1, "restaurant": restaurant_name}
        
    session["cart"] = cart
    return redirect(request.referrer or url_for("home"))

@app.route("/cart")
def view_cart():
    cart = session.get("cart", {})
    total = sum(item["price"] * item["quantity"] for item in cart.values())
    return render_template("cart.html", cart=cart, total=total)

@app.route("/order/place", methods=["POST"])
def order_place():
    cart = session.get("cart", {})
    if not cart:
        return redirect(url_for("home"))
        
    address = request.form.get("address", "Takeaway / Default Guest Address")
    guest_user_id = 1 
    
    try:
        order_id = db.place_order(guest_user_id, cart, address)
        session.pop("cart", None) 
        return redirect(url_for("order_confirmation", order_id=order_id))
    except Exception as e:
        return f"Database Transaction Error: {str(e)}", 500

@app.route("/order/confirm/<int:order_id>")
def order_confirmation(order_id):
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    order = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("confirmation.html", order=order)

@app.route("/order/status/<int:order_id>")
def order_status(order_id):
    conn = db.get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    order = cursor.fetchone()
    
    if not order:
        cursor.close()
        conn.close()
        return "Order Not Found", 404

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

if __name__ == "__main__":
    app.run(debug=True, port=5000)