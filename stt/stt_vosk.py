import os
import queue
import json
import zipfile
import urllib.request
import sounddevice as sd
from vosk import Model, KaldiRecognizer

# === 1. Parametry ===
SCIEZKA_MODELU = "models/vosk-pl"
URL_MODELU = "https://alphacephei.com/vosk/models/vosk-model-small-pl-0.22.zip"
ZIP_MODELU = "models/vosk-pl.zip"
SAMPLERATE = 16000

# === 2. Automatyczne pobieranie i przygotowanie modelu ===
def pobierz_model_vosk():
    if os.path.exists(SCIEZKA_MODELU):
        return

    os.makedirs("models", exist_ok=True)
    print("⬇️ Pobieranie modelu Vosk PL...")
    urllib.request.urlretrieve(URL_MODELU, ZIP_MODELU)

    print("📦 Rozpakowywanie modelu...")
    with zipfile.ZipFile(ZIP_MODELU, 'r') as zip_ref:
        zip_ref.extractall("models")

    os.rename("models/vosk-model-small-pl-0.22", SCIEZKA_MODELU)
    os.remove(ZIP_MODELU)
    print("✅ Model Vosk PL gotowy.")

# === 3. Ładowanie modelu i inicjalizacja ===
pobierz_model_vosk()
model = Model(SCIEZKA_MODELU)
recognizer = KaldiRecognizer(model, SAMPLERATE)
q = queue.Queue()

# === 4. Callback audio ===
def callback(indata, frames, time, status):
    if status:
        print(f"⚠️ Błąd wejścia audio: {status}")
    q.put(bytes(indata))

# === 5. Rozpoznawanie mowy z mikrofonu ===
def rozpoznaj_mowe_z_mikrofonu() -> str:
    print("🎤 Nasłuchuję (Vosk)... Powiedz coś.")
    try:
        with sd.RawInputStream(samplerate=SAMPLERATE, blocksize=8000, dtype="int16",
                               channels=1, callback=callback):
            tekst = ""
            while True:
                data = q.get()
                if recognizer.AcceptWaveform(data):
                    result = recognizer.Result()
                    tekst_json = json.loads(result)
                    tekst = tekst_json.get("text", "")
                    break
        return tekst.strip()
    except Exception as e:
        print(f"❌ Błąd Vosk STT: {e}")
        return ""

# === 6. Test lokalny ===
if __name__ == "__main__":
    wynik = rozpoznaj_mowe_z_mikrofonu()
    print("📝 Rozpoznany tekst:", wynik)