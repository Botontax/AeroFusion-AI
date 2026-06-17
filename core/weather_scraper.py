from __future__ import annotations

import requests

HEADERS = {
    "User-Agent": "SkyWalker/1.0 educational flight monitoring project"
}


def _fetch_raw(url: str) -> str:
    try:
        response = requests.get(url, headers=HEADERS, timeout=12)
        response.raise_for_status()

        text = response.text.strip()

        if not text:
            return "No data available."

        return text

    except Exception as exc:
        return f"Weather fetch failed: {exc}"


def get_metar(icao: str) -> str:
    icao = (icao or "").upper().strip()

    if not icao or len(icao) != 4:
        return "Invalid ICAO."

    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
    return _fetch_raw(url)


def get_taf(icao: str) -> str:
    icao = (icao or "").upper().strip()

    if not icao or len(icao) != 4:
        return "Invalid ICAO."

    url = f"https://aviationweather.gov/api/data/taf?ids={icao}&format=raw"
    return _fetch_raw(url)


def get_weather(icao: str) -> dict:
    icao = (icao or "").upper().strip()

    return {
        "icao": icao,
        "metar": get_metar(icao),
        "taf": get_taf(icao),
        "source": "NOAA AviationWeather.gov",
    }