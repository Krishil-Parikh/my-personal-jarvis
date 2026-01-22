import os
import re
import json
import asyncio
import requests
from datetime import datetime, timedelta
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from playwright.async_api import async_playwright
import random

# Import our existing modules
try:
    from .memory import ConversationMemory
    from .ai_assistant import AIAssistant
except ImportError:
    # Fallback for standalone execution
    from memory import ConversationMemory
    from ai_assistant import AIAssistant

# ============================================================
# CONFIG
# ============================================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)",
]

SCREENSHOT_DIR = "screenshots"
IMAGE_DIR = "images"
MAX_TEXT_LEN = 5000
MIN_CONTENT_LEN = 150

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

# ============================================================
# INTELLIGENT WEB SEARCH SYSTEM
# ============================================================

class IntelligentWebSearch:
    """
    Advanced web search system that:
    - Checks ChromaDB cache before searching
    - Generates multiple query variants
    - Decides intelligently when to use browser automation
    - Stores results for future retrieval
    """
    
    def __init__(self, show_browser=False):
        self.memory = ConversationMemory()
        self.ai_assistant = AIAssistant()
        self.show_browser = show_browser
        self.session = requests.Session()
        
        # Cache settings (results valid for 24 hours)
        self.cache_validity_hours = 24
        
    # ============================================================
    # QUERY GENERATION
    # ============================================================
    
    def generate_query_variants(self, user_query):
        """
        Generate multiple search query variants from a single user query
        using the AI assistant
        """
        prompt = f"""Given this user query: "{user_query}"

Generate 3-4 different search query variations that would help find comprehensive information.
Make them specific, diverse, and complementary to each other.

Return ONLY a JSON array of strings, nothing else. Example format:
["query 1", "query 2", "query 3"]
"""
        
        try:
            response = self.ai_assistant.generate_response(
                prompt, 
                temperature=0.7, 
                max_tokens=200
            )
            
            # Extract JSON array from response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            response = response.strip()
            
            queries = json.loads(response)
            
            # Always include the original query
            if user_query not in queries:
                queries.insert(0, user_query)
                
            print(f"🔄 Generated {len(queries)} query variants:")
            for i, q in enumerate(queries, 1):
                print(f"   {i}. {q}")
                
            return queries[:4]  # Limit to 4 queries max
            
        except Exception as e:
            print(f"⚠️ Error generating query variants: {e}")
            # Fallback to original query
            return [user_query]
    
    # ============================================================
    # BROWSER AUTOMATION DECISION
    # ============================================================
    
    def needs_browser_automation(self, user_query, initial_results):
        """
        Intelligently decide if browser automation is needed based on:
        - User's query intent
        - Quality of initial search results
        """
        
        # Keywords that suggest browser automation is needed
        automation_keywords = [
            'screenshot', 'image', 'visual', 'show me', 'what does it look like',
            'interface', 'design', 'layout', 'appearance', 'navigate', 'click',
            'interactive', 'demo', 'tutorial', 'step by step', 'how to use',
            'login', 'sign up', 'dashboard', 'real-time', 'live data', 'scrape',
            'extract data', 'table', 'download'
        ]
        
        query_lower = user_query.lower()
        
        # Check if user explicitly asks for browser automation
        if any(keyword in query_lower for keyword in automation_keywords):
            print("🤖 Browser automation needed: User query suggests it")
            return True
        
        # Check if initial results are sufficient
        if not initial_results:
            print("🤖 Browser automation needed: No initial results")
            return True
        
        # Check result quality
        total_content_length = sum(len(r.get('snippet', '')) for r in initial_results)
        if total_content_length < 500:  # Not enough content
            print("🤖 Browser automation needed: Insufficient content in results")
            return True
        
        # Let AI decide based on context
        decision_prompt = f"""Analyze if browser automation is needed for this query: "{user_query}"

Current search results quality: {len(initial_results)} results with {total_content_length} chars of content.

Reply with ONLY "YES" if browser automation is needed (for interactive content, visual data, tables, real-time info).
Reply with ONLY "NO" if simple search results are sufficient (for informational queries, definitions, explanations).

Your answer:"""
        
        try:
            response = self.ai_assistant.generate_response(
                decision_prompt,
                temperature=0.3,
                max_tokens=10
            )
            
            decision = "YES" in response.upper()
            
            if decision:
                print("🤖 Browser automation needed: AI decision")
            else:
                print("✅ Browser automation NOT needed: Search results sufficient")
                
            return decision
            
        except Exception as e:
            print(f"⚠️ Error in automation decision: {e}")
            # Default to NO (more efficient)
            return False
    
    # ============================================================
    # CACHE MANAGEMENT
    # ============================================================
    
    def check_cache(self, query):
        """
        Check if we have recent cached results for this query in ChromaDB
        """
        try:
            results = self.memory.web_context.query(
                query_texts=[query],
                n_results=5
            )
            
            if not results or not results.get('documents') or not results['documents'][0]:
                return None
            
            # Check if cached results are still valid (within 24 hours)
            cached_results = []
            
            for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                timestamp_str = metadata.get('timestamp', '')
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    age = datetime.now() - timestamp
                    
                    if age < timedelta(hours=self.cache_validity_hours):
                        cached_results.append({
                            'url': metadata.get('url', ''),
                            'content': doc,
                            'query': metadata.get('query', ''),
                            'cached': True
                        })
                except Exception:
                    pass
            
            if cached_results:
                print(f"💾 Found {len(cached_results)} cached results for query")
                return cached_results
            
            return None
            
        except Exception as e:
            print(f"⚠️ Cache check error: {e}")
            return None
    
    def store_results(self, query, url, content):
        """
        Store search results in ChromaDB for future use
        """
        try:
            self.memory.add_web_context(query, url, content)
        except Exception as e:
            print(f"⚠️ Error storing results: {e}")
    
    # ============================================================
    # SEARCH METHODS
    # ============================================================
    
    def simple_search(self, query, n=5):
        """
        Perform simple DuckDuckGo search without browser automation
        """
        print(f"🔍 Simple search: {query}")
        results = []
        
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=n, backend="lite"):
                    if r.get("href"):
                        result = {
                            "title": r.get("title", ""),
                            "snippet": r.get("body", ""),
                            "url": r["href"],
                            "query": query
                        }
                        results.append(result)
                        
                        # Store in cache
                        self.store_results(query, result["url"], result["snippet"])
        except Exception as e:
            print(f"⚠️ Search error: {e}")
        
        return results
    
    async def browser_scrape(self, url, query):
        """
        Perform browser automation to scrape content
        """
        domain = urlparse(url).netloc
        keywords = [k.lower() for k in query.split() if len(k) > 3]
        
        print(f"🌐 Browser scrape: {url}")
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=not self.show_browser)
                context = await browser.new_context(
                    user_agent=random.choice(USER_AGENTS),
                    viewport={"width": 1280, "height": 800}
                )
                page = await context.new_page()
                
                await page.goto(url, timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Extract content
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # Remove unwanted tags
                for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                    tag.decompose()
                
                text = soup.get_text(separator=" ", strip=True)
                text = re.sub(r"\s+", " ", text)
                
                # Take screenshot if browser is visible
                if self.show_browser:
                    screenshot_path = os.path.join(
                        SCREENSHOT_DIR, 
                        f"{domain.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    )
                    await page.screenshot(path=screenshot_path, full_page=False)
                    print(f"📸 Screenshot saved: {screenshot_path}")
                
                await browser.close()
                
                return text[:MAX_TEXT_LEN] if text else ""
                
        except Exception as e:
            print(f"❌ Browser scrape error: {e}")
            return ""
    
    # ============================================================
    # MAIN SEARCH PIPELINE
    # ============================================================
    
    async def search(self, user_query, force_browser=False):
        """
        Main search pipeline:
        1. Generate multiple query variants
        2. Check cache for each variant
        3. Perform searches
        4. Decide if browser automation is needed
        5. Return compiled results
        """
        print(f"\n{'='*60}")
        print(f"🎯 USER QUERY: {user_query}")
        print(f"{'='*60}\n")
        
        # Step 1: Generate query variants
        query_variants = self.generate_query_variants(user_query)
        
        # Step 2: Check cache and perform searches
        all_results = {}
        
        for query in query_variants:
            # Check cache first
            cached = self.check_cache(query)
            if cached:
                all_results[query] = cached
                continue
            
            # Perform new search
            search_results = self.simple_search(query)
            all_results[query] = search_results
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
        
        # Flatten all results
        flat_results = []
        for results_list in all_results.values():
            flat_results.extend(results_list)
        
        # Remove duplicates by URL
        seen_urls = set()
        unique_results = []
        for r in flat_results:
            url = r.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)
        
        print(f"\n📊 Total unique results: {len(unique_results)}")
        
        # Step 3: Decide if browser automation is needed
        needs_automation = force_browser or self.needs_browser_automation(
            user_query, 
            unique_results
        )
        
        # Step 4: Perform browser automation if needed
        if needs_automation and unique_results:
            print(f"\n🚀 Starting browser automation for top {min(3, len(unique_results))} results...")
            
            for result in unique_results[:3]:  # Only top 3 results
                url = result.get('url', '')
                if not url:
                    continue
                
                # Check if we already have good content
                if len(result.get('snippet', '')) > 300:
                    continue
                
                # Scrape with browser
                scraped_content = await self.browser_scrape(url, user_query)
                if scraped_content:
                    result['content'] = scraped_content
                    result['browser_scraped'] = True
                    
                    # Store detailed content in cache
                    self.store_results(user_query, url, scraped_content)
                
                await asyncio.sleep(1)  # Delay between scrapes
        
        # Step 5: Compile final results
        compiled_results = {
            'query': user_query,
            'query_variants': query_variants,
            'total_results': len(unique_results),
            'browser_automation_used': needs_automation,
            'results': unique_results
        }
        
        return compiled_results
    
    # ============================================================
    # ANSWER GENERATION
    # ============================================================
    
    def generate_answer(self, user_query, search_results):
        """
        Generate a comprehensive answer using AI based on search results
        """
        # Compile context from all results
        context_parts = []
        
        for idx, result in enumerate(search_results.get('results', [])[:5], 1):
            url = result.get('url', '')
            content = result.get('content', result.get('snippet', ''))
            
            context_parts.append(f"[Source {idx}: {url}]\n{content[:1000]}")
        
        combined_context = "\n\n".join(context_parts)
        
        if len(combined_context) > 8000:
            combined_context = combined_context[:8000] + "..."
        
        # Generate answer
        answer = self.ai_assistant.generate_response(
            user_query,
            context=combined_context,
            temperature=0.7,
            max_tokens=600
        )
        
        return answer


# ============================================================
# USAGE EXAMPLE
# ============================================================

async def main():
    # Initialize search system
    search_system = IntelligentWebSearch(show_browser=False)
    
    # Test queries
    test_queries = [
        "What is the transformer attention mechanism?",
        "Show me how to use GitHub Actions",  # This should trigger browser automation
        "Latest news about AI developments"
    ]
    
    for query in test_queries:
        # Perform search
        results = await search_system.search(query)
        
        # Generate answer
        answer = search_system.generate_answer(query, results)
        
        print(f"\n{'='*60}")
        print(f"ANSWER FOR: {query}")
        print(f"{'='*60}")
        print(answer)
        print(f"\n{'='*60}\n")
        
        # Wait before next query
        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
