import requests

urls = [
    "https://heartcry.simpledonation.com/",
    "https://st-charge-1.vercel.app/check?gateway=St_Charge_1$&key=AloneOp&cc=1|1|1|1"
]

for url in urls:
    try:
        print(f"Checking {url}...")
        resp = requests.get(url, timeout=10)
        print(f"Status: {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")
