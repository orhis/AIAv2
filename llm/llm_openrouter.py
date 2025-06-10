# llm/llm_openrouter.py
import requests
import json
import os
import time
from datetime import datetime

# === Cache dla odpowiedzi (opcjonalne) ===
response_cache = {}
MAX_CACHE_SIZE = 100

def _get_api_key():
    """Pobiera klucz API z różnych źródeł"""
    # 1. Zmienna środowiskowa (najwyższy priorytet)
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        return api_key
    
    # 2. secure.json
    try:
        if os.path.exists("config/secure.json"):
            with open("config/secure.json", "r", encoding="utf-8") as f:
                secure = json.load(f)
                api_key = secure.get("api_key")
                if api_key:
                    return api_key
    except Exception as e:
        print(f"⚠️ Błąd odczytu secure.json: {e}")
    
    # 3. Streamlit secrets
    try:
        import streamlit as st
        api_key = st.secrets.get("OPENROUTER_API_KEY")
        if api_key:
            return api_key
    except:
        pass
    
    return None

def _build_system_prompt(config):
    """Buduje system prompt na podstawie konfiguracji"""
    styl = config.get("local_config", {}).get("styl", "precyzyjny")
    
    base_prompt = "Jesteś AIA - inteligentnym asystentem AI, który mówi po polsku."
    
    if styl == "kreatywny":
        style_prompt = " Odpowiadaj w sposób kreatywny, używaj metafor i żywego języka. Możesz być bardziej luźny i emocjonalny w rozmowie."
    else:  # precyzyjny
        style_prompt = " Odpowiadaj precyzyjnie i rzeczowo. Udzielaj konkretnych, użytecznych informacji. Bądź zwięzły ale kompletny."
    
    context_prompt = " Pamiętaj, że jesteś częścią systemu domowego asystenta głosowego, więc użytkownik prawdopodobnie zadaje pytania głosowo."
    
    return base_prompt + style_prompt + context_prompt

def _prepare_messages(prompt, config, conversation_history=None):
    """Przygotowuje listę wiadomości do wysłania"""
    messages = []
    
    # System prompt
    system_prompt = _build_system_prompt(config)
    messages.append({"role": "system", "content": system_prompt})
    
    # Historia rozmowy (jeśli podana)
    if conversation_history:
        messages.extend(conversation_history[-6:])  # ostatnie 6 wiadomości (3 pary)
    
    # Aktualne zapytanie
    messages.append({"role": "user", "content": prompt})
    
    return messages

def _prepare_request_data(messages, config):
    """Przygotowuje dane żądania dla OpenRouter"""
    llm_config = config["llm_config"]
    
    data = {
        "model": llm_config["model"],
        "messages": messages,
        "max_tokens": llm_config.get("max_tokens", 1024),
        "stream": False
    }
    
    # Opcjonalne parametry
    optional_params = ["temperature", "top_p", "frequency_penalty", "presence_penalty"]
    for param in optional_params:
        if param in llm_config:
            data[param] = llm_config[param]
    
    return data

def odpowiedz(prompt, config, conversation_history=None, use_cache=False):
    """
    Główna funkcja odpowiedzi LLM
    Args:
        prompt: tekst zapytania użytkownika
        config: konfiguracja systemu
        conversation_history: opcjonalna historia rozmowy
        use_cache: czy używać cache'u odpowiedzi
    """
    start_time = time.time()
    
    # Sprawdź cache
    if use_cache:
        cache_key = f"{prompt}_{config['llm_config']['model']}"
        if cache_key in response_cache:
            print("💾 Odpowiedź z cache")
            return response_cache[cache_key]
    
    # Pobierz klucz API
    api_key = _get_api_key()
    if not api_key:
        error_msg = "[Błąd: brak klucza API OpenRouter. Sprawdź zmienne środowiskowe, secure.json lub streamlit.secrets]"
        print(f"❌ {error_msg}")
        return error_msg

    # Przygotuj żądanie
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/your-repo",  # dla OpenRouter analytics
        "X-Title": "AIA Assistant"
    }

    messages = _prepare_messages(prompt, config, conversation_history)
    data = _prepare_request_data(messages, config)
    
    print(f"🧠 Pytam {data['model']} (tokens: {data['max_tokens']})...")
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions", 
            headers=headers, 
            json=data,
            timeout=30  # 30 sekund timeout
        )
        
        elapsed = time.time() - start_time
        
        if response.ok:
            result = response.json()
            
            # Wyciągnij odpowiedź
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                content = choice.get("message", {}).get("content") or choice.get("text", "")
                
                if content:
                    # Informacje o użyciu
                    usage = result.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    
                    print(f"✅ Odpowiedź w {elapsed:.1f}s (🔤{prompt_tokens}→{completion_tokens} tokens)")
                    
                    # Zapisz do cache
                    if use_cache:
                        if len(response_cache) >= MAX_CACHE_SIZE:
                            # Usuń najstarszy wpis
                            oldest_key = next(iter(response_cache))
                            del response_cache[oldest_key]
                        response_cache[cache_key] = content
                    
                    return content.strip()
                else:
                    return "[⚠️ Model zwrócił pustą odpowiedź]"
            else:
                return "[⚠️ Brak choices w odpowiedzi API]"
        else:
            error_msg = f"[Błąd API OpenRouter: {response.status_code}]"
            try:
                error_detail = response.json().get("error", {}).get("message", response.text)
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {response.text[:200]}"
            
            print(f"❌ {error_msg}")
            return error_msg
            
    except requests.Timeout:
        return "[Błąd: Timeout - model nie odpowiedział w czasie 30 sekund]"
    except requests.ConnectionError:
        return "[Błąd: Brak połączenia z internetem]"
    except Exception as e:
        error_msg = f"[Błąd połączenia z OpenRouter: {type(e).__name__}: {e}]"
        print(f"❌ {error_msg}")
        return error_msg

def test_connection(config):
    """Testuje połączenie z OpenRouter"""
    print("🧪 Test połączenia z OpenRouter...")
    
    test_response = odpowiedz("Powiedz 'test'", config)
    
    if test_response.startswith("[Błąd"):
        print("❌ Test nieudany:", test_response)
        return False
    else:
        print("✅ Test udany:", test_response)
        return True

def dostepne_modele():
    """Zwraca listę popularnych modeli OpenRouter"""
    return {
        "GPT-4 Turbo": "openai/gpt-4-turbo",
        "GPT-3.5 Turbo": "openai/gpt-3.5-turbo", 
        "Claude 3 Opus": "anthropic/claude-3-opus",
        "Claude 3 Sonnet": "anthropic/claude-3-sonnet",
        "Claude 3 Haiku": "anthropic/claude-3-haiku",
        "Mixtral 8x7B": "mistralai/mixtral-8x7b-instruct",
        "LLaMA 3 8B": "meta-llama/llama-3-8b-instruct",
        "LLaMA 3 70B": "meta-llama/llama-3-70b-instruct"
    }

def wyczysc_cache():
    """Czyści cache odpowiedzi"""
    global response_cache
    response_cache.clear()
    print("🗑️ Cache wyczyszczony")

# === Test lokalny ===
if __name__ == "__main__":
    # Mock config dla testów
    test_config = {
        "llm_config": {
            "model": "openai/gpt-3.5-turbo",
            "max_tokens": 100,
            "temperature": 0.7
        },
        "local_config": {
            "styl": "precyzyjny"
        }
    }
    
    print("🧪 Test modułu LLM")
    print(f"Dostępne modele: {list(dostepne_modele().keys())}")
    
    if test_connection(test_config):
        print("\n--- Test konwersacji ---")
        response = odpowiedz("Jak się nazywasz?", test_config)
        print(f"Odpowiedź: {response}")