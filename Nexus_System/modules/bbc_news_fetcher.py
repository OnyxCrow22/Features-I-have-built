import requests
import os
import time
import xml.etree.ElementTree as ET
import email.utils
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse
import re
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utility import send_discord_alert

def clean_html(text):
    # Remove junk from RSS feed
    if not text:
        return ""
    
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)

    # Decode HTML attributes
    clean = clean.replace('&nbsp; ', ' ').replace('&amp;', '&').replace('&gt;', '>').replace('&quot;', '"')
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean # Finish cleaning up

def normalise_link(URL): # Stop news from spamming
    if not URL:
        return ""
    parsed = urlparse(URL)

    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

def check_headlines():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    CACHED_FILE = os.path.join(script_dir, "news_cache.txt")

    # Get the BBC News UK Top Stories RSS Feed
    NEWS_SOURCE = {
        "BBC News": "https://feeds.bbci.co.uk/news/rss.xml",
        "Sky News": "https://feeds.skynews.com/feeds/rss/home.xml",
        "Daily Mail": "https://www.dailymail.co.uk/home/index.rss",
        "The Guardian": "https://www.theguardian.com/uk/rss"
    }

    try:
        if (os.path.exists(CACHED_FILE)):
            with open(CACHED_FILE, "r", encoding = "utf-8") as f:
                seen_links = [line.strip() for line in f if line.strip()]

        else:
            seen_links = [] # Create a new list

        current_links = [] # Create a new current link list
        new_stories = [] # Create a new stories list

        for source_name, rss_url in NEWS_SOURCE.items():
            print(f"Checking {source_name}")
            try:
                responses = requests.get(rss_url, timeout=10)
                if responses.status_code != 200:
                    print(f"FAILED to fetch feed from {source_name}'s RSS Feed!")
                    continue

                root = ET.fromstring(responses.content)
                now = datetime.now(timezone.utc)


                for item in root.findall(".//item")[:10]:
                    title = item.find("title").text if item.find("title") is not None else "No Title"
                    link = item.find("link").text if item.find("link") is not None else ""
                    description = item.find("description").text if item.find("description") is not None else ""
                    pub_date_text = item.find("pubDate").text if item.find("pubDate") is not None else None

                    if not link:
                        continue

                    clean_link = normalise_link(link)
                    current_links.append(clean_link)

                    if clean_link not in seen_links:
                        is_recent = True
                        if pub_date_text:
                            try:
                                pub_date = email.utils.parsedate_to_datetime(pub_date_text)
                                if now - pub_date > timedelta(minutes=15):
                                    is_recent = False
                            except Exception:
                                pass

                        if is_recent:
                            clean_description = clean_html(description)

                            if len(clean_description) > 250:
                                clean_description = clean_description[:247] + "..."
                            formatted_story = f"**{title}**\n>{clean_description}\n{link}"
                            new_stories.append(formatted_story)

            except Exception as e:
                print(f"FAILURE in fetching RSS feed!: {e}")
                continue

        if new_stories:
            for i, story in enumerate(new_stories):
                send_discord_alert("news", story)

                if (i < len(new_stories) - 1):
                    time.sleep(5)

        else:
            print(f"No headlines found!")

        with open(CACHED_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(current_links))

    except Exception as e:
        print(f"ERROR fetching news!: {e}")

if __name__ == "__main__":
    print("Checking for breaking news...")
    check_headlines()