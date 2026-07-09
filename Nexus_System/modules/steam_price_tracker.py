import requests
import time
import sys
import os
import subprocess

# Adds the parent directory to the search path so it can find shared_utility
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utility import send_discord_alert, commit_github

# Checks for the Steam prices inside of the wishlist.txt file
def check_steam_prices():

    script_dir = os.path.dirname(os.path.abspath(__file__))
    WISHLIST_FILE = os.path.join(script_dir, "wishlist.txt")
    CACHED_FILE = os.path.join(script_dir, "steam_cache.txt")
    
    sale_alerts = [] # New list for listing everything on sale
    current_sale_snapshot = [] # Track the current snapshot

    try:
        with open(WISHLIST_FILE, "r") as f:
            app_ids = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return
    
    for app_id in app_ids:
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=gb"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            json_data = response.json()
            app_data = json_data.get(app_id, {})

        except Exception as SE:
            print(f"Failed to fetch {app_id}! {SE}")
            continue

        if app_data.get("success") and "data" in app_data:
                data = app_data["data"]
                price_info = data.get("price_overview")

                if price_info and price_info["discount_percent"] > 0:
                    name = data["name"]
                    price = price_info["final_formatted"]
                    discount = price_info["discount_percent"]

                    snapshot_str = f"{app_id}_{discount}"
                    current_sale_snapshot.append(snapshot_str)

                    alert_msg = (f"**{name}** is currently **{discount}% off**! The current price is **{price}**")
                    sale_alerts.append((snapshot_str, alert_msg))

    # Load the previous cached file
    if (os.path.exists(CACHED_FILE)):
        with open(CACHED_FILE, "r", encoding="utf-8") as f:
            seen_sales = [line.strip() for line in f if line.strip()]
    else:
        seen_sales = []
    
    new_sale_report = [] # Create a new sale report
    for snapshot, sales_report in sale_alerts:
         if snapshot not in seen_sales:
              new_sale_report.append(sales_report)
    
    # Fresh data? Ping it to Discord!
    if new_sale_report:
        nexus_message = f"Steam Sales Alert:\n" + "\n".join(new_sale_report)
        send_discord_alert("gaming_price", nexus_message)
    else:
        print(f"No new Steam sales currently occuring!")

    with open(CACHED_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(current_sale_snapshot))

    commit_github(CACHED_FILE, f"Update cache - {len(current_sale_snapshot)} sales")

if __name__ == "__main__":
    check_steam_prices()
