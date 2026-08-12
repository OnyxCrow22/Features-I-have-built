import sqlite3
import os
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "nexus.db")

def initialise_database():
    connect = sqlite3.connect(DB_PATH)
    cursor = connect.cursor()

    # Table for Aircraft
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS aircraft_cache (
            icao24 TEXT PRIMARY KEY,
            callsign TEXT,
            registration TEXT,
            aircraft_type TEXT,
            lat REAL,
            lon REAL,
            distance_miles REAL,
            is_watchlist INTEGER,
            timestamp REAL,
            formatted_time TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS train_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_name TEXT,
            scheduled_time TEXT,
            delay_minutes INTEGER,
            disruption_score INTEGER,
            reason TEXT,
            timestamp REAL
        )
    ''')

    connect.commit()
    connect.close()

def aircraft_event(flight, distance, is_watched):
    icao24 = flight.get('hex', '').strip().lower()
    callsign = flight.get('flight', '').strip().upper() or "EMPTY"
    raw_registration = flight.get('r', '').strip().upper() or "UNKNOWN"
    aircraft_type = flight.get('t', '').strip().upper() or "UNKNOWN"
    lat = flight.get('lat')
    lon = flight.get('lon')
    now = time.time()
    formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
    
    connect = sqlite3.connect(DB_PATH)
    cursor = connect.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO aircraft_cache (
            icao24, callsign, registration, aircraft_type, lat, lon, distance_miles, is_watchlist, timestamp, formatted_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (icao24, callsign, raw_registration, aircraft_type, lat, lon, round(distance, 1), 1 if is_watched else 0, now, formatted_time))

    connect.commit()
    connect.close()

initialise_database()