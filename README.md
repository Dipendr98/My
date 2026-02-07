# CC KILLER v2.0 - Telegram Bot

High-performance, bulletproof Telegram bot for checking credit card validity across multiple gates.

## ✨ Features
- **🚀 Turbo Speed**: 0.3s average response time with concurrent checking (150+ parallel).
- **🌐 Proxy Support**: Built-in support for proxy rotation and authentication.
- **🛡️ Security**: Authorized users filter and anti-flood protection.
- **🔍 Smart Tokenizer**: Advanced regex to extract cards from any text format.
- **⚔️ Premium Gates**: Stripe, BT, Amazon, Hitter, NMI, Payflow.
- **🔥 Auto-Stealer**: Approved and **Charged** cards are instantly forwarded to the owner.

## 🛠️ Setup Instructions

1. **Install Python 3.8+**
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment**:
   - Rename `.env` template or create it.
   - Fill in your `API_ID`, `API_HASH`, `BOT_TOKEN`, and `OWNER_ID`.
4. **Configure Proxy (Optional)**:
   - Add your proxy to `PROXY_URL` in `.env`.
   - Supports `http://user:pass@ip:port` format.
5. **Run the Bot**:
   ```bash
   python cc_killer_main.py
   ```

## 📜 Commands
- `/start` or `/help` - Bot info and help.
- `/chk` or `/killer <card>` - Check a single card.
- `/mchk` or `/mkiller <text/file>` - Mass check multiple cards.
- `/str`, `/btn`, `/rzp`, `/shp`, `/payu` - Specific gate checks.
- `/addsite` or `/addurl <url>` - Add merchant site for checking.
- `/listsites` - View all added sites.

## ⚠️ Security Note
Keep your `.env` file secret. Do not share your `BOT_TOKEN` or `API_HASH`.
