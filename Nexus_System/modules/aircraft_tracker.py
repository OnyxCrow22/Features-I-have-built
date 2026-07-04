import requests
import os
import sys
import time
import math

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utility import send_discord_alert

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def current_location():
    try:
        resp = requests.get('http://ip-api.com/json/', timeout=3).json()
        return resp['lat'], resp['lon'], resp['city']
    except:
        return 50.77, 0.28, "Eastbourne"


def check_local_airspace():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    AIRCRAFT_FILE = os.path.join(script_dir, "aircraft_cache.txt")

    # --- CONFIGURATION ---
    CURRENT_LAT, CURRENT_LON, CURRENT_CITY = current_location()
    RADIUS_KM = 15

    # Aircraft to monitor:
    WATCHLIST = ["ZA947", "PA474", "DRAGON01", "EZY", "BAW", "RYR", "GBMSB", "GAIDN", "GAWGB",
                 "GMCSW", "MIL", "SPMIL", "CFE", "EFW", "EJU", "ZZ334", "RRR"]
    
    BOX_DEG = RADIUS_KM / 111
    LAT_MIN, LAT_MAX = CURRENT_LAT - BOX_DEG, CURRENT_LAT + BOX_DEG
    LON_MIN, LON_MAX = CURRENT_LON - BOX_DEG * 1.5, CURRENT_LON + BOX_DEG * 1.5

    url = f"https://opensky-network.org/api/states/all?lamin={LAT_MIN}&lamax={LAT_MAX}&lomin={LON_MIN}&lomax={LON_MAX}" # The Uniform Resource Locator for fetching the data

    try:
        if os.path.exists(AIRCRAFT_FILE):
            with open(AIRCRAFT_FILE, "r") as f:
                seen_aircraft = [line.strip() for line in f if line.strip()]
        else:
            seen_aircraft = [] # New list

        response = requests.get(url, timeout=10)
        if (response.status_code != 200):
            print(f"Hmm, it appears the OpenSky API could not be reached at this time. Please try again later")
            return
        
        data = response.json() # Output contents to a .JSON file
        states = data.get("states", [])

        if not states:
            print(f"Target airspace is currently void of targeted aircraft at the moment.")
            # clear cache
            with open(AIRCRAFT_FILE, "w") as f:
                f.write("")
                return
            
        new_alert = [] # New list for alerts
        newly_alerted_aircraft = [] # The aircraft currently being tracked by the Discord bot

        for flight in states:
            icao24 = flight[0].strip().lower() # Get the ICAO code
            callsign = flight[1].strip().upper() if flight[1] else "EMPTY" # Get the callsign, if known
            on_ground = flight[8] # Check whether the aircraft is on the ground or in the air
            lat, lon = flight[6], flight[5] # Lat and Lon from OpenSky

            if on_ground or not lat or not lon:
                continue # Not worth tracking

            dist = haversine(CURRENT_LAT, CURRENT_LON, lat, lon)
            if dist > RADIUS_KM:
                continue # Too far away from the current location

            is_watched = any(item in callsign or item in icao24 for item in WATCHLIST) # Is the aircraft being watched?
            is_uncommon = "MIL" in callsign or "RESCUE" in callsign # Is the aircraft uncommon?

            if is_watched or is_uncommon:
                if icao24 not in seen_aircraft:
                    source_label = "🚨 WATCHLIST MATCH!" if is_watched else "😃 UNCOMMON AIRCRAFT FOUND!"

                    message = (
                        f"**{source_label}**\n"
                        f"✈️ **Callsign:** {callsign} \n"
                        f"🌐 **Origin point:** {flight[2]} \n"
                        f"📍 **Radar Tracker**: [ADS-B Exchange](https://globe.adsbexchange.com/?icao={icao24})" 
                        )
                    new_alert.append(message)
                    newly_alerted_aircraft.append(icao24)

        if new_alert:
            for i, alert in enumerate(new_alert):
                send_discord_alert("aircraft", alert)
                if i < len(new_alert) - 1:
                    time.sleep(5)

            with open(AIRCRAFT_FILE, "a") as f:
                for ac in newly_alerted_aircraft:
                    f.write(f"{ac}\n")
        else:
            print("No aircraft detected :(")

    except Exception as e:
        print(f"ERROR checking airspace!")

if __name__ == "__main__":
    CURRENT_LAT, CURRENT_LON, CURRENT_CITY = current_location()
    print("Scanning EWS area for aircraft...")
    check_local_airspace()

            