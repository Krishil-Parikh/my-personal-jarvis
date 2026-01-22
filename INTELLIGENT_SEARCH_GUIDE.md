# Intelligent Web Search System - Integration Guide

## Overview

The Intelligent Web Search System is a sophisticated search solution that integrates:
- **Multi-query generation**: Automatically creates multiple search queries from user input
- **ChromaDB caching**: Stores and retrieves results to avoid redundant searches
- **Smart browser automation**: Intelligently decides when to use browser automation vs simple search
- **AI-powered answers**: Generates comprehensive answers from search results

## Architecture

```
User Query
    ↓
AI Assistant (process_query)
    ↓
Needs Web Search? ─NO→ Direct Answer
    ↓ YES
Intelligent Web Search
    ↓
┌─────────────────────────────┐
│ 1. Generate Query Variants  │ (AI-powered multi-query generation)
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ 2. Check ChromaDB Cache     │ (24-hour validity)
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ 3. Simple DuckDuckGo Search │ (For non-cached queries)
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ 4. Browser Automation?      │ (AI decision based on query intent)
└─────────────────────────────┘
    ↓ YES
┌─────────────────────────────┐
│ 5. Browser Scraping         │ (Playwright automation)
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ 6. Store in ChromaDB        │ (Cache for future)
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ 7. Generate AI Answer       │ (Synthesize from all sources)
└─────────────────────────────┘
    ↓
Final Answer + Sources
```

## Key Features

### 1. Multi-Query Generation

Automatically generates 3-4 diverse query variants from a single user query:

```python
User: "transformer attention mechanism"
Generated:
  1. "transformer attention mechanism"
  2. "how does attention work in transformers"
  3. "self-attention mechanism explained"
  4. "transformer architecture attention layer"
```

### 2. Intelligent Browser Automation Decision

The system decides whether to use browser automation based on:

**Triggers browser automation:**
- Visual/interactive keywords: "show me", "screenshot", "interface", "how to use"
- Insufficient initial search results
- AI analysis of query intent
- User explicit request

**Skips browser automation:**
- Simple informational queries
- Good quality search snippets available
- Definitions and explanations
- Non-interactive content

### 3. ChromaDB Caching

- Results cached for 24 hours
- Reduces redundant web searches
- Faster response times
- Organized by query and URL

### 4. Smart Content Extraction

- Removes navigation, ads, scripts
- Focuses on main content
- Handles dynamic JavaScript sites
- Takes screenshots for visual queries

## Usage

### Basic Usage with AI Assistant

```python
from backend.ai_assistant import AIAssistant

ai = AIAssistant()

# Automatic web search integration
result = ai.process_query("What are the latest AI developments?")

print(result['answer'])
print(result['sources'])
```

### Direct Web Search

```python
import asyncio
from backend.intelligent_web_search import IntelligentWebSearch

async def search_example():
    search = IntelligentWebSearch(show_browser=False)
    
    # Perform intelligent search
    results = await search.search("quantum computing advances")
    
    # Generate answer
    answer = search.generate_answer("quantum computing advances", results)
    
    print(answer)

asyncio.run(search_example())
```

### Force Browser Automation

```python
# When you explicitly need browser automation
result = await ai.answer_with_intelligent_search(
    "Show me the GitHub Actions interface",
    force_browser=True
)
```

## Configuration

### Environment Variables

```bash
# Required
OPENROUTER_API_KEY=your_api_key_here

# Optional (defaults shown)
CACHE_VALIDITY_HOURS=24
SCREENSHOT_DIR=screenshots
IMAGE_DIR=images
```

### Customization

Edit `backend/intelligent_web_search.py`:

```python
class IntelligentWebSearch:
    def __init__(self, show_browser=False):
        # Cache duration
        self.cache_validity_hours = 24  # Change as needed
        
        # Browser visibility
        self.show_browser = show_browser  # Set True for debugging
```

## Query Examples

### Informational (No Browser Automation)

```python
queries = [
    "What is machine learning?",
    "Explain quantum entanglement",
    "History of the internet",
    "How does photosynthesis work?"
]
```

### Interactive (May Trigger Browser Automation)

```python
queries = [
    "Show me how to use GitHub Actions",
    "LinkedIn interface tutorial",
    "Netflix dashboard layout",
    "Real-time stock prices for Tesla"
]
```

### Current Events (Automatic Web Search)

```python
queries = [
    "Latest SpaceX launches",
    "Current inflation rate USA",
    "Who won the Nobel Prize 2025?",
    "Recent AI breakthroughs"
]
```

## ChromaDB Collections

### conversations
Stores user-assistant interactions:
```python
{
    "type": "conversation",
    "timestamp": "2026-01-22T10:30:00",
    "user_query": "...",
    "assistant_response": "..."
}
```

### web_context
Stores web search results:
```python
{
    "type": "web_search",
    "timestamp": "2026-01-22T10:30:00",
    "query": "...",
    "url": "...",
    "content": "..."
}
```

## Performance

### Without Cache
- Search: 3-5 seconds
- With browser automation: 10-20 seconds
- Total: 13-25 seconds

### With Cache
- Search: 0.5-1 second
- No browser automation needed
- Total: 1-2 seconds

**Speed improvement: 10-20x faster!**

## Error Handling

The system gracefully handles:
- Network timeouts
- Invalid URLs
- JavaScript-heavy sites
- Rate limiting
- API errors
- Cache corruption

## Troubleshooting

### "No results found"
- Check internet connection
- Verify DuckDuckGo is accessible
- Try different query phrasing

### Browser automation not working
- Install Playwright: `playwright install chromium`
- Check if site blocks automation
- Enable `show_browser=True` for debugging

### Cache not working
- Check ChromaDB directory permissions
- Verify `chroma_db` folder exists
- Clear cache: delete `chroma_db` folder

### Slow responses
- Reduce number of query variants
- Decrease cache validity duration
- Disable browser automation for testing

## API Reference

### IntelligentWebSearch

```python
class IntelligentWebSearch:
    def __init__(self, show_browser=False)
    
    async def search(self, user_query, force_browser=False)
    # Returns: dict with keys:
    #   - query: original query
    #   - query_variants: list of generated queries
    #   - total_results: int
    #   - browser_automation_used: bool
    #   - results: list of result dicts
    
    def generate_answer(self, user_query, search_results)
    # Returns: string answer
```

### AIAssistant

```python
class AIAssistant:
    async def answer_with_intelligent_search(self, query, force_browser=False)
    # Returns: dict with keys:
    #   - answer: string
    #   - search_results: dict
    #   - sources: list of URLs
    
    def process_query(self, query, conversation_history=None)
    # Returns: dict with same structure as above
    # Automatically triggers web search if needed
```

## Best Practices

1. **Let the AI decide**: Don't force browser automation unless necessary
2. **Use caching**: Results are valid for 24 hours
3. **Multiple queries**: The system automatically generates variants
4. **Error handling**: Always check result validity
5. **Rate limiting**: Add delays between searches
6. **Resource cleanup**: Browser instances are automatically closed

## Integration with Existing Code

### Voice Assistant Integration

```python
from backend.voice_assistant import VoiceAssistant
from backend.ai_assistant import AIAssistant

voice = VoiceAssistant()
ai = AIAssistant()

# Listen for query
query = voice.listen()

# Process with intelligent search
result = ai.process_query(query)

# Speak answer
voice.speak(result['answer'])
```

### Memory Integration

The system automatically uses ChromaDB through the `ConversationMemory` class:

```python
from backend.memory import ConversationMemory

memory = ConversationMemory()

# Retrieve relevant context
context = memory.get_relevant_context("machine learning")

# Both conversations and web_context are searched
```

## Future Enhancements

- [ ] Multi-language support
- [ ] Image understanding with vision models
- [ ] PDF and document parsing
- [ ] Video content extraction
- [ ] Social media integration
- [ ] News aggregation
- [ ] Fact-checking pipeline
- [ ] Source credibility scoring

## License

Part of the Personal Jarvis AI Assistant project.

## Support

For issues and questions:
1. Check this documentation
2. Review error logs
3. Enable debug mode: `show_browser=True`
4. Check ChromaDB contents
