import requests
import os
import subprocess

def send_discord_alert(category, message):
    env_key = f"{category.upper()}_WEBHOOK_URL"
    url = os.environ.get(env_key)

    if not url:
        print(f"Error: Could not find the environment variable {env_key}. Please set it!.")
        return
    
    payload = {"content": message}
    try:
        requests.post(url, json=payload, timeout=10)
        requests.raise_for_status()
        return True

    except Exception as e:
        print(f"Failed to send Discord alert!")
        return False

def commit_github(cache_path, commit_message="Update cache"):
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", cache_path], check=True)
        
        # Check if there are staged changes
        result = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if result.returncode!= 0: # 1 = changes exist
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            subprocess.run(["git", "push"], check=True)
            print(f"Committed {os.path.basename(cache_path)}")
            return True
        else:
            print(f"No changes to {os.path.basename(cache_path)}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"Git commit failed for {cache_path}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected git error: {e}")
        return False
