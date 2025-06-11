# 📖 AIA v2 Configuration Documentation

## 🤖 llm_config
- **model**: Główny model LLM
- **alternative_models**: Fallback gdy brak kredytów
- **max_tokens**: Limit tokenów (auto-dostosowywany)
- **temperature**: Kreatywność (0.0-1.0)
- **top_p**: Nucleus sampling (0.0-1.0)

## 🏠 local_config  
- **tryb**: "testowy" | "produkcyjny" | "debug"
- **styl**: "precyzyjny" | "kreatywny"
- **stt**: "faster_whisper" | "openai_whisper"
- **tts**: "edge" | "openai" | "elevenlabs"
- **edge_voice**: "marek" | "zofia" | "agnieszka"

## 🧠 recognition_config
- **method**: "regex_only" | "regex_plus_simple" | "regex_plus_few_shot"
- **confidence_threshold**: Próg pewności (0.0-1.0)
- **use_context**: Kontekst poprzedniej rozmowy
- **debug_mode**: Pokazuj kroki klasyfikacji
- **fallback_model**: Model dla nieznanych intencji

## 🎯 Przykładowe tryby:
**Debug**: tryb="debug", debug_mode=true
**Oszczędny**: method="regex_only", max_tokens=512
**Najlepszy**: method="regex_plus_few_shot", model="gpt-4-turbo"