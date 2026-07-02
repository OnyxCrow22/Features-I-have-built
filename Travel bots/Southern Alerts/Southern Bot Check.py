import time
import requests
from datetime import datetime, timedelta

# The link for the bot to feed into.
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1522249965559349459/-0T8gQFHHIpMPyskyJGrIiKsLSr8XNLYZFLXA90nvE4Q8hM52ahsl7wlf36crvvzJ9tq"

# Journey details, which the bot will use to alert me of issues
ROUTES = [
    {"from": "HMD", "to": "MCB", "name": "Hampden Park to Moulsecoomb"},
    {"from": "MCB", "to": "HMD", "name": "Moulsecoomb to Hampden Park"}
]

# Track already sent alerts, so I do not bombard my phone
ALREADY_SENT = {}

# Clear trains older than two hours
def clean_memory():
    now = datetime.now()
    cutoff = now - timedelta(hours=2)

    expired_keys = [sid for sid, timestamp in ALREADY_SENT.items() if timestamp < cutoff]
    for sid in expired_keys:
        del ALREADY_SENT[sid]

def check_trains():
    clean_memory()
    now = datetime.now()

    for route in ROUTES:
        from_st = route["from"]
        to_st = route["to"]
        route_name = route["name"]

        url = f"https://huxley2.azurewebsites.net/departures/{from_st}/to/{to_st}" # Gets the train data from the Huxley API.

        try:
            responses = requests.get(url, timeout=10)
            if responses.status_code != 200:
                print(f"Failed to fetch train data for {route_name}!")
                continue
            data = responses.json()
        except Exception as e:
            print(f"Network error detected in checking for {route_name}: {e}")
            continue

        train_services = data.get("trainServices", []) # Get a list of the train services on that explicit route.

        if not train_services:
            continue 
    
        
        for train in train_services:
            service_id = train.get("serviceID") # Get the service ID of the train on the route.
            
            if service_id in ALREADY_SENT:
                continue # Not interested in ones already sent

            scheduled = train.get("std") 
            estimated = train.get("etd") 
            delay_reason = train.get("delayReason", "No reason provided.")

            # Get the cancellation status
            is_cancelled = train.get("isCancelled", False)
            cancel_reason = train.get("cancelReason", "No reason provided.")

            # Train is cancelled
            if is_cancelled:
                message = (f"**Southern Cancelled Train!!**\n"
                           f"The **{scheduled}** Southern service ({route_name}) has been **cancelled**.\n"
                           f"💬 **Reason:** {cancel_reason}")
                payload = {"content": message}
                requests.post(DISCORD_WEBHOOK_URL, json=payload)
                
                
                ALREADY_SENT[service_id] = now
                print(f"Cancellation alert sent for {scheduled} train ({route_name})")
                time.sleep(15)
                continue

            # Only interested in trains delayed by five minutes or more
            if estimated and estimated.lower() != "on time" and "delayed" not in estimated.lower():
                try:
                    sched_min = int(scheduled.split(":")[0]) * 60 + int(scheduled.split(":")[1])
                    est_min = int(estimated.split(":")[0]) * 60 + int(estimated.split(":")[1])
                    delay_amount = est_min - sched_min

                    # Trigger the alert
                    if delay_amount >= 5:
                        message = (f"**Southern alert!**\n"
                                   f"The **{scheduled}** Southern service ({route_name}) "
                                   f"is running **{delay_amount} minutes late**\n"
                                   f"💬 **Reason:** {delay_reason}")
                        
                        # Send to Discord
                        payload = {"content": message}
                        requests.post(DISCORD_WEBHOOK_URL, json=payload)

                        ALREADY_SENT[service_id] = now
                        print(f"Alert sent for {scheduled} train - {delay_amount} mins late ({route_name})")
                        time.sleep(15)

                # No time displayed?
                except:
                    pass

# Runs every 5 minutes
if __name__ == "__main__":
    print("Checking for problems on Southern's network...")
    check_trains()
    print("Check complete. Powering down.")