SkyWalker v5 Dashboard Patch

Files included:
- app.py: replace your current app.py
- templates/dashboard.html: add this new file
- static/js/dashboard.js: add this new file
- static/css/dashboard_additions.css: append this file content to your existing static/css/style.css

Keep your existing:
- templates/index.html
- templates/login.html
- static/js/app.js
- core/weather_scraper.py

Routes after patch:
- /        -> Dashboard
- /radar   -> VATSIM Radar map
- /login   -> Login
- /api/dashboard -> Dashboard data placeholder
- /api/vatsim-summary -> Dashboard VATSIM summary
- /api/vatsim-data -> Radar data
- /api/weather/<icao> -> METAR/TAF
