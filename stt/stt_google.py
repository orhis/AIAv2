import speech_recognition as sr

# === Rozpoznawanie mowy z Google STT ===
def rozpoznaj_mowe_z_mikrofonu() -> str:
    rozpoznawacz = sr.Recognizer()

    try:
        with sr.Microphone() as zrodlo:
            print("🎤 Nasłuchuję (Google STT)... Powiedz coś.")
            audio = rozpoznawacz.listen(zrodlo)

        tekst = rozpoznawacz.recognize_google(audio, language="pl-PL")
        return tekst

    except sr.UnknownValueError:
        print("❓ Nie rozpoznano mowy.")
        return ""
    except sr.RequestError as e:
        print(f"❌ Błąd usługi Google STT: {e}")
        return ""
    except Exception as e:
        print(f"❌ Błąd STT: {e}")
        return ""

# === Test lokalny ===
if __name__ == "__main__":
    wynik = rozpoznaj_mowe_z_mikrofonu()
    print("📝 Rozpoznany tekst:", wynik)