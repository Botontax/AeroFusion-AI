async function fetchJson(url) {
    const res = await fetch(url);
    return await res.json();
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.innerText = value;
}

async function loadAirportWeather(icao, prefix) {
    if (!icao || icao === "----") {
        setText(`${prefix}-metar`, "No airport selected.");
        setText(`${prefix}-taf`, "No airport selected.");
        return;
    }

    try {
        const data = await fetchJson(`/api/weather/${icao}`);

        setText(`${prefix}-metar`, data.metar || "No METAR available.");
        setText(`${prefix}-taf`, data.taf || "No TAF available.");

    } catch (err) {
        console.error(`Weather fetch failed for ${icao}`, err);

        setText(`${prefix}-metar`, "Weather fetch failed.");
        setText(`${prefix}-taf`, "Weather fetch failed.");
    }
}

async function loadManualWeather() {
    const icao = document.getElementById("weather-icao").value.trim().toUpperCase();

    if (!icao || icao.length !== 4) {
        setText("manual-weather-result", "Please enter a valid ICAO code.");
        return;
    }

    setText("manual-weather-result", "Loading weather...");

    try {
        const data = await fetchJson(`/api/weather/${icao}`);

        setText(
            "manual-weather-result",
            `${icao}\n\nMETAR:\n${data.metar || "No METAR available."}\n\nTAF:\n${data.taf || "No TAF available."}`
        );

    } catch (err) {
        console.error("Manual weather failed:", err);
        setText("manual-weather-result", "Manual weather fetch failed.");
    }
}

async function loadSimBriefRoute() {
    try {
        const data = await fetchJson("/api/simbrief-route");

        const origin = data.origin || "----";
        const destination = data.destination || "----";

        setText("dash-origin", origin);
        setText("dash-destination", destination);
        setText("dash-callsign", data.callsign || "----");

        // 先顯示 SimBrief aircraft，之後如果 SimConnect 有連上會被實際機型覆蓋
        setText("dash-aircraft", data.aircraft || "A350");

        setText("dash-route", data.route || "No active SimBrief flight plan loaded.");

        setText("weather-origin-title", origin);
        setText("weather-destination-title", destination);

        const weatherInput = document.getElementById("weather-icao");
        if (weatherInput) {
            weatherInput.value = destination !== "----" ? destination : "";
        }

        await loadAirportWeather(origin, "dash-origin");
        await loadAirportWeather(destination, "dash-destination");

    } catch (err) {
        console.error("SimBrief route load failed:", err);

        setText("dash-origin", "----");
        setText("dash-destination", "----");
        setText("dash-route", "SimBrief fetch failed.");
    }
}

async function loadVatsimSummary() {
    try {
        const data = await fetchJson("/api/vatsim-summary");

        setText("dash-pilots-online", data.pilots ?? "---");
        setText("dash-controllers-online", data.controllers ?? "---");

    } catch (err) {
        console.error("VATSIM summary failed:", err);
    }
}

async function loadDashboardData() {
    try {
        const data = await fetchJson("/api/dashboard");

        const statusEl = document.getElementById("dash-sim-status");

        if (statusEl) {
            statusEl.innerText = data.connected ? "CONNECTED" : "SIM NOT CONNECTED";
            statusEl.className = data.connected ? "status-big online" : "status-big standby";
        }

        setText("dash-alt", `${data.altitude || 0} FT`);
        setText("dash-gs", `${data.ground_speed || 0} KT`);
        setText("dash-vs", `${data.vertical_speed || 0} FPM`);
        setText("dash-hdg", `${data.heading || "000"}°`);
        setText("dash-squawk", data.squawk || "----");

        setText("dash-tod-available", data.tod_available ? "A350 READY" : "UNSUPPORTED");
        setText("dash-tod-distance", `${data.tod_distance_nm ?? "---"} NM`);
        setText("dash-tod-time", `${data.minutes_to_tod ?? "---"} MIN`);
        setText("dash-req-dist", `${data.required_descent_nm ?? "---"} NM`);
        setText("dash-req-fpm", `${data.required_fpm ?? "---"} FPM`);
        setText("dash-profile", data.profile || "Unsupported aircraft");

        if (data.connected) {
            setText("dash-aircraft", data.aircraft_title || data.aircraft || "UNKNOWN");
        }

        setText("dash-atc-status", data.atc_status || "STANDBY");
        setText("dash-atc-latest", data.atc_latest || "Waiting for ATC transcript...");

        const historyBox = document.getElementById("dash-atc-history");
        if (historyBox && Array.isArray(data.atc_history)) {
            if (data.atc_history.length === 0) {
                historyBox.innerHTML = "> System ready.";
            } else {
                historyBox.innerHTML = data.atc_history
                    .map(item => `> [${item.time}] ${item.text}`)
                    .join("<br>");
            }
        }

    } catch (err) {
        console.error("Dashboard data failed:", err);
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    await loadSimBriefRoute();
    await loadVatsimSummary();
    await loadDashboardData();

    setInterval(loadVatsimSummary, 30000);
    setInterval(loadDashboardData, 1000);
});