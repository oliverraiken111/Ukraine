import requests
from bs4 import BeautifulSoup
import datetime
import xml.etree.ElementTree as ET
import json

# WSJ Syria section
url = "https://www.wsj.com/topics/place/syria"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

response = requests.get(url, headers=headers)
response.raise_for_status()
soup = BeautifulSoup(response.text, "html.parser")

# Set up RSS feed
ET.register_namespace('media', 'http://search.yahoo.com/mrss/')
rss = ET.Element('rss', {"version": "2.0", "xmlns:media": "http://search.yahoo.com/mrss/"})
channel = ET.SubElement(rss, 'channel')
ET.SubElement(channel, 'title').text = "WSJ Syria News"
ET.SubElement(channel, 'link').text = url
ET.SubElement(channel, 'description').text = "Latest news on Syria from the Wall Street Journal"
ET.SubElement(channel, 'lastBuildDate').text = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

# Extract Syria-specific articles
articles_found = 0
seen_titles = set()

for teaser in soup.select('a[href^="/articles/"]'):
    title = teaser.get_text(strip=True)
    href = teaser["href"]

    if not title or title in seen_titles:
        continue

    seen_titles.add(title)
    full_url = "https://www.wsj.com" + href

    # Fetch article page to extract real pubDate
    pub_date = datetime.datetime.utcnow()  # fallback if not found
    try:
        article_resp = requests.get(full_url, headers=headers)
        article_resp.raise_for_status()
        article_soup = BeautifulSoup(article_resp.text, "html.parser")

        json_ld_tag = article_soup.find("script", type="application/ld+json")
        if json_ld_tag:
            json_ld = json.loads(json_ld_tag.string)
            # WSJ sometimes wraps in list
            if isinstance(json_ld, list):
                json_ld = json_ld[0]
            date_str = json_ld.get("datePublished")
            if date_str:
                pub_date = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))

    except Exception as e:
        print(f"⚠️ Failed to extract pubDate for '{title}': {e}")

    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "link").text = full_url
    ET.SubElement(item, "description").text = f"WSJ article on Syria: {title}"
    ET.SubElement(item, "pubDate").text = pub_date.strftime("%a, %d %b %Y %H:%M:%S GMT")

    articles_found += 1
    if articles_found >= 10:
        break

# Write output
with open("wsj_syria.xml", "wb") as f:
    ET.ElementTree(rss).write(f, encoding="utf-8", xml_declaration=True)

print(f"✅ RSS feed created with {articles_found} Syria-specific articles.")
