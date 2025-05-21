import os
import torch
import numpy as np
import queue
import sounddevice as sd
from faster_whisper import WhisperModel

# === 1. Parametry ===
SCIEZKA_MODELU = "models/faster-whisper-small"
NAZWA_MODELU = "small"
SAMPLERATE = 16000
DURATION = 5  # czas nagrania w sekundach

# === 2. Wykrycie GPU/CPU i precyzji ===
if torch.cuda.is_available():
    URZADZENIE = "cuda"
    PRECISION = "float16"
else:
    URZADZENIE = "cpu"
    PRECISION = "int8"

# === 3. Model ładowany tylko raz ===
model = None

def zaladuj_model():
    global model
    if model is not None:
        return

    if not os.path.isdir(SCIEZKA_MODELU):
        print(f"📥 Model '{NAZWA_MODELU}' nie znaleziony, trwa pobieranie...")
        model = WhisperModel(NAZWA_MODELU, device=URZADZENIE, compute_type=PRECISION)
        print("✅ Pobieranie zakończone.")
    else:
        print(f"📦 Ładowanie modelu z: {SCIEZKA_MODELU}")
        model = WhisperModel(SCIEZKA_MODELU, device=URZADZENIE, compute_type=PRECISION)

    print("✅ Model gotowy do użycia.")

# === 4. Kolejka i callback do mikrofonu ===
q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(f"⚠️ Błąd wejścia audio: {status}")
    q.put(indata.copy())

# === 5. Rozpoznawanie mowy z mikrofonu ===
def rozpoznaj_mowe_z_mikrofonu() -> str:
    zaladuj_model()
    print("🎙️ Nagrywam... (Faster-Whisper)")

    try:
        with sd.InputStream(samplerate=SAMPLERATE, channels=1, callback=callback):
            frames = []
            for _ in range(0, int(SAMPLERATE * DURATION / 1024)):
                data = q.get()
                frames.append(data)

        audio_data = np.concatenate(frames, axis=0)

        if audio_data.ndim > 1:
            audio_data = np.mean(audio_data, axis=1)
        audio_data = audio_data.astype(np.float32)

        segments, _ = model.transcribe(audio_data, language="pl")
        tekst = " ".join([seg.text for seg in segments])
        return tekst.strip()

    except Exception as e:
        print(f"❌ Błąd Faster-Whisper STT: {e}")
        return ""

# === 6. Test lokalny ===
if __name__ == "__main__":
    wynik = rozpoznaj_mowe_z_mikrofonu()
    print("📝 Rozpoznany tekst:", wynik)
