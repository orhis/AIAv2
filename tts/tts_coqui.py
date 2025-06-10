#TTS COQUI.PY
import os
import sys
import torch
import tempfile
import sounddevice as sd
import numpy as np

try:
    from TTS.api import TTS
except ImportError:
    print("📦 Instaluję coqui-ai/TTS...")
    os.system(f"{sys.executable} -m pip install TTS")
    from TTS.api import TTS

# === 1. Parametry ===
MODEL_NAME = "tts_models/pl/mai/base"
CACHE_DIR = "models/tts/coqui"
SAMPLERATE = 22050

tts_model = None

def zaladuj_model():
    global tts_model
    if tts_model is not None:
        return

    print("📦 Ładowanie modelu Coqui TTS...")
    try:
        tts_model = TTS(model_name=MODEL_NAME, progress_bar=False, gpu=torch.cuda.is_available(), cache_dir=CACHE_DIR)
        print("✅ Model Coqui TTS gotowy.")
    except Exception as e:
        print(f"❌ Błąd ładowania modelu Coqui TTS: {e}")

def mow_tekstem(tekst: str):
    zaladuj_model()
    print(f"🗣️ Coqui-TTS mówi: {tekst}")
    try:
        waveform = tts_model.tts(tekst)
        waveform = waveform.squeeze()
        sd.play(waveform, samplerate=SAMPLERATE)
        sd.wait()
    except Exception as e:
        print(f"❌ Błąd Coqui TTS: {e}")

# === Test lokalny ===
if __name__ == "__main__":
    mow_tekstem("Witaj w systemie AIA. Działam poprawnie.")