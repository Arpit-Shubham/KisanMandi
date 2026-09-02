from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

queue = []
bookings = []

mandi = {
    "name": "Hapur Mandi",
    "center": "Center A",
    "gate": "Gate No. 2",
    "distance": "4.2 km"
}



# -------------------------
# HTML PAGES
# -------------------------

@app.route("/")
def home_page():
    return render_template("home.html")


@app.route("/booking")
def booking_page():
    return render_template("booking.html")


@app.route("/queue-page")
def queue_page():
    return render_template("queue.html")


@app.route("/tracking")
def tracking_page():
    return render_template("tracking.html")


# -------------------------
# API
# -------------------------

@app.route("/book-slot", methods=["POST"])
def book_slot():

    data = request.json

    token = len(queue) + 1

    booking = {
        "name": data.get("name"),
        "mobile": data.get("mobile"),

        "crop": data.get("crop"),
        "quantity": data.get("quantity"),

        "date": data.get("date"),
        "slot": data.get("slot"),

        "mandi": mandi["name"],
        "center": mandi["center"],
        "gate": mandi["gate"],
        "distance": mandi["distance"],

        "token": token,
        "people_ahead": len(queue),
        "estimated_wait": len(queue) * 5,

        "status": "in_queue"
    }

    queue.append(booking)
    bookings.append(booking)

    return jsonify(booking)


@app.route("/queue")
def get_queue():

    return jsonify({
        "total": len(queue),
        "current": queue[0]["token"] if queue else 0,
        "queue": queue
    })


@app.route("/status/<int:token>")
def get_status(token):

    for b in bookings:
        if b["token"] == token:
            return jsonify(b)

    return jsonify({
        "error": "Not found"
    }), 404


@app.route("/home")
def get_home():

    if not bookings:
        return jsonify({
            "message": "No booking yet"
        })

    token = request.args.get("token", type=int)

    b = bookings[-1]

    if token is not None:
        for booking in bookings:
            if booking["token"] == token:
                b = booking
                break

    return jsonify({
        "name": b["name"],
        "mobile": b["mobile"],
        "mandi": b["mandi"],
        "center": b["center"],
        "distance": b["distance"],
        "token": b["token"],
        "status": b["status"],
        "date": b["date"],
        "slot": b["slot"]
    })


@app.route("/bookings")
def get_bookings():

    return jsonify([
        {
            "token": b["token"],
            "name": b["name"],
            "crop": b["crop"],
            "date": b["date"],
            "slot": b["slot"]
        }
        for b in bookings
    ])


app.run(debug=True)