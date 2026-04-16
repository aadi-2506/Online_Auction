from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "secretkey123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///auction.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "static/uploads"

IST = ZoneInfo("Asia/Kolkata")

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(300), nullable=False)

class Auction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    image = db.Column(db.String(200), nullable=False)
    start_price = db.Column(db.Float, nullable=False)
    highest_bid = db.Column(db.Float, nullable=False)
    highest_bidder = db.Column(db.String(100), default="No bids")
    seller = db.Column(db.String(100), nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    extended = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default="Active")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def update_status():
    now = datetime.now(IST)
    items = Auction.query.filter_by(status="Active").all()

    for item in items:
        if now >= item.end_time:
            item.status = "Ended"

    db.session.commit()

with app.app_context():
    os.makedirs("static/uploads", exist_ok=True)
    db.create_all()

@app.route("/")
def home():
    update_status()
    items = Auction.query.order_by(Auction.id.desc()).all()
    return render_template("index.html", items=items)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        if User.query.filter_by(username=username).first():
            flash("Username already exists")
            return redirect(url_for("register"))

        user = User(
            username=username,
            password=generate_password_hash(password)
        )

        db.session.add(user)
        db.session.commit()

        flash("Registration successful")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Invalid username or password")

    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    my_items = Auction.query.filter_by(seller=current_user.username).all()
    return render_template("dashboard.html", my_items=my_items)

@app.route("/add_item", methods=["GET", "POST"])
@login_required
def add_item():
    if request.method == "POST":
        file = request.files["image"]

        if file.filename == "":
            flash("Select image")
            return redirect(url_for("add_item"))

        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        price = float(request.form["price"])
        minutes = int(request.form["minutes"])

        item = Auction(
            title=request.form["title"],
            description=request.form["description"],
            image=filename,
            start_price=price,
            highest_bid=price,
            highest_bidder="No bids",
            seller=current_user.username,
            end_time=datetime.now(IST) + timedelta(minutes=minutes)
        )

        db.session.add(item)
        db.session.commit()

        flash("Auction created")
        return redirect(url_for("home"))

    return render_template("add_item.html")

@app.route("/auction/<int:item_id>", methods=["GET", "POST"])
@login_required
def auction(item_id):
    update_status()
    item = Auction.query.get_or_404(item_id)

    if request.method == "POST":
        if item.status == "Ended":
            flash("Auction ended")
            return redirect(url_for("auction", item_id=item.id))

        bid = float(request.form["bid"])

        if bid > item.highest_bid:
            item.highest_bid = bid
            item.highest_bidder = current_user.username
            db.session.commit()
            flash("Bid placed successfully")
        else:
            flash("Bid must be higher than current highest bid")

        return redirect(url_for("auction", item_id=item.id))

    return render_template("auction.html", item=item)

@app.route("/extend/<int:item_id>")
@login_required
def extend(item_id):
    item = Auction.query.get_or_404(item_id)

    if item.seller == current_user.username and item.extended == False and item.status == "Active":
        item.end_time = item.end_time + timedelta(minutes=5)
        db.session.commit()
        item.extended = True
        db.session.commit()
        flash("Auction extended by 5 minutes")

    return redirect(url_for("auction", item_id=item.id))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
