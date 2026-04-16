from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "secretkey"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///auction.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "static/uploads"

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
    title = db.Column(db.String(200))
    description = db.Column(db.String(500))
    image = db.Column(db.String(200))
    start_price = db.Column(db.Float)
    highest_bid = db.Column(db.Float)
    highest_bidder = db.Column(db.String(100))
    seller = db.Column(db.String(100))
    end_time = db.Column(db.DateTime)
    extended = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default="Active")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def update_status():
    items = Auction.query.filter_by(status="Active").all()
    now = datetime.now()
    for item in items:
        if now >= item.end_time:
            item.status = "Ended"
    db.session.commit()

@app.route("/")
def home():
    update_status()
    items = Auction.query.order_by(Auction.id.desc()).all()
    return render_template("index.html", items=items)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        if User.query.filter_by(username=username).first():
            flash("Username already exists")
            return redirect(url_for("register"))

        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash("Registered Successfully")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()

        if user and check_password_hash(user.password, request.form["password"]):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Invalid Login")

    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    my_items = Auction.query.filter_by(seller=current_user.username).all()
    return render_template("dashboard.html", my_items=my_items)

@app.route("/add_item", methods=["GET","POST"])
@login_required
def add_item():
    if request.method == "POST":
        file = request.files["image"]
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
            end_time=datetime.now() + timedelta(minutes=minutes)
        )

        db.session.add(item)
        db.session.commit()
        return redirect(url_for("home"))

    return render_template("add_item.html")

@app.route("/auction/<int:id>", methods=["GET","POST"])
@login_required
def auction(id):
    update_status()
    item = Auction.query.get_or_404(id)

    if request.method == "POST":
        if item.status == "Ended":
            flash("Auction Ended")
            return redirect(url_for("auction", id=id))

        bid = float(request.form["bid"])

        if bid > item.highest_bid:
            item.highest_bid = bid
            item.highest_bidder = current_user.username
            db.session.commit()
            flash("Bid Placed Successfully")
        else:
            flash("Bid must be higher than current highest bid")

    return render_template("auction.html", item=item)

@app.route("/extend/<int:id>")
@login_required
def extend(id):
    item = Auction.query.get_or_404(id)

    if item.seller == current_user.username and item.extended == False and item.status == "Active":
        item.end_time = item.end_time + timedelta(minutes=5)
        item.extended = True
        db.session.commit()

    return redirect(url_for("auction", id=id))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

if __name__ == "__main__":
    os.makedirs("static/uploads", exist_ok=True)
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
