import time
import requests

VATSIM_URL = "https://data.vatsim.net/v3/vatsim-data.json"


def start_flight_crawler(app, db, FlightSnapshot, interval_seconds=300):
    print("[CRAWLER] VATSIM flight crawler started.")

    while True:
        try:
            res = requests.get(VATSIM_URL, timeout=10)
            res.raise_for_status()
            data = res.json()

            pilots = data.get("pilots", [])
            saved = 0

            with app.app_context():
                for p in pilots:
                    fp = p.get("flight_plan") or {}

                    aircraft_raw = fp.get("aircraft") or ""
                    aircraft = aircraft_raw.split("/")[0] if aircraft_raw else "UNKNOWN"

                    snap = FlightSnapshot(
                        callsign=p.get("callsign", "UNKNOWN"),
                        aircraft=aircraft,
                        origin=fp.get("departure") or "----",
                        destination=fp.get("arrival") or "----",
                        altitude=int(p.get("altitude") or 0),
                        groundspeed=int(p.get("groundspeed") or 0),
                        heading=int(p.get("heading") or 0),
                        latitude=float(p.get("latitude") or 0),
                        longitude=float(p.get("longitude") or 0),
                    )

                    db.session.add(snap)
                    saved += 1

                db.session.commit()

            print(f"[CRAWLER] Saved {saved} flight snapshots.")

        except Exception as exc:
            print(f"[CRAWLER ERROR] {exc}")

        time.sleep(interval_seconds)