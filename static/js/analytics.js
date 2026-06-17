async function fetchJson(url) {
    const res = await fetch(url);
    return await res.json();
}

function renderList(id, items, formatter) {
    const el = document.getElementById(id);

    if (!items || items.length === 0) {
        el.innerHTML = `<div class="muted">No data collected yet.</div>`;
        return;
    }

    el.innerHTML = items.map(formatter).join("");
}

async function loadAnalytics() {
    try {
        const data = await fetchJson("/api/analytics/summary");

        document.getElementById("total-snapshots").innerText =
            data.total_snapshots.toLocaleString();

        renderList("top-aircraft", data.top_aircraft, item => `
            <div class="analytics-row">
                <span>${item.aircraft}</span>
                <strong>${item.count}</strong>
            </div>
        `);

        renderList("top-routes", data.top_routes, item => `
            <div class="analytics-row">
                <span>${item.route}</span>
                <strong>${item.count}</strong>
            </div>
        `);

        renderList("avg-altitude", data.avg_altitude, item => `
            <div class="analytics-row">
                <span>${item.aircraft}</span>
                <strong>${item.avg_altitude.toLocaleString()} FT</strong>
            </div>
        `);

    } catch (err) {
        console.error("Analytics load failed:", err);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadAnalytics();
    setInterval(loadAnalytics, 30000);
});