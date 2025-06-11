# ===================================================================
# CORE/STT_PROCESSOR.PY - UNIWERSALNY STT POST-PROCESSING
# ===================================================================
# Wersja: AIA v2.1
# Opis: Korekta błędów STT przez LLM z kontekstem specjalizacji
# Obsługuje: cooking, calendar, smart_home, finance, general
# ===================================================================

import time
from typing import Optional, Dict, Any

def popraw_stt_uniwersalny(raw_text: str, config: Dict[str, Any], context_type: str = "general") -> str:
    """
    Uniwersalna korekta STT z kontekstem specjalizacji
    
    Args:
        raw_text (str): Surowy tekst z STT
        config (dict): Konfiguracja systemu LLM
        context_type (str): Typ kontekstu dla specjalizacji
        
    Returns:
        str: Poprawiony tekst
        
    Available contexts:
        - "general": Ogólna korekta (default)
        - "cooking": Kontekst kulinarny
        - "calendar": Daty i spotkania  
        - "smart_home": Sterowanie domem
        - "finance": Kontekst finansowy
    """
    
    # Import tylko gdy potrzebny (avoid circular imports)
    from core.rozumienie import zapytaj_llm_safe
    
    # Konteksty specjalizowane z instrukcjami
    context_prompts = {
        "general": {
            "description": "Popraw błędy w tekście z rozpoznawania mowy",
            "rules": [
                "Popraw ortografię i interpunkcję",
                "Przywróć sens zdania", 
                "Zachowaj intencję i znaczenie",
                "Dodaj przecinki gdzie potrzeba"
            ],
            "examples": [
                '"co robic" → "co robić"',
                '"ktora godina" → "która godzina"'
            ]
        },
        
        "cooking": {
            "description": "Popraw tekst dla kontekstu kulinarnego",
            "rules": [
                "Popraw nazwy składników (pomidol→pomidor, hamlet→omlet)",
                "Przywróć ilości i jednostki (gram→g, pu→pół, kilo→kg)",
                "Dodaj przecinki między składnikami", 
                "Popraw nazwy przepisów",
                "Zachowaj wszystkie liczby i ilości"
            ],
            "examples": [
                '"mam pomidol jajka" → "mam pomidor, jajka"',
                '"potrzebuje gram masła" → "potrzebuję 100g masła"',
                '"pu cebuli" → "pół cebuli"',
                '"przepis na hamlet" → "przepis na omlet"'
            ]
        },
        
        "calendar": {
            "description": "Popraw tekst dla kontekstu kalendarza i terminów",
            "rules": [
                "Popraw daty i godziny",
                "Popraw dni tygodnia (poniedzialek→poniedziałek)",
                "Przywróć formaty czasowe (o pietnastej→o 15:00)",
                "Popraw nazwy miesięcy"
            ],
            "examples": [
                '"spotkanie poniedzialek" → "spotkanie w poniedziałek"',
                '"o pietnastej" → "o 15:00"'
            ]
        },
        
        "smart_home": {
            "description": "Popraw tekst dla sterowania smart home",
            "rules": [
                "Popraw nazwy urządzeń",
                "Popraw komendy sterowania (włancz→włącz)",
                "Popraw nazwy pomieszczeń",
                "Zachowaj wartości (20 stopni, 50%)"
            ],
            "examples": [
                '"włancz swiatło" → "włącz światło"',
                '"ustaw temp dwadziescia" → "ustaw temperaturę 20 stopni"'
            ]
        },
        
        "finance": {
            "description": "Popraw tekst dla kontekstu finansowego",
            "rules": [
                "Popraw kwoty i waluty (zlotych→złotych)",
                "Popraw nazwy banków i firm",
                "Przywróć formaty liczbowe",
                "Popraw terminy finansowe"
            ],
            "examples": [
                '"transfer sto zlotych" → "transfer 100 złotych"',
                '"sprawdz saldo" → "sprawdź saldo"'
            ]
        }
    }
    
    # Pobierz kontekst lub użyj general
    context = context_prompts.get(context_type, context_prompts["general"])
    
    # Skonstruuj rules string
    rules_text = "\n".join([f"- {rule}" for rule in context["rules"]])
    examples_text = "\n".join([f"- {example}" for example in context["examples"]])
    
    # Główny prompt
    prompt = f"""{context["description"]}.

ORYGINALNY TEKST STT: "{raw_text}"

ZASADY KOREKTY:
{rules_text}

PRZYKŁADY:
{examples_text}

WAŻNE: 
- Odpowiadaj TYLKO po polsku
- Zwróć TYLKO poprawiony tekst, bez dodatkowych komentarzy
- Zachowaj wszystkie liczby i ilości z oryginalnego tekstu

POPRAWIONY TEKST:"""

    try:
        start_time = time.time()
        
        # Użyj prostej konfiguracji dla korekty STT
        correction_config = config.copy()
        correction_config["llm_config"]["max_tokens"] = 150  # Krótkie odpowiedzi
        correction_config["llm_config"]["temperature"] = 0.1  # Deterministyczne
        
        print(f"🔧 STT korekta ({context_type}): '{raw_text[:50]}...'")
        
        corrected_text = zapytaj_llm_safe(prompt, correction_config, max_retries=1)
        
        # Wyczyść odpowiedź z prefixów
        corrected_text = corrected_text.strip()
        if corrected_text.startswith("🧠 ["):
            # Usuń prefix jeśli jest
            corrected_text = corrected_text.split("]: ", 1)[-1]
        
        elapsed_time = time.time() - start_time
        
        print(f"✅ STT poprawiony ({elapsed_time:.1f}s): '{raw_text}' → '{corrected_text}'")
        
        return corrected_text
        
    except Exception as e:
        print(f"❌ Błąd korekty STT: {e}")
        # Fallback - zwróć oryginalny tekst
        return raw_text

def test_stt_correction():
    """
    Funkcja testowa - sprawdza różne konteksty korekty STT
    """
    print("🧪 Test korekty STT...")
    
    # Mock config dla testów
    mock_config = {
        "llm_config": {
            "provider": "ollama",
            "model": "llama3.1:8b",
            "base_url": "http://localhost:11434",
            "max_tokens": 150,
            "temperature": 0.1
        }
    }
    
    # Test cases dla różnych kontekstów
    test_cases = [
        # Cooking context
        ("mam pomidol jajka", "cooking"),
        ("potrzebuje gram masła", "cooking"), 
        ("przepis na hamlet", "cooking"),
        ("pu cebuli i marchefka", "cooking"),
        
        # General context
        ("ktora godina", "general"),
        ("co robic", "general"),
        ("jak sie masz", "general"),
        
        # Calendar context  
        ("spotkanie poniedzialek", "calendar"),
        ("o pietnastej", "calendar"),
    ]
    
    for raw_text, context in test_cases:
        print(f"\n--- Test {context.upper()} ---")
        corrected = popraw_stt_uniwersalny(raw_text, mock_config, context)
        print(f"Input:  '{raw_text}'")
        print(f"Output: '{corrected}'")

# ===================================================================
# HELPER FUNCTIONS
# ===================================================================

def detect_context_auto(text: str) -> str:
    """
    Automatyczne wykrywanie kontekstu na podstawie słów kluczowych
    
    Args:
        text (str): Tekst do analizy
        
    Returns:
        str: Wykryty kontekst
    """
    
    text_lower = text.lower()
    
    # Cooking keywords
    cooking_keywords = [
        "przepis", "gotować", "ugotować", "smażyć", "piec", "upiec", 
        "składniki", "jajka", "pomidor", "cebula", "masło", "mąka",
        "kalorie", "omlet", "zupa", "sałatka", "mam", "potrzebuję"
    ]
    
    # Calendar keywords  
    calendar_keywords = [
        "spotkanie", "termin", "godzina", "dzisiaj", "jutro", "wczoraj",
        "poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela",
        "stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca"
    ]
    
    # Smart home keywords
    smarthome_keywords = [
        "włącz", "wyłącz", "ustaw", "temperatura", "światło", "muzyka",
        "głośność", "klimatyzacja", "ogrzewanie", "rolety", "alarm"
    ]
    
    # Finance keywords
    finance_keywords = [
        "przelew", "saldo", "konto", "bank", "złotych", "euro", "dolar",
        "zapłać", "rachunek", "faktury", "kredyt", "oszczędności"
    ]
    
    # Count matches
    cooking_score = sum(1 for kw in cooking_keywords if kw in text_lower)
    calendar_score = sum(1 for kw in calendar_keywords if kw in text_lower)  
    smarthome_score = sum(1 for kw in smarthome_keywords if kw in text_lower)
    finance_score = sum(1 for kw in finance_keywords if kw in text_lower)
    
    # Return context with highest score
    scores = {
        "cooking": cooking_score,
        "calendar": calendar_score, 
        "smart_home": smarthome_score,
        "finance": finance_score
    }
    
    max_context = max(scores, key=scores.get)
    
    # Require at least 1 match for specialized context
    if scores[max_context] > 0:
        return max_context
    else:
        return "general"

# ===================================================================
# TESTY LOKALNE
# ===================================================================

if __name__ == "__main__":
    print("🧪 Testowanie modułu stt_processor.py")
    
    # Test wykrywania kontekstu
    print("\n--- Test wykrywania kontekstu ---")
    test_texts = [
        "mam pomidor co zrobić",
        "spotkanie w poniedziałek", 
        "włącz światło w salonie",
        "przelew 100 złotych",
        "jak się masz"
    ]
    
    for text in test_texts:
        context = detect_context_auto(text)
        print(f"'{text}' → {context}")
    
    # Test korekty (wymaga działającego Ollama)
    # test_stt_correction()

# ===================================================================
# KONIEC PLIKU
# ===================================================================