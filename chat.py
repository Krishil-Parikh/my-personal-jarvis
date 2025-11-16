# chat.py
import ollama
import json
import os
from pyttsx3 import init as tts_init

# Initialize TTS
engine = tts_init()
engine.setProperty("rate", 180)

# JSON log file
CHAT_LOG_FILE = "conversation_log.json"


def speak(text: str):
    """Speak text using pyttsx3."""
    print(f"Jarvis: {text}")
    engine.say(text)
    engine.runAndWait()


def save_conversation(user_input: str, jarvis_response: str):
    """Save a single conversation turn to JSON file."""
    log_entry = {"user": user_input, "jarvis": jarvis_response}

    # If file exists, append; else create new
    if os.path.exists(CHAT_LOG_FILE):
        try:
            with open(CHAT_LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []
    else:
        data = []

    data.append(log_entry)

    # Save updated conversation list
    with open(CHAT_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def chat_with_user(prompt: str, model: str = "llama3"):
    """
    Handles conversational chat using Ollama.
    Stores all conversation pairs (user, Jarvis) in a JSON file.
    """
    if not prompt or prompt == "none":
        speak("I didn't catch that.")
        return

    try:
        response = ollama.chat(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Jarvis, a helpful, conversational AI assistant. "
                        "Respond in a natural, concise, slightly friendly tone."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )

        reply = response["message"]["content"].strip()
        speak(reply)
        save_conversation(prompt, reply)

    except Exception as e:
        print(f"⚠️ Ollama Chat Error: {e}")
        speak("Sorry, I encountered an issue while responding.")
