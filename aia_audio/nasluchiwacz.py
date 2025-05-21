import time

# === 1. Parametry ===
HASLO_AKTYWUJACE = "stefan"
KOMENDA_STOP = "dobra stop"

# === 2. Funkcja ciągłego nasłuchu ===
def nasluchuj(callback_tekstowy, stt):
    print("🟢 Nasłuchiwanie aktywne... Powiedz:", HASLO_AKTYWUJACE)

    aktywny = False

    while True:
        try:
            tekst = stt.rozpoznaj_mowe_z_mikrofonu().lower()
        except Exception as e:
            print(f"❌ Błąd rozpoznawania mowy: {e}")
            continue

        if not tekst:
            continue

        print("🎧 Rozpoznano:", tekst)

        if not aktywny:
            if HASLO_AKTYWUJACE in tekst:
                print("✅ Hasło aktywujące wykryte. AIA w trybie aktywnym.")
                aktywny = True
        else:
            if KOMENDA_STOP in tekst:
                print("🛑 Komenda STOP wykryta – nasłuch przerwany.")
                break

            # Przekaż tekst do dalszej obsługi
            callback_tekstowy(tekst)
            print("🟡 AIA powraca do trybu czuwania.")
            aktywny = False
            time.sleep(1)
