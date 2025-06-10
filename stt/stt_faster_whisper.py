# stt/stt_faster_whisper.py
import os
import torch
import numpy as np
import queue
import sounddevice as sd
from faster_whisper import WhisperModel
import json

# === 1. Parametry ===
SCIEZKA_MODELU = "models/faster-whisper-small"
NAZWA_MODELU = "small"
SAMPLERATE = 16000
DURATION = 5  # czas nagrania w sekundach
MIN_AUDIO_LENGTH = 0.5  # minimalna długość audio do transkrypcji (sekundy)

# === 2. Wykrycie GPU/CPU i precyzji ===
if torch.cuda.is_available():
    URZADZENIE = "cuda"
    PRECISION = "float16"
    print(f"🚀 Faster-Whisper: GPU {torch.cuda.get_device_name(0)}")
else:
    URZADZENIE = "cpu"
    PRECISION = "int8"
    print("🔧 Faster-Whisper: CPU")

# === 3. Model ładowany tylko raz ===
model = None

def wczytaj_config():
    """Wczytuje konfigurację STT jeśli istnieje"""
    try:
        with open("config/config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        stt_config = config.get("stt_config", {})
        return {
            "duration": stt_config.get("duration", DURATION),
            "model_size": stt_config.get("model_size", NAZWA_MODELU),
            "language": stt_config.get("language", "pl"),
            "beam_size": stt_config.get("beam_size", 5),
            "temperature": stt_config.get("temperature", 0.0)
        }
    except:
        return {
            "duration": DURATION,
            "model_size": NAZWA_MODELU,
            "language": "pl",
            "beam_size": 5,
            "temperature": 0.0
        }

def zaladuj_model():
    global model
    if model is not None:
        return

    config = wczytaj_config()
    model_size = config["model_size"]
    sciezka = f"models/faster-whisper-{model_size}"

    print(f"📦 Ładowanie Faster-Whisper model: {model_size}")
    
    if not os.path.isdir(sciezka):
        print(f"📥 Model '{model_size}' nie znaleziony, trwa pobieranie...")
        model = WhisperModel(model_size, device=URZADZENIE, compute_type=PRECISION)
        print("✅ Pobieranie zakończone.")
    else:
        print(f"📦 Ładowanie modelu z: {sciezka}")
        model = WhisperModel(sciezka, device=URZADZENIE, compute_type=PRECISION)

    print(f"✅ Faster-Whisper gotowy ({URZADZENIE}, {PRECISION})")

# === 4. Kolejka i callback do mikrofonu ===
q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(f"⚠️ Błąd wejścia audio: {status}")
    q.put(indata.copy())

def _sprawdz_poziom_audio(audio_data):
    """Sprawdza czy audio nie jest za ciche"""
    rms = np.sqrt(np.mean(audio_data**2))
    if rms < 0.01:  # bardzo cichy dźwięk
        return False
    return True

def _normalizuj_audio(audio_data):
    """Normalizuje audio do zakresu [-1, 1]"""
    if audio_data.ndim > 1:
        audio_data = np.mean(audio_data, axis=1)
    
    # Normalizacja
    max_val = np.max(np.abs(audio_data))
    if max_val > 0:
        audio_data = audio_data / max_val * 0.8  # 80% maksymalnej amplitudy
    
    return audio_data.astype(np.float32)

# === 5. Rozpoznawanie mowy z mikrofonu ===
def rozpoznaj_mowe_z_mikrofonu() -> str:
    zaladuj_model()
    config = wczytaj_config()
    duration = config["duration"]
    
    print(f"🎙️ Nagrywam {duration}s... (Faster-Whisper)")

    try:
        # Wyczyść kolejkę przed nagrywaniem
        while not q.empty():
            q.get_nowait()

        with sd.InputStream(samplerate=SAMPLERATE, channels=1, callback=callback):
            frames = []
            chunks_needed = int(SAMPLERATE * duration / 1024)
            
            for i in range(chunks_needed):
                try:
                    data = q.get(timeout=duration + 1)  # timeout na wypadek problemów
                    frames.append(data)
                except queue.Empty:
                    print("⚠️ Timeout podczas nagrywania")
                    break

        if not frames:
            return ""

        # Przetworzenie audio
        audio_data = np.concatenate(frames, axis=0)
        audio_data = _normalizuj_audio(audio_data)

        # Sprawdź czy audio nie jest za ciche
        if not _sprawdz_poziom_audio(audio_data):
            print("🔇 Audio za ciche - prawdopodobnie cisza")
            return ""

        # Sprawdź minimalną długość
        if len(audio_data) / SAMPLERATE < MIN_AUDIO_LENGTH:
            print("⏱️ Audio za krótkie")
            return ""

        # Transkrypcja z konfiguracją
        segments, info = model.transcribe(
            audio_data, 
            language=config["language"],
            beam_size=config["beam_size"],
            temperature=config["temperature"],
            condition_on_previous_text=False,
            vad_filter=True,  # Voice Activity Detection
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        tekst = " ".join([seg.text for seg in segments]).strip()
        
        if tekst:
            confidence = getattr(info, 'language_probability', 0)
            print(f"🎯 Rozpoznano (pewność: {confidence:.2f}): {tekst}")
        
        return tekst

    except Exception as e:
        print(f"❌ Błąd Faster-Whisper STT: {e}")
        return ""

def ustaw_czas_nagrania(nowy_czas):
    """Zmienia czas nagrania w runtime"""
    global DURATION
    DURATION = max(1, min(nowy_czas, 30))  # 1-30 sekund
    print(f"✅ Czas nagrania ustawiony na {DURATION}s")

def info_modelu():
    """Zwraca informacje o załadowanym modelu"""
    if model is None:
        return "Model nie załadowany"
    return f"Faster-Whisper: {NAZWA_MODELU}, {URZADZENIE}, {PRECISION}"

# === 6. Test lokalny ===
if __name__ == "__main__":
    print("🧪 Test Faster-Whisper STT")
    print(f"Konfiguracja: {wczytaj_config()}")
    
    while True:
        input("Naciśnij Enter aby nagrać (Ctrl+C aby zakończyć)...")
        wynik = rozpoznaj_mowe_z_mikrofonu()
        print(f"📝 Wynik: '{wynik}'\n")