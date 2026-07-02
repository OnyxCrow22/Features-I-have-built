import requests
import os

def send_discord_alert(category, message):
    env_key = f"{category.upper()}_WEBHOOK_URL"
    url = os.environ.get(env_key)

    if not url:
        print(f"Error: Could not find the environment variable {env_key}. Please set it!.")
        return
    
    payload = {"content": message}
    try:
        requests.post(url, json=payload)

    except Exception as e:
        print(f"Failed to send Discord alert!")