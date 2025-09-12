# P2P Bitcoin Swap Bot - Service Flow Specification Bible

**Version:** 1.0  
**Date:** 2025-09-12  
**Status:** Immutable Development Reference  
**Purpose:** Definitive specification for all P2P Swap Bot development

---

## Bitcoin Batch Processing System

### Hourly Schedule
- **Processing Times:** Every hour at :00 minutes (11:00, 12:00, 13:00, etc.)
- **Request Cutoff:** 10 minutes before processing (:50 minutes)
- **Queue Reset:** New requests accepted starting :01 minutes for next batch

### Example Timeline
```
13:45 - Deal completes, enters queue for 14:00 batch
13:50 - Cutoff: No new deals accepted for 14:00 batch
14:00 - Batch processing starts, Bitcoin transactions sent
14:01 - New deals can enter queue for 15:00 batch
```

### Rules
1. **Fixed Schedule:** No early processing, always wait for hourly schedule
2. **Buffer Time:** 10-minute buffer prevents processing conflicts
3. **Guaranteed Processing:** Any deal in queue will be processed at next scheduled time
4. **Queue Management:** Clear separation between batch cycles

---

## Offer Lifecycle Management

### Initial Publication
- Offer created with 48-hour timer started
- Timer runs continuously, never resets

### During Deal Attempt
- Offer hidden from channel when `/take` executed
- Original 48-hour timer continues running in background
- Deal attempt has independent 30-minute timeout

### Reactivation Rules
- **If deal cancelled/timeout:** Offer returns to channel
- **Remaining Time:** Only time left from original 48-hour timer
- **No Timer Reset:** Timer never restarts, only counts down

### Example Scenario
```
Day 1, 10:00 - Offer created (expires Day 3, 10:00)
Day 2, 15:00 - Carlos takes offer, hidden from channel (21 hours remaining)
Day 2, 15:15 - Carlos cancels, offer reappears with 20:45 remaining
Day 3, 10:00 - Offer expires and removed permanently
```

---

## Overview

This document defines the complete service flow for the P2P Bitcoin Swap Bot. Any implementation, modification, or debugging must strictly follow this specification. This serves as the immutable bible for the project.

---

## Complete Service Flow - 16 Steps

### Phase 1: Offer Creation (Ana - Seller)

**Step 1: User Registration**
- Trigger: `/start` command
- Action: User registered, welcome message displayed
- Timeout: None
- Next State: User active

**Step 2: Swap Offer Creation** 
- Trigger: `/swapout` command + amount selection
- Action: Offer created with 48-hour visibility
- Timeout: 48 hours offer visibility in channel
- Next State: Offer active and published

**Step 3: Channel Publication**
- Trigger: Automatic after offer creation
- Action: Offer published to public channel without revealing username
- Format: "Swap Out Offer #ID - Offering: X sats Lightning - Seeking: Bitcoin onchain"

### Phase 2: Deal Initiation (Carlos - Buyer)

**Step 4: Order Activation**
- Trigger: `/take [offer_id]` command
- Action: Deal created, warnings displayed with Accept/Cancel buttons
- Timeout: 30 minutes to accept
- Next State: Deal pending

**Step 5: Deal Acceptance**
- Trigger: Accept button pressed
- Action: Fixed Bitcoin address revealed + TXID submission instructions
- Timeout: 30 minutes to submit TXID
- Next State: Deal accepted
- Critical: Address is fixed per tier (10k sats → ADDRESS_10K, 100k sats → ADDRESS_100K)

### Phase 3: Bitcoin Deposit (Carlos - Buyer)

**Step 6: Bitcoin Transaction**
- Trigger: Manual Bitcoin transaction by Carlos
- Action: Carlos sends exact amount to fixed address
- Validation: External blockchain transaction
- Next State: Awaiting TXID submission

**Step 7: TXID Submission**
- Trigger: `/txid [transaction_hash]` command  
- Action: TXID recorded, verification initiated
- Timeout: 48 hours for confirmations
- Next State: Bitcoin sent
- **Critical Validation:**
  - Verify transaction sends to exact fixed address
  - Verify exact satoshi amount matches deal
  - Validate transaction format and network

### Phase 4: Bitcoin Confirmation (Automated)

**Step 8: Confirmation Monitoring**
- Trigger: Automatic every 10 minutes
- Action: Monitor blockchain confirmations
- Required: 3 confirmations minimum
- Timeout: 48 hours maximum
- **Robust Verification:**
  - Confirm transaction is in our fixed address
  - Verify amount is exactly what was specified
  - Check confirmation depth on blockchain

**Step 9: Confirmation Complete**
- Trigger: 3 confirmations reached
- Action: Request Lightning invoice from Carlos
- Timeout: 2 hours to provide Lightning invoice
- Next State: Bitcoin confirmed

### Phase 5: Lightning Invoice (Carlos - Buyer)

**Step 10: Invoice Submission**
- Trigger: `/invoice [lightning_invoice]` command
- Action: lnproxy privacy optimization attempted
- Process: 5 minutes automatic optimization attempt
- Next State: Invoice processing

**Step 11: Privacy Processing**
- **If lnproxy succeeds:**
  - Invoice wrapped for privacy
  - Carlos notified: "Invoice processed, wait for sound of money"
  - Next State: Invoice ready
- **If lnproxy fails:**
  - User choice: Continue trying (2h max) or reveal original
  - Retry every 20 minutes for maximum 2 hours
  - User can reveal with `/reveal [deal_id]` command

### Phase 6: Critical Coordination (Ana - Seller)

**Step 12: Conditions Check**
- Trigger: Automatic when both conditions met:
  1. Bitcoin confirmed (3+ confirmations)
  2. Lightning invoice available (processed or revealed)
- Action: Request Bitcoin address from Ana
- **Critical Rule: Ana NEVER sees Lightning invoice before providing her address**
- Timeout: 2 hours to provide address
- Next State: Awaiting Bitcoin address

**Step 13: Address Collection**
- Trigger: `/address [bitcoin_address]` command from Ana
- Action: Address validated and stored
- **Address Requirements:**
  - Valid Bitcoin testnet format (tb1... or legacy)
  - Properly formatted bech32 or P2SH
- Next State: Address provided

### Phase 7: Lightning Payment (Ana - Seller)

**Step 14: Invoice Revelation**
- Trigger: Automatic after Ana provides address
- Action: Lightning invoice revealed to Ana for payment
- Message: "Pay this invoice to complete swap - wait for sound of money"
- Timeout: 2 hours to complete payment

**Step 15: Lightning Payment Verification**
- Trigger: Ana pays Lightning invoice manually
- **Verification Method: Integrated Neutrino Node**
  - Real Lightning payment verification (not placeholder)
  - Cross-reference payment hash with invoice
  - Confirm payment settlement on Lightning Network
- Action: Carlos notified "Payment identified - deal successful!" and Ana notified "Payment verified - your Bitcoin will be included in the next batch"
- Next State: Ready for batch

### Phase 8: Bitcoin Settlement (Automated)

**Step 16: Batch Processing**
- Trigger: Either condition met:
  - 3+ deals ready for batch, OR
  - 60 minutes maximum wait time
- Action: Bitcoin sent to Ana's provided address
- Verification: Real Bitcoin transaction executed
- Final State: Deal completed
- Notifications: Both users informed of successful completion

---

## State Transitions

```
pending → accepted → bitcoin_sent → bitcoin_confirmed → 
lightning_invoice_received → awaiting_bitcoin_address → 
address_provided_awaiting_payment → ready_for_batch → completed
```

**Error States:**
- cancelled (user cancellation or timeout)
- expired (exceeded maximum timeouts)
- disputed (future implementation)

---

## Timeout Rules

| Phase | State | Timeout | Auto-Action |
|-------|-------|---------|-------------|
| Deal Initiation | pending | 30 minutes | Cancel + reactivate offer |
| TXID Submission | accepted | 30 minutes | Cancel + reactivate offer |
| Bitcoin Confirmation | bitcoin_sent | 48 hours | Cancel + refund notice |
| Lightning Invoice | bitcoin_confirmed | 2 hours | Cancel deal |
| Bitcoin Address | awaiting_bitcoin_address | 2 hours | Cancel deal |
| Lightning Payment | address_provided_awaiting_payment | 2 hours | Cancel deal |
| Batch Processing | ready_for_batch | 60 minutes | Process batch |

---

## Critical Validation Requirements

### TXID Verification (Robust Implementation Required)
```python
def verify_txid_robust(txid, expected_address, expected_amount):
    """
    CRITICAL: This function MUST verify:
    1. Transaction sends to our exact fixed address
    2. Amount matches deal specification exactly  
    3. Transaction is valid on Bitcoin testnet
    4. Minimum of 3 confirmations before proceeding
    """
    pass  # Implementation required
```

### Lightning Payment Verification (Real Implementation Required)
```python
def verify_lightning_payment_real(payment_hash):
    """
    CRITICAL: This function MUST use real neutrino node:
    1. Connect to actual Lightning Network
    2. Verify payment_hash is settled
    3. Confirm invoice was paid in full
    4. Return True only for confirmed payments
    """
    pass  # Implementation required
```

### Bitcoin Batch Sending (Real Implementation Required)
```python
def send_bitcoin_batch(deals_list):
    """
    CRITICAL: This function MUST send real Bitcoin:
    1. Create actual Bitcoin transactions
    2. Send to users' provided addresses
    3. Use proper fee calculation
    4. Return actual transaction IDs
    """
    pass  # Implementation required
```

---

## Fixed Address Configuration

**Address Tiers (Testnet):**
```
10,000 sats  → BITCOIN_ADDRESS_10K  (environment variable)
100,000 sats → BITCOIN_ADDRESS_100K (environment variable)
```

**Security Requirements:**
- Addresses must be pre-generated from secure mnemonic
- Private keys stored securely and never exposed in code
- Each tier has dedicated address to prevent amount confusion

---

## Privacy and Security Rules

### Rule 1: Coordination Critical Path
- Ana NEVER sees Lightning invoice before providing Bitcoin address
- Both conditions must be met before requesting address:
  1. Bitcoin confirmed (3+ confirmations)
  2. Lightning invoice ready (lnproxy processed or revealed)

### Rule 2: lnproxy Privacy Integration
- Always attempt lnproxy first for invoice privacy
- Provide user choice if lnproxy fails
- Retry mechanism: every 20 minutes for maximum 2 hours
- User can override with `/reveal` command

### Rule 3: Exact Amount Matching
- Bitcoin deposits must match exact satoshi amounts
- Lightning invoices must match exact satoshi amounts  
- Any discrepancy results in deal cancellation

### Rule 4: Real Verification Required
- No placeholder implementations in production
- TXID verification must check actual blockchain
- Lightning verification must use real neutrino node
- Bitcoin sending must use real wallet operations

---

## Error Handling

### Timeout Scenarios
- Automatic cancellation with appropriate notifications
- **Offer reactivation:** When deal is cancelled or times out, offer returns to `active` state and reappears in public channel
- Graceful degradation and user communication

### Validation Failures
- Clear error messages to users
- Logging for debugging and dispute resolution
- Secure handling of sensitive information

### Network Failures
- Retry mechanisms for blockchain interactions
- Fallback procedures for API failures
- Graceful handling of Lightning Network issues

---

## Implementation Compliance

### Development Requirements
Any code changes must:
1. Follow this exact 16-step flow
2. Implement robust validation functions
3. Use real blockchain/Lightning operations (no placeholders)
4. Maintain all timeout rules precisely
5. Preserve privacy and security rules

### Testing Requirements
1. Test complete flow end-to-end
2. Validate all timeout scenarios
3. Verify real blockchain interactions
4. Test privacy features (lnproxy integration)
5. Confirm batch processing works correctly

### Deployment Requirements
1. Environment variables properly configured
2. Real Bitcoin addresses generated and secured
3. Neutrino node operational and connected
4. lnproxy integration functional
5. All monitoring systems active

---

## Future Enhancements

While maintaining this core flow, future versions may add:
- Additional amount tiers
- Enhanced dispute resolution
- Advanced privacy features
- Multi-signature escrow options
- Extended cryptocurrency support

Any enhancements must preserve the fundamental 16-step flow and security principles defined in this specification.

---

**END OF SPECIFICATION**

*This document serves as the immutable reference for P2P Bitcoin Swap Bot development. All implementations must comply with this specification exactly.*
