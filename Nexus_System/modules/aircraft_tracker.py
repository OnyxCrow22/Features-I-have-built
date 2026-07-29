import requests
import os
import sys
import time
import math
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared_utility import send_discord_alert, commit_github

def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8 # Earth's radius in miles
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
    
#--------------- LOAD WATCHLIST FROM JSON FILE --------------#
def load_watchlist(watchlist_file):
    try:
        if os.path.exists(watchlist_file):
            with open(watchlist_file, "r") as f:
                watchlist_data = json.load(f)
        else:
            watchlist_data = {"registrations": [], "callsigns": []}
    except Exception as e:
        print(f"Failed to load watchlist file! {e}")
        watchlist_data = {"registrations": [], "callsigns": []}

    watch_regs = {reg.strip().upper() for reg in watchlist_data.get("registrations", [])}
    watch_callsigns = [call.strip().upper() for call in watchlist_data.get("callsigns", [])]

    return watch_regs, watch_callsigns

#--------------- LOAD CACHE ---------------#
def load_cache(cached_file, expiry_amount):
    seen_cache = {}
    current_time = time.time()

    if os.path.exists(cached_file):
            with open(cached_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if "|" in line:
                        ac_ICAO, ts = line.split("|")
                        try:
                            if current_time - float(ts) < expiry_amount:
                                seen_cache[ac_ICAO.lower()] = float(ts)
                        except ValueError:
                            continue
                    elif line:
                        seen_cache[line.lower()] = current_time

    return seen_cache

#------------------------------------- SAVE CACHE ----------------------------#
def save_cache(cache_file, seen_cache):
        with open(cache_file, "w") as f:
            for ac_ICAO, ts in seen_cache.items():
                f.write(f"{ac_ICAO}|{ts}\n")

#------------------------------------ EVALUATION OF AIRCRAFT -----------------#
def evaluate_aircraft(flight, watch_regs, watch_callsigns):
            callsign = flight.get('flight', '').strip().upper() or "EMPTY" # Get callsign
            registration = flight.get('r', '').strip().upper() # Get registration
            
            # Match directly against registration, or partially check if any watched callsign is inside the flight callsign
            is_watched = (
                (registration and registration in watch_regs) or 
                any(item in callsign for item in watch_callsigns)
            )
            is_uncommon = "RESCUE" in callsign or flight.get('type') == "MILT"

            return (is_watched or is_uncommon), is_watched

#------------------------------ DISCORD ALERT SYSTEM -----------------------#
def alert_server(flight, distance, city_name, is_watched):
    callsign = flight.get('flight', '').strip().upper() or "EMPTY"
    registration = flight.get('r', '').strip().upper() or "Unknown"
    aircraft_type = flight.get('t') or "Unknown"
    ICAO24 = flight.get('hex', '').strip().lower()

    source_label = "🚨 WATCHLIST MATCH!" if is_watched else "😃 UNCOMMON AIRCRAFT FOUND!"
    return (
        f"**{source_label}**\n"
        f"✈️ **Aircraft Callsign:** {callsign} \n"
        f"📝 **Aircraft Registration: {registration}** | **Type:** {aircraft_type}\n"
        f"🗺️ **Distance from {city_name}**: {distance:.1f} miles\n"
        f"📍 **Radar Tracker**: [ADS-B Exchange](https://globe.adsbexchange.com/?icao={ICAO24})" 
    )

#---------------------------- MAIN FUNCTION ----------------------#

def check_local_airspace():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    AIRCRAFT_FILE = os.path.join(script_dir, "aircraft_cache.txt")
    WATCHLIST_FILE = os.path.join(script_dir, "aircraft_watchlist.json")

    # --- CONFIGURATION ---
    CURRENT_LAT, CURRENT_LON, CURRENT_CITY = current_location()
    RADIUS_MILES = 30 # 30 Miles
    RADIUS_NM = int(RADIUS_MILES * 0.868976) # Convert mile into Nautical Mile.
    CACHE_EXPIRY_SECONDS = 10800 # Approximately three hours

    watch_regs, watch_callsigns = load_watchlist(WATCHLIST_FILE) # Load the current watchlist
    seen_cache = load_cache(AIRCRAFT_FILE, CACHE_EXPIRY_SECONDS)

    url = f"https://api.adsb.lol/v2/point/{CURRENT_LAT}/{CURRENT_LON}/{RADIUS_NM}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        aircraft_list = response.json().get('ac', [])
        
        if not aircraft_list:
            print(f"Target airspace is currently void of targeted aircraft at the moment.")
            return
            
        new_alert = [] # New list for alerts
        processed_aircraft = set() # The aircraft currently being tracked by the Discord bot
        current_time = time.time()

        for flight in aircraft_list:
            icao24 = flight.get('hex', '').strip().lower() # Get the ICAO code
            on_ground = flight.get('ground', False) # Check ground status
            lat = flight.get('lat') 
            lon = flight.get('lon')

            if on_ground or not lat or not lon or not icao24:
                continue # Not worth tracking

            if icao24 in processed_aircraft:
                continue # Do not log again

            dist = haversine(CURRENT_LAT, CURRENT_LON, lat, lon)
            if dist > RADIUS_MILES:
                continue # Too far away from the current location

            is_matched, is_watched = evaluate_aircraft(flight, watch_regs, watch_callsigns) # Use the aircraft evaluation method

            if is_matched:
                processed_aircraft.add(icao24)

                if icao24 not in seen_cache:
                    alert_msg = alert_server(flight, dist, CURRENT_CITY, is_watched)
                    new_alert.append(alert_msg)
                    seen_cache[icao24] = current_time

        # Only send alert if a new aircraft is found
        if new_alert:
            for i, alert in enumerate(new_alert):
                send_discord_alert("aircraft", alert)
                if i < len(new_alert) - 1:
                    time.sleep(5)

        save_cache(AIRCRAFT_FILE, seen_cache)

        if new_alert:
            commit_github(AIRCRAFT_FILE, "Update aircraft cache")
        else:
            print("No aircraft identified within target airspace.")

    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    print("Scanning EWS area for aircraft...")
    check_local_airspace()