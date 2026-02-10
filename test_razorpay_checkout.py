import requests
import json

key = "rzp_live_Rfe6IjnX0n3ToN"
secret = "bNwyMG7yUeFBmk68qLqTFRH0"

try:
    # 1. Create Order first
    order_resp = requests.post(
        "https://api.razorpay.com/v1/orders",
        auth=(key, secret),
        json={
            "amount": 100,
            "currency": "INR",
            "receipt": "test_chk_1",
            "notes": {"purpose": "test"}
        }
    )
    order_id = order_resp.json().get("id")
    print(f"Order ID: {order_id}")

    if order_id:
        # 2. Try Standard Checkout Endpoint (mimicking SDK)
        # This is usually NOT authenticated with Secret, but with Public Key?
        # But for S2S we want to use the key:secret if possible.
        
        # Endpoint used by Razorpay.js
        url = "https://api.razorpay.com/v1/payments/create/checkout" 
        
        payload = {
            "key_id": key,
            "order_id": order_id,
            "amount": 100,
            "currency": "INR",
            "contact": "9999999999",
            "email": "test@test.com",
            "method": "card",
            "card": {
                "number": "411111111111111",
                "expiry_month": "12",
                "expiry_year": "30",
                "cvv": "123",
                "name": "Test User"
            }
        }
        
        print("Testing v1/payments/create/checkout...")
        resp = requests.post(url, json=payload)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text[:300]}")

except Exception as e:
    print(e)
