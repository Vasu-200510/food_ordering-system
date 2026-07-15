from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from functools import wraps
import models

app = Flask(__name__)
app.config["SECRET_KEY"] = "foodies-dev-secret-key"

with app.app_context():
    models.init_db()
    models.seed_food_items()


# ---------- helpers ----------

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return models.get_user_by_id(uid)


@app.context_processor
def inject_globals():
    user = current_user()
    return {
        "current_user": user,
        "cart_badge": models.cart_count(user["id"]) if user else 0,
    }


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


# ---------- routes ----------

@app.route("/")
def index():
    featured = models.get_all_food_items()[:3]
    return render_template("index.html", featured=featured)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()

        if not name or not email or not password:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("register"))

        if models.get_user_by_email(email):
            flash("An account with that email already exists.", "error")
            return redirect(url_for("register"))

        uid = models.create_user(name, email, password, phone)
        session["user_id"] = uid
        flash("Welcome to Foodies! Your account has been created.", "success")
        return redirect(url_for("menu"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = models.get_user_by_email(email)
        if user and models.verify_password(user["password"], password):
            session["user_id"] = user["id"]
            flash("Logged in successfully.", "success")
            return redirect(url_for("menu"))
        flash("Invalid email or password.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/menu")
def menu():
    category = request.args.get("category", "All")
    items = models.get_all_food_items(category)
    categories = ["All", "Pizza", "Burger", "Pasta", "Sides", "Drinks", "Desserts"]
    return render_template("menu.html", items=items, categories=categories, active=category)


@app.route("/cart/add/<int:item_id>", methods=["POST"])
@login_required
def add_to_cart(item_id):
    user = current_user()
    models.add_to_cart(user["id"], item_id)
    flash("Added to your cart.", "success")
    return redirect(request.referrer or url_for("menu"))


@app.route("/cart/update/<int:cart_id>", methods=["POST"])
@login_required
def update_cart(cart_id):
    action = request.form.get("action")
    models.update_cart_item(cart_id, current_user()["id"], action)
    return redirect(url_for("cart"))


@app.route("/cart")
@login_required
def cart():
    user = current_user()
    items = models.get_cart_items(user["id"])
    total = sum(i["price"] * i["quantity"] for i in items)
    return render_template("cart.html", items=items, total=total)


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    user = current_user()
    items = models.get_cart_items(user["id"])
    if not items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("menu"))
    total = sum(i["price"] * i["quantity"] for i in items)

    if request.method == "POST":
        order_id = models.create_order(
            user_id=user["id"],
            total=total,
            name=request.form.get("name"),
            address=request.form.get("address"),
            phone=request.form.get("phone"),
            pincode=request.form.get("pincode"),
            payment_method=request.form.get("payment_method", "Cash on Delivery"),
            cart_items=items,
        )
        return redirect(url_for("order_confirmation", order_id=order_id))

    return render_template("checkout.html", items=items, total=total, user=user)


@app.route("/order/<int:order_id>")
@login_required
def order_confirmation(order_id):
    order = models.get_order(order_id)
    if not order or order["user_id"] != current_user()["id"]:
        return redirect(url_for("index"))
    return render_template("order_confirmation.html", order=order)


@app.route("/profile")
@login_required
def profile():
    user = current_user()
    orders = models.get_orders_for_user(user["id"])
    orders_with_items = []
    for o in orders:
        d = dict(o)
        d["order_items"] = models.get_order_items(o["id"])
        d["date_obj"] = datetime.fromisoformat(o["date"])
        orders_with_items.append(d)
    return render_template("profile.html", user=user, orders=orders_with_items)


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    user = current_user()
    if request.method == "POST":
        models.update_user(
            user["id"],
            request.form.get("name", user["name"]),
            request.form.get("phone", user["phone"]),
            request.form.get("address", user["address"]),
        )
        flash("Profile updated.", "success")
        return redirect(url_for("profile"))
    return render_template("edit_profile.html", user=user)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        flash("Thanks for reaching out — we'll reply within 24 hours.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")


if_name_=="_main_":
port=int(os.environ.get("PORT",5000))app.run(host="0.0.0.0",port=port)