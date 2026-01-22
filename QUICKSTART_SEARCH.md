# Quick Start: Intelligent Web Search System

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Set Environment Variables

Create a `.env` file in the project root:

```env
OPENROUTER_API_KEY=your_api_key_here
```

## Quick Test

### Test 1: Simple Search (No Browser)

```python
python demo_integrated_search.py
```

Select option 1 and watch as the system:
1. Generates multiple query variants
2. Checks cache
3. Performs searches
4. Decides intelligently on browser automation
5. Returns comprehensive answer

### Test 2: Direct Integration

Create a test file `test_search.py`:

```python
import asyncio
from backend.ai_assistant import AIAssistant

async def test():
    ai = AIAssistant()
    
    # This will automatically trigger web search if needed
    result = ai.process_query("What are the latest AI developments in 2026?")
    
    print("ANSWER:")
    print(result['answer'])
    
    if result['sources']:
        print("\nSOURCES:")
        for source in result['sources']:
            print(f"- {source}")

asyncio.run(test())
```

Run it:
```bash
python test_search.py
```

### Test 3: Browser Automation

```python
import asyncio
from backend.intelligent_web_search import IntelligentWebSearch

async def test_browser():
    search = IntelligentWebSearch(show_browser=True)  # Show browser window
    
    # This should trigger browser automation
    results = await search.search("Show me GitHub Actions interface")
    
    answer = search.generate_answer("GitHub Actions", results)
    print(answer)

asyncio.run(test_browser())
```

## Usage Patterns

### Pattern 1: Voice Assistant Integration

```python
from backend.voice_assistant import VoiceAssistant
from backend.ai_assistant import AIAssistant

voice = VoiceAssistant()
ai = AIAssistant()

# Listen
query = voice.listen()

# Process (auto web search if needed)
result = ai.process_query(query)

# Respond
voice.speak(result['answer'])
```

### Pattern 2: Chat Interface

```python
from backend.ai_assistant import AIAssistant

ai = AIAssistant()
conversation_history = []

while True:
    user_input = input("You: ")
    if user_input.lower() in ['exit', 'quit']:
        break
    
    result = ai.process_query(user_input, conversation_history)
    
    print(f"Jarvis: {result['answer']}")
    
    if result['sources']:
        print(f"Sources: {', '.join(result['sources'][:3])}")
    
    # Update history
    conversation_history.append({"role": "user", "content": user_input})
    conversation_history.append({"role": "assistant", "content": result['answer']})
```

### Pattern 3: Batch Processing

```python
import asyncio
from backend.intelligent_web_search import IntelligentWebSearch

async def batch_search():
    search = IntelligentWebSearch(show_browser=False)
    
    queries = [
        "transformer attention mechanism",
        "quantum computing basics",
        "blockchain technology explained"
    ]
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Processing: {query}")
        print('='*60)
        
        results = await search.search(query)
        answer = search.generate_answer(query, results)
        
        print(answer)
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(2)

asyncio.run(batch_search())
```

## Common Issues & Solutions

### Issue: "Module not found: intelligent_web_search"

**Solution:**
```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
```

### Issue: "Playwright not installed"

**Solution:**
```bash
playwright install chromium
```

### Issue: "ChromaDB permission error"

**Solution:**
```bash
# Windows
rmdir /s chroma_db
mkdir chroma_db

# Linux/Mac
rm -rf chroma_db
mkdir chroma_db
```

### Issue: "API key not configured"

**Solution:**
Create `.env` file or set environment variable:
```bash
# Windows PowerShell
$env:OPENROUTER_API_KEY="your_key"

# Linux/Mac
export OPENROUTER_API_KEY="your_key"
```

### Issue: "Slow responses"

**Solutions:**
1. Disable browser automation for testing:
   ```python
   search = IntelligentWebSearch(show_browser=False)
   result = await search.search(query, force_browser=False)
   ```

2. Use cached results (automatic after first search)

3. Reduce query variants in `intelligent_web_search.py`:
   ```python
   return queries[:2]  # Only 2 variants instead of 4
   ```

## Testing the System

### Test Case 1: Information Query (No Browser)

```python
query = "What is machine learning?"
# Expected: Fast response, no browser, good answer
```

### Test Case 2: Visual Query (Browser)

```python
query = "Show me the Python documentation interface"
# Expected: Browser opens, screenshot taken, detailed answer
```

### Test Case 3: Current Events (Auto Web Search)

```python
query = "Latest SpaceX launches"
# Expected: Automatic web search, current information
```

### Test Case 4: Cache Efficiency

```python
# First search
await search.search("quantum computing")  # ~5 seconds

# Second search (same query)
await search.search("quantum computing")  # ~1 second (cached!)
```

## Performance Expectations

| Operation | Without Cache | With Cache | Speed-up |
|-----------|--------------|------------|----------|
| Simple Search | 3-5s | 0.5-1s | 5x |
| Browser Automation | 10-20s | 1-2s | 10x |
| Multi-query | 8-12s | 1-3s | 6x |

## Next Steps

1. ✅ Basic installation
2. ✅ Run demo script
3. ✅ Test simple query
4. 🔄 Integrate with your voice assistant
5. 🔄 Customize for your needs
6. 🔄 Deploy to production

## Configuration Options

Edit `backend/intelligent_web_search.py` for customization:

```python
class IntelligentWebSearch:
    def __init__(self, show_browser=False):
        # How long to cache results (hours)
        self.cache_validity_hours = 24
        
        # Show browser window (debug mode)
        self.show_browser = show_browser

# In generate_query_variants method:
return queries[:2]  # Reduce from 4 to 2 for faster searches

# In needs_browser_automation method:
# Adjust keywords that trigger browser automation
automation_keywords = [...]
```

## Production Deployment

### 1. Environment Setup

```bash
# Install in virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows

pip install -r requirements.txt
playwright install chromium
```

### 2. Configuration

```env
# .env file
OPENROUTER_API_KEY=your_key
CACHE_VALIDITY_HOURS=24
MAX_QUERY_VARIANTS=3
SHOW_BROWSER=False
```

### 3. Service Setup

```python
# main.py
from backend.ai_assistant import AIAssistant

def main():
    ai = AIAssistant()
    
    while True:
        try:
            query = get_user_input()  # Your input method
            result = ai.process_query(query)
            output_response(result)  # Your output method
        except KeyboardInterrupt:
            break
        except Exception as e:
            log_error(e)

if __name__ == "__main__":
    main()
```

## Support & Documentation

- 📖 Full Guide: [INTELLIGENT_SEARCH_GUIDE.md](INTELLIGENT_SEARCH_GUIDE.md)
- 🎯 Demo Script: [demo_integrated_search.py](demo_integrated_search.py)
- 💻 Source Code: [backend/intelligent_web_search.py](backend/intelligent_web_search.py)

## Quick Commands

```bash
# Install everything
pip install -r requirements.txt && playwright install chromium

# Run demo
python demo_integrated_search.py

# Test integration
python -c "from backend.ai_assistant import AIAssistant; ai = AIAssistant(); print('✅ Setup successful!')"

# Clear cache
rm -rf chroma_db  # Linux/Mac
rmdir /s chroma_db  # Windows

# Update dependencies
pip install -U duckduckgo-search playwright beautifulsoup4
```

Happy searching! 🚀
