# ===================================================================
# INTERFACE/CONFIG_GUI.PY - KONFIGURACJA AIA V2 PRZEZ STREAMLIT
# ===================================================================
# Wersja: AIA v2.1 - UPROSZCZONA Z OLLAMA SUPPORT
# Opis: GUI do konfiguracji wszystkich komponentów systemu AIA
# Komponenty: STT, TTS, LLM Provider Switcher, Recognition Methods, Parametry
# ===================================================================

# === 1. IMPORTY I INICJALIZACJA SESJI ===
import streamlit as st
import json
import os
import subprocess

# Inicjalizacja stanu sesji - śledzenie czy AIA została uruchomiona
if "aia_uruchomiono" not in st.session_state:
    st.session_state["aia_uruchomiono"] = False

# === 2. ŚCIEŻKI DO PLIKÓW KONFIGURACYJNYCH ===
config_path = "config/config.json"        # Główna konfiguracja systemu

# === 3. WCZYTYWANIE ISTNIEJĄCEJ KONFIGURACJI ===
config = {}  # Główna konfiguracja

# Wczytaj config.json jeśli istnieje
if os.path.exists(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

# Konfiguracja strony Streamlit
st.set_page_config(page_title="AIA v2 – Konfiguracja", layout="centered")
st.title("🧠 AIA v2 – Konfiguracja systemu")

# ===================================================================
# 🤖 SEKCJA 4: LLM PROVIDER SELECTOR - NOWA SEKCJA
# ===================================================================

st.header("🤖 Wybór LLM Provider")

# Pobierz aktualny provider z config
current_provider = config.get("llm_config", {}).get("provider", "openrouter")
provider_index = 0 if current_provider == "openrouter" else 1

# Wybór provider
llm_provider = st.radio(
    "Wybierz provider:",
    options=["OpenRouter (chmura)", "Ollama (lokalny)"],
    index=provider_index,
    help="OpenRouter = modele w chmurze (płatne)\nOllama = modele lokalne (darmowe)"
)

# Mapowanie do wartości config
if llm_provider == "Ollama (lokalny)":
    provider = "ollama"
    st.success("🆓 Darmowy lokalny LLM")
else:
    provider = "openrouter" 
    st.info("💰 Płatne modele w chmurze")

# ===================================================================
# DYNAMICZNY WYBÓR MODELU NA PODSTAWIE PROVIDER
# ===================================================================

if provider == "ollama":
    # SEKCJA OLLAMA
    st.subheader("🦙 Ollama Models")
    
    # Sprawdź dostępne modele Ollama
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code == 200:
            models_data = response.json()
            ollama_models = [model["name"] for model in models_data.get("models", [])]
            
            if ollama_models:
                # Znajdź aktualny model
                current_model = config.get("llm_config", {}).get("model", "llama3.1:8b")
                model_index = ollama_models.index(current_model) if current_model in ollama_models else 0
                
                llm_model = st.selectbox(
                    "Model lokalny:",
                    options=ollama_models,
                    index=model_index,
                    help="Modele pobrane lokalnie"
                )
                st.success(f"✅ Ollama działa ({len(ollama_models)} modeli)")
            else:
                st.error("❌ Brak modeli Ollama")
                st.code("ollama pull llama3.1:8b")
                llm_model = "llama3.1:8b"  # Fallback
                
        else:
            st.error("❌ Ollama server nie odpowiada")
            st.code("ollama serve")
            llm_model = "llama3.1:8b"  # Fallback
            
    except Exception as e:
        st.error("❌ Ollama niedostępny")
        st.code("ollama serve")
        llm_model = "llama3.1:8b"  # Fallback
    
    # Ustawienia Ollama
    current_base_url = config.get("llm_config", {}).get("base_url", "http://localhost:11434")
    base_url = st.text_input(
        "Ollama URL:",
        value=current_base_url,
        help="Adres serwera Ollama"
    )
    
else:
    # SEKCJA OPENROUTER (ISTNIEJĄCY KOD)
    st.subheader("🌐 OpenRouter Models")
    
    openrouter_models = [
        "openai/gpt-3.5-turbo",
        "openai/gpt-4-turbo", 
        "openai/gpt-4",
        "mistralai/mistral-7b-instruct",
        "anthropic/claude-3-sonnet"
    ]
    
    # Znajdź aktualny model
    current_model = config.get("llm_config", {}).get("model", "openai/gpt-3.5-turbo")
    model_index = openrouter_models.index(current_model) if current_model in openrouter_models else 0
    
    llm_model = st.selectbox(
        "Model LLM:",
        options=openrouter_models,
        index=model_index,
        help="Wybierz model językowy"
    )
    
    base_url = None  # OpenRouter nie potrzebuje base_url

# Status panel - info o aktualnym provider
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    st.metric("Provider", provider.upper())
    st.metric("Model", llm_model.split("/")[-1] if "/" in llm_model else llm_model.split(":")[0])
with col2:
    st.metric("Koszt", "Darmowy" if provider == "ollama" else "Płatny")
    st.metric("Lokalizacja", "GPU" if provider == "ollama" else "Chmura")

# ===================================================================
# 🧠 SEKCJA 5: METODY ROZPOZNAWANIA INTENCJI
# ===================================================================

st.header("🎛️ Metody rozpoznawania intencji")

# Pobierz aktualną konfigurację rozpoznawania
recognition_config = config.get("recognition_config", {})

# Wybór metody rozpoznawania
recognition_methods = {
    "regex_only": "🏃‍♂️ Tylko Regex (najszybsze)",
    "regex_plus_simple": "🤖 Regex + Prosty LLM (standardowe)", 
    "regex_plus_few_shot": "🧠 Regex + Few-shot LLM (najlepsze)",
}

current_method = recognition_config.get("method", "regex_plus_simple")
method_index = list(recognition_methods.keys()).index(current_method) if current_method in recognition_methods.keys() else 1

recognition_method = st.selectbox(
    "Metoda rozpoznawania:",
    options=list(recognition_methods.keys()),
    format_func=lambda x: recognition_methods[x],
    index=method_index,
    help="""
    • Regex Only: Tylko wzorce - bardzo szybkie, ograniczone
    • Regex + Simple: Wzorce + prosty LLM - dobry kompromis  
    • Regex + Few-shot: Wzorce + inteligentny LLM - najlepsze rozumienie
    """
)

# Zaawansowane ustawienia rozpoznawania
with st.expander("⚙️ Zaawansowane ustawienia rozpoznawania"):
    # Próg pewności klasyfikacji
    confidence_threshold = st.slider(
        "🎯 Próg pewności klasyfikacji",
        min_value=0.0,
        max_value=1.0,
        value=float(recognition_config.get("confidence_threshold", 0.7)),
        step=0.05,
        help="Poniżej tego progu system przejdzie do czystego LLM"
    )
    
    # Kontekst z poprzedniej rozmowy
    use_context = st.checkbox(
        "💭 Używaj kontekstu poprzedniej rozmowy",
        value=recognition_config.get("use_context", False),
        help="System będzie pamiętać poprzednią wymianę zdań"
    )
    
    # Tryb debug
    debug_mode = st.checkbox(
        "🔍 Tryb debug (pokaż kroki klasyfikacji)",
        value=recognition_config.get("debug_mode", False),
        help="Wyświetla szczegółowe informacje o procesie rozpoznawania"
    )

# Informacyjny box o wybranej metodzie
if recognition_method == "regex_only":
    st.info("⚡ **Regex Only**: Najszybsza metoda. Rozpoznaje tylko dokładne wzorce z pliku komendy_domyslne.json")
elif recognition_method == "regex_plus_simple":
    st.info("🔄 **Regex + Simple LLM**: Standardowa metoda. Regex + prosty prompt do LLM")
elif recognition_method == "regex_plus_few_shot":
    st.success("🎯 **Regex + Few-shot LLM**: Najlepsza metoda. Regex + inteligentny LLM z przykładami")

# ===================================================================
# 🔧 SEKCJA 6: KOMPONENTY SYSTEMU - STT, TTS
# ===================================================================

st.header("🔧 Komponenty systemu")

# === STT (Speech-to-Text) Configuration ===
st.subheader("🗣️ Rozpoznawanie mowy (STT)")

stt_options = ["whisper", "faster_whisper", "vosk", "google"]
current_stt = config.get("local_config", {}).get("stt", "faster_whisper")
stt_index = stt_options.index(current_stt) if current_stt in stt_options else 1

stt = st.selectbox(
    "Silnik STT:",
    stt_options,
    index=stt_index,
    help="""
    • whisper: OpenAI Whisper (dokładny, wymaga internetu)
    • faster_whisper: Zoptymalizowany Whisper (zalecany, działa offline)  
    • vosk: Lokalny model (szybki, mniej dokładny)
    • google: Google Speech API (wymaga klucza API)
    """
)

# === TTS (Text-to-Speech) Configuration ===
st.subheader("🔊 Synteza mowy (TTS)")

tts_options = ["edge"]
current_tts = config.get("local_config", {}).get("tts", "edge")
tts_index = tts_options.index(current_tts) if current_tts in tts_options else 0

tts = st.selectbox(
    "Silnik TTS:", 
    tts_options, 
    index=tts_index,
    help="Obecnie dostępny tylko Edge-TTS z powodu najlepszej jakości polskiego głosu"
)

# Konfiguracja Edge-TTS - polskie głosy
if tts == "edge":
    edge_voices = ["zofia", "marek"]
    voice_descriptions = {
        "zofia": "👩 Zofia - głos kobiecy (naturalny, przyjemny)", 
        "marek": "👨 Marek - głos męski (spokojny, profesjonalny)"
    }
    
    current_edge_voice = config.get("local_config", {}).get("edge_voice", "marek")
    edge_voice_index = edge_voices.index(current_edge_voice) if current_edge_voice in edge_voices else 1
    
    edge_voice = st.selectbox(
        "Głos polski:",
        edge_voices,
        index=edge_voice_index,
        format_func=lambda x: voice_descriptions[x],
        help="Wybierz preferowany głos dla systemu AIA"
    )
else:
    edge_voice = "marek"  # Wartość domyślna

# ===================================================================
# 🎛️ SEKCJA 7: PARAMETRY GENEROWANIA LLM
# ===================================================================

st.header("🎛️ Parametry generowania")

llm_config = config.get("llm_config", {})

# Max tokens - maksymalna długość odpowiedzi
max_tokens = st.slider(
    "🎯 Maksymalna długość odpowiedzi (tokens)", 
    min_value=128, 
    max_value=8192, 
    value=llm_config.get("max_tokens", 2048), 
    step=64,
    help="Większa wartość = dłuższe odpowiedzi, ale większy koszt/czas"
)

# Temperature - kreatywność odpowiedzi
temperature = st.slider(
    "🔥 Temperature (kreatywność)", 
    min_value=0.0, 
    max_value=1.5, 
    value=float(llm_config.get("temperature", 0.7)), 
    step=0.05,
    help="0.0 = deterministyczne, 1.0 = bardzo kreatywne"
)

# Top-p - nucleus sampling (tylko dla OpenRouter)
if provider == "openrouter":
    top_p = st.slider(
        "🎲 Top-p (nucleus sampling)", 
        min_value=0.0, 
        max_value=1.0, 
        value=float(llm_config.get("top_p", 1.0)), 
        step=0.05,
        help="1.0 = wszystkie tokeny, 0.9 = top 90% prawdopodobnych"
    )
else:
    top_p = 1.0  # Wartość domyślna dla Ollama

# ===================================================================
# ⚙️ SEKCJA 8: TRYB I STYL DZIAŁANIA
# ===================================================================

st.header("⚙️ Tryb działania")

# Tryby pracy systemu
tryby = ["standardowy", "testowy", "prezentacja", "domowy"]
current_tryb = config.get("local_config", {}).get("tryb", "testowy")
tryb_index = tryby.index(current_tryb) if current_tryb in tryby else 1

tryb = st.selectbox(
    "Tryb pracy:", 
    tryby,
    index=tryb_index,
    help="""
    • standardowy: Normalna praca systemu
    • testowy: Rozszerzone logowanie i debugowanie  
    • prezentacja: Tryb demonstracyjny
    • domowy: Optymalizacja dla użytku domowego
    """
)

# Styl odpowiedzi AI
styl_options = ["precyzyjny", "kreatywny"]
current_styl = config.get("local_config", {}).get("styl", "precyzyjny")
styl_index = styl_options.index(current_styl) if current_styl in styl_options else 0

styl = st.radio(
    "🎨 Styl odpowiedzi", 
    styl_options,
    index=styl_index,
    help="""
    • precyzyjny: Konkretne, rzeczowe odpowiedzi
    • kreatywny: Bardziej rozbudowane, emocjonalne odpowiedzi
    """
)

# ===================================================================
# 💾 SEKCJA 10: ZAPISZ I URUCHOM
# ===================================================================

st.markdown("---")
st.header("💾 Zapisz i uruchom")

# Podgląd konfiguracji
with st.expander("👁️ Podgląd konfiguracji"):
    if provider == "ollama":
        preview_llm_config = {
            "provider": "ollama",
            "model": llm_model,
            "base_url": base_url,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "alternative_models": []
        }
    else:
        preview_llm_config = {
            "provider": "openrouter",
            "model": llm_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "alternative_models": []
        }
    
    preview_config = {
        "llm_config": preview_llm_config,
        "local_config": {
            "tryb": tryb,
            "styl": styl,
            "stt": stt,
            "tts": tts,
            "edge_voice": edge_voice
        },
        "recognition_config": {
            "method": recognition_method,
            "confidence_threshold": confidence_threshold,
            "use_context": use_context,
            "debug_mode": debug_mode
        }
    }
    st.json(preview_config)

# Kolumny dla przycisków
col1, col2 = st.columns(2)

with col1:
    # Przycisk zapisu konfiguracji
    if st.button("💾 Zapisz konfigurację", type="primary"):
        if provider == "ollama":
            new_llm_config = {
                "provider": "ollama",
                "model": llm_model,
                "base_url": base_url,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "alternative_models": []
            }
        else:
            new_llm_config = {
                "provider": "openrouter",
                "model": llm_model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "alternative_models": []
            }
        
        new_config = {
            "llm_config": new_llm_config,
            "local_config": {
                "tryb": tryb,
                "styl": styl,
                "stt": stt,
                "tts": tts,
                "edge_voice": edge_voice
            },
            "recognition_config": {
                "method": recognition_method,
                "confidence_threshold": confidence_threshold,
                "use_context": use_context,
                "debug_mode": debug_mode
            }
        }
        
        try:
            # Zapisz konfigurację do pliku
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=4, ensure_ascii=False)
            st.success("✅ Konfiguracja została zapisana pomyślnie!")
            st.info(f"📁 Zapisano w: {config_path}")
            
        except Exception as e:
            st.error(f"❌ Błąd podczas zapisu konfiguracji: {e}")

with col2:
    # Przycisk uruchomienia
    if st.button("🚀 Zapisz i uruchom AIA", type="secondary"):
        # Najpierw zapisz konfigurację (kod identyczny jak wyżej)
        if provider == "ollama":
            new_llm_config = {
                "provider": "ollama",
                "model": llm_model,
                "base_url": base_url,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "alternative_models": []
            }
        else:
            new_llm_config = {
                "provider": "openrouter",
                "model": llm_model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "alternative_models": []
            }
        
        new_config = {
            "llm_config": new_llm_config,
            "local_config": {
                "tryb": tryb,
                "styl": styl,
                "stt": stt,
                "tts": tts,
                "edge_voice": edge_voice
            },
            "recognition_config": {
                "method": recognition_method,
                "confidence_threshold": confidence_threshold,
                "use_context": use_context,
                "debug_mode": debug_mode
            }
        }
        
        try:
            # Zapisz konfigurację
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=4, ensure_ascii=False)
            
            st.success("✅ Konfiguracja zapisana!")
            
            # Uruchom AIA
            subprocess.Popen(["python", "main.py"], shell=True)
            st.success("✅ System AIA został uruchomiony!")
            st.info("🧠 AIA działa zgodnie z konfiguracją. Sprawdź terminal.")
            
            # Animacja sukcesu
            st.balloons()
            
        except Exception as e:
            st.error(f"❌ Błąd: {e}")

# Instrukcje dla użytkownika
st.markdown("### 📢 Co dalej?")
st.info("""
🎤 **Powiedz:** "Stefan" aby aktywować system

🗣️ **Przykładowe komendy:**
• "Stefan, którą mamy godzinę?"
• "Stefan, ile kalorii ma pomidor?"
• "Stefan, mam pomidor, co zrobić?" (test RAG)
• "Stefan, stop" - aby zakończyć
""")

# ===================================================================
# 📝 FOOTER
# ===================================================================

st.markdown("---")
st.caption("🤖 **AIA v2.1** - Asystent z obsługą Ollama i OpenRouter")
st.caption(f"💡 Aktualny provider: **{provider.upper()}** | Model: **{llm_model}**")

# ===================================================================
# KONIEC PLIKU - UPROSZCZONA WERSJA CONFIG_GUI.PY
# ===================================================================