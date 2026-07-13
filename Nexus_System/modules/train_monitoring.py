import os
import time
import sys
import requests
import json
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utility import send_discord_alert, commit_github

# --- Configuration & Memory ---
script_dir = os.path.dirname(os.path.abspath(__file__))
# Cache the trains into this file to prevent duplicate alerts
ALERT_CACHE = os.path.join(script_dir, "train_status_cache.txt")
# Separate file for platform tracking to ensure it isn't cleared by delay logic
PLATFORM_CACHE = os.path.join(script_dir, "platform_history.txt")

# Journey details, which the bot will use to alert me of issues
config_path = os.path.join(script_dir, "train_routes.json")
with open(config_path, "r") as f:
    ROUTES = json.load(f)

def check_trains():
    # Load previously alerted bad events
    if os.path.exists(ALERT_CACHE):
        with open(ALERT_CACHE, "r") as f:
            sent_alerts = {line.strip() for line in f if line.strip()}
    else:
        sent_alerts = set()

    # Load platform history
    history = {}
    if os.path.exists(PLATFORM_CACHE):
        with open(PLATFORM_CACHE, "r") as f:
            for line in f:
                if '|' in line:
                    sid, plat = line.strip().split('|')
                    history[sid] = plat

    new_history = {}
    current_active_alerts = []

    for route in ROUTES:
        from_st = route["from"]
        to_st = route["to"]
        route_name = route["name"]

        # Gets the train data from the Huxley API.
        url = f"https://huxley2.azurewebsites.net/departures/{from_st}/to/{to_st}" 

        try:
            responses = requests.get(url, timeout=10)
            responses.raise_for_status()
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
            platform = train.get("platform") or "TBA"

            # 1. Platform Change Detection
            if service_id in history and history[service_id] != platform and platform != "TBA":
                message = (f"⚠️ **Platform Change!**\n"
                           f"The **{scheduled}** service ({route_name}) "
                           f"has moved to **Platform {platform}**.")
                send_discord_alert("trains", message)
                time.sleep(2)
            
            new_history[service_id] = platform

            # Get the cancellation status
            is_cancelled = train.get("isCancelled", False)
            cancel_reason = train.get("cancelReason", "No reason provided.")

            if not scheduled:
                continue

            # Calculate delay
            delay_amount = 0
            if estimated and estimated.replace(":", "").isdigit():
                sched_min = int(scheduled.split(":")[0]) * 60 + int(scheduled.split(":")[1])
                est_min = int(estimated.split(":")[0]) * 60 + int(estimated.split(":")[1])
                delay_amount = max(0, est_min - sched_min)

            # Train is cancelled
            if is_cancelled:
                snapshot = f"{scheduled}_{route_name}_Cancelled"
                current_active_alerts.append(snapshot)

                if snapshot not in sent_alerts:
                    message = (f"**Southern Cancelled Train!!**\n"
                               f"The **{scheduled}** Southern service ({route_name}) has been **cancelled**.\n"
                               f"🚫**Reason:** {cancel_reason}")
                    send_discord_alert("trains", message)
                    time.sleep(5)
                
            elif delay_amount >= 5 or estimated == "Delayed":
                snapshot = f"{scheduled}_{route_name}_{delay_amount} minutes"
                current_active_alerts.append(snapshot)

                if snapshot not in sent_alerts:
                    
                    # Direction-aware urgency logic
                    if delay_amount >= 30 or estimated == "Delayed":
                        if from_st == "HMD" and to_st == "MCB":
                            urgency_msg = "🚨 **SEVERE DELAYS!** Do not travel. Study from home!"
                        elif from_st == "MCB" and to_st == "HMD":
                            urgency_msg = "🚨 **SEVERE DELAYS!** Get home quickly!"
                        else:
                            urgency_msg = "🚨 **DO NOT TRAVEL if you can!** Get home immediately or find another route."
                    else:
                        urgency_msg = f"⚠️ **Reason:** {delay_reason}"

                    message = (f"**Southern alert!**\n"
                               f"The **{scheduled}** Southern service ({route_name}) "
                               f"is running **{delay_amount} minutes late**\n"
                               f"{urgency_msg}")
                    
                    # Send to Discord
                    send_discord_alert("trains", message)
                    time.sleep(5)

    # Save platform history
    with open(PLATFORM_CACHE, "w") as f:
        for sid, plat in new_history.items():
            f.write(f"{sid}|{plat}\n")

    # Save alert cache
    with open(ALERT_CACHE, "w") as f:
        f.write("\n".join(current_active_alerts))

    commit_github(ALERT_CACHE, f"Update train cache - {len(current_active_alerts)} issues")

# Runs every 5 minutes
if __name__ == "__main__":
    print("Checking for problems on Southern's network...")
    check_trains()
    print("Check complete. Powering down.")