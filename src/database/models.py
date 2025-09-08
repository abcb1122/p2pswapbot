"""
===============================================================================
MODELOS DE BASE DE DATOS PARA P2P SWAP BOT
===============================================================================
Define la estructura de datos para usuarios, ofertas y deals
Optimizado para principiantes - Fácil de entender y modificar
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

# =============================================================================
# MODELO USER - INFORMACIÓN DE USUARIOS DEL BOT
# =============================================================================

class User(Base):
    """
    Modelo de Usuario - Almacena información de usuarios de Telegram
    Incluye estadísticas de reputación y historial de deals
    """
    __tablename__ = 'users'
    
    # Identificadores principales
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(50))
    first_name = Column(String(100))
    
    # Información Bitcoin
    bitcoin_address = Column(String(100))  # Dirección preferida del usuario
    
    # Estadísticas y reputación
    reputation_score = Column(Float, default=5.0)  # Calificación de 1-5 estrellas
    total_deals = Column(Integer, default=0)        # Deals completados exitosamente
    total_volume = Column(Integer, default=0)       # Volumen total en sats
    
    # Control de cuenta
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_active = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_banned = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"

# =============================================================================
# MODELO OFFER - OFERTAS DE SWAP CREADAS POR USUARIOS
# =============================================================================

class Offer(Base):
    """
    Modelo de Oferta - Ofertas de swap creadas por usuarios
    Puede ser 'swapout' (Lightning→Bitcoin) o 'swapin' (Bitcoin→Lightning)
    """
    __tablename__ = 'offers'
    
    # Identificadores
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)  # telegram_id del creador
    
    # Detalles de la oferta
    offer_type = Column(String(10), nullable=False)  # 'swapout' o 'swapin'
    amount_sats = Column(Integer, nullable=False, index=True)
    rate = Column(Float, default=1.0)  # Tasa de cambio (normalmente 1:1)
    
    # Estados posibles: 'active', 'taken', 'completed', 'cancelled', 'expired'
    status = Column(String(20), default='active', index=True)
    
    # Control temporal
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    taken_by = Column(Integer, index=True)      # telegram_id de quien tomó la oferta
    taken_at = Column(DateTime)
    expires_at = Column(DateTime)               # Auto-expiración de ofertas
    
    def __repr__(self):
        return f"<Offer(id={self.id}, type={self.offer_type}, amount={self.amount_sats}, status={self.status})>"

# =============================================================================
# MODELO DEAL - INTERCAMBIOS ACTIVOS ENTRE USUARIOS
# =============================================================================

class Deal(Base):
    """
    Modelo de Deal/Intercambio - Representa un swap activo entre dos usuarios
    Contiene toda la información necesaria para completar el intercambio
    """
    __tablename__ = 'deals'
    
    # Identificadores principales
    id = Column(Integer, primary_key=True)
    offer_id = Column(Integer, nullable=False, index=True)
    
    # Participantes del deal
    seller_id = Column(Integer, nullable=False, index=True)  # Vende Lightning (en swapout)
    buyer_id = Column(Integer, nullable=False, index=True)   # Compra Lightning (en swapout)
    amount_sats = Column(Integer, nullable=False)
    
    # =============================================================================
    # INFORMACIÓN BITCOIN ONCHAIN
    # =============================================================================
    
    # Transacción de depósito del comprador
    buyer_bitcoin_txid = Column(String(100), index=True)     # TXID reportado por buyer
    bitcoin_confirmations = Column(Integer, default=0)       # Confirmaciones actuales
    
    # Dirección donde recibe el vendedor
    seller_bitcoin_address = Column(String(100))             # Dirección final de pago
    
    # Transacción de pago final (batch)
    bitcoin_txid = Column(String(100))                       # TXID del pago final al seller
    bitcoin_sent_at = Column(DateTime)                       # Timestamp del envío
    
    # =============================================================================
    # INFORMACIÓN LIGHTNING NETWORK
    # =============================================================================
    
    # Invoice del comprador para recibir Lightning
    lightning_invoice = Column(String(1000))                 # Invoice completo
    payment_hash = Column(String(100), index=True)          # Hash para verificación
    
    # Control de pago Lightning
    lightning_paid = Column(Boolean, default=False)
    lightning_paid_at = Column(DateTime)                     # Timestamp del pago
    lightning_preimage = Column(String(100))                 # Preimage del pago (opcional)
    
    # =============================================================================
    # ESTADOS Y CONTROL DEL DEAL
    # =============================================================================
    
    # Estado principal del deal
    status = Column(String(30), default='pending', index=True)
    
    """
    FLUJO DE ESTADOS DEL DEAL (SWAPOUT):
    
    1. 'pending'                      - Deal creado, esperando aceptación
    2. 'accepted'                     - Comprador aceptó, debe depositar Bitcoin
    3. 'bitcoin_sent'                 - Comprador reportó TXID, esperando confirmaciones
    4. 'bitcoin_confirmed'            - Bitcoin confirmado, esperando Lightning invoice
    5. 'lightning_invoice_received'   - Invoice recibido, esperando pago del vendedor
    6. 'awaiting_bitcoin_address'     - Lightning pagado, esperando dirección Bitcoin
    7. 'ready_for_batch'              - Listo para envío en batch
    8. 'completed'                    - Deal completado exitosamente
    9. 'cancelled'                    - Deal cancelado
    10. 'expired'                     - Deal expirado
    11. 'disputed'                    - En disputa (para futuro)
    """
    
    # Control temporal detallado
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    accepted_at = Column(DateTime)              # Cuando se aceptó el deal
    expires_at = Column(DateTime, index=True)   # Cuándo expira el deal
    completed_at = Column(DateTime)             # Cuando se completó
    
    # Campos adicionales para monitoreo
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_count = Column(Integer, default=0)    # Contador de errores para debugging
    notes = Column(String(500))                 # Notas internas del sistema
    
    def __repr__(self):
        return f"<Deal(id={self.id}, seller={self.seller_id}, buyer={self.buyer_id}, amount={self.amount_sats}, status={self.status})>"
    
    @property
    def is_expired(self):
        """Verifica si el deal ha expirado"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    @property
    def age_minutes(self):
        """Retorna la edad del deal en minutos"""
        return int((datetime.utcnow() - self.created_at).total_seconds() / 60)

# =============================================================================
# MODELO OPCIONAL: TRANSACTION LOG (PARA AUDITORÍA)
# =============================================================================

class TransactionLog(Base):
    """
    Log de transacciones para auditoría y debugging
    Registra todos los eventos importantes del sistema
    """
    __tablename__ = 'transaction_logs'
    
    id = Column(Integer, primary_key=True)
    deal_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    
    # Tipo de evento
    event_type = Column(String(50), nullable=False)  # 'deal_created', 'bitcoin_sent', etc.
    event_data = Column(String(1000))                # JSON con detalles del evento
    
    # Información de la transacción
    txid = Column(String(100))
    amount_sats = Column(Integer)
    
    # Control temporal
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<TransactionLog(id={self.id}, event={self.event_type}, deal_id={self.deal_id})>"

# =============================================================================
# CONFIGURACIÓN DE BASE DE DATOS
# =============================================================================

# URL de la base de datos desde variables de entorno
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///p2pswap.db')

# Configuración del engine con optimizaciones
if DATABASE_URL.startswith('sqlite'):
    # Configuración específica para SQLite
    engine = create_engine(
        DATABASE_URL,
        echo=False,  # Cambiar a True para ver todas las queries SQL
        pool_pre_ping=True,
        connect_args={
            "check_same_thread": False,  # Permitir acceso desde múltiples threads
            "timeout": 20  # Timeout para operaciones de base de datos
        }
    )
else:
    # Configuración para PostgreSQL/MySQL
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )

# Factory de sesiones
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# =============================================================================
# FUNCIONES PÚBLICAS PARA EL BOT
# =============================================================================

def create_tables():
    """
    Crear todas las tablas en la base de datos
    Ejecutar una vez al inicializar el bot
    """
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise

def get_db():
    """
    Obtener sesión de base de datos
    IMPORTANTE: El bot debe cerrar la sesión después de usarla
    """
    return SessionLocal()

def drop_all_tables():
    """
    FUNCIÓN PELIGROSA: Elimina todas las tablas
    Solo usar en desarrollo para reset completo
    """
    try:
        Base.metadata.drop_all(bind=engine)
        print("⚠️ All tables dropped")
    except Exception as e:
        print(f"❌ Error dropping tables: {e}")
        raise

def get_database_stats():
    """
    Obtener estadísticas básicas de la base de datos
    Útil para monitoring y debugging
    """
    db = get_db()
    try:
        stats = {
            'users': db.query(User).count(),
            'offers': db.query(Offer).count(),
            'deals': db.query(Deal).count(),
            'active_offers': db.query(Offer).filter(Offer.status == 'active').count(),
            'pending_deals': db.query(Deal).filter(Deal.status.in_(['pending', 'accepted', 'bitcoin_sent'])).count(),
            'completed_deals': db.query(Deal).filter(Deal.status == 'completed').count()
        }
        return stats
    finally:
        db.close()

# =============================================================================
# FUNCIONES DE UTILIDAD PARA DEBUGGING
# =============================================================================

def print_database_stats():
    """Imprimir estadísticas de la base de datos"""
    stats = get_database_stats()
    print("\n📊 Database Statistics:")
    print(f"   Users: {stats['users']}")
    print(f"   Total Offers: {stats['offers']} (Active: {stats['active_offers']})")
    print(f"   Total Deals: {stats['deals']} (Pending: {stats['pending_deals']}, Completed: {stats['completed_deals']})")

def cleanup_expired_deals():
    """
    Limpiar deals expirados
    Función de mantenimiento para ejecutar periódicamente
    """
    db = get_db()
    try:
        expired_deals = db.query(Deal).filter(
            Deal.expires_at < datetime.utcnow(),
            Deal.status.in_(['pending', 'accepted'])
        ).all()
        
        for deal in expired_deals:
            deal.status = 'expired'
            
            # Reactivar la oferta asociada
            offer = db.query(Offer).filter(Offer.id == deal.offer_id).first()
            if offer:
                offer.status = 'active'
                offer.taken_by = None
                offer.taken_at = None
        
        db.commit()
        print(f"🧹 Cleaned up {len(expired_deals)} expired deals")
        return len(expired_deals)
        
    finally:
        db.close()

# =============================================================================
# INICIALIZACIÓN AUTOMÁTICA
# =============================================================================

# Crear tablas automáticamente al importar el módulo (solo en desarrollo)
if os.getenv('AUTO_CREATE_TABLES', 'false').lower() == 'true':
    create_tables()

# =============================================================================
# NOTAS PARA PRODUCCIÓN
# =============================================================================
"""
MIGRACIÓN A PRODUCCIÓN:

1. POSTGRESQL:
   - Cambiar DATABASE_URL a PostgreSQL
   - Instalar psycopg2: pip install psycopg2-binary
   - Configurar pool de conexiones apropiado

2. ÍNDICES ADICIONALES:
   - Agregar índices compuestos para queries frecuentes
   - Optimizar queries de búsqueda de ofertas activas

3. RESPALDOS:
   - Configurar backups automáticos de la base de datos
   - Implementar replicación para alta disponibilidad

4. MONITOREO:
   - Agregar logging de queries lentas
   - Implementar métricas de performance de DB

5. MIGRATIONS:
   - Usar Alembic para migraciones de schema
   - Versionar cambios de base de datos
"""
