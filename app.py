import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'kisan-mandi-super-secret-key')

# PostgreSQL database URI (Vercel Postgres / Neon DB / Supabase compatible)
db_url = os.environ.get('DATABASE_URL', 'sqlite:///kisan_mandi.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login_page'

# ---------------------------------------------------------------------------
# Database Models
# ---------------------------------------------------------------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    bookings = db.relationship('Booking', backref='user', lazy=True)

class Mandi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    center = db.Column(db.String(100), nullable=False)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mandi_id = db.Column(db.Integer, db.ForeignKey('mandi.id'), nullable=False)
    mandi_relation = db.relationship('Mandi', backref='bookings')
    crop = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(10), nullable=False)
    slot = db.Column(db.String(20), nullable=False)
    token = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), default='WAITING') # WAITING, IN_PROGRESS, COMPLETED, ABSENT
    payment_status = db.Column(db.String(20), default='PENDING') # PENDING, PAID
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# State-wise Mandi Database Initializer
MANDI_SEED = [
    ("Andhra Pradesh", "Guntur Mirchi Yard", "Yard A"),
    ("Arunachal Pradesh", "Nirjuli Market Yard", "Center 1"),
    ("Assam", "Guwahati APMC Mandi", "Gate 3"),
    ("Bihar", "Gulabbagh Mandi Purnea", "Block B"),
    ("Chhattisgarh", "Raipur Rajdhani Mandi", "Main Yard"),
    ("Goa", "Margao APMC Yard", "Center A"),
    ("Gujarat", "Unjha APMC Mandi", "Yard 2"),
    ("Haryana", "Karnal Grain Market", "Center 1"),
    ("Himachal Pradesh", "Solan Grain & Fruit Mandi", "Gate 1"),
    ("Jharkhand", "Ranchi Dhurwa Mandi", "Block A"),
    ("Karnataka", "Azadpur APMC Hubli", "Yard 1"),
    ("Kerala", "Kochi Nettoor APMC", "Center B"),
    ("Madhya Pradesh", "Neemuch APMC Mandi", "Gate 4"),
    ("Maharashtra", "Vashi APMC Mandi Mumbai", "Section 1"),
    ("Manipur", "Imphal Lamphelpat Mandi", "Yard A"),
    ("Meghalaya", "Shillong Mawiong APMC", "Center 1"),
    ("Mizoram", "Aizawl Khatla Mandi", "Block A"),
    ("Nagaland", "Dimapur Supermarket Mandi", "Center 1"),
    ("Odisha", "Cuttack Malgodown Mandi", "Gate 2"),
    ("Punjab", "Khanna Grain Market", "Main Yard"),
    ("Rajasthan", "Kota Grain Mandi Yard", "Yard 3"),
    ("Sikkim", "Gangtok Local Produce Yard", "Center A"),
    ("Tamil Nadu", "Koyambedu Wholesale Market", "Block C"),
    ("Telangana", "Warangal Enamulgutta Mandi", "Gate 1"),
    ("Tripura", "Agartala Maharajganj Mandi", "Yard 1"),
    ("Uttar Pradesh", "Hapur APMC Grain Mandi", "Gate 2"),
    ("Uttarakhand", "Haldwani Wholesale Mandi", "Block B"),
    ("West Bengal", "Siliguri Regulated Market", "Yard 4")
]

def seed_database():
    db.create_all()
    if Mandi.query.count() == 0:
        for state, name, center in MANDI_SEED:
            db.session.add(Mandi(state=state, name=name, center=center))
        db.session.commit()
    
    # Create default admin if not existing
    if not User.query.filter_by(mobile="9999999999").first():
        admin = User(
            name="Super Admin",
            mobile="9999999999",
            password_hash=generate_password_hash("Admin@Kisan2026"),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()

with app.app_context():
    seed_database()

# ---------------------------------------------------------------------------
# Views & API Endpoints
# ---------------------------------------------------------------------------

@app.route("/")
def home_page():
    return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        mobile = request.form.get("mobile")
        password = request.form.get("password")
        user = User.query.filter_by(mobile=mobile).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("home_page"))
        flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register_page():
    if request.method == "POST":
        name = request.form.get("name")
        mobile = request.form.get("mobile")
        password = request.form.get("password")
        
        if User.query.filter_by(mobile=mobile).first():
            flash("Mobile number already registered.", "warning")
            return redirect(url_for("register_page"))
            
        hashed_pw = generate_password_hash(password)
        new_user = User(name=name, mobile=mobile, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("home_page"))
    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login_page"))

@app.route("/booking")
@login_required
def booking_page():
    mandis = Mandi.query.order_by(Mandi.state).all()
    return render_template("booking.html", mandis=mandis)

@app.route("/queue-page")
@login_required
def queue_page():
    return render_template("queue.html")

@app.route("/tracking")
@login_required
def tracking_page():
    return render_template("tracking.html")

@app.route("/admin")
@login_required
def admin_page():
    if not current_user.is_admin:
        return "Unauthorized Access", 403
    return render_template("admin.html")

# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------

@app.route("/api/mandis")
def get_mandis():
    mandis = Mandi.query.order_by(Mandi.state).all()
    return jsonify([{"id": m.id, "state": m.state, "name": m.name, "center": m.center} for m in mandis])

@app.route("/api/availability")
def slot_availability():
    mandi_id = request.args.get("mandi_id", type=int)
    date = request.args.get("date")
    CAPACITY_PER_SLOT = 15
    slots = ["08:00 - 10:00", "10:00 - 12:00", "12:00 - 02:00", "02:00 - 04:00"]
    
    result = []
    for slot in slots:
        count = Booking.query.filter_by(mandi_id=mandi_id, date=date, slot=slot).count()
        remaining = max(0, CAPACITY_PER_SLOT - count)
        
        if remaining > 10:
            color = "green"
        elif remaining >= 5:
            color = "yellow"
        elif remaining >= 1:
            color = "orange"
        else:
            color = "red"
            
        result.append({
            "slot": slot,
            "remaining": remaining,
            "color": color
        })
    return jsonify(result)

@app.route("/book-slot", methods=["POST"])
@login_required
def book_slot():
    data = request.json
    date = data.get("date")
    mandi_id = data.get("mandi_id")
    slot = data.get("slot")
    
    # Rule: Max 2 slots per day per person
    daily_count = Booking.query.filter_by(user_id=current_user.id, date=date).count()
    if daily_count >= 2:
        return jsonify({"error": "Limit exceeded: You can book at most 2 slots per day."}), 400
        
    # Generate incremental token per mandi per day
    tokens_today = Booking.query.filter_by(mandi_id=mandi_id, date=date).count()
    token_number = tokens_today + 1
    
    booking = Booking(
        user_id=current_user.id,
        mandi_id=mandi_id,
        crop=data.get("crop"),
        quantity=float(data.get("quantity")),
        date=date,
        slot=slot,
        token=token_number,
        status="WAITING"
    )
    db.session.add(booking)
    db.session.commit()
    
    mandi = Mandi.query.get(mandi_id)
    return jsonify({
        "id": booking.id,
        "name": current_user.name,
        "token": booking.token,
        "mandi": mandi.name,
        "slot": booking.slot,
        "status": booking.status
    })

@app.route("/queue")
@login_required
def get_queue():
    today = datetime.now().strftime("%Y-%m-%d")
    waiting_list = Booking.query.filter_by(date=today, status="WAITING").order_by(Booking.id.asc()).all()
    in_progress = Booking.query.filter_by(date=today, status="IN_PROGRESS").first()
    
    formatted = []
    for idx, b in enumerate(waiting_list):
        formatted.append({
            "token": b.token,
            "name": b.user.name,
            "people_ahead": idx,
            "estimated_wait": idx * 10
        })
        
    return jsonify({
        "total": len(waiting_list),
        "current": in_progress.token if in_progress else (waiting_list[0].token if waiting_list else None),
        "queue": formatted
    })

@app.route("/status/<int:booking_id>")
@login_required
def get_status(booking_id):
    b = Booking.query.get(booking_id)
    if not b or b.user_id != current_user.id:
        return jsonify({"error": "Booking not found"}), 404
        
    return jsonify({
        "token": b.token,
        "name": b.user.name,
        "crop": b.crop,
        "quantity": b.quantity,
        "mandi": b.mandi_relation.name,
        "date": b.date,
        "slot": b.slot,
        "status": b.status,
        "payment_status": b.payment_status
    })

@app.route("/bookings")
@login_required
def get_user_bookings():
    user_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.id.desc()).all()
    return jsonify([{
        "id": b.id,
        "token": b.token,
        "crop": b.crop,
        "date": b.date,
        "slot": b.slot,
        "status": b.status
    } for b in user_bookings])

# ---------------------------------------------------------------------------
# Admin API Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/admin/queue")
@login_required
def admin_queue():
    if not current_user.is_admin:
        return jsonify({"error": "Forbidden"}), 403
    today = datetime.now().strftime("%Y-%m-%d")
    bookings = Booking.query.filter_by(date=today).order_by(Booking.id.asc()).all()
    return jsonify([{
        "id": b.id,
        "token": b.token,
        "name": b.user.name,
        "mobile": b.user.mobile,
        "crop": b.crop,
        "quantity": b.quantity,
        "status": b.status,
        "payment_status": b.payment_status
    } for b in bookings])

@app.route("/api/admin/action", methods=["POST"])
@login_required
def admin_action():
    if not current_user.is_admin:
        return jsonify({"error": "Forbidden"}), 403
    data = request.json
    booking_id = data.get("booking_id")
    action = data.get("action") # 'NEXT', 'MARK_ABSENT', 'MARK_DONE', 'MARK_PAID'
    
    b = Booking.query.get(booking_id)
    if not b:
        return jsonify({"error": "Booking not found"}), 404
        
    if action == "NEXT":
        b.status = "IN_PROGRESS"
    elif action == "MARK_ABSENT":
        b.status = "ABSENT"
    elif action == "MARK_DONE":
        b.status = "COMPLETED"
    elif action == "MARK_PAID":
        b.payment_status = "PAID"
        
    db.session.commit()
    return jsonify({"success": True, "new_status": b.status, "payment_status": b.payment_status})

if __name__ == "__main__":
    app.run(debug=True)
