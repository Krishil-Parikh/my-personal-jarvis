import pyttsx3
import cv2
import torch
import numpy as np
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image
import sys
import time
import speech_recognition as sr
import ollama
from chat import chat_with_user

engine = pyttsx3.init()
    

engine.setProperty("rate", 180)
            
def speak(text: str):
    """Speak the given text using pyttsx3 with optional rate and voice."""
    engine.say(text)
    print(f"Jarvis: {text}")
    engine.runAndWait()
    engine.stop() 

def takeCommand():
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        print("\n🎤 Listening...")
        recognizer.pause_threshold = 0.8  # Slightly relaxed for natural pauses

        try:
            audio = recognizer.listen(source)
        except sr.WaitTimeoutError:
            print("⏱ Timeout: No speech detected.")
            return "none"

    try:
        print("🧠 Recognizing...")
        query = recognizer.recognize_google(audio, language="en-in")
        print(f"🗣 You said: {query}\n")
        return query.lower()

    except sr.UnknownValueError:
        print("❌ Could not understand audio.")
        return "none"
    except sr.RequestError:
        print("⚠️ Speech recognition service unavailable.")
        return "none"

def authentication():
    start_time = time.time()
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # Load models
    mtcnn = MTCNN(image_size=160, margin=0, min_face_size=40, device=device)
    resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

    # Load your saved embedding
    known_embedding = np.load("krishil_face_embedding.npy")

    # Threshold for similarity (tune between 0.6–0.8)
    SIMILARITY_THRESHOLD = 0.75

    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        face = mtcnn(img)

        if face is not None:
            embedding = resnet(face.unsqueeze(0).to(device)).detach().cpu().numpy()[0]
            sim = np.dot(known_embedding, embedding) / (
                np.linalg.norm(known_embedding) * np.linalg.norm(embedding)
            )

            if sim > SIMILARITY_THRESHOLD:
                text = f"Access Granted ({sim:.2f})"
                color = (0, 255, 0)
                cap.release()
                cv2.destroyAllWindows()
                return True
            else:
                text = f"Unknown ({sim:.2f})"
                color = (0, 0, 255)
            cv2.putText(frame, text, (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        current_time = time.time()
        if current_time - start_time >= 10:
            cap.release()
            cv2.destroyAllWindows()
        
        cv2.imshow("Face Recognition", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def analyzeCommand(command: str, model: str = "llama3") -> str:
    """
    Analyzes the user's spoken command using Ollama (local LLM)
    and returns the command category like: system, chat, info, media, etc.
    """
    if not command or command == "none":
        return "unknown"

    prompt = f"""
You are a command classifier for an AI assistant like JARVIS.
Classify the user's command into one of these categories:

1. system — opening apps, shutting down, system operations
2. chat — small talk, greetings, personal questions
3. info — asking facts, weather, time, or data
4. media — music, video, volume controls
5. authentication — face or voice login commands
6. other — anything that doesn't fit above

Command: "{command}"

Return ONLY one word — the category name (system/chat/info/media/authentication/other).
"""

    try:
        response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
        result = response["message"]["content"].strip().lower()

        # Normalize output
        for key in ["system", "chat", "info", "media", "authentication", "other"]:
            if key in result:
                return key

        return "other"

    except Exception as e:
        print(f"⚠️ Ollama Error: {e}")
        return "error"
    
auth = authentication()

if auth == True:
    speak("Access Granted")
else:
    speak("Access Denied")
    sys.exit()

while True:
    query = takeCommand().lower()
    category = analyzeCommand(query)
    print(f"🧩 Command Type: {category}")

    if category == "system":
        speak("System command detected.")
    elif category == "chat":
        chat_with_user(query)
    elif category == "media":
        speak("Playing your music.")
    else:
        speak("I'm not sure what that means.")
