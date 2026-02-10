import razorpay
try:
    client = razorpay.Client(auth=("key", "secret"))
    print(dir(client.payment))
except Exception as e:
    print(e)
