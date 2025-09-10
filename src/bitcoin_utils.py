"""
===============================================================================
BITCOIN UTILITIES FOR P2P SWAP BOT
===============================================================================
Maneja operaciones Bitcoin testnet, validación de direcciones y monitoreo de transacciones
Optimizado para principiantes - Fácil de modificar y entender
"""

import os
import requests
import logging
import time
import base64
import binascii
from datetime import datetime

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURACIÓN - MODIFICAR AQUÍ PARA CAMBIOS RÁPIDOS
# =============================================================================

# Red Bitcoin (desde .env)
NETWORK = os.getenv('BITCOIN_NETWORK', 'testnet')

# APIs de blockchain - CAMBIAR AQUÍ PARA USAR DIFERENTES APIS
if NETWORK == 'testnet':
    BLOCKSTREAM_API = "https://blockstream.info/testnet/api"
    MEMPOOL_API = "https://mempool.space/testnet/api"
else:
    BLOCKSTREAM_API = "https://blockstream.info/api"
    MEMPOOL_API = "https://mempool.space/api"

# Configuración de timeouts y reintentos
API_TIMEOUT = 10        # Timeout para requests API (segundos)
RETRY_ATTEMPTS = 3      # Número de reintentos para APIs
MONITOR_INTERVAL = 30   # Intervalo de monitoreo (segundos)

# =============================================================================
# CLASE PRINCIPAL - MANEJO DE BITCOIN
# =============================================================================

class BitcoinManager:
    """
    Maneja todas las operaciones Bitcoin para el bot de swap
    Incluye validación, monitoreo y verificación de pagos
    """
    
    def __init__(self):
        self.network = NETWORK
        logger.info(f"Bitcoin manager initialized for {self.network}")
        
    def validate_address(self, address: str) -> bool:
        """
        Valida formato de dirección Bitcoin
        Soporta formatos testnet y mainnet
        """
        try:
            if not address or len(address) < 26 or len(address) > 62:
                return False
                
            # Validación para testnet
            if self.network == 'testnet':
                valid_prefixes = ('tb1', 'bc1', '2', 'm', 'n')
                return address.startswith(valid_prefixes)
            else:
                # Validación para mainnet
                valid_prefixes = ('bc1', '1', '3')
                return address.startswith(valid_prefixes)
                
        except Exception as e:
            logger.error(f"Error validating address {address}: {e}")
            return False
    
    def get_address_balance(self, address: str) -> int:
        """
        Obtiene balance de dirección en satoshis usando Blockstream API
        """
        try:
            for attempt in range(RETRY_ATTEMPTS):
                try:
                    response = requests.get(
                        f"{BLOCKSTREAM_API}/address/{address}", 
                        timeout=API_TIMEOUT
                    )
                    if response.status_code == 200:
                        data = response.json()
                        balance = data.get('chain_stats', {}).get('funded_txo_sum', 0)
                        logger.info(f"Address {address} balance: {balance} sats")
                        return balance
                    else:
                        logger.warning(f"API returned status {response.status_code} for address {address}")
                        
                except requests.RequestException as e:
                    logger.warning(f"API attempt {attempt + 1} failed: {e}")
                    if attempt < RETRY_ATTEMPTS - 1:
                        time.sleep(2)  # Esperar antes de reintentar
                        
            return 0
        except Exception as e:
            logger.error(f"Error getting balance for {address}: {e}")
            return 0
    
    def get_address_utxos(self, address: str) -> list:
        """
        Obtiene UTXOs para una dirección
        """
        try:
            for attempt in range(RETRY_ATTEMPTS):
                try:
                    response = requests.get(
                        f"{BLOCKSTREAM_API}/address/{address}/utxo", 
                        timeout=API_TIMEOUT
                    )
                    if response.status_code == 200:
                        utxos = response.json()
                        logger.info(f"Found {len(utxos)} UTXOs for {address}")
                        return utxos
                    else:
                        logger.warning(f"API returned status {response.status_code} for UTXOs {address}")
                        
                except requests.RequestException as e:
                    logger.warning(f"UTXO API attempt {attempt + 1} failed: {e}")
                    if attempt < RETRY_ATTEMPTS - 1:
                        time.sleep(2)
                        
            return []
        except Exception as e:
            logger.error(f"Error getting UTXOs for {address}: {e}")
            return []
    
    def get_transaction_info(self, txid: str) -> dict:
        """
        Obtiene información de transacción
        """
        try:
            for attempt in range(RETRY_ATTEMPTS):
                try:
                    response = requests.get(
                        f"{BLOCKSTREAM_API}/tx/{txid}", 
                        timeout=API_TIMEOUT
                    )
                    if response.status_code == 200:
                        tx_data = response.json()
                        logger.info(f"Transaction {txid} found")
                        return tx_data
                    else:
                        logger.warning(f"API returned status {response.status_code} for tx {txid}")
                        
                except requests.RequestException as e:
                    logger.warning(f"TX API attempt {attempt + 1} failed: {e}")
                    if attempt < RETRY_ATTEMPTS - 1:
                        time.sleep(2)
                        
            return {}
        except Exception as e:
            logger.error(f"Error getting transaction info for {txid}: {e}")
            return {}
    
    def get_transaction_confirmations(self, txid: str) -> int:
        """
        Obtiene número de confirmaciones para una transacción
        FUNCIÓN CLAVE: Usada por el bot para verificar confirmaciones Bitcoin
        """
        try:
            tx_data = self.get_transaction_info(txid)
            if not tx_data:
                logger.warning(f"No transaction data found for {txid}")
                return 0
                
            # Verificar si la transacción está confirmada
            if 'status' in tx_data and tx_data['status'].get('confirmed'):
                # Obtener altura actual del blockchain
                for attempt in range(RETRY_ATTEMPTS):
                    try:
                        tip_response = requests.get(
                            f"{BLOCKSTREAM_API}/blocks/tip/height", 
                            timeout=API_TIMEOUT
                        )
                        if tip_response.status_code == 200:
                            current_height = int(tip_response.text)
                            tx_height = tx_data['status']['block_height']
                            confirmations = current_height - tx_height + 1
                            logger.info(f"TX {txid}: {confirmations} confirmations (height {tx_height}/{current_height})")
                            return confirmations
                    except requests.RequestException as e:
                        logger.warning(f"Block height API attempt {attempt + 1} failed: {e}")
                        if attempt < RETRY_ATTEMPTS - 1:
                            time.sleep(2)
            else:
                logger.info(f"TX {txid} not confirmed yet (in mempool)")
                return 0
                
        except Exception as e:
            logger.error(f"Error getting confirmations for {txid}: {e}")
            return 0
    
    def verify_payment_to_address(self, address: str, expected_amount: int, txid: str = None) -> dict:
        """
        Verifica si se hizo un pago a una dirección
        FUNCIÓN CLAVE: Usada por el bot para verificar depósitos Bitcoin
        """
        try:
            utxos = self.get_address_utxos(address)
            
            for utxo in utxos:
                # Si se proporciona txid, solo verificar esa transacción específica
                if txid and utxo.get('txid') != txid:
                    continue
                    
                # Verificar si el monto coincide
                if utxo.get('value', 0) == expected_amount:
                    confirmations = self.get_transaction_confirmations(utxo['txid'])
                    
                    result = {
                        'found': True,
                        'txid': utxo['txid'],
                        'amount': utxo['value'],
                        'confirmations': confirmations,
                        'confirmed': confirmations >= 3,
                        'vout': utxo.get('vout', 0)
                    }
                    
                    logger.info(f"Payment verification result: {result}")
                    return result
            
            # No se encontró pago matching
            return {
                'found': False,
                'txid': txid,
                'amount': 0,
                'confirmations': 0,
                'confirmed': False,
                'error': 'Payment not found or amount mismatch'
            }
            
        except Exception as e:
            logger.error(f"Error verifying payment to {address}: {e}")
            return {
                'found': False,
                'error': str(e),
                'confirmations': 0,
                'confirmed': False
            }
    
    def monitor_address(self, address: str, expected_amount: int, timeout: int = 3600) -> dict:
        """
        Monitorea dirección para transacción entrante
        Retorna información detallada del pago cuando se encuentra
        """
        start_time = time.time()
        logger.info(f"Monitoring {address} for {expected_amount} sats (timeout: {timeout}s)")
        
        while time.time() - start_time < timeout:
            result = self.verify_payment_to_address(address, expected_amount)
            
            if result['found'] and result['confirmed']:
                logger.info(f"Payment confirmed: {result}")
                return result
            elif result['found']:
                logger.info(f"Payment found but not confirmed: {result['confirmations']}/3")
                return result
            
            time.sleep(MONITOR_INTERVAL)
        
        logger.warning(f"Timeout waiting for payment to {address}")
        return {
            'found': False,
            'error': 'Timeout',
            'confirmed': False,
            'timeout': True
        }

# =============================================================================
# FUNCIONES LIGHTNING NETWORK
# =============================================================================

def extract_payment_hash_from_invoice(invoice):
    """Extract payment hash from Lightning invoice using LND"""
    from lightning_utils import extract_payment_hash_from_invoice as lnd_extract
    return lnd_extract(invoice)

def check_lightning_payment_status(payment_hash):
    """Check if Lightning payment is settled using LND"""
    from lightning_utils import check_lightning_payment_status as lnd_check
    return lnd_check(payment_hash)

    """
    Verifica si el pago Lightning fue completado
    FUNCIÓN CLAVE: Usada por el bot para verificar pagos Lightning
    
    NOTA: En testing usa timeout manual, en producción integrar con nodo Lightning
    """
    try:
        logger.info(f"Checking Lightning payment status for hash: {payment_hash}")
        
        # En testing: siempre retorna False para usar override manual
        # En producción: integrar con LND, CLN o servicio Lightning
        
        # Placeholder para integración futura:
        # - Conectar con nodo Lightning via gRPC/REST
        # - Verificar estado de invoice usando payment_hash
        # - Retornar True si el pago fue exitoso
        
        # Para testing, siempre usar override manual después de timeout
        return False
        
    except Exception as e:
        logger.error(f"Error checking Lightning payment: {e}")
        return False

# =============================================================================
# FUNCIONES PÚBLICAS - INTERFACE PARA EL BOT
# =============================================================================

# Instancia global del manager
bitcoin_manager = BitcoinManager()

def validate_bitcoin_address(address: str) -> bool:
    """
    FUNCIÓN PÚBLICA: Validar dirección Bitcoin
    Usada por el bot en comando /address
    """
    return bitcoin_manager.validate_address(address)

def get_address_balance(address: str) -> int:
    """
    FUNCIÓN PÚBLICA: Obtener balance de dirección
    """
    return bitcoin_manager.get_address_balance(address)

def verify_payment(address: str, amount: int, txid: str = None) -> dict:
    """
    FUNCIÓN PÚBLICA: Verificar pago a dirección
    """
    return bitcoin_manager.verify_payment_to_address(address, amount, txid)

def get_confirmations(txid: str) -> int:
    """
    FUNCIÓN PÚBLICA: Obtener confirmaciones de transacción
    Usada por el bot para monitorear confirmaciones Bitcoin
    """
    return bitcoin_manager.get_transaction_confirmations(txid)

def monitor_payment(address: str, amount: int, timeout: int = 3600) -> dict:
    """
    FUNCIÓN PÚBLICA: Monitorear pago a dirección
    """
    return bitcoin_manager.monitor_address(address, amount, timeout)

def get_transaction_info(txid: str) -> dict:
    """
    FUNCIÓN PÚBLICA: Obtener información de transacción
    """
    return bitcoin_manager.get_transaction_info(txid)

# =============================================================================
# FUNCIONES DE TESTING Y DEBUG
# =============================================================================

def test_bitcoin_functions():
    """
    Función de testing para verificar que las APIs funcionan
    Ejecutar para debuggear problemas de conectividad
    """
    logger.info("Testing Bitcoin utilities...")
    
    # Test de validación de direcciones
    test_addresses = [
        "tb1q9xv6kf5n4q7wzvgaq0lu0y5kln6cjuy3wg0y6d",  # Testnet válida
        "invalid_address",  # Inválida
        "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"  # Mainnet válida
    ]
    
    for addr in test_addresses:
        valid = validate_bitcoin_address(addr)
        logger.info(f"Address {addr[:20]}... is valid: {valid}")
    
    # Test de conexión API
    try:
        response = requests.get(f"{BLOCKSTREAM_API}/blocks/tip/height", timeout=5)
        if response.status_code == 200:
            logger.info(f"API connection successful. Current block: {response.text}")
        else:
            logger.error(f"API connection failed: {response.status_code}")
    except Exception as e:
        logger.error(f"API test failed: {e}")
    
    logger.info("Bitcoin utilities test completed")

# =============================================================================
# CONFIGURACIÓN DE LOGGING
# =============================================================================

def setup_bitcoin_logging():
    """
    Configurar logging específico para funciones Bitcoin
    """
    bitcoin_logger = logging.getLogger(__name__)
    bitcoin_logger.setLevel(logging.INFO)
    
    if not bitcoin_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        bitcoin_logger.addHandler(handler)
    
    return bitcoin_logger

# Configurar logging al importar el módulo
setup_bitcoin_logging()

# =============================================================================
# NOTAS PARA PRODUCCIÓN
# =============================================================================
"""
PARA MIGRAR A MAINNET:
1. Cambiar BITCOIN_NETWORK=mainnet en .env
2. Verificar direcciones Bitcoin reales en FIXED_ADDRESSES
3. Integrar nodo Lightning real para check_lightning_payment_status()
4. Ajustar timeouts para red principal (más lenta que testnet)
5. Configurar APIs de backup en caso de que Blockstream falle

PARA INTEGRACIÓN LIGHTNING:
1. Instalar librería Lightning (lnd-grpc, python-clightning)
2. Configurar conexión a nodo Lightning
3. Implementar verificación real de invoices
4. Manejar errores de red Lightning

MONITOREO MEJORADO:
1. Usar webhooks en lugar de polling para mejor eficiencia
2. Implementar cache de resultados de API
3. Agregar métricas de performance
"""
