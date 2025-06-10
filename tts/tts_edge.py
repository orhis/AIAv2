# tts_edge.py
import os
import sys
import asyncio
import tempfile
import sounddevice as sd
import soundfile as sf
import json

try:
    import edge_tts
except ImportError:
    print("📦 Instaluję edge-tts...")
    os.system(f"{sys.executable} -m pip install edge-tts soundfile")
    import edge_tts

# === Parametry ===
# Najlepsze polskie głosy w Edge-TTS
POLISH_VOICES = {
    "marek": "pl-PL-MarekNeural",      # mężczyzna, spokojny
    "zofia": "pl-PL-ZofiaNeural",      # kobieta, przyjemny
    "agnieszka": "pl-PL-AgnieszkaNeural"  # kobieta, naturalny
}

# Wczytaj głos z konfiguracji lub użyj domyślnego
voice_name = "zofia"  # domyślny
try:
    with open("config/config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        voice_name = config.get("local_config", {}).get("edge_voice", "zofia")
except Exception:
    pass

VOICE = POLISH_VOICES.get(voice_name, POLISH_VOICES["zofia"])
RATE = "+0%"    # prędkość mówienia
VOLUME = "+0%"  # głośność

print(f"🎙️ Edge-TTS używa głosu: {voice_name} ({VOICE})")

async def _generuj_mowe_async(tekst: str, output_path: str):
    """Asynchroniczna generacja mowy"""
    try:
        communicate = edge_tts.Communicate(tekst, VOICE, rate=RATE, volume=VOLUME)
        await communicate.save(output_path)
        return True
    except Exception as e:
        print(f"❌ Błąd Edge-TTS async: {e}")
        return False

def mow_tekstem(tekst: str):
    """Główna funkcja TTS - zgodna z interfejsem AIA"""
    print(f"🗣️ Edge-TTS mówi: {tekst}")
    
    try:
        # Stwórz tymczasowy plik audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            temp_path = tmp_file.name
        
        # Generuj mowę asynchronicznie
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(_generuj_mowe_async(tekst, temp_path))
        loop.close()
        
        if success and os.path.exists(temp_path):
            # Odtwórz plik audio
            data, samplerate = sf.read(temp_path)
            sd.play(data, samplerate)
            sd.wait()  # czekaj na zakończenie
            
            # Usuń tymczasowy plik
            os.unlink(temp_path)
        else:
            print("❌ Nie udało się wygenerować mowy")
            
    except Exception as e:
        print(f"❌ Błąd Edge-TTS: {e}")

def dostepne_glosy():
    """Zwraca listę dostępnych polskich głosów"""
    return list(POLISH_VOICES.keys())

def zmien_glos(nowy_glos: str):
    """Zmienia głos na jeden z dostępnych"""
    global VOICE
    if nowy_glos in POLISH_VOICES:
        VOICE = POLISH_VOICES[nowy_glos]
        print(f"🎙️ Zmieniono głos na: {nowy_glos}")
        return True
    else:
        print(f"❌ Nieznany głos: {nowy_glos}. Dostępne: {list(POLISH_VOICES.keys())}")
        return False

# === Test lokalny ===
if __name__ == "__main__":
    print("🧪 Test Edge-TTS:")
    print(f"Dostępne głosy: {dostepne_glosy()}")
    
    # Test podstawowy
    mow_tekstem("Witaj w systemie AIA. Używam Microsoft Edge TTS.")
    
    # Test różnych głosów
    for glos in dostepne_glosy():
        print(f"\n🎙️ Testuję głos: {glos}")
        zmien_glos(glos)
        mow_tekstem(f"To jest test głosu {glos}.")