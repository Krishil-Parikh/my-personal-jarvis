import requests
from bs4 import BeautifulSoup
import re
import logging
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

class ReliableWebSearcher:
    def __init__(self):
        self.session = requests.Session()
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        ]
        self.max_results_per_engine = 6
        self.max_content_chars = 4500

    def _get_headers(self):
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
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

    def search_duckduckgo_html(self, query: str) -> list[str]:
        """Scrape DuckDuckGo HTML – no external package needed"""
        try:
            url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
            resp = self.session.get(url, headers=self._get_headers(), timeout=12)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            results = []

            for result in soup.select(".result__body"):
                link = result.select_one(".result__a")
                if link and (href := link.get("href")):
                    # DuckDuckGo wraps real URLs
                    if "uddg=" in href:
                        real_url = href.split("uddg=")[1].split("&")[0]
                        real_url = requests.utils.unquote(real_url)
                        results.append(real_url)
                    else:
                        results.append(href)

                if len(results) >= self.max_results_per_engine:
                    break

            print(f"[DDG HTML] Found {len(results)} URLs")
            return results
        except Exception as e:
            print(f"[DDG HTML] Failed: {str(e)[:80]}")
            return []

    def search_bing_html(self, query: str) -> list[str]:
        """Bing HTML scraping – more stable than before"""
        try:
            url = f"https://www.bing.com/search?q={quote_plus(query)}"
            resp = self.session.get(url, headers=self._get_headers(), timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")

            links = []
            for li in soup.select("li.b_algo"):
                a = li.select_one("h2 a")
                if a and (href := a.get("href")):
                    if href.startswith(("http://", "https://")):
                        links.append(href)
                if len(links) >= self.max_results_per_engine:
                    break

            print(f"[Bing HTML] Found {len(links)} URLs")
            return links
        except Exception as e:
            print(f"[Bing HTML] Failed: {str(e)[:80]}")
            return []

    def fetch_content(self, url: str) -> tuple[str, str]:
        """Fetch and clean page content – simple & fast fallback"""
        try:
            resp = self.session.get(url, headers=self._get_headers(), timeout=12)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove junk
            for tag in soup(["script", "style", "nav", "footer", "header", "form", "noscript"]):
                tag.decompose()

            text = soup.get_text(separator=" ", strip=True)
            text = re.sub(r'\s+', ' ', text).strip()

            if len(text) > self.max_content_chars:
                text = text[:self.max_content_chars] + " [...]"

            return url, text if len(text) > 150 else ""
        except Exception as e:
            return url, f"[FETCH ERROR] {str(e)[:120]}"

    def search_and_crawl(self, query: str) -> dict[str, str]:
        query = query.strip()
        if not query:
            return {}

        print(f"\n[Search] Query: {query}")

        # Try engines in order of reliability right now (2025/2026)
        urls = []
        urls += self.search_duckduckgo_html(query)
        if len(urls) < 3:
            urls += self.search_bing_html(query)

        urls = list(dict.fromkeys(urls))  # remove duplicates
        print(f"→ Found {len(urls)} unique URLs to crawl")

        if not urls:
            return {}

        results = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(self.fetch_content, url): url for url in urls[:12]}
            for future in as_completed(future_to_url):
                url, content = future.result()
                if content and not content.startswith("[FETCH ERROR]"):
                    results[url] = content
                    print(f"  ✓ {url[:70]}... ({len(content)} chars)")
                else:
                    print(f"  ✗ {url[:70]}... ({content[:60]})")

        print(f"→ Successfully fetched {len(results)} pages")
        return results

    def search_and_crawl_multi(self, queries: list[str]) -> dict[str, dict[str, str]]:
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
    def __init__(self):
        self.session = requests.Session()
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        ]
        self.max_results_per_engine = 6
        self.max_content_chars = 4500

    def _get_headers(self):
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def search_duckduckgo_html(self, query: str) -> list[str]:
        """Scrape DuckDuckGo HTML – no external package needed"""
        try:
            url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
            resp = self.session.get(url, headers=self._get_headers(), timeout=12)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            results = []

            for result in soup.select(".result__body"):
                link = result.select_one(".result__a")
                if link and (href := link.get("href")):
                    # DuckDuckGo wraps real URLs
                    if "uddg=" in href:
                        real_url = href.split("uddg=")[1].split("&")[0]
                        real_url = requests.utils.unquote(real_url)
                        results.append(real_url)
                    else:
                        results.append(href)

                if len(results) >= self.max_results_per_engine:
                    break

            print(f"[DDG HTML] Found {len(results)} URLs")
            return results
        except Exception as e:
            print(f"[DDG HTML] Failed: {str(e)[:80]}")
            return []

    def search_bing_html(self, query: str) -> list[str]:
        """Bing HTML scraping – more stable than before"""
        try:
            url = f"https://www.bing.com/search?q={quote_plus(query)}"
            resp = self.session.get(url, headers=self._get_headers(), timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")

            links = []
            for li in soup.select("li.b_algo"):
                a = li.select_one("h2 a")
                if a and (href := a.get("href")):
                    if href.startswith(("http://", "https://")):
                        links.append(href)
                if len(links) >= self.max_results_per_engine:
                    break

            print(f"[Bing HTML] Found {len(links)} URLs")
            return links
        except Exception as e:
            print(f"[Bing HTML] Failed: {str(e)[:80]}")
            return []

    def fetch_content(self, url: str) -> tuple[str, str]:
        """Fetch and clean page content – simple & fast fallback"""
        try:
            resp = self.session.get(url, headers=self._get_headers(), timeout=12)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove junk
            for tag in soup(["script", "style", "nav", "footer", "header", "form", "noscript"]):
                tag.decompose()

            text = soup.get_text(separator=" ", strip=True)
            text = re.sub(r'\s+', ' ', text).strip()

            if len(text) > self.max_content_chars:
                text = text[:self.max_content_chars] + " [...]"

            return url, text if len(text) > 150 else ""
        except Exception as e:
            return url, f"[FETCH ERROR] {str(e)[:120]}"

    def search_and_crawl(self, query: str) -> dict[str, str]:
        query = query.strip()
        if not query:
            return {}

        print(f"\n[Search] Query: {query}")

        # Try engines in order of reliability right now (2025/2026)
        urls = []
        urls += self.search_duckduckgo_html(query)
        if len(urls) < 3:
            urls += self.search_bing_html(query)

        urls = list(dict.fromkeys(urls))  # remove duplicates
        print(f"→ Found {len(urls)} unique URLs to crawl")

        if not urls:
            return {"error": "No search results from any engine"}

        results = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(self.fetch_content, url): url for url in urls[:12]}
            for future in as_completed(future_to_url):
                url, content = future.result()
                if content and not content.startswith("[FETCH ERROR]"):
                    results[url] = content
                    print(f"  ✓ {url[:70]}... ({len(content)} chars)")
                else:
                    print(f"  ✗ {url[:70]}... ({content[:60]})")

        print(f"→ Successfully fetched {len(results)} pages")
        return results

    def search_and_crawl_multi(self, queries: list[str]) -> dict[str, dict[str, str]]:
        if not queries:
            return {}

        print(f"[Multi] Processing {len(queries)} queries")

        results = {}
        for q in queries:
            results[q] = self.search_and_crawl(q)
            time.sleep(random.uniform(0.6, 1.8))  # light politeness delay

        return results


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