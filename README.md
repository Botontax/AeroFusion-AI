# AeroFusion AI：智慧飛航營運與即時監控平台

## 一、專題簡介

**AeroFusion AI** 是一套專為 Microsoft Flight Simulator（MSFS）與 VATSIM 網路飛行環境所設計的智慧飛航營運平台。系統以 Flask 作為後端核心，整合 SimBrief 飛行計畫、MSFS SimConnect 即時飛機資料、VATSIM 即時航機資料、天氣資訊、A350 TOD 計算器、飛行階段判斷與航班資料分析功能，提供使用者一個集中式的飛航資訊監控介面。

本系統希望解決虛擬飛行玩家在進行 IFR、長程航班或 VATSIM 網路飛行時，需要同時開啟多個網站與工具的問題。透過 AeroFusion AI，使用者可以在單一 Dashboard 中查看飛行計畫、目前飛機狀態、VATSIM 線上航機、天氣資訊、TOD 下降點與歷史飛行資料分析。

---

## 二、專題動機

在虛擬飛行過程中，玩家通常需要同時使用多個外部工具，例如 SimBrief、VATSIM Radar、天氣查詢網站、航圖工具、飛行紀錄工具或其他第三方飛行監控平台。這些工具雖然功能完整，但也造成資訊分散、操作複雜與系統資源消耗增加的問題。

特別是在長程飛行（Long Haul Flight）中，玩家可能會長時間離開電腦，例如進行跨洋航線或洲際航班時，飛行時間可能長達 6 到 12 小時以上。在這種情況下，玩家仍然需要能夠快速掌握目前飛機狀態，例如高度、地速、垂直速度、航向、Squawk、距離目的地、飛行階段與 TOD 狀態。

因此，本專題希望建立一個整合式飛航監控平台，讓使用者即使不長時間盯著 MSFS 畫面，也可以透過本網站快速確認目前飛行狀況。

此外，部分飛行輔助平台或進階功能可能需要訂閱或付費使用，例如航班追蹤、飛行紀錄、進階地圖或營運分析功能。AeroFusion AI 嘗試以開源專題形式實作基礎飛航監控、VATSIM Radar、資料分析與即時狀態顯示，讓使用者能以較低成本獲得一個可自行部署、可擴充、可客製化的飛航營運中心。

---

## 三、專題目標

本專題主要目標如下：

1. 建立一套基於 Flask 的飛航資訊整合平台。
2. 串接 SimBrief API，讀取使用者目前的飛行計畫。
3. 透過 SimConnect 取得 MSFS 中的即時飛機狀態。
4. 整合 VATSIM API，取得線上航機與管制員資料。
5. 建立自製 VATSIM Radar 頁面，顯示即時線上航機位置。
6. 建立 A350 專用 Top of Descent 計算器。
7. 建立 Flight Phase Detection，判斷目前飛行階段。
8. 建立 Flight Progress Bar，顯示航班目前完成進度。
9. 建立 Weather Module，顯示起飛與抵達機場 METAR / TAF。
10. 建立 Analytics 頁面，分析 VATSIM 歷史航機資料。
11. 建立本機部署架構，並透過 Cloudflare Tunnel 提供安全的遠端存取能力。
12. 規劃 AI ATC Assistant 作為未來開發方向。

---

## 四、系統功能

### 1. SimBrief Flight Plan Integration

系統登入時，使用者輸入 SimBrief Username，後端會透過 SimBrief API 取得目前的飛行計畫資料，並顯示於 Dashboard。

包含資料：

* 起飛機場
* 抵達機場
* Callsign
* Aircraft ICAO Code
* Route
* SimBrief User ID

此功能讓使用者不需要另外開啟 SimBrief 網頁，即可在 AeroFusion AI 內查看目前航班資訊。

---

### 2. MSFS SimConnect Status

系統透過 Python SimConnect 與 Microsoft Flight Simulator 連線，即時取得使用者飛機狀態。

顯示資料包含：

* ALT：目前高度
* GS：地速
* VS：垂直速度
* HDG：航向
* Squawk：電碼
* Aircraft Title：目前使用機型
* Connection Status：是否連線至模擬器

此功能可讓使用者在不切換回 MSFS 畫面的情況下，快速掌握飛機目前狀態。

---

### 3. Flight Phase Detection

AeroFusion AI 會根據高度、地速與垂直速度，自動判斷目前飛行階段。

目前支援判斷：

* At Gate / Preflight
* Pushing Back
* Taxiing
* Departing
* Climbing
* Cruising
* Descending
* Approach
* Landed / Taxiing
* In Flight
* Simulator Not Connected

此功能讓 Dashboard 不只是顯示原始數據，而是進一步將飛機狀態轉換成更容易理解的飛行階段。

---

### 4. Flight Progress Tracking

系統透過 SimBrief 航班資料取得起飛與抵達機場，再根據 SimConnect 取得的目前飛機經緯度，計算目前航班進度。

功能包含：

* 航班完成百分比
* 距離目的地剩餘距離
* Flight Progress Bar
* 視覺化飛機位置進度

此功能特別適合長程飛行使用。玩家可以快速確認目前航班是否仍在正常航線上，以及距離目的地還有多遠。

---

### 5. A350 TOD Calculator

本系統提供 iniBuilds A350 專用的 Top of Descent 計算功能。系統會偵測目前使用機型，只有在使用 A350 時才啟用 TOD 功能，避免其他機型使用不準確的下降剖面。

計算項目包含：

* Distance to Top of Descent
* Required Descent Distance
* Minutes to TOD
* Required FPM
* A350 Optimized Profile

TOD 計算會根據：

* 目前高度
* 目前地速
* 目的地座標
* 目標高度
* A350 profile bias

進行下降點估算。

---

### 6. Weather System

系統整合天氣查詢功能，可自動根據 SimBrief 航班中的起飛與抵達機場取得天氣資料。

顯示項目包含：

* Departure METAR
* Departure TAF
* Arrival METAR
* Arrival TAF
* Manual ICAO Weather Query

此功能讓飛行員可以在 Dashboard 中快速查看起飛與降落機場的天氣，不需要另外開啟天氣查詢網站。

---

### 7. VATSIM Network Summary

Dashboard 中會即時顯示 VATSIM 網路狀態。

包含：

* 線上飛行員數量
* 線上管制員數量
* VATSIM Radar 狀態

系統會定期向 VATSIM API 取得資料，並更新 Dashboard 顯示內容。

---

## 五、VATSIM Radar 開發流程

AeroFusion AI 內建自製 VATSIM Radar 頁面，目標是讓使用者不需要額外開啟第三方 VATSIM Radar 網站，即可直接在本系統中查看線上航機狀態。

### 1. 地圖介面建立

Radar 頁面使用前端地圖技術建立互動式地圖介面。系統將地圖作為基礎圖層，並在其上疊加 VATSIM 航機資料。

地圖介面功能包含：

* 可拖曳地圖
* 可縮放地圖
* 顯示航機圖示
* 顯示 Callsign 標籤
* 點擊航機顯示詳細資訊

此設計讓使用者可以像使用航空雷達系統一樣查看附近航機動態。

---

### 2. VATSIM API 資料抓取

後端透過 VATSIM 官方資料來源取得即時網路資料。資料內容包含目前在線上的 pilots、controllers 與其他網路資訊。

系統會定期抓取：

* 航機 callsign
* 飛機緯度
* 飛機經度
* 高度
* 地速
* 航向
* 起飛機場
* 抵達機場
* 飛行計畫資料
* 飛機型號

後端會將取得的 JSON 資料整理後提供給前端 Radar 使用。

---

### 3. 航機資料處理

VATSIM API 回傳的資料量較大，因此系統需要將資料進行整理與過濾。

處理流程包含：

1. 從 VATSIM API 取得 pilots 資料。
2. 解析每架航機的經緯度。
3. 讀取高度、航向、速度與航班資訊。
4. 將資料轉換成前端地圖可使用的格式。
5. 回傳給 Radar 頁面更新航機標記。

此流程讓前端不需要直接處理龐大的原始資料，而是由 Flask 後端負責整理資料。

---

### 4. 航機圖示顯示

前端根據每架航機的經緯度，在地圖上建立 aircraft marker。

航機 marker 會包含：

* 飛機圖示
* Callsign 標籤
* 航向旋轉
* 點擊事件
* 航機資訊面板

航機圖示會依照 heading 旋轉，讓使用者可以直觀看出航機飛行方向。

---

### 5. 航機資訊面板

當使用者點擊某架航機時，系統會在側邊資訊面板顯示詳細資料。

內容包含：

* Callsign
* Aircraft Type
* Origin
* Destination
* Altitude
* Ground Speed
* Heading
* Route
* Departure / Arrival Weather

此功能讓 Radar 不只是顯示航機位置，也能提供完整航班資訊。

---

### 6. Radar 與 Dashboard 整合

AeroFusion AI 的 Radar 並不是獨立工具，而是整合在整個 Flight Operations Center 內。

Dashboard 可一鍵切換至 Radar 頁面，Radar 頁面也可回到 Dashboard。這樣的設計減少了使用者在多個網站之間切換的需求，也讓系統更像一個完整的飛航營運平台。

---

## 六、Analytics 資料分析

系統內建 VATSIM Flight Data Analytics 頁面，透過背景爬蟲定期蒐集 VATSIM 航機資料，並存入資料庫進行分析。

分析項目包含：

* Total Flight Snapshots
* Top Aircraft
* Top Routes
* Average Cruise Altitude

此功能展現本專題不只是即時監控，也具備歷史資料儲存與資料分析能力。

---

## 七、系統架構

系統架構如下：

```text
使用者瀏覽器 / 手機
          ↓
   Cloudflare Tunnel
          ↓
      Flask Web App
          ↓
Dashboard / Radar / Analytics
          ↓
SimBrief API / VATSIM API / Weather API / SimConnect
          ↓
SQLite / PostgreSQL
          ↓
Microsoft Flight Simulator
```
### AeroFusion AI 本機部署架構

AeroFusion AI 並非純雲端系統，而是一套本機飛航監控平台。

由於系統需要透過 SimConnect 即時讀取 Microsoft Flight Simulator（MSFS）中的飛機資料，因此 AeroFusion AI 必須運行於安裝 MSFS 的電腦上。

為了讓使用者能夠透過手機、平板或其他裝置查看目前飛行狀態，本專案採用 Cloudflare Tunnel 建立安全的 HTTPS 存取通道。

此架構可同時保留本機資料存取能力與跨裝置遠端監控功能。

## 為什麼不使用 Render？

AeroFusion AI 的核心功能依賴 Microsoft Flight Simulator 提供的 SimConnect 介面。

系統需要即時讀取：

- Altitude
- Ground Speed
- Vertical Speed
- Heading
- Latitude / Longitude
- Aircraft Title
- Simulator Connection Status

上述資料僅存在於執行 Microsoft Flight Simulator 的本機電腦中。

Render、Railway、Vercel 等雲端平台雖然可以執行 Flask 網站，但無法直接存取使用者本機安裝的 Microsoft Flight Simulator，也無法透過 SimConnect 與模擬器建立連線。

因此即使成功部署網站，Flight Phase Detection、Flight Progress Tracking、A350 TOD Calculator 等核心功能仍無法正常運作。

為了解決此問題，本專案採用本機部署架構，並透過 Cloudflare Tunnel 提供 HTTPS 遠端存取能力。

如此一來，AeroFusion AI 既能直接取得本機模擬器資料，也能讓使用者透過手機或其他裝置隨時查看飛行狀態。

本系統可分為四個主要模組：

1. Frontend UI
   負責 Dashboard、Radar、Analytics 頁面顯示。

2. Flask Backend
   負責頁面路由、API 整合、資料處理與回傳。

3. External Data Integration
   整合 SimBrief、VATSIM、Weather 與 MSFS SimConnect。

4. Database / Analytics
   負責儲存 VATSIM 快照資料，並提供分析結果。

---

## 八、使用技術

### Backend

* Python
* Flask
* Flask-Login
* Flask-SQLAlchemy
* SQLAlchemy
* Requests

### Database

* SQLite
* PostgreSQL（選用）

### Frontend

* HTML
* CSS
* JavaScript

### Flight Simulation Integration

* Microsoft Flight Simulator
* SimConnect
* SimBrief API
* VATSIM API
* METAR / TAF Weather Data

### Deployment

* Git
* GitHub
* Cloudflare Tunnel
* Gunicorn

---

## 九、專案頁面

| 頁面                       | 功能                      |
| ------------------------ | ----------------------- |
| `/login`                 | SimBrief 使用者登入          |
| `/`                      | AeroFusion AI Dashboard |
| `/radar`                 | VATSIM Live Radar       |
| `/analytics`             | Flight Data Analytics   |
| `/logout`                | 登出系統                    |
| `/api/dashboard`         | Dashboard 即時資料 API      |
| `/api/simbrief-route`    | SimBrief 航班資料 API       |
| `/api/vatsim-data`       | VATSIM 原始資料 API         |
| `/api/vatsim-summary`    | VATSIM 線上人數 API         |
| `/api/weather/<icao>`    | 機場天氣 API                |
| `/api/analytics/summary` | 飛行分析資料 API              |

---

## 十、執行方式

### 1. 安裝套件

```bash
pip install -r requirements.txt
```

### 2. 建立 `.env`

```env
SECRET_KEY=your_secret_key
DATABASE_URL=your_database_url
```

### 3. 啟動 Flask

```bash
python app.py
```

### 4. 開啟網站

```text
### 4. 啟動 Cloudflare Tunnel

確認已安裝 Cloudflared：

```bash
cloudflared --version
建立 Tunnel：
cloudflared tunnel --url http://127.0.0.1:5000
成功後會產生：
https://xxxxx.trycloudflare.com
5. 開啟網站

本機：

http://127.0.0.1:5000

遠端：

https://xxxxx.trycloudflare.com

使用者即可透過手機、平板或其他電腦查看 AeroFusion AI Dashboard。
* 已完成 Cloudflare Tunnel 遠端存取整合
```

---

## 十一、目前完成進度

* 已建立 GitHub Repository
* 已完成 Flask 專案架構
* 已完成 SimBrief 登入與航班資料讀取
* 已完成 Dashboard UI
* 已完成 MSFS SimConnect 即時資料讀取
* 已完成 Squawk BCD 轉換
* 已完成 Flight Phase Detection
* 已完成 Flight Progress Tracking
* 已完成 A350 TOD Calculator
* 已完成 Weather Module
* 已完成 VATSIM Network Summary
* 已完成自製 VATSIM Radar
* 已完成 PostgreSQL 資料庫整合
* 已完成 VATSIM Flight Data Crawler
* 已完成 Analytics 頁面

---

## 十二、未來展望

### 1. AI ATC Assistant

未來可整合 vPilot 音訊輸出與 Whisper 語音辨識模型，將 VATSIM ATC 語音即時轉錄為文字，並進一步解析高度、航向、速度與 Squawk 等指令。

預計功能：

* 即時 ATC 語音辨識
* ATC 指令文字化
* Clearance 解析
* Altitude / Heading / Speed 指令辨識
* AI Copilot 提醒

---

### 2. AI Copilot

未來可發展電子副駕駛功能，根據目前飛機狀態與 ATC 指令提供飛行提醒。

可能功能包含：

* 檢查目前高度是否符合 ATC 指令
* 提醒轉向或下降
* 協助檢查 TOD
* 提供進場前檢查提醒
* 協助管理長程飛行監控

---

### 3. Flight Report System

未來可加入完整飛行報告功能。

可能內容：

* 起飛時間
* 落地時間
* 最大高度
* 平均地速
* 飛行距離
* Landing Rate
* Fuel Usage
* Flight Score

---

### 4. 更完整的 Radar 功能

未來 Radar 可進一步加入：

* 航路線顯示
* FIR 邊界
* 管制區域
* ATC 頻率顯示
* 附近航機篩選
* 航機搜尋
* 航班詳細資料彈窗
