# User Stories - P2P Bitcoin Swap Bot

## Epic: Core Trading Functionality

### As a Lightning User wanting Bitcoin onchain

**Story 1: Create Swap Out Offer**
```
As a Lightning Network user with sats in channels
I want to create an offer to sell my Lightning sats for Bitcoin onchain
So that I can get onchain liquidity without using centralized services

Acceptance Criteria:
- I can select standard amounts (10k, 50k, 100k, 500k, 1M sats)
- My offer gets posted to the public channel automatically
- I receive confirmation with offer ID
- Other users can see and take my offer
```

**Story 2: Take Swap In Offer**
```
As a Bitcoin holder wanting Lightning liquidity
I want to take someone's swap in offer
So that I can get Lightning sats by paying Bitcoin onchain

Acceptance Criteria:
- I can browse available swap in offers
- I can take an offer with /take [ID]
- A deal is created between me and the offer creator
- Both parties get notified of the match
```

## Epic: User Management

**Story 3: User Registration**
```
As a new user
I want to easily register with the bot
So that I can start trading immediately

Acceptance Criteria:
- Registration happens automatically on /start
- My Telegram info is saved securely
- I get a welcome message with instructions
- I can see my profile with /profile
```

**Story 4: Reputation System**
```
As a trader
I want to see reputation scores of other users
So that I can trade with confidence

Acceptance Criteria:
- Users start with 5.0 rating
- Completed deals improve reputation
- Reputation is visible in offers
- Dispute resolution affects scores
```

## Epic: Marketplace Discovery

**Story 5: Browse Offers**
```
As a potential trader
I want to see all available offers
So that I can find good trading opportunities

Acceptance Criteria:
- /offers shows active swap out and swap in offers
- Offers are grouped by type
- I can see amount, user, and rating
- Channel shows real-time offers
```

**Story 6: Public Channel**
```
As a trader
I want offers to be visible in a public channel
So that maximum people can see and take my offers

Acceptance Criteria:
- New offers auto-post to @btcp2pswapoffers
- Posts include offer type, amount, and take command
- Channel is read-only for non-admins
- Posts are formatted professionally
```

## Epic: Security & Escrow (Future)

**Story 7: Multisig Escrow**
```
As a trader
I want my funds to be held in secure escrow
So that I can trade safely without counterparty risk

Acceptance Criteria:
- 2-of-3 multisig address created for each deal
- Buyer deposits Bitcoin to escrow
- Seller provides Lightning invoice
- Automatic release on successful payment
```

**Story 8: Dispute Resolution**
```
As a trader experiencing issues
I want a way to resolve disputes
So that my funds are not permanently locked

Acceptance Criteria:
- Either party can open dispute
- Bot acts as arbitrator with third key
- Evidence can be submitted
- Resolution affects reputation scores
```

## Epic: User Experience

**Story 9: Guided Workflows**
```
As a user
I want clear step-by-step guidance
So that I know exactly what to do at each stage

Acceptance Criteria:
- Clear messages after each action
- Next steps are always indicated
- Timeouts and deadlines are communicated
- Help is available at any stage
```

**Story 10: Mobile-Friendly Interface**
```
As a mobile user
I want an interface that works well on phone
So that I can trade on the go

Acceptance Criteria:
- Buttons instead of typing commands
- Short, clear messages
- Emojis for visual clarity
- Quick actions available
```

## Technical Stories

**Story 11: Database Persistence**
```
As the system
I need to persist all user and offer data
So that the bot can restart without losing state

Acceptance Criteria:
- SQLite for development, PostgreSQL for production
- All models properly indexed
- Migration system for schema changes
- Backup and recovery procedures
```

**Story 12: Error Handling**
```
As the system
I need robust error handling
So that users get helpful messages instead of crashes

Acceptance Criteria:
- All exceptions are caught and logged
- Users get friendly error messages
- System can recover from API failures
- Monitoring and alerting in place
```

## Success Metrics

- **Adoption**: 100+ registered users in first month
- **Activity**: 10+ successful swaps per week
- **Reliability**: 99% uptime, <5% failed transactions
- **Security**: Zero lost funds, no major exploits
- **Growth**: 20% month-over-month user growth
