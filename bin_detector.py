def get_bin_info(bin6: str) -> dict:
    """Detailed BIN lookup for premium UI."""
    # Common prefixes for demonstration
    BIN_DATA = {
        "400112": {"bank": "HDFC BANK", "country": "INDIA", "flag": "🇮🇳", "type": "DEBIT", "level": "CLASSIC"},
        "426869": {"bank": "CITIBANK", "country": "USA", "flag": "🇺🇸", "type": "CREDIT", "level": "SIGNATURE"},
        "439227": {"bank": "SBI", "country": "INDIA", "flag": "🇮🇳", "type": "DEBIT", "level": "PLATINUM"},
        "512345": {"bank": "CHASE", "country": "USA", "flag": "🇺🇸", "type": "CREDIT", "level": "WORLD"},
        "371234": {"bank": "AMERICAN EXPRESS", "country": "USA", "flag": "🇺🇸", "type": "CREDIT", "level": "PLATINUM"},
        "400022": {"bank": "NAVY FEDERAL CREDIT UNION", "country": "UNITED STATES", "flag": "🇺🇸", "type": "DEBIT", "level": "CLASSIC"}
    }
    
    # Prefix level country detection
    COUNTRY_MAP = {
        "4": "United States", "5": "United States", "3": "United States", "6": "India"
    }
    FLAG_MAP = {
        "4": "🇺🇸", "5": "🇺🇸", "3": "🇺🇸", "6": "🇮🇳"
    }

    data = BIN_DATA.get(bin6)
    if not data:
        # Fallback for unknown BINs
        prefix = bin6[0]
        return {
            "bank": "UNKNOWN BANK",
            "country": COUNTRY_MAP.get(prefix, "GLOBAL"),
            "flag": FLAG_MAP.get(prefix, "🌍"),
            "type": "UNKNOWN",
            "level": "STANDARD"
        }
    return data

def get_gate_priority(bin6: str) -> list:
    if bin6.startswith(("4", "5", "3")):
        return ["Stripe", "Braintree", "Amazon"]
    return ["Stripe", "Braintree"]

print("✅ PREMIUM BIN DETECTOR LOADED")