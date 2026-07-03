import requests
import os
import time
import xml.etree.ElementTree as ET
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utility import send_discord_alert

def check_headlines():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    CACHED_FILE = os.path.join(script_dir, "news_cache.txt")

    # Get the BBC News UK Top Stories RSS Feed
    NEWS_SOURCE = {
        "BBC News": "https://feeds.bbci.co.uk/news/rss.xml",
        "Sky News": "https://news.sky.com/feeds/rss/home.xml",
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


                for item in root.findall(".//item")[:1]:
                    title = item.find("title").text
                    link = item.find("link").text
                    description = item.find("description").text

                    current_links.append(link)

                    if link not in seen_links:
                        formatted_story = f"**{title}**\n>{description}\n{link}"
                        new_stories.append(formatted_story)

            except Exception as e:
                print(f"FAILURE in fetching RSS feed!: {e}")
            continue

        if new_stories:
            for i, story in enumerate(new_stories):
                send_discord_alert("news", story)

                if (i < len(new_stories) - 1):
                    time.sleep(25)

        else:
            print(f"No headlines found!")

        with open(CACHED_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(current_links))

    except Exception as e:
        print(f"ERROR fetching news from {source_name}!: {e}")

if __name__ == "__main__":
    print("Checking for breaking news...")
    check_headlines()