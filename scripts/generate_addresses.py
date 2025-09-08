#!/usr/bin/env python3
"""
Generate Bitcoin testnet addresses for P2P Swap Bot escrow
"""

from bitcoinlib.keys import Key
import os

def generate_testnet_addresses():
    """Generate testnet addresses for escrow"""
    
    print("🔑 Generating Bitcoin testnet addresses for P2P Swap Bot")
    print("=" * 60)
    
    # Generate addresses for different amounts
    amounts = [10000, 50000, 100000, 500000, 1000000]
    addresses = {}
    
    for amount in amounts:
        # Generate random private key
        key = Key(network='testnet')
        
        # Get address
        address = key.address()
        
        # Store for .env file
        if amount >= 1000000:
            key_name = f"BITCOIN_ADDRESS_{amount//1000000}M"
        elif amount >= 1000:
            key_name = f"BITCOIN_ADDRESS_{amount//1000}K"
        else:
            key_name = f"BITCOIN_ADDRESS_{amount}"
            
        addresses[key_name] = {
            'address': address,
            'private_key': key.hex(),
            'amount': amount
        }
        
        print(f"📍 {amount:,} sats: {address}")
    
    print("\n🔐 PRIVATE KEYS (KEEP SECURE!):")
    print("=" * 60)
    
    for key_name, data in addresses.items():
        print(f"{key_name}_PRIVATE={data['private_key']}")
    
    print("\n📝 Add to your .env file:")
    print("=" * 60)
    
    for key_name, data in addresses.items():
        print(f"{key_name}={data['address']}")
    
    print("\n⚠️  SECURITY WARNINGS:")
    print("- Store private keys securely")
    print("- These are for TESTNET only")
    print("- Never use these keys on mainnet")
    print("- Backup private keys before using")
    
    return addresses

if __name__ == "__main__":
    addresses = generate_testnet_addresses()
