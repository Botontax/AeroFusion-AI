import re

class ATCParser:
    def __init__(self, my_callsign="SJX"):
        # 轉換成大寫以利比對
        self.my_callsign = str(my_callsign).upper()

    def analyze_speaker(self, text):
        """判斷這句 ATC 指令是不是衝著我們來的"""
        text_upper = text.upper()
        # 如果文字中包含我們的呼號，觸發紅色警戒 (ATC_COMMAND)
        if self.my_callsign in text_upper:
            return "ATC_COMMAND"
        return "OTHER"

    def extract_instructions(self, text):
        """使用正規表達式 (Regex) 抓取關鍵飛行參數"""
        text_upper = text.upper()
        instructions = {}

        # 1. 抓取高度 (Altitude / Flight Level)
        # 匹配 "FLIGHT LEVEL 310" 或 "FL 310"
        alt_match = re.search(r'(?:FLIGHT LEVEL|FL)\s*(\d{3})', text_upper)
        if alt_match:
            instructions["Altitude"] = f"FL{alt_match.group(1)}"
        else:
            # 匹配 "MAINTAIN 9000", "DESCEND TO 3000"
            alt_match = re.search(r'(?:MAINTAIN|TO|ALTITUDE)\s*(\d{3,5})', text_upper)
            if alt_match:
                instructions["Altitude"] = alt_match.group(1)

        # 2. 抓取航向 (Heading)
        # 匹配 "HEADING 250", "TURN RIGHT HEADING 040"
        hdg_match = re.search(r'HEADING\s*(\d{3})', text_upper)
        if hdg_match:
            instructions["Heading"] = hdg_match.group(1)

        # 3. 抓取速度 (Speed)
        # 匹配 "SPEED 250", "REDUCE SPEED 210"
        spd_match = re.search(r'SPEED\s*(\d{2,3})', text_upper)
        if spd_match:
            instructions["Speed"] = spd_match.group(1)

        # 4. 抓取跑道 (Runway)
        # 匹配 "RUNWAY 05L", "CLEARED ILS RUNWAY 23R"
        rwy_match = re.search(r'RUNWAY\s*(\d{1,2}[LCR]?)', text_upper)
        if rwy_match:
            instructions["Runway"] = rwy_match.group(1)

        # 5. 抓取應答機 (Squawk)
        # 匹配 "SQUAWK 1234"
        sqk_match = re.search(r'SQUAWK\s*(\d{4})', text_upper)
        if sqk_match:
            instructions["Squawk"] = sqk_match.group(1)

        return instructions

# ==========================================
# 獨立測試區塊 (直接執行這個檔案可以測試解析邏輯)
# ==========================================
if __name__ == "__main__":
    parser = ATCParser("SJX031")
    # 模擬一句極度複雜的 ATC 指令
    test_text = "SJX031 turn right heading 250, descend and maintain 5000, speed 210, cleared ILS runway 05L, squawk 4721"
    
    print(f"說話者類型: {parser.analyze_speaker(test_text)}")
    print(f"擷取指令結果: {parser.extract_instructions(test_text)}")