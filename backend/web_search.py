import requests
from bs4 import BeautifulSoup
import re
import logging
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus, unquote, urlparse
from duckduckgo_search import DDGS  # Use 'duckduckgo-search' package

logger = logging.getLogger(__name__)


class ReliableWebSearcher:
    """Robust web searcher that actually gets results"""
    
    def __init__(self):
        self.session = requests.Session()
        # Domains that are blocked, slow, or spam
        self.blocked_domains = {'baidu.com', 'jingyan.baidu.com', 'pinterest.com', 'facebook.com', 'linkedin.com', 'indeed.com', 'zhihu.com', 'github.com'}
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
        ]
        self.max_results_per_engine = 8
        self.max_content_chars = 5000
        self.timeout = 15

    def _get_headers(self):
        """Get random user agent headers"""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def extract_search_query(self, command):
        """Extract clean search query from voice command"""
        remove_words = [
            'jarvis', 'hey jarvis', 'ok jarvis',
            'search', 'search for', 'look up', 'find',
            'google', 'bing', 'can you', 'could you', 'please',
            'tell me about', 'what is', 'who is', 'how to',
            'why is', 'when is', 'where is'
        ]
        
        command = command.lower().strip()
        command = command.rstrip('.,!?')
        
        for word in remove_words:
            command = re.sub(r'\b' + re.escape(word) + r'\b', '', command, flags=re.IGNORECASE)
        
        query = ' '.join(command.split()).strip()
        return query

    def search_google_html(self, query: str) -> list[str]:
        """Fallback: Try to scrape Google (less reliable than DDGS)"""
        try:
            # This might not work due to Google's protections, but try anyway
            url = f"https://www.google.com/search?q={quote_plus(query)}&num=10"
            resp = self.session.get(url, headers=self._get_headers(), timeout=self.timeout)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            results = []

            # Look for citation links or result links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('/url?q='):
                    # Extract real URL from Google's redirect
                    real_url = href.split('/url?q=')[1].split('&')[0]
                    real_url = unquote(real_url)
                    if real_url.startswith('http'):
                        results.append(real_url)
                        if len(results) >= self.max_results_per_engine:
                            break

            print(f"[Google] Found {len(results)} URLs")
            return results
        except Exception as e:
            print(f"[Google] Failed: {str(e)[:60]}")
            return []

    def search_duckduckgo_html(self, query: str) -> list[str]:
        """Use duckduckgo-search package for reliable results"""
        try:
            ddgs = DDGS(timeout=self.timeout)
            results = []
            
            for result in ddgs.text(query, max_results=self.max_results_per_engine):
                if 'href' in result:
                    url = result['href']
                    if url.startswith('http'):
                        results.append(url)

            print(f"[DDG API] Found {len(results)} URLs")
            return results
        except Exception as e:
            print(f"[DDG API] Failed: {str(e)[:60]}")
            # Fallback to HTML scraping
            return self._search_ddg_html_fallback(query)

    def _search_ddg_html_fallback(self, query: str) -> list[str]:
        """Fallback HTML scraper for DuckDuckGo if API fails"""
        try:
            url = f"https://html.duckduckgo.com/?q={quote_plus(query)}&t=h_&ia=web"
            resp = self.session.get(url, headers=self._get_headers(), timeout=self.timeout)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            results = []

            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('http'):
                    results.append(href)
                    if len(results) >= self.max_results_per_engine:
                        break

            print(f"[DDG HTML] Found {len(results)} URLs")
            return results
        except Exception as e:
            print(f"[DDG HTML] Failed: {str(e)[:60]}")
            return []

    def search_bing_html(self, query: str) -> list[str]:
        """Scrape Bing search results"""
        try:
            url = f"https://www.bing.com/search?q={quote_plus(query)}&count={self.max_results_per_engine}"
            resp = self.session.get(url, headers=self._get_headers(), timeout=self.timeout)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            results = []

            for li in soup.find_all('li', class_='b_algo'):
                a = li.find('h2')
                if a:
                    link = a.find('a')
                    if link and link.get('href'):
                        href = link['href']
                        if href.startswith('http'):
                            results.append(href)
                            if len(results) >= self.max_results_per_engine:
                                break

            print(f"[Bing] Found {len(results)} URLs")
            return results
        except Exception as e:
            print(f"[Bing] Failed: {str(e)[:60]}")
            return []

    def fetch_content(self, url: str) -> tuple[str, str]:
        """Fetch and clean page content – returns (url, content_text)"""
        try:
            resp = self.session.get(url, headers=self._get_headers(), timeout=self.timeout)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove junk
            for tag in soup(["script", "style", "nav", "footer", "header", "form", "noscript"]):
                tag.decompose()

            text = soup.get_text(separator=" ", strip=True)
            text = re.sub(r'\s+', ' ', text).strip()

            # Validate meaningful content (>200 chars)
            if len(text) > 200:
                if len(text) > self.max_content_chars:
                    text = text[:self.max_content_chars] + " [...]"
                print(f"  ✓ Fetched {len(text)} chars from {url[:60]}...")
                return url, text
            else:
                print(f"  ✗ Content too short ({len(text)} chars) from {url[:60]}...")
                return url, ""

        except Exception as e:
            print(f"  ✗ Fetch failed from {url[:60]}... ({str(e)[:40]})")
            return url, ""

    def search_and_crawl(self, query: str) -> dict[str, str]:
        """Search for URLs and crawl them for content"""
        query = query.strip()
        if not query:
            return {}

        print(f"\n[Search] Query: '{query}'")

        # Try engines in order – Google first (most reliable), then fallbacks
        urls = []
        urls += self.search_google_html(query)
        if len(urls) < 5:
            urls += self.search_duckduckgo_html(query)
        if len(urls) < 5:
            urls += self.search_bing_html(query)

        # Filter out blocked domains
        urls = [u for u in urls if not any(domain in u for domain in self.blocked_domains)]
        urls = list(dict.fromkeys(urls))  # Remove duplicates while preserving order
        print(f"  → Found {len(urls)} valid URLs (after filtering)")

        if not urls:
            print(f"  → No results to crawl")
            return {}

        # Crawl URLs in parallel
        results = {}
        with ThreadPoolExecutor(max_workers=6) as executor:
            future_to_url = {executor.submit(self.fetch_content, url): url for url in urls[:10]}
            for future in as_completed(future_to_url):
                url, content = future.result()
                if content:  # Only store if content was successfully extracted
                    results[url] = content

        print(f"  → Successfully fetched {len(results)} pages")
        return results

    def search_and_crawl_multi(self, queries: list[str], num_results: int = 5, max_workers: int = 4) -> dict[str, dict[str, str]]:
        """Search and crawl multiple queries in parallel"""
        if not queries:
            return {}

        print(f"[Multi] Processing {len(queries)} queries")

        results = {}
        for q in queries:
            results[q] = self.search_and_crawl(q)
            time.sleep(random.uniform(0.6, 1.8))  # light politeness delay

        return results

    def summarize_web_results(self, query: str, web_results: dict[str, str]) -> str:
        """Format web results for AI context"""
        if not web_results:
            return ""
        
        context = f"Web search results for '{query}':\n\n"
        for idx, (url, content) in enumerate(web_results.items(), 1):
            snippet = content[:500] if content else ""
            context += f"[Source {idx}]: {url}\n{snippet}\n\n"
        
        return context


# ────────────────────────────────────────────────
#  Usage example
# ────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    searcher = ReliableWebSearcher()

    test_queries = [
        "Latest Venezuela attack January 2026",
        "Nicolás Maduro US capture 2026",
        "Operation Absolute Resolve Venezuela"
    ]

    multi_results = searcher.search_and_crawl_multi(test_queries)

    for q, res in multi_results.items():
        print(f"\nQuery: {q}")
        print(f"Results count: {len(res)}")
        for url, content in list(res.items())[:2]:
            print(f"  {url[:80]}...")
            print(f"  {content[:180]}...\n")

# Alias for backwards compatibility
WebSearcher = ReliableWebSearcher