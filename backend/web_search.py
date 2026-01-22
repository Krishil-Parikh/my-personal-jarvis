import os
import re
import json
import time
import random
import asyncio
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from playwright.async_api import async_playwright

# ============================================================
# CONFIG
# ============================================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)",
]

JS_HEAVY_FILE = "js_heavy_domains.json"
SCREENSHOT_DIR = "screenshots"
IMAGE_DIR = "images"

MAX_TEXT_LEN = 5000
MIN_CONTENT_LEN = 150

STATIC_HINTS = [
    "blog", "docs", "documentation", "wiki",
    "research", "paper", "article", "posts"
]

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

# ============================================================
# SMART WEB AGENT
# ============================================================

class SmartWebAgent:

    def __init__(self, show_browser=True):
        self.session = requests.Session()
        self.show_browser = show_browser
        self.js_heavy_domains = self._load_js_heavy_domains()

    # -------------------- Persistence --------------------

    def _load_js_heavy_domains(self):
        if os.path.exists(JS_HEAVY_FILE):
            with open(JS_HEAVY_FILE, "r") as f:
                return set(json.load(f))
        return set()

    def _save_js_heavy_domain(self, domain):
        if domain not in self.js_heavy_domains:
            self.js_heavy_domains.add(domain)
            with open(JS_HEAVY_FILE, "w") as f:
                json.dump(sorted(self.js_heavy_domains), f, indent=2)
            print(f"⚠️ Learned JS-heavy domain: {domain}")

    # -------------------- Search --------------------

    def search(self, query, n=5):
        print(f"\n🔍 SEARCH: {query}")
        results = []

        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=n, backend="lite"):
                if r.get("href"):
                    results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r["href"]
                    })
        return results

    # -------------------- Heuristics --------------------

    def snippet_insufficient(self, snippet):
        return not snippet or len(snippet) < 120

    def looks_static(self, url):
        return any(h in url.lower() for h in STATIC_HINTS)

    def is_js_heavy(self, url):
        return urlparse(url).netloc in self.js_heavy_domains

    # -------------------- Browser Intelligence --------------------

    async def scrape_with_browser(self, url, query):
        domain = urlparse(url).netloc
        keywords = [k.lower() for k in query.split() if len(k) > 3]

        print(f"🧠 Intelligent browser scrape: {url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=not self.show_browser)
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()

            try:
                await page.goto(url, timeout=30000)
                await page.wait_for_timeout(3000)

                # ---- Find relevant elements via JS ----
                elements = await page.evaluate(
                    """(keywords) => {
                        const matches = [];
                        const nodes = document.querySelectorAll("p, h1, h2, h3, article, section");

                        nodes.forEach(el => {
                            const text = el.innerText.toLowerCase();
                            if (keywords.some(k => text.includes(k))) {
                                matches.push(el);
                            }
                        });
                        return matches.map(el => el.outerHTML);
                    }""",
                    keywords
                )

                if not elements:
                    print("❌ No query-matching section found.")
                    self._save_js_heavy_domain(domain)
                    await browser.close()
                    return "", []

                # ---- Scroll to first relevant element ----
                await page.evaluate(
                    """(keywords) => {
                        const nodes = document.querySelectorAll("p, h1, h2, h3, article, section");
                        for (const el of nodes) {
                            const text = el.innerText.toLowerCase();
                            if (keywords.some(k => text.includes(k))) {
                                el.scrollIntoView({behavior: 'smooth', block: 'center'});
                                el.style.border = '3px solid red';
                                el.style.backgroundColor = '#fff3cd';
                                break;
                            }
                        }
                    }""",
                    keywords
                )

                await page.wait_for_timeout(2000)

                # ---- Screenshot relevant section ----
                screenshot_path = os.path.join(
                    SCREENSHOT_DIR, f"{domain.replace('.', '_')}_focused.png"
                )
                await page.screenshot(path=screenshot_path, full_page=False)

                # ---- Extract nearby images ----
                images = await page.evaluate(
                    """() => {
                        const imgs = Array.from(document.images)
                            .filter(img => img.width > 150 && img.height > 150)
                            .slice(0, 5)
                            .map(img => img.src);
                        return imgs;
                    }"""
                )

                saved_images = []
                for idx, img_url in enumerate(images):
                    try:
                        img_data = requests.get(img_url, timeout=10).content
                        img_path = os.path.join(
                            IMAGE_DIR, f"{domain.replace('.', '_')}_{idx}.jpg"
                        )
                        with open(img_path, "wb") as f:
                            f.write(img_data)
                        saved_images.append(img_path)
                    except Exception:
                        pass

                # ---- Extract cleaned text ----
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                    tag.decompose()

                text = soup.get_text(separator=" ", strip=True)
                text = re.sub(r"\s+", " ", text)

                await browser.close()

                if len(text) < MIN_CONTENT_LEN:
                    self._save_js_heavy_domain(domain)
                    return "", []

                return text[:MAX_TEXT_LEN], saved_images

            except Exception as e:
                print(f"❌ Browser error: {e}")
                self._save_js_heavy_domain(domain)
                await browser.close()
                return "", []

    # -------------------- Pipeline --------------------

    async def run(self, query):
        results = self.search(query)
        context = []

        for r in results:
            context.append({
                "source": r["url"],
                "text": r["snippet"]
            })

        if all(not self.snippet_insufficient(r["snippet"]) for r in results):
            return context

        for r in results:
            url = r["url"]
            if self.is_js_heavy(url):
                continue

            text, images = await self.scrape_with_browser(url, query)
            if text:
                context.append({
                    "source": url,
                    "text": text,
                    "images": images
                })
                return context

        return context


# ============================================================
# USAGE
# ============================================================

if __name__ == "__main__":

    agent = SmartWebAgent(show_browser=True)

    queries = [
        "transformer attention mechanism",
        "Venezuela oil production sanctions"
    ]

    for q in queries:
        result = asyncio.run(agent.run(q))

        print(f"\n📄 RESULT FOR QUERY: {q}")
        for r in result:
            print(f"\nSOURCE: {r['source']}")
            print(r["text"][:300])
            if "images" in r:
                print("🖼️ Images:")
                for img in r["images"]:
                    print("  ", img)
