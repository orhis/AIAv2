import json
import os
import torch
from stt import stt_whisper, stt_vosk, stt_google, stt_faster_whisper
from llm import llm_openrouter
from aia_audio import nasluchiwacz
from aia_audio import mowca
from core import rozumienie

# === 0. Informacja o GPU ===
if torch.cuda.is_available():
    print("✅ GPU aktywne:", torch.cuda.get_device_name(0))
else:
    print("⚠️ GPU nieaktywne – przełączono na CPU")

# === 1. Wczytanie konfiguracji ===
with open("config/config.json", encoding="utf-8") as f:
    config = json.load(f)

try:
    import streamlit as st
    config["api_key"] = st.secrets.get("OPENROUTER_API_KEY")
    print("🔑 Klucz API pobrany z .streamlit/secrets.toml")
except:
    try:
        with open("config/secure.json", encoding="utf-8") as f:
            secure = json.load(f)
            if isinstance(secure, dict):
                config["api_key"] = secure.get("api_key")
                print("🔑 Klucz API pobrany z config/secure.json")
            else:
                raise ValueError("secure.json nie ma formatu słownika (dict)")
    except Exception as e:
        print(f"❌ Brak klucza API: {e}")
        config["api_key"] = None

# === 2. Tryb uruchomienia ===
tryb = config["local_config"].get("tryb", "standardowy")
print(f"🔧 AIA v2 – uruchamianie w trybie: {tryb.upper()}")

# === 3. Inicjalizacja komponentów ===
# === STT ===
stt_nazwa = config["local_config"]["stt"]

if stt_nazwa == "whisper":
    from stt import stt_whisper as stt
elif stt_nazwa == "faster_whisper":
    from stt import stt_faster_whisper as stt
elif stt_nazwa == "vosk":
    from stt import stt_vosk as stt
elif stt_nazwa == "google":
    from stt import stt_google as stt
else:
    raise NotImplementedError(f"STT nieobsługiwany: {stt_nazwa}")

# === TTS ===
tts_nazwa = config["local_config"].get("tts", "coqui")

if tts_nazwa == "coqui":
    from tts import tts_coqui as tts
elif tts_nazwa == "pyttsx3":
    from tts import tts_pyttsx3 as tts
elif tts_nazwa == "google":
    from tts import tts_google as tts
elif tts_nazwa == "elevenlabs":
    from tts import tts_elevenlabs as tts
else:
    raise NotImplementedError(f"TTS nieobsługiwany: {tts_nazwa}")



llm = llm_openrouter

# === 4. Tryb TESTOWY – pełny nasłuch i rozumienie ===
if tryb == "testowy":
    print("🎧 AIA nasłuchuje... Powiedz: 'Stefan'")
    nasluchiwacz.nasluchuj(lambda tekst: rozumienie.analizuj(tekst, config), stt)

# === 5. Inne tryby – do zaimplementowania ===
else:
    print("🟡 Obsługa tego trybu nie została jeszcze zaimplementowana.")
