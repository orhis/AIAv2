# core/rozumienie.py
import json
import re
import time
from llm import llm_openrouter
from core import logger

# === 1. Wczytanie komend predefiniowanych ===
try:
    with open("config/komendy_domyslne.json", encoding="utf-8") as f:
        KOMENDY = json.load(f)
    print(f"✅ Wczytano {len(KOMENDY)} predefiniowanych komend")
except FileNotFoundError:
    print("⚠️ Brak pliku komendy_domyslne.json - używam trybu tylko LLM")
    KOMENDY = []
except json.JSONDecodeError as e:
    print(f"❌ Błąd w pliku komendy_domyslne.json: {e}")
    KOMENDY = []

# === 2. Analiza tekstu ===
def analizuj(tekst, config, tts_module):
    """
    Główna funkcja analizy tekstu z pełnym logowaniem
    """
    start_time = time.time()
    intencja = None
    model_llm = None
    odpowiedz = ""
    
    print("📥 Otrzymano polecenie:", tekst)

    try:
        # Szukaj dopasowania do wzorców z JSON-a
        for komenda in KOMENDY:
            try:
                wzorzec = komenda["wzorzec"]
                intencja = komenda["intencja"]
                if re.search(wzorzec, tekst, re.IGNORECASE):
                    print(f"✅ Rozpoznano intencję: {intencja}")
                    
                    # Loguj rozpoznaną intencję
                    logger.loguj_intencje(intencja, tekst)
                    
                    # Wykonaj intencję
                    odpowiedz = wykonaj_intencje(intencja, tekst, tts_module)
                    
                    # Loguj pełną rozmowę
                    logger.loguj_rozmowe(
                        tekst_wej=tekst,
                        tekst_wyj=odpowiedz,
                        intencja=intencja,
                        model_llm=None,  # intencje lokalne nie używają LLM
                        czas_start=start_time,
                        metadata={"typ": "intencja_lokalna", "wzorzec": wzorzec}
                    )
                    
                    return odpowiedz
                    
            except KeyError as e:
                logger.loguj_blad("config_error", f"Błędna struktura komendy: brak klucza {e}", komenda)
                continue
            except re.error as e:
                logger.loguj_blad("regex_error", f"Błędny wzorzec regex: {e}", wzorzec)
                continue

        # Brak dopasowania → LLM
        print("🤖 Brak predefiniowanej komendy – pytam LLM...")
        
        try:
            model_llm = config["llm_config"]["model"]
            odpowiedz = llm_openrouter.odpowiedz(tekst, config)
            print(f"🧠 LLM odpowiada: {odpowiedz}")
            
            # Sprawdź czy odpowiedź nie jest błędem
            if odpowiedz.startswith("[Błąd"):
                logger.loguj_blad("llm_error", odpowiedz, {"tekst": tekst, "model": model_llm})
                odpowiedz = "Przepraszam, wystąpił problem z połączeniem. Spróbuj ponownie."
            
            # Wypowiedz odpowiedź
            tts_module.mow_tekstem(odpowiedz)
            
            # Loguj rozmowę LLM
            logger.loguj_rozmowe(
                tekst_wej=tekst,
                tekst_wyj=odpowiedz,
                intencja=None,
                model_llm=model_llm,
                czas_start=start_time,
                metadata={"typ": "llm_response"}
            )
            
        except Exception as e:
            error_msg = f"Przepraszam, wystąpił błąd podczas przetwarzania: {str(e)}"
            logger.loguj_blad("llm_processing_error", str(e), {"tekst": tekst})
            
            tts_module.mow_tekstem(error_msg)
            
            # Loguj błąd jako rozmowę
            logger.loguj_rozmowe(
                tekst_wej=tekst,
                tekst_wyj=error_msg,
                intencja=None,
                model_llm=model_llm,
                czas_start=start_time,
                metadata={"typ": "error_response", "error": str(e)}
            )
            
            odpowiedz = error_msg
        
    except Exception as e:
        error_msg = f"Wystąpił nieoczekiwany błąd systemu."
        logger.loguj_blad("system_error", str(e), {"tekst": tekst, "function": "analizuj"})
        
        tts_module.mow_tekstem(error_msg)
        odpowiedz = error_msg
    
    return odpowiedz

# === 3. Wykonanie intencji ===
def wykonaj_intencje(intencja, tekst, tts_module):
    """
    Wykonuje konkretną intencję z logowaniem
    """
    odpowiedz = ""
    
    try:
        if intencja == "zapytanie_godzina":
            from datetime import datetime
            godzina = datetime.now().strftime("%H:%M")
            odpowiedz = f"Jest godzina {godzina}"
            
        elif intencja == "zapytanie_data":
            from datetime import datetime
            data = datetime.now().strftime("%d %B %Y")
            odpowiedz = f"Dzisiaj jest {data}"
            
        elif intencja == "powitanie":
            import random
            powitania = [
                "Cześć! Jak mogę pomóc?",
                "Witaj! W czym mogę Ci pomóc?",
                "Hej! Gotowy do pracy!"
            ]
            odpowiedz = random.choice(powitania)
            
        elif intencja == "pozegnanie":
            import random
            pozegnania = [
                "Do widzenia!",
                "Miłego dnia!",
                "Do zobaczenia!"
            ]
            odpowiedz = random.choice(pozegnania)
            
        elif intencja == "status_systemu":
            import torch
            gpu_status = "aktywne" if torch.cuda.is_available() else "nieaktywne"
            odpowiedz = f"System AIA działa poprawnie. GPU: {gpu_status}"
            
        elif intencja == "zapisz_wiadomosc":
            # Wyciągnij treść wiadomości z tekstu
            import re
            match = re.search(r'(?:zapisz|dodaj|utw[oó]rz).*wiadomo[śćs][ćc]?\s*[":]\s*(.+)', tekst, re.IGNORECASE)
            if match:
                tresc = match.group(1).strip()
                from core.pamiec import zapisz_wiadomosc
                uuid_msg = zapisz_wiadomosc("Notatka głosowa", tresc, "AIA Użytkownik")
                odpowiedz = f"Zapisałem wiadomość: {tresc}"
            else:
                odpowiedz = "Nie zrozumiałem co mam zapisać. Spróbuj: 'Zapisz wiadomość: treść'"
                
        elif intencja == "odczytaj_wiadomosc":
            from core.pamiec import pobierz_wiadomosci
            wiadomosci = pobierz_wiadomosci(limit=3)
            if wiadomosci:
                odpowiedz = "Twoje ostatnie wiadomości: "
                for i, w in enumerate(wiadomosci, 1):
                    odpowiedz += f"{i}. {w['tytul']}: {w['tresc']}. "
            else:
                odpowiedz = "Nie masz żadnych zapisanych wiadomości."
                
        elif intencja == "przeglad_wiadomosci":
            from core.pamiec import pobierz_wiadomosci
            wiadomosci = pobierz_wiadomosci(limit=5)
            if wiadomosci:
                odpowiedz = f"Masz {len(wiadomosci)} wiadomości. "
                for i, w in enumerate(wiadomosci, 1):
                    odpowiedz += f"{i}. {w['tytul']} z {w['timestamp'][:10]}. "
            else:
                odpowiedz = "Nie masz żadnych zapisanych wiadomości."
            
        else:
            odpowiedz = f"Zrozumiałem intencję: {intencja}, ale nie mam jeszcze implementacji."
            
    except Exception as e:
        logger.loguj_blad("intencja_error", f"Błąd podczas wykonywania intencji {intencja}: {e}", {"tekst": tekst})
        odpowiedz = "Przepraszam, wystąpił błąd podczas wykonywania polecenia."

    # Wyświetl i wypowiedz odpowiedź
    print(f"🗣️ AIA odpowiada: {odpowiedz}")
    try:
        tts_module.mow_tekstem(odpowiedz)
    except Exception as e:
        logger.loguj_blad("tts_error", f"Błąd TTS: {e}", {"odpowiedz": odpowiedz})

    return odpowiedz

# === 4. Funkcje pomocnicze ===
def dodaj_komende(wzorzec, intencja):
    """Dodaje nową komendę do listy (w runtime)"""
    KOMENDY.append({"wzorzec": wzorzec, "intencja": intencja})
    print(f"✅ Dodano komendę: {wzorzec} -> {intencja}")

def lista_intencji():
    """Zwraca listę wszystkich dostępnych intencji"""
    return [komenda["intencja"] for komenda in KOMENDY]

# === Test lokalny ===
if __name__ == "__main__":
    print("🧪 Test modułu rozumienie z loggerem")
    
    # Mock config i TTS dla testów
    mock_config = {
        "local_config": {"styl": "precyzyjny"},
        "llm_config": {"model": "test-model"}
    }
    
    class MockTTS:
        def mow_tekstem(self, tekst):
            print(f"[MOCK TTS]: {tekst}")
    
    mock_tts = MockTTS()
    
    # Testy
    print("\n--- Test 1: Zapytanie o godzinę ---")
    analizuj("która godzina?", mock_config, mock_tts)
    
    print("\n--- Test 2: Powitanie ---")
    analizuj("cześć", mock_config, mock_tts)
    
    print("\n--- Test 3: Zapisanie wiadomości ---")
    analizuj("zapisz wiadomość: spotkanie o 15:00", mock_config, mock_tts)