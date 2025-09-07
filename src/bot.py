#!/usr/bin/env python3
"""
P2P Swap Bot - Telegram Bot para intercambios Lightning <-> Bitcoin onchain
"""

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token del bot
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /start - Registro de usuario"""
    user = update.effective_user
    
    welcome_message = f"""
🚀 ¡Bienvenido a P2P Swap Bot, {user.first_name}!

Este bot te permite intercambiar Lightning sats por Bitcoin onchain de forma P2P.

📋 **Comandos disponibles:**
/start - Iniciar y registrarse
/help - Ver ayuda
/perfil - Ver tu perfil
/vender - Crear oferta de venta Lightning
/comprar - Crear oferta de compra Lightning

🔧 **Estado:** MVP en desarrollo
🔗 **Repositorio:** github.com/abcb1122/p2pswapbot

¡Empecemos! Usa /help para más información.
    """
    
    await update.message.reply_text(welcome_message)
    logger.info(f"Usuario {user.id} ({user.username}) inició el bot")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /help"""
    help_text = """
📖 **Ayuda - P2P Swap Bot**

🔄 **¿Cómo funciona?**
1. Usuarios crean ofertas (vender/comprar Lightning sats)
2. Otros usuarios toman las ofertas
3. Se crea un escrow multisig automático
4. Intercambio seguro Lightning ↔ Bitcoin onchain

⚡ **Comandos:**
/start - Registrarse en el bot
/perfil - Ver tu perfil y configuración
/vender [cantidad] - Vender Lightning sats por Bitcoin onchain
/comprar [cantidad] - Comprar Lightning sats con Bitcoin onchain
/ofertas - Ver ofertas disponibles

🛡️ **Seguridad:**
- Escrow multisig 2-of-3
- Sin custodia de fondos
- Sistema de reputación

❓ **Soporte:** @tu_usuario_admin
    """
    
    await update.message.reply_text(help_text)

async def perfil(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /perfil"""
    user = update.effective_user
    
    perfil_text = f"""
👤 **Tu Perfil**

🆔 ID: {user.id}
👥 Usuario: @{user.username or 'No configurado'}
📝 Nombre: {user.first_name}

📊 **Estadísticas:**
- Deals completados: 0
- Reputación: ⭐⭐⭐⭐⭐ (Nuevo usuario)
- Volumen total: 0 sats

🔧 **Configuración:**
- Dirección Bitcoin: No configurada
- Estado: Activo

💡 Configura tu dirección Bitcoin con /config
    """
    
    await update.message.reply_text(perfil_text)

def main():
    """Función principal del bot"""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN no configurado en .env")
        return
    
    # Crear aplicación
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Agregar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("perfil", perfil))
    
    # Iniciar bot
    logger.info("Iniciando P2P Swap Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
