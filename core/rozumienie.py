# core/rozumienie.py
import json
import re
import time
import os
from llm import llm_openrouter
from core import logger

# === NOWY - Token Manager ===
class TokenManager:
    def __init__(self):
        self.cache_file = "data/token_limits.json"
        self.model_limits = self.load_cache()
        self.default_safe_tokens = 150  # Bezpieczny start
        
    def load_cache(self):
        """Wczytuje zapisane limity tokenów z pliku"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Nie można wczytać cache tokenów: {e}")
        return {}
    
    def save_cache(self):
        """Zapisuje limity tokenów do pliku"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.model_limits, f, indent=2)
        except Exception as e:
            print(f"⚠️ Nie można zapisać cache tokenów: {e}")
    
    def get_safe_tokens(self, model, requested_tokens=2048):
        """Zwraca bezpieczną liczbę tokenów dla modelu"""
        if model in self.model_limits:
            safe_limit = min(requested_tokens, self.model_limits[model])
            print(f"🔒 Model {model}: używam zapisanego limitu {safe_limit} tokenów")
            return safe_limit
        else:
            print(f"🆕 Model {model}: pierwsza próba z {self.default_safe_tokens} tokenów")
            return min(requested_tokens, self.default_safe_tokens)
    
    def handle_402_error(self, model, error_message):
        """Wyciąga i zapisuje rzeczywisty limit z błędu 402"""
        match = re.search(r"can only afford (\d+)", error_message)
        if match:
            actual_limit = int(match.group(1))
            self.model_limits[model] = actual_limit
            self.save_cache()
            print(f"💾 Zapisano limit dla {model}: {actual_limit} tokenów")
            return actual_limit
        return self.default_safe_tokens

# Globalna instancja Token Manager
token_manager = TokenManager()

# === NOWE - Import RAG ===
try:
    import sys
    import os
    rag_path = os.path.join(os.path.dirname(__file__), 'rag')
    sys.path.insert(0, rag_path)
    from rag_engine import RecipeRAG
    RAG_AVAILABLE = True
    # Inicjalizacja RAG - raz przy starcie
    recipe_rag = RecipeRAG()
    if recipe_rag.initialize():
        print("✅ RAG zainicjalizowany w rozumieniu")
    else:
        print("❌ Błąd inicjalizacji RAG")
        RAG_AVAILABLE = False
except Exception as e:
    print(f"⚠️ RAG niedostępny: {e}")
    RAG_AVAILABLE = False
    recipe_rag = None

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

# === 2.5. NOWA FUNKCJA - LLM Intent Classifier ===
def klasyfikuj_intencje_llm(tekst, dostepne_intencje):
    """Używa LLM do inteligentnej klasyfikacji intencji"""
    
    # Przygotuj prompt z listą dostępnych intencji
    intencje_lista = ", ".join([k["intencja"] for k in dostepne_intencje])
    
    prompt_klasyfikacji = f"""Przeanalizuj tekst użytkownika i określ jego intencję.

TEKST: "{tekst}"

DOSTĘPNE INTENCJE:
{intencje_lista}

Zadanie: Wybierz DOKŁADNIE JEDNĄ intencję z listy powyżej, która najlepiej pasuje do tekstu.
Jeśli żadna nie pasuje, odpowiedz: "brak_dopasowania"

Odpowiedz TYLKO nazwą intencji, bez dodatkowych słów."""

    try:
        # Użyj małego, szybkiego modelu do klasyfikacji
        config_klasyfikacja = {
            "llm_config": {
                "model": "openai/gpt-3.5-turbo",  # Szybki i tani
                "max_tokens": 50,
                "temperature": 0.1  # Deterministyczne odpowiedzi
            }
        }
        
        print(f"🔍 LLM klasyfikuje intencję dla: '{tekst[:50]}...'")
        odpowiedz = zapytaj_llm_safe(prompt_klasyfikacji, config_klasyfikacja, max_retries=1)
        
        # Wyczyść odpowiedź
        intencja = odpowiedz.strip().replace("🧠 [Czysty LLM]: ", "").strip()
        
        # Sprawdź czy to prawidłowa intencja
        if intencja in [k["intencja"] for k in dostepne_intencje]:
            print(f"✅ LLM rozpoznał intencję: {intencja}")
            return intencja
        elif intencja == "brak_dopasowania":
            print(f"❌ LLM nie rozpoznał żadnej intencji")
            return None
        else:
            print(f"⚠️ LLM zwrócił nieprawidłową intencję: {intencja}")
            return None
            
    except Exception as e:
        print(f"❌ Błąd klasyfikacji LLM: {e}")
        return None
def zapytaj_llm_safe_with_fallback(tekst, config, max_retries=2):
    """Próbuje różne modele jeśli główny nie ma kredytów"""
    
    modele = [config["llm_config"]["model"]]  # Główny model
    
    # Dodaj alternatywne modele jeśli są
    if "alternative_models" in config["llm_config"]:
        modele.extend(config["llm_config"]["alternative_models"])
    
    for model in modele:
        print(f"🎯 Próbuję model: {model}")
        
        # Skopiuj config z nowym modelem
        temp_config = config.copy()
        temp_config["llm_config"]["model"] = model
        
        result = zapytaj_llm_safe(tekst, temp_config, max_retries)
        
        # Jeśli sukces lub nie ma błędu kredytów
        if not ("Brak kredytów API" in result or "can only afford" in result):
            return result
            
        print(f"❌ Model {model} wymaga kredytów, próbuję następny...")
    
    return "❌ Wszystkie modele wymagają doładowania kredytów"

def zapytaj_llm_safe(tekst, config, max_retries=2):
    """Bezpieczne zapytanie LLM z auto-adjustem tokenów"""
    
    model = config["llm_config"]["model"]
    requested_tokens = config["llm_config"].get("max_tokens", 2048)
    
    for attempt in range(max_retries):
        # Pobierz bezpieczną liczbę tokenów
        safe_tokens = token_manager.get_safe_tokens(model, requested_tokens)
        
        # Aktualizuj config z bezpiecznymi tokenami
        temp_config = config.copy()
        temp_config["llm_config"]["max_tokens"] = safe_tokens
        
        try:
            print(f"🧠 Pytam {model} (tokens: {safe_tokens})...")
            odpowiedz = llm_openrouter.odpowiedz(tekst, temp_config)
            
            # Sprawdź czy odpowiedź zawiera błąd 402
            if "[Błąd API OpenRouter: 402]" in odpowiedz and "can only afford" in odpowiedz:
                # Wyciągnij liczbę tokenów z błędu
                actual_limit = token_manager.handle_402_error(model, odpowiedz)
                
                print(f"🔄 Wykryto limit {actual_limit} tokenów, ponawiam zapytanie...")
                
                # Jeśli to pierwsza próba, spróbuj ponownie
                if attempt == 0:
                    continue
                else:
                    return f"❌ Brak kredytów API. Dostępne tokeny: {actual_limit}. Doładuj konto na https://openrouter.ai/settings/credits"
            
            elif odpowiedz.startswith("[Błąd"):
                # Inny błąd API
                if attempt == 0:
                    print(f"⚠️ Błąd API (próba {attempt + 1}), ponawiam...")
                    continue
                else:
                    return "Przepraszam, wystąpił problem z połączeniem. Spróbuj ponownie."
            
            # Sukces!
            return odpowiedz
            
        except Exception as e:
            if attempt == 0:
                print(f"⚠️ Błąd połączenia (próba {attempt + 1}): {e}")
                continue
            else:
                return f"Przepraszam, wystąpił błąd połączenia: {str(e)}"
    
    return "❌ Przekroczono liczbę prób połączenia z LLM"

# === 3. Analiza tekstu (zaktualizowana) ===
def analizuj(tekst, config, tts_module):
    """
    Główna funkcja analizy tekstu z pełnym logowaniem i bezpiecznym LLM
    """
    start_time = time.time()
    intencja = None
    model_llm = None
    odpowiedz = ""
    
    print("📥 Otrzymano polecenie:", tekst)

    try:
        # === KROK 1: Próba tradycyjnych wzorców regex ===
        for komenda in KOMENDY:
            try:
                wzorzec = komenda["wzorzec"]
                intencja = komenda["intencja"]
                if re.search(wzorzec, tekst, re.IGNORECASE):
                    print(f"✅ Rozpoznano intencję (regex): {intencja}")
                    
                    # Loguj rozpoznaną intencję
                    logger.loguj_intencje(intencja, tekst)
                    
                    # Wykonaj intencję
                    odpowiedz = wykonaj_intencje(intencja, tekst, tts_module)
                    
                    # Sprawdź czy to była implementacja lokalna czy LLM fallback
                    if "🤖 [LLM za intencję" in odpowiedz:
                        # To był LLM fallback - już zalogowane w wykonaj_intencje
                        return odpowiedz
                    else:
                        # Lokalna implementacja
                        logger.loguj_rozmowe(
                            tekst_wej=tekst,
                            tekst_wyj=odpowiedz,
                            intencja=intencja,
                            model_llm=None,
                            czas_start=start_time,
                            metadata={"typ": "intencja_lokalna_regex", "wzorzec": wzorzec}
                        )
                    
                    return odpowiedz
                    
            except KeyError as e:
                logger.loguj_blad("config_error", f"Błędna struktura komendy: brak klucza {e}", komenda)
                continue
            except re.error as e:
                logger.loguj_blad("regex_error", f"Błędny wzorzec regex: {e}", wzorzec)
                continue

        # === KROK 2: Jeśli regex nie zadziałał, spróbuj LLM Intent Classifier ===
        print("🔍 Regex nie rozpoznał - próbuję LLM Intent Classifier...")
        
        llm_intencja = klasyfikuj_intencje_llm(tekst, KOMENDY)
        
        if llm_intencja:
            print(f"✅ Rozpoznano intencję (LLM): {llm_intencja}")
            
            # Loguj rozpoznaną intencję
            logger.loguj_intencje(llm_intencja, tekst)
            
            # Wykonaj intencję
            odpowiedz = wykonaj_intencje(llm_intencja, tekst, tts_module)
            
            # Sprawdź czy to była implementacja lokalna czy LLM fallback
            if "🤖 [LLM za intencję" in odpowiedz:
                # To był LLM fallback - już zalogowane
                return odpowiedz
            else:
                # Lokalna implementacja przez LLM classifier
                logger.loguj_rozmowe(
                    tekst_wej=tekst,
                    tekst_wyj=odpowiedz,
                    intencja=llm_intencja,
                    model_llm="gpt-3.5-turbo",  # Model użyty do klasyfikacji
                    czas_start=start_time,
                    metadata={"typ": "intencja_lokalna_llm_classifier"}
                )
            
            return odpowiedz

        # Brak dopasowania → LLM z bezpiecznym systemem tokenów
        print("🤖 Brak predefiniowanej komendy – pytam LLM...")
        
        try:
            model_llm = config["llm_config"]["model"]
            
            # NOWE: Użyj bezpiecznej funkcji LLM z fallback
            odpowiedz = zapytaj_llm_safe_with_fallback(tekst, config)
            
            print(f"🧠 LLM odpowiada: {odpowiedz}")
            
            # Sprawdź czy odpowiedź nie jest błędem
            if odpowiedz.startswith("❌") or odpowiedz.startswith("[Błąd"):
                logger.loguj_blad("llm_error", odpowiedz, {"tekst": tekst, "model": model_llm})
                if "Brak kredytów API" in odpowiedz:
                    # Zachowaj oryginalną wiadomość o brakach kredytów
                    pass  # nie zmieniaj odpowiedzi
                else:
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

# === 4. Wykonanie intencji (bez zmian) ===
def wykonaj_intencje(intencja, tekst, tts_module):
    """
    Wykonuje konkretną intencję z logowaniem
    """
    odpowiedz = ""
    
    try:
        # === ISTNIEJĄCE INTENCJE ===
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
            rag_status = "dostępny" if RAG_AVAILABLE else "niedostępny"
            
            # NOWE: Dodaj info o limitach tokenów
            cached_models = len(token_manager.model_limits)
            odpowiedz = f"System AIA działa poprawnie. GPU: {gpu_status}, RAG: {rag_status}, Limity tokenów: {cached_models} modeli w cache"
            
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
        
        # === NOWE INTENCJE KULINARNE ===
        elif intencja in ["co_moge_zrobic_z_lodowki", "zaproponuj_dania", "dania_z_skladnikow"]:
            odpowiedz = obsługa_rag_ogolna(tekst, intencja)
            
        elif intencja == "dania_wege":
            odpowiedz = obsługa_rag_kategoria(tekst, "wege")
            
        elif intencja == "dania_niskotluszczowe":
            odpowiedz = obsługa_rag_kategoria(tekst, "niskotłuszczowa")
            
        elif intencja == "dania_niskocukrowe":
            odpowiedz = obsługa_rag_kategoria(tekst, "niskocukrowa")
            
        elif intencja == "kalorie_przepisu":
            odpowiedz = "Funkcja liczenia kalorii będzie wkrótce dostępna."
            
        elif intencja == "kalorie_produktu":
            odpowiedz = oblicz_kalorie_produktu(tekst)
            
        elif intencja == "przepis_szczegolowy":
            odpowiedz = "Szczegółowe przepisy będą dostępne w przyszłej wersji."
            
        elif intencja == "skladniki_na_danie":
            odpowiedz = "Funkcja wyświetlania składników będzie wkrótce dostępna."
            
        else:
            # NOWE: Nieznana intencja → przekaż do LLM
            print(f"❓ Nieznana intencja '{intencja}' - przekazuję do LLM...")
            
            try:
                model_llm = "LLM_fallback"  # Oznacz że to fallback
                odpowiedz_llm = zapytaj_llm_safe_with_fallback(tekst, {"llm_config": {"model": "openai/gpt-4-turbo", "max_tokens": 2048, "temperature": 0.65}})
                
                # Dodaj prefix żeby było widać źródło
                odpowiedz = f"🤖 [LLM za intencję '{intencja}']: {odpowiedz_llm}"
                
                # Zaloguj jako hybrydową odpowiedź
                logger.loguj_rozmowe(
                    tekst_wej=tekst,
                    tekst_wyj=odpowiedz,
                    intencja=intencja,
                    model_llm=model_llm,
                    czas_start=time.time(),
                    metadata={"typ": "intencja_llm_fallback", "original_intent": intencja}
                )
                
            except Exception as e:
                odpowiedz = f"❌ Zrozumiałem intencję '{intencja}', ale wystąpił błąd podczas przetwarzania: {str(e)}"
                logger.loguj_blad("intent_llm_fallback_error", str(e), {"intencja": intencja, "tekst": tekst})
            
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

# === 5. Funkcja kalorii ===
def oblicz_kalorie_produktu(tekst):
    """Wyciąga produkt i zwraca kalorie z bazy składników"""
    import re
    match = re.search(r'ile.*kalorii.*ma.*?([a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+)', tekst, re.IGNORECASE)
    
    if not match:
        return "Nie zrozumiałem o jaki produkt pytasz."
    
    produkt = match.group(1).lower()
    print(f"🔍 Szukam kalorii dla: {produkt}")
    
    # Sprawdź w bazie składników
    if RAG_AVAILABLE and recipe_rag:
        try:
            skladniki = recipe_rag.engine.loader.skladniki
            if produkt in skladniki:
                kalorie = skladniki[produkt]['kalorie_na_100g']
                waga = skladniki[produkt]['waga_standardowa'] 
                jednostka = skladniki[produkt]['jednostka']
                return f"{produkt.capitalize()} ma {kalorie} kalorii na 100g. Standardowa porcja ({waga}g/{jednostka}) to {int(kalorie * waga / 100)} kalorii."
            else:
                return f"Nie mam informacji o kaloriach dla {produkt}. Dostępne produkty: jajka, papryka, pomidor, łosoś, tofu..."
        except Exception as e:
            print(f"❌ Błąd sprawdzania kalorii: {e}")
            return "Wystąpił błąd podczas sprawdzania kalorii."
    else:
        return "System kalorii jest niedostępny."

# === 6. FUNKCJE RAG (bez zmian) ===
def wyciagnij_skladniki(tekst):
    """Wyciąga składniki z tekstu użytkownika"""
    # Lista możliwych składników (z bazy danych)
    mozliwe_skladniki = [
        "awokado", "banan", "brokuły", "cebula", "chleb", "cukinia", "cytryna", 
        "czosnek", "imbir", "jajka", "jarmuż", "kapary", "kasza", "koperek",
        "kurczak", "marchewka", "mleko", "ocet", "ogórek", "oliwa", "papryka",
        "pieprz", "pomidor", "soczewica", "sos", "szpinak", "słonecznik", "tofu", "łosoś"
    ]
    
    znalezione = []
    tekst_lower = tekst.lower()
    
    for skladnik in mozliwe_skladniki:
        if skladnik in tekst_lower:
            znalezione.append(skladnik)
    
    return znalezione

def obsługa_rag_ogolna(tekst, intencja):
    """Obsługa ogólnych zapytań RAG"""
    if not RAG_AVAILABLE:
        return "Przepraszam, system przepisów jest chwilowo niedostępny."
    
    # Wyciągnij składniki z tekstu
    skladniki = wyciagnij_skladniki(tekst)
    
    if not skladniki:
        return "Nie rozpoznałem żadnych składników. Spróbuj: 'mam jajka, paprykę, pomidory'"
    
    print(f"🔍 Znalezione składniki: {skladniki}")
    
    # Wyszukaj przepisy
    result = recipe_rag.suggest_recipes(skladniki, max_results=3)
    
    if result.get('found_recipes', 0) == 0:
        return f"Nie znalazłem przepisów z {', '.join(skladniki)}. Spróbuj innych składników."
    
    # Sformułuj odpowiedź
    odpowiedz = f"Z {', '.join(skladniki)} mogę zaproponować: "
    
    for category, recipes in result.get('by_category', {}).items():
        cat_name = {"wege": "wegetariańskie", "niskotłuszczowa": "niskotłuszczowe", 
                   "niskocukrowa": "niskocukrowe", "keto": "keto"}.get(category, category)
        
        recipe_names = [r['title'] for r in recipes[:2]]  # max 2 z kategorii
        odpowiedz += f"{cat_name}: {', '.join(recipe_names)}. "
    
    return odpowiedz

def obsługa_rag_kategoria(tekst, kategoria):
    """Obsługa zapytań z konkretną kategorią"""
    if not RAG_AVAILABLE:
        return "Przepraszam, system przepisów jest chwilowo niedostępny."
    
    # Wyciągnij składniki jeśli są
    skladniki = wyciagnij_skladniki(tekst)
    
    if not skladniki:
        # Brak składników - pokaż ogólne przepisy z kategorii
        result = recipe_rag.suggest_recipes([''], category=kategoria, max_results=3)
    else:
        # Z konkretnymi składnikami
        result = recipe_rag.suggest_recipes(skladniki, category=kategoria, max_results=3)
    
    if result.get('found_recipes', 0) == 0:
        cat_name = {"wege": "wegetariańskich", "niskotłuszczowa": "niskotłuszczowych", 
                   "niskocukrowa": "niskocukrowych"}.get(kategoria, kategoria)
        return f"Nie znalazłem {cat_name} przepisów. Spróbuj innych składników."
    
    # Sformułuj odpowiedź
    cat_name = {"wege": "wegetariańskie", "niskotłuszczowa": "niskotłuszczowe", 
               "niskocukrowa": "niskocukrowe"}.get(kategoria, kategoria)
    
    recipes = result.get('all_recipes', [])
    recipe_names = [r['title'] for r in recipes[:3]]
    
    if skladniki:
        odpowiedz = f"Dania {cat_name} z {', '.join(skladniki)}: {', '.join(recipe_names)}"
    else:
        odpowiedz = f"Proponuję {cat_name} dania: {', '.join(recipe_names)}"
    
    return odpowiedz

# === 7. Funkcje pomocnicze ===
def dodaj_komende(wzorzec, intencja):
    """Dodaje nową komendę do listy (w runtime)"""
    KOMENDY.append({"wzorzec": wzorzec, "intencja": intencja})
    print(f"✅ Dodano komendę: {wzorzec} -> {intencja}")

def lista_intencji():
    """Zwraca listę wszystkich dostępnych intencji"""
    return [komenda["intencja"] for komenda in KOMENDY]

# NOWA FUNKCJA: Info o tokenach
def sprawdz_limity_tokenow():
    """Zwraca informacje o zapisanych limitach tokenów"""
    return token_manager.model_limits

def wyczysc_cache_tokenow():
    """Czyści cache limitów tokenów"""
    token_manager.model_limits = {}
    token_manager.save_cache()
    print("🧹 Wyczyszczono cache limitów tokenów")

# === Test lokalny ===
if __name__ == "__main__":
    print("🧪 Test modułu rozumienie z RAG i bezpiecznymi tokenami")
    
    # Mock config i TTS dla testów
    mock_config = {
        "local_config": {"styl": "precyzyjny"},
        "llm_config": {"model": "openai/gpt-4-turbo", "max_tokens": 2048}
    }
    
    class MockTTS:
        def mow_tekstem(self, tekst):
            print(f"[MOCK TTS]: {tekst}")
    
    mock_tts = MockTTS()
    
    # Testy
    print("\n--- Test 1: Zapytanie o godzinę ---")
    analizuj("która godzina?", mock_config, mock_tts)
    
    print("\n--- Test 2: RAG - składniki ---")
    analizuj("mam jajka i paprykę co mogę zrobić", mock_config, mock_tts)
    
    print("\n--- Test 3: Status systemu z tokenami ---") 
    analizuj("status systemu", mock_config, mock_tts)
    
    print("\n--- Test 4: Sprawdź limity tokenów ---")
    print("Zapisane limity:", sprawdz_limity_tokenow())