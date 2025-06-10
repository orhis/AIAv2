# core/logger.py
import time
from datetime import datetime
from core.pamiec import zapisz_rozmowe, zapisz_metrykę, inicjalizuj_pamiec

# Globalna sesja rozmowy (resetuje się co restart)
import uuid
CURRENT_SESSION = str(uuid.uuid4())[:8]

def loguj_rozmowe(tekst_wej, tekst_wyj, intencja=None, model_llm=None, czas_start=None, metadata=None):
    """
    Loguje rozmowę z dodatkowymi metadanymi
    Args:
        tekst_wej: tekst wejściowy użytkownika
        tekst_wyj: odpowiedź systemu
        intencja: rozpoznana intencja (opcjonalne)
        model_llm: użyty model LLM (opcjonalne)
        czas_start: czas rozpoczęcia przetwarzania (opcjonalne)
        metadata: dodatkowe dane (opcjonalne)
    """
    global CURRENT_SESSION
    
    # Oblicz czas odpowiedzi
    czas_ms = None
    if czas_start:
        czas_ms = int((time.time() - czas_start) * 1000)
    
    # Logowanie konsolowe
    print("✅ loguj_rozmowe działa:", tekst_wej, "→", tekst_wyj)
    if intencja:
        print(f"   🎯 Intencja: {intencja}")
    if model_llm:
        print(f"   🧠 Model: {model_llm}")
    if czas_ms:
        print(f"   ⏱️ Czas: {czas_ms}ms")
    
    # Zapis do bazy danych
    try:
        zapisz_rozmowe(
            tekst_wej=tekst_wej,
            tekst_wyj=tekst_wyj, 
            intencja=intencja,
            model_llm=model_llm,
            czas_ms=czas_ms,
            session_id=CURRENT_SESSION,
            metadata=metadata
        )
        
        # Zapisz metryki
        if intencja:
            zapisz_metrykę("intencja", intencja)
        if model_llm:
            zapisz_metrykę("llm_usage", model_llm)
            
    except Exception as e:
        print(f"❌ Błąd logowania rozmowy: {e}")

def loguj_tts_usage(tts_engine):
    """Loguje użycie TTS"""
    try:
        zapisz_metrykę("tts_usage", tts_engine)
        print(f"📊 TTS usage: {tts_engine}")
    except Exception as e:
        print(f"❌ Błąd logowania TTS: {e}")

def loguj_stt_usage(stt_engine):
    """Loguje użycie STT"""
    try:
        zapisz_metrykę("stt_usage", stt_engine)
        print(f"📊 STT usage: {stt_engine}")
    except Exception as e:
        print(f"❌ Błąd logowania STT: {e}")

def loguj_intencje(intencja, tekst_wej):
    """Loguje rozpoznaną intencję"""
    try:
        zapisz_metrykę("intencja", intencja)
        print(f"🎯 Intencja: {intencja} dla '{tekst_wej}'")
    except Exception as e:
        print(f"❌ Błąd logowania intencji: {e}")

def loguj_blad(typ_bledu, opis, context=None):
    """Loguje błędy systemu"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"❌ [{timestamp}] {typ_bledu}: {opis}")
    
    if context:
        print(f"   📋 Kontekst: {context}")
    
    try:
        metadata = {"error_type": typ_bledu, "description": opis, "context": context}
        zapisz_metrykę("error", typ_bledu)
    except Exception as e:
        print(f"❌ Błąd logowania błędu: {e}")

def nowa_sesja():
    """Rozpoczyna nową sesję rozmowy"""
    global CURRENT_SESSION
    CURRENT_SESSION = str(uuid.uuid4())[:8]
    print(f"🔄 Nowa sesja rozmowy: {CURRENT_SESSION}")
    return CURRENT_SESSION

def aktywna_sesja():
    """Zwraca ID aktywnej sesji"""
    return CURRENT_SESSION

# === Inicjalizacja przy imporcie ===
try:
    inicjalizuj_pamiec()
except Exception as e:
    print(f"⚠️ Nie udało się zainicjalizować pamięci: {e}")

# === Kompatybilność wsteczna ===
def loguj_rozmowe_legacy(tekst_wej, tekst_wyj):
    """Stara funkcja dla kompatybilności"""
    return loguj_rozmowe(tekst_wej, tekst_wyj)

print(f"📝 Logger zainicjalizowany - sesja: {CURRENT_SESSION}")