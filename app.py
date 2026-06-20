from __future__ import annotations

import os
import time
import threading
import requests
from core.tod_calc import A350TODCalculator
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

# ATC AI is intentionally disabled for the current project scope.
# Keep the STT code in core/stt_engine.py for future development,
# but do not start microphone / Whisper processing in this version.
ENABLE_ATC_AI = os.getenv("ENABLE_ATC_AI", "false").lower() == "true"

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
    "latitude": 0.0,
    "longitude": 0.0,
    "flight_phase": "SIM NOT CONNECTED",
    "flight_progress": 0,
    "distance_to_dest_nm": "---",
}


atc_state = {
    "enabled": False,
    "status": "ROADMAP",
    "latest": "AI ATC Assistant planned for future versions.",
    "history": [
        {"time": "Future", "text": "Real-time VATSIM ATC transcription"},
        {"time": "Future", "text": "AI clearance interpretation"},
        {"time": "Future", "text": "Altitude, heading, speed and squawk parsing"},
        {"time": "Future", "text": "Electronic Copilot integration"},
    ],
}

AIRPORT_COORDS = {
    "RCTP": (25.0797, 121.2328),
    "VHHH": (22.3080, 113.9185),
    "RJTT": (35.5494, 139.7798),
    "RJAA": (35.7647, 140.3864),
    "RJBB": (34.4347, 135.2440),
    "ZBAA": (40.0801, 116.5846),
    "ZSPD": (31.1443, 121.8083),
    "ZUCK": (29.7192, 106.6417),
    "KSEA": (47.4502, -122.3088),
    "KLAX": (33.9416, -118.4085),
    "KSFO": (37.6213, -122.3790),
    "EGLL": (51.4700, -0.4543),
    "EDDF": (50.0379, 8.5622),
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

def detect_flight_phase(altitude, ground_speed, vertical_speed):
    if not sim_state["connected"]:
        return "SIM NOT CONNECTED"

    if altitude < 50 and ground_speed < 1:
        return "AT GATE / PREFLIGHT"

    if altitude < 50 and 1 <= ground_speed < 10:
        return "PUSHING BACK"

    if altitude < 50 and 10 <= ground_speed < 40:
        return "TAXIING"

    if altitude < 1500 and ground_speed >= 40 and vertical_speed > 300:
        return "DEPARTING"

    if altitude >= 1500 and vertical_speed > 500:
        return "CLIMBING"

    if altitude >= 28000 and abs(vertical_speed) < 300:
        return "CRUISING"

    if altitude > 3000 and vertical_speed < -500:
        return "DESCENDING"

    if altitude <= 3000 and ground_speed > 80:
        return "APPROACH"

    if altitude < 50 and ground_speed >= 5:
        return "LANDED / TAXIING"

    return "IN FLIGHT"

def calculate_flight_progress(origin, destination, current_lat, current_lon):
    origin_coord = AIRPORT_COORDS.get(origin)
    dest_coord = AIRPORT_COORDS.get(destination)

    if not origin_coord or not dest_coord:
        return 0, "---"

    if abs(current_lat) < 0.01 and abs(current_lon) < 0.01:
        return 0, "---"

    calc = A350TODCalculator()

    total_distance = calc._haversine(
        origin_coord[0], origin_coord[1],
        dest_coord[0], dest_coord[1]
    )

    distance_to_dest = calc._haversine(
        current_lat, current_lon,
        dest_coord[0], dest_coord[1]
    )

    if total_distance <= 0:
        return 0, "---"

    progress = ((total_distance - distance_to_dest) / total_distance) * 100
    progress = max(0, min(100, round(progress)))

    return progress, round(distance_to_dest, 1)

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

                altitude = float(aq.get("INDICATED_ALTITUDE") or aq.get("PLANE_ALTITUDE") or 0)
                gs = float(aq.get("GROUND_VELOCITY") or 0)
                vs = float(aq.get("VERTICAL_SPEED") or 0)
                hdg = float(aq.get("PLANE_HEADING_DEGREES_TRUE") or 0)

                lat = float(
                    aq.get("PLANE_LATITUDE")
                    or aq.get("GPS_POSITION_LAT")
                    or 0
                )  

                lon = float(
                    aq.get("PLANE_LONGITUDE")
                    or aq.get("GPS_POSITION_LON")
                    or 0
                )

                try:
                    squawk_raw = aq.get("TRANSPONDER_CODE:1")

                    if squawk_raw:
                        squawk_int = int(float(squawk_raw))

                        squawk = (
                             f"{(squawk_int >> 12) & 0xF}"
                            f"{(squawk_int >> 8) & 0xF}"
                            f"{(squawk_int >> 4) & 0xF}"
                            f"{squawk_int & 0xF}"
                    )
                    else:
                        squawk = "----"
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
                    "latitude": lat,
                    "longitude": lon,
                    "flight_phase": detect_flight_phase(altitude, gs, vs),
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
    """Start ATC AI only when explicitly enabled.

    Current project version treats ATC AI as future development, so this
    function does not start microphone capture unless ENABLE_ATC_AI=true.
    """
    if not ENABLE_ATC_AI:
        atc_state["enabled"] = False
        atc_state["status"] = "ROADMAP"
        atc_state["latest"] = "AI ATC Assistant planned for future versions."
        return

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
            return render_template("login.html", error="請輸入 SimBrief Username。")

        # 先驗證 SimBrief ID 是否存在
        try:
            url = f"https://www.simbrief.com/api/xml.fetcher.php?username={sid}&json=1"
            res = requests.get(url, timeout=8)
            data = res.json()

            if not data or "error" in data or not data.get("params"):
                return render_template(
                    "login.html",
                    error="找不到這個 SimBrief ID，請確認 Username 是否正確。"
                )

        except Exception:
            return render_template(
                "login.html",
                error="無法連線到 SimBrief，請稍後再試。"
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

    tod_distance_nm = "---"
    minutes_to_tod = "---"
    required_descent_nm = "---"
    required_fpm = "---"
    flight_progress = 0
    distance_to_dest = "---"
    profile = "A350 optimized" if aircraft_supported else "Unsupported aircraft"

    if not sim_state["connected"]:
        profile = "Simulator not connected"

    elif aircraft_supported:
        if abs(sim_state["latitude"]) < 0.01 and abs(sim_state["longitude"]) < 0.01:
            profile = "Waiting for aircraft position"
        else:
            try:
                simbrief_id = current_user.simbrief_id
                url = f"https://www.simbrief.com/api/xml.fetcher.php?username={simbrief_id}&json=1"
                res = requests.get(url, timeout=5)
                data = res.json()

                origin = data.get("origin", {}).get("icao_code", "----")
                destination = data.get("destination", {}).get("icao_code", "----")

                flight_progress, distance_to_dest = calculate_flight_progress(
                    origin,
                    destination,
                    sim_state["latitude"],
                    sim_state["longitude"]
                )

                dest_coord = AIRPORT_COORDS.get(destination)

                if dest_coord:
                    dest_lat, dest_lon = dest_coord

                    calc = A350TODCalculator(target_alt=2500)

                    tod = calc.calculate_tod(
                        current_lat=sim_state["latitude"],
                        current_lon=sim_state["longitude"],
                        dest_lat=dest_lat,
                        dest_lon=dest_lon,
                        current_alt=sim_state["altitude"],
                        ground_speed=sim_state["ground_speed"],
                        wind_speed=0,
                        wind_angle=0,
                    )

                    tod_distance_nm = tod["countdown_nm"]
                    minutes_to_tod = tod["minutes_to_tod"]
                    required_descent_nm = tod["required_descent_nm"]

                    if required_descent_nm > 0 and sim_state["ground_speed"] > 0:
                        required_fpm = round(
                            max(0, sim_state["altitude"] - 2500)
                            / max(1, (required_descent_nm / sim_state["ground_speed"]) * 60)
                        )
                    else:
                        required_fpm = 0

                    profile = "A350 optimized"
                else:
                    profile = f"No airport coordinate: {destination}"

            except Exception as exc:
                profile = f"TOD error: {exc}"

    return jsonify({
        "connected": sim_state["connected"],
        "aircraft": sim_state["aircraft"],
        "aircraft_title": sim_state["aircraft_title"],
        "altitude": sim_state["altitude"],
        "ground_speed": sim_state["ground_speed"],
        "vertical_speed": sim_state["vertical_speed"],
        "heading": sim_state["heading"],
        "squawk": sim_state["squawk"],

        "flight_phase": sim_state["flight_phase"],
        "flight_progress": flight_progress if sim_state["connected"] else 0,
        "distance_to_dest_nm": distance_to_dest if sim_state["connected"] else "---",

        "tod_available": aircraft_supported,
        "tod_distance_nm": tod_distance_nm,
        "minutes_to_tod": minutes_to_tod,
        "required_descent_nm": required_descent_nm,
        "required_fpm": required_fpm,
        "profile": profile,

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

# ATC AI is future development. Do not start microphone / Whisper by default.
if ENABLE_ATC_AI:
    threading.Thread(target=start_atc_engine, daemon=True).start()
else:
    start_atc_engine()

threading.Thread(
    target=start_flight_crawler,
    args=(app, db, FlightSnapshot),
    daemon=True
).start()

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

