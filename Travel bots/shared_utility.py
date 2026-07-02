import requests

def send_discord_alert(webhook_url, message):
    payload = {"content": message}
    try:
        requests.post(webhook_url, json=payload)

    except Exception as e:
        print(f"Failed to send Discord alert!")