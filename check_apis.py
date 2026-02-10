import requests

urls = [
    "https://cyborx.net/api/autog.php",
    "https://babachecker.com/api/autog.php",
    "http://206.206.78.217:1212", # HITTER_API
]

for url in urls:
    try:
        print(f"Checking {url}...")
        resp = requests.get(url, timeout=5)
        print(f"Status: {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")
