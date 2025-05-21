# 🧠 AIA v2 – Publiczny Asystent Głosowy oparty na LLM

`AIA v2` to otwartoźródłowy, modularny asystent głosowy stworzony w Pythonie. Łączy w sobie rozpoznawanie mowy (STT), syntezę mowy (TTS) i generatywne modele językowe (LLM). Działa lokalnie i wspiera wiele trybów, silników i interfejs graficzny do konfiguracji.

---

## 🚀 Kluczowe funkcje

- 🎙️ Rozpoznawanie mowy (Whisper, Faster-Whisper, Vosk, Google STT)
- 🔊 Synteza mowy (Coqui, pyttsx3, ElevenLabs, Google TTS)
- 🤖 Obsługa LLM przez OpenRouter (GPT, Claude, Mistral, LLaMA)
- 🖥️ Interfejs GUI oparty na Streamlit
- 🧩 Dynamiczne ładowanie komponentów STT / TTS / LLM
- 🔁 Wiele trybów: testowy, standardowy, prezentacja, alarmowy
- 🛡️ Oddzielenie konfiguracji lokalnej i prywatnych kluczy

---

## 📦 Technologie

- Python 3.10+
- Streamlit
- Torch + TTS
- Sounddevice, Pyttsx3
- gTTS, ElevenLabs API
- Vosk STT
- OpenRouter API

---

## 📁 Struktura katalogów

```
AIAv2/
├── aia_audio/           # Obsługa mikrofonu i mowy
├── config/              # Konfiguracja i klucze (zabezpieczone)
├── core/                # Logika i analiza
├── interface/           # GUI Streamlit
├── llm/                 # Integracja z modelami LLM
├── stt/                 # Moduły rozpoznawania mowy
├── tts/                 # Moduły syntezy mowy
├── models/              # Bufor lokalnych modeli (gitignored)
├── main.py              # Główne wejście systemu
├── requirements.txt     # Wymagania systemowe
└── .gitignore           # Wykluczenia dla Git
```

---

## 🔧 Instalacja

1. Sklonuj repozytorium:

```bash
git clone https://github.com/orhis/AIAv2.git
cd AIAv2
```

2. Utwórz i aktywuj środowisko:

```bash
python -m venv venv
.env\Scriptsctivate    # Windows
# lub
source venv/bin/activate  # Linux/macOS
```

3. Zainstaluj zależności:

```bash
pip install -r requirements.txt
```

---

## 🧠 Uruchamianie

### Interfejs GUI:

```bash
streamlit run interface/config_gui.py
```

### Główna aplikacja:

```bash
python main.py
```

---

## 🔑 Klucze API (zabezpieczenia)

- `.streamlit/secrets.toml` – zawiera `OPENROUTER_API_KEY`, `elevenlabs_api_key`, itd.
- `config/secure.json` – zawiera głos systemowy, voice_id lub lokalne ustawienia

---

## ❌ Ignorowane przez Git (`.gitignore`)

- `venv/`, `.venv/`
- `models/`, `*.mp3`, `*.wav`, `*.log`
- `config/secure.json`
- `.streamlit/secrets.toml`
- `__pycache__/`

---

## 📄 Licencja

Projekt open-source – do wykorzystania edukacyjnego, testowego i rozwojowego.  
Możesz go forkować, rozwijać i dostosowywać do własnych potrzeb!

---

## 👨‍💻 Autor

Projekt rozwijany w ramach nauki i eksperymentów z AI.  
GitHub: [https://github.com/orhis](https://github.com/orhis)
