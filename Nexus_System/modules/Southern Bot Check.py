import os
import time
import sys
import requests
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utility import send_discord_alert

# --- Configuration & Memory ---
script_dir = os.path.dirname(os.path.abspath(__file__))
TRAIN_CACHED_FILE = os.path.join(script_dir, "train_status_cache.txt") # Cache the trains into this file

# Journey details, which the bot will use to alert me of issues
ROUTES = [
    {"from": "HMD", "to": "MCB", "name": "Hampden Park to Moulsecoomb"},
    {"from": "MCB", "to": "HMD", "name": "Moulsecoomb to Hampden Park"}
]

def check_trains():
    if os.path.exists(TRAIN_CACHED_FILE): # Does the requested file exist?
        with open(TRAIN_CACHED_FILE, "r") as f:
            sent_snapshots = [line.strip() for line in f if line.strip()] # Search through the file
    else:
        sent_snapshots = [] # Make a new list

    current_bad_snapshot = [] # Make a list of bad snapshots

    for route in ROUTES:
        from_st = route["from"]
        to_st = route["to"]
        route_name = route["name"]

        # Gets the train data from the Huxley API.
        url = f"https://huxley2.azurewebsites.net/departures/{from_st}/to/{to_st}" 

        try:
            responses = requests.get(url, timeout=10)
            if responses.status_code != 200:
                print(f"Failed to fetch train data for {route_name}!")
                continue
            data = responses.json()
        except Exception as e:
            print(f"Network error detected in checking for {route_name}: {e}")
            continue

        # Get a list of the train services on that explicit route.
        train_services = data.get("trainServices", []) 

        if not train_services:
            continue 
        
        for train in train_services:
            # Get the service ID of the train on the route.
            service_id = train.get("serviceID") 
            scheduled = train.get("std") 
            estimated = train.get("etd") 
            delay_reason = train.get("delayReason", "No reason provided.")

            # Get the cancellation status
            is_cancelled = train.get("isCancelled", False)
            cancel_reason = train.get("cancelReason", "No reason provided.")

            # Calculate delay
            delay_amount = 0
            if estimated and estimated.replace(":", "").isdigit():
                sched_min = int(scheduled.split(":")[0]) * 60 + int(scheduled.split(":")[1])
                est_min = int(estimated.split(":")[0]) * 60 + int(estimated.split(":")[1])
                delay_amount = max(0, est_min - sched_min)

            # Train is cancelled
            if is_cancelled:
                snapshot = f"{scheduled}_{route_name}_Cancelled"
                current_bad_snapshot.append(snapshot)

                if snapshot not in sent_snapshots:
                    message = (f"**Southern Cancelled Train!!**\n"
                               f"The **{scheduled}** Southern service ({route_name}) has been **cancelled**.\n"
                               f"🚫**Reason:** {cancel_reason}")
                    send_discord_alert("trains", message)
                    time.sleep(5)
                
            elif delay_amount >= 5:
                snapshot = f"{scheduled}_{route_name}_{delay_amount} minutes"
                current_bad_snapshot.append(snapshot)

                if snapshot not in sent_snapshots:
                        message = (f"**Southern alert!**\n"
                                   f"The **{scheduled}** Southern service ({route_name}) "
                                   f"is running **{delay_amount} minutes late**\n"
                                   f"⚠️**Reason:** {delay_reason}")
                        # Send to Discord
                        send_discord_alert("trains", message)
                        time.sleep(5)

    with open(TRAIN_CACHED_FILE, "w") as f:
        f.write("\n".join(current_bad_snapshot))

# Runs every 5 minutes
if __name__ == "__main__":
    print("Checking for problems on Southern's network...")
    check_trains()
    print("Check complete. Powering down.")