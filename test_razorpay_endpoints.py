import razorpay
import requests
import json

key = "rzp_live_Rfe6IjnX0n3ToN"
secret = "bNwyMG7yUeFBmk68qLqTFRH0"

print(f"Testing Keys: {key}")

# 1. Try Order Create (Known working?)
try:
    client = razorpay.Client(auth=(key, secret))
    order = client.order.create({
        "amount": 100,
        "currency": "INR",
        "receipt": "test_1",
        "notes": {"purpose": "test"}
    })
    print(f"Order Create: SUCCESS, Order ID: {order['id']}")
except Exception as e:
    print(f"Order Create: FAILED, {e}")

# 2. Try POST /payments/create/json (The one failing)
try:
    print("Trying /payments/create/json...")
    resp = requests.post(
        "https://api.razorpay.com/v1/payments/create/json",
        auth=(key, secret),
        # Razorpay expects form-urlencoded or json? Library uses form encoded usually for older endpoints or json for newer.
        # But let's try standard request
        data={
            "amount": 100, 
            "currency": "INR", 
            "email": "test@test.com", 
            "contact": "9999999999", 
            "method": "card",
            "card[number]": "411111111111111",
            "card[expiry_month]": "12",
            "card[expiry_year]": "2030",
            "card[cvv]": "123"
        }
    )
    print(f"POST /payments/create/json: {resp.status_code}")
    print(resp.text[:200])
except Exception as e:
    print(f"POST /payments/create/json: ERROR, {e}")

# 3. Try POST /payments (Direct)
try:
    print("Trying /payments...")
    # This endpoint usually requires capturing, but let's see response
    resp = requests.post(
        "https://api.razorpay.com/v1/payments",
        auth=(key, secret),
        data={
            "amount": 100, 
            "currency": "INR", 
            "email": "test@test.com", 
            "contact": "9999999999", 
        }
    )
    print(f"POST /payments: {resp.status_code}")
    print(resp.text[:200])
except Exception as e:
    print(f"POST /payments: ERROR, {e}")
