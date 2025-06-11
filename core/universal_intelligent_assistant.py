# ===================================================================
# CORE/UNIVERSAL_INTELLIGENT_ASSISTANT.PY - UNIWERSALNY SYSTEM AI
# ===================================================================
# Wersja: AIA v2.1 Universal
# Opis: Uniwersalny inteligentny asystent dla WSZYSTKICH modułów
# Flow: STT → LLM Post-processing → LLM + RAG → Response (+ fallback)
# Moduły: cooking, smart_home, calendar, finance, general, alarms, etc.
# ===================================================================

import time
from typing import Dict, Any, List, Optional, Tuple
from core.stt_processor import popraw_stt_uniwersalny, detect_context_auto

# ===================================================================
# GŁÓWNA FUNKCJA UNIWERSALNEGO ASYSTENTA
# ===================================================================

def universal_intelligent_assistant(voice_input: str, config: Dict[str, Any], tts_module) -> str:
    """
    UNIWERSALNY INTELIGENTNY ASYSTENT
    
    Flow: 🎙️ STT → 🔧 LLM POST-PROCESSING → 🧠 LLM + RAG → 🗣️ Response
                                                    ↓ (jeśli RAG pusty)
                                               🧠 LLM SOLO
    
    Args:
        voice_input (str): Surowy tekst z STT
        config (dict): Konfiguracja systemu
        tts_module: Moduł TTS do odpowiedzi
        
    Returns:
        str: Odpowiedź asystenta
    """
    
    print(f"\n🤖 === UNIVERSAL INTELLIGENT ASSISTANT ===")
    start_time = time.time()
    
    try:
        # === KROK 1: WYKRYJ KONTEKST ===
        detected_context = detect_context_auto(voice_input)
        print(f"🔍 Wykryty kontekst: {detected_context.upper()}")
        
        # === KROK 2: STT POST-PROCESSING ===
        print(f"🔧 Krok 1/3: STT Post-processing ({detected_context})...")
        corrected_text = popraw_stt_uniwersalny(voice_input, config, detected_context)
        
        if corrected_text != voice_input:
            print(f"✅ STT poprawiony: '{voice_input}' → '{corrected_text}'")
        else:
            print(f"✅ STT bez zmian: '{corrected_text}'")
        
        # === KROK 3: RAG QUERY (UNIWERSALNY) ===
        print(f"🔍 Krok 2/3: Universal RAG Query...")
        rag_data = query_universal_rag(corrected_text, detected_context, config)
        
        # === KROK 4: LLM + DYNAMIC CONTEXT ===
        print(f"🧠 Krok 3/3: LLM + Dynamic Context...")
        
        if rag_data:
            print(f"✅ RAG HIT: Znaleziono {len(rag_data)} wyników dla {detected_context}")
            response = llm_with_rag_mode_universal(corrected_text, rag_data, detected_context, config)
        else:
            print(f"⚠️ RAG MISS: Brak danych w bazie - tryb LLM solo dla {detected_context}")
            response = llm_solo_mode_universal(corrected_text, detected_context, config)
        
        # === FINALIZACJA ===
        elapsed_time = time.time() - start_time
        print(f"🎯 Odpowiedź wygenerowana ({elapsed_time:.1f}s)")
        
        # TTS Response
        if tts_module and hasattr(tts_module, 'mow'):
            tts_module.mow(response)
        
        return response
        
    except Exception as e:
        print(f"❌ Błąd Universal Assistant: {e}")
        fallback_response = get_context_fallback_message(detected_context)
        
        if tts_module and hasattr(tts_module, 'mow'):
            tts_module.mow(fallback_response)
            
        return fallback_response

# ===================================================================
# UNIWERSALNY RAG SYSTEM
# ===================================================================

def query_universal_rag(query_text: str, context: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Uniwersalne przeszukiwanie RAG dla różnych kontekstów
    
    Args:
        query_text (str): Zapytanie użytkownika
        context (str): Kontekst (cooking, smart_home, calendar, etc.)
        config (dict): Konfiguracja systemu
        
    Returns:
        List[Dict]: Lista znalezionych wyników
    """
    
    try:
        # Wybierz odpowiedni RAG engine na podstawie kontekstu
        rag_results = []
        
        if context == "cooking":
            rag_results = query_cooking_rag(query_text, config)
            
        elif context == "smart_home":
            rag_results = query_smarthome_rag(query_text, config)
            
        elif context == "calendar":
            rag_results = query_calendar_rag(query_text, config)
            
        elif context == "finance":
            rag_results = query_finance_rag(query_text, config)
            
        elif context == "general":
            # Szukaj we wszystkich bazach
            rag_results = query_general_rag(query_text, config)
            
        else:
            print(f"⚠️ Nieznany kontekst RAG: {context}")
            rag_results = []
        
        return rag_results
        
    except Exception as e:
        print(f"❌ Błąd Universal RAG: {e}")
        return []

def query_cooking_rag(query_text: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """RAG dla kontekstu kulinarnego"""
    try:
        from rag.rag_engine import RagEngine
        rag = RagEngine(config.get("rag_config", {}))
        
        keywords = extract_cooking_keywords(query_text)
        print(f"🍳 Cooking RAG keywords: {keywords}")
        
        results = []
        for keyword in keywords:
            search_results = rag.search_relevant(keyword)
            if search_results:
                results.extend(search_results)
        
        return remove_duplicates(results)[:5]
        
    except Exception as e:
        print(f"❌ Błąd Cooking RAG: {e}")
        return []

def query_smarthome_rag(query_text: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """RAG dla smart home"""
    try:
        # TODO: Implementacja smart home RAG
        # Tutaj można dodać przeszukiwanie bazy urządzeń, scen, automatyzacji
        
        keywords = extract_smarthome_keywords(query_text)
        print(f"🏠 Smart Home RAG keywords: {keywords}")
        
        # Mock data dla demonstracji
        mock_devices = [
            {"name": "Światło salon", "type": "light", "status": "off", "room": "salon"},
            {"name": "Klimatyzacja", "type": "climate", "status": "20°C", "room": "salon"},
            {"name": "Telewizor", "type": "media", "status": "off", "room": "salon"}
        ]
        
        # Filtruj urządzenia na podstawie keywords
        results = []
        for device in mock_devices:
            for keyword in keywords:
                if keyword in device["name"].lower() or keyword in device["room"].lower():
                    results.append(device)
                    break
        
        return results
        
    except Exception as e:
        print(f"❌ Błąd Smart Home RAG: {e}")
        return []

def query_calendar_rag(query_text: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """RAG dla kalendarza"""
    try:
        # TODO: Integracja z Google Calendar API / Outlook
        
        keywords = extract_calendar_keywords(query_text)
        print(f"📅 Calendar RAG keywords: {keywords}")
        
        # Mock data dla demonstracji  
        mock_events = [
            {"title": "Spotkanie z zespołem", "date": "2025-06-12", "time": "10:00"},
            {"title": "Prezentacja projektu", "date": "2025-06-13", "time": "14:00"},
            {"title": "Lunch z klientem", "date": "2025-06-14", "time": "12:30"}
        ]
        
        # Filtruj wydarzenia
        results = []
        for event in mock_events:
            for keyword in keywords:
                if keyword in event["title"].lower():
                    results.append(event)
                    break
        
        return results
        
    except Exception as e:
        print(f"❌ Błąd Calendar RAG: {e}")
        return []

def query_finance_rag(query_text: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """RAG dla finansów"""
    try:
        # TODO: Integracja z bankowością API
        
        keywords = extract_finance_keywords(query_text)
        print(f"💰 Finance RAG keywords: {keywords}")
        
        # Mock data
        mock_finance = [
            {"account": "Konto główne", "balance": "2500 PLN", "type": "checking"},
            {"account": "Oszczędności", "balance": "15000 PLN", "type": "savings"},
            {"transaction": "Zakupy Biedronka", "amount": "-45.60 PLN", "date": "2025-06-11"}
        ]
        
        return mock_finance[:3]  # Return first few items
        
    except Exception as e:
        print(f"❌ Błąd Finance RAG: {e}")
        return []

def query_general_rag(query_text: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """RAG dla ogólnych zapytań - przeszukuje wszystkie bazy"""
    try:
        all_results = []
        
        # Szukaj w każdym kontekście
        contexts = ["cooking", "smart_home", "calendar", "finance"]
        
        for ctx in contexts:
            ctx_results = query_universal_rag(query_text, ctx, config)
            if ctx_results:
                # Dodaj info o źródle
                for result in ctx_results:
                    result["source_context"] = ctx
                all_results.extend(ctx_results)
        
        return remove_duplicates(all_results)[:5]
        
    except Exception as e:
        print(f"❌ Błąd General RAG: {e}")
        return []

# ===================================================================
# KEYWORDS EXTRACTION dla różnych kontekstów
# ===================================================================

def extract_cooking_keywords(text: str) -> List[str]:
    """Ekstraktuje słowa kluczowe dla kontekstu kulinarnego"""
    ingredients = [
        'jajko', 'jajka', 'pomidor', 'pomidory', 'cebula', 'czosnek',
        'masło', 'olej', 'mąka', 'cukier', 'sól', 'pieprz', 'marchew'
    ]
    
    dishes = ['omlet', 'jajecznica', 'zupa', 'kotlet', 'sałatka']
    actions = ['ugotować', 'smażyć', 'przepis', 'składniki']
    
    return extract_keywords_from_lists(text, ingredients + dishes + actions)

def extract_smarthome_keywords(text: str) -> List[str]:
    """Ekstraktuje słowa kluczowe dla smart home"""
    devices = ['światło', 'lampa', 'klimatyzacja', 'telewizor', 'muzyka', 'alarm']
    rooms = ['salon', 'kuchnia', 'sypialnia', 'łazienka', 'biuro']
    actions = ['włącz', 'wyłącz', 'ustaw', 'zmień', 'kontroluj']
    
    return extract_keywords_from_lists(text, devices + rooms + actions)

def extract_calendar_keywords(text: str) -> List[str]:
    """Ekstraktuje słowa kluczowe dla kalendarza"""
    time_words = ['spotkanie', 'termin', 'dzisiaj', 'jutro', 'wczoraj', 'godzina']
    days = ['poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota', 'niedziela']
    actions = ['dodaj', 'usuń', 'przenieś', 'sprawdź', 'przypomnij']
    
    return extract_keywords_from_lists(text, time_words + days + actions)

def extract_finance_keywords(text: str) -> List[str]:
    """Ekstraktuje słowa kluczowe dla finansów"""
    financial = ['saldo', 'przelew', 'konto', 'pieniądze', 'złotych', 'euro']
    actions = ['sprawdź', 'wyślij', 'zapłać', 'transfer', 'historia']
    
    return extract_keywords_from_lists(text, financial + actions)

def extract_keywords_from_lists(text: str, keyword_lists: List[str]) -> List[str]:
    """Helper function do ekstrakcji keywords"""
    text_lower = text.lower()
    found_keywords = []
    
    for keyword in keyword_lists:
        if keyword in text_lower:
            found_keywords.append(keyword)
    
    # Dodaj także pojedyncze słowa
    words = text_lower.split()
    for word in words:
        if len(word) > 3 and word not in found_keywords:
            found_keywords.append(word)
    
    return list(set(found_keywords))

# ===================================================================
# UNIWERSALNY LLM SYSTEM
# ===================================================================

def llm_with_rag_mode_universal(user_query: str, rag_data: List[Dict], context: str, config: Dict[str, Any]) -> str:
    """
    LLM w trybie z danymi RAG - uniwersalny dla wszystkich kontekstów
    """
    
    # Sformatuj dane RAG
    rag_context = format_rag_data_for_llm_universal(rag_data, context)
    
    # Kontekst-specific instructions
    context_instructions = get_context_instructions(context)
    
    prompt = f"""Jesteś inteligentnym asystentem "{get_assistant_name(context)}". 
Użytkownik powiedział: "{user_query}"

KONTEKST: {context.upper()}

DOSTĘPNE DANE Z BAZY:
{rag_context}

INSTRUKCJE:
{context_instructions}
- Odpowiadaj TYLKO po polsku
- Używaj konkretnych danych z bazy powyżej
- Bądź praktyczny i pomocny
- Jeśli brakuje informacji, zaproponuj rozwiązania

ODPOWIEDŹ:"""

    try:
        from core.rozumienie import zapytaj_llm_safe
        response = zapytaj_llm_safe(prompt, config)
        return clean_llm_response(response)
        
    except Exception as e:
        print(f"❌ Błąd LLM RAG mode ({context}): {e}")
        return get_context_error_message(context)

def llm_solo_mode_universal(user_query: str, context: str, config: Dict[str, Any]) -> str:
    """
    LLM w trybie solo (bez RAG) - uniwersalny dla wszystkich kontekstów
    """
    
    # Kontekst-specific instructions
    context_instructions = get_context_instructions(context)
    fallback_intro = get_context_fallback_intro(context)
    
    prompt = f"""Jesteś asystentem "{get_assistant_name(context)}". 
Użytkownik powiedział: "{user_query}"

KONTEKST: {context.upper()}

SYTUACJA: {fallback_intro}

INSTRUKCJE:
{context_instructions}
- Odpowiadaj TYLKO po polsku
- Używaj swojej wiedzy w tym obszarze
- Bądź praktyczny i pomocny

ODPOWIEDŹ:"""

    try:
        from core.rozumienie import zapytaj_llm_safe
        response = zapytaj_llm_safe(prompt, config)
        return clean_llm_response(response)
        
    except Exception as e:
        print(f"❌ Błąd LLM solo mode ({context}): {e}")
        return get_context_error_message(context)

# ===================================================================
# CONTEXT-SPECIFIC HELPERS
# ===================================================================

def get_assistant_name(context: str) -> str:
    """Zwraca nazwę asystenta dla kontekstu"""
    names = {
        "cooking": "Stefan - Asystent Kulinarny",
        "smart_home": "Stefan - Asystent Domowy", 
        "calendar": "Stefan - Asystent Kalendarza",
        "finance": "Stefan - Asystent Finansowy",
        "general": "Stefan - Asystent AI"
    }
    return names.get(context, "Stefan")

def get_context_instructions(context: str) -> str:
    """Zwraca instrukcje specyficzne dla kontekstu"""
    instructions = {
        "cooking": "- Podawaj konkretne przepisy\n- Sprawdzaj ilości składników\n- Proponuj alternatywy",
        "smart_home": "- Kontroluj urządzenia precyzyjnie\n- Potwierdź wykonane akcje\n- Dbaj o bezpieczeństwo",
        "calendar": "- Podaj dokładne daty i godziny\n- Sprawdź konflikty terminów\n- Zaproponuj optymalizację",
        "finance": "- Podaj dokładne kwoty\n- Sprawdź dostępne środki\n- Dbaj o bezpieczeństwo transakcji",
        "general": "- Odpowiadaj wszechstronnie\n- Jeśli potrzeba, zapytaj o szczegóły"
    }
    return instructions.get(context, "- Bądź pomocny i precyzyjny")

def get_context_fallback_intro(context: str) -> str:
    """Zwraca intro dla trybu fallback"""
    intros = {
        "cooking": "Nie mam tego przepisu w bazie, ale z doświadczenia kulinarnego mogę pomóc.",
        "smart_home": "Nie wykryłem tego urządzenia w systemie, ale mogę doradzić ogólnie.",
        "calendar": "Nie mam dostępu do kalendarza, ale mogę pomóc z planowaniem.",
        "finance": "Nie mam dostępu do konta, ale mogę doradzić finansowo.",
        "general": "Nie mam konkretnych danych, ale postaram się pomóc z wiedzy ogólnej."
    }
    return intros.get(context, "Brak danych w bazie, ale mogę pomóc z doświadczenia.")

def get_context_fallback_message(context: str) -> str:
    """Zwraca wiadomość fallback przy błędzie"""
    messages = {
        "cooking": "Przepraszam, mam problem z asystentem kulinarnym. Spróbuj ponownie.",
        "smart_home": "Przepraszam, mam problem z kontrolą domu. Sprawdź połączenie.",
        "calendar": "Przepraszam, mam problem z kalendarzem. Spróbuj ponownie.",
        "finance": "Przepraszam, mam problem z danymi finansowymi. Sprawdź bezpieczeństwo.",
        "general": "Przepraszam, wystąpił problem techniczny. Spróbuj ponownie."
    }
    return messages.get(context, "Przepraszam, wystąpił problem. Spróbuj ponownie.")

def get_context_error_message(context: str) -> str:
    """Zwraca wiadomość błędu dla kontekstu"""
    return get_context_fallback_message(context)

# ===================================================================
# UTILITY FUNCTIONS
# ===================================================================

def format_rag_data_for_llm_universal(rag_data: List[Dict], context: str) -> str:
    """Formatuje dane RAG dla LLM - uniwersalnie"""
    if not rag_data:
        return f"Brak danych w bazie dla kontekstu {context}."
    
    formatted_lines = []
    
    for i, item in enumerate(rag_data, 1):
        if isinstance(item, dict):
            line = format_rag_item_by_context(item, context, i)
        else:
            line = f"{i}. {str(item)}"
        
        formatted_lines.append(line)
    
    return "\n".join(formatted_lines)

def format_rag_item_by_context(item: Dict, context: str, index: int) -> str:
    """Formatuje pojedynczy item RAG według kontekstu"""
    
    if context == "cooking":
        name = item.get('name', item.get('przepis', f'Przepis {index}'))
        calories = item.get('calories', item.get('kalorie', ''))
        ingredients = item.get('ingredients', item.get('skladniki', ''))
        
        line = f"{index}. {name}"
        if ingredients:
            line += f" (Składniki: {ingredients})"
        if calories:
            line += f" - {calories} kcal"
            
    elif context == "smart_home":
        name = item.get('name', f'Urządzenie {index}')
        status = item.get('status', '')
        room = item.get('room', '')
        
        line = f"{index}. {name}"
        if room:
            line += f" ({room})"
        if status:
            line += f" - Status: {status}"
            
    elif context == "calendar":
        title = item.get('title', f'Wydarzenie {index}')
        date = item.get('date', '')
        time = item.get('time', '')
        
        line = f"{index}. {title}"
        if date:
            line += f" - {date}"
        if time:
            line += f" o {time}"
            
    elif context == "finance":
        account = item.get('account', '')
        transaction = item.get('transaction', '')
        balance = item.get('balance', '')
        amount = item.get('amount', '')
        
        if account:
            line = f"{index}. {account}"
            if balance:
                line += f" - Saldo: {balance}"
        elif transaction:
            line = f"{index}. {transaction}"
            if amount:
                line += f" - {amount}"
        else:
            line = f"{index}. {str(item)}"
            
    else:
        # General format
        line = f"{index}. {str(item)}"
    
    return line

def clean_llm_response(response: str) -> str:
    """Czyści odpowiedź LLM z prefixów"""
    if response.startswith("🧠 ["):
        response = response.split("]: ", 1)[-1]
    return response.strip()

def remove_duplicates(items: List[Dict]) -> List[Dict]:
    """Usuwa duplikaty z listy dict"""
    unique_items = []
    seen_ids = set()
    
    for item in items:
        item_id = item.get('id', str(item))
        if item_id not in seen_ids:
            unique_items.append(item)
            seen_ids.add(item_id)
    
    return unique_items

# ===================================================================
# INTEGRATION FUNCTION
# ===================================================================

def integrate_with_existing_rozumienie(tekst: str, config: Dict[str, Any], tts_module) -> str:
    """
    GŁÓWNA FUNKCJA INTEGRACYJNA
    
    Zastępuje standardowe rozumienie.analizuj() 
    Automatycznie wykrywa kontekst i przekierowuje do odpowiedniego systemu
    
    Args:
        tekst (str): Tekst z STT
        config (dict): Konfiguracja systemu  
        tts_module: Moduł TTS
        
    Returns:
        str: Odpowiedź systemu
    """
    
    print(f"\n🎯 === UNIVERSAL INTELLIGENT ASSISTANT START ===")
    print(f"📝 Input: '{tekst}'")
    
    # Zawsze używaj uniwersalnego systemu
    return universal_intelligent_assistant(tekst, config, tts_module)

# ===================================================================
# TESTY I DEMO
# ===================================================================

def test_universal_assistant():
    """Test uniwersalnego asystenta"""
    
    print("🧪 Test Universal Intelligent Assistant...")
    
    # Mock config
    mock_config = {
        "llm_config": {
            "provider": "ollama",
            "model": "llama3.1:8b",
            "max_tokens": 300,
            "temperature": 0.3
        }
    }
    
    # Mock TTS
    class MockTTS:
        def mow(self, text):
            print(f"🔊 TTS: {text[:100]}...")
    
    mock_tts = MockTTS()
    
    # Test cases dla różnych kontekstów
    test_cases = [
        # Cooking
        ("Stefan mam pomidor co zrobić", "cooking"),
        ("przepis na omlet", "cooking"),
        
        # Smart Home  
        ("włącz światło w salonie", "smart_home"),
        ("ustaw temperaturę 22 stopnie", "smart_home"),
        
        # Calendar
        ("jakie mam spotkania jutro", "calendar"),
        ("dodaj spotkanie na poniedziałek", "calendar"),
        
        # Finance
        ("sprawdź saldo konta", "finance"),
        ("wyślij przelew 100 złotych", "finance"),
        
        # General
        ("jak się masz", "general"),
        ("pogoda dzisiaj", "general")
    ]
    
    for query, expected_context in test_cases:
        print(f"\n--- Test: '{query}' (expected: {expected_context}) ---")
        try:
            response = universal_intelligent_assistant(query, mock_config, mock_tts)
            print(f"✅ Response: {response[:100]}...")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Testing Universal Intelligent Assistant")
    # test_universal_assistant()  # Uncomment when ready

# ===================================================================
# KONIEC PLIKU
# ===================================================================