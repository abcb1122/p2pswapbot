#!/usr/bin/env python3
"""
===============================================================================
LNPROXY UTILS - Privacy Integration for Lightning Invoices
===============================================================================
Integrates with lnproxy.org service for invoice privacy masking
"""

import requests
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

LNPROXY_BASE_URL = "https://lnproxy.lnemail.net"

class LNProxyClient:
    """Client for lnproxy.org invoice masking service"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'P2PSwapBot/1.0',
            'Content-Type': 'application/json'
        })
    
    def check_service_availability(self) -> bool:
        """Check if lnproxy service is available"""
        try:
            response = self.session.get(f"{LNPROXY_BASE_URL}/spec", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"lnproxy service check failed: {e}")
            return False
    
    def create_wrapped_invoice(self, original_invoice: str) -> Optional[Dict]:
        """
        Create a privacy-wrapped invoice using lnproxy
        Returns dict with wrapped_invoice and tracking info, or None if failed
        """
        try:
            # First check service availability
            if not self.check_service_availability():
                logger.warning("lnproxy service unavailable")
                return None
            
            # Prepare request payload based on lnproxy API
            payload = {
                "invoice": original_invoice,
                
            }
            
            response = self.session.post(
                f"{LNPROXY_BASE_URL}/spec",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract the wrapped invoice and metadata
                return {
                    'status': 'success',
                    'original_invoice': original_invoice,
                    'wrapped_invoice': data.get('proxy_invoice'),
                    'proxy_id': data.get('id'),
                    'expires_at': data.get('expires_at'),
                    'privacy_enabled': True
                }
            else:
                logger.error(f"lnproxy API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create wrapped invoice: {e}")
            return None
    
    def get_payment_status(self, proxy_id: str) -> Optional[Dict]:
        """Check payment status of wrapped invoice"""
        try:
            response = self.session.get(
                f"{LNPROXY_BASE_URL}/status/{proxy_id}",
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Status check failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to check payment status: {e}")
            return None

# =============================================================================
# HIGH-LEVEL FUNCTIONS FOR BOT INTEGRATION
# =============================================================================

def wrap_invoice_for_privacy(original_invoice: str) -> Tuple[bool, Dict]:
    """
    Attempt to wrap invoice with lnproxy for privacy
    Returns (success, result_dict)
    
    result_dict contains:
    - If success: wrapped_invoice, original_invoice, proxy_id, privacy_enabled=True
    - If failed: original_invoice, privacy_enabled=False, error_message
    """
    try:
        client = LNProxyClient()
        
        # Try to create wrapped invoice
        result = client.create_wrapped_invoice(original_invoice)
        
        if result:
            logger.info(f"Successfully created wrapped invoice via lnproxy")
            return True, result
        else:
            # Return fallback with original invoice
            fallback_result = {
                'status': 'fallback',
                'original_invoice': original_invoice,
                'wrapped_invoice': original_invoice,  # Same as original
                'privacy_enabled': False,
                'error_message': 'lnproxy service unavailable'
            }
            logger.warning("lnproxy failed, falling back to original invoice")
            return False, fallback_result
            
    except Exception as e:
        logger.error(f"Error in wrap_invoice_for_privacy: {e}")
        fallback_result = {
            'status': 'error',
            'original_invoice': original_invoice,
            'wrapped_invoice': original_invoice,
            'privacy_enabled': False,
            'error_message': str(e)
        }
        return False, fallback_result

def test_lnproxy_integration():
    """Test lnproxy integration - for debugging"""
    print("Testing lnproxy integration...")
    
    client = LNProxyClient()
    
    # Test service availability
    if client.check_service_availability():
        print("✅ lnproxy service is available")
    else:
        print("❌ lnproxy service is unavailable")
        return
    
    # Test with a sample testnet invoice (you'll need a real one for testing)
    sample_invoice = "lntb100u1p3xnhl2pp5..."  # This would be a real testnet invoice
    
    success, result = wrap_invoice_for_privacy(sample_invoice)
    
    if success:
        print(f"✅ Invoice wrapping successful")
        print(f"   Privacy enabled: {result.get('privacy_enabled')}")
        print(f"   Proxy ID: {result.get('proxy_id')}")
    else:
        print(f"❌ Invoice wrapping failed: {result.get('error_message')}")

if __name__ == "__main__":
    test_lnproxy_integration()
