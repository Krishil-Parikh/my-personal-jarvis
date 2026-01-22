# JARVIS Personal Assistant - Setup Guide

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

## Configuration

### OpenRouter API Key
Set your OpenRouter API key as an environment variable:

**Windows (PowerShell):**
```powershell
$env:OPENROUTER_API_KEY="your_api_key_here"
```

**Windows (Command Prompt):**
```cmd
set OPENROUTER_API_KEY=your_api_key_here
```

**Or set it permanently:**
```powershell
[System.Environment]::SetEnvironmentVariable('OPENROUTER_API_KEY', 'your_api_key_here', 'User')
```

Get your API key from: https://openrouter.ai/

## Features

### 1. Face Recognition Authentication
- System starts with face recognition
- Once authenticated, speaks "Access Granted"
- Voice assistant activates automatically

### 2. App Launcher
**Usage:** "Open [app name]"
- Examples: "Open Chrome", "Open Notepad", "Launch Spotify"
- System automatically removes filler words (jarvis, open, please, etc.)
- Uses Windows search to find and open applications

### 3. Web Search with AI
**Usage:** "Search [query]" or "What is [query]"
- Examples: "Search quantum computing", "What is machine learning"
- Searches Google and retrieves top 10 results
- Crawls all websites
- Sends context to Mistral AI for summarization
- Stores everything in ChromaDB for conversational memory

### 4. Conversational Memory
- All conversations stored in ChromaDB
- Maintains context across sessions
- Retrieves relevant past conversations
- Remembers web search results

## Running the System

```bash
python frontend/02.py
```

## Terminal Output

The middle column displays a terminal-style interface showing:
- `[SYSTEM]` - System messages (green)
- `[STATUS]` - Listening/Processing status (yellow)
- `USER >>` - Your voice commands (cyan)
- `JARVIS >>` - Assistant responses (pink/red)
- `[ERROR]` - Errors (bright red)

## Commands

- **"Open [app]"** - Launch applications
- **"Search [query]"** - Web search with AI summary
- **"Stop"/"Exit"/"Shutdown"** - Close voice assistant
- General questions - Uses AI with conversational context

## Database Location

ChromaDB stores data in: `./chroma_db/`
- Conversations
- Web search results
- All query context

## Notes

- Face recognition uses the embedding from `learning/face-detection/krishil_face_embedding.npy`
- Requires microphone access for voice commands
- Requires camera access for face recognition
- Internet connection required for web search and AI features
