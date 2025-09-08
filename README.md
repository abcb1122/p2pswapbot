# P2P Bitcoin Swap Bot 🔄

A Telegram bot for peer-to-peer Lightning Network ⚡ and Bitcoin onchain swaps without custody.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Telegram](https://img.shields.io/badge/Telegram-@btcp2pswapbot-blue.svg)](https://t.me/btcp2pswapbot)

## ✨ Features

- **Swap Out**: Lightning → Bitcoin onchain
- **Swap In**: Bitcoin onchain → Lightning  
- **Non-custodial**: Bot never holds your funds
- **P2P Matching**: Direct user-to-user trades
- **Public Channel**: Transparent offer marketplace
- **Standard Amounts**: 10k, 50k, 100k, 500k, 1M sats
- **Reputation System**: User ratings and deal history

## 🚀 Quick Start

## 📋 Complete Setup Guide

For detailed setup instructions, see [SETUP.md](SETUP.md)

This guide covers:
- Telegram bot configuration
- Bitcoin testnet setup
- Environment variables
- Testing and troubleshooting

### Prerequisites

- Python 3.9+
- Telegram account
- Basic knowledge of Bitcoin/Lightning

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/p2pswapbot.git
   cd p2pswapbot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the bot**
   ```bash
   python src/bot.py
   ```

## 🔧 Configuration

### Getting Bot Token

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Create new bot: `/newbot`
3. Follow instructions and get your token
4. Add token to `.env` file

### Setting Up Channel

1. Create public Telegram channel
2. Add your bot as admin
3. Get channel ID and add to `.env`

### Environment Variables

See `.env.example` for all configuration options.

## 📖 How It Works

### For Users

1. **Start**: `/start` to register
2. **Create Offers**: 
   - `/swapout` - Sell Lightning for Bitcoin
   - `/swapin` - Buy Lightning with Bitcoin
3. **Browse**: `/offers` to see available trades
4. **Trade**: `/take [ID]` to accept an offer

### Technical Flow

1. **Offer Creation**: User creates swap offer
2. **Public Listing**: Offer posted to channel
3. **Matching**: Another user takes the offer
4. **Escrow**: Multisig address created (planned)
5. **Settlement**: Atomic swap execution (planned)

## 🏗️ Development

### Current Status: TESTNET ONLY

This bot is currently running on Bitcoin testnet for development and testing.

### Architecture

- **Backend**: Python + SQLAlchemy
- **Database**: SQLite (local) / PostgreSQL (production)
- **Bot Framework**: python-telegram-bot
- **Network**: Bitcoin testnet

### Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## 🛣️ Roadmap

### Phase 1 (Current)
- [x] Basic bot functionality
- [x] Offer creation and matching
- [x] Public channel integration
- [ ] Post-match workflow
- [ ] Address/invoice validation

### Phase 2
- [ ] Multisig escrow system
- [ ] Automatic settlement
- [ ] Dispute resolution
- [ ] Enhanced security

### Phase 3
- [ ] Mainnet deployment
- [ ] Advanced privacy features
- [ ] Mobile app integration
- [ ] Lightning node integration

## ⚠️ Security Notice

**TESTNET ONLY**: This bot is currently for testing purposes only. Do not use with real Bitcoin on mainnet until security audits are complete.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

- **Telegram**: [@btcp2pswapbot](https://t.me/btcp2pswapbot)
- **Channel**: [@btcp2pswapoffers](https://t.me/btcp2pswapoffers)
- **Issues**: [GitHub Issues](https://github.com/yourusername/p2pswapbot/issues)

## ⚡ Live Bot

Try the bot: [@btcp2pswapbot](https://t.me/btcp2pswapbot)

**Commands:**
- `/start` - Register and get started
- `/swapout` - Lightning → Bitcoin
- `/swapin` - Bitcoin → Lightning
- `/offers` - View marketplace
- `/help` - Get help

---

**Disclaimer**: This is experimental software. Use at your own risk.
