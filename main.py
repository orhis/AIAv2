# main.py
import json
import os
import torch
from stt import stt_whisper, stt_vosk, stt_google, stt_faster_whisper
from llm import llm_openrouter
from aia_audio import nasluchiwacz
from core import rozumienie
from core import logger

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
elif tts_nazwa == "edge":
    from tts import tts_edge as tts
else:
    raise NotImplementedError(f"TTS nieobsługiwany: {tts_nazwa}")

# === LLM ===
llm = llm_openrouter

# === 4. Logowanie użycia komponentów ===
print(f"📊 Logowanie komponentów systemu...")
logger.loguj_stt_usage(stt_nazwa)
logger.loguj_tts_usage(tts_nazwa)
print(f"✅ Komponenty zarejestrowane: STT={stt_nazwa}, TTS={tts_nazwa}")

# === 5. Tryb TESTOWY – pełny nasłuch i rozumienie ===
if tryb == "testowy":
    print(f"🎧 AIA nasłuchuje... Powiedz: 'Stefan' (Sesja: {logger.aktywna_sesja()})")
    print(f"🔊 Używane komponenty: {stt_nazwa} + {tts_nazwa}")
    print("🛑 Aby zakończyć, powiedz: 'dobra stop' lub naciśnij Ctrl+C")
    
    try:
        # Rozpocznij nasłuchiwanie z pełnym logowaniem
        nasluchiwacz.nasluchuj(lambda tekst: rozumienie.analizuj(tekst, config, tts), stt)
    except KeyboardInterrupt:
        print("\n🛑 Nasłuchiwanie przerwane przez użytkownika")
        logger.loguj_rozmowe(
            tekst_wej="[SYSTEM]",
            tekst_wyj="Nasłuchiwanie zakończone przez użytkownika",
            intencja="system_shutdown",
            metadata={"typ": "shutdown", "sposob": "keyboard_interrupt"}
        )
    except Exception as e:
        print(f"\n❌ Błąd podczas nasłuchiwania: {e}")
        logger.loguj_blad("nasluchiwanie_error", str(e), {"tryb": tryb})
    finally:
        print("👋 AIA zakończyla pracę. Do zobaczenia!")

# === 6. Tryb PREZENTACJA – demo systemu ===
elif tryb == "prezentacja":
    print("🎭 Uruchamianie trybu prezentacji...")
    try:
        import subprocess
        subprocess.run(["python", "demo.py"], check=True)
        
        logger.loguj_rozmowe(
            tekst_wej="[SYSTEM]",
            tekst_wyj="Prezentacja zakończona pomyślnie",
            intencja="system_demo",
            metadata={"typ": "demo_complete"}
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ Błąd uruchamiania demo: {e}")
        logger.loguj_blad("demo_error", str(e), {"tryb": tryb})
    except FileNotFoundError:
        print("❌ Nie znaleziono pliku demo.py")
        logger.loguj_blad("demo_file_error", "Brak demo.py", {"tryb": tryb})

# === 7. Tryb STANDARDOWY – interfejs GUI ===
elif tryb == "standardowy":
    print("🖥️ Tryb standardowy - użyj GUI Streamlit do interakcji")
    print("💡 Uruchom: streamlit run interface/config_gui.py")
    
    logger.loguj_rozmowe(
        tekst_wej="[SYSTEM]",
        tekst_wyj="System uruchomiony w trybie standardowym",
        intencja="system_start",
        metadata={"typ": "standard_mode", "gui": "streamlit"}
    )

# === 8. Tryb DOMOWY – automatyzacja domowa ===
elif tryb == "domowy":
    print("🏠 Tryb domowy - funkcje automatyzacji domowej")
    print("🔧 Ten tryb jest w fazie rozwoju...")
    
    # Tutaj można dodać integracje z IoT, smart home, etc.
    logger.loguj_rozmowe(
        tekst_wej="[SYSTEM]",
        tekst_wyj="Tryb domowy - w rozwoju",
        intencja="system_start",
        metadata={"typ": "home_mode", "status": "development"}
    )

# === 9. Tryb ALARMOWY – monitorowanie i alerty ===
elif tryb == "alarmowy":
    print("🚨 Tryb alarmowy - monitorowanie systemu")
    print("🔧 Ten tryb jest w fazie rozwoju...")
    
    # Tutaj można dodać monitoring, alerty, etc.
    logger.loguj_rozmowe(
        tekst_wej="[SYSTEM]",
        tekst_wyj="Tryb alarmowy - w rozwoju",
        intencja="system_start",
        metadata={"typ": "alarm_mode", "status": "development"}
    )

# === 10. Nieznany tryb ===
else:
    print(f"🟡 Nieznany tryb: {tryb}")
    print("📋 Dostępne tryby: testowy, prezentacja, standardowy, domowy, alarmowy")
    
    logger.loguj_blad(
        "unknown_mode", 
        f"Nieznany tryb: {tryb}", 
        {"dostepne_tryby": ["testowy", "prezentacja", "standardowy", "domowy", "alarmowy"]}
    )

# === 11. Zakończenie programu ===
print("🔚 Program główny zakończony")
logger.loguj_rozmowe(
    tekst_wej="[SYSTEM]",
    tekst_wyj="Program główny zakończony",
    intencja="system_end",
    metadata={"typ": "main_exit", "tryb": tryb}
)