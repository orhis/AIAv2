# main.py
# ===================================================================
# AIA v2.1 UNIVERSAL INTELLIGENT ASSISTANT
# ===================================================================
# Nowa wersja z Universal Intelligent Assistant
# Flow: STT → LLM Post-processing → LLM + RAG → Response (+ fallback)
# Obsługuje: cooking, smart_home, calendar, finance, general, alarms
# ===================================================================

import json
import os
import torch
from stt import stt_whisper, stt_vosk, stt_google, stt_faster_whisper
from llm import llm_openrouter
from aia_audio import nasluchiwacz
from core import rozumienie
from core import logger

# NOWY IMPORT - Universal Intelligent Assistant
from core.universal_intelligent_assistant import integrate_with_existing_rozumienie

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
print(f"🔧 AIA v2.1 Universal – uruchamianie w trybie: {tryb.upper()}")

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

# === 5. Tryb TESTOWY – pełny nasłuch z Universal Assistant ===
if tryb == "testowy":
    print(f"🎧 AIA Universal nasłuchuje... Powiedz: 'Stefan' (Sesja: {logger.aktywna_sesja()})")
    print(f"🔊 Używane komponenty: {stt_nazwa} + {tts_nazwa}")
    print(f"🤖 Universal AI: cooking, smart_home, calendar, finance, general")
    print("🛑 Aby zakończyć, powiedz: 'dobra stop' lub naciśnij Ctrl+C")
    
    try:
        # ===================================================================
        # GŁÓWNA ZMIANA: Użycie Universal Intelligent Assistant
        # ===================================================================
        # STARE: nasluchiwacz.nasluchuj(lambda tekst: rozumienie.analizuj(tekst, config, tts), stt)
        # NOWE: Universal system z auto-detection kontekstu
        nasluchiwacz.nasluchuj(
            lambda tekst: integrate_with_existing_rozumienie(tekst, config, tts), 
            stt
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Nasłuchiwanie przerwane przez użytkownika")
        logger.loguj_rozmowe(
            tekst_wej="[SYSTEM]",
            tekst_wyj="Universal Assistant zakończony przez użytkownika",
            intencja="system_shutdown",
            metadata={"typ": "shutdown", "sposob": "keyboard_interrupt", "version": "universal"}
        )
    except Exception as e:
        print(f"\n❌ Błąd podczas nasłuchiwania Universal Assistant: {e}")
        logger.loguj_blad("universal_assistant_error", str(e), {"tryb": tryb})
    finally:
        print("👋 AIA Universal zakończyła pracę. Do zobaczenia!")

# === 6. Tryb PREZENTACJA – demo systemu ===
elif tryb == "prezentacja":
    print("🎭 Uruchamianie trybu prezentacji...")
    print("🤖 Demo będzie pokazywać Universal Intelligent Assistant")
    try:
        import subprocess
        subprocess.run(["python", "demo.py"], check=True)
        
        logger.loguj_rozmowe(
            tekst_wej="[SYSTEM]",
            tekst_wyj="Prezentacja Universal Assistant zakończona pomyślnie",
            intencja="system_demo",
            metadata={"typ": "demo_complete", "version": "universal"}
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
    print("🤖 GUI będzie używać Universal Intelligent Assistant")
    
    logger.loguj_rozmowe(
        tekst_wej="[SYSTEM]",
        tekst_wyj="Universal Assistant uruchomiony w trybie standardowym",
        intencja="system_start",
        metadata={"typ": "standard_mode", "gui": "streamlit", "version": "universal"}
    )

# === 8. Tryb DOMOWY – automatyzacja domowa (Enhanced) ===
elif tryb == "domowy":
    print("🏠 Tryb domowy - Universal Smart Home Assistant")
    print("🤖 Automatyzacja domowa z kontekstem smart_home")
    print("🔧 Funkcje: sterowanie urządzeniami, sceny, automatyzacje")
    
    # Tutaj można dodać dedykowane integracje z IoT
    # Universal Assistant automatycznie wykryje kontekst smart_home
    logger.loguj_rozmowe(
        tekst_wej="[SYSTEM]",
        tekst_wyj="Universal Smart Home Assistant aktywny",
        intencja="system_start",
        metadata={
            "typ": "home_mode", 
            "status": "enhanced", 
            "version": "universal",
            "contexts": ["smart_home", "general"]
        }
    )

# === 9. Tryb ALARMOWY – monitorowanie i alerty (Enhanced) ===
elif tryb == "alarmowy":
    print("🚨 Tryb alarmowy - Universal Monitoring Assistant")
    print("🤖 Monitorowanie systemu z kontekstem alarms")
    print("🔧 Funkcje: alerty, monitorowanie, diagnostyka")
    
    # Universal Assistant może obsługiwać kontekst "alarms"
    logger.loguj_rozmowe(
        tekst_wej="[SYSTEM]",
        tekst_wyj="Universal Monitoring Assistant aktywny",
        intencja="system_start",
        metadata={
            "typ": "alarm_mode", 
            "status": "enhanced", 
            "version": "universal",
            "contexts": ["alarms", "smart_home", "general"]
        }
    )

# === 10. Tryb KUCHENNY – dedykowany asystent kulinarny ===
elif tryb == "kuchenny":
    print("🍳 Tryb kuchenny - Dedicated Cooking Assistant")
    print("🤖 Specjalizowany asystent kulinarny")
    print("🔧 Funkcje: przepisy, składniki, kalorie, planowanie posiłków")
    
    # Nowy tryb dedykowany dla kuchni
    logger.loguj_rozmowe(
        tekst_wej="[SYSTEM]",
        tekst_wyj="Dedicated Cooking Assistant aktywny",
        intencja="system_start",
        metadata={
            "typ": "cooking_mode", 
            "status": "dedicated", 
            "version": "universal",
            "contexts": ["cooking"]
        }
    )

# === 11. Tryb FINANSOWY – asystent finansowy ===
elif tryb == "finansowy":
    print("💰 Tryb finansowy - Universal Finance Assistant")
    print("🤖 Asystent finansowy z kontekstem finance")
    print("🔧 Funkcje: saldo, przelewy, budżet, analiza wydatków")
    
    # Nowy tryb dla finansów
    logger.loguj_rozmowe(
        tekst_wej="[SYSTEM]",
        tekst_wyj="Universal Finance Assistant aktywny",
        intencja="system_start",
        metadata={
            "typ": "finance_mode", 
            "status": "enhanced", 
            "version": "universal",
            "contexts": ["finance", "general"]
        }
    )

# === 12. Nieznany tryb ===
else:
    print(f"🟡 Nieznany tryb: {tryb}")
    print("📋 Dostępne tryby:")
    print("   • testowy - pełny Universal Assistant")
    print("   • prezentacja - demo systemu")
    print("   • standardowy - GUI Streamlit")
    print("   • domowy - smart home automation")
    print("   • alarmowy - monitoring i alerty")
    print("   • kuchenny - dedykowany cooking assistant")
    print("   • finansowy - asystent finansowy")
    
    dostepne_tryby = [
        "testowy", "prezentacja", "standardowy", 
        "domowy", "alarmowy", "kuchenny", "finansowy"
    ]
    
    logger.loguj_blad(
        "unknown_mode", 
        f"Nieznany tryb: {tryb}", 
        {
            "dostepne_tryby": dostepne_tryby,
            "version": "universal"
        }
    )

# === 13. Zakończenie programu ===
print("🔚 Universal Intelligent Assistant - program główny zakończony")
print("🤖 Dostępne konteksty: cooking, smart_home, calendar, finance, general")

logger.loguj_rozmowe(
    tekst_wej="[SYSTEM]",
    tekst_wyj="Universal Assistant - program główny zakończony",
    intencja="system_end",
    metadata={
        "typ": "main_exit", 
        "tryb": tryb, 
        "version": "universal",
        "available_contexts": ["cooking", "smart_home", "calendar", "finance", "general"]
    }
)

# === 14. Dodatkowe informacje o systemie ===
print("\n" + "="*60)
print("🎯 AIA v2.1 UNIVERSAL INTELLIGENT ASSISTANT")
print("="*60)
print("🔧 Komponenty:")
print(f"   • STT: {stt_nazwa}")
print(f"   • TTS: {tts_nazwa}")
print(f"   • LLM: {config.get('llm_config', {}).get('provider', 'unknown')}")
print("🤖 Konteksty:")
print("   • 🍳 cooking - asystent kulinarny")
print("   • 🏠 smart_home - automatyzacja domowa")
print("   • 📅 calendar - zarządzanie kalendarzem")
print("   • 💰 finance - asystent finansowy")
print("   • 🌐 general - ogólne zapytania")
print("🎯 Flow:")
print("   🎙️ STT → 🔧 LLM Post-processing → 🧠 LLM + RAG → 🗣️ Response")
print("                                            ↓ (jeśli RAG pusty)")
print("                                       🧠 LLM SOLO")
print("="*60)