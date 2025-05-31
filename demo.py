import time
import json

# Ikony
IKONA_AIA = "💻"
IKONA_USER = "🧠"
IKONA_SYSTEM = "🛠️"

# Kolory ANSI
KOLOR_AIA = "\033[96m"     # jasny błękit
KOLOR_USER = "\033[93m"    # żółty
KOLOR_SYSTEM = "\033[92m"  # zielony
RESET = "\033[0m"

# Funkcja wypisywania z ikoną i opóźnieniem zależnym od długości
def pokaz_ladnie(linia):
    if linia.startswith("[AIA]:"):
        print(f"{KOLOR_AIA}{IKONA_AIA} {linia}{RESET}")
        time.sleep(len(linia) * 0.035)
    elif linia.startswith("+ [USER INPUT]:"):
        time.sleep(2)
        print(f"{KOLOR_USER}{IKONA_USER} {linia}{RESET}")
        time.sleep(len(linia) * 0.03)
    elif linia.startswith("[SYSTEM]:"):
        print(f"{KOLOR_SYSTEM}{IKONA_SYSTEM} {linia}{RESET}")
        time.sleep(1)
    else:
        print(linia)
        time.sleep(1)

# Wczytaj dane z pliku JSON (łącznie z modułami startowymi)
with open("config/demo.json", "r", encoding="utf-8") as plik:
    skrypt_demo = json.load(plik)

# Przetwarzanie całego scenariusza
for linia in skrypt_demo:
    if "System nadal aktywny" in linia:
        pokaz_ladnie(linia)
        time.sleep(3)
    elif "Odebrano nową wiadomość" in linia:
        time.sleep(5)
        pokaz_ladnie(linia)
    else:
        pokaz_ladnie(linia)

# Czekaj na użytkownika przed zakończeniem
print()
input()  # nie pokazujemy tekstu, użytkownik wie że ma zakończyć
print(f"{KOLOR_SYSTEM}{IKONA_SYSTEM} Symulacja zakończona. Dziękuję za uwagę.{RESET}")
print(f"{KOLOR_SYSTEM}{IKONA_SYSTEM} --- KONIEC SYMULACJI ---{RESET}")
