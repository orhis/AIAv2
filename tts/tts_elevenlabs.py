import os
import sys
import json
import tempfile
import requests

try:
    from playsound import playsound
except ImportError:
    print("📦 Instaluję playsound...")
    os.system(f"{sys.executable} -m pip install --force-reinstall playsound==1.2.2")
    from playsound import playsound

# === 1. Pobranie API key i voice_id ===
api_key = None
voice_id = "EXAVITQu4vr4xnSDxMaL"  # domyślny głos: Rachel

try:
    import streamlit as st
    api_key = st.secrets.get("elevenlabs_api_key")
    voice_id = st.secrets.get("elevenlabs_voice_id", voice_id)
    if api_key:
        print("🔑 API ElevenLabs z .streamlit/secrets.toml")
    if not voice_id:
        print("⚠️ Brak voice_id w secrets.toml – użyto domyślnego.")
except:
    pass

if not api_key:
    try:
        with open("config/secure.json", "r", encoding="utf-8") as f:
            secure = json.load(f)
            api_key = secure.get("elevenlabs_api_key")
            voice_id = secure.get("elevenlabs_voice_id", voice_id)
            if api_key:
                print("🔑 API ElevenLabs z secure.json")
            if not voice_id:
                print("⚠️ Brak voice_id w secure.json – użyto domyślnego.")
    except:
        pass

if not api_key:
    print("❌ Brak klucza API ElevenLabs!")

# === 2. Funkcja do mówienia ===
def mow_tekstem(tekst: str):
    if not api_key:
        print("❌ Nie można użyć ElevenLabs – brak klucza API.")
        return

    print(f"🗣️ ElevenLabs mówi: {tekst}")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "text": tekst,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }

    tmp_path = None
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"❌ Błąd API ElevenLabs: {response.status_code}")
            try:
                print(response.json())
            except:
                print(response.text)
            return

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        playsound(tmp_path)

    except Exception as e:
        print(f"❌ Błąd ElevenLabs TTS: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

# === Test lokalny ===
if __name__ == "__main__":
    mow_tekstem("To jest testowy komunikat z ElevenLabs. Działa poprawnie.")
