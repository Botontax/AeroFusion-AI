import requests

class SimBriefFetcher:
    def __init__(self, username):
        self.username = username
        # SimBrief 的官方 API 端點 (加上 json=1 確保回傳好處理的 JSON 格式)
        self.api_url = f"https://www.simbrief.com/api/xml.fetcher.php?username={self.username}&json=1"

    def get_latest_flight_plan(self):
        """連線至 SimBrief 抓取最新的航班計畫"""
        try:
            # 這裡設定 timeout=30，避免伺服器稍微延遲就報錯 (我們之前修過的這個坑！)
            response = requests.get(self.api_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # 檢查 SimBrief 是否回傳錯誤 (例如玩家還沒按下 Generate Flight)
                if 'errormsg' in data:
                    print(f"⚠️ SimBrief 回報: {data['errormsg']}")
                    return None
                    
                # 🧩 成功抓到資料！開始萃取我們儀表板需要的關鍵資訊
                flight_plan = {
                    "origin": data.get('origin', {}).get('icao_code', 'N/A'),
                    "dest": data.get('destination', {}).get('icao_code', 'N/A'),
                    "callsign": data.get('atc', {}).get('callsign', 'N/A'),
                    # 抓取預計使用的起飛跑道當作參考
                    "planned_sid": data.get('origin', {}).get('plan_rwy', 'N/A') 
                }
                return flight_plan
                
            else:
                print(f"❌ 無法連線至 SimBrief API，狀態碼: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            print("❌ 連線至 SimBrief 逾時 (Timeout)。請給伺服器多一點時間或檢查網路。")
            return None
        except Exception as e:
            print(f"❌ SimBrief 模組發生未知的錯誤: {e}")
            return None

# ==========================================
# 獨立測試區塊 (直接執行這個檔案可以測試有沒有抓到)
# ==========================================
if __name__ == "__main__":
    # 測試時換成你的帳號
    test_fetcher = SimBriefFetcher("Botontax")
    plan = test_fetcher.get_latest_flight_plan()
    if plan:
        print("✅ 測試成功！抓到計畫：")
        print(plan)
    else:
        print("❌ 測試失敗，請去 SimBrief 網頁確認你有產出最新的航班。")