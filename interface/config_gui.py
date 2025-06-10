# === 1. IMPORTY I STAN SESJI ===
import streamlit as st
import json
import os
import subprocess

if "aia_uruchomiono" not in st.session_state:
    st.session_state["aia_uruchomiono"] = False

# === 2. ŚCIEŻKI DO PLIKÓW ===
config_path = "config/config.json"
secure_path = "config/secure.json"

# === 3. WCZYTYWANIE KONFIGURACJI ===
config = {}
secure = {}

if os.path.exists(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
if os.path.exists(secure_path):
    with open(secure_path, "r", encoding="utf-8") as f:
        secure = json.load(f)

st.set_page_config(page_title="AIA v2 – Konfiguracja", layout="centered")
st.title("🧠 AIA v2 – Konfiguracja systemu")

# === 4. KOMPONENTY SYSTEMU ===
st.header("🔧 Wybierz komponenty")

stt_options = ["whisper", "faster_whisper", "vosk", "google"]

stt = st.selectbox(
    "🗣️ Silnik STT",
    stt_options,
    index=stt_options.index(config.get("local_config", {}).get("stt", "whisper"))
)

# AKTUALIZOWANE - dodano Edge-TTS
# tts_options = ["coqui", "pyttsx3", "elevenlabs", "google", "edge"] # Obecnie Nieużywane - problem z j. polskim
tts_options = ["edge"]
current_tts = config.get("local_config", {}).get("tts", "edge")
tts_index = tts_options.index(current_tts) if current_tts in tts_options else 0

tts = st.selectbox("🔊 TTS", tts_options, index=tts_index)

# NOWE - Konfiguracja Edge-TTS
if tts == "edge":
    st.subheader("🎙️ Konfiguracja Edge-TTS")
    edge_voices = ["zofia", "marek"]
    current_edge_voice = config.get("local_config", {}).get("edge_voice", "zofia")
    edge_voice_index = edge_voices.index(current_edge_voice) if current_edge_voice in edge_voices else 0
    
    edge_voice = st.selectbox(
        "Głos polski:",
        edge_voices,
        index=edge_voice_index,
        help="Zofia - kobieta (naturalny), Marek - mężczyzna (spokojny)"
    )
    
    # Podgląd głosów - NOWA IMPLEMENTACJA
    if st.button("🎧 Testuj głos"):
        try:
            # Import potrzebnych bibliotek
            import asyncio
            import tempfile
            import os
            
            # Mapowanie głosów
            POLISH_VOICES = {
                "marek": "pl-PL-MarekNeural",
                "zofia": "pl-PL-ZofiaNeural"
            }
            
            # Test głosu
            test_text = f"Witaj! To jest test głosu {edge_voice}. System AIA działa poprawnie."
            
            with st.spinner("🎵 Generuję test głosu..."):
                try:
                    import edge_tts
                    
                    # Asynchroniczne generowanie
                    async def test_voice():
                        voice_id = POLISH_VOICES.get(edge_voice, "pl-PL-ZofiaNeural")
                        communicate = edge_tts.Communicate(test_text, voice_id)
                        
                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                            await communicate.save(tmp.name)
                            return tmp.name
                    
                    # Uruchom generator głosu
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    audio_file = loop.run_until_complete(test_voice())
                    loop.close()
                    
                    # Odtwórz audio
                    try:
                        import sounddevice as sd
                        import soundfile as sf
                        
                        data, samplerate = sf.read(audio_file)
                        sd.play(data, samplerate)
                        sd.wait()
                        
                        st.success(f"✅ Test głosu {edge_voice} zakończony!")
                        
                    except ImportError:
                        # Fallback - pokaż plik do pobrania
                        with open(audio_file, "rb") as f:
                            st.audio(f.read(), format="audio/wav")
                        st.info("🔊 Odtwórz powyższy plik audio")
                    
                    # Usuń tymczasowy plik
                    try:
                        os.unlink(audio_file)
                    except:
                        pass
                        
                except ImportError:
                    st.error("❌ Brak biblioteki edge-tts. Zainstaluj: pip install edge-tts")
                    
        except Exception as e:
            st.error(f"❌ Błąd testu głosu: {e}")
            st.info("💡 Upewnij się że masz zainstalowane: edge-tts, sounddevice, soundfile")
else:
    edge_voice = "zofia"  # domyślna wartość

MODELE_LLM = {
    "GPT-3.5 Turbo": "openai/gpt-3.5-turbo",
    "GPT-4 Turbo": "openai/gpt-4-turbo",
    "Claude 3 Opus": "anthropic/claude-3-opus",
    "Claude 3 Sonnet": "anthropic/claude-3-sonnet",
    "Mistral 7B": "mistralai/mistral-7b-instruct",
    "Mixtral 8x7B": "mistralai/mixtral-8x7b-instruct",
    "LLaMA 3 8B": "meta-llama/llama-3-8b-instruct"
}
REVERSE_LLM = {v: k for k, v in MODELE_LLM.items()}
llm_config = config.get("llm_config", {})
llm_label = st.selectbox("🧠 Model LLM", list(MODELE_LLM.keys()),
                         index=list(MODELE_LLM.keys()).index(REVERSE_LLM.get(llm_config.get("model", "openai/gpt-4-turbo"))))
llm = MODELE_LLM[llm_label]

# === 5. TRYB I STYL ===
st.header("⚙️ Tryb działania")
tryby = ["standardowy", "testowy", "prezentacja", "domowy", "alarmowy"]
tryb = st.selectbox("Tryb:", tryby,
                    index=tryby.index(config.get("local_config", {}).get("tryb", "standardowy")))
styl = st.radio("🎨 Styl odpowiedzi", ["precyzyjny", "kreatywny"],
                index=["precyzyjny", "kreatywny"].index(config.get("local_config", {}).get("styl", "precyzyjny")))

# === 6. PARAMETRY GENEROWANIA ===
st.header("🎛️ Parametry generowania")

PARAMETRY_LLM = {
    "openai/gpt-3.5-turbo": ["temperature", "top_p"],
    "openai/gpt-4-turbo": ["temperature", "top_p"],
    "anthropic/claude-3-opus": ["temperature", "top_p"],
    "anthropic/claude-3-sonnet": ["temperature", "top_p"],
    "mistralai/mistral-7b-instruct": ["temperature", "top_p"],
    "mistralai/mixtral-8x7b-instruct": ["temperature", "top_p"],
    "meta-llama/llama-3-8b-instruct": ["temperature", "top_p"]
}

parametry = {
    "model": llm,
    "max_tokens": st.slider("🎯 Max tokens", 128, 8192, llm_config.get("max_tokens", 2048), step=64)
}
if "temperature" in PARAMETRY_LLM[llm]:
    parametry["temperature"] = st.slider("🔥 Temperature", 0.0, 1.5, float(llm_config.get("temperature", 0.7)), step=0.05)
if "top_p" in PARAMETRY_LLM[llm]:
    parametry["top_p"] = st.slider("🎲 Top-p", 0.0, 1.0, float(llm_config.get("top_p", 1.0)), step=0.05)

# === 7. API KEY ===
# UKRYTE - niebezpieczne wpisywanie kluczy w GUI
st.header("🔑 Klucz API")
st.info("💡 Klucz API skonfiguruj przez plik config/secure.json lub zmienne środowiskowe")
st.code('{"api_key": "twój-klucz-tutaj"}', language="json")

# === 8. ZAPIS KONFIGURACJI ===
if st.button("💾 Zapisz konfigurację"):
    new_config = {
        "llm_config": parametry,
        "local_config": {
            "tryb": tryb,
            "styl": styl,
            "stt": stt,
            "tts": tts,
            "edge_voice": edge_voice
        }
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(new_config, f, indent=4, ensure_ascii=False)
    st.success("✅ Konfiguracja zapisana!")

# === 9. URUCHOMIENIE AIA ===
st.markdown("---")
st.header("🚀 Uruchomienie")

if st.button("🚀 Uruchom AIA teraz"):
    new_config = {
        "llm_config": parametry,
        "local_config": {
            "tryb": tryb,
            "styl": styl,
            "stt": stt,
            "tts": tts,
            "edge_voice": edge_voice
        }
    }
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(new_config, f, indent=4, ensure_ascii=False)

        st.session_state["aia_uruchomiono"] = True
    except Exception as e:
        st.error(f"❌ Błąd zapisu konfiguracji: {e}")

if st.session_state["aia_uruchomiono"]:
    try:
        if tryb == "prezentacja":
            subprocess.Popen(["python", "demo.py"], shell=True)
            st.success("✅ Tryb prezentacji uruchomiony.")
            st.info("🧪 Symulacja AIA działa w osobnym oknie terminala.")
        else:
            subprocess.Popen(["python", "main.py"], shell=True)
            st.success("✅ Konfiguracja zapisana. Uruchamiam AIA...")
            st.info("🧠 AIA została uruchomiona zgodnie z konfiguracją.")
        
        # Reset stanu po uruchomieniu
        st.session_state["aia_uruchomiono"] = False
    except Exception as e:
        st.error(f"❌ Błąd uruchamiania AIA: {e}")