import os
import re
import secrets
import hashlib
import sqlite3
import string
from datetime import date, datetime, time, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

from config import Config
from database import init_app, get_db

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    init_app(app)

    @app.before_request
    def csrf_protect():
        if app.config.get("DISABLE_CSRF", False):
            return
        if request.method == "POST":
            token = session.get("_csrf_token")
            submitted = request.form.get("_csrf_token") or request.headers.get("X-CSRF-Token")
            if not token or not submitted or not secrets.compare_digest(token, submitted):
                abort(400, description="Invalid or missing security token.")

    @app.context_processor
    def inject_csrf():
        if "_csrf_token" not in session:
            session["_csrf_token"] = secrets.token_urlsafe(32)
        return {"csrf_token": session["_csrf_token"], "today": date.today().isoformat()}

    def current_user():
        uid = session.get("user_id")
        if not uid:
            return None
        return get_db().execute("SELECT id,name,email FROM users WHERE id=?", (uid,)).fetchone()

    def owned_business():
        user = current_user()
        if not user:
            return None
        return get_db().execute("SELECT * FROM businesses WHERE owner_id=?", (user["id"],)).fetchone()

    def login_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user():
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            return fn(*args, **kwargs)
        return wrapper

    def business_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user():
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if not owned_business():
                return redirect(url_for("setup"))
            return fn(*args, **kwargs)
        return wrapper

    @app.context_processor
    def inject_globals():
        return {"nav_user": current_user(), "nav_business": owned_business()}

    def slugify(value):
        value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
        return value[:48] or "my-business"

    def unique_slug(name):
        db = get_db()
        root = slugify(name)
        slug = root
        n = 2
        while db.execute("SELECT 1 FROM businesses WHERE slug=?", (slug,)).fetchone():
            slug = f"{root}-{n}"
            n += 1
        return slug

    def token_hash(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def parse_hhmm(value):
        return datetime.strptime(value, "%H:%M").time()

    def minutes(t):
        return t.hour * 60 + t.minute

    def hhmm(total):
        return f"{total // 60:02d}:{total % 60:02d}"

    def get_slots(business_id, service, day):
        """Return valid start times; service duration + buffer blocks the next booking."""
        db = get_db()
        day_obj = date.fromisoformat(day)
        if day_obj < date.today():
            return []
        settings = db.execute("SELECT * FROM booking_settings WHERE business_id=?", (business_id,)).fetchone()
        if settings:
            if day_obj > date.today() + timedelta(days=settings["advance_booking_days"]):
                return []
            min_notice = settings["minimum_notice"]
        else:
            min_notice = 60
        weekday = day_obj.weekday()
        hours = db.execute(
            "SELECT * FROM business_hours WHERE business_id=? AND weekday=?",
            (business_id, weekday)
        ).fetchone()
        if not hours or hours["is_closed"] or not hours["opening_time"] or not hours["closing_time"]:
            return []
        if db.execute("SELECT 1 FROM unavailable_dates WHERE business_id=? AND date=?", (business_id, day)).fetchone():
            return []
        opening, closing = minutes(parse_hhmm(hours["opening_time"])), minutes(parse_hhmm(hours["closing_time"]))
        duration = int(service["duration"])
        buffer_time = int(service["buffer_time"])
        if duration <= 0 or opening >= closing:
            return []
        breaks = db.execute(
            "SELECT start_time,end_time FROM business_breaks WHERE business_id=? AND weekday=?",
            (business_id, weekday)
        ).fetchall()
        break_ranges = [(minutes(parse_hhmm(b["start_time"])), minutes(parse_hhmm(b["end_time"]))) for b in breaks]
        bookings = db.execute(
            """SELECT start_time,block_end_time FROM appointments
               WHERE business_id=? AND appointment_date=? AND status IN ('confirmed','completed','no_show')""",
            (business_id, day)
        ).fetchall()
        booked_ranges = [(minutes(parse_hhmm(b["start_time"])), minutes(parse_hhmm(b["block_end_time"]))) for b in bookings]
        now = datetime.now()
        earliest = opening
        if day_obj == date.today():
            earliest = max(earliest, minutes(now.time()) + min_notice)
        # 15-minute start increments; duration and buffer determine the occupied interval.
        first = ((earliest + 14) // 15) * 15
        result = []
        for start in range(first, closing - duration - buffer_time + 1, 15):
            end = start + duration
            block_end = end + buffer_time
            overlaps_break = any(start < b_end and block_end > b_start for b_start, b_end in break_ranges)
            overlaps_booking = any(start < b_end and block_end > b_start for b_start, b_end in booked_ranges)
            if not overlaps_break and not overlaps_booking:
                result.append(hhmm(start))
        return result

    @app.get("/")
    def index():
        featured = get_db().execute(
            "SELECT name,slug,category,description,address FROM businesses ORDER BY created_at DESC LIMIT 6"
        ).fetchall()
        return render_template("index.html", featured=featured)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")
            if not name or not email or len(password) < 8:
                flash("Enter your name, a valid email and a password of at least 8 characters.", "danger")
            elif password != confirm:
                flash("Passwords do not match.", "danger")
            else:
                try:
                    cur = get_db().execute(
                        "INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                        (name, email, generate_password_hash(password))
                    )
                    session.clear()
                    session["user_id"] = cur.lastrowid
                    flash("Account created. Let's set up your business.", "success")
                    return redirect(url_for("setup"))
                except sqlite3.IntegrityError:
                    flash("An account with that email already exists.", "danger")
        return render_template("auth.html", mode="register")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                flash("Welcome back.", "success")
                return redirect(url_for("dashboard") if owned_business() else url_for("setup"))
            flash("Invalid email or password.", "danger")
        return render_template("auth.html", mode="login")

    @app.post("/logout")
    def logout():
        session.clear()
        flash("You have been logged out.", "success")
        return redirect(url_for("index"))

    @app.route("/setup", methods=["GET", "POST"])
    @login_required
    def setup():
        if owned_business():
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            name = request.form.get("business_name", "").strip()
            category = request.form.get("category", "").strip()
            phone = request.form.get("phone", "").strip()
            email = request.form.get("business_email", "").strip()
            description = request.form.get("description", "").strip()
            address = request.form.get("address", "").strip()
            if not name or not category or not phone:
                flash("Business name, category and phone are required.", "danger")
                return render_template("setup.html")
            db = get_db()
            try:
                cur = db.execute(
                    """INSERT INTO businesses(owner_id,name,slug,category,description,phone,email,address)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (current_user()["id"], name, unique_slug(name), category, description, phone, email, address)
                )
                bid = cur.lastrowid
                db.execute("INSERT INTO booking_settings(business_id) VALUES(?)", (bid,))
                # Default Mon-Sat, 09:00-17:00; Sunday closed. Owner can edit afterwards.
                for weekday in range(7):
                    closed = 1 if weekday == 6 else 0
                    db.execute(
                        "INSERT INTO business_hours(business_id,weekday,opening_time,closing_time,is_closed) VALUES(?,?,?,?,?)",
                        (bid, weekday, "09:00", "17:00", closed)
                    )
                flash("Business created. Add your services and adjust your schedule.", "success")
                return redirect(url_for("management"))
            except sqlite3.IntegrityError:
                flash("Could not create the business. Please try a different name.", "danger")
        return render_template("setup.html")

    @app.get("/dashboard")
    @business_required
    def dashboard():
        biz = owned_business()
        db = get_db()
        stats = {
            "total": db.execute("SELECT COUNT(*) n FROM appointments WHERE business_id=?", (biz["id"],)).fetchone()["n"],
            "upcoming": db.execute("SELECT COUNT(*) n FROM appointments WHERE business_id=? AND status='confirmed' AND appointment_date>=?", (biz["id"], date.today().isoformat())).fetchone()["n"],
            "completed": db.execute("SELECT COUNT(*) n FROM appointments WHERE business_id=? AND status='completed'", (biz["id"],)).fetchone()["n"],
            "no_show": db.execute("SELECT COUNT(*) n FROM appointments WHERE business_id=? AND status='no_show'", (biz["id"],)).fetchone()["n"],
        }
        appointments = db.execute(
            """SELECT * FROM appointments WHERE business_id=? AND appointment_date>=?
               AND status IN ('confirmed','completed','no_show')
               ORDER BY appointment_date,start_time LIMIT 30""",
            (biz["id"], date.today().isoformat())
        ).fetchall()
        return render_template("dashboard.html", biz=biz, stats=stats, appointments=appointments)

    @app.get("/management")
    @business_required
    def management():
        biz = owned_business()
        db = get_db()
        services = db.execute("SELECT * FROM services WHERE business_id=? ORDER BY id DESC", (biz["id"],)).fetchall()
        hours = db.execute("SELECT * FROM business_hours WHERE business_id=? ORDER BY weekday", (biz["id"],)).fetchall()
        breaks = db.execute("SELECT * FROM business_breaks WHERE business_id=? ORDER BY weekday,start_time", (biz["id"],)).fetchall()
        settings = db.execute("SELECT * FROM booking_settings WHERE business_id=?", (biz["id"],)).fetchone()
        unavailable = db.execute("SELECT * FROM unavailable_dates WHERE business_id=? ORDER BY date", (biz["id"],)).fetchall()
        return render_template("management.html", biz=biz, services=services, hours=hours, breaks=breaks, settings=settings, unavailable=unavailable)

    @app.post("/services")
    @business_required
    def add_service():
        biz = owned_business()
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        try:
            price = float(request.form.get("price", "0"))
            duration = int(request.form.get("duration", "0"))
            buffer_time = int(request.form.get("buffer_time", "0"))
        except ValueError:
            price, duration, buffer_time = -1, 0, -1
        if not name or price < 0 or duration <= 0 or buffer_time < 0 or duration > 720 or buffer_time > 240:
            flash("Enter a service name, non-negative price, duration (1–720 min) and buffer (0–240 min).", "danger")
        else:
            get_db().execute(
                "INSERT INTO services(business_id,name,description,price,duration,buffer_time) VALUES(?,?,?,?,?,?)",
                (biz["id"], name, description, price, duration, buffer_time)
            )
            flash("Service added.", "success")
        return redirect(url_for("management") + "#services")

    @app.post("/services/<int:service_id>/update")
    @business_required
    def update_service(service_id):
        biz = owned_business()
        row = get_db().execute("SELECT * FROM services WHERE id=? AND business_id=?", (service_id, biz["id"])).fetchone()
        if not row:
            abort(404)
        name = request.form.get("name", "").strip()
        try:
            price = float(request.form.get("price", "0"))
            duration = int(request.form.get("duration", "0"))
            buffer_time = int(request.form.get("buffer_time", "0"))
        except ValueError:
            price, duration, buffer_time = -1, 0, -1
        if not name or price < 0 or duration <= 0 or buffer_time < 0:
            flash("Please enter valid service details.", "danger")
        else:
            get_db().execute(
                "UPDATE services SET name=?,description=?,price=?,duration=?,buffer_time=? WHERE id=? AND business_id=?",
                (name, request.form.get("description", "").strip(), price, duration, buffer_time, service_id, biz["id"])
            )
            flash("Service updated.", "success")
        return redirect(url_for("management") + "#services")

    @app.post("/services/<int:service_id>/toggle")
    @business_required
    def toggle_service(service_id):
        biz = owned_business()
        row = get_db().execute("SELECT * FROM services WHERE id=? AND business_id=?", (service_id, biz["id"])).fetchone()
        if not row:
            abort(404)
        get_db().execute("UPDATE services SET is_active=? WHERE id=?", (0 if row["is_active"] else 1, service_id))
        flash("Service availability updated.", "success")
        return redirect(url_for("management") + "#services")

    @app.post("/services/<int:service_id>/delete")
    @business_required
    def delete_service(service_id):
        biz = owned_business()
        row = get_db().execute("SELECT id FROM services WHERE id=? AND business_id=?", (service_id, biz["id"])).fetchone()
        if not row:
            abort(404)
        # Preserve appointment history; deactivation is safer than deleting a referenced service.
        get_db().execute("UPDATE services SET is_active=0 WHERE id=?", (service_id,))
        flash("Service archived. Existing appointment history is preserved.", "success")
        return redirect(url_for("management") + "#services")

    @app.post("/schedule")
    @business_required
    def save_schedule():
        biz = owned_business()
        db = get_db()
        for weekday in range(7):
            closed = 1 if request.form.get(f"closed_{weekday}") == "on" else 0
            opening = request.form.get(f"open_{weekday}", "09:00")
            closing = request.form.get(f"close_{weekday}", "17:00")
            try:
                valid = parse_hhmm(opening) < parse_hhmm(closing)
            except ValueError:
                valid = False
            if not closed and not valid:
                flash("For open days, closing time must be later than opening time.", "danger")
                return redirect(url_for("management") + "#hours")
            db.execute(
                """UPDATE business_hours SET opening_time=?,closing_time=?,is_closed=?
                   WHERE business_id=? AND weekday=?""",
                (opening, closing, closed, biz["id"], weekday)
            )
        flash("Working hours saved.", "success")
        return redirect(url_for("management") + "#hours")

    @app.post("/breaks")
    @business_required
    def add_break():
        biz = owned_business()
        try:
            weekday = int(request.form.get("weekday"))
            start = request.form.get("start_time")
            end = request.form.get("end_time")
            if weekday not in range(7) or parse_hhmm(start) >= parse_hhmm(end):
                raise ValueError
            get_db().execute(
                "INSERT INTO business_breaks(business_id,weekday,start_time,end_time) VALUES(?,?,?,?)",
                (biz["id"], weekday, start, end)
            )
            flash("Break period added.", "success")
        except (ValueError, TypeError):
            flash("Enter a valid break period.", "danger")
        return redirect(url_for("management") + "#hours")

    @app.post("/breaks/<int:break_id>/delete")
    @business_required
    def delete_break(break_id):
        biz = owned_business()
        get_db().execute("DELETE FROM business_breaks WHERE id=? AND business_id=?", (break_id, biz["id"]))
        flash("Break removed.", "success")
        return redirect(url_for("management") + "#hours")

    @app.post("/unavailable")
    @business_required
    def add_unavailable():
        biz = owned_business()
        day = request.form.get("date", "")
        reason = request.form.get("reason", "").strip()
        try:
            date.fromisoformat(day)
            get_db().execute(
                "INSERT OR REPLACE INTO unavailable_dates(business_id,date,reason) VALUES(?,?,?)",
                (biz["id"], day, reason)
            )
            flash("Unavailable date saved.", "success")
        except (ValueError, sqlite3.Error):
            flash("Please choose a valid date.", "danger")
        return redirect(url_for("management") + "#hours")

    @app.post("/unavailable/<int:item_id>/delete")
    @business_required
    def delete_unavailable(item_id):
        biz = owned_business()
        get_db().execute("DELETE FROM unavailable_dates WHERE id=? AND business_id=?", (item_id, biz["id"]))
        flash("Unavailable date removed.", "success")
        return redirect(url_for("management") + "#hours")

    @app.post("/settings")
    @business_required
    def save_settings():
        biz = owned_business()
        try:
            notice = int(request.form.get("minimum_notice", "60"))
            advance = int(request.form.get("advance_booking_days", "60"))
            cancellation = 1 if request.form.get("cancellation_enabled") == "on" else 0
            if notice < 0 or notice > 10080 or advance < 1 or advance > 365:
                raise ValueError
            get_db().execute(
                "UPDATE booking_settings SET minimum_notice=?,advance_booking_days=?,cancellation_enabled=? WHERE business_id=?",
                (notice, advance, cancellation, biz["id"])
            )
            flash("Booking settings saved.", "success")
        except ValueError:
            flash("Enter valid booking settings.", "danger")
        return redirect(url_for("management") + "#settings")

    @app.get("/book/<slug>")
    def booking(slug):
        biz = get_db().execute("SELECT * FROM businesses WHERE slug=?", (slug,)).fetchone()
        if not biz:
            abort(404)
        services = get_db().execute("SELECT * FROM services WHERE business_id=? AND is_active=1 ORDER BY name", (biz["id"],)).fetchall()
        return render_template("booking.html", biz=biz, services=services, today=date.today().isoformat())

    @app.get("/api/slots/<slug>")
    def api_slots(slug):
        biz = get_db().execute("SELECT * FROM businesses WHERE slug=?", (slug,)).fetchone()
        if not biz:
            return jsonify({"error": "Business not found"}), 404
        day = request.args.get("date", "")
        service_id = request.args.get("service_id", type=int)
        try:
            parsed_day = date.fromisoformat(day)
            if parsed_day < date.today():
                raise ValueError
        except ValueError:
            return jsonify({"error": "Choose a valid date."}), 400
        service = get_db().execute(
            "SELECT * FROM services WHERE id=? AND business_id=? AND is_active=1",
            (service_id, biz["id"])
        ).fetchone()
        if not service:
            return jsonify({"error": "Choose a valid service."}), 400
        return jsonify({"slots": get_slots(biz["id"], service, day)})

    @app.post("/book/<slug>")
    def create_booking(slug):
        biz = get_db().execute("SELECT * FROM businesses WHERE slug=?", (slug,)).fetchone()
        if not biz:
            abort(404)
        db = get_db()
        service_id = request.form.get("service_id", type=int)
        day = request.form.get("appointment_date", "")
        start = request.form.get("start_time", "")
        name = request.form.get("customer_name", "").strip()
        phone = request.form.get("customer_phone", "").strip()
        email = request.form.get("customer_email", "").strip()
        service = db.execute(
            "SELECT * FROM services WHERE id=? AND business_id=? AND is_active=1",
            (service_id, biz["id"])
        ).fetchone()
        try:
            day_obj = date.fromisoformat(day)
            start_obj = parse_hhmm(start)
            if not service or not name or len(name) > 100 or not re.fullmatch(r"[0-9+()\\-\\s]{7,20}", phone):
                raise ValueError
            if email and ("@" not in email or len(email) > 150):
                raise ValueError
        except (ValueError, TypeError):
            flash("Please complete the form with valid details.", "danger")
            return redirect(url_for("booking", slug=slug))
        duration = int(service["duration"])
        buffer_time = int(service["buffer_time"])
        start_min = minutes(start_obj)
        end_min = start_min + duration
        block_end = end_min + buffer_time
        if end_min > 24 * 60 or block_end > 24 * 60:
            flash("That appointment time is invalid.", "danger")
            return redirect(url_for("booking", slug=slug))
        reference = "ILO-" + secrets.token_hex(4).upper()
        token = secrets.token_urlsafe(32)
        # Serialize competing booking attempts. Recheck availability inside the write transaction.
        try:
            db.execute("BEGIN IMMEDIATE")
            fresh_service = db.execute(
                "SELECT * FROM services WHERE id=? AND business_id=? AND is_active=1",
                (service_id, biz["id"])
            ).fetchone()
            if not fresh_service or start not in get_slots(biz["id"], fresh_service, day):
                db.execute("ROLLBACK")
                flash("That time slot is no longer available. Please choose another time.", "warning")
                return redirect(url_for("booking", slug=slug))
            db.execute(
                """INSERT INTO appointments(
                    business_id,service_id,service_name,service_price,service_duration,service_buffer,
                    customer_name,customer_phone,customer_email,appointment_date,start_time,end_time,
                    block_end_time,booking_reference,management_token_hash
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (biz["id"], service_id, service["name"], service["price"], duration, buffer_time,
                 name, phone, email, day, start, hhmm(end_min), hhmm(block_end), reference, token_hash(token))
            )
            appointment_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            db.execute("COMMIT")
        except sqlite3.IntegrityError:
            db.execute("ROLLBACK")
            flash("We couldn't reserve that slot. Please choose another.", "warning")
            return redirect(url_for("booking", slug=slug))
        except sqlite3.OperationalError:
            try:
                db.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            flash("The booking system is busy. Please try again.", "warning")
            return redirect(url_for("booking", slug=slug))
        return redirect(url_for("confirmation", reference=reference, token=token))

    @app.get("/confirmation/<reference>")
    def confirmation(reference):
        token = request.args.get("token", "")
        row = get_db().execute(
            """SELECT a.*,b.name AS business_name,b.phone AS business_phone,b.slug
               FROM appointments a JOIN businesses b ON b.id=a.business_id
               WHERE a.booking_reference=? AND a.management_token_hash=?""",
            (reference, token_hash(token))
        ).fetchone()
        if not row:
            abort(404)
        return render_template("confirmation.html", appointment=row, token=token)

    @app.route("/manage/<token>", methods=["GET", "POST"])
    def manage_booking(token):
        digest = token_hash(token)
        row = get_db().execute(
            """SELECT a.*,b.name AS business_name,b.phone AS business_phone,b.slug,
                      bs.cancellation_enabled
               FROM appointments a JOIN businesses b ON b.id=a.business_id
               LEFT JOIN booking_settings bs ON bs.business_id=b.id
               WHERE a.management_token_hash=?""", (digest,)
        ).fetchone()
        if not row:
            abort(404)
        if request.method == "POST":
            action = request.form.get("action")
            if action == "cancel":
                if not row["cancellation_enabled"]:
                    flash("Online cancellation is disabled for this business.", "warning")
                elif row["status"] != "confirmed":
                    flash("Only confirmed appointments can be cancelled.", "warning")
                else:
                    get_db().execute("UPDATE appointments SET status='cancelled' WHERE id=?", (row["id"],))
                    flash("Your appointment has been cancelled. The slot is available again.", "success")
                return redirect(url_for("manage_booking", token=token))
            if action == "reschedule":
                day = request.form.get("appointment_date", "")
                start = request.form.get("start_time", "")
                try:
                    date.fromisoformat(day)
                    service = get_db().execute("SELECT duration,buffer_time FROM services WHERE id=?", (row["service_id"],)).fetchone()
                    if not service or row["status"] != "confirmed":
                        raise ValueError
                    db = get_db()
                    db.execute("BEGIN IMMEDIATE")
                    # Temporarily ignore this appointment when checking its new slot.
                    db.execute("UPDATE appointments SET status='cancelled' WHERE id=?", (row["id"],))
                    slots = get_slots(row["business_id"], service, day)
                    if start not in slots:
                        db.execute("UPDATE appointments SET status='confirmed' WHERE id=?", (row["id"],))
                        db.execute("COMMIT")
                        flash("That new time is no longer available.", "warning")
                    else:
                        dur = int(service["duration"])
                        buf = int(service["buffer_time"])
                        s = minutes(parse_hhmm(start))
                        db.execute(
                            """UPDATE appointments SET appointment_date=?,start_time=?,end_time=?,block_end_time=?,status='confirmed'
                               WHERE id=?""",
                            (day, start, hhmm(s+dur), hhmm(s+dur+buf), row["id"])
                        )
                        db.execute("COMMIT")
                        flash("Appointment rescheduled successfully.", "success")
                except (ValueError, sqlite3.Error):
                    try:
                        db.execute("ROLLBACK")
                    except Exception:
                        pass
                    flash("Please choose a valid available date and time.", "danger")
                return redirect(url_for("manage_booking", token=token))
        return render_template("manage_booking.html", appointment=row, token=token, today=date.today().isoformat())

    @app.get("/api/manage-slots/<token>")
    def api_manage_slots(token):
        row = get_db().execute("SELECT * FROM appointments WHERE management_token_hash=?", (token_hash(token),)).fetchone()
        if not row or row["status"] != "confirmed":
            return jsonify({"error": "Booking cannot be changed."}), 400
        try:
            requested_day = date.fromisoformat(request.args.get("date", ""))
            if requested_day < date.today():
                raise ValueError
        except ValueError:
            return jsonify({"error": "Choose a valid future date."}), 400
        service = get_db().execute("SELECT duration,buffer_time FROM services WHERE id=?", (row["service_id"],)).fetchone()
        if not service:
            return jsonify({"error": "Service unavailable."}), 400
        # Temporarily remove current booking from collision set within this request's read context.
        db = get_db()
        db.execute("BEGIN")
        db.execute("UPDATE appointments SET status='cancelled' WHERE id=?", (row["id"],))
        slots = get_slots(row["business_id"], service, request.args.get("date", ""))
        db.execute("ROLLBACK")
        return jsonify({"slots": slots})

    @app.post("/appointments/<int:appointment_id>/status")
    @business_required
    def update_appointment_status(appointment_id):
        biz = owned_business()
        status = request.form.get("status")
        if status not in ("completed", "no_show", "cancelled"):
            abort(400)
        cur = get_db().execute(
            "UPDATE appointments SET status=? WHERE id=? AND business_id=? AND status='confirmed'",
            (status, appointment_id, biz["id"])
        )
        if cur.rowcount:
            flash("Appointment status updated.", "success")
        else:
            flash("Appointment could not be updated.", "warning")
        return redirect(url_for("dashboard"))

    @app.get("/calendar")
    @business_required
    def calendar():
        biz = owned_business()
        rows = get_db().execute(
            "SELECT * FROM appointments WHERE business_id=? ORDER BY appointment_date,start_time",
            (biz["id"],)
        ).fetchall()
        return render_template("calendar.html", biz=biz, appointments=rows)

    @app.get("/profile")
    @business_required
    def profile():
        return render_template("profile.html", biz=owned_business())

    @app.post("/profile")
    @business_required
    def update_profile():
        biz = owned_business()
        fields = [request.form.get(k, "").strip() for k in ("name", "category", "description", "phone", "email", "address")]
        if not fields[0] or not fields[1] or not fields[3]:
            flash("Business name, category and phone are required.", "danger")
        else:
            get_db().execute(
                "UPDATE businesses SET name=?,category=?,description=?,phone=?,email=?,address=? WHERE id=?",
                (*fields, biz["id"])
            )
            flash("Business profile updated. Your public URL remains unchanged.", "success")
        return redirect(url_for("profile"))

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("404.html"), 404

    @app.errorhandler(413)
    def too_large(_error):
        return "Upload is too large (maximum 5 MB).", 413

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1")
