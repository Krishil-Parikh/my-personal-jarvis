#!/usr/bin/env python3
import requests
import re
from urllib.parse import quote_plus, unquote

url = f'https://www.google.com/search?q={quote_plus("python programming")}&num=20'

session = requests.Session()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,*/*',
    'Accept-Language': 'en-US,en;q=0.9',
}

print("Fetching Google search...")
resp = session.get(url, headers=headers, timeout=10)
print(f"Status: {resp.status_code}")
print(f"Content length: {len(resp.text)}")

# Extract URLs using regex
pattern = r'/url\?q=([^&]+)'
matches = re.findall(pattern, resp.text)
print(f"\nFound {len(matches)} URLs with regex /url\\?q=...")

if matches:
    print("\nFirst 10 URLs:")
    for i, m in enumerate(matches[:10], 1):
        try:
            decoded = unquote(m)
            if decoded.startswith('http'):
                print(f"  {i}. {decoded[:90]}")
        except:
            pass
else:
    print("\nNo URLs found. Checking raw content...")
    if '/url' in resp.text:
        print("Found '/url' in response - debug regex")
        idx = resp.text.find('/url')
        print(resp.text[idx:idx+200])
