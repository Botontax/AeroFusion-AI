import speech_recognition as sr
from faster_whisper import WhisperModel
import os

class STTEngine:
    def __init__(self, callback, my_callsign="SJX"):
        self.callback = callback
        self.my_callsign = my_callsign
        self.is_listening = False
        
        print("⏳ 正在掛載 Faster-Whisper 模型 (small.en)...")
        # 預設使用 CPU 與 small.en，確保所有人都能流暢執行
        self.model = WhisperModel("small.en", device="cpu", compute_type="int8")
        print("✅ AI 語音模型掛載完成！")
        
        self.recognizer = sr.Recognizer()
        
        # 🔌 虛擬音源線接入點 (你之前掃描測試成功的設備號碼是 1)
        try:
            self.microphone = sr.Microphone(device_index=1)
        except Exception as e:
            print(f"❌ 找不到虛擬音源線 (device_index=1)，請確認 VB-Cable 是否啟用: {e}")
            self.microphone = None

    def start_listening(self):
        if not self.microphone:
            print("⚠️ 麥克風未就緒，無法啟動監聽。")
            return
            
        self.is_listening = True
        with self.microphone as source:
            print("🎙️ 正在適應虛擬音源底噪...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("🟢 虛擬專線已接通，開始零雜音背景監聽！")
            
        # 啟動背景非同步監聽，這樣才不會卡住 Flask 網頁伺服器
        self.stop_listening_func = self.recognizer.listen_in_background(
            self.microphone, 
            self.audio_callback,
            phrase_time_limit=15 # 避免一次錄製過長，加快反應速度
        )

    def stop_listening(self):
        self.is_listening = False
        if hasattr(self, 'stop_listening_func'):
            self.stop_listening_func(wait_for_stop=False)
            print("🛑 語音監聽已停止。")

    def audio_callback(self, recognizer, audio):
        if not self.is_listening:
            return
        
        try:
            # 將語音資料轉為 WAV 格式
            wav_data = audio.get_wav_data()
            tmp_file_path = "temp_atc.wav"
            
            # 寫入暫存檔供 faster-whisper 讀取
            with open(tmp_file_path, "wb") as f:
                f.write(wav_data)
            
            # 🚀 動態 Prompt 小抄：加入常聽錯的字與你的呼號
            dynamic_prompt = f"Taipei Approach, cleared to, ILS, RNAV, runway, flight level, heading, squawk, descend and maintain, climb and maintain, {self.my_callsign}, tree, niner, fife."
            
            # 呼叫 AI 進行辨識，並開啟 VAD 濾除空白音
            segments, info = self.model.transcribe(
                tmp_file_path, 
                beam_size=5,
                initial_prompt=dynamic_prompt,
                vad_filter=True, 
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            # 組合辨識結果
            full_text = " ".join([segment.text for segment in segments]).strip()
            
            if full_text:
                print(f"🎧 [AI 聽到]: {full_text}")
                # 將文字透過回呼函數送回 app.py
                self.callback(full_text)
                
            # 清理暫存檔
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
                
        except Exception as e:
            print(f"⚠️ 語音辨識發生錯誤: {e}")