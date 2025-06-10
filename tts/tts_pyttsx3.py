#TTS_pyttsx3.py
import sys
import os
import json

try:
    import pyttsx3
except ImportError:
    print("📦 Instaluję pyttsx3 i pywin32...")
    os.system(f"{sys.executable} -m pip install pyttsx3==2.90 pywin32 --upgrade")
    import pyttsx3

# === Inicjalizacja silnika ===
engine = pyttsx3.init()
engine.setProperty('rate', 170)  # prędkość mówienia

# === Lista dostępnych głosów ===
try:
    voices = engine.getProperty('voices')
    print("🔊 Dostępne głosy:")
    for i, voice in enumerate(voices):
        print(f"{i}: {voice.name} ({voice.id})")
except Exception as e:
    print(f"⚠️ Błąd przy pobieraniu głosów: {e}")

# === Możliwość wyboru głosu z config ===
voice_index = 0  # domyślny głos
try:
    with open("config/secure.json", "r", encoding="utf-8") as f:
        secure = json.load(f)
        voice_index = int(secure.get("pyttsx3_voice_index", 0))
except Exception:
    pass

try:
    engine.setProperty('voice', voices[voice_index].id)
except Exception as e:
    print(f"⚠️ Błąd przy ustawianiu głosu: {e}")

def mow_tekstem(tekst: str):
    try:
        print(f"🗣️ pyttsx3 mówi: {tekst}")
        engine.say(tekst)
        engine.runAndWait()
    except Exception as e:
        print(f"❌ Błąd pyttsx3 TTS: {e}")

# === Test lokalny ===
if __name__ == "__main__":
    mow_tekstem("To jest test głosu systemowego. Wszystko działa.")
