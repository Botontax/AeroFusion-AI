const map = L.map('map', { zoomControl: false }).setView([25.0, 121.5], 6);
L.control.zoom({ position: 'bottomleft' }).addTo(map);
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap & CartoDB'
}).addTo(map);

const markers = {};
const latestPilots = {};

function safeText(value, fallback = '---') {
    if (value === undefined || value === null || value === '') return fallback;
    return value;
}

function parseAircraftCode(p) {
    const fp = p.flight_plan || {};
    const raw = fp.aircraft || p.aircraft || '';
    return raw.toString().split('/')[0].trim().toUpperCase() || 'UNK';
}

function isQuadEngine(code) {
    return ['A340', 'A380', 'B747', 'B748', 'C5', 'A124'].some(prefix => code.startsWith(prefix));
}

// 保留目前效果好的 SVG 飛機外型：機頭朝上，整個容器依 heading 旋轉。
function getAircraftIcon(aircraftCode, heading) {
    const code = (aircraftCode || '').toString().toUpperCase();
    const quad = isQuadEngine(code);
    const engineSvg = quad
        ? `<circle cx="10" cy="18" r="2.2" fill="#f39c12"/><circle cx="15" cy="18" r="2.2" fill="#f39c12"/><circle cx="29" cy="18" r="2.2" fill="#f39c12"/><circle cx="34" cy="18" r="2.2" fill="#f39c12"/>`
        : `<circle cx="13" cy="18" r="2.4" fill="#f39c12"/><circle cx="31" cy="18" r="2.4" fill="#f39c12"/>`;

    const iconHtml = `
        <div class="aircraft-wrap" style="transform: rotate(${Number(heading || 0)}deg);">
            <svg class="aircraft-svg" viewBox="0 0 44 44" xmlns="http://www.w3.org/2000/svg">
                <path d="M22 3 C19.8 7.8 19.1 14.4 19.1 22.5 L19.1 34.5 L15.2 39.5 L17.2 40.8 L22 37.8 L26.8 40.8 L28.8 39.5 L24.9 34.5 L24.9 22.5 C24.9 14.4 24.2 7.8 22 3Z" fill="#ecf0f1" stroke="#0b1117" stroke-width="1.2"/>
                <path d="M6 21 L19.4 16.8 L20.5 21.6 L7.2 26.2 Z" fill="#3498db" stroke="#0b1117" stroke-width="1"/>
                <path d="M38 21 L24.6 16.8 L23.5 21.6 L36.8 26.2 Z" fill="#3498db" stroke="#0b1117" stroke-width="1"/>
                <path d="M16.5 33.2 L21 30.7 L21.5 34.4 L18.2 37.1 Z" fill="#3498db" stroke="#0b1117" stroke-width="0.8"/>
                <path d="M27.5 33.2 L23 30.7 L22.5 34.4 L25.8 37.1 Z" fill="#3498db" stroke="#0b1117" stroke-width="0.8"/>
                <line x1="22" y1="5" x2="22" y2="36" stroke="#95a5a6" stroke-width="0.8" opacity="0.65"/>
                ${engineSvg}
            </svg>
        </div>`;

    return L.divIcon({
        html: iconHtml,
        className: 'aircraft-marker',
        iconSize: [42, 42],
        iconAnchor: [21, 21]
    });
}

function formatNumber(n) {
    const value = Number(n || 0);
    return Number.isFinite(value) ? value.toLocaleString() : '0';
}

function updateFlights() {
    fetch('/api/vatsim-data')
        .then(res => res.json())
        .then(data => {
            const active = new Set();
            const pilots = data.pilots || [];
            document.getElementById('radar-status').innerText = `${pilots.length} VATSIM pilots`;

            pilots.forEach(p => {
                if (typeof p.latitude !== 'number' || typeof p.longitude !== 'number') return;

                const callsign = p.callsign;
                active.add(callsign);
                latestPilots[callsign] = p;

                const aircraftCode = parseAircraftCode(p);
                const latLng = [p.latitude, p.longitude];

                if (!markers[callsign]) {
                    markers[callsign] = L.marker(latLng, {
                        icon: getAircraftIcon(aircraftCode, p.heading)
                    }).addTo(map);

                    markers[callsign].bindTooltip(callsign, {
                        permanent: true,
                        direction: 'bottom',
                        offset: [0, 18],
                        className: 'callsign-label'
                    });

                    markers[callsign].on('click', () => showPanel(latestPilots[callsign]));
                } else {
                    markers[callsign].setLatLng(latLng);
                    markers[callsign].setIcon(getAircraftIcon(aircraftCode, p.heading));
                }
            });

            Object.keys(markers).forEach(callsign => {
                if (!active.has(callsign)) {
                    map.removeLayer(markers[callsign]);
                    delete markers[callsign];
                    delete latestPilots[callsign];
                }
            });
        })
        .catch(err => {
            console.error('VATSIM fetch failed:', err);
            document.getElementById('radar-status').innerText = 'VATSIM fetch failed';
        });
}

function showPanel(p) {
    if (!p) return;

    const fp = p.flight_plan || {};
    const aircraftCode = parseAircraftCode(p);
    const dep = safeText(fp.departure);
    const arr = safeText(fp.arrival);
    const route = safeText(fp.route, 'No route available');

    document.getElementById('info-panel').style.display = 'block';
    document.getElementById('panel-callsign').innerText = p.callsign;

    document.getElementById('panel-content').innerHTML = `
        <div class="card">
            <div class="route-section">
                <div>${dep}</div>
                <div class="route-arrow">→</div>
                <div>${arr}</div>
            </div>
        </div>

        <div class="card">
            <div class="row-group">
                <div class="kv"><div class="label">GS</div><div class="value">${safeText(p.groundspeed, 0)} kt</div></div>
                <div class="kv"><div class="label">Alt</div><div class="value">${formatNumber(p.altitude)} ft</div></div>
                <div class="kv"><div class="label">Hdg</div><div class="value">${safeText(p.heading, 0)}°</div></div>
            </div>
        </div>

        <div class="card">
            <div class="row-group"><span class="label">Aircraft</span><span class="value">${aircraftCode}</span></div>
            <div class="row-group"><span class="label">Squawk</span><span class="value">${safeText(p.transponder, 'N/A')}</span></div>
            <div class="row-group"><span class="label">CID</span><span class="value">${safeText(p.cid, 'N/A')}</span></div>
        </div>

        <div class="card">
            <div class="card-title">Route</div>
            <div class="mono">${route}</div>
        </div>

        <div class="card weather" id="weather-card">
            <div class="card-title">Destination Weather</div>
            <div class="mono muted">Loading ${arr} METAR / TAF...</div>
        </div>
    `;

    loadWeather(arr);
}

function loadWeather(icao) {
    const card = document.getElementById('weather-card');

    if (!card || !icao || icao === '---') {
        if (card) {
            card.innerHTML = '<div class="card-title">Destination Weather</div><div class="mono muted">No destination available</div>';
        }
        return;
    }

    fetch(`/api/weather/${icao}`)
        .then(res => res.json())
        .then(w => {
            card.innerHTML = `
                <div class="card-title">Destination Weather - ${safeText(w.icao, icao)}</div>
                <div class="mono"><b>METAR</b>\n${safeText(w.metar, 'No METAR')}\n\n<b>TAF</b>\n${safeText(w.taf, 'No TAF')}\n\n<span class="muted">Source: ${safeText(w.source, 'Unknown')}</span></div>
            `;
        })
        .catch(() => {
            card.innerHTML = `<div class="card-title">Destination Weather - ${icao}</div><div class="mono muted">Weather fetch failed</div>`;
        });
}

updateFlights();
setInterval(updateFlights, 15000);
