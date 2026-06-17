from SimConnect import SimConnect, AircraftRequests
import time

class SimTracker:
    def __init__(self):
        self.sm = None
        self.aq = None
        self.connected = False

    def connect(self):
        """嘗試連線至 MSFS"""
        try:
            if not self.connected:
                self.sm = SimConnect()
                self.aq = AircraftRequests(self.sm, _time=1000) # 設定 1 秒刷新率
                self.connected = True
                print("✅ 成功連線至 MSFS SimConnect!")
        except Exception:
            self.connected = False

    def get_flight_data(self):
        """一次抓取所有核心飛行數據"""
        if not self.connected:
            self.connect()
            
        # 預設離線資料
        default_data = {
            "status": "OFFLINE",
            "model": "UNKNOWN",
            "lat": 0.0,
            "lon": 0.0,
            "alt": 0,
            "heading": 0,
            "ground_speed": 0
        }

        if self.connected:
            try:
                # 抓取飛機型號
                model = self.aq.get("ATC_MODEL")
                model_str = model.decode('utf-8') if isinstance(model, bytes) else str(model) if model else "UNKNOWN"
                
                # 抓取經緯度、高度、航向、地速 (這些是 MSFS 標準變數)
                lat = self.aq.get("PLANE_LATITUDE")
                lon = self.aq.get("PLANE_LONGITUDE")
                alt = self.aq.get("INDICATED_ALTITUDE")
                hdg = self.aq.get("PLANE_HEADING_DEGREES_MAGNETIC")
                gs = self.aq.get("GROUND_VELOCITY") # 單位：節 Knots

                return {
                    "status": "ONLINE",
                    "model": model_str,
                    "lat": float(lat) if lat else 0.0,
                    "lon": float(lon) if lon else 0.0,
                    "alt": int(alt) if alt else 0,
                    "heading": int(hdg) if hdg else 0,
                    "ground_speed": int(gs) if gs else 0
                }
            except Exception:
                # 連線中斷時重設狀態
                self.connected = False
                return default_data
                
        return default_data

# 本地獨立測試區塊
if __name__ == "__main__":
    tracker = SimTracker()
    print("正在尋找模擬器數據...")
    while True:
        data = tracker.get_flight_data()
        print(f"狀態: {data['status']} | 機型: {data['model']} | 高度: {data['alt']} ft | 地速: {data['ground_speed']} kt")
        time.sleep(1)