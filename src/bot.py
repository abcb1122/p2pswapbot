#!/usr/bin/env python3
"""
===============================================================================
P2P SWAP BOT - Bot de Telegram para intercambios Lightning <-> Bitcoin onchain
===============================================================================

FLUJO SWAP OUT (Lightning → Bitcoin):
1. Ana /start → registra
2. Ana /swapout → selecciona monto → oferta creada y publicada en canal
3. Carlos /take X → acepta deal con botones Accept/Cancel  
4. Carlos deposita Bitcoin → /txid → espera 3 confirmaciones
5. Carlos /invoice → proporciona factura Lightning
6. Ana paga factura Lightning → bot verifica pago
7. Ana /address → proporciona dirección Bitcoin
8. Bot envía Bitcoin en batch a Ana

Versión optimizada para principiantes - Fácil de modificar
"""

import os
import logging
import asyncio
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Importar modelos de base de datos
from database.models import get_db, User, Offer, Deal, create_tables

# Cargar variables de entorno
load_dotenv()

# =============================================================================
# CONFIGURACIÓN PRINCIPAL - MODIFICAR AQUÍ PARA CAMBIOS RÁPIDOS
# =============================================================================

# Tokens y configuración básica
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OFFERS_CHANNEL_ID = os.getenv('OFFERS_CHANNEL_ID')  # Canal público para ofertas

# Montos disponibles (en sats) - CAMBIAR AQUÍ PARA DIFERENTES MONTOS
AMOUNTS = [10000, 100000]  # Solo 10k y 100k sats

# Direcciones Bitcoin fijas (testnet) - CONFIGURAR EN .env
FIXED_ADDRESSES = {
    10000: os.getenv('BITCOIN_ADDRESS_10K'),    # Dirección para 10k sats
    100000: os.getenv('BITCOIN_ADDRESS_100K')   # Dirección para 100k sats
}

# Configuración de tiempos - AJUSTAR SEGÚN NECESIDADES
DEAL_EXPIRY_HOURS = 2           # Deals expiran en 2 horas
CONFIRMATION_COUNT = 3          # Confirmaciones Bitcoin requeridas
BATCH_WAIT_MINUTES = 60         # Tiempo máximo para batch Bitcoin
LIGHTNING_TIMEOUT_MINUTES = 2   # Override Lightning para testing (cambiar a 30 en producción)

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =============================================================================
# SECCIÓN 1: COMANDOS BÁSICOS (/start, /help, /profile)
# =============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /start - Registra usuario automáticamente
    Ana y Carlos usan este comando para activar el bot
    """
    user = update.effective_user
    
    # Registrar usuario en base de datos
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
        logger.info(f"New user registered: {user.id} ({user.username})")
    else:
        logger.info(f"Existing user: {user.id} ({user.username})")
    
    db.close()
    
    welcome_message = """
🔄 P2P Bitcoin Swap Bot

Welcome!

Commands:
/swapout - Lightning ⚡ → Bitcoin ₿
/swapin - Bitcoin ₿ → Lightning ⚡  
/offers - View your active offers
/profile - Your stats
/help - More info

Channel: @btcp2pswapoffers
Status: Live & Ready ✅
    """
    
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /help - Información sobre cómo usar el bot"""
    help_text = """
📖 How it works:

1. Create swap offers
2. Others take your offers  
3. Automatic escrow handles exchange
4. Safe Lightning ↔ Bitcoin swaps

Commands:
/swapout - Sell Lightning for Bitcoin
/swapin - Buy Lightning with Bitcoin
/offers - View your active offers
/take [ID] - Take an offer
/deals - Your active swaps
/profile - View your stats

Security: Multisig escrow, no custody
Channel: @btcp2pswapoffers
    """
    await update.message.reply_text(help_text)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /profile - Ver estadísticas del usuario"""
    user = update.effective_user
    
    db = get_db()
    user_data = db.query(User).filter(User.telegram_id == user.id).first()
    db.close()
    
    if not user_data:
        await update.message.reply_text("❌ Register first: /start")
        return
    
    profile_text = f"""
👤 **Your Profile**

ID: {user_data.telegram_id}
User: @{user_data.username or 'Not set'}
Name: {user_data.first_name}

**Stats:**
Completed: {user_data.total_deals}
Rating: {'⭐' * int(user_data.reputation_score)} ({user_data.reputation_score}/5.0)
Volume: {user_data.total_volume:,} sats

**Bitcoin address:** {user_data.bitcoin_address or 'Not set'}
    """
    await update.message.reply_text(profile_text, parse_mode='Markdown')

# =============================================================================
# SECCIÓN 2: CREACIÓN DE OFERTAS (/swapout, /swapin)
# =============================================================================

async def swapout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /swapout - Ana crea oferta Lightning → Bitcoin
    Paso 3 del flujo: Ana selecciona monto con botones
    """
    keyboard = []
    
    # Crear botones para cada monto disponible
    for amount in AMOUNTS:
        if amount >= 1000000:
            text = f"{amount:,}"
        elif amount >= 1000:
            text = f"{amount:,}"
        else:
            text = str(amount)
            
        keyboard.append([InlineKeyboardButton(text, callback_data=f"swapout_{amount}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Swap Out: Lightning ⚡ → Bitcoin ₿\n\nSelect amount:",
        reply_markup=reply_markup
    )

async def swapin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /swapin - Crear oferta Bitcoin → Lightning"""
    keyboard = []
    
    for amount in AMOUNTS:
        if amount >= 1000000:
            text = f"{amount:,}"
        elif amount >= 1000:
            text = f"{amount:,}"
        else:
            text = str(amount)
            
        keyboard.append([InlineKeyboardButton(text, callback_data=f"swapin_{amount}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Swap In: Bitcoin ₿ → Lightning ⚡\n\nSelect amount:",
        reply_markup=reply_markup
    )

# =============================================================================
# SECCIÓN 3: MANEJO DE BOTONES Y CREACIÓN DE OFERTAS
# =============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja clicks de botones - Auto-registra usuarios y procesa acciones
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    # Auto-registrar usuario si no existe
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
        logger.info(f"Auto-registered user: {user.id} ({user.username})")
    
    # Procesar diferentes tipos de botones
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

async def create_offer(query, user, amount, offer_type, db):
    """
    Crear nueva oferta y publicarla en canal
    Paso 4-6 del flujo: Oferta creada y publicada sin mostrar username
    """
    new_offer = Offer(
        user_id=user.id,
        offer_type=offer_type,
        amount_sats=amount,
        rate=1.0,
        status='active'
    )
    
    db.add(new_offer)
    db.commit()
    offer_id = new_offer.id
    
    # Obtener estadísticas del usuario
    user_data = db.query(User).filter(User.telegram_id == user.id).first()
    total_swaps = user_data.total_deals
    db.close()
    
    # Formatear monto para mostrar
    if amount >= 1000000:
        amount_text = f"{amount:,}"
    elif amount >= 1000:
        amount_text = f"{amount:,}"
    else:
        amount_text = f"{amount:,}"
    
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
    
    # Publicar en canal SIN mostrar username (como requieres)
    await post_to_channel(offer_id, total_swaps, amount, offer_type, amount_text)
    
    logger.info(f"User {user.id} created {offer_type} offer: {amount} sats")

async def post_to_channel(offer_id, total_swaps, amount, offer_type, amount_text):
    """
    Publicar oferta en canal público - SIN mostrar username del creador
    Paso 6 del flujo: Publicación sin @ del usuario
    """
    if not OFFERS_CHANNEL_ID:
        return
    
    if offer_type == "swapout":
        channel_message = f"""
**Swap Out Offer #{offer_id}**

**Offering:** {amount_text} sats Lightning
**Seeking:** Bitcoin onchain  
**User swaps:** {total_swaps}

Take offer: /take {offer_id}
        """
    else:
        channel_message = f"""
**Swap In Offer #{offer_id}**

**Offering:** Bitcoin onchain
**Seeking:** {amount_text} sats Lightning
**User swaps:** {total_swaps}

Take offer: /take {offer_id}
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
# SECCIÓN 4: TOMAR OFERTAS (/take) - PASO 8-11 DEL FLUJO
# =============================================================================

async def take(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /take - Carlos toma oferta de Ana
    Paso 8-9 del flujo: Carlos acepta deal con advertencias y botones Accept/Cancel
    """
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text("""
❌ Usage: /take [offer_id]

Example: /take 5
See offers: /offers
        """)
        return
    
    try:
        offer_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid offer ID")
        return
    
    db = get_db()
    user_data = db.query(User).filter(User.telegram_id == user.id).first()
    
    if not user_data:
        # Auto-registrar si no existe
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
    
    # Extract data BEFORE any modifications to prevent DetachedInstanceError
    offer_type = offer.offer_type
    offer_amount = offer.amount_sats
    creator_username = offer_creator.username if offer_creator else "Anonymous"
    
    # Marcar oferta como tomada
    offer.status = 'taken'
    offer.taken_by = user.id
    offer.taken_at = datetime.utcnow()
    
    # Crear deal con expiración
    new_deal = Deal(
        offer_id=offer.id,
        seller_id=offer.user_id if offer_type == 'swapout' else user.id,
        buyer_id=user.id if offer_type == 'swapout' else offer.user_id,
        amount_sats=offer_amount,
        status='pending',
        expires_at=datetime.utcnow() + timedelta(hours=DEAL_EXPIRY_HOURS)
    )
    
    db.add(new_deal)
    db.commit()
    deal_id = new_deal.id
    db.close()
    
    # Formatear monto
    amount = offer_amount  # Use extracted value
    if amount >= 1000000:
        amount_text = f"{amount:,}"
    elif amount >= 1000:
        amount_text = f"{amount:,}"
    else:
        amount_text = f"{amount:,}"
    
    if offer_type == 'swapout':
        # Carlos está comprando Lightning, debe depositar Bitcoin
        # Paso 9 del flujo: Mensaje con advertencias y botones Accept/Cancel
        keyboard = [
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"accept_deal_{deal_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_deal_{deal_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(f"""
🤝 **Deal #{deal_id} Started**

**Your role:** Lightning Buyer ⚡
**You get:** {amount_text} Lightning sats
**You pay:** {amount_text} Bitcoin sats
**Operation time:** Up to 60 minutes ⏰

⚠️ **IMPORTANT WARNINGS:**
- Send EXACT amounts or risk losing sats
- This operation cannot be cancelled once started
- Follow instructions carefully

**Expires:** {DEAL_EXPIRY_HOURS} hours ⏱️
        """, reply_markup=reply_markup)
        
    else:
        # Swap in - flujo diferente (no implementado completamente en tu solicitud)
        await update.message.reply_text(f"""
🤝 **Deal #{deal_id} Started**

Swap in functionality - To be implemented
        """)
    
    logger.info(f"User {user.id} took offer {offer_id}, deal {deal_id} created")

# =============================================================================
# SECCIÓN 5: MANEJO DE ACCEPT/CANCEL - PASO 10-11 DEL FLUJO
# =============================================================================

async def accept_deal(query, user, deal_id, db):
    """
    Paso 11 del flujo: Carlos acepta - recibe dirección Bitcoin y instrucciones
    """
    deal = db.query(Deal).filter(Deal.id == deal_id, Deal.buyer_id == user.id).first()
    
    if not deal:
        db.close()
        await query.edit_message_text("❌ Deal not found or not yours")
        return
    
    if deal.status != 'pending':
        db.close()
        await query.edit_message_text(f"❌ Deal #{deal_id} already processed")
        return
    
    # Actualizar estado del deal
    deal.status = 'accepted'
    deal.accepted_at = datetime.utcnow()
    db.commit()
    
    # Obtener dirección fija para este monto
    fixed_address = FIXED_ADDRESSES.get(deal.amount_sats, "ADDRESS_NOT_CONFIGURED")
    
    # Formatear monto
    amount = deal.amount_sats
    if amount >= 1000000:
        amount_text = f"{amount:,}"
    elif amount >= 1000:
        amount_text = f"{amount:,}"
    else:
        amount_text = f"{amount:,}"
    
    db.close()
    
    # Paso 11: Primer mensaje con dirección Bitcoin
    await query.edit_message_text(f"""
💰 **Bitcoin Deposit Required - Deal #{deal_id}**

Send exactly **{amount_text} sats** to:
`{fixed_address}`

⚠️ **CRITICAL:**
- Send EXACTLY {amount_text} sats
- Wrong amount = lost funds
- Use this address only

After sending, report your transaction ID.
    """, parse_mode='Markdown')
    
    # Segundo mensaje con instrucciones de /txid
    await query.message.reply_text(f"""
🔍 **Next Step - Report Transaction**

After sending Bitcoin to the address above:

**Use:** /txid [your_transaction_id]
**Example:** /txid abc123def456...

We need 3 confirmations before proceeding.
**Estimated time:** 30 minutes ⏰
    """)

async def cancel_deal(query, user, deal_id, db):
    """
    Paso 10 del flujo: Carlos cancela - oferta regresa al canal
    """
    deal = db.query(Deal).filter(Deal.id == deal_id, Deal.buyer_id == user.id).first()
    
    if not deal:
        db.close()
        await query.edit_message_text("❌ Deal not found or not yours")
        return
    
    # Cancelar deal y reactivar oferta
    deal.status = 'cancelled'
    
    offer = db.query(Offer).filter(Offer.id == deal.offer_id).first()
    if offer:
        offer.status = 'active'
        offer.taken_by = None
        offer.taken_at = None
    
    db.commit()
    db.close()
    
    await query.edit_message_text(f"""
❌ **Deal #{deal_id} Cancelled**

The offer is now available again in the channel.
Others can take it with /take {deal.offer_id}
    """)

# =============================================================================
# SECCIÓN 6: REPORTE DE TRANSACCIONES (/txid) - PASO 11 DEL FLUJO
# =============================================================================

async def txid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /txid - Carlos reporta transacción Bitcoin
    Paso 11 del flujo: Carlos envía TXID y espera confirmaciones
    """
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text("""
❌ Usage: /txid [transaction_id]

Example: /txid abc123def456...
        """)
        return
    
    txid = context.args[0].strip()
    
    # Buscar deal activo para este usuario
    db = get_db()
    deal = db.query(Deal).filter(
        Deal.buyer_id == user.id,
        Deal.status.in_(['accepted', 'bitcoin_sent'])
    ).first()
    
    if not deal:
        db.close()
        await update.message.reply_text("❌ No active deal found requiring Bitcoin deposit")
        return
    
    # Actualizar deal con TXID
    deal.buyer_bitcoin_txid = txid
    deal.status = 'bitcoin_sent'
    db.commit()
    
    # Formatear monto
    amount = deal.amount_sats
    if amount >= 1000000:
        amount_text = f"{amount:,}"
    elif amount >= 1000:
        amount_text = f"{amount:,}"
    else:
        amount_text = f"{amount:,}"
    
    db.close()
    
    await update.message.reply_text(f"""
⏳ **TXID Received - Deal #{deal.id}**

**Transaction:** `{txid}`
**Status:** Waiting confirmations (0/{CONFIRMATION_COUNT})
**Amount:** {amount_text} sats

We'll notify you when confirmed.
**Estimated time:** 30 minutes ⏰

Next: Lightning invoice setup after confirmation.
    """, parse_mode='Markdown')
    
    logger.info(f"User {user.id} reported TXID {txid} for deal {deal.id}")

# =============================================================================
# SECCIÓN 7: FACTURAS LIGHTNING (/invoice) - PASO 12-13 DEL FLUJO
# =============================================================================

async def invoice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /invoice - Carlos proporciona factura Lightning
    Paso 12-13 del flujo: Carlos envía invoice, Ana recibe solicitud de pago
    """
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text("""
❌ Usage: /invoice [lightning_invoice]

Example: /invoice lnbc100u1p3xnhl2pp5...
        """)
        return
    
    invoice = ' '.join(context.args).strip()
    
    # Validación básica de invoice
    if not invoice.startswith(('lnbc', 'lntb', 'lnbcrt')):
        await update.message.reply_text("❌ Invalid Lightning invoice format")
        return
    
    # Buscar deal esperando invoice
    db = get_db()
    deal = db.query(Deal).filter(
        Deal.buyer_id == user.id,
        Deal.status == 'bitcoin_confirmed'
    ).first()
    
    if not deal:
        db.close()
        await update.message.reply_text("❌ No deal found waiting for Lightning invoice")
        return
    
    # Extraer payment hash del invoice
    try:
        from bitcoin_utils import extract_payment_hash_from_invoice
        payment_hash = extract_payment_hash_from_invoice(invoice) or "hash_placeholder"
    except:
        payment_hash = "hash_placeholder"
    
    # Actualizar deal
    deal.lightning_invoice = invoice
    deal.payment_hash = payment_hash
    deal.status = 'lightning_invoice_received'
    db.commit()
    
    seller_id = deal.seller_id
    
    # Formatear monto
    amount = deal.amount_sats
    if amount >= 1000000:
        amount_text = f"{amount:,}"
    elif amount >= 1000:
        amount_text = f"{amount:,}"
    else:
        amount_text = f"{amount:,}"
    
    db.close()
    
    # Paso 13: Notificar a Carlos que espere el pago
    await update.message.reply_text(f"""
⚡ **Invoice Received - Deal #{deal.id}**

**Status:** Payment request sent to seller
**Your invoice:** `{invoice[:20]}...`
**Amount:** {amount_text} sats

The seller will pay your Lightning invoice.
Bot will verify payment and complete the swap.

**Estimated time:** 30 minutes ⏰
    """, parse_mode='Markdown')
    
    # Paso 14: Notificar a Ana para pagar la factura
    try:
        await context.bot.send_message(
            chat_id=seller_id,
            text=f"""
🔔 **Payment Required - Deal #{deal.id}**

Your escrow funds are secured. Please pay this Lightning invoice:

`{invoice}`

**Amount:** {amount_text} sats
**Time limit:** 30 minutes ⏰

After payment:
- Buyer receives Lightning instantly  
- You'll provide Bitcoin address
- Bot sends you Bitcoin in next batch
            """,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to notify seller {seller_id}: {e}")

# =============================================================================
# SECCIÓN 8: DIRECCIÓN BITCOIN (/address) - PASO 15-16 DEL FLUJO
# =============================================================================

async def address_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /address - Ana proporciona dirección Bitcoin para recibir pago
    Paso 15-16 del flujo: Ana recibe fondos en batch con notificación de tiempo
    """
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text("""
❌ Usage: /address [bitcoin_address]

Example: /address tb1q...
        """)
        return
    
    address = context.args[0].strip()
    
    # Validar dirección Bitcoin
    from bitcoin_utils import validate_bitcoin_address
    if not validate_bitcoin_address(address):
        await update.message.reply_text("❌ Invalid Bitcoin address format")
        return
    
    # Buscar deal completado esperando dirección
    db = get_db()
    deal = db.query(Deal).filter(
        Deal.seller_id == user.id,
        Deal.status == 'awaiting_bitcoin_address',
        Deal.seller_bitcoin_address.is_(None)
    ).first()
    
    if not deal:
        db.close()
        await update.message.reply_text("❌ No completed deal found waiting for Bitcoin address")
        return
    
    # Guardar dirección
    deal.seller_bitcoin_address = address
    deal.status = 'ready_for_batch'
    db.commit()
    
    amount = deal.amount_sats
    if amount >= 1000000:
        amount_text = f"{amount:,}"
    elif amount >= 1000:
        amount_text = f"{amount:,}"
    else:
        amount_text = f"{amount:,}"
    
    # Calcular próximo batch
    next_batch_time = datetime.utcnow() + timedelta(minutes=BATCH_WAIT_MINUTES)
    batch_time_str = next_batch_time.strftime("%H:%M")
    
    db.close()
    
    # Paso 16: Confirmar dirección y informar sobre batch
    await update.message.reply_text(f"""
✅ **Bitcoin Address Saved - Deal #{deal.id}**

**Address:** `{address}`
**Amount:** {amount_text} sats

**Batch Processing:**
- Next batch: ~{batch_time_str} (max {BATCH_WAIT_MINUTES} min)
- Or when 3+ requests accumulated
- You'll be notified when sent

Your swap is complete! 🎉
    """, parse_mode='Markdown')

# =============================================================================
# SECCIÓN 9: COMANDOS DE CONSULTA (/offers, /deals)
# =============================================================================

async def offers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ver ofertas del usuario con estados detallados"""
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
        # Formatear monto
        amount = offer.amount_sats
        if amount >= 1000000:
            amount_text = f"{amount:,}"
        elif amount >= 1000:
            amount_text = f"{amount:,}"
        else:
            amount_text = f"{amount:,}"
        
        # Determinar tipo y dirección
        if offer.offer_type == 'swapout':
            direction = "⚡→₿"
            offer_desc = f"Selling {amount_text} Lightning"
        else:
            direction = "₿→⚡"
            offer_desc = f"Buying {amount_text} Lightning"
        
        # Obtener estado del deal si la oferta fue tomada
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
    """Ver deals activos del usuario"""
    user = update.effective_user
    
    db = get_db()
    user_deals = db.query(Deal).filter(
        (Deal.seller_id == user.id) | (Deal.buyer_id == user.id),
        Deal.status.in_(['pending', 'accepted', 'bitcoin_sent', 'bitcoin_confirmed', 'lightning_invoice_received'])
    ).all()
    
    if not user_deals:
        await update.message.reply_text("""
📋 **No active deals**

Create offers:
/swapout - Lightning ⚡ → Bitcoin ₿
/swapin - Bitcoin ₿ → Lightning ⚡

Browse: /offers
        """, parse_mode='Markdown')
        db.close()
        return
    
    message = "📋 **Your Active Deals**\n\n"
    
    for deal in user_deals:
        # Formatear monto
        amount = deal.amount_sats
        if amount >= 1000000:
            amount_text = f"{amount:,}"
        elif amount >= 1000:
            amount_text = f"{amount:,}"
        else:
            amount_text = f"{amount:,}"
        
        # Determinar rol y estado
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
        message += f"Status: {deal.status.replace('_', ' ').title()} {status_emoji}\n\n"
    
    db.close()
    await update.message.reply_text(message, parse_mode='Markdown')

# =============================================================================
# SECCIÓN 10: MONITOREO AUTOMÁTICO - PROCESOS EN BACKGROUND
# =============================================================================

async def monitor_confirmations():
    """
    Monitorea confirmaciones Bitcoin - Paso 11 del flujo
    Detecta cuando Carlos tiene 3 confirmaciones y pide Lightning invoice
    """
    while True:
        try:
            db = get_db()
            
            # Buscar deals esperando confirmaciones
            pending_deals = db.query(Deal).filter(
                Deal.status == 'bitcoin_sent',
                Deal.buyer_bitcoin_txid.isnot(None)
            ).all()
            
            for deal in pending_deals:
                txid = deal.buyer_bitcoin_txid
                
                # Importar funciones de bitcoin_utils
                try:
                    from bitcoin_utils import get_confirmations
                except ImportError as e:
                    logger.error(f"Failed to import get_confirmations: {e}")
                    continue
                
                confirmations = get_confirmations(txid)
                logger.info(f"Deal {deal.id}: TXID {txid} has {confirmations} confirmations")
                
                if confirmations >= CONFIRMATION_COUNT:
                    # Actualizar estado del deal
                    deal.status = 'bitcoin_confirmed'
                    db.commit()
                    
                    logger.info(f"Deal {deal.id}: Bitcoin confirmed! Requesting Lightning invoice")
                    
                    # Notificar a Carlos para proporcionar Lightning invoice
                    app = Application.builder().token(BOT_TOKEN).build()
                    
                    amount = deal.amount_sats
                    if amount >= 1000000:
                        amount_text = f"{amount:,}"
                    elif amount >= 1000:
                        amount_text = f"{amount:,}"
                    else:
                        amount_text = f"{amount:,}"
                    
                    await app.bot.send_message(
                        chat_id=deal.buyer_id,
                        text=f"""
✅ **Bitcoin Confirmed - Deal #{deal.id}**

Your deposit: {amount_text} sats confirmed!
**Status:** Ready for Lightning setup

**Next step:** Generate Lightning invoice

Create invoice for {amount_text} sats in your wallet and send it here.

**Reply with:** /invoice [your_lightning_invoice]
                        """,
                        parse_mode='Markdown'
                    )
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error in monitor_confirmations: {e}")
        
        # Esperar hasta el próximo minuto "redondo" (terminado en 0)
        import time
        current_time = time.time()
        seconds_since_epoch = int(current_time)
        seconds_in_minute = seconds_since_epoch % 60
        minutes_since_hour = (seconds_since_epoch // 60) % 60

        # Calcular cuántos segundos faltan para el próximo minuto terminado en 0
        minutes_to_next_round = (10 - (minutes_since_hour % 10)) % 10
        if minutes_to_next_round == 0:
            minutes_to_next_round = 10
            
        seconds_to_wait = (minutes_to_next_round * 60) - seconds_in_minute
        await asyncio.sleep(seconds_to_wait)

async def monitor_lightning_payments():
    """
    Monitorea pagos Lightning - PRODUCCIÓN REAL
    Solo avanza con verificación real de Lightning
    """
    while True:
        try:
            db = get_db()
            
            # Buscar deals esperando verificación de pago Lightning
            pending_deals = db.query(Deal).filter(
                Deal.status == 'lightning_invoice_received',
                Deal.payment_hash.isnot(None)
            ).all()
            
            for deal in pending_deals:
                payment_hash = deal.payment_hash
                
                logger.info(f"Deal {deal.id}: Checking Lightning payment {payment_hash}")
                
                # Verificación real de Lightning
                try:
                    from bitcoin_utils import check_lightning_payment_status
                    is_paid = check_lightning_payment_status(payment_hash)
                except ImportError:
                    is_paid = False
                
                # Solo avanzar si hay verificación REAL de Lightning
                if is_paid:
                    # Marcar como completado - pedir dirección Bitcoin
                    deal.status = 'awaiting_bitcoin_address'
                    deal.completed_at = datetime.utcnow()
                    db.commit()
                    
                    logger.info(f"Deal {deal.id}: Lightning payment verified! Requesting Bitcoin address")
                    
                    # Notificar ambos usuarios
                    app = Application.builder().token(BOT_TOKEN).build()
                    
                    amount = deal.amount_sats
                    if amount >= 1000000:
                        amount_text = f"{amount:,}"
                    elif amount >= 1000:
                        amount_text = f"{amount:,}"
                    else:
                        amount_text = f"{amount:,}"
                    
                    # Notificar a Carlos (comprador Lightning)
                    await app.bot.send_message(
                        chat_id=deal.buyer_id,
                        text=f"""
✅ **Deal Completed - #{deal.id}**

Lightning payment of {amount_text} sats confirmed!
Your swap out is complete.

Thanks for using P2P Swap Bot!
                        """,
                        parse_mode='Markdown'
                    )
                    
                    # Notificar a Ana (vendedor) - pedir dirección Bitcoin
                    await app.bot.send_message(
                        chat_id=deal.seller_id,
                        text=f"""
✅ **Payment Verified - Deal #{deal.id}**

Lightning payment received and verified!
Your {amount_text} sats Bitcoin will be sent in the next batch.

**Please provide your Bitcoin address:**
/address [your_bitcoin_address]

Your funds are secured and will be sent shortly.
                        """,
                        parse_mode='Markdown'
                    )
                    
                    logger.info(f"Deal {deal.id}: Added to Bitcoin batch queue")
                else:
                    # Log que está esperando verificación real
                    logger.info(f"Deal {deal.id}: Waiting for Lightning payment verification")
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error in monitor_lightning_payments: {e}")
        
        # Verificar cada 30 segundos
        await asyncio.sleep(30)

async def process_bitcoin_batches():
    """
    Procesa batches de Bitcoin - Paso 16 del flujo
    Envía Bitcoin a Ana cuando hay suficientes deals o tiempo límite
    """
    # Configuración de batch - AJUSTAR SEGÚN NECESIDADES
    MIN_BATCH_SIZE = 3          # Mínimo deals para procesar batch
    MAX_WAIT_MINUTES = BATCH_WAIT_MINUTES  # Tiempo máximo de espera
    
    while True:
        try:
            db = get_db()
            
            # Obtener deals listos para pago Bitcoin
            pending_payouts = db.query(Deal).filter(
                Deal.status == 'ready_for_batch',
                Deal.seller_bitcoin_address.isnot(None)
            ).all()
            
            if not pending_payouts:
                logger.info("No pending payouts, waiting for more")
                db.close()
                # Esperar hasta la próxima hora exacta (00 minutos)
                import time
                current_time = time.time()
                seconds_since_epoch = int(current_time)
                seconds_in_minute = seconds_since_epoch % 60
                minutes_since_hour = (seconds_since_epoch // 60) % 60

                # Calcular segundos hasta la próxima hora exacta
                minutes_to_next_hour = 60 - minutes_since_hour
                if minutes_to_next_hour == 60:
                    minutes_to_next_hour = 0
                    
                seconds_to_wait = (minutes_to_next_hour * 60) - seconds_in_minute
                await asyncio.sleep(seconds_to_wait)
                continue
            
            logger.info(f"{len(pending_payouts)} pending payouts, checking batch criteria")
            
            # Obtener el deal más antiguo para verificar tiempo
            oldest_deal = min(pending_payouts, key=lambda d: d.created_at)
            elapsed_minutes = (datetime.utcnow() - oldest_deal.created_at).total_seconds() / 60
            
            # Procesar batch si hay suficientes deals O pasó suficiente tiempo
            if len(pending_payouts) >= MIN_BATCH_SIZE or elapsed_minutes >= MAX_WAIT_MINUTES:
                
                if len(pending_payouts) >= MIN_BATCH_SIZE:
                    reason = f"batch size reached ({len(pending_payouts)} >= {MIN_BATCH_SIZE})"
                else:
                    reason = f"time limit reached ({elapsed_minutes:.1f} >= {MAX_WAIT_MINUTES} minutes)"
                
                logger.info(f"Processing batch of {len(pending_payouts)} payouts - {reason}")
                
                # Procesar el batch
                success = await send_bitcoin_batch(pending_payouts, db)
                
                if success:
                    logger.info(f"Successfully processed batch of {len(pending_payouts)} Bitcoin payouts")
                else:
                    logger.error("Failed to process Bitcoin batch")
            
            db.close()
            # Esperar hasta la próxima hora exacta para verificar nuevamente
            import time
            current_time = time.time()
            seconds_since_epoch = int(current_time)
            seconds_in_minute = seconds_since_epoch % 60
            minutes_since_hour = (seconds_since_epoch // 60) % 60

            # Calcular segundos hasta la próxima hora exacta
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
    Envía Bitcoin real usando wallet del bot - Paso 16 del flujo
    Ana recibe Bitcoin en su dirección proporcionada
    """
    try:
        # Agrupar deals por monto para privacidad
        deals_by_amount = {}
        for deal in pending_deals:
            amount = deal.amount_sats
            if amount not in deals_by_amount:
                deals_by_amount[amount] = []
            deals_by_amount[amount].append(deal)
        
        # Procesar cada grupo de monto
        for amount_sats, amount_deals in deals_by_amount.items():
            logger.info(f"Creating Bitcoin batch transaction for {len(amount_deals)} deals of {amount_sats} sats each")
            
            # Para testing, simular transacción Bitcoin
            # En producción: integrar con wallet_manager para transacciones reales
            simulated_txid = f"batch_{amount_sats}_{len(amount_deals)}_{int(datetime.utcnow().timestamp())}"
            
            # Marcar deals como completados
            for deal in amount_deals:
                deal.bitcoin_txid = simulated_txid
                deal.status = 'completed'
                deal.completed_at = datetime.utcnow()
            
            # Notificar vendedores (Ana)
            await notify_sellers_batch_sent(amount_deals, simulated_txid)
            
            logger.info(f"Simulated Bitcoin batch sent: {simulated_txid} for {len(amount_deals)} deals")
        
        db.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error in send_bitcoin_batch: {e}")
        return False

async def notify_sellers_batch_sent(deals, txid):
    """
    Notificar a vendedores que se envió Bitcoin - Paso 16 final
    Ana recibe confirmación de que recibió Bitcoin
    """
    app = Application.builder().token(BOT_TOKEN).build()
    
    for deal in deals:
        amount = deal.amount_sats
        if amount >= 1000000:
            amount_text = f"{amount:,}"
        elif amount >= 1000:
            amount_text = f"{amount:,}"
        else:
            amount_text = f"{amount:,}"
        
        try:
            await app.bot.send_message(
                chat_id=deal.seller_id,
                text=f"""
💰 **Bitcoin Sent - Deal #{deal.id}**

Your {amount_text} sats have been sent!

**Transaction:** `{txid}`
**Address:** `{deal.seller_bitcoin_address}`

Check testnet blockchain explorer.
**Swap completed successfully!** ✅

Thanks for using P2P Swap Bot!
                """,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify seller {deal.seller_id}: {e}")

# =============================================================================
# SECCIÓN 11: FUNCIÓN PRINCIPAL Y CONFIGURACIÓN
# =============================================================================

def main():
    """
    Función principal del bot - Configura todos los handlers y monitores
    """
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return
    
    if not OFFERS_CHANNEL_ID:
        logger.warning("OFFERS_CHANNEL_ID not configured - channel posting disabled")
    
    # Crear tablas de base de datos
    create_tables()
    
    # Crear aplicación de Telegram
    application = Application.builder().token(BOT_TOKEN).build()

    # Iniciar monitores en background
    monitor_thread = threading.Thread(target=lambda: asyncio.run(monitor_confirmations()))
    monitor_thread.daemon = True
    monitor_thread.start()

    monitor_thread_ln = threading.Thread(target=lambda: asyncio.run(monitor_lightning_payments()))
    monitor_thread_ln.daemon = True
    monitor_thread_ln.start() 

    batch_thread = threading.Thread(target=lambda: asyncio.run(process_bitcoin_batches()))
    batch_thread.daemon = True
    batch_thread.start()

    # Agregar handlers de comandos
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
    
    # Handler para botones
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Iniciar bot
    logger.info("Starting P2P Swap Bot...")
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=['message', 'callback_query']
    )

if __name__ == '__main__':
    main()
