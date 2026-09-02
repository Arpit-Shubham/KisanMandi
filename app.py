import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.pool import NullPool

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'kisan-mandi-fixed-secret-key-2026')

# ---------------------------------------------------------------------------
# Database Configuration (Neon Optimized)
# ---------------------------------------------------------------------------

db_url = os.environ.get('DATABASE_URL', 'sqlite:///kisan_mandi.db')

# Convert legacy postgres:// to postgresql://
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Optimized for Neon Pooled Serverless Connections
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "poolclass": NullPool,
    "pool_pre_ping": True,
    "connect_args": {
        "connect_timeout": 10
    } if db_url.startswith("postgresql") else {}
}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login_page'

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    bookings = db.relationship('Booking', backref='user', lazy=True)

class Mandi(db.Model):
    __tablename__ = 'mandi'
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    center = db.Column(db.String(100), nullable=False)

class Booking(db.Model):
    __tablename__ = 'booking'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mandi_id = db.Column(db.Integer, db.ForeignKey('mandi.id'), nullable=False)
    mandi_relation = db.relationship('Mandi', backref='bookings')
    crop = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(10), nullable=False)
    slot = db.Column(db.String(30), nullable=False)
    token = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), default='WAITING')
    payment_status = db.Column(db.String(20), default='PENDING')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def generate_10min_slots():
    slots = []
    start_time = datetime.strptime("08:00", "%H:%M")
    end_time = datetime.strptime("17:00", "%H:%M")
    current = start_time
    while current < end_time:
        nxt = current + timedelta(minutes=10)
        slot_str = f"{current.strftime('%I:%M %p')} - {nxt.strftime('%I:%M %p')}"
        slots.append(slot_str)
        current = nxt
    return slots

ALL_SLOTS = generate_10min_slots()

# Automatic Schema Creation & Seeding for Fresh Database
def init_db():
    with app.app_context():
        try:
            db.create_all()
            
            # Create default admin user if none exists
            admin = User.query.filter_by(mobile="9999999999").first()
            if not admin:
                admin_pw = generate_password_hash("Admin@Kisan2026", method='pbkdf2:sha256')
                admin = User(name="Admin", mobile="9999999999", password_hash=admin_pw, is_admin=True)
                db.session.add(admin)
                
            # Seed Mandi data if empty
            if Mandi.query.count() == 0:
                sample_mandis = [
                    Mandi(state="Punjab", name="Khanna Mandi", center="Central Yard"),
                    Mandi(state="Haryana", name="Karnal Mandi", center="Gate 1"),
                    Mandi(state="Uttar Pradesh", name="Agra Mandi", center="Block B")
                ]
                db.session.add_all(sample_mandis)
                
            db.session.commit()
            print("Database initialized successfully.")
        except Exception as e:
            print("Database init bypassed:", e)

init_db()

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def home_page():
    return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        mobile = request.form.get("mobile", "").strip()
        password = request.form.get("password", "").strip()
        
        try:
            user = User.query.filter_by(mobile=mobile).first()
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                return redirect(url_for("home_page"))
            flash("Invalid mobile number or password.", "danger")
        except Exception as e:
            db.session.rollback()
            error_msg = f"LOGIN_ERROR: {type(e).__name__} - {str(e)}"
            print(error_msg)
            flash(error_msg, "danger")
            
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register_page():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        mobile = request.form.get("mobile", "").strip()
        password = request.form.get("password", "").strip()

        if not name or not mobile or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        try:
            existing_user = User.query.filter_by(mobile=mobile).first()
            if existing_user:
                flash("Mobile number already registered.", "warning")
                return redirect(url_for("register_page"))

            hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(name=name, mobile=mobile, password_hash=hashed_pw)
            
            db.session.add(new_user)
            db.session.commit()

            login_user(new_user)
            return redirect(url_for("home_page"))

        except Exception as e:
            db.session.rollback()
            error_msg = f"REGISTRATION_ERROR: {type(e).__name__} - {str(e)}"
            print(error_msg)
            flash(error_msg, "danger")
            return render_template("register.html")

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
# API Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/availability")
def slot_availability():
    mandi_id = request.args.get("mandi_id", type=int)
    date = request.args.get("date")
    
    if not mandi_id or not date:
        return jsonify({"overall_color": "green", "remaining_count": len(ALL_SLOTS), "total_slots": len(ALL_SLOTS), "slots": []})

    booked_slots = db.session.query(Booking.slot).filter_by(mandi_id=mandi_id, date=date).all()
    booked_set = set([b[0] for b in booked_slots])
    
    total_slots_count = len(ALL_SLOTS)
    remaining_count = total_slots_count - len(booked_set)
    
    if remaining_count > 35:
        overall_color = "green"
    elif remaining_count >= 15:
        overall_color = "yellow"
    elif remaining_count >= 1:
        overall_color = "orange"
    else:
        overall_color = "red"
        
    slots_data = []
    for s in ALL_SLOTS:
        is_booked = s in booked_set
        slots_data.append({
            "slot": s,
            "available": not is_booked,
            "status_text": "Booked" if is_booked else "Available",
            "color": "red" if is_booked else "green"
        })

    return jsonify({
        "overall_color": overall_color,
        "remaining_count": remaining_count,
        "total_slots": total_slots_count,
        "slots": slots_data
    })

@app.route("/book-slot", methods=["POST"])
@login_required
def book_slot():
    data = request.json
    date = data.get("date")
    mandi_id = data.get("mandi_id")
    slot = data.get("slot")
    
    try:
        daily_count = Booking.query.filter_by(user_id=current_user.id, date=date).count()
        if daily_count >= 2:
            return jsonify({"error": "Limit exceeded: You can book at most 2 slots per day."}), 400

        existing = Booking.query.filter_by(mandi_id=mandi_id, date=date, slot=slot).first()
        if existing:
            return jsonify({"error": "This slot is already booked."}), 400
            
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
    except Exception as e:
        db.session.rollback()
        print("Booking Error:", str(e))
        return jsonify({"error": "Booking failed. Try again."}), 500

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
            "slot": b.slot,
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
        return jsonify({"error": "Not found"}), 404
        
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
        "slot": b.slot,
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
    action = data.get("action")
    
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
