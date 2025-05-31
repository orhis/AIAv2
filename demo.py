import json
import time
import os

def odtworz_scenariusz(plik_json):
    with open(plik_json, "r", encoding="utf-8") as f:
        scenariusz = json.load(f)

    print("\n--- SYMULACJA SYSTEMU AIA – TRYB PREZENTACJA ---\n")
    for krok in scenariusz:
        rola = krok.get("rola")
        tekst = krok.get("tekst", "")
        czas = krok.get("czas", 2)

        if rola == "system":
            print(f"[SYSTEM]: {tekst}")
        elif rola == "uzytkownik":
            print(f"[UŻYTKOWNIK]: {tekst}")
        elif rola == "pauza":
            time.sleep(czas)
        else:
            print(f"[NIEZNANA ROLA]: {tekst}")
        time.sleep(2)

    print("\n--- KONIEC SYMULACJI ---\n")

if __name__ == "__main__":
    sciezka = os.path.join("config", "demo.json")
    if not os.path.exists(sciezka):
        print("Nie znaleziono pliku demo.json w katalogu config.")
    else:
        odtworz_scenariusz(sciezka)
