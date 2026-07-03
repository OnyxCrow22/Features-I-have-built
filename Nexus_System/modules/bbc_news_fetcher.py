import requests
import os
import xml.etree.ElementTree as ET
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utility import send_discord_alert

def check_headlines():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    CACHED_FILE = os.path.join(script_dir, "news_cache.txt")

    # Get the BBC News UK Top Stories RSS Feed
    rss_url = "https://feeds.bbci.co.uk/news/rss.xml"

    try:
        responses = requests.get(rss_url, timeout=10)
        if responses.status_code != 200:
            print("FAILED to fetch the BBC News RSS Feed")
            return
        
        root = ET.fromstring(responses.content) # Turn the content into a string

        if (os.path.exists(CACHED_FILE)):
            with open(CACHED_FILE, "r") as f:
                seen_links = [line.strip() for line in f if line.strip()]

        else:
            seen_links = [] # Create a new list

        current_links = [] # Create a new current link list
        new_stories = [] # Create a new stories list

        for item in root.findall(".//item")[:5]:
            title = item.find("title").text
            link = item.find("link").text
            description = item.find("description").text

            current_links.append(link)

            if link not in seen_links:
                formatted_story = f"**{title}**\n>{description}\n{link}"
                new_stories.append(formatted_story)

        if new_stories:
            for story in reversed(new_stories):
                send_discord_alert("news", story)

        else:
            print(f"No headlines found!")

        with open(CACHED_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(current_links))

    except Exception as e:
        print(f"ERROR fetching news from BBC News!: {e}")

if __name__ == "__main__":
    print("Checking for breaking news...")
    check_headlines()