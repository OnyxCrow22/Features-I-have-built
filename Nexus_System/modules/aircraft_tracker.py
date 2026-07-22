import requests
import os
import sys
import time
import math
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared_utility import send_discord_alert, commit_github

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def current_location():
    # Check for manual override first
    if os.getenv('OVERRIDE_LAT') is not None:
        return float(os.getenv('OVERRIDE_LAT')), float(os.getenv('OVERRIDE_LON')), os.getenv('OVERRIDE_CITY', 'Custom')
    
    if os.getenv('GITHUB_ACTIONS') == 'true':
        print("Running on GitHub Actions - forcing Eastbourne coords")
        return 50.77, 0.28, "Eastbourne"
    
    try:
        resp = requests.get('http://ip-api.com/json/', timeout=3).json()
        return resp['lat'], resp['lon'], resp['city']
    except Exception as e:
        print(f"Geolocation failed: {e}")
        return 50.77, 0.28, "Eastbourne"


def check_local_airspace():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    AIRCRAFT_FILE = os.path.join(script_dir, "aircraft_cache.txt")
    WATCHLIST_FILE = os.path.join(script_dir, "aircraft_watchlist.json")

    # --- CONFIGURATION ---
    CURRENT_LAT, CURRENT_LON, CURRENT_CITY = current_location()
    RADIUS_KM = 50 # 30 Miles

    # Load Watchlist from JSON
    try:
        if os.path.exists(WATCHLIST_FILE):
            with open(WATCHLIST_FILE, "r") as f:
                watchlist_data = json.load(f)
        else:
            watchlist_data = {"registrations": [], "callsigns": []}
    except Exception as e:
        print(f"Failed to load watchlist JSON: {e}")
        watchlist_data = {"registrations": [], "callsigns": []}

    # Normalize tracking terms to uppercase for reliable matching
    watch_regs = {reg.strip().upper() for reg in watchlist_data.get("registrations", [])}
    watch_callsigns = [call.strip().upper() for call in watchlist_data.get("callsigns", [])]

    url = f"https://api.adsb.lol/v2/point/{CURRENT_LAT}/{CURRENT_LON}/{RADIUS_KM}"

    try:
        if os.path.exists(AIRCRAFT_FILE):
            with open(AIRCRAFT_FILE, "r") as f:
                previously_seen_icaos = {line.strip() for line in f if line.strip()}
        else:
            previously_seen_icaos = set()

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        aircraft_list = response.json().get('ac', [])
        
        if not aircraft_list:
            print(f"Target airspace is currently void of targeted aircraft at the moment.")
            # clear cache
            with open(AIRCRAFT_FILE, "w") as f:
                f.write("")
            commit_github(AIRCRAFT_FILE, "Clear Aircraft cache")
            return
            
        new_alert = [] # New list for alerts
        newly_alerted_aircraft = [] # The aircraft currently being tracked by the Discord bot

        for flight in aircraft_list:
            icao24 = flight.get('hex', '').strip().lower() # Get the ICAO code
            callsign = flight.get('flight', '').strip().upper() or "EMPTY" # Get the callsign
            on_ground = flight.get('ground', False) # Check ground status
            lat = flight.get('lat') 
            lon = flight.get('lon')

            if on_ground or not lat or not lon:
                continue # Not worth tracking

            dist = haversine(CURRENT_LAT, CURRENT_LON, lat, lon)
            if dist > RADIUS_KM:
                continue # Too far away from the current location
            
            registration = flight.get('r', '').strip().upper() # Get registration
            
            # Match directly against registration, or partially check if any watched callsign is inside the flight callsign
            is_watched = (
                (registration and registration in watch_regs) or 
                any(item in callsign for item in watch_callsigns)
            )
            is_uncommon = "RESCUE" in callsign or flight.get('type') == "MILT"

            if is_watched or is_uncommon:
                if icao24 not in previously_seen_icaos:
                    source_label = "🚨 WATCHLIST MATCH!" if is_watched else "😃 UNCOMMON AIRCRAFT FOUND!"

                    registration_label = registration if registration else "Unknown"
                    aircraft_type = flight.get('t') or "Unknown"

                    message = (
                        f"**{source_label}**\n"
                        f"✈️ **Callsign:** {callsign} \n"
                        f"📝 **{registration_label}** | **Type:** {aircraft_type}\n"
                        f"🗺️ **Distance from {CURRENT_CITY}**: {dist:.1f}km\n"
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

            commit_github(AIRCRAFT_FILE, "Update aircraft cache")
        else:
            print("No aircraft detected :(")

    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    CURRENT_LAT, CURRENT_LON, CURRENT_CITY = current_location()
    print("Scanning EWS area for aircraft...")
    check_local_airspace()