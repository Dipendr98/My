import razorpay

key = "rzp_live_Rfe6IjnX0n3ToN"
secret = "bNwyMG7yUeFBmk68qLqTFRH0"

client = razorpay.Client(auth=(key, secret))

try:
    # This should fail with 404
    client.payment.createPaymentJson({
        "amount": 100, 
        "currency": "INR", 
        "email": "test@test.com", 
        "contact": "9999999999", 
        "method": "card",
        "card": {
            "number": "411111111111111",
            "expiry_month": "12",
            "expiry_year": "2030",
            "cvv": "123",
            "name": "Test User"
            }
    })
except Exception as e:
    print(f"Exception Type: {type(e)}")
    print(f"Exception String: '{str(e)}'")
    print(f"Contains 'requested url was not found': {'requested url was not found' in str(e).lower()}")
