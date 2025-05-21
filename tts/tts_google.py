import os
import sys
import tempfile

try:
    from gtts import gTTS
except ImportError:
    print("📦 Instaluję gTTS...")
    os.system(f"{sys.executable} -m pip install gTTS")
    from gtts import gTTS

try:
    from playsound import playsound
except ImportError:
    print("📦 Instaluję playsound...")
    os.system(f"{sys.executable} -m pip install --force-reinstall playsound==1.2.2")
    from playsound import playsound

def mow_tekstem(tekst: str):
    print(f"🗣️ Google TTS mówi: {tekst}")
    tmp_path = None
    try:
        tts = gTTS(text=tekst, lang="pl")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tts.save(tmp.name)
            tmp_path = tmp.name

        playsound(tmp_path)

    except Exception as e:
        print(f"❌ Błąd Google TTS: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

# === Test lokalny ===
if __name__ == "__main__":
    mow_tekstem("To jest testowy komunikat z Google Text to Speech.")
