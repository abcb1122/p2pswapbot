# P2P Swap Bot - Setup Guide

Complete setup guide for running the P2P Bitcoin Swap Bot on testnet.

## Prerequisites

- Python 3.9+
- Git
- Telegram account
- Basic Bitcoin/Lightning knowledge

## Step 1: Clone Repository

```bash
git clone https://github.com/abcb1122/p2pswapbot.git
cd p2pswapbot
```

## Step 2: Setup Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Telegram Bot Setup

### 3.1 Create Bot
1. Message [@BotFather](https://t.me/botfather)
2. Send `/newbot`
3. Choose name: `Your P2P Swap Bot`
4. Choose username: `@yourp2pswapbot`
5. Copy the token

### 3.2 Create Channel
1. Create public channel: `@yourswapoffers`
2. Add your bot as admin
3. Give bot permission to post messages
4. Get channel ID using [@userinfobot](https://t.me/userinfobot)

## Step 4: Bitcoin Testnet Setup

### 4.1 Generate Escrow Addresses

Run the mnemonic-based address generator:
```bash
python scripts/generate_addresses.py
```

**CRITICAL: This will generate a 12-word mnemonic seed phrase**

The script will output:
- 12-word mnemonic seed (BACKUP SECURELY)
- 5 derived testnet addresses (tb1... format)
- BIP84 derivation paths
- Security warnings and backup checklist

**Security Requirements:**
- Write down the 12 words immediately
- Store in multiple secure offline locations
- Never take photos or screenshots
- Test recovery with small amounts first
- The seed phrase controls ALL addresses

**Example output:**
```
🔐 MNEMONIC SEED - BACKUP THESE 12 WORDS:
word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12

📍 DERIVED ADDRESSES (BIP84 - Native SegWit):
10,000 sats: tb1q...
50,000 sats: tb1q...
100,000 sats: tb1q...
500,000 sats: tb1q...
1,000,000 sats: tb1q...
```

**Recovery Information:**
- Standard: BIP84 (Native SegWit)
- Derivation: m/84'/1'/0'/0/x
- Network: testnet
- Format: bech32 (tb1...)

### 4.2 Important: Seed Phrase Management

**Key Points:**
- Each time you run the generator script, it creates a COMPLETELY NEW seed phrase
- New seed = new addresses = previous addresses become inaccessible through the bot
- Your previous seed phrase still controls its respective addresses (for manual recovery)

**When to regenerate:**
- First time setup
- Lost your seed phrase
- Want to start fresh with new addresses

**When NOT to regenerate:**
- Bot is already working with existing addresses
- You have funds in current addresses
- You're just restarting the bot

**Safe Practice:**
- Backup each seed phrase with a date/version label
- Test new addresses with small amounts first
- Keep record of which seed controls which addresses

## Step 5: Environment Configuration

```bash
# Copy template
cp .env.example .env

# Edit configuration
nano .env
```

### Required Configuration:

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
OFFERS_CHANNEL_ID=-1001234567890

# Bitcoin Network
BITCOIN_NETWORK=testnet

# Database
DATABASE_URL=sqlite:///p2pswap.db

# Escrow Addresses (from Step 4)
BITCOIN_ADDRESS_10K=tb1q...your_testnet_address
BITCOIN_ADDRESS_50K=tb1q...your_testnet_address  
BITCOIN_ADDRESS_100K=tb1q...your_testnet_address
BITCOIN_ADDRESS_500K=tb1q...your_testnet_address
BITCOIN_ADDRESS_1M=tb1q...your_testnet_address

# Private Keys (KEEP SECURE!)
BITCOIN_ADDRESS_10K_PRIVATE=your_private_key_hex
BITCOIN_ADDRESS_50K_PRIVATE=your_private_key_hex
BITCOIN_ADDRESS_100K_PRIVATE=your_private_key_hex
BITCOIN_ADDRESS_500K_PRIVATE=your_private_key_hex
BITCOIN_ADDRESS_1M_PRIVATE=your_private_key_hex
```

## Step 6: Database Setup

```bash
# Initialize database (automatic on first run)
python src/bot.py
```

## Step 7: Testing

### 7.1 Start Bot
```bash
python src/bot.py
```

### 7.2 Test Commands
1. Message your bot: `/start`
2. Create offer: `/swapout`
3. Check channel for posted offers
4. Test other commands: `/swapin`, `/offers`, `/profile`

### 7.3 Test Bitcoin Flow
1. Create small offer (10k sats)
2. Note the deposit address
3. Send testnet coins to address
4. Verify bot detects payment

## Step 8: Production Deployment

### For 24/7 Operation

**VPS Deployment:**
```bash
# On Ubuntu/Debian server
sudo apt update
sudo apt install python3 python3-pip git

# Clone and setup (same as above)
git clone https://github.com/abcb1122/p2pswapbot.git
cd p2pswapbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure .env file
cp .env.example .env
nano .env

# Run as systemd service
sudo cp scripts/p2pswapbot.service /etc/systemd/system/
sudo systemctl enable p2pswapbot
sudo systemctl start p2pswapbot
```

**Docker Deployment:**
```bash
# Configure .env
cp .env.example .env
nano .env

# Start with Docker
docker-compose up -d

# View logs
docker-compose logs -f
```

## Security Considerations

### Critical Security Steps:

1. **Private Key Security**
   - Store private keys securely
   - Never commit private keys to git
   - Use environment variables only
   - Backup keys securely

2. **Testnet Only**
   - This setup is for testnet only
   - Never use testnet keys on mainnet
   - Clearly label all wallets as testnet

3. **Access Control**
   - Limit server access
   - Use SSH keys
   - Regular security updates
   - Monitor bot activity

## Troubleshooting

### Common Issues:

**Bot not starting:**
- Check token in .env
- Verify Python dependencies
- Check logs for errors

**Addresses showing placeholder:**
- Verify .env has real addresses
- Check environment variable names
- Restart bot after .env changes

**Channel not working:**
- Verify bot is admin
- Check channel ID format
- Test with private messages first

**Bitcoin addresses not working:**
- Confirm addresses are testnet format (start with 'tb1' or 'mxxx')
- Verify private keys match addresses
- Test with small amounts first

## Troubleshooting

### Installation Issues

**Error: "Could not find a version that satisfies the requirement bitcoinlib==0.12.0"**
```bash
# Solution: Use the correct version
pip install bitcoinlib==0.7.5
```

**Error: "pip version is outdated" warnings**
```bash
# Update pip first
pip install --upgrade pip
# Then install requirements
pip install -r requirements.txt
```

**Error: "AttributeError: module 'bitcoinlib.keys' has no attribute 'PrivateKey'"**
- This indicates an outdated script version
- Make sure you have the latest version from GitHub
- The script should use `Key()` not `PrivateKey()`

### Address Generation Issues

**Script crashes during address generation:**
```bash
# Verify bitcoinlib is installed correctly
pip list | grep bitcoinlib
# Should show: bitcoinlib 0.7.5

# Test basic functionality
python3 -c "from bitcoinlib.keys import Key; print('OK')"
```

### Bot Runtime Issues

**Bot shows placeholder addresses:**
- Verify .env file has real addresses, not placeholders
- Check that environment variable names match exactly
- Restart bot after making .env changes

**"Authentication failed" when pushing to GitHub:**
- Use Personal Access Token instead of password
- Get token from GitHub Settings → Developer settings → Personal access tokens

### Common Issues:

**Bot not starting:**
- Check token in .env
- Verify Python dependencies
- Check logs for errors

**Addresses showing placeholder:**
- Verify .env has real addresses
- Check environment variable names
- Restart bot after .env changes

**Channel not working:**
- Verify bot is admin
- Check channel ID format
- Test with private messages first

**Bitcoin addresses not working:**
- Confirm addresses are testnet format (start with 'tb1' or 'mxxx')
- Verify private keys match addresses
- Test with small amounts first

## Support

- **Documentation**: Check README.md
- **Issues**: [GitHub Issues](https://github.com/abcb1122/p2pswapbot/issues)
- **Telegram**: @abcb1122

## Next Steps

1. Test thoroughly on testnet
2. Document any issues
3. Prepare for mainnet deployment
4. Set up monitoring and alerts
5. Plan for scaling and security audits
