import asyncio
import httpx
from xml.etree import ElementTree as ET
from urllib.parse import quote_plus

async def test_google_news(company: str = "Google"):
    query = quote_plus(f'"{company}"')
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    
    print(f"Connecting to: {url}\n")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                print("✅ Connection Successful (200 OK)")
                root = ET.fromstring(r.content)
                items = root.findall("./channel/item")
                print(f"✅ Found {len(items)} news items for '{company}'")
                
                # Show top 2 articles
                for i, item in enumerate(items[:2]):
                    print(f"\n[{i+1}] {item.findtext('title')}")
                    print(f"    Link: {item.findtext('link')}")
            else:
                print(f"❌ Failed with Status Code: {r.status_code}")
    except Exception as e:
        print(f"❌ Error occurred: {e}")

if __name__ == "__main__":
    import sys
    company_query = sys.argv[1] if len(sys.argv) > 1 else "Google"
    asyncio.run(test_google_news(company_query))
