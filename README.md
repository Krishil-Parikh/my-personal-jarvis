# Jarvis – Personal AI Voice Assistant

A powerful, voice-activated AI assistant that combines speech recognition, real-time web search, face recognition, and intelligent system control. Jarvis listens to your commands, understands context, searches the web for current information, and responds naturally.

## 🚀 Features

- **Voice-Activated Control** – Speak naturally; Jarvis listens and responds with natural speech
- **Real-Time Web Search** – Automatic web scraping when knowledge is needed; stays up-to-date
- **Conversation Memory** – Remembers context from previous interactions for smarter responses
- **Face Recognition** – Detects and recognizes faces using advanced ML models
- **System Control** – Launch applications, search files, manage your PC hands-free
- **Intelligent Responses** – Powered by Mistral AI; generates thoughtful, contextual answers
- **Multi-Engine Search** – DuckDuckGo + Bing + Google fallback for reliable results
- **Parallel Processing** – Fast, concurrent web crawling for rapid information gathering

## 📋 Requirements

- **Python 3.9+**
- **Windows 10/11** (currently Windows-specific due to Azure Speech Services)
- **Microphone & Speaker** – For voice interaction
- **Internet Connection** – For web search and API calls

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Krishil-Parikh/my-personal-jarvis.git
cd my-personal-jarvis
```

### 2. Create Virtual Environment
```bash
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory:

```
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=mistralai/mistral-7b-instruct
AZURE_SPEECH_KEY=your_azure_speech_key_here
AZURE_SPEECH_REGION=centralindia
AZURE_SPEECH_VOICE=en-US-GuyNeural
```

**Get API Keys:**
- **OpenRouter**: https://openrouter.ai/
- **Azure Speech**: https://portal.azure.com/

### 5. Run the Assistant
```bash
python .\frontend\02.py
```

## 📖 Usage

Once running, Jarvis will listen for voice commands:

### Examples

**Web Search:**
```
"Tell me about the latest AI advancements"
"Search for current events in Venezuela"
"What are the newest features in Python 3.14?"
```
→ Jarvis searches the web and provides up-to-date information

**System Control:**
```
"Open Chrome"
"Launch Valorant"
"Search for documents"
```
→ Jarvis launches applications and finds files

**General Conversation:**
```
"What is machine learning?"
"Tell me a joke"
"How do I learn programming?"
```
→ Jarvis responds with intelligent, contextual answers

**System Commands:**
```
"Put the system to sleep"
"Shutdown the computer"
"Goodbye Jarvis"
```
→ Jarvis controls system functions

## 🏗️ Architecture

```
my-personal-jarvis/
├── backend/
│   ├── ai_assistant.py          # Mistral AI response generation
│   ├── voice_assistant.py       # Main voice interaction logic
│   ├── web_search.py            # Web scraping & search
│   ├── app_launcher.py          # Application launching
│   ├── memory.py                # Conversation memory management
│   ├── face_recognition.py      # Face detection & recognition
│   ├── camera.py                # Camera interface
│   └── system_monitor.py        # System resource monitoring
├── frontend/
│   └── 02.py                    # Main entry point
├── learning/
│   └── face-detection/          # ML models for face detection
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (create this)
└── README.md                    # This file
```

### Key Components

| Component | Purpose |
|-----------|---------|
| `ai_assistant.py` | Handles LLM calls, context management, web-aware responses |
| `voice_assistant.py` | Orchestrates STT, command processing, TTS, web search |
| `web_search.py` | DuckDuckGo/Bing HTML scraping, parallel page fetching |
| `app_launcher.py` | File indexing, app launching, system integration |
| `memory.py` | Conversation history, context retrieval, web context storage |

## ⚙️ How It Works

### 1. **Voice Input** 
User speaks → Azure Speech Recognition (STT) → Text command

### 2. **Command Processing**
- Detect command type (search, app launch, system, general chat)
- Extract relevant parameters
- Route to appropriate handler

### 3. **Web Search (when needed)**
- AI detects knowledge gap → signals `[NEEDS_WEB_SEARCH]`
- Generate research angles for comprehensive coverage
- Parallel search + crawl top results
- Compile context for AI

### 4. **Response Generation**
- AI processes command + web context + conversation history
- Generate intelligent, current response
- Store interaction in memory

### 5. **Voice Output**
- TTS synthesis → Azure Speech Synthesis
- Play audio response
- Wait for next command

## 🔧 Configuration

### Azure Speech Services
- Get free tier at https://azure.microsoft.com/en-us/services/cognitive-services/
- Set `AZURE_SPEECH_VOICE` to one of:
  - `en-US-GuyNeural` (male, default)
  - `en-US-JennyNeural` (female)
  - See [Azure voice list](https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/language-support?tabs=text-to-speech)

### OpenRouter Model Selection
Change `OPENROUTER_MODEL` in `.env`:
- `mistralai/mistral-7b-instruct` (default, fast)
- `mistralai/mistral-medium` (better quality)
- `openai/gpt-3.5-turbo` (if you have credits)

## 📦 Dependencies Overview

- **Azure Cognitive Services** – Speech STT/TTS
- **Mistral AI (via OpenRouter)** – LLM for responses
- **BeautifulSoup4** – HTML parsing for web scraping
- **Requests** – HTTP for web searches
- **PyAutoGUI** – System control & automation
- **OpenCV** – Face detection
- **ChromaDB** – Vector storage for memory
- **Torch/TorchVision** – ML model support
- **PyQt6** – UI components

## 🚀 Advanced Usage

### Custom Voice
Modify `voice_assistant.py`:
```python
self.voice_name = "en-US-JennyNeural"  # Change to preferred voice
```

### Conversation Memory
Jarvis stores conversations in memory for context:
```python
self.memory.add_conversation(command, response, metadata)
context = self.memory.get_relevant_context(query, n_results=5)
```

### Web Search Customization
Adjust crawling behavior in `web_search.py`:
```python
self.max_results_per_engine = 10  # URLs per search engine
self.max_content_chars = 5000     # Max characters per page
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Azure Speech Key error | Verify `.env` file has correct keys and region |
| No web results found | Check internet connection; DuckDuckGo/Bing may be blocking |
| Face recognition not working | Ensure camera is connected; update OpenCV |
| App launching fails | Check if app is installed or indexed in file system |

## 📝 License

This project is open-source. Customize and extend as needed!

## 🤝 Contributing

Have improvements? Fork, modify, and submit a pull request!

## 📞 Support

For issues or questions, open a GitHub issue or contact the maintainer.

---

**Made with ❤️ by Krishil Parikh**
