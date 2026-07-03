import os
import requests
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utility import send_discord_alert

def check_epic_freebies():
    CACHED_FILE = "epic_cache.txt" # Cache the file
    url = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=GB&allowCountries=GB" # Scan for free games

    try:
        response = requests.get(url).json()
        elements = response["data"]["Catalog"]["searchStore"]["elements"]

        current_free_game = []
        for game in elements:
            # Check for a free game promotional offer
                offers = game["promotions"]["promotionalOffers"]
                if offers:
                    current_free_game.append(game["title"])

        if os.path.exists(CACHED_FILE):
             with open(CACHED_FILE, "r") as f:
                  seen_games = [line.strip() for line in f]

        else:
             seen_games = [] # Make a new list

        # Only alert me if there is a new game released every week.
        new_game = [g for g in current_free_game if g not in seen_games]
        
        if new_game:
            message = "Epic Games are currently giving these freebies this week: \n" + "\n".join([f"- {game}" for game in new_game])
            send_discord_alert("gaming_price", message)

            # Updates the cached file, preventing duplicate announcments every two hours.
            with open (CACHED_FILE, "w") as f:
                 f.write("\n".join(current_free_game))

    except Exception as e:
        print(f"Failed to find Free games! :(")

if __name__ == "__main__":
    check_epic_freebies()