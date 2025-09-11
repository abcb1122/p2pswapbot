# P2P Bitcoin Swap Bot v2.0 🔄

A non-custodial Telegram bot for peer-to-peer Lightning Network ⚡ and Bitcoin onchain swaps with advanced privacy features and automated settlement.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Network: Testnet](https://img.shields.io/badge/Network-Testnet-orange.svg)](https://mempool.space/testnet)
[![Status: Beta](https://img.shields.io/badge/Status-Beta-yellow.svg)](https://t.me/btcp2pswapbot)

## 🎯 Current Implementation Status

### ✅ Completed Features
- **Full Swap-Out Flow**: Complete swapout steps Lightning → Bitcoin implementation
- **Granular Timeouts**: Stage-specific expiration handling
- **Privacy Integration**: lnproxy.org invoice wrapping with retry logic
- **Automated Monitoring**: Background threads for confirmations and payments
- **Coordinated Notifications**: Smart timing for user notifications
- **Batch Processing**: Grouped Bitcoin transactions for efficiency
- **Auto-Recovery**: Automatic offer reactivation on timeouts

### 🚧 In Development
- Real Bitcoin batch sending (currently simulated)
- Lightning payment verification (placeholder for LND integration)
- Swap-In flow (Bitcoin → Lightning)
- Dispute resolution system

### ⏳ Planned
- Multi-signature escrow
- Mainnet deployment

## 📋 Complete Swap-Out Flow

### Overview: Ana (Lightning Seller) ↔️ Carlos (Bitcoin Buyer)

The bot facilitates a trustless swap where Ana sells Lightning sats for Bitcoin onchain, and Carlos buys Lightning sats with Bitcoin onchain.

### Step-by-Step Flow with Actual Messages

#### **Phase 1: Offer Creation (Ana)**

**Step 1: Ana starts the bot**
```
Ana: /start

Bot: 🔄 P2P Bitcoin Swap Bot

Welcome!

Commands:
/swapout - Lightning ⚡ → Bitcoin ₿
/swapin - Bitcoin ₿ → Lightning ⚡  
/offers - View your active offers
/profile - Your stats
/help - More info

Channel: @btcp2pswapoffers
Status: Live & Ready ✅
```

**Step 2: Ana creates swap-out offer**
```
Ana: /swapout

Bot: Swap Out: Lightning ⚡ → Bitcoin ₿

Select amount:
[10.000] [100.000]  (buttons)
```

**Step 3: Ana selects amount**
```
Ana: [Clicks 100.000 button]

Bot: ✅ Offer Created #42

Swap Out: Lightning → Bitcoin
Amount: 100.000 sats
Completed swaps: 0

Your offer is live in @btcp2pswapoffers
Relax and wait for someone to take it
```

**Step 4: Offer posted to public channel**
```
Channel Post:
Swap Out Offer #42

Offering: 100.000 sats Lightning
Seeking: Bitcoin onchain  
User swaps: 0

Activate this order sending the command /take 42 to @btcp2pswapbot
```

#### **Phase 2: Deal Acceptance (Carlos)**

**Step 5: Carlos takes the offer**
```
Carlos: /take 42

Bot: 🤝 Deal #42 Started

Your role: Lightning Buyer ⚡
You get: 100.000 Lightning sats
You pay: 100.000 sats onchain

⚠️ IMPORTANT WARNINGS:
- Send EXACT amount or risk losing sats
- This operation cannot be cancelled once started
- Follow instructions carefully

You have 30 minutes to accept and send TXID ⏱️

[✅ Accept] [❌ Cancel]  (buttons)
```

**Step 6a: Carlos accepts the deal**
```
Carlos: [Clicks ✅ Accept]

Bot (Message 1): 💰 Bitcoin Deposit Required - Deal #42

Send exactly 100.000 sats to this address:

Bot (Message 2): `tb1q9xv6kf5n4q7wzvgaq0lu0y5kln6cjuy3wg0y6d`

Bot (Message 3): Next step: Report your TXID

Send 100.000 sats to the address shared above and submit the transaction ID using /txid abc1234def567890

Critical: Send the exact amount or risk losing your funds.

You have 30 minutes to send TXID.

Once the tx gets 3 confirmations you will receive a new message to send a Lightning Network invoice.
```

**Step 6b: Alternative - Carlos cancels**
```
Carlos: [Clicks ❌ Cancel]

Bot: ❌ Deal #42 Cancelled

The offer is now available again in the channel.
Others can take it with /take 42
```

#### **Phase 3: Bitcoin Deposit & Confirmation**

**Step 7: Carlos sends Bitcoin and reports TXID**
```
Carlos: /txid abc1234def567890abcdef1234567890

Bot: ⏳ TXID Received - Deal #42

Status: Waiting confirmations (0/3)
Amount: 100.000 sats

We'll notify you when confirmed.
Maximum time: 48 hours (auto-refund if not confirmed)

Next: Lightning invoice setup after confirmation.
```

**Step 8: Bot monitors confirmations (automatic)**
```
After 3 confirmations (~30 minutes), Carlos receives:

Bot: ✅ Bitcoin Confirmed - Deal #42

Your deposit: 100.000 sats confirmed!
Status: Ready for Lightning setup

Next step: Generate Lightning invoice

Create invoice for 100.000 sats in your wallet and send it here.

Reply with: /invoice [your_lightning_invoice]
Time limit: 2 hours ⏰
```

#### **Phase 4: Lightning Invoice with Privacy**

**Step 9: Carlos provides Lightning invoice**
```
Carlos: /invoice lnbc1000u1p3xnhl2pp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzq...

Bot: ⚡ Invoice Received - Deal #42

Your invoice will be optimized for privacy and sent to the counterpart.
If privacy enhancement fails, we will inform you to define the next step.

Status: Processing privacy enhancement
```

**Step 10a: Privacy enhancement succeeds**
```
Bot: ⚡ Invoice Received - Deal #42

Status: Payment request sent to seller
Your invoice: `lnbc1000u1p3xnhl2...`
Amount: 100.000 sats

The seller will pay your Lightning invoice.
Bot will verify payment and complete the swap.

Time limit: 2 hours ⏰
```

**Step 10b: Privacy enhancement fails - Decision required**
```
Bot: 🔒 Privacy Enhancement Failed - Deal #42

lnproxy service could not wrap your invoice after 3 attempts.

Your options:

🔓 Reveal Original Invoice
- Your Lightning node will be visible to the payer
- Swap proceeds immediately

⏳ Keep Trying (Recommended)
- Retry lnproxy every 20 minutes for 2 hours
- Maintains your privacy
- Auto-cancel if unsuccessful after 2 hours

Choose your preference:
[🔓 Reveal Original Invoice] [⏳ Keep Trying]  (buttons)
```

#### **Phase 5: Coordinated Settlement (Ana)**

**Step 11: Ana receives notification (only when BOTH conditions met)**
```
When Bitcoin is confirmed AND Lightning invoice is ready:

Bot: Bitcoin Confirmed - Deal #42

Bitcoin deposit confirmed: 100.000 sats
Status: Ready for final step

IMPORTANT: Provide your Bitcoin address first
After you send your address, the Lightning invoice will be revealed to complete the swap.

Send: /address [your_bitcoin_address]
Time limit: 48 hours

Your funds are secured and this step ensures smooth completion.
```

**Step 12: Ana provides Bitcoin address**
```
Ana: /address tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4

Bot (Message 1): ✅ Bitcoin Address Saved - Deal #42

Address: `tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4`
Amount: 100.000 sats

Now please pay the Lightning invoice below:

Bot (Message 2): ⚡ Lightning Payment Required

Pay this invoice to complete your swap:

`lnbc1000u1p3xnhl2pp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzq...`

Amount: 100.000 sats
Time limit: 2 hours

After payment verification, your Bitcoin will be sent in the next batch.
```

#### **Phase 6: Completion**

**Step 13: Ana pays Lightning invoice (manual)**

**Step 14: Bot verifies payment and notifies both users**
```
Carlos receives:
Bot: ✅ Deal Completed - #42

Lightning payment of 100.000 sats confirmed!
Your swap out is complete.

Thanks for using P2P Swap Bot!

---

Ana receives:
Bot: ✅ Payment Verified - Deal #42

Lightning payment received and verified!
Your 100.000 sats Bitcoin will be sent in the next batch.

Your funds are secured and will be sent shortly.
```

**Step 15: Bitcoin batch processing (automatic)**
```
When batch criteria met (3+ deals or 60 minutes):

Ana receives:
Bot: 💰 Bitcoin Sent - Deal #42

Your 100.000 sats have been sent!

Transaction: batch_100000_3_1699564800
Address: tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4

Check testnet blockchain explorer.
Swap completed successfully! ✅

Thanks for using P2P Swap Bot!
```

## 🚨 Timeout Scenarios

### TXID Timeout (30 minutes)
If Carlos doesn't send TXID within 30 minutes:
```
Carlos: ❌ Deal #42 Cancelled
Timeout: TXID timeout
The offer is available again in the channel.

Ana: 🔄 Deal #42 Cancelled
Reason: TXID timeout
Your offer is active again in @btcp2pswapoffers
```

### Bitcoin Confirmation Timeout (48 hours)
If Bitcoin doesn't get 3 confirmations within 48 hours:
```
Carlos: ⏰ Deal #42 Expired
Bitcoin confirmations not received within 48 hours.
Your funds will return to your wallet automatically.
TXID: `abc1234def567890`

Ana: ⏰ Deal #42 Expired
Bitcoin confirmations timeout (48h).
Deal cancelled, your offer remains expired.
```

### Lightning Invoice Timeout (2 hours)
If Carlos doesn't provide invoice after Bitcoin confirmation:
```
Both users: ❌ Deal #42 Cancelled
Timeout: Lightning invoice timeout
Deal terminated due to inactivity.
```

### Lightning Payment Timeout (2 hours)
If Ana doesn't pay the Lightning invoice:
```
Both users: ❌ Deal #42 Cancelled
Timeout: Lightning payment timeout
Deal terminated due to inactivity.
```

### Privacy Retry Timeout (2 hours)
If lnproxy fails for 2 hours when Carlos chose to keep trying:
```
Carlos: Deal #42 has expired after 2 hours.
Your Bitcoin will be returned to the original sending address minus network fees.
Refund will be processed in the next batch.
```

## 🏗️ Technical Architecture

### Core Components

```
src/
├── bot.py                 # Main bot logic (2000+ lines)
├── database/
│   └── models.py         # SQLAlchemy models (User, Offer, Deal)
├── bitcoin_utils.py      # Bitcoin operations & confirmation monitoring
├── lightning_utils.py    # LND integration for payment verification
└── lnproxy_utils.py     # Privacy enhancement for Lightning invoices
```

### Background Monitoring Threads

1. **Confirmation Monitor** (`monitor_confirmations`)
   - Checks Bitcoin confirmations every 10 minutes
   - Auto-advances deals when 3 confirmations reached

2. **Lightning Payment Monitor** (`monitor_lightning_payments`)
   - Verifies Lightning payments every 30 seconds
   - Adds completed deals to Bitcoin batch queue

3. **Timeout Monitor** (`monitor_expired_timeouts`)
   - Checks for expired deals every 5 minutes
   - Cancels and reactivates offers as needed

4. **lnproxy Retry Monitor** (`monitor_lnproxy_retries`)
   - Retries privacy wrapping every 20 minutes
   - Maximum 2-hour retry window

5. **Batch Processor** (`process_bitcoin_batches`)
   - Processes Bitcoin payouts hourly
   - Triggers on 3+ deals or 60-minute timeout

### Database Schema

**User Table**
- telegram_id, username, first_name
- bitcoin_address (preferred)
- reputation_score (5.0 default)
- total_deals, total_volume

**Offer Table**
- offer_type (swapout/swapin)
- amount_sats, status
- expires_at (48 hours)

**Deal Table**
- seller_id, buyer_id, amount_sats
- status (16 different states)
- current_stage, stage_expires_at
- bitcoin_confirmations, lightning_invoice
- seller_bitcoin_address, payment_hash

### Timeout Configuration

```python
OFFER_VISIBILITY_HOURS = 48      # Offers in channel
TXID_TIMEOUT_MINUTES = 30        # Send TXID after accepting
BITCOIN_CONFIRMATION_HOURS = 48  # Max for 3 confirmations
LIGHTNING_INVOICE_HOURS = 2      # Send invoice after BTC confirmed
LIGHTNING_PAYMENT_HOURS = 2      # Pay Lightning invoice
CONFIRMATION_COUNT = 3            # Required confirmations
BATCH_WAIT_MINUTES = 60          # Max wait for batch
```

## 🔧 Configuration & Setup

### Prerequisites
- Python 3.9+
- Telegram Bot Token (from @BotFather)
- Public Telegram Channel
- Bitcoin Testnet addresses (5 tiers)

### Environment Variables (.env)
```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
OFFERS_CHANNEL_ID=-1001234567890

# Bitcoin Network
BITCOIN_NETWORK=testnet
DATABASE_URL=sqlite:///p2pswap.db

# Escrow Addresses (generated via scripts/generate_addresses.py)
BITCOIN_ADDRESS_10K=tb1q...
BITCOIN_ADDRESS_100K=tb1q...
```

### Quick Start
```bash
# Clone repository
git clone https://github.com/yourusername/p2pswapbot.git
cd p2pswapbot

# Setup environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your values

# Generate Bitcoin addresses
python scripts/generate_addresses.py
# SAVE THE 12-WORD SEED SECURELY!

# Run bot
python src/bot.py
```

## 📊 Commands Reference

### User Commands
- `/start` - Register and activate bot
- `/swapout` - Create Lightning → Bitcoin offer
- `/swapin` - Create Bitcoin → Lightning offer (pending)
- `/offers` - View your active offers
- `/deals` - View your active swaps
- `/profile` - View stats and reputation
- `/take [ID]` - Accept an offer from channel
- `/help` - Get help information

### Transaction Commands
- `/txid [transaction_id]` - Report Bitcoin transaction
- `/invoice [lightning_invoice]` - Provide Lightning invoice
- `/address [bitcoin_address]` - Provide Bitcoin address
- `/reveal [deal_id]` - Reveal original invoice (privacy override)

## 🔒 Security Features

### Implemented
- **Non-custodial**: Bot never holds funds
- **Fixed addresses**: Pre-generated per amount tier
- **Exact amount matching**: Prevents loss from incorrect amounts
- **Timeout protection**: Automatic cancellation and refunds
- **Privacy by default**: lnproxy integration with fallback options

### Pending
- Multi-signature escrow (2-of-3)
- Dispute resolution with arbitrator
- Rate limiting and DDoS protection
- Encrypted communication channels

## 🚀 Roadmap

### Phase 1 ✅ 
- [x] Complete swap-out flow
- [x] Timeout management
- [x] Privacy integration
- [x] Batch processing logic
- [x] Channel integration

### Phase 2 🚧 
- [ ] Bitcoin batch sending
- [ ] LND node integration
- [ ] Swap-in implementation
- [ ] Basic dispute handling
- [ ] Testnet beta launch

### Phase 3 📅 
- [ ] Mainnet deployment
- [ ] Advanced reputation system
- [ ] Fee optimization

## ⚠️ Important Notes

### Current Limitations
- **TESTNET ONLY** - Do not use with real Bitcoin
- Lightning payment verification uses placeholder (awaiting LND)
- Bitcoin batch sending is simulated (awaiting wallet integration)
- Only swap-out flow is implemented
- Limited to 10k and 100k sat amounts for testing

### Known Issues
- lnproxy service can be unreliable (fallback implemented)
- Confirmation monitoring depends on external APIs
- Database uses SQLite (PostgreSQL recommended for production)

### Development Setup
```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Code formatting
black src/
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Live Bot**: [@btcp2pswapbot](https://t.me/btcp2pswapbot)
- **Offers Channel**: [@btcp2pswapoffers](https://t.me/btcp2pswapoffers)
- **GitHub**: [github.com/yourusername/p2pswapbot](https://github.com/yourusername/p2pswapbot)
- **Support**: [GitHub Issues](https://github.com/yourusername/p2pswapbot/issues)

---

**Disclaimer**: This is experimental software in active development. Use at your own risk. Currently for testing purposes only on Bitcoin testnet.
