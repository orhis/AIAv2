import json
import re
from llm import llm_openrouter
from tts import tts_coqui

# === 1. Wczytanie komend predefiniowanych ===
with open("config/komendy_domyslne.json", encoding="utf-8") as f:
    KOMENDY = json.load(f)

# === 2. Analiza tekstu ===
def analizuj(tekst, config):
    print("📥 Otrzymano polecenie:", tekst)

    # Szukaj dopasowania do wzorców z JSON-a
    for komenda in KOMENDY:
        wzorzec = komenda["wzorzec"]
        intencja = komenda["intencja"]
        if re.search(wzorzec, tekst, re.IGNORECASE):
            print(f"✅ Rozpoznano intencję: {intencja}")
            return wykonaj_intencje(intencja, tekst)

    # Brak dopasowania → LLM
    print("🤖 Brak predefiniowanej komendy – pytam LLM...")
    odpowiedz = llm_openrouter.odpowiedz(tekst, config)
    tts_coqui.powiedz(odpowiedz)
    return

# === 3. Wykonanie intencji ===
def wykonaj_intencje(intencja, tekst):
    if intencja == "zapytanie_godzina":
        from datetime import datetime
        godzina = datetime.now().strftime("%H:%M")
        odpowiedz = f"Jest godzina {godzina}"
    elif intencja == "powitanie":
        odpowiedz = "Cześć! Jak mogę pomóc?"
    else:
        odpowiedz = f"Zrozumiałem intencję: {intencja}, ale nie mam jeszcze implementacji."

    tts_coqui.powiedz(odpowiedz)
