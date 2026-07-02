import os
import requests
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utility import send_discord_alert

def check_epic_freebies():
    url = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=GB&allowCountries=GB" # Scan for free games

    try:
        response = requests.get(url).json()
        elements = response["data"]["Catalog"]["searchStore"]["elements"]

        free_game = []
        for game in elements:
            # Check for a free game promotional offer
            if game.get("promotions") and game["promotions"].get("promotionalOffers"):
                offers = game["promotions"]["promotionalOffers"]
                if offers:
                    free_game.append(game["title"])

        if free_game:
            message = "Epic Games are currently giving these freebies this week: \n" + "\n".join([f"- {game}" for game in free_game])
            send_discord_alert("gaming_price", message)

    except Exception as e:
        print(f"Failed to find Free games! :(")

if __name__ == "__main__":
    check_epic_freebies()