"""
Modelos de base de datos para P2P Swap Bot
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class User(Base):
    """Modelo de Usuario"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(50))
    first_name = Column(String(100))
    bitcoin_address = Column(String(100))
    reputation_score = Column(Float, default=5.0)
    total_deals = Column(Integer, default=0)
    total_volume = Column(Integer, default=0)  # en sats
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class Offer(Base):
    """Modelo de Oferta"""
    __tablename__ = 'offers'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)  # telegram_id del creador
    offer_type = Column(String(10), nullable=False)  # 'sell' o 'buy'
    amount_sats = Column(Integer, nullable=False)
    rate = Column(Float, default=1.0)
    status = Column(String(20), default='active')  # active, taken, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    taken_by = Column(Integer)  # telegram_id de quien tomó la oferta
    taken_at = Column(DateTime)

class Deal(Base):
    """Modelo de Deal/Intercambio"""
    __tablename__ = 'deals'
    
    id = Column(Integer, primary_key=True)
    offer_id = Column(Integer, nullable=False)
    seller_id = Column(Integer, nullable=False)  # quien vende Lightning
    buyer_id = Column(Integer, nullable=False)   # quien compra Lightning
    amount_sats = Column(Integer, nullable=False)
    multisig_address = Column(String(100))
    status = Column(String(20), default='pending')  # pending, funded, completed, disputed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

# Configurar base de datos
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///p2pswap.db')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Crear todas las tablas"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Obtener sesión de base de datos"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()
