#!/usr/bin/env python3
"""
===============================================================================
LIGHTNING UTILS - LND Integration for P2P Swap Bot
===============================================================================
Functions to interact with LND for Lightning payment verification
Uses REST API for simplicity and reliability
"""

import os
import json
import base64
import requests
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# =============================================================================
# LND CONFIGURATION
# =============================================================================

LND_REST_HOST = os.getenv('LND_REST_HOST', 'localhost:8080')
LND_TLS_CERT_PATH = os.getenv('LND_TLS_CERT_PATH', '~/.lnd/tls.cert')
LND_MACAROON_PATH = os.getenv('LND_MACAROON_PATH', '~/.lnd/data/chain/bitcoin/testnet/readonly.macaroon')

class LNDClient:
    """Client for connecting to LND via REST API"""
    
    def __init__(self):
        self.base_url = f"https://{LND_REST_HOST}"
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self):
        """Setup SSL and authentication for LND REST API"""
        try:
            # Setup TLS certificate
            tls_cert_path = os.path.expanduser(LND_TLS_CERT_PATH)
            if os.path.exists(tls_cert_path):
                self.session.verify = tls_cert_path
            else:
                logger.warning(f"TLS cert not found: {tls_cert_path}")
                self.session.verify = False
            
            # Setup macaroon authentication
            macaroon_path = os.path.expanduser(LND_MACAROON_PATH)
            if os.path.exists(macaroon_path):
                with open(macaroon_path, 'rb') as f:
                    macaroon_bytes = f.read()
                    macaroon_hex = macaroon_bytes.hex()
                
                self.session.headers.update({
                    'Grpc-Metadata-macaroon': macaroon_hex
                })
                logger.info("LND authentication configured successfully")
            else:
                logger.error(f"Macaroon not found: {macaroon_path}")
                
        except Exception as e:
            logger.error(f"Failed to setup LND session: {e}")
    
    def get_info(self) -> Optional[Dict]:
        """Get node information from LND"""
        try:
            response = self.session.get(f"{self.base_url}/v1/getinfo")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get LND info: {e}")
            return None
    
    def decode_payment_request(self, payment_request: str) -> Optional[Dict]:
        """Decode Lightning invoice to extract payment hash and details"""
        try:
            response = self.session.get(
                f"{self.base_url}/v1/payreq/{payment_request}"
            )
            response.raise_for_status()
            decoded = response.json()
            
            return {
                'payment_hash': decoded.get('payment_hash'),
                'destination': decoded.get('destination'),
                'num_satoshis': int(decoded.get('num_satoshis', 0)),
                'timestamp': int(decoded.get('timestamp', 0)),
                'expiry': int(decoded.get('expiry', 0)),
                'description': decoded.get('description', ''),
                'cltv_expiry': int(decoded.get('cltv_expiry', 0))
            }
        except Exception as e:
            logger.error(f"Failed to decode payment request: {e}")
            return None
    
    def lookup_invoice(self, payment_hash: str) -> Optional[Dict]:
        """Look up invoice by payment hash to check payment status"""
        try:
            # Convert hex payment hash to base64url for REST API
            payment_hash_bytes = bytes.fromhex(payment_hash)
            payment_hash_b64 = base64.urlsafe_b64encode(payment_hash_bytes).decode().rstrip('=')
            
            response = self.session.get(
                f"{self.base_url}/v1/invoice/{payment_hash_b64}"
            )
            response.raise_for_status()
            invoice_data = response.json()
            
            return {
                'settled': invoice_data.get('settled', False),
                'settle_date': int(invoice_data.get('settle_date', 0)),
                'value': int(invoice_data.get('value', 0)),
                'memo': invoice_data.get('memo', ''),
                'creation_date': int(invoice_data.get('creation_date', 0)),
                'payment_request': invoice_data.get('payment_request', ''),
                'state': invoice_data.get('state', 'OPEN')  # OPEN, SETTLED, CANCELED, ACCEPTED
            }
        except Exception as e:
            logger.error(f"Failed to lookup invoice {payment_hash}: {e}")
            return None

# =============================================================================
# HIGH-LEVEL FUNCTIONS FOR BOT INTEGRATION
# =============================================================================

def check_lnd_connection() -> bool:
    """Check if LND is available and responding"""
    try:
        client = LNDClient()
        info = client.get_info()
        if info and info.get('synced_to_chain'):
            logger.info(f"LND connected: {info.get('alias', 'Unknown')}")
            return True
        else:
            logger.warning("LND not fully synced")
            return False
    except Exception as e:
        logger.error(f"LND connection failed: {e}")
        return False

def extract_payment_hash_from_invoice(invoice: str) -> Optional[str]:
    """Extract payment hash from Lightning invoice"""
    try:
        client = LNDClient()
        decoded = client.decode_payment_request(invoice)
        if decoded:
            return decoded.get('payment_hash')
        return None
    except Exception as e:
        logger.error(f"Failed to extract payment hash: {e}")
        return None

def check_lightning_payment_status(payment_hash: str) -> bool:
    """
    Check if a Lightning payment has been completed
    Returns True if payment is settled, False otherwise
    """
    try:
        client = LNDClient()
        invoice_data = client.lookup_invoice(payment_hash)
        
        if invoice_data:
            is_settled = invoice_data.get('settled', False)
            state = invoice_data.get('state', 'OPEN')
            
            logger.info(f"Payment {payment_hash[:10]}... status: {state}, settled: {is_settled}")
            
            return is_settled and state == 'SETTLED'
        else:
            logger.warning(f"Invoice not found for payment hash: {payment_hash[:10]}...")
            return False
            
    except Exception as e:
        logger.error(f"Failed to check payment status: {e}")
        return False

def validate_lightning_invoice(invoice: str) -> Tuple[bool, Optional[Dict]]:
    """
    Validate Lightning invoice and return decoded information
    Returns (is_valid, invoice_info)
    """
    try:
        if not invoice or not isinstance(invoice, str):
            return False, None
            
        # Basic format check
        if not invoice.startswith(('lnbc', 'lntb', 'lnbcrt')):
            return False, None
        
        client = LNDClient()
        decoded = client.decode_payment_request(invoice)
        
        if decoded and decoded.get('payment_hash'):
            return True, decoded
        else:
            return False, None
            
    except Exception as e:
        logger.error(f"Invoice validation failed: {e}")
        return False, None

# =============================================================================
# TESTING AND DIAGNOSTICS
# =============================================================================

def test_lnd_integration():
    """Test LND integration - for debugging purposes"""
    print("Testing LND Integration...")
    
    # Test connection
    if check_lnd_connection():
        print("✅ LND connection successful")
    else:
        print("❌ LND connection failed")
        return
    
    # Test node info
    client = LNDClient()
    info = client.get_info()
    if info:
        print(f"✅ Node info: {info.get('alias')} - {info.get('identity_pubkey')[:10]}...")
        print(f"   Synced to chain: {info.get('synced_to_chain')}")
        print(f"   Synced to graph: {info.get('synced_to_graph')}")
        print(f"   Block height: {info.get('block_height')}")
    else:
        print("❌ Failed to get node info")

if __name__ == "__main__":
    # Run tests if executed directly
    test_lnd_integration()
