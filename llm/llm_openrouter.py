import requests
import json
import os

def odpowiedz(prompt, config):
    # Klucz API – secure.json lub secrets.toml
    api_key = None
    try:
        if os.path.exists("config/secure.json"):
            with open("config/secure.json", "r", encoding="utf-8") as f:
                secure = json.load(f)
                api_key = secure.get("api_key")
    except:
        pass

    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("OPENROUTER_API_KEY")
        except:
            pass

    if not api_key:
        return "[Błąd: brak klucza API OpenRouter w secure.json ani w streamlit.secrets]"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": "Jesteś pomocnym asystentem AI, który mówi po polsku."}]
    messages.append({"role": "user", "content": prompt})

    data = {
        "model": config["llm_config"]["model"],
        "messages": messages,
        "max_tokens": config["llm_config"].get("max_tokens", 1024),
    }

    for param in ["temperature", "top_p"]:
        if param in config["llm_config"]:
            data[param] = config["llm_config"][param]

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        if response.ok:
            result = response.json()
            choice = result["choices"][0]
            return choice.get("message", {}).get("content") or choice.get("text", "[⚠️ Brak treści]")
        else:
            return f"[Błąd API OpenRouter: {response.status_code} – {response.text}]"
    except Exception as e:
        return f"[Błąd połączenia z OpenRouter: {e}]"
