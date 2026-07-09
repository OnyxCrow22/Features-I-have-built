import os
import requests
import sys
import json
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utility import send_discord_alert, commit_github

def check_epic_freebies():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    CACHED_FILE = os.path.join(script_dir, "epic_cache.txt")
    url = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=GB&allowCountries=GB" # Scan for free games

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        elements = data["data"]["Catalog"]["searchStore"]["elements"]

        current_free_game = []
        now = datetime.now(timezone.utc)

        for game in elements:
            title = game.get("title", "Unknown")

            promotions = game.get("promotions") # Find promotions
            if not promotions: # No promotions?
                continue # Carry on

            promo_offers = promotions.get("promotionalOffers", [])
            if not promo_offers:
                continue

            for offer_group in promo_offers:
                for offer in offer_group.get("promotionalOffers", []):
                    discount_pct = offer.get("discountSetting", {}.get("discountPercentage"), 0)

                    start_date = offer.get("startDate")
                    end_date = offer.get("endDate")

                    if discount_pct == 0 and start_date and end_date:
                        try:
                            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

                            if start <= now <= end:
                                current_free_game.append(title)
                        except Exception as e:
                            continue

        current_free_game = list(set(current_free_game))

        if os.path.exists(CACHED_FILE):
             with open(CACHED_FILE, "r") as f:
                  seen_games = [line.strip() for line in f]

        else:
             seen_games = set()

        # Only alert me if there is a new game released every week.
        new_game = [g for g in current_free_game if g not in seen_games]
        
        if new_game:
            message = "Epic Games are currently giving these freebies this week: \n" + "\n".join([f"- {game}" for game in new_game])
            send_discord_alert("gaming_price", message)
        else:
            print("No freebies found")

            # Updates the cached file, preventing duplicate announcments every two hours.
        with open (CACHED_FILE, "w") as f:
            f.write("\n".join(current_free_game))

        commit_github(CACHED_FILE, f"Update Epic cache - {len(current_free_game)} free games")

    except Exception as e:
        print(f"Failed to find Free games! {e}")

if __name__ == "__main__":
    check_epic_freebies()