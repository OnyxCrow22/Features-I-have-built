import os
import time
import sys
import requests
import json
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utility import send_discord_alert, commit_github

# --- CONFIGURATION, MEMORY AND ROUTES --------------------- #
script_dir = os.path.dirname(os.path.abspath(__file__))
# Cache the trains into this file to prevent duplicate alerts
ALERT_CACHE = os.path.join(script_dir, "train_status_cache.txt")
# Separate file for platform tracking to ensure it isn't cleared by delay logic
PLATFORM_CACHE = os.path.join(script_dir, "platform_history.txt")

# Journey details, which the bot will use to alert me of issues
CONFIGURATION_PATH = os.path.join(script_dir, "train_routes.json")

def load_routes():
    if os.path.exists(CONFIGURATION_PATH):
        with open(CONFIGURATION_PATH, "r") as f:
            return json.load(f)
    return []

# ---------------------------- ALERT CACHE MANAGEMENT ---------------------- #

def LOAD_alert_cache(CACHED_FILE):
    if os.path.exists(CACHED_FILE):
        with open(CACHED_FILE, "r") as f:
            return {line.strip() for line in f if line.strip()}
    return set()

def SAVE_alert_cache(CACHED_FILE, CURRENT_ALERTS):
    with open(CACHED_FILE, "w") as f:
        f.write("\n".join(CURRENT_ALERTS))
    commit_github(CACHED_FILE, f"Update Train Cache - {len(CURRENT_ALERTS)} issues")

# --------------------------- PLATFORM CACHE MANAGEMENT -------------------- #

def LOAD_platform_history(CACHED_FILE):
    plat_history = {}
    if os.path.exists(CACHED_FILE):
        with open(CACHED_FILE, "r") as f:
            for line in f:
                if "|" in line:
                    sid, plat = line.strip().split("|")
                    plat_history[sid] = plat
    return plat_history

def SAVE_platform_history(CACHED_FILE, PLATFORM_DATA):
    with open(CACHED_FILE, "w") as f:
        for sid, plat in PLATFORM_DATA.items():
            f.write(f"{sid}|{plat}\n")

# --------------------------- DELAY CALCULATOR --------------------------- #
def calculate_delay(scheduled, estimated):
    if estimated and estimated.replace(":", "").isdigit():
        try: 
            sched_min = int(scheduled.split(":")[0]) * 60 + int(scheduled.split(":")[1])
            est_min = int(estimated.split(":")[0]) * 60 + int(estimated.split(":")[1])
            return max(0, est_min - sched_min)
        except (ValueError, IndexError):
            pass
    return 0

# ----------------------- ROUTE DATA ----------------------------- #
def route_data(from_st, to_st):
    url = f"https://huxley2.azurewebsites.net/departures/{from_st}/to/{to_st}" 

    try:
            responses = requests.get(url, timeout=10)
            responses.raise_for_status()
            return responses.json().get("trainServices", [])
    except Exception as e:
            print(f"Network error detected in checking {from_st}->{to_st}: {e}")
            return []

# ------------------- MESSAGE FORMATTERS ---------------------- #
def format_platform_msg(scheduled, route_name, platform_num):
    return (
        f"ℹ️ **Platform Change!**\n"
        f"The **{scheduled}** service ({route_name}) "
        f"has moved to **Platform {platform_num}**."
    )

def format_alert_msg(alert, disruption_score):
    if alert["type"] == "cancelled":
        return (
            f"❌ **Train cancellation!**\n"
            f"The **{alert['scheduled']}** service {alert['route_name']} has been CANCELLED!\n"
            f"**This is because of**: {alert['reason']}"
        )


    delay_text = "Delayed Indefinitely" if alert['is_indefinite'] else f"This train is currently running **{alert['delay_amount']} minutes late**"

    if alert['is_major'] and disruption_score >= 4: # Only alert if the score is equal or above two
        if alert['from_st'] == "HMD" and alert['to_st'] == "MCB":
            severe_msg = "🛑 **SEVERE DELAYS REPORTED!**: Do NOT travel. Complete work at home!"
        elif alert['from_st'] == "MCB" and alert['to_st'] == "HMD":
            severe_msg = "🛑 **SEVERE DELAYS REPORTED!**: GO HOME"
        else:
            severe_msg = "🚨 **MULTIPLE ISSUES ACROSS THE NETWORK!!**: Consider alternative transportation!"
    else:
        severe_msg = f"⚠️ **This is because of**: {alert['reason']}"

    return (
        f"⚠️**Service delay alert!**\n"
        f"The **{alert['scheduled']}** service ({alert['route_name']})\n"
        f"is {delay_text}\n"
        f"{severe_msg}"
    )
 
def check_trains():
    routes = load_routes() # Load the routes
    sent_alerts = LOAD_alert_cache(ALERT_CACHE) # Load the alert cached file
    history = LOAD_platform_history(PLATFORM_CACHE) # Load the platform alert cache file
    
    new_history = {}
    current_active_alerts = []
    pending_alerts = [] # For the new alert system
    disruption_score = 0 # 0 means no issues, 10 means widespread disruption

    for route in routes:
        from_st = route["from"]
        to_st = route["to"]
        route_name = route["name"]

        train_services = route_data(from_st, to_st)
        if not train_services:
            continue 
        
        for train in train_services:
            # Get the service ID of the train on the route.
            service_id = train.get("serviceID") 
            scheduled = train.get("std") 
            estimated = train.get("etd") 
            delay_reason = train.get("delayReason", "No reason provided.")
            cancel_reason = train.get("cancelReason", "No reason provided.")
            is_cancelled = train.get("isCancelled", False)
            platform = train.get("platform") or "TBA"

            # Platform Change Detection
            if service_id in history and history[service_id] != platform and platform != "TBA":
                plat_msg = format_platform_msg(scheduled, route_name, platform)
                send_discord_alert("trains", plat_msg)
                time.sleep(2)
            
            new_history[service_id] = platform

            if not scheduled:
                continue

            # Calculate delay
            delay_amount = calculate_delay(scheduled, estimated)
            is_indefinite_delay = (estimated == "Delayed")

            # Train is cancelled
            if is_cancelled:
                snapshot = f"{scheduled}_{route_name}_Cancelled"
                current_active_alerts.append(snapshot)
                disruption_score += 1 # One point added

                if snapshot not in sent_alerts:
                    pending_alerts.append({
                        "snapshot": snapshot,
                        "scheduled": scheduled,
                        "route_name": route_name,
                        "type": "cancelled",
                        "reason": cancel_reason,
                        "from_st": from_st,
                        "to_st": to_st
                    })
                
            elif delay_amount >= 5 or is_indefinite_delay:
                snapshot = f"{scheduled}_{route_name}_{delay_amount} minutes"
                current_active_alerts.append(snapshot)

                IS_MAJOR = (delay_amount >= 30 or is_indefinite_delay)
                if IS_MAJOR:
                    disruption_score += 1

                if snapshot not in sent_alerts:
                    pending_alerts.append({
                        "snapshot": snapshot,
                        "scheduled": scheduled,
                        "route_name": route_name,
                        "type": "delayed",
                        "delay_amount": delay_amount,
                        "is_indefinite": is_indefinite_delay,
                        "is_major": IS_MAJOR,
                        "reason": delay_reason,
                        "from_st": from_st,
                        "to_st": to_st
                    })

    for alert in pending_alerts:
        alert_msg = format_alert_msg(alert, disruption_score)
        send_discord_alert("trains", alert_msg)
        time.sleep(5)

    SAVE_platform_history(PLATFORM_CACHE, new_history)
    SAVE_alert_cache(ALERT_CACHE, current_active_alerts)

# Runs every 5 minutes
if __name__ == "__main__":
    print("Checking for problems on Southern's network...")
    check_trains()
    print("Check complete. Powering down.")