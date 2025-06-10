# aia_audio/nasluchiwacz.py
import time
from datetime import datetime, timedelta

# === 1. Parametry ===
HASLO_AKTYWUJACE = ["stefan", "cześć", "aja"]
KOMENDY_STOP = ["dobra stop", "koniec", "stop", "wystarczy", "dziękuję wystarczy"]

# Timeouts i limity
TIMEOUT_AKTYWNY = 30  # sekund bez aktywności - auto powrót do czuwania
MAX_BLEDY_PODRZAD = 3  # maksymalna liczba błędów STT z rzędu
SLEEP_CZUWANIE = 0.5  # opóźnienie w trybie czuwania
SLEEP_AKTYWNY = 0.3   # opóźnienie w trybie aktywnym

def _loguj_z_czasem(wiadomosc):
    """Dodaje timestamp do logów"""
    czas = datetime.now().strftime("%H:%M:%S")
    print(f"[{czas}] {wiadomosc}")

def _sprawdz_haslo_aktywujace(tekst):
    """Sprawdza czy tekst zawiera słowo aktywujące"""
    tekst_lower = tekst.lower()
    for haslo in HASLO_AKTYWUJACE:
        if haslo.lower() in tekst_lower:
            return True
    return False

def _sprawdz_komende_stop(tekst):
    """Sprawdza czy tekst zawiera komendę stop"""
    tekst_lower = tekst.lower()
    for komenda in KOMENDY_STOP:
        if komenda.lower() in tekst_lower:
            return True
    return False

# === 2. Funkcja ciągłego nasłuchu ===
def nasluchuj(callback_tekstowy, stt):
    """
    Główna pętla nasłuchiwania z obsługą stanów
    Args:
        callback_tekstowy: funkcja callback która przyjmuje tekst
        stt: moduł STT do rozpoznawania mowy
    """
    _loguj_z_czasem(f"🟢 Nasłuchiwanie aktywne... Słowa aktywujące: {', '.join(HASLO_AKTYWUJACE)}")
    _loguj_z_czasem(f"🛑 Komendy stop: {', '.join(KOMENDY_STOP)}")
    
    aktywny = False
    czas_aktywacji = None
    licznik_bledow = 0
    
    while True:
        try:
            # Rozpoznaj mowę
            tekst = stt.rozpoznaj_mowe_z_mikrofonu()
            
            if not tekst or not tekst.strip():
                time.sleep(SLEEP_CZUWANIE if not aktywny else SLEEP_AKTYWNY)
                continue
                
            # Reset licznika błędów po udanym rozpoznaniu
            licznik_bledow = 0
            tekst = tekst.strip()
            _loguj_z_czasem(f"🎧 Rozpoznano: {tekst}")
            
            # === TRYB CZUWANIA ===
            if not aktywny:
                if _sprawdz_haslo_aktywujace(tekst):
                    _loguj_z_czasem("✅ Hasło aktywujące wykryte. AIA w trybie aktywnym.")
                    aktywny = True
                    czas_aktywacji = datetime.now()
                    
                    # Jeśli w tym samym tekście jest już komenda, wykonaj ją
                    tekst_bez_hasla = tekst.lower()
                    for haslo in HASLO_AKTYWUJACE:
                        tekst_bez_hasla = tekst_bez_hasla.replace(haslo.lower(), "").strip()
                    
                    if tekst_bez_hasla:
                        _loguj_z_czasem(f"🚀 Bezpośrednia komenda: {tekst_bez_hasla}")
                        callback_tekstowy(tekst_bez_hasla)
                        _loguj_z_czasem("🟡 AIA powraca do trybu czuwania.")
                        aktywny = False
                        czas_aktywacji = None
                else:
                    # W trybie czuwania - ignoruj wszystko inne
                    pass
                    
            # === TRYB AKTYWNY ===
            else:
                # Sprawdź timeout
                if datetime.now() - czas_aktywacji > timedelta(seconds=TIMEOUT_AKTYWNY):
                    _loguj_z_czasem(f"⏰ Timeout {TIMEOUT_AKTYWNY}s - powrót do czuwania.")
                    aktywny = False
                    czas_aktywacji = None
                    continue
                
                # Sprawdź komendę stop
                if _sprawdz_komende_stop(tekst):
                    _loguj_z_czasem("🛑 Komenda STOP wykryta – nasłuch przerwany.")
                    break
                
                # Sprawdź czy to znów słowo aktywujące (ignoruj)
                if _sprawdz_haslo_aktywujace(tekst):
                    _loguj_z_czasem("🔄 Słowo aktywujące powtórzone - pozostaję aktywny.")
                    czas_aktywacji = datetime.now()  # odnów timeout
                    continue
                
                # Przekaż tekst do dalszej obsługi
                _loguj_z_czasem(f"📤 Przekazuję komendę: {tekst}")
                try:
                    callback_tekstowy(tekst)
                except Exception as e:
                    _loguj_z_czasem(f"❌ Błąd w callback: {e}")
                
                # Odnów czas aktywacji (użytkownik mówił)
                czas_aktywacji = datetime.now()
                
        except Exception as e:
            licznik_bledow += 1
            _loguj_z_czasem(f"❌ Błąd rozpoznawania mowy ({licznik_bledow}/{MAX_BLEDY_PODRZAD}): {e}")
            
            # Jeśli za dużo błędów z rzędu, wyświetl ostrzeżenie
            if licznik_bledow >= MAX_BLEDY_PODRZAD:
                _loguj_z_czasem("⚠️ Za dużo błędów STT z rzędu! Sprawdź mikrofon.")
                _loguj_z_czasem("🔄 Resetuję licznik błędów i kontynuuję...")
                licznik_bledow = 0
                time.sleep(2)  # dłuższa pauza po błędach
            else:
                time.sleep(SLEEP_CZUWANIE)
            
            continue
        
        # Krótka pauza między cyklami
        time.sleep(SLEEP_CZUWANIE if not aktywny else SLEEP_AKTYWNY)

# === 3. Funkcje pomocnicze ===
def ustaw_hasla_aktywujace(nowe_hasla):
    """Zmienia listę haseł aktywujących w runtime"""
    global HASLO_AKTYWUJACE
    HASLO_AKTYWUJACE = nowe_hasla
    print(f"✅ Zaktualizowano hasła aktywujące: {', '.join(HASLO_AKTYWUJACE)}")

def ustaw_komendy_stop(nowe_komendy):
    """Zmienia listę komend stop w runtime"""
    global KOMENDY_STOP
    KOMENDY_STOP = nowe_komendy
    print(f"✅ Zaktualizowano komendy stop: {', '.join(KOMENDY_STOP)}")

def ustaw_timeout(nowy_timeout):
    """Zmienia timeout aktywności"""
    global TIMEOUT_AKTYWNY
    TIMEOUT_AKTYWNY = nowy_timeout
    print(f"✅ Timeout ustawiony na {TIMEOUT_AKTYWNY} sekund")

# === Test lokalny ===
if __name__ == "__main__":
    print("🧪 Test modułu nasluchiwacz")
    
    # Mock STT dla testów
    class MockSTT:
        def __init__(self):
            self.komendy = ["stefan jak się masz", "która godzina", "stop"]
            self.index = 0
            
        def rozpoznaj_mowe_z_mikrofonu(self):
            if self.index < len(self.komendy):
                komenda = self.komendy[self.index]
                self.index += 1
                time.sleep(1)  # symulacja nagrywania
                return komenda
            return ""
    
    def mock_callback(tekst):
        print(f"[MOCK CALLBACK]: Otrzymano tekst: {tekst}")
    
    # Test
    mock_stt = MockSTT()
    print("\n--- Rozpoczynam test (zostanie przerwany po komendzie 'stop') ---")
    nasluchuj(mock_callback, mock_stt)