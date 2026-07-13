import requests
import os
import time
import xml.etree.ElementTree as ET
import email.utils
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, urlunparse
import re
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utility import send_discord_alert, commit_github

def clean_html(text):
    if not text:
        return ""
    
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    
    # Improved decoding and cleanup
    clean = clean.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&gt;', '>').replace('&quot;', '"')
    
    # Strip away common repeating junk patterns often found in Google News RSS
    # This removes redundant repeating news source mentions
    clean = re.sub(r'(\w+&nbsp;)+', '', clean)
    
    # Final cleanup of multiple spaces
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def normalise_link(URL): # Stop news from spamming
    if not URL:
        return ""
    parsed = urlparse(URL)

    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

# Check for the latest headlines
def check_headlines():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    CACHED_FILE = os.path.join(script_dir, "news_cache.txt")
    
    # Words that should be blocked
    BLOCKLIST = ["sponsored", "advertorial", "promoted", "ad:"]

    # The news sources supplied
    NEWS_SOURCE = {
        "UK News": "https://news.google.com/rss/topics/CAAqJQgKIh9DQkFTRVFvSUwyMHZNRGR6YzJNU0JXVnVMVWRDS0FBUAE?hl=en-GB&gl=GB&ceid=GB%3Aen",
        "International News": "https://news.google.com/rss/topics/CAAqKggKIiRDQkFTRlFvSUwyMHZNRGx1YlY4U0JXVnVMVWRDR2dKSFFpZ0FQAQ?hl=en-GB&gl=GB&ceid=GB%3Aen",
        "Local News": "https://news.google.com/rss/topics/CAAqHAgKIhZDQklTQ2pvSWJHOWpZV3hmZGpJb0FBUAE/sections/CAQiUENCSVNOam9JYkc5allXeGZkakpDRUd4dlkyRnNYM1l5WDNObFkzUnBiMjV5Q3hJSkwyMHZNREUzTkhGdGVnc0tDUzl0THpBeE56UnhiU2dBKjEIACotCAoiJ0NCSVNGem9JYkc5allXeGZkako2Q3dvSkwyMHZNREUzTkhGdEtBQVABUAE?hl=en-GB&gl=GB&ceid=GB%3Aen"
    }

    try:
        # Load existing seen links into a list for immediate tracking
        if os.path.exists(CACHED_FILE):
            with open(CACHED_FILE, "r", encoding="utf-8") as f:
                seen_links = [line.strip() for line in f if line.strip()]
        else:
            seen_links = []

        current_links = list(seen_links) # Keep track of all links to save back to file later
        new_stories = [] # New stories to be alerted

        for source_name, rss_url in NEWS_SOURCE.items():
            print(f"Checking {source_name}")
            try:
                responses = requests.get(rss_url, timeout=10)
                responses.raise_for_status()
                root = ET.fromstring(responses.content)
                now = datetime.now(timezone.utc)

                for item in root.findall(".//item")[:10]:
                    title = item.find("title").text if item.find("title") is not None else "No Title"
                    link = item.find("link").text if item.find("link") is not None else ""
                    description = item.find("description").text if item.find("description") is not None else ""
                    pub_date_text = item.find("pubDate").text if item.find("pubDate") is not None else None

                    if not link:
                        continue
                    
                    # --- BLOCKLIST CHECK ---
                    content_to_check = (title + " " + description).lower()
                    if any(term in content_to_check for term in BLOCKLIST):
                        print(f"Skipping blocked content: {title}")
                        continue
                    # -----------------------

                    clean_link = normalise_link(link)

                    # Real-time duplicate check: skip if we've already processed this link in this run or previous runs
                    if clean_link in seen_links:
                        continue

                    # Mark as seen immediately so it doesn't get processed again
                    seen_links.append(clean_link)
                    current_links.append(clean_link)

                    is_recent = True
                    if pub_date_text:
                        try:
                            pub_date = email.utils.parsedate_to_datetime(pub_date_text)
                            if now - pub_date > timedelta(hours=2):
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
                print(f"FAILURE in fetching RSS feed for {source_name}: {e}")
                continue

        if new_stories:
            for i, story in enumerate(new_stories):
                send_discord_alert("news", story)
                if i < len(new_stories) - 1:
                    time.sleep(5)
        else:
            print("No new headlines found!")

        # Save all links (seen + new) to cache
        with open(CACHED_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(current_links))

        commit_github(CACHED_FILE, f"Update news cache - {len(current_links)} headlines tracked")

    except Exception as e:
        print(f"ERROR fetching news!: {e}")

if __name__ == "__main__":
    print("Checking for breaking news...")
    check_headlines()