
import asyncio
from gates import check_paypal_render

async def main():
    print("Testing PayPal Render Gate...")
    
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
