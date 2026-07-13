import requests
import os
import sys
import time
import math

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

    # --- CONFIGURATION ---
    CURRENT_LAT, CURRENT_LON, CURRENT_CITY = current_location()
    RADIUS_KM = 19 # 11 Miles

    # Aircraft to monitor:
    WATCHLIST = ["ZA947", "PA474", "GBMSB", "GAIDN", "GAWGB",
                 "GMCSW", "GCCA", "GCICK", "MIL", "SPMIL", "ZZ334", "RRR", "GMRLL", "ZK313",
                 "ZK317", "P7350", "AB910", "TE311", "LF363", "PZ865", "GBYWT",
                 "GBYDB", "FHMEL", "GJPT", "GEWIZ", "GNGTC", "GIIRP", "GBPLM",
                 "GHJSS", "GAYIJ", "GJJGI", "GBSET", "GCCXB", "GSPRX", "GSPRK", "FAYSB",
                 "FHUSA", "DLZFN", "RED1", "RED2", "RED3", "RED4", "RED5", "RED6", "RED7", "UAE", "ETIHAD", "EMIRATES",
                 "CGFMX", "GAF359", "LNDHY", "LNDHZ", "JAL"]

    url = f"https://api.adsb.lol/v2/point/{CURRENT_LAT}/{CURRENT_LON}/{RADIUS_KM}" # The Uniform Resource Locator for fetching the data

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
            callsign = flight.get('flight', '').strip().upper() or "EMPTY" # Get the callsign, if known
            on_ground = flight.get('ground', False) # Check whether the aircraft is on the ground or in the air
            lat = flight.get('lat') # Lat and Lon from ADSB
            lon = flight.get('lon')

            if on_ground or not lat or not lon:
                continue # Not worth tracking

            dist = haversine(CURRENT_LAT, CURRENT_LON, lat, lon)
            if dist > RADIUS_KM:
                continue # Too far away from the current location
            
            registration = flight.get('r', '').strip.upper() # Get the flight's registration
            is_watched = any(item in callsign or item in icao24 for item in WATCHLIST) # Is the aircraft being watched?
            is_uncommon = "MIL" in callsign or "RESCUE" in callsign or flight.get('type') == "MILT" # Is the aircraft uncommon?

            if is_watched or is_uncommon:
                if icao24 not in previously_seen_icaos:
                    source_label = "🚨 WATCHLIST MATCH!" if is_watched else "😃 UNCOMMON AIRCRAFT FOUND!"

                    registration = flight.get('r') or "Unknown"
                    aircraft_type = flight.get('t') or "Unknown"

                    message = (
                        f"**{source_label}**\n"
                        f"✈️ **Callsign:** {callsign} \n"
                        f"📝 **{registration}** | **Type:** {aircraft_type}\n"
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

            