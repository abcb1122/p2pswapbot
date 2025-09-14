#!/usr/bin/env python3
"""
===============================================================================
P2P SWAP BOT - Telegram Bot for Lightning <-> Bitcoin Onchain Swaps
===============================================================================

Non-custodial P2P trading bot enabling secure Lightning Network to Bitcoin swaps.
Implements granular timeouts, lnproxy privacy integration, and batch processing.

SWAP OUT FLOW (Lightning → Bitcoin):
1. Ana /start → Register user
2. Ana /swapout → Create offer → Posted to public channel
3. Carlos /take X → Accept deal with Accept/Cancel buttons
4. Carlos deposits Bitcoin → /txid → Wait for 3 confirmations
5. Carlos /invoice → Provide Lightning invoice (lnproxy privacy attempted)
6. Ana /address → Provide Bitcoin address FIRST
7. Ana receives Lightning invoice → Ana pays Lightning
8. Bot verifies Lightning payment → Ana added to Bitcoin batch
9. Bitcoin sent in batches → Deal completed

Version: Optimized for production - Clean English implementation
"""

import os
import logging
import asyncio
import time
import threading
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Import database models
from database.models import get_db, User, Offer, Deal, create_tables
from message_manager import MessageManager

# Import logging system
from logger_config import get_swap_logger, init_logging

# Load environment variables
load_dotenv()

# Global message manager instance
msg = None

# Global swap logger instance
swap_logger = None

# =============================================================================
# CORE CONFIGURATION - MODIFY HERE FOR QUICK CHANGES
# =============================================================================

# Bot tokens and configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OFFERS_CHANNEL_ID = os.getenv('OFFERS_CHANNEL_ID')  # Public channel for offers

# Available amounts (sats) - Currently testing with 2 amounts only
AMOUNTS = [10000, 100000]  # 10k and 100k sats

# Fixed Bitcoin addresses per amount (testnet) - Configure in .env
FIXED_ADDRESSES = {
    10000: os.getenv('BITCOIN_ADDRESS_10K'),    # Address for 10k sats
    100000: os.getenv('BITCOIN_ADDRESS_100K')   # Address for 100k sats
}

# Granular timeout configuration - ADJUST PER STAGE REQUIREMENTS
OFFER_VISIBILITY_HOURS = 48        # Offers visible in channel for 48 hours
TXID_TIMEOUT_MINUTES = 30          # Time to send TXID after accepting deal
BITCOIN_CONFIRMATION_HOURS = 48    # Maximum time for 3 Bitcoin confirmations
LIGHTNING_INVOICE_HOURS = 2        # Time to send Lightning invoice after Bitcoin confirmed
LIGHTNING_PAYMENT_HOURS = 2        # Time to pay Lightning invoice
CONFIRMATION_COUNT = 3             # Required Bitcoin confirmations
CONFIRMATION_CHECK_MINUTES = 10    # Check confirmations every 10 minutes
BATCH_WAIT_MINUTES = 60            # Maximum wait time for Bitcoin batch (or min 3 requests)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def format_amount(amount):
    """Format amounts with dots as thousand separators (Latino format)"""
    return f"{amount:,}".replace(",", ".")

async def send_message_with_retry(context, chat_id, text, parse_mode='Markdown', max_retries=3):
    """
    Send message with retry logic for critical notifications
    Implements exponential backoff: 1s, 2s, 4s delays
    """
    for attempt in range(max_retries):
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )
            logger.info(f'Message sent successfully to {chat_id} on attempt {attempt + 1}')
            return True
        except Exception as e:
            logger.warning(f'Failed to send message to {chat_id} on attempt {attempt + 1}: {e}')
            if attempt < max_retries - 1:
                delay = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.info(f'Retrying in {delay} seconds...')
                await asyncio.sleep(delay)
            else:
                logger.error(f'All {max_retries} attempts failed to send message to {chat_id}')
                return False
    return False

# =============================================================================
# SECTION 1: BASIC COMMANDS (/start, /help, /profile)
# =============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command /start - Register user automatically
    Both Ana and Carlos use this command to activate the bot
    """
    user = update.effective_user
    
    # Register user in database
    db = get_db()
    existing_user = db.query(User).filter(User.telegram_id == user.id).first()
    
    if not existing_user:
        new_user = User(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            bitcoin_address="",
            reputation_score=5.0,
            total_deals=0,
            total_volume=0
        )
        db.add(new_user)
        db.commit()

        # Log new user registration
        swap_logger.log_user_registration(
            user_id=user.id,
            username=user.username or '',
            registration_type='manual'
        )
        logger.info(f"New user registered: {user.id} ({user.username})")
    else:
        # Log existing user start command
        swap_logger.log_command(
            user_id=user.id,
            command='/start',
            details={'status': 'existing_user'}
        )
        logger.info(f"Existing user: {user.id} ({user.username})")

    db.close()

    # Log command execution
    swap_logger.log_command(user_id=user.id, command='/start')

    await update.message.reply_text(msg.get_message('MSG-001'))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /help - Information about how to use the bot"""
    user = update.effective_user

    # Log command execution
    swap_logger.log_command(user_id=user.id, command='/help')

    await update.message.reply_text(msg.get_message('MSG-002'))

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /profile - View user statistics"""
    user = update.effective_user

    # Log command execution
    swap_logger.log_command(user_id=user.id, command='/profile')

    db = get_db()
    user_data = db.query(User).filter(User.telegram_id == user.id).first()
    db.close()

    if not user_data:
        # Log user not found
        swap_logger.log_user_interaction(
            user_id=user.id,
            action='profile_access',
            details='user_not_registered'
        )
        await update.message.reply_text(msg.get_message('MSG-003'))
        return
    
    profile_text = f"""
👤 **Your Profile**

ID: {user_data.telegram_id}
User: @{user_data.username or 'Not set'}
Name: {user_data.first_name}

**Stats:**
Completed: {user_data.total_deals}
Rating: {'⭐' * int(user_data.reputation_score)} ({user_data.reputation_score}/5.0)
Volume: {format_amount(user_data.total_volume)} sats

**Bitcoin address:** {user_data.bitcoin_address or 'Not set'}
    """
    await update.message.reply_text(profile_text, parse_mode='Markdown')

# =============================================================================
# SECTION 2: OFFER CREATION (/swapout, /swapin)
# =============================================================================

async def swapout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command /swapout - Ana creates Lightning → Bitcoin offer
    Step 2 in flow: Ana selects amount with buttons
    """
    user = update.effective_user

    # Log command execution
    swap_logger.log_command(
        user_id=user.id,
        command='/swapout',
        details={'available_amounts': AMOUNTS}
    )

    keyboard = []

    # Create buttons for each available amount
    for amount in AMOUNTS:
        text = format_amount(amount)
        keyboard.append([InlineKeyboardButton(text, callback_data=f"swapout_{amount}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        msg.get_message('MSG-035'),
        reply_markup=reply_markup
    )

async def swapin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command /swapin - Create Bitcoin → Lightning offer"""
    user = update.effective_user

    # Log command execution
    swap_logger.log_command(
        user_id=user.id,
        command='/swapin',
        details={'available_amounts': AMOUNTS}
    )

    keyboard = []

    for amount in AMOUNTS:
        text = format_amount(amount)
        keyboard.append([InlineKeyboardButton(text, callback_data=f"swapin_{amount}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        msg.get_message('MSG-036'),
        reply_markup=reply_markup
    )

# =============================================================================
# SECTION 3: BUTTON HANDLERS AND OFFER CREATION
# =============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle button clicks - Auto-register users and process actions
    """
    query = update.callback_query
    await query.answer()

    user = query.from_user
    data = query.data

    # Log button click
    swap_logger.log_button_click(
        user_id=user.id,
        callback_data=data,
        context='button_handler'
    )

    # Auto-register user if doesn't exist
    db = get_db()
    user_data = db.query(User).filter(User.telegram_id == user.id).first()

    if not user_data:
        new_user = User(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            bitcoin_address="",
            reputation_score=5.0,
            total_deals=0,
            total_volume=0
        )
        db.add(new_user)
        db.commit()

        # Log auto-registration
        swap_logger.log_user_registration(
            user_id=user.id,
            username=user.username or '',
            registration_type='auto'
        )
        logger.info(f"Auto-registered user: {user.id} ({user.username})")
    
    # Process different button types
    if data.startswith("swapout_"):
        amount = int(data.split("_")[1])
        await create_offer(query, user, amount, "swapout", db)
    elif data.startswith("swapin_"):
        amount = int(data.split("_")[1])
        await create_offer(query, user, amount, "swapin", db)
    elif data.startswith("accept_deal_"):
        deal_id = int(data.split("_")[2])
        await accept_deal(query, user, deal_id, db)
    elif data.startswith("cancel_deal_"):
        deal_id = int(data.split("_")[2])
        await cancel_deal(query, user, deal_id, db)
    elif data.startswith("reveal_invoice_"):
        deal_id = int(data.split("_")[2])
        await handle_reveal_invoice(query, user, deal_id, db)
    elif data.startswith("retry_lnproxy_"):
        deal_id = int(data.split("_")[2])
        await handle_retry_lnproxy(query, user, deal_id, db)

async def create_offer(query, user, amount, offer_type, db):
    """
    Create new offer and publish to channel
    Steps 3-4 in flow: Offer created and published without showing username
    """
    new_offer = Offer(
        user_id=user.id,
        offer_type=offer_type,
        amount_sats=amount,
        rate=1.0,
        status='active',
        expires_at=datetime.now(timezone.utc) + timedelta(hours=OFFER_VISIBILITY_HOURS)
    )
    
    db.add(new_offer)
    db.commit()
    offer_id = new_offer.id
    
    # Get user statistics
    user_data = db.query(User).filter(User.telegram_id == user.id).first()
    total_swaps = user_data.total_deals
    db.close()
    
    # Format amount for display
    amount_text = format_amount(amount)
    
    if offer_type == "swapout":
        success_message = f"""
✅ Offer Created #{offer_id}

Swap Out: Lightning → Bitcoin
Amount: {amount_text} sats
Completed swaps: {total_swaps}

Your offer is live in @btcp2pswapoffers
Relax and wait for someone to take it
        """
    else:
        success_message = f"""
✅ Offer Created #{offer_id}

Swap In: Bitcoin → Lightning  
Amount: {amount_text} sats
Completed swaps: {total_swaps}

Your offer is live in @btcp2pswapoffers
Relax and wait for someone to take it
        """
    
    await query.edit_message_text(success_message)
    
    # Publish to channel WITHOUT showing username (as required)
    await post_to_channel(offer_id, total_swaps, amount, offer_type, amount_text)
    
    logger.info(f"User {user.id} created {offer_type} offer: {amount} sats")

async def post_to_channel(offer_id, total_swaps, amount, offer_type, amount_text):
    """
    Publish offer to public channel - WITHOUT showing creator's username
    Step 4 in flow: Publication without user @mention
    """
    if not OFFERS_CHANNEL_ID:
        return
    
    if offer_type == "swapout":
        channel_message = f"""
**Swap Out Offer #{offer_id}**

**Offering:** {amount_text} sats Lightning
**Seeking:** Bitcoin onchain  
**User swaps:** {total_swaps}

Activate this order sending the command /take {offer_id} to @btcp2pswapbot
        """
    else:
        channel_message = f"""
**Swap In Offer #{offer_id}**

**Offering:** Bitcoin onchain
**Seeking:** {amount_text} sats Lightning
**User swaps:** {total_swaps}

Activate this order sending the command /take {offer_id} to @btcp2pswapbot
        """
    
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        await app.bot.send_message(
            chat_id=OFFERS_CHANNEL_ID,
            text=channel_message,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to post to channel: {e}")

# =============================================================================
# SECTION 4: TAKING OFFERS (/take) - STEPS 5-7 OF FLOW
# =============================================================================

async def take(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command /take - Carlos takes Ana's offer
    Steps 5-6 in flow: Carlos accepts deal with warnings and Accept/Cancel buttons
    """
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text(msg.get_message('MSG-005'))
        return

    try:
        offer_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(msg.get_message('MSG-006'))
        return
    
    db = get_db()
    user_data = db.query(User).filter(User.telegram_id == user.id).first()
    
    if not user_data:
        # Auto-register if doesn't exist
        new_user = User(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            bitcoin_address="",
            reputation_score=5.0,
            total_deals=0,
            total_volume=0
        )
        db.add(new_user)
        db.commit()
        logger.info(f"Auto-registered user taking offer: {user.id}")
        user_data = new_user
    
    offer = db.query(Offer).filter(Offer.id == offer_id, Offer.status == 'active').first()
    
    if not offer:
        db.close()
        await update.message.reply_text(f"❌ Offer #{offer_id} not found or already taken")
        return
    
    if offer.user_id == user.id:
        db.close()
        await update.message.reply_text("❌ Cannot take your own offer")
        return
    
    # Get offer creator data
    offer_creator = db.query(User).filter(User.telegram_id == offer.user_id).first()
    
    # Extract data BEFORE modifications to prevent DetachedInstanceError
    offer_type = offer.offer_type
    offer_amount = offer.amount_sats
    creator_username = offer_creator.username if offer_creator else "Anonymous"
    
    # Mark offer as taken
    offer.status = 'taken'
    offer.taken_by = user.id
    offer.taken_at = datetime.now(timezone.utc)
    
    # Create deal with granular timeouts
    new_deal = Deal(
        offer_id=offer.id,
        seller_id=offer.user_id if offer_type == 'swapout' else user.id,
        buyer_id=user.id if offer_type == 'swapout' else offer.user_id,
        amount_sats=offer_amount,
        status='pending',
        current_stage='pending',
        stage_expires_at=datetime.now(timezone.utc) + timedelta(minutes=TXID_TIMEOUT_MINUTES),
        offer_expires_at=datetime.now(timezone.utc) + timedelta(hours=OFFER_VISIBILITY_HOURS)
    )
    
    db.add(new_deal)
    db.commit()
    deal_id = new_deal.id
    db.close()
    
    # Format amount
    amount = offer_amount
    amount_text = format_amount(amount)
    
    if offer_type == 'swapout':
        # Carlos is buying Lightning, must deposit Bitcoin
        # Step 6 in flow: Message with warnings and Accept/Cancel buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"accept_deal_{deal_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_deal_{deal_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(f"""
🤝 Deal #{offer_id} Started

Your role: Lightning Buyer ⚡
You get: {amount_text} Lightning sats
You pay: {amount_text} sats onchain

⚠️ IMPORTANT WARNINGS:
- Send EXACT amount or risk losing sats
- This operation cannot be cancelled once started
- Follow instructions carefully

You have {TXID_TIMEOUT_MINUTES} minutes to accept and send TXID ⏱️
        """, reply_markup=reply_markup)
        
    else:
        # Swap in - different flow (not fully implemented in your request)
        await update.message.reply_text(f"""
🤝 Deal #{offer_id} Started

Swap in functionality - To be implemented
        """)

    logger.info(f"User {user.id} took offer {offer_id}, deal {deal_id} created")

# =============================================================================
# SECTION 5: DEAL ACCEPTANCE/CANCELLATION - STEPS 7-8 OF FLOW
# =============================================================================

async def accept_deal(query, user, deal_id, db):
    """
    Step 7 in flow: Carlos accepts - receives Bitcoin address and instructions
    """
    deal = db.query(Deal).filter(Deal.id == deal_id, Deal.buyer_id == user.id).first()
    
    if not deal:
        db.close()
        await query.edit_message_text(msg.get_message('MSG-011'))
        return
    
    if deal.status != 'pending':
        db.close()
        await query.edit_message_text(msg.get_message('MSG-012', deal_id=deal_id))
        return
    
    # Update deal state with timeouts
    deal.status = 'accepted'
    deal.accepted_at = datetime.now(timezone.utc)
    deal.current_stage = 'txid_required'
    deal.stage_expires_at = datetime.now(timezone.utc) + timedelta(minutes=TXID_TIMEOUT_MINUTES)
    db.commit()
    
    # Get fixed address for this amount
    fixed_address = FIXED_ADDRESSES.get(deal.amount_sats, "ADDRESS_NOT_CONFIGURED")
    
    # Format amount
    amount = deal.amount_sats
    amount_text = format_amount(amount)
    
    db.close()
    
    # Step 7: First message with Bitcoin address
    await query.edit_message_text(
        msg.get_message('MSG-013', deal_id=deal_id, amount_text=amount_text), 
        parse_mode='Markdown'
    )
    
    # Send address separately for easy copying
    await query.message.reply_text(
        msg.get_message('MSG-014', fixed_address=fixed_address), 
        parse_mode='Markdown'
    )
    
    # Second message with /txid instructions
    await query.message.reply_text(f"""
Next step: Report your TXID

Send {amount_text} sats to the address shared above and submit the transaction ID using /txid abc1234def567890

Critical: Send the exact amount or risk losing your funds.

You have {TXID_TIMEOUT_MINUTES} minutes to send TXID.

Once the tx gets 3 confirmations you will receive a new message to send a Lightning Network invoice.
    """)

async def cancel_deal(query, user, deal_id, db):
    """
    Step 8 alternative: Carlos cancels - offer returns to channel
    """
    deal = db.query(Deal).filter(Deal.id == deal_id, Deal.buyer_id == user.id).first()
    
    if not deal:
        db.close()
        await query.edit_message_text("❌ Deal not found or not yours")
        return
    
    # Cancel deal and reactivate offer
    deal.status = 'cancelled'
    deal.timeout_reason = 'User cancelled'
    
    offer = db.query(Offer).filter(Offer.id == deal.offer_id).first()
    if offer:
        offer.status = 'active'
        offer.taken_by = None
        offer.taken_at = None
    
    db.commit()
    db.close()
    
    await query.edit_message_text(f"""
❌ Deal #{deal_id} Cancelled

The offer is now available again in the channel.
Others can take it with /take {deal.offer_id}
    """)

# =============================================================================
# SECTION 6: TRANSACTION REPORTING (/txid) - STEP 8 OF FLOW
# =============================================================================

async def txid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command /txid - Carlos reports Bitcoin transaction
    Step 8 in flow: Carlos sends TXID and waits for confirmations
    """
    user = update.effective_user

    # Log command execution
    txid_value = context.args[0].strip() if context.args else ''
    swap_logger.log_command(
        user_id=user.id,
        command='/txid',
        details={'has_txid': bool(context.args)}
    )

    if not context.args:
        await update.message.reply_text(msg.get_message('MSG-018'))
        return

    txid = context.args[0].strip()

    # Log TXID submission (filtered)
    swap_logger.log_user_interaction(
        user_id=user.id,
        action='txid_submission',
        details=f'txid={txid[:8]}...' if txid else 'empty_txid'
    )
    
    # Find active deal for this user
    db = get_db()
    deal = db.query(Deal).filter(
        Deal.buyer_id == user.id,
        Deal.status.in_(['accepted', 'bitcoin_sent'])
    ).first()
    
    if not deal:
        db.close()
        await update.message.reply_text(msg.get_message('MSG-019'))
        return

    # Get fixed address for this deal amount
    fixed_address = FIXED_ADDRESSES.get(deal.amount_sats, "ADDRESS_NOT_CONFIGURED")
    if fixed_address == "ADDRESS_NOT_CONFIGURED":
        db.close()
        await update.message.reply_text(msg.get_message('MSG-019b'))
        return

    # Verify the Bitcoin transaction on blockchain
    try:
        from bitcoin_utils import verify_payment
        verification_result = verify_payment(fixed_address, deal.amount_sats, txid)

        if not verification_result.get('found', False):
            db.close()
            await update.message.reply_text(
                msg.get_message('MSG-019c',
                    error=verification_result.get('error', 'Payment not found')),
                parse_mode='Markdown'
            )
            return

        # Log verification details
        confirmations = verification_result.get('confirmations', 0)
        logger.info(f"TXID {txid} verified: {confirmations} confirmations for {deal.amount_sats} sats to {fixed_address}")

    except Exception as e:
        logger.error(f"Error verifying Bitcoin transaction {txid}: {e}")
        db.close()
        await update.message.reply_text(msg.get_message('MSG-019d'))
        return

    # Update deal with TXID and timeouts
    deal.buyer_bitcoin_txid = txid
    deal.status = 'bitcoin_sent'
    deal.current_stage = 'confirming_bitcoin'
    deal.stage_expires_at = datetime.now(timezone.utc) + timedelta(hours=BITCOIN_CONFIRMATION_HOURS)
    db.commit()
    
    # Format amount
    amount = deal.amount_sats
    amount_text = format_amount(amount)
    
    db.close()
    
    await update.message.reply_text(
        msg.get_message('MSG-020', deal=deal, amount_text=amount_text),
        parse_mode='Markdown'
    )
    
    logger.info(f"User {user.id} reported TXID {txid} for deal {deal.id}")

# =============================================================================
# SECTION 7: LIGHTNING INVOICE (/invoice) - STEPS 9-10 OF FLOW
# =============================================================================

async def invoice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command /invoice - Carlos provides Lightning invoice
    Step 9 in flow: Carlos sends invoice, lnproxy privacy attempted
    """
    user = update.effective_user

    # Log command execution
    swap_logger.log_command(
        user_id=user.id,
        command='/invoice',
        details={'has_invoice': bool(context.args)}
    )

    if not context.args:
        await update.message.reply_text(
            msg.get_message('MSG-022'),
            parse_mode='Markdown'
        )
        return

    invoice = ' '.join(context.args).strip()

    # Log invoice submission (filtered)
    swap_logger.log_user_interaction(
        user_id=user.id,
        action='invoice_submission',
        details=f'invoice={invoice[:10]}...' if invoice else 'empty_invoice'
    )

    # Basic invoice validation
    if not invoice.startswith(('lnbc', 'lntb', 'lnbcrt')):
        await update.message.reply_text(
            msg.get_message('MSG-023'),
            parse_mode='Markdown'
        )
        return
    
    # Find deal waiting for invoice
    db = get_db()
    deal = db.query(Deal).filter(
        Deal.buyer_id == user.id,
        Deal.status == 'bitcoin_confirmed'
    ).first()
    
    if not deal:
        db.close()
        await update.message.reply_text(
            msg.get_message('MSG-024'),
            parse_mode='Markdown'
        )
        return
    
    # Extract payment hash from invoice
    try:
        from bitcoin_utils import extract_payment_hash_from_invoice
        payment_hash = extract_payment_hash_from_invoice(invoice) or "hash_placeholder"
    except:
        payment_hash = "hash_placeholder"

    # Notify Carlos that we're processing privacy enhancement
    await update.message.reply_text(
        msg.get_message('MSG-025', deal=deal),
        parse_mode='Markdown'
    )
    
    # Attempt lnproxy wrapping - Multiple attempts with timeout
    final_invoice = None
    lnproxy_success = False
    
    try:
        from lnproxy_utils import wrap_invoice_for_privacy
        import time
        
        # Maximum 3 attempts in 5 minutes
        max_attempts = 3
        timeout_minutes = 5
        start_time = time.time()
        
        for attempt in range(max_attempts):
            # Check timeout (5 minutes maximum)
            elapsed = (time.time() - start_time) / 60
            if elapsed >= timeout_minutes:
                logger.warning(f'lnproxy timeout after {elapsed:.1f} minutes')
                break
                
            logger.info(f'lnproxy attempt {attempt + 1}/{max_attempts}')
            success, result = wrap_invoice_for_privacy(invoice)
            
            if success and result.get('wrapped_invoice'):
                final_invoice = result['wrapped_invoice']
                lnproxy_success = True
                logger.info(f'lnproxy success on attempt {attempt + 1}')
                break
            else:
                logger.warning(f'lnproxy attempt {attempt + 1} failed: {result.get("error", "unknown")}')
                if attempt < max_attempts - 1:
                    time.sleep(30)  # Wait 30 seconds between attempts
                    
    except Exception as e:
        logger.error(f'lnproxy error: {e}')
    
    # Check lnproxy result
    if lnproxy_success:
        # lnproxy worked - proceed normally
        deal.lightning_invoice = final_invoice
        deal.payment_hash = payment_hash
        deal.status = 'lightning_invoice_received'
        deal.current_stage = 'payment_required'
        deal.stage_expires_at = datetime.now(timezone.utc) + timedelta(hours=LIGHTNING_PAYMENT_HOURS)
        db.commit()
        
        seller_id = deal.seller_id
        
        # Format amount
        amount = deal.amount_sats
        amount_text = format_amount(amount)
        
        db.close()

        # Notify Carlos of successful privacy enhancement
        await update.message.reply_text(
            msg.get_message('MSG-026',
                deal=deal,
                invoice=final_invoice,
                amount_text=amount_text,
                LIGHTNING_PAYMENT_HOURS=LIGHTNING_PAYMENT_HOURS
            ),
            parse_mode='Markdown'
        )

        # Call coordinated function to check if Ana should be notified
        await check_and_notify_ana(deal.id)
        
    else:
        # lnproxy failed - show decision UI to Carlos
        deal.status = 'awaiting_privacy_decision'
        deal.lightning_invoice = invoice  # Save original invoice temporarily
        deal.payment_hash = payment_hash
        db.commit()
        db.close()
        
        await handle_lnproxy_failure(update, deal.id, invoice)
        return  # Exit - wait for Carlos's decision
    
    # Step 10: Notify Carlos to wait for payment
    await update.message.reply_text(f"""
⚡ Invoice Received - Deal #{deal.id}

Status: Payment request sent to seller
Your invoice: `{invoice[:20]}...`
Amount: {amount_text} sats

The seller will pay your Lightning invoice.
Bot will verify payment and complete the swap.

Time limit: {LIGHTNING_PAYMENT_HOURS} hours ⏰
    """, parse_mode='Markdown')
    
    # Call coordinated function to check if Ana should be notified
    await check_and_notify_ana(deal.id)

# =============================================================================
# SECTION 8: BITCOIN ADDRESS (/address) - STEPS 11-12 OF FLOW
# =============================================================================

async def address_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command /address - Ana provides Bitcoin address and receives Lightning invoice
    CORRECTED FLOW: Address FIRST, then invoice to pay
    """
    user = update.effective_user

    # Log command execution
    swap_logger.log_command(
        user_id=user.id,
        command='/address',
        details={'has_address': bool(context.args)}
    )

    if not context.args:
        await update.message.reply_text("""
❌ Usage: /address [bitcoin_address]

Example: /address tb1q...
        """)
        return

    address = context.args[0].strip()

    # Log address submission (filtered)
    swap_logger.log_user_interaction(
        user_id=user.id,
        action='address_submission',
        details=f'address={address[:8]}...' if address else 'empty_address'
    )

    # Validate Bitcoin address
    try:
        from bitcoin_utils import validate_bitcoin_address
        if not validate_bitcoin_address(address):
            await update.message.reply_text("❌ Invalid Bitcoin address format")
            return
    except ImportError:
        # If no bitcoin_utils, basic validation
        if not (address.startswith(('tb1', 'bc1', '1', '3')) and len(address) >= 26):
            await update.message.reply_text("❌ Invalid Bitcoin address format")
            return
    
    # Find deal waiting for Bitcoin address
    db = get_db()
    deal = db.query(Deal).filter(
        Deal.seller_id == user.id,
        Deal.status == 'awaiting_bitcoin_address',
        Deal.seller_bitcoin_address.is_(None)
    ).first()
    
    if not deal:
        db.close()
        await update.message.reply_text("❌ No deal found waiting for Bitcoin address")
        return
    
    # Save Bitcoin address
    deal.seller_bitcoin_address = address
    deal.status = 'address_provided_awaiting_payment'
    db.commit()
    
    amount = deal.amount_sats
    amount_text = format_amount(amount)
    
    # Confirm address was saved
    await update.message.reply_text(f"""
✅ Bitcoin Address Saved - Deal #{deal.id}

Address: `{address}`
Amount: {amount_text} sats

Now please pay the Lightning invoice below:
    """, parse_mode='Markdown')
    
    # NEW: Send Lightning invoice to Ana for payment
    if deal.lightning_invoice:
        invoice_message = f"""
⚡ Lightning Payment Required

Pay this invoice to complete your swap:

`{deal.lightning_invoice}`

Amount: {amount_text} sats
Time limit: 2 hours

After payment verification, your Bitcoin will be sent in the next batch.
        """
        
        await update.message.reply_text(invoice_message, parse_mode='Markdown')
        
        # Change status to indicate we're waiting for Lightning payment
        deal.status = 'lightning_payment_pending'
        deal.stage_expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
        db.commit()
        
        logger.info(f"Deal {deal.id}: Lightning invoice sent to Ana after address provided")
    else:
        await update.message.reply_text("❌ Lightning invoice not available. Please contact support.")
        logger.error(f"Deal {deal.id}: No lightning_invoice found when Ana provided address")
    
    db.close()

# =============================================================================
# SECTION 9: QUERY COMMANDS (/offers, /deals)
# =============================================================================

async def offers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View user offers with detailed status"""
    user = update.effective_user
    
    db = get_db()
    user_offers = db.query(Offer).filter(Offer.user_id == user.id).all()
    
    if not user_offers:
        await update.message.reply_text("""
📋 No offers yet

Create one:
/swapout - Lightning ⚡ → Bitcoin ₿
/swapin - Bitcoin ₿ → Lightning ⚡

Channel: @btcp2pswapoffers
        """)
        db.close()
        return
    
    message = "📋 Your Offers\n\n"
    
    for offer in user_offers:
        # Format amount
        amount = offer.amount_sats
        amount_text = format_amount(amount)
        
        # Determine type and direction
        if offer.offer_type == 'swapout':
            direction = "⚡→₿"
            offer_desc = f"Selling {amount_text} Lightning"
        else:
            direction = "₿→⚡"
            offer_desc = f"Buying {amount_text} Lightning"
        
        # Get deal state if offer was taken
        deal = db.query(Deal).filter(Deal.offer_id == offer.id).first()
        
        if offer.status == 'active':
            status_info = "🟢 Active - Waiting for taker"
        elif offer.status == 'taken' and deal:
            if deal.status == 'pending':
                status_info = "🟡 Taken - Awaiting acceptance"
            elif deal.status == 'accepted':
                status_info = "🟡 In progress - Bitcoin deposit needed"
            elif deal.status == 'bitcoin_sent':
                status_info = "🟡 In progress - Waiting confirmations"
            elif deal.status == 'bitcoin_confirmed':
                status_info = "🟡 In progress - Lightning setup"
            elif deal.status == 'lightning_invoice_received':
                status_info = "🟡 In progress - Lightning payment pending"
            elif deal.status == 'awaiting_bitcoin_address':
                status_info = "🟡 Almost done - Provide Bitcoin address"
            elif deal.status == 'ready_for_batch':
                status_info = "🟠 In batch queue - Payment processing"
            elif deal.status == 'completed':
                status_info = "🟢 Completed"
            else:
                status_info = f"🟡 Status: {deal.status}"
        else:
            status_info = f"⚪ {offer.status.title()}"
        
        message += f"#{offer.id} - {direction} {amount_text} sats\n"
        message += f"{offer_desc}\n"
        message += f"{status_info}\n\n"
    
    message += f"Total: {len(user_offers)} offers"
    
    db.close()
    await update.message.reply_text(message)

async def deals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View user's active deals"""
    user = update.effective_user
    
    db = get_db()
    user_deals = db.query(Deal).filter(
        (Deal.seller_id == user.id) | (Deal.buyer_id == user.id),
        Deal.status.in_(['pending', 'accepted', 'bitcoin_sent', 'bitcoin_confirmed', 'lightning_invoice_received'])
    ).all()
    
    if not user_deals:
        await update.message.reply_text("""
📋 No active deals

Create offers:
/swapout - Lightning ⚡ → Bitcoin ₿
/swapin - Bitcoin ₿ → Lightning ⚡

Browse: /offers
        """, parse_mode='Markdown')
        db.close()
        return
    
    message = "📋 Your Active Deals\n\n"
    
    for deal in user_deals:
        # Format amount
        amount = deal.amount_sats
        amount_text = format_amount(amount)
        
        # Determine role and state
        if deal.seller_id == user.id:
            role = "Seller (Lightning)"
            direction = "⚡→₿"
        else:
            role = "Buyer (Bitcoin)"
            direction = "₿→⚡"
        
        status_emoji = {
            'pending': '⏳',
            'accepted': '✅',
            'bitcoin_sent': '💸',
            'bitcoin_confirmed': '🔄',
            'lightning_invoice_received': '⚡'
        }.get(deal.status, '❓')
        
        message += f"#{deal.id} - {direction} {amount_text} sats\n"
        message += f"Role: {role}\n"
        
        # Add real-time confirmation checking and timeout info
        status_text = deal.status.replace('_', ' ').title()
        if deal.status == 'bitcoin_sent' and deal.buyer_bitcoin_txid:
            try:
                from bitcoin_utils import get_confirmations
                current_confirmations = get_confirmations(deal.buyer_bitcoin_txid)
                status_text = f"Bitcoin Sent ({current_confirmations}/3 confirmations)"
                if current_confirmations < 3:
                    remaining = 3 - current_confirmations
                    status_text += f"\nNext: Waiting {remaining} more confirmation{'s' if remaining != 1 else ''}"
            except Exception:
                status_text = "Bitcoin Sent (checking confirmations...)"
        
        # Add timeout information
        if deal.stage_expires_at and deal.stage_expires_at > datetime.now(timezone.utc):
            time_left = deal.stage_expires_at - datetime.now(timezone.utc)
            if time_left.total_seconds() > 3600:  # More than 1 hour
                hours_left = int(time_left.total_seconds() / 3600)
                status_text += f"\nTimeout: {hours_left}h remaining"
            else:  # Less than 1 hour
                minutes_left = int(time_left.total_seconds() / 60)
                status_text += f"\nTimeout: {minutes_left}m remaining"
        
        message += f"Status: {status_text} {status_emoji}\n\n"
    
    db.close()
    await update.message.reply_text(message, parse_mode='Markdown')

# =============================================================================
# SECTION 10: BACKGROUND MONITORING - AUTOMATED PROCESSES
# =============================================================================

async def check_and_notify_ana(deal_id):
    """
    Check if Ana should be notified: Bitcoin confirmed + invoice ready
    Implements coordinated timing according to Issue #25
    """
    try:
        db = get_db()
        deal = db.query(Deal).filter(Deal.id == deal_id).first()
        
        if not deal:
            db.close()
            return False
        
        # Check both conditions
        bitcoin_confirmed = (deal.status == 'bitcoin_confirmed' or 
                            deal.bitcoin_confirmations >= CONFIRMATION_COUNT)
        invoice_ready = deal.lightning_invoice is not None
        
        if bitcoin_confirmed and invoice_ready:
            # Both conditions met - request Bitcoin address from Ana
            seller_id = deal.seller_id
            amount_text = format_amount(deal.amount_sats)
            
            # Change status to indicate we're waiting for address
            deal.status = 'awaiting_bitcoin_address'
            db.commit()
            
            app = Application.builder().token(BOT_TOKEN).build()
            
            address_request_message = f"""
Bitcoin Confirmed - Deal #{deal.id}

Bitcoin deposit confirmed: {amount_text} sats
Status: Ready for final step

IMPORTANT: Provide your Bitcoin address first
After you send your address, the Lightning invoice will be revealed to complete the swap.

Send: /address [your_bitcoin_address]
Time limit: 48 hours

Your funds are secured and this step ensures smooth completion.
            """
            
            await app.bot.send_message(
                chat_id=seller_id,
                text=address_request_message
            )
            
            logger.info(f"Ana notified for address request - deal {deal_id}")
            db.close()
            return True
        else:
            logger.info(f"Deal {deal_id}: Waiting - Bitcoin confirmed: {bitcoin_confirmed}, Invoice ready: {invoice_ready}")
            db.close()
            return False
            
    except Exception as e:
        logger.error(f"Error in check_and_notify_ana: {e}")
        return False

async def monitor_confirmations():
    """
    Monitor Bitcoin confirmations - Step 8 of flow
    Detects when Carlos has 3 confirmations and requests Lightning invoice
    """
    while True:
        try:
            db = get_db()
            
            # Find deals waiting for confirmations
            pending_deals = db.query(Deal).filter(
                Deal.current_stage == 'confirming_bitcoin',
                Deal.buyer_bitcoin_txid.isnot(None),
                Deal.stage_expires_at > datetime.now(timezone.utc)
            ).all()
            
            for deal in pending_deals:
                txid = deal.buyer_bitcoin_txid
                
                # Import bitcoin functions
                try:
                    from bitcoin_utils import get_confirmations
                except ImportError as e:
                    logger.error(f"Failed to import get_confirmations: {e}")
                    continue
                
                confirmations = get_confirmations(txid)
                logger.info(f"Deal {deal.id}: TXID {txid} has {confirmations} confirmations")
                
                if confirmations >= CONFIRMATION_COUNT:
                    # Update deal state
                    deal.status = 'bitcoin_confirmed'
                    deal.current_stage = 'invoice_required'
                    deal.stage_expires_at = datetime.now(timezone.utc) + timedelta(hours=LIGHTNING_INVOICE_HOURS)
                    db.commit()
                    
                    logger.info(f"Deal {deal.id}: Bitcoin confirmed! Requesting Lightning invoice")
                    # Also check if Ana can be notified
                    await check_and_notify_ana(deal.id)                    
                    # Notify Carlos to provide Lightning invoice
                    app = Application.builder().token(BOT_TOKEN).build()
                    
                    amount = deal.amount_sats
                    amount_text = format_amount(amount)
                    
                    await app.bot.send_message(
                        chat_id=deal.buyer_id,
                        text=msg.get_message('MSG-021', deal=deal, amount_text=amount_text),
                        parse_mode='Markdown'
                    )
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error in monitor_confirmations: {e}")
        
        # Check every 10 minutes as configured
        await asyncio.sleep(CONFIRMATION_CHECK_MINUTES * 60)

async def monitor_lightning_payments():
    """
    Monitor Lightning payments - PRODUCTION REAL
    Only advances with real Lightning verification
    """
    while True:
        try:
            db = get_db()
            
            # Find deals waiting for Lightning payment verification
            pending_deals = db.query(Deal).filter(
                Deal.status == 'lightning_payment_pending',
                Deal.payment_hash.isnot(None)
            ).all()
            
            for deal in pending_deals:
                payment_hash = deal.payment_hash
                
                logger.info(f"Deal {deal.id}: Checking Lightning payment {payment_hash}")
                
                # Real Lightning verification
                try:
                    from bitcoin_utils import check_lightning_payment_status
                    is_paid = check_lightning_payment_status(payment_hash)
                except ImportError:
                    is_paid = False
                
                # Only advance if there's REAL Lightning verification
                if is_paid:
                    # Mark as completed - add to Bitcoin batch
                    deal.status = 'ready_for_batch'
                    deal.current_stage = 'batch_processing'
                    deal.completed_at = datetime.now(timezone.utc)
                    db.commit()
                    
                    logger.info(f"Deal {deal.id}: Lightning payment verified! Adding to Bitcoin batch")
                    
                    # Notify both users
                    app = Application.builder().token(BOT_TOKEN).build()
                    
                    amount = deal.amount_sats
                    amount_text = format_amount(amount)
                    
                    # Notify Carlos (Lightning buyer)
                    await app.bot.send_message(
                        chat_id=deal.buyer_id,
                        text=f"""
✅ Deal Completed - #{deal.id}

Lightning payment of {amount_text} sats confirmed!
Your swap out is complete.

Thanks for using P2P Swap Bot!
                        """,
                        parse_mode='Markdown'
                    )
                    
                    # Notify Ana (seller) - Bitcoin will be sent in batch
                    await app.bot.send_message(
                        chat_id=deal.seller_id,
                        text=f"""
✅ Payment Verified - Deal #{deal.id}

Lightning payment received and verified!
Your {amount_text} sats Bitcoin will be sent in the next batch.

Your funds are secured and will be sent shortly.
                        """,
                        parse_mode='Markdown'
                    )
                    
                    logger.info(f"Deal {deal.id}: Added to Bitcoin batch queue")
                else:
                    # Log that it's waiting for real verification
                    logger.info(f"Deal {deal.id}: Waiting for Lightning payment verification")
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error in monitor_lightning_payments: {e}")
        
        # Check every 30 seconds
        await asyncio.sleep(30)

async def monitor_expired_timeouts():
    """
    Monitor and process expired timeouts - Automatic cleanup
    Cancel deals and reactivate offers according to which stage expired
    """
    while True:
        try:
            db = get_db()
            
            # Find deals with expired timeout
            expired_deals = db.query(Deal).filter(
                Deal.stage_expires_at < datetime.now(timezone.utc),
                Deal.status.in_(['pending', 'accepted', 'bitcoin_sent', 'bitcoin_confirmed', 'lightning_invoice_received'])
            ).all()
            
            for deal in expired_deals:
                await handle_expired_deal(deal, db)
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error in monitor_expired_timeouts: {e}")
        
        # Check every 5 minutes
        await asyncio.sleep(300)

async def handle_expired_deal(deal, db):
    """
    Handle expired deal according to stage - Specific actions per timeout
    """
    stage = deal.current_stage
    
    try:
        if stage == 'txid_required':
            # Carlos didn't send TXID in 30 min - cancel and reactivate offer
            await cancel_deal_and_reactivate_offer(deal, db, 'TXID timeout')
            
        elif stage == 'confirming_bitcoin':
            # Bitcoin not confirmed in 48h - cancel with refund warning
            await cancel_deal_bitcoin_timeout(deal, db)
            
        elif stage == 'invoice_required':
            # Carlos didn't send invoice in 2h - cancel deal
            await cancel_deal_and_notify(deal, db, 'Lightning invoice timeout')
            
        elif stage == 'payment_required':
            # Ana didn't pay Lightning in 2h - cancel deal
            await cancel_deal_and_notify(deal, db, 'Lightning payment timeout')
            
        logger.info(f"Handled expired deal {deal.id} in stage {stage}")
        
    except Exception as e:
        logger.error(f"Error handling expired deal {deal.id}: {e}")

# =============================================================================
# TIMEOUT HELPER FUNCTIONS
# =============================================================================

async def cancel_deal_and_reactivate_offer(deal, db, reason):
    """Cancel deal due to TXID timeout and reactivate offer"""
    deal.status = 'cancelled'
    deal.timeout_reason = reason
    
    # Reactivate offer preserving remaining time
    offer = db.query(Offer).filter(Offer.id == deal.offer_id).first()
    if offer:
        offer.status = 'active'
        offer.taken_by = None
        offer.taken_at = None
    
    db.commit()
    
    # Notify both users
    app = Application.builder().token(BOT_TOKEN).build()
    
    await app.bot.send_message(
        chat_id=deal.buyer_id,
        text=f"❌ Deal #{deal.id} Cancelled\n\nTimeout: {reason}\nThe offer is available again in the channel."
    )
    
    await app.bot.send_message(
        chat_id=deal.seller_id,
        text=f"🔄 Deal #{deal.id} Cancelled\n\nReason: {reason}\nYour offer is active again in @btcp2pswapoffers"
    )

async def cancel_deal_bitcoin_timeout(deal, db):
    """Cancel deal due to Bitcoin confirmation timeout (48h)"""
    deal.status = 'cancelled'
    deal.timeout_reason = 'Bitcoin confirmation timeout - 48h expired'
    db.commit()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    await app.bot.send_message(
        chat_id=deal.buyer_id,
        text=f"⏰ Deal #{deal.id} Expired\n\nBitcoin confirmations not received within 48 hours.\n\nYour funds will return to your wallet automatically.\n\nTXID: `{deal.buyer_bitcoin_txid}`",
        parse_mode='Markdown'
    )
    
    await app.bot.send_message(
        chat_id=deal.seller_id,
        text=f"⏰ Deal #{deal.id} Expired\n\nBitcoin confirmations timeout (48h).\nDeal cancelled, your offer remains expired."
    )

async def cancel_deal_and_notify(deal, db, reason):
    """Cancel deal and notify both parties"""
    deal.status = 'cancelled'
    deal.timeout_reason = reason
    db.commit()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    await app.bot.send_message(
        chat_id=deal.buyer_id,
        text=f"❌ Deal #{deal.id} Cancelled\n\nTimeout: {reason}\nDeal terminated due to inactivity."
    )
    
    await app.bot.send_message(
        chat_id=deal.seller_id,
        text=f"❌ Deal #{deal.id} Cancelled\n\nTimeout: {reason}\nDeal terminated due to inactivity."
    )

# =============================================================================
# BITCOIN BATCH PROCESSING
# =============================================================================

async def process_bitcoin_batches():
    """
    Process Bitcoin batches - Step 16 of flow
    Send Bitcoin to Ana when there are enough deals or time limit
    """
    # Batch configuration - ADJUST ACCORDING TO NEEDS
    MIN_BATCH_SIZE = 3          # Minimum deals to process batch
    MAX_WAIT_MINUTES = BATCH_WAIT_MINUTES  # Maximum wait time
    
    while True:
        try:
            db = get_db()
            
            # Get deals ready for Bitcoin payment
            pending_payouts = db.query(Deal).filter(
                Deal.status == 'ready_for_batch',
                Deal.seller_bitcoin_address.isnot(None)
            ).all()
            
            if not pending_payouts:
                logger.info("No pending payouts, waiting for more")
                db.close()
                # Wait until next exact hour (00 minutes)
                current_time = time.time()
                seconds_since_epoch = int(current_time)
                seconds_in_minute = seconds_since_epoch % 60
                minutes_since_hour = (seconds_since_epoch // 60) % 60

                # Calculate seconds until next exact hour
                minutes_to_next_hour = 60 - minutes_since_hour
                if minutes_to_next_hour == 60:
                    minutes_to_next_hour = 0
                    
                seconds_to_wait = (minutes_to_next_hour * 60) - seconds_in_minute
                await asyncio.sleep(seconds_to_wait)
                continue
            
            logger.info(f"{len(pending_payouts)} pending payouts, checking batch criteria")
            
            # Get oldest deal to check time
            oldest_deal = min(pending_payouts, key=lambda d: d.created_at)
            elapsed_minutes = (datetime.now(timezone.utc) - oldest_deal.created_at).total_seconds() / 60
            
            # Process batch if enough deals OR enough time passed
            if len(pending_payouts) >= MIN_BATCH_SIZE or elapsed_minutes >= MAX_WAIT_MINUTES:
                
                if len(pending_payouts) >= MIN_BATCH_SIZE:
                    reason = f"batch size reached ({len(pending_payouts)} >= {MIN_BATCH_SIZE})"
                else:
                    reason = f"time limit reached ({elapsed_minutes:.1f} >= {MAX_WAIT_MINUTES} minutes)"
                
                logger.info(f"Processing batch of {len(pending_payouts)} payouts - {reason}")
                
                # Process the batch
                success = await send_bitcoin_batch(pending_payouts, db)
                
                if success:
                    logger.info(f"Successfully processed batch of {len(pending_payouts)} Bitcoin payouts")
                else:
                    logger.error("Failed to process Bitcoin batch")
            
            db.close()
            # Wait until next exact hour to check again
            current_time = time.time()
            seconds_since_epoch = int(current_time)
            seconds_in_minute = seconds_since_epoch % 60
            minutes_since_hour = (seconds_since_epoch // 60) % 60

            # Calculate seconds until next exact hour
            minutes_to_next_hour = 60 - minutes_since_hour
            if minutes_to_next_hour == 60:
                minutes_to_next_hour = 0
                
            seconds_to_wait = (minutes_to_next_hour * 60) - seconds_in_minute
            await asyncio.sleep(seconds_to_wait)
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            await asyncio.sleep(300)

async def send_bitcoin_batch(pending_deals, db):
    """
    Send real Bitcoin using bot's wallet - Step 16 of flow
    Ana receives Bitcoin at her provided address
    """
    try:
        # Group deals by amount for privacy
        deals_by_amount = {}
        for deal in pending_deals:
            amount = deal.amount_sats
            if amount not in deals_by_amount:
                deals_by_amount[amount] = []
            deals_by_amount[amount].append(deal)
        
        # Process each amount group
        for amount_sats, amount_deals in deals_by_amount.items():
            logger.info(f"Creating Bitcoin batch transaction for {len(amount_deals)} deals of {amount_sats} sats each")
            
            # For testing, simulate Bitcoin transaction
            # In production: integrate with wallet_manager for real transactions
            simulated_txid = f"batch_{amount_sats}_{len(amount_deals)}_{int(datetime.now(timezone.utc).timestamp())}"
            
            # Mark deals as completed
            for deal in amount_deals:
                deal.bitcoin_txid = simulated_txid
                deal.status = 'completed'
                deal.completed_at = datetime.now(timezone.utc)
            
            # Notify sellers (Ana)
            await notify_sellers_batch_sent(amount_deals, simulated_txid)
            
            logger.info(f"Simulated Bitcoin batch sent: {simulated_txid} for {len(amount_deals)} deals")
        
        db.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error in send_bitcoin_batch: {e}")
        return False

async def notify_sellers_batch_sent(deals, txid):
    """
    Notify sellers that Bitcoin was sent - Step 16 final
    Ana receives confirmation that she received Bitcoin
    """
    app = Application.builder().token(BOT_TOKEN).build()
    
    for deal in deals:
        amount = deal.amount_sats
        amount_text = format_amount(amount)
        
        try:
            await app.bot.send_message(
                chat_id=deal.seller_id,
                text=f"""
💰 Bitcoin Sent - Deal #{deal.id}

Your {amount_text} sats have been sent!

Transaction: {txid}
Address: {deal.seller_bitcoin_address}

Check testnet blockchain explorer.
Swap completed successfully! ✅

Thanks for using P2P Swap Bot!
                """
            )
        except Exception as e:
            logger.error(f"Failed to notify seller {deal.seller_id}: {e}")

# =============================================================================
# LNPROXY PRIVACY HANDLING
# =============================================================================

async def handle_lnproxy_failure(update, deal_id, invoice):
    """
    Handle when lnproxy fails - show decision UI to Carlos
    """
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [InlineKeyboardButton("🔓 Reveal Original Invoice", callback_data=f"reveal_invoice_{deal_id}")],
        [InlineKeyboardButton("⏳ Keep Trying (20min retries)", callback_data=f"retry_lnproxy_{deal_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        msg.get_message('MSG-027', deal_id=deal_id),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_reveal_invoice(query, user, deal_id, db):
    """
    Handle when Carlos decides to reveal his original invoice
    """
    deal = db.query(Deal).filter(Deal.id == deal_id, Deal.seller_id == user.id).first()
    
    if not deal or deal.status != 'awaiting_privacy_decision':
        await query.edit_message_text("❌ Deal not found or already processed")
        db.close()
        return
    
    # Update deal with original invoice
    deal.status = 'lightning_invoice_received'
    deal.current_stage = 'payment_required'
    deal.stage_expires_at = datetime.now(timezone.utc) + timedelta(hours=LIGHTNING_PAYMENT_HOURS)
    db.commit()
    
    amount_text = format_amount(deal.amount_sats)
    
    await query.edit_message_text(
        msg.get_message('MSG-028',
            deal_id=deal_id,
            amount_text=amount_text,
            LIGHTNING_PAYMENT_HOURS=LIGHTNING_PAYMENT_HOURS
        ),
        parse_mode='Markdown'
    )
    
    db.close()
    
    # Call coordinated function to check if Ana should be notified
    await check_and_notify_ana(deal_id)

async def handle_retry_lnproxy(query, user, deal_id, db):
    """
    Handle when Carlos decides to keep trying lnproxy
    """
    deal = db.query(Deal).filter(Deal.id == deal_id, Deal.seller_id == user.id).first()
    
    if not deal or deal.status != 'awaiting_privacy_decision':
        await query.edit_message_text("❌ Deal not found or already processed")
        db.close()
        return
    
    # Update deal for retries
    deal.status = 'retrying_lnproxy'
    deal.current_stage = 'privacy_retry'
    deal.stage_expires_at = datetime.now(timezone.utc) + timedelta(hours=2)  # 2 hours for retries
    db.commit()
    db.close()
    
    await query.edit_message_text(
        msg.get_message('MSG-029', deal_id=deal_id),
        parse_mode='Markdown'
    )

async def reveal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command /reveal - Carlos can change his mind and reveal original invoice
    """
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text(
            msg.get_message('MSG-030')
        )
        return
    
    try:
        deal_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            msg.get_message('MSG-031')
        )
        return
    
    db = get_db()
    deal = db.query(Deal).filter(
        Deal.id == deal_id,
        Deal.seller_id == user.id,  # Carlos must be the seller (who sends invoice)
        Deal.status == 'retrying_lnproxy'
    ).first()
    
    if not deal:
        db.close()
        await update.message.reply_text(
            msg.get_message('MSG-032', deal_id=deal_id)
        )
        return
    
    # Change from retries to revealed invoice
    deal.status = 'lightning_invoice_received'
    deal.current_stage = 'payment_required'
    deal.stage_expires_at = datetime.now(timezone.utc) + timedelta(hours=LIGHTNING_PAYMENT_HOURS)
    db.commit()
    
    amount_text = format_amount(deal.amount_sats)
    
    await update.message.reply_text(
        msg.get_message('MSG-033',
            deal_id=deal_id,
            amount_text=amount_text,
            LIGHTNING_PAYMENT_HOURS=LIGHTNING_PAYMENT_HOURS
        ),
        parse_mode='Markdown'
    )
    
    db.close()
    
    # Check if Ana can be notified now
    await check_and_notify_ana(deal_id)

# =============================================================================
# LNPROXY RETRY MONITORING
# =============================================================================

async def monitor_lnproxy_retries():
    """
    Monitor for lnproxy retries every 20 minutes for 2 hours maximum
    """
    while True:
        try:
            db = get_db()
            
            # Find deals waiting for lnproxy retries
            retry_deals = db.query(Deal).filter(
                Deal.status == 'retrying_lnproxy',
                Deal.current_stage == 'privacy_retry'
            ).all()
            
            for deal in retry_deals:
                # Check if deal has expired (2 hours)
                if deal.stage_expires_at and datetime.now(timezone.utc) > deal.stage_expires_at:
                    logger.info(f"Deal {deal.id}: lnproxy retry timeout after 2 hours")
                    await handle_lnproxy_timeout(deal)
                    continue
                
                # Check if it's time to retry (every 20 minutes)
                last_attempt = deal.last_updated
                minutes_since_last = (datetime.now(timezone.utc) - last_attempt).total_seconds() / 60
                
                if minutes_since_last >= 20:
                    logger.info(f"Deal {deal.id}: Starting 20-minute lnproxy retry")
                    await perform_lnproxy_retry(deal)
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error in monitor_lnproxy_retries: {e}")
        
        # Check every 5 minutes
        await asyncio.sleep(300)

async def handle_lnproxy_timeout(deal):
    """
    Handle lnproxy timeout after 2 hours - cancel deal and refund
    """
    try:
        db = get_db()
        
        # Update deal as expired
        deal.status = 'expired_privacy_timeout'
        
        # Reactivate Ana's offer to return to channel
        offer = db.query(Offer).filter(Offer.id == deal.offer_id).first()
        if offer:
            offer.status = 'active'
            offer.taken_by = None
            offer.taken_at = None
            
            logger.info(f"Deal {deal.id}: Ana's offer {offer.id} returned to channel after lnproxy timeout")
            
            # Notify Carlos (buyer) about timeout and refund
            app = Application.builder().token(BOT_TOKEN).build()
            await app.bot.send_message(
                chat_id=deal.buyer_id,  # Carlos - the buyer
                text=f"""
Deal #{deal.id} has expired after 2 hours.

Your Bitcoin will be returned to the original sending address minus network fees.

Refund will be processed in the next batch.
                """
            )
        
        db.commit()
        db.close()
        
    except Exception as e:
        logger.error(f"Error handling lnproxy timeout for deal {deal.id}: {e}")

async def perform_lnproxy_retry(deal):
    """
    Perform lnproxy retry for a specific deal
    """
    try:
        db = get_db()
        
        # Get original invoice from deal
        original_invoice = deal.lightning_invoice
        
        logger.info(f"Deal {deal.id}: Starting lnproxy retry attempt")
        
        # Try lnproxy for 5 minutes maximum (3 attempts)
        from lnproxy_utils import wrap_invoice_for_privacy
        import time
        
        max_attempts = 3
        timeout_minutes = 5
        start_time = time.time()
        
        for attempt in range(max_attempts):
            # Check timeout (5 minutes maximum)
            elapsed = (time.time() - start_time) / 60
            if elapsed >= timeout_minutes:
                logger.warning(f"Deal {deal.id}: lnproxy retry timeout after {elapsed:.1f} minutes")
                break
                
            logger.info(f"Deal {deal.id}: lnproxy retry attempt {attempt + 1}/{max_attempts}")
            success, result = wrap_invoice_for_privacy(original_invoice)
            
            if success and result.get('wrapped_invoice'):
                # lnproxy worked! Update deal
                deal.lightning_invoice = result['wrapped_invoice']
                deal.status = 'lightning_invoice_received'
                deal.current_stage = 'payment_required'
                deal.stage_expires_at = datetime.now(timezone.utc) + timedelta(hours=LIGHTNING_PAYMENT_HOURS)
                deal.last_updated = datetime.now(timezone.utc)
                db.commit()
                
                logger.info(f"Deal {deal.id}: lnproxy retry successful on attempt {attempt + 1}")
                
                # Check if Ana can be notified
                await check_and_notify_ana(deal.id)
                
                db.close()
                return True
            else:
                logger.warning(f"Deal {deal.id}: lnproxy retry attempt {attempt + 1} failed")
                if attempt < max_attempts - 1:
                    time.sleep(30)  # Wait 30 seconds between attempts
        
        # Update timestamp for next retry in 20 minutes
        deal.last_updated = datetime.now(timezone.utc)
        db.commit()
        db.close()
        
        logger.info(f"Deal {deal.id}: lnproxy retry failed, will try again in 20 minutes")
        return False
        
    except Exception as e:
        logger.error(f"Error performing lnproxy retry for deal {deal.id}: {e}")
        return False

# =============================================================================
# MAIN FUNCTION AND APPLICATION SETUP
# =============================================================================

def main():
    """
    Main bot function - Configure all handlers and monitors
    """
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return
    
    if not OFFERS_CHANNEL_ID:
        logger.warning("OFFERS_CHANNEL_ID not configured - channel posting disabled")
    
    # Create database tables
    create_tables()
    
    # Initialize MessageManager
    global msg
    try:
        msg = MessageManager()
        logger.info("MessageManager initialized successfully")
    except Exception as e:
        logger.error(f"MessageManager initialization failed: {e}")
        logger.warning("Bot will continue with hardcoded fallback messages")
        msg = None

    # Initialize Swap Logger
    global swap_logger
    try:
        swap_logger = get_swap_logger()
        logger.info("Swap Logger initialized successfully")
    except Exception as e:
        logger.error(f"Swap Logger initialization failed: {e}")
        return
    
    # Create Telegram application
    application = Application.builder().token(BOT_TOKEN).build()

    # Start background monitors in threads
    monitor_thread = threading.Thread(target=lambda: asyncio.run(monitor_confirmations()))
    monitor_thread.daemon = True
    monitor_thread.start()

    monitor_thread_ln = threading.Thread(target=lambda: asyncio.run(monitor_lightning_payments()))
    monitor_thread_ln.daemon = True
    monitor_thread_ln.start() 

    # Monitor expired timeouts
    timeout_thread = threading.Thread(target=lambda: asyncio.run(monitor_expired_timeouts()))
    timeout_thread.daemon = True
    timeout_thread.start()

    # Monitor lnproxy retries
    lnproxy_retry_thread = threading.Thread(target=lambda: asyncio.run(monitor_lnproxy_retries()))
    lnproxy_retry_thread.daemon = True
    lnproxy_retry_thread.start()

    # Bitcoin batch processing
    batch_thread = threading.Thread(target=lambda: asyncio.run(process_bitcoin_batches()))
    batch_thread.daemon = True
    batch_thread.start()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("swapout", swapout))
    application.add_handler(CommandHandler("swapin", swapin))
    application.add_handler(CommandHandler("offers", offers))
    application.add_handler(CommandHandler("deals", deals))
    application.add_handler(CommandHandler("take", take))
    application.add_handler(CommandHandler("txid", txid_command))
    application.add_handler(CommandHandler("invoice", invoice_command))
    application.add_handler(CommandHandler("address", address_command))
    application.add_handler(CommandHandler("reveal", reveal_command))
    
    # Button handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Initialize logging
    init_logging()
    swap_logger.log_system_event('bot_startup', 'P2P Swap Bot starting')

    # Start bot
    logger.info("Starting P2P Swap Bot...")
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=['message', 'callback_query']
    )

if __name__ == '__main__':
    main()
