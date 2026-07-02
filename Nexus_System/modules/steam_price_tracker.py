import requests
import time
import sys
import os

# Adds the parent directory to the search path so it can find shared_utility
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utility import send_discord_alert

# Checks for the Steam prices inside of the wishlist.txt file
def check_steam_prices():

    script_dir = os.path.dirname(os.path.abspath(__file__))

    file_path = os.path.join(script_dir, "wishlist.txt")
    
    sales_report = [] # New list for listing everything on sale

    try:
        with open(file_path, "r") as f:
            app_ids = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return
    
    for app_id in app_ids:
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=gb"
        response = requests.get(url).json()

        app_data = response.get(app_id, {})
        if app_data.get("success") and "data" in app_data:
            data = app_data["data"]
            price_info = data.get("price_overview")

            if price_info and price_info["discount_percent"] > 0:
                name = data["name"]
                price = price_info["final_formatted"]
                discount = price_info["discount_percent"]
                sales_report.append(f"**{name}** is currently **{discount}% off**! The current price is **{price}**")

    if sales_report:
        nexus_message = f"Steam Sales Alert:\n" + "\n".join(sales_report)
        send_discord_alert("gaming_price", nexus_message)

if __name__ == "__main__":
    check_steam_prices()
