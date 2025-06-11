# ===================================================================
# CORE/ROZUMIENIE.PY - GŁÓWNY MODUŁ PRZETWARZANIA JĘZYKA NATURALNEGO
# ===================================================================
# Wersja: AIA v2.1 + Ollama Support
# Opis: System 3-poziomowego rozpoznawania intencji + zarządzanie tokenami + Ollama
# Komponenty: TokenManager, LLM Intent Classifier, RAG, Intencje lokalne, Ollama
# ===================================================================

import json
import re
import time
import os
from llm import llm_openrouter

# Import Ollama z fallback
try:
    from llm import llm_ollama
    OLLAMA_AVAILABLE = True
    print("✅ Moduł Ollama załadowany")
except ImportError:
    OLLAMA_AVAILABLE = False
    print("⚠️ Moduł Ollama niedostępny")

from core import logger

# ===================================================================
# IMPORT UNIVERSAL INTELLIGENT ASSISTANT - NOWY SYSTEM
# ===================================================================

# Import Universal Assistant z fallback
try:
    from core.universal_intelligent_assistant import universal_intelligent_assistant
    UNIVERSAL_ASSISTANT_AVAILABLE = True
    print("✅ Universal Intelligent Assistant załadowany")
except ImportError:
    UNIVERSAL_ASSISTANT_AVAILABLE = False
    print("⚠️ Universal Assistant niedostępny - używam klasycznego systemu")

# Konfiguracja Universal Assistant
UNIVERSAL_ASSISTANT_CONFIG = {
    "enabled": True,  # Domyślnie włączony
    "fallback_to_classic": True,  # Fallback na klasyczny system przy błędzie
    "auto_context_detection": True,  # Automatyczne wykrywanie kontekstu
    "supported_contexts": ["cooking", "smart_home", "calendar", "finance", "general"]
}

print(f"🤖 Universal Assistant: {'ENABLED' if UNIVERSAL_ASSISTANT_AVAILABLE else 'DISABLED'}")

# ===================================================================
# 📋 SEKCJA 1: FUNKCJE POMOCNICZE - PRZETWARZANIE TEKSTU
# ===================================================================

def wypowiedz_bez_prefixow(odpowiedz):
    """
    Usuwa prefixy wizualne przed wysłaniem do TTS
    
    Usuwa znaczniki:
    - 🤖 [LLM za intencję 'nazwa']: 
    - 🧠 [Czysty LLM]: 
    - 🧠 [Ollama LLM]:  # ← DODANE
    
    Returns:
        str: Tekst bez prefixów wizualnych
    """
    clean_text = re.sub(r'^🤖 \[LLM za intencję.*?\]: ', '', odpowiedz)
    clean_text = re.sub(r'^🧠 \[Czysty LLM\]: ', '', clean_text)
    clean_text = re.sub(r'^🧠 \[Ollama LLM\]: ', '', clean_text)  # ← DODAJ TĘ LINIĘ
    return clean_text

# ===================================================================
# 🔐 SEKCJA 2: TOKEN MANAGER - ZARZĄDZANIE LIMITAMI API
# ===================================================================

class TokenManager:
    """
    Klasa zarządzająca limitami tokenów dla różnych modeli LLM
    
    Funkcje:
    - Auto-wykrywanie limitów z błędów 402
    - Persistent cache w data/token_limits.json
    - Bezpieczne startowe wartości
    - Fallback między modelami
    """
    
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
        """
        Zwraca bezpieczną liczbę tokenów dla modelu
        
        Args:
            model (str): Nazwa modelu (np. "openai/gpt-4-turbo")
            requested_tokens (int): Żądana liczba tokenów
            
        Returns:
            int: Bezpieczna liczba tokenów
        """
        if model in self.model_limits:
            safe_limit = min(requested_tokens, self.model_limits[model])
            print(f"🔒 Model {model}: używam zapisanego limitu {safe_limit} tokenów")
            return safe_limit
        else:
            print(f"🆕 Model {model}: pierwsza próba z {self.default_safe_tokens} tokenów")
            return min(requested_tokens, self.default_safe_tokens)
    
    def handle_402_error(self, model, error_message):
        """
        Wyciąga i zapisuje rzeczywisty limit z błędu 402
        
        Args:
            model (str): Nazwa modelu
            error_message (str): Komunikat błędu z API
            
        Returns:
            int: Rzeczywisty limit tokenów
        """
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

# ===================================================================
# 🎛️ SEKCJA 2.5: INTENT RECOGNIZER - SWITCHER METOD ROZPOZNAWANIA
# ===================================================================

class IntentRecognizer:
    """
    Klasa zarządzająca różnymi metodami rozpoznawania intencji
    
    Obsługuje:
    - regex_only: tylko wzorce regex
    - regex_plus_simple: regex + prosty LLM
    - regex_plus_few_shot: regex + few-shot LLM
    """
    
    def __init__(self, config):
        self.method = config.get("recognition_config", {}).get("method", "regex_plus_simple")
        self.confidence_threshold = config.get("recognition_config", {}).get("confidence_threshold", 0.7)
        self.use_context = config.get("recognition_config", {}).get("use_context", False)
        self.debug_mode = config.get("recognition_config", {}).get("debug_mode", False)
        self.previous_context = ""
        
        if self.debug_mode:
            print(f"🎛️ IntentRecognizer: method={self.method}, confidence={self.confidence_threshold}")
    
    def classify_intent(self, tekst, dostepne_intencje, config):
        """Główna funkcja klasyfikacji z wyborem metody"""
        
        if self.debug_mode:
            print(f"🔍 Debug: Klasyfikuję '{tekst}' metodą {self.method}")
        
        # KROK 1: Zawsze sprawdź regex (najszybsze)
        regex_result = self._try_regex(tekst, dostepne_intencje)
        if regex_result:
            if self.debug_mode:
                print(f"✅ Debug: Regex znalazł '{regex_result}'")
            return regex_result, "regex"
        
        # KROK 2: Jeśli method == "regex_only", kończymy
        if self.method == "regex_only":
            if self.debug_mode:
                print("❌ Debug: Regex_only - brak dopasowania")
            return None, "regex_only"
        
        # KROK 3: Próbuj LLM classifier
        if self.method in ["regex_plus_simple", "regex_plus_few_shot"]:
            llm_result = self._try_llm_classifier(tekst, dostepne_intencje, config)
            if llm_result:
                if self.debug_mode:
                    print(f"✅ Debug: LLM znalazł '{llm_result}'")
                return llm_result, "llm_classifier"
        
        if self.debug_mode:
            print("❌ Debug: Żadna metoda nie znalazła intencji")
        return None, "no_match"
    
    def _try_regex(self, tekst, dostepne_intencje):
        """Próbuje dopasować regex patterns"""
        for komenda in dostepne_intencje:
            try:
                wzorzec = komenda["wzorzec"]
                intencja = komenda["intencja"]
                if re.search(wzorzec, tekst, re.IGNORECASE):
                    return intencja
            except (KeyError, re.error):
                continue
        return None
    
    def _try_llm_classifier(self, tekst, dostepne_intencje, config):
        """Próbuje LLM classifier"""
        if self.method == "regex_plus_simple":
            return klasyfikuj_intencje_llm_simple(tekst, dostepne_intencje, config)
        elif self.method == "regex_plus_few_shot":
            return klasyfikuj_intencje_llm_few_shot(tekst, dostepne_intencje, config)
        return None

# Globalna instancja (zostanie utworzona w analizuj())
intent_recognizer = None

# ===================================================================
# 🧠 SEKCJA 3: RAG SYSTEM - INICJALIZACJA I KONFIGURACJA  
# ===================================================================

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

# ===================================================================
# RAG ADAPTER DLA UNIVERSAL ASSISTANT - KOMPATYBILNOŚĆ
# ===================================================================
class RagEngineAdapter:
    """
    Adapter dla kompatybilności między RecipeRAG a Universal Assistant
    Konwertuje interfejs RecipeRAG na RagEngine wymagany przez Universal Assistant
    """
    def __init__(self, recipe_rag_instance):
        self.recipe_rag = recipe_rag_instance
    
    def search_relevant(self, query):
        """Interfejs wymagany przez Universal Assistant"""
        if not self.recipe_rag:
            return []
        
        try:
            # Użyj istniejącej funkcji suggest_recipes
            result = self.recipe_rag.suggest_recipes([query], max_results=5)
            recipes = result.get('all_recipes', [])
            
            print(f"🔍 RAG Adapter: '{query}' → {len(recipes)} wyników")
            return recipes
            
        except Exception as e:
            print(f"❌ Błąd RAG Adapter: {e}")
            return []

# Stwórz adapter dla Universal Assistant
if RAG_AVAILABLE and recipe_rag:
    rag_adapter = RagEngineAdapter(recipe_rag)
    print("✅ RAG Adapter utworzony dla Universal Assistant")
else:
    rag_adapter = None
    print("⚠️ RAG Adapter niedostępny")

# ===================================================================
# 📚 SEKCJA 4: KOMENDY PREDEFINIOWANE - WCZYTANIE I WALIDACJA
# ===================================================================

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

# ===================================================================
# 🤖 SEKCJA 5: LLM PROVIDERS - SWITCHER MIĘDZY OLLAMA I OPENROUTER
# ===================================================================

def zapytaj_llm_safe(tekst, config, max_retries=2):
    """
    Uniwersalna funkcja LLM z auto-switcherem provider
    
    Obsługuje:
    - provider: "openrouter" → llm_openrouter
    - provider: "ollama" → llm_ollama (lokalny)
    - Auto-fallback między providerami
    
    Args:
        tekst (str): Tekst zapytania
        config (dict): Konfiguracja z provider i model
        max_retries (int): Maksymalne próby
        
    Returns:
        str: Odpowiedź LLM lub komunikat błędu
    """
    
    provider = config.get("llm_config", {}).get("provider", "openrouter")
    model = config.get("llm_config", {}).get("model", "")
    
    print(f"🎯 Provider: {provider}, Model: {model}")
    
    # ===============================================================
    # OLLAMA (LOKALNY)
    # ===============================================================
    if provider == "ollama":
        if not OLLAMA_AVAILABLE:
            print("❌ Ollama nie jest dostępny - fallback na OpenRouter")
            return zapytaj_openrouter_safe(tekst, config, max_retries)
        
        try:
            return llm_ollama.odpowiedz(tekst, config)
        except Exception as e:
            print(f"❌ Błąd Ollama: {e}")
            
            # Fallback na OpenRouter jeśli Ollama nie działa
            print("🔄 Fallback na OpenRouter...")
            return zapytaj_openrouter_safe(tekst, config, max_retries)
    
    # ===============================================================
    # OPENROUTER (CHMURA)
    # ===============================================================
    else:
        return zapytaj_openrouter_safe(tekst, config, max_retries)

def zapytaj_openrouter_safe(tekst, config, max_retries=2):
    """
    Bezpieczne zapytanie OpenRouter LLM z auto-adjustem tokenów
    (stara funkcja zapytaj_llm_safe, ale tylko dla OpenRouter)
    """
    
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

def zapytaj_llm_safe_with_fallback(tekst, config, max_retries=2):
    """
    Próbuje różne modele jeśli główny nie ma kredytów
    Teraz z obsługą Ollama
    """
    
    provider = config.get("llm_config", {}).get("provider", "openrouter")
    
    # Jeśli to Ollama - użyj prostego zapytania
    if provider == "ollama":
        return zapytaj_llm_safe(tekst, config, max_retries)
    
    # OpenRouter - próbuj różne modele
    modele = [config["llm_config"]["model"]]
    
    if "alternative_models" in config["llm_config"]:
        modele.extend(config["llm_config"]["alternative_models"])
    
    for model in modele:
        print(f"🎯 Próbuję model: {model}")
        
        temp_config = config.copy()
        temp_config["llm_config"]["model"] = model
        
        result = zapytaj_openrouter_safe(tekst, temp_config, max_retries)
        
        if not ("Brak kredytów API" in result or "can only afford" in result):
            return result
            
        print(f"❌ Model {model} wymaga kredytów, próbuję następny...")
    
    return "❌ Wszystkie modele wymagają doładowania kredytów"

# ===================================================================
# 🤖 SEKCJA 6: LLM INTENT CLASSIFIERS - RÓŻNE METODY
# ===================================================================

def klasyfikuj_intencje_llm_simple(tekst, dostepne_intencje, config):
    """Prosty LLM classifier (stara wersja)"""
    
    intencje_lista = ", ".join([k["intencja"] for k in dostepne_intencje])
    
    prompt_klasyfikacji = f"""UWAGA: Odpowiadaj WYŁĄCZNIE po polsku!

Przeanalizuj tekst użytkownika: "{tekst}"

Dostępne polskie intencje: {intencje_lista}

ZADANIE: Wybierz dokładnie JEDNĄ intencję z listy która pasuje do tekstu.
- Jeśli tekst mówi o składnikach i gotowaniu → "dania_z_skladnikow"  
- Jeśli pyta o kalorie → "kalorie_produktu"
- Jeśli pyta o godzinę → "zapytanie_godzina"
- Jeśli żadna nie pasuje → "brak_dopasowania"

ODPOWIEDŹ (TYLKO nazwa intencji po polsku):"""

    try:
       # Użyj tej samej konfiguracji co główny system
        config_klasyfikacja = config.copy()
        config_klasyfikacja["llm_config"]["max_tokens"] = 50
        config_klasyfikacja["llm_config"]["temperature"] = 0.1
        
        print(f"🔍 Simple LLM klasyfikuje: '{tekst[:50]}...'")
        odpowiedz = zapytaj_llm_safe(prompt_klasyfikacji, config_klasyfikacja, max_retries=1)
        
        # Wyczyść odpowiedź
        intencja = odpowiedz.strip().replace("🧠 [Czysty LLM]: ", "").strip()
        
        # Sprawdź czy to prawidłowa intencja
        if intencja in [k["intencja"] for k in dostepne_intencje]:
            print(f"✅ Simple LLM rozpoznał: {intencja}")
            return intencja
        elif intencja == "brak_dopasowania":
            print(f"❌ Simple LLM nie rozpoznał intencji")
            return None
        else:
            print(f"⚠️ Simple LLM zwrócił nieprawidłową intencję: {intencja}")
            return None
            
    except Exception as e:
        print(f"❌ Błąd simple klasyfikacji: {e}")
        return None

def klasyfikuj_intencje_llm_few_shot(tekst, dostepne_intencje, config):
    """Few-shot LLM classifier (ulepszona wersja)"""
    
    # Few-shot examples
    examples = """PRZYKŁADY KLASYFIKACJI:

    "Która godzina?" → zapytanie_godzina
    "Która jest godzina?" → zapytanie_godzina  
    "Którą mamy godzinę?" → zapytanie_godzina
    "Powiedz mi godzinę" → zapytanie_godzina
    "Jaki mamy czas?" → zapytanie_godzina

    "Jak się masz?" → zapytanie_samopoczucie  
    "Co u ciebie?" → zapytanie_samopoczucie
    "Jak leci?" → zapytanie_samopoczucie
    "Co słychać?" → zapytanie_samopoczucie
    "Jak tam?" → zapytanie_samopoczucie

    "Do zobaczenia!" → pozegnanie
    "Na razie" → pozegnanie
    "Żegnaj" → pozegnanie
    "Do widzenia" → pozegnanie
    "Papa" → pozegnanie

    "Ile kalorii ma jajko?" → kalorie_produktu
    "Kalorie w pomidorze?" → kalorie_produktu
    "Ile kalorii to ma?" → kalorie_produktu

    "Mam jajka, co zrobić?" → dania_z_skladnikow
    "Co można z tego ugotować?" → dania_z_skladnikow
    "Co mogę przygotować?" → dania_z_skladnikow
    "Mam pomidor, co zrobić?" → dania_z_skladnikow

    "Opowiedz dowcip" → brak_dopasowania
    "Jak działa samolot?" → brak_dopasowania
    "Czy jutro będzie padać deszcz?" → brak_dopasowania"""

    intencje_lista = ", ".join([k["intencja"] for k in dostepne_intencje])
    
    prompt = f"""{examples}

ZADANIE: Przeanalizuj tekst i wybierz najlepszą intencję.

TEKST: "{tekst}"
DOSTĘPNE INTENCJE: {intencje_lista}

INSTRUKCJE:
- Jeśli tekst pasuje do intencji z listy → zwróć nazwę
- Jeśli nie pasuje do żadnej → zwróć "brak_dopasowania"  
- Zwróć TYLKO nazwę intencji

ODPOWIEDŹ:"""

    try:
        config_klasyfikacja = {
            "llm_config": {
                "provider": "openrouter",  # Zawsze OpenRouter dla klasyfikacji
                "model": "openai/gpt-3.5-turbo",
                "max_tokens": 50,
                "temperature": 0.1
            }
        }
        
        print(f"🔍 Few-shot LLM klasyfikuje: '{tekst[:50]}...'")
        odpowiedz = zapytaj_llm_safe(prompt, config_klasyfikacja, max_retries=1)
        
        # Wyczyść odpowiedź
        intencja = odpowiedz.strip().replace("🧠 [Czysty LLM]: ", "").strip()
        
        # Sprawdź czy to prawidłowa intencja
        if intencja in [k["intencja"] for k in dostepne_intencje]:
            print(f"✅ Few-shot LLM rozpoznał: {intencja}")
            return intencja
        elif intencja == "brak_dopasowania":
            print(f"❌ Few-shot LLM nie rozpoznał intencji")
            return None
        else:
            print(f"⚠️ Few-shot LLM zwrócił nieprawidłową intencję: {intencja}")
            return None
            
    except Exception as e:
        print(f"❌ Błąd few-shot klasyfikacji: {e}")
        return None

# ===================================================================
# 🎯 SEKCJA 7: GŁÓWNA LOGIKA ANALIZY - SWITCHER SYSTEM
# ===================================================================

def analizuj(tekst, config, tts_module):
    """
    Główna funkcja analizy tekstu z switcherem metod rozpoznawania
    
    Nowy system:
    1. IntentRecognizer wybiera metodę z config
    2. Różne metody: regex_only, regex_plus_simple, regex_plus_few_shot
    3. Fallback na czysty LLM jeśli nic nie pasuje
    4. Obsługa Ollama + OpenRouter
    
    Args:
        tekst (str): Tekst użytkownika
        config (dict): Konfiguracja systemu
        tts_module: Moduł Text-to-Speech
        
    Returns:
        str: Odpowiedź systemu
    """
    start_time = time.time()
    intencja = None
    model_llm = None
    odpowiedz = ""
    
    print("📥 Otrzymano polecenie:", tekst)

    try:
        # ===============================================================
        # NOWY SYSTEM: SWITCHER METOD ROZPOZNAWANIA
        # ===============================================================
        
        # Inicjalizuj recognizer z config
        global intent_recognizer
        intent_recognizer = IntentRecognizer(config)
        
        # Użyj wybranej metody klasyfikacji
        intencja, method_used = intent_recognizer.classify_intent(tekst, KOMENDY, config)
        
        if intencja:
            print(f"✅ Rozpoznano intencję ({method_used}): {intencja}")
            
            # Loguj rozpoznaną intencję
            logger.loguj_intencje(intencja, tekst)
            
            # Wykonaj intencję
            odpowiedz = wykonaj_intencje(intencja, tekst, tts_module, config)
            
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
                    metadata={"typ": f"intencja_{method_used}", "method": method_used}
                )
            
            return odpowiedz

        # ===============================================================
        # POZIOM 3: CZYSTY LLM - OGÓLNA ROZMOWA
        # ===============================================================
        print("🤖 Żadna metoda nie rozpoznała intencji – pytam LLM...")
        
        try:
            model_llm = config["llm_config"]["model"]
            provider = config.get("llm_config", {}).get("provider", "openrouter")
            
            # Użyj bezpiecznej funkcji LLM z fallback
            polish_prompt = f"Odpowiadaj TYLKO po polsku. Użytkownik powiedział: '{tekst}'"
            odpowiedz = zapytaj_llm_safe_with_fallback(polish_prompt, config)
            
            # Dodaj prefix żeby było widać że to czysty LLM
            if not odpowiedz.startswith("❌"):
                if provider == "ollama":
                    odpowiedz = f"🧠 [Ollama LLM]: {odpowiedz}"
                else:
                    odpowiedz = f"🧠 [Czysty LLM]: {odpowiedz}"
            
            print(f"🧠 LLM odpowiada: {odpowiedz}")
            
            # Sprawdź czy odpowiedź nie jest błędem
            if odpowiedz.startswith("❌") or odpowiedz.startswith("[Błąd"):
                logger.loguj_blad("llm_error", odpowiedz, {"tekst": tekst, "model": model_llm})
                if "Brak kredytów API" in odpowiedz:
                    # Zachowaj oryginalną wiadomość o brakach kredytów
                    pass  # nie zmieniaj odpowiedzi
                else:
                    odpowiedz = "Przepraszam, wystąpił problem z połączeniem. Spróbuj ponownie."
            
            # NAPRAWIONE: Wypowiedz odpowiedź BEZ prefixów
            tts_module.mow_tekstem(wypowiedz_bez_prefixow(odpowiedz))
            
            # Loguj rozmowę LLM
            logger.loguj_rozmowe(
                tekst_wej=tekst,
                tekst_wyj=odpowiedz,
                intencja=None,
                model_llm=model_llm,
                czas_start=start_time,
                metadata={"typ": "llm_response", "provider": provider}
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

# ===================================================================
# 🍳 SEKCJA 8: FUNKCJE RAG - SYSTEM PRZEPISÓW KULINARNYCH
# ===================================================================

def wyciagnij_skladniki(tekst):
    """
    Wyciąga składniki z tekstu użytkownika
    
    Przeszukuje tekst pod kątem znanych składników z bazy.
    Używa prostego dopasowania stringów (case-insensitive).
    
    Args:
        tekst (str): Tekst użytkownika
        
    Returns:
        list: Lista znalezionych składników
    """
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
    """
    Obsługa ogólnych zapytań RAG - wyszukiwanie przepisów
    
    Proces:
    1. Wyciągnij składniki z tekstu
    2. Wyszukaj przepisy w RAG engine
    3. Sformułuj odpowiedź z kategoryzacją
    
    Args:
        tekst (str): Tekst użytkownika
        intencja (str): Rozpoznana intencja
        
    Returns:
        str: Odpowiedź z propozycjami przepisów
    """
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
    """
    Obsługa zapytań z konkretną kategorią diety
    
    Obsługuje kategorie: wege, niskotłuszczowa, niskocukrowa, keto
    
    Args:
        tekst (str): Tekst użytkownika
        kategoria (str): Kategoria diety
        
    Returns:
        str: Odpowiedź z przepisami z danej kategorii
    """
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

# ===================================================================
# 🔢 SEKCJA 8.1: SYSTEM KALORII - OBLICZENIA WARTOŚCI ODŻYWCZYCH
# ===================================================================

def oblicz_kalorie_produktu(tekst):
    """
    Wyciąga produkt z tekstu i zwraca kalorie z bazy składników
    
    Regex pattern: "ile.*kalorii.*ma.*produkt"
    Źródło danych: recipe_rag.engine.loader.skladniki
    
    Args:
        tekst (str): Tekst użytkownika z pytaniem o kalorie
        
    Returns:
        str: Informacja o kaloriach produktu
    """
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

# ===================================================================
# 🎭 SEKCJA 9: WYKONANIE INTENCJI - LOKALNE IMPLEMENTACJE
# ===================================================================

def wykonaj_intencje(intencja, tekst, tts_module, config):
    """
    Wykonuje konkretną intencję z pełnym logowaniem
    
    Obsługuje:
    - Intencje podstawowe (godzina, data, powitania)
    - Intencje systemowe (status, pamięć)  
    - Intencje kulinarne (RAG)
    - Fallback na LLM dla nieznanych intencji
    
    Args:
        intencja (str): Nazwa intencji do wykonania
        tekst (str): Oryginalny tekst użytkownika
        tts_module: Moduł Text-to-Speech
        config (dict): Konfiguracja systemu
        
    Returns:
        str: Odpowiedź systemu
    """
    odpowiedz = ""
    
    try:
        # ===============================================================
        # GRUPA 9.1: INTENCJE PODSTAWOWE - CZAS I POWITANIA
        # ===============================================================
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
            
        elif intencja == "zapytanie_samopoczucie":
            import random
            samopoczucie = [
                "Dzięki za pytanie! Wszystko w porządku!",
                "Świetnie się mam! Gotowy do pomocy!",
                "Doskonale! Co mogę dla Ciebie zrobić?"
            ]
            odpowiedz = random.choice(samopoczucie)
            
        # ===============================================================
        # GRUPA 9.2: INTENCJE SYSTEMOWE - STATUS I DIAGNOSTYKA
        # ===============================================================
        elif intencja == "status_systemu":
            import torch
            gpu_status = "aktywne" if torch.cuda.is_available() else "nieaktywne"
            rag_status = "dostępny" if RAG_AVAILABLE else "niedostępny"
            ollama_status = "dostępny" if OLLAMA_AVAILABLE else "niedostępny"
            
            # Dodaj info o limitach tokenów i metodzie rozpoznawania
            cached_models = len(token_manager.model_limits)
            method = intent_recognizer.method if intent_recognizer else "unknown"
            provider = config.get("llm_config", {}).get("provider", "openrouter")
            model = config.get("llm_config", {}).get("model", "unknown")
            
            odpowiedz = f"System AIA działa poprawnie. GPU: {gpu_status}, RAG: {rag_status}, Ollama: {ollama_status}, Provider: {provider}, Model: {model}, Metoda: {method}, Cache tokenów: {cached_models} modeli"
            
        # ===============================================================
        # GRUPA 9.3: INTENCJE PAMIĘCI - NOTATKI I WIADOMOŚCI
        # ===============================================================
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
        
        # ===============================================================
        # GRUPA 9.4: INTENCJE KULINARNE - RAG SYSTEM
        # ===============================================================
        elif intencja in ["co_moge_zrobic_z_lodowki", "zaproponuj_dania", "dania_z_skladnikow"]:
            odpowiedz = obsługa_rag_ogolna(tekst, intencja)
            
        elif intencja == "dania_wege":
            odpowiedz = obsługa_rag_kategoria(tekst, "wege")
            
        elif intencja == "dania_niskotluszczowe":
            odpowiedz = obsługa_rag_kategoria(tekst, "niskotłuszczowa")
            
        elif intencja == "dania_niskocukrowe":
            odpowiedz = obsługa_rag_kategoria(tekst, "niskocukrowa")
            
        elif intencja == "kalorie_produktu":
            odpowiedz = oblicz_kalorie_produktu(tekst)
            
        # ===============================================================
        # GRUPA 9.5: INTENCJE PLACEHOLDER - DO IMPLEMENTACJI
        # ===============================================================
        elif intencja == "kalorie_przepisu":
            odpowiedz = "Funkcja liczenia kalorii będzie wkrótce dostępna."
            
        elif intencja == "przepis_szczegolowy":
            odpowiedz = "Szczegółowe przepisy będą dostępne w przyszłej wersji."
            
        elif intencja == "skladniki_na_danie":
            odpowiedz = "Funkcja wyświetlania składników będzie wkrótce dostępna."
            
        # ===============================================================
        # GRUPA 9.6: FALLBACK LLM - NIEZNANE INTENCJE
        # ===============================================================
        else:
            # Nieznana intencja → przekaż do LLM
            print(f"❓ Nieznana intencja '{intencja}' - przekazuję do LLM...")
            
            try:
                model_llm = "LLM_fallback"  # Oznacz że to fallback
                provider = config.get("llm_config", {}).get("provider", "openrouter")
                odpowiedz_llm = zapytaj_llm_safe_with_fallback(tekst, config)
                
                # Dodaj prefix żeby było widać źródło
                if provider == "ollama":
                    odpowiedz = f"🤖 [Ollama za intencję '{intencja}']: {odpowiedz_llm}"
                else:
                    odpowiedz = f"🤖 [LLM za intencję '{intencja}']: {odpowiedz_llm}"
                
                # Zaloguj jako hybrydową odpowiedź
                logger.loguj_rozmowe(
                    tekst_wej=tekst,
                    tekst_wyj=odpowiedz,
                    intencja=intencja,
                    model_llm=model_llm,
                    czas_start=time.time(),
                    metadata={"typ": "intencja_llm_fallback", "original_intent": intencja, "provider": provider}
                )
                
            except Exception as e:
                odpowiedz = f"❌ Zrozumiałem intencję '{intencja}', ale wystąpił błąd podczas przetwarzania: {str(e)}"
                logger.loguj_blad("intent_llm_fallback_error", str(e), {"intencja": intencja, "tekst": tekst})
            
    except Exception as e:
        logger.loguj_blad("intencja_error", f"Błąd podczas wykonywania intencji {intencja}: {e}", {"tekst": tekst})
        odpowiedz = "Przepraszam, wystąpił błąd podczas wykonywania polecenia."

    # ===================================================================
    # SEKCJA 9.7: FINALIZACJA - TTS I RETURN
    # ===================================================================
    
    # Wyświetl i wypowiedz odpowiedź
    print(f"🗣️ AIA odpowiada: {odpowiedz}")
    try:
        # NAPRAWIONE: Usuń prefixy przed TTS
        tts_module.mow_tekstem(wypowiedz_bez_prefixow(odpowiedz))
    except Exception as e:
        logger.loguj_blad("tts_error", f"Błąd TTS: {e}", {"odpowiedz": odpowiedz})

    return odpowiedz

# ===================================================================
# 🛠️ SEKCJA 10: FUNKCJE POMOCNICZE - ZARZĄDZANIE I DIAGNOSTYKA
# ===================================================================

def dodaj_komende(wzorzec, intencja):
    """
    Dodaje nową komendę do listy (w runtime)
    
    Args:
        wzorzec (str): Wzorzec regex
        intencja (str): Nazwa intencji
    """
    KOMENDY.append({"wzorzec": wzorzec, "intencja": intencja})
    print(f"✅ Dodano komendę: {wzorzec} -> {intencja}")

def lista_intencji():
    """
    Zwraca listę wszystkich dostępnych intencji
    
    Returns:
        list: Lista nazw intencji
    """
    return [komenda["intencja"] for komenda in KOMENDY]

def sprawdz_limity_tokenow():
    """
    Zwraca informacje o zapisanych limitach tokenów
    
    Returns:
        dict: Słownik z limitami per model
    """
    return token_manager.model_limits

def wyczysc_cache_tokenow():
    """
    Czyści cache limitów tokenów
    """
    token_manager.model_limits = {}
    token_manager.save_cache()
    print("🧹 Wyczyszczono cache limitów tokenów")

def get_recognition_stats():
    """
    Zwraca statystyki rozpoznawania
    
    Returns:
        dict: Statystyki aktualnej sesji
    """
    if intent_recognizer:
        return {
            "method": intent_recognizer.method,
            "confidence_threshold": intent_recognizer.confidence_threshold,
            "use_context": intent_recognizer.use_context,
            "debug_mode": intent_recognizer.debug_mode
        }
    return {"status": "not_initialized"}

def get_llm_stats():
    """
    Zwraca statystyki LLM i provider
    
    Returns:
        dict: Informacje o aktualnej konfiguracji LLM
    """
    return {
        "ollama_available": OLLAMA_AVAILABLE,
        "token_limits_cached": len(token_manager.model_limits),
        "cache_file": token_manager.cache_file
    }

# ===================================================================
# 🧪 SEKCJA 11: TESTY LOKALNE - ROZWÓJ I DIAGNOSTYKA
# ===================================================================

if __name__ == "__main__":
    print("🧪 Test modułu rozumienie z obsługą Ollama")
    
    # Mock config i TTS dla testów
    mock_config_openrouter = {
        "local_config": {"styl": "precyzyjny"},
        "llm_config": {
            "provider": "openrouter",
            "model": "openai/gpt-3.5-turbo", 
            "max_tokens": 2048
        },
        "recognition_config": {
            "method": "regex_plus_few_shot",
            "confidence_threshold": 0.7,
            "debug_mode": True
        }
    }
    
    mock_config_ollama = {
        "local_config": {"styl": "precyzyjny"},
        "llm_config": {
            "provider": "ollama",
            "model": "llama3.1:8b",
            "base_url": "http://localhost:11434",
            "max_tokens": 2048,
            "temperature": 0.7
        },
        "recognition_config": {
            "method": "regex_plus_simple",
            "confidence_threshold": 0.7,
            "debug_mode": True
        }
    }
    
    class MockTTS:
        def mow_tekstem(self, tekst):
            print(f"[MOCK TTS]: {tekst}")
    
    mock_tts = MockTTS()
    
    # Testy poszczególnych komponentów
    print("\n--- Test 1: Zapytanie o godzinę (regex) ---")
    analizuj("która godzina?", mock_config_ollama, mock_tts)
    
    print("\n--- Test 2: Status systemu ---") 
    analizuj("status systemu", mock_config_ollama, mock_tts)
    
    print("\n--- Test 3: Test Ollama (jeśli dostępny) ---")
    if OLLAMA_AVAILABLE:
        analizuj("powiedz krótko cześć", mock_config_ollama, mock_tts)
    else:
        print("Ollama niedostępny - pomijam test")
    
    print("\n--- Test 4: Statystyki ---")
    print("Recognition Stats:", get_recognition_stats())
    print("LLM Stats:", get_llm_stats())

# ===================================================================
# KONIEC PLIKU - CORE/ROZUMIENIE.PY Z OBSŁUGĄ OLLAMA
# ===================================================================