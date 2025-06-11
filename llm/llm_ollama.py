# ===================================================================
# LLM_OLLAMA.PY - OBSŁUGA LOKALNEGO MODELU OLLAMA
# ===================================================================
# Wersja: AIA v2.1
# Opis: Interfejs do lokalnych modeli LLM przez Ollama API
# Endpoint: http://localhost:11434
# ===================================================================

import requests
import json
import time
from typing import Dict, Any, Optional

class OllamaError(Exception):
    """Błędy związane z Ollama"""
    pass

def sprawdz_polaczenie(base_url: str = "http://localhost:11434") -> bool:
    """
    Sprawdza czy serwer Ollama działa
    
    Args:
        base_url (str): URL serwera Ollama
        
    Returns:
        bool: True jeśli serwer odpowiada
    """
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def lista_modeli(base_url: str = "http://localhost:11434") -> list:
    """
    Pobiera listę dostępnych modeli
    
    Args:
        base_url (str): URL serwera Ollama
        
    Returns:
        list: Lista nazw modeli
    """
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return [model["name"] for model in data.get("models", [])]
    except requests.RequestException as e:
        raise OllamaError(f"Nie można pobrać listy modeli: {e}")

def ollama_generate(prompt: str, config: Dict[str, Any]) -> str:
    """
    Generuje odpowiedź używając modelu Ollama
    
    Args:
        prompt (str): Tekst zapytania
        config (dict): Konfiguracja z ustawieniami modelu
        
    Returns:
        str: Odpowiedź modelu
        
    Raises:
        OllamaError: Jeśli wystąpi błąd API
    """
    
    # Wyciągnij ustawienia z config
    llm_config = config.get("llm_config", {})
    base_url = llm_config.get("base_url", "http://localhost:11434")
    model = llm_config.get("model", "llama3.1:8b")
    max_tokens = llm_config.get("max_tokens", 2048)
    temperature = llm_config.get("temperature", 0.7)
    
    # Sprawdź połączenie
    if not sprawdz_polaczenie(base_url):
        raise OllamaError("Serwer Ollama nie odpowiada. Sprawdź czy działa: ollama serve")
    
    # Sprawdź czy model istnieje
    dostepne_modele = lista_modeli(base_url)
    if model not in dostepne_modele:
        raise OllamaError(f"Model '{model}' nie jest dostępny. Dostępne: {dostepne_modele}")
    
    # Przygotuj żądanie
    url = f"{base_url}/api/generate"
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature
        }
    }
    
    start_time = time.time()
    
    try:
        print(f"🧠 Pytam Ollama {model} (local)...")
        
        response = requests.post(url, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        # Sprawdź czy odpowiedź zawiera błąd
        if "error" in result:
            raise OllamaError(f"Błąd modelu: {result['error']}")
        
        odpowiedz = result.get("response", "").strip()
        
        # Statystyki
        elapsed_time = time.time() - start_time
        total_duration = result.get("total_duration", 0) / 1e9  # nanosekund → sekundy
        
        print(f"✅ Ollama odpowiada ({elapsed_time:.1f}s): {odpowiedz[:50]}...")
        
        return odpowiedz
        
    except requests.exceptions.Timeout:
        raise OllamaError("Timeout - model zbyt długo generuje odpowiedź")
    except requests.exceptions.ConnectionError:
        raise OllamaError("Brak połączenia z serwerem Ollama")
    except requests.exceptions.HTTPError as e:
        raise OllamaError(f"Błąd HTTP: {e}")
    except json.JSONDecodeError:
        raise OllamaError("Nieprawidłowa odpowiedź JSON z serwera")

def odpowiedz(prompt: str, config: Dict[str, Any]) -> str:
    """
    Główna funkcja interfejsu - kompatybilna z llm_openrouter.py
    
    Args:
        prompt (str): Tekst zapytania
        config (dict): Konfiguracja systemu
        
    Returns:
        str: Odpowiedź modelu lub komunikat błędu
    """
    try:
        return ollama_generate(prompt, config)
        
    except OllamaError as e:
        error_msg = f"[Błąd Ollama]: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg
        
    except Exception as e:
        error_msg = f"[Błąd nieoczekiwany]: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg

def test_ollama():
    """
    Funkcja testowa - sprawdza czy Ollama działa
    """
    print("🧪 Test modułu Ollama...")
    
    # Test połączenia
    if sprawdz_polaczenie():
        print("✅ Serwer Ollama działa")
    else:
        print("❌ Serwer Ollama nie odpowiada")
        return False
    
    # Test modeli
    try:
        modele = lista_modeli()
        print(f"✅ Dostępne modele: {modele}")
        
        if not modele:
            print("❌ Brak modeli - pobierz: ollama pull llama3.1:8b")
            return False
            
    except OllamaError as e:
        print(f"❌ Błąd: {e}")
        return False
    
    # Test generacji
    test_config = {
        "llm_config": {
            "model": modele[0],  # Pierwszy dostępny model
            "max_tokens": 50,
            "temperature": 0.7
        }
    }
    
    try:
        odpowiedz_test = odpowiedz("Cześć! Odpowiedz krótko po polsku.", test_config)
        print(f"✅ Test odpowiedzi: {odpowiedz_test}")
        return True
        
    except Exception as e:
        print(f"❌ Błąd testu: {e}")
        return False

# ===================================================================
# TESTY LOKALNE
# ===================================================================

if __name__ == "__main__":
    print("🧪 Testowanie modułu llm_ollama.py")
    
    if test_ollama():
        print("🎉 Ollama gotowy do użycia!")
    else:
        print("❌ Ollama wymaga konfiguracji")
        print("Sprawdź:")
        print("1. ollama serve (czy działa)")
        print("2. ollama list (czy masz modele)")
        print("3. ollama pull llama3.1:8b (pobierz model)")

# ===================================================================
# KONIEC PLIKU
# ===================================================================