from __future__ import annotations

import os
import time
import threading
import requests
from datetime import datetime
from sqlalchemy import func, desc
from core.flight_crawler import start_flight_crawler
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    UserMixin,
    logout_user,
    current_user,
)
from flask_sqlalchemy import SQLAlchemy

from core.weather_scraper import get_weather, get_metar

try:
    from SimConnect import SimConnect, AircraftRequests
except Exception:
    SimConnect = None
    AircraftRequests = None

try:
    from core.stt_engine import STTEngine
except Exception as exc:
    print(f"[ATC AI] STT engine unavailable: {exc}")
    STTEngine = None


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "skywalker_dev_key_2026")

database_url = os.getenv("DATABASE_URL", "sqlite:///users.db")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "sqlite:///users.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    simbrief_id = db.Column(db.String(120), unique=True, nullable=False)

class FlightSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    callsign = db.Column(db.String(32), nullable=False)
    aircraft = db.Column(db.String(32))
    origin = db.Column(db.String(8))
    destination = db.Column(db.String(8))
    altitude = db.Column(db.Integer)
    groundspeed = db.Column(db.Integer)
    heading = db.Column(db.Integer)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))


sim_state = {
    "connected": False,
    "aircraft_title": "UNKNOWN",
    "aircraft": "UNKNOWN",
    "altitude": 0,
    "ground_speed": 0,
    "vertical_speed": 0,
    "heading": "000",
    "squawk": "----",
}


atc_state = {
    "enabled": False,
    "status": "STANDBY",
    "latest": "Waiting for ATC transcript...",
    "history": [],
}


def normalize_title(raw_title) -> str:
    if isinstance(raw_title, bytes):
        return raw_title.decode("utf-8", errors="ignore")
    return str(raw_title or "UNKNOWN")


def detect_aircraft_profile(title: str) -> str:
    t = (title or "").upper()

    if "A350" in t or ("INI" in t and "350" in t):
        return "iniBuilds A350"

    return "Unsupported"


def simconnect_worker():
    if SimConnect is None or AircraftRequests is None:
        print("[SIMCONNECT] Python-SimConnect package not available.")
        return

    while True:
        try:
            sm = SimConnect()
            time.sleep(1)
            aq = AircraftRequests(sm, _time=500)

            sim_state["connected"] = True
            print("[SIMCONNECT] Connected")

            while True:
                title = normalize_title(aq.get("TITLE"))

                altitude = float(aq.get("PLANE_ALTITUDE") or 0)
                gs = float(aq.get("GROUND_VELOCITY") or 0)
                vs = float(aq.get("VERTICAL_SPEED") or 0)
                hdg = float(aq.get("PLANE_HEADING_DEGREES_TRUE") or 0)

                try:
                    squawk_raw = aq.get("TRANSPONDER_CODE:1")
                    squawk = str(squawk_raw) if squawk_raw else "----"
                except Exception:
                    squawk = "----"

                sim_state.update({
                    "connected": True,
                    "aircraft_title": title,
                    "aircraft": detect_aircraft_profile(title),
                    "altitude": round(altitude),
                    "ground_speed": round(gs),
                    "vertical_speed": round(vs),
                    "heading": f"{round(hdg) % 360:03d}",
                    "squawk": squawk,
                })

                time.sleep(1)

        except Exception as exc:
            print(f"[SIMCONNECT ERROR] {exc}")
            sim_state["connected"] = False
            sim_state["aircraft_title"] = "UNKNOWN"
            sim_state["aircraft"] = "UNKNOWN"
            time.sleep(5)


def on_atc_transcript(text: str):
    text = (text or "").strip()

    if not text:
        return

    atc_state["latest"] = text
    atc_state["status"] = "LISTENING"

    atc_state["history"].insert(0, {
        "time": time.strftime("%H:%M:%S"),
        "text": text,
    })

    atc_state["history"] = atc_state["history"][:10]

    print(f"[ATC AI] {text}")


def start_atc_engine():
    if STTEngine is None:
        atc_state["enabled"] = False
        atc_state["status"] = "STT UNAVAILABLE"
        atc_state["latest"] = "STT engine not available. Check faster-whisper / SpeechRecognition."
        return

    try:
        engine = STTEngine(callback=on_atc_transcript, my_callsign="SJX")
        engine.start_listening()

        atc_state["enabled"] = True
        atc_state["status"] = "LISTENING"
        atc_state["latest"] = "ATC AI listening via VB-CABLE device_index=1."

    except Exception as exc:
        atc_state["enabled"] = False
        atc_state["status"] = "ERROR"
        atc_state["latest"] = f"ATC AI failed: {exc}"
        print(f"[ATC AI ERROR] {exc}")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        sid = (request.form.get("simbrief_id") or "").strip()

        if not sid:
            return render_template(
                "login.html",
                error="Please enter your SimBrief username."
            )

        user = User.query.filter_by(simbrief_id=sid).first()

        if user is None:
            user = User(simbrief_id=sid)
            db.session.add(user)
            db.session.commit()

        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html", simbrief_id=current_user.simbrief_id)


@app.route("/radar")
@login_required
def radar():
    return render_template("index.html")

@app.route("/analytics")
@login_required
def analytics():
    return render_template("analytics.html", simbrief_id=current_user.simbrief_id)

_vatsim_cache = {
    "timestamp": 0.0,
    "data": {"pilots": [], "controllers": []},
}


@app.route("/api/vatsim-data")
def get_vatsim_data():
    now = time.time()

    if now - _vatsim_cache["timestamp"] < 15:
        return jsonify(_vatsim_cache["data"])

    try:
        res = requests.get("https://data.vatsim.net/v3/vatsim-data.json", timeout=8)
        res.raise_for_status()
        data = res.json()

        _vatsim_cache["timestamp"] = now
        _vatsim_cache["data"] = data

        return jsonify(data)

    except Exception as exc:
        print(f"[VATSIM ERROR] {exc}")
        return jsonify(_vatsim_cache.get("data") or {"pilots": [], "controllers": []})


@app.route("/api/vatsim-summary")
def vatsim_summary():
    data = _vatsim_cache.get("data") or {}

    if not data.get("pilots"):
        try:
            res = requests.get("https://data.vatsim.net/v3/vatsim-data.json", timeout=8)
            res.raise_for_status()
            data = res.json()

            _vatsim_cache["timestamp"] = time.time()
            _vatsim_cache["data"] = data

        except Exception:
            data = {"pilots": [], "controllers": []}

    return jsonify({
        "pilots": len(data.get("pilots", [])),
        "controllers": len(data.get("controllers", [])),
    })


@app.route("/api/simbrief-route")
@login_required
def get_simbrief_route():
    try:
        simbrief_id = current_user.simbrief_id
        url = f"https://www.simbrief.com/api/xml.fetcher.php?username={simbrief_id}&json=1"

        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()

        origin = data.get("origin", {}).get("icao_code", "----")
        destination = data.get("destination", {}).get("icao_code", "----")
        callsign = data.get("atc", {}).get("callsign", "----")
        aircraft = data.get("aircraft", {}).get("icaocode", "A350")
        route = data.get("general", {}).get("route", "")

        return jsonify({
            "ok": True,
            "simbrief_id": simbrief_id,
            "origin": origin,
            "destination": destination,
            "callsign": callsign,
            "aircraft": aircraft,
            "route": route,
        })

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
            "origin": "----",
            "destination": "----",
            "callsign": "----",
            "aircraft": "A350",
            "route": "Unable to load SimBrief route.",
        })


@app.route("/api/dashboard")
@login_required
def dashboard_data():
    aircraft_supported = sim_state["aircraft"] == "iniBuilds A350"

    return jsonify({
        "connected": sim_state["connected"],
        "aircraft": sim_state["aircraft"],
        "aircraft_title": sim_state["aircraft_title"],
        "altitude": sim_state["altitude"],
        "ground_speed": sim_state["ground_speed"],
        "vertical_speed": sim_state["vertical_speed"],
        "heading": sim_state["heading"],
        "squawk": sim_state["squawk"],

        "tod_available": aircraft_supported,
        "tod_distance_nm": 0 if aircraft_supported else "---",
        "minutes_to_tod": 0 if aircraft_supported else "---",
        "required_descent_nm": 0 if aircraft_supported else "---",
        "required_fpm": 0 if aircraft_supported else "---",
        "profile": "A350 optimized" if aircraft_supported else "Unsupported aircraft",

        "atc_status": atc_state["status"],
        "atc_latest": atc_state["latest"],
        "atc_history": atc_state["history"],
    })


@app.route("/api/metar/<icao>")
def get_metar_api(icao: str):
    return jsonify({
        "icao": icao.upper(),
        "metar": get_metar(icao),
    })


@app.route("/api/weather/<icao>")
def get_weather_api(icao: str):
    return jsonify(get_weather(icao))


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


threading.Thread(target=simconnect_worker, daemon=True).start()
threading.Thread(target=start_atc_engine, daemon=True).start()
threading.Thread(
    target=start_flight_crawler,
    args=(app, db, FlightSnapshot),
    daemon=True
).start()

@login_required
def analytics_summary():
    total = FlightSnapshot.query.count()

@app.route("/api/analytics/summary")
@login_required
def analytics_summary():
    total = FlightSnapshot.query.count()

    top_aircraft = (
        db.session.query(
            FlightSnapshot.aircraft,
            func.count(FlightSnapshot.id).label("count")
        )
        .filter(FlightSnapshot.aircraft != None)
        .group_by(FlightSnapshot.aircraft)
        .order_by(desc("count"))
        .limit(10)
        .all()
    )

    top_routes = (
        db.session.query(
            FlightSnapshot.origin,
            FlightSnapshot.destination,
            func.count(FlightSnapshot.id).label("count")
        )
        .filter(FlightSnapshot.origin != "----")
        .filter(FlightSnapshot.destination != "----")
        .group_by(FlightSnapshot.origin, FlightSnapshot.destination)
        .order_by(desc("count"))
        .limit(10)
        .all()
    )

    avg_altitude = (
        db.session.query(
            FlightSnapshot.aircraft,
            func.avg(FlightSnapshot.altitude).label("avg_alt")
        )
        .filter(FlightSnapshot.aircraft != None)
        .filter(FlightSnapshot.altitude > 10000)
        .group_by(FlightSnapshot.aircraft)
        .order_by(desc("avg_alt"))
        .limit(10)
        .all()
    )

    return jsonify({
        "total_snapshots": total,
        "top_aircraft": [
            {"aircraft": a or "UNKNOWN", "count": c}
            for a, c in top_aircraft
        ],
        "top_routes": [
            {"route": f"{o} -> {d}", "count": c}
            for o, d, c in top_routes
        ],
        "avg_altitude": [
            {"aircraft": a or "UNKNOWN", "avg_altitude": round(avg or 0)}
            for a, avg in avg_altitude
        ],
    })

if __name__ == "__main__":
    app.run(debug=True, threaded=True, port=5000)

