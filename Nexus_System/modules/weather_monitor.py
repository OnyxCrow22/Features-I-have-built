import requests
from datetime import datetime

def weather_data(lat, lon): # For getting the current weather
    url = "https://api.open-meteo.com/v1/forecast" # Open meteo's API
    parameters = {
        "latitude": lat, # The current latitude
        "longitude": lon, # The current longitude
        "current": ["temperature_2m", "weather_code", "wind_speed_10m"], # The current temperature, weather and wind speed
        "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min"], # The daily weather, temperature maximum and temperature minimum
        "timezone": "auto", # Automatically set the timezone
        "models": "ukmo_seamless" # Use the Met Office's model
    }

    alert_url = f"https://alerts.open-meteo.com/v1/alerts?latitude={lat}&longitude={lon}" # Get the alert for the current location

    try:
        response = requests.get(url, params=parameters) # Get the URL using the parameters
        response.raise_for_status()
        weather_data = response.json() # Convert into a .json file

        alert_response = requests.get(alert_url) # Get the weather warning alert
        alert_response.raise_for_status()
        alert_data = alert_response.json() # Convert into a .json file

        return weather_data, alert_data # Return both the weather and alert datas
    
    except requests.exceptions.RequestException as WE:
        print(f"Failure in fetching requested data! {WE}")
        return None, None # Failure
    
def WMO_codes(wCode):
    mapping = {
        0: "Clear Sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
        80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
        # A list of possible weather 
    }
    return mapping.get(wCode, "Unknown Weather")

def weather_report(weather, alert):
    if not weather:
        return
    
    current = weather['current'] # Current weather conditions

    daily = weather['daily']
    for i in range(7):
        date_str = daily['time'][i]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A, %b, %d")
        max_temperature = daily['temperature_2m_max'][i]
        minimum_temperature = daily['temperature_2m_min'][i]
        conditions = WMO_codes(daily['weather_code'][i])

LONDON_LAT = 51.498
LONDON_LON = -0.143

weather_json, alert_json = weather_data(LONDON_LAT, LONDON_LON)
weather_report(weather_json, alert_json)

