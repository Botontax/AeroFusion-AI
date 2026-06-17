import math

class A350TODCalculator:
    def __init__(self, target_alt=2500):
        # 預設目標高度為 2500 ft (攔截 ILS 的常見高度)
        self.target_alt = target_alt

    def _haversine(self, lat1, lon1, lat2, lon2):
        """計算兩點經緯度之間的直線距離 (海里 NM)"""
        R = 3440.065  # 地球半徑 (以海里為單位)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def calculate_tod(self, current_lat, current_lon, dest_lat, dest_lon, current_alt, ground_speed, wind_speed=0, wind_angle=0):
        """執行 A350 TOD 下降頂點運算"""
        
        # 1. 計算目前距離 (Distance to Destination)
        dist_to_dest = self._haversine(current_lat, current_lon, dest_lat, dest_lon)

        # 2. 計算需要下降的高度 (Altitude to Lose)
        alt_to_lose = max(0, current_alt - self.target_alt)

        # 3. 基礎 3 度下滑角下降距離 (Base Descent)
        base_descent = alt_to_lose / 318.0

        # 4. A350 專用阻力與減速緩衝 (Profile Bias)
        if current_alt >= 25000:
            bias = 18.0
        elif current_alt >= 10000:
            bias = 10.0
        else:
            bias = 4.0

        # 5. 風偏修正 (Wind Correction)
        # 假設 wind_angle 是相對機頭的風向角
        wind_factor = math.cos(math.radians(wind_angle))
        wind_correction = (-wind_factor) * (wind_speed / 12.0)

        # 6. 最終所需下降距離 (Required Descent NM)
        required_descent = base_descent + bias + wind_correction

        # 7. TOD 倒數距離 (Countdown NM)
        countdown_nm = dist_to_dest - required_descent

        # 8. TOD 剩餘時間 (Minutes to TOD)
        if ground_speed > 0:
            minutes_to_tod = (countdown_nm / ground_speed) * 60.0
        else:
            minutes_to_tod = 0.0

        return {
            "distance_to_dest_nm": round(dist_to_dest, 1),
            "required_descent_nm": round(required_descent, 1),
            "countdown_nm": round(countdown_nm, 1),
            "minutes_to_tod": round(minutes_to_tod, 1)
        }

# ==========================================
# 獨立測試區塊
# ==========================================
if __name__ == "__main__":
    calc = A350TODCalculator()
    
    # 模擬測試數據
    result = calc.calculate_tod(
        current_lat=25.0, current_lon=121.0,  # 飛機目前位置
        dest_lat=22.5, dest_lon=120.3,        # 目的地位置
        current_alt=40000,                    # 目前高度 (FL400)
        ground_speed=520,                     # 地速 (kt)
        wind_speed=20, wind_angle=180         # 逆風 20 節
    )
    
    print("🛫 A350 TOD 計算結果:")
    for key, value in result.items():
        print(f" - {key}: {value}")