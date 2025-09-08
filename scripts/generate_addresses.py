#!/usr/bin/env python3
"""
Generate Bitcoin testnet addresses for P2P Swap Bot escrow using mnemonic seed
"""

from bitcoinlib.mnemonic import Mnemonic
from bitcoinlib.wallets import Wallet
import os

def generate_testnet_addresses():
    """Generate testnet addresses from mnemonic seed using BIP84 derivation"""
    
    print("🔑 Generating Bitcoin testnet addresses for P2P Swap Bot")
    print("=" * 70)
    
    # Generate 12-word mnemonic seed
    mnemonic_obj = Mnemonic('english')
    mnemonic = mnemonic_obj.generate(strength=128)  # 128 bits = 12 words
    
    print("🔐 MNEMONIC SEED - BACKUP THESE 12 WORDS:")
    print("=" * 70)
    print(f"📝 {mnemonic}")
    print("=" * 70)
    print()
    
    print("⚠️  CRITICAL SECURITY WARNINGS:")
    print("🚨 BACKUP THESE WORDS IMMEDIATELY")
    print("🚨 Anyone with these words controls ALL addresses")
    print("🚨 Store offline in multiple secure locations")
    print("🚨 Never share or store online")
    print("🚨 TESTNET ONLY - Never use on mainnet")
    print()
    
    # Create wallet from mnemonic
    wallet_name = 'p2pswap_testnet_escrow'
    
    # Remove wallet if it exists (for clean generation)
    try:
        if Wallet.exists(wallet_name):
            Wallet.delete(wallet_name)
    except:
        pass
    
    # Create new wallet
    wallet = Wallet.create(
        name=wallet_name,
        keys=mnemonic,
        network='testnet',
        account_id=0,
        witness_type='segwit'  # Use native segwit (bech32)
    )
    
    # Generate addresses for different amounts
    amounts = [10000, 50000, 100000, 500000, 1000000]
    addresses = {}
    
    print("📍 DERIVED ADDRESSES (BIP84 - Native SegWit):")
    print("=" * 70)
    
    for i, amount in enumerate(amounts):
        # Get key at derivation path m/84'/1'/0'/0/i
        key = wallet.get_key(account_id=0, network='testnet', change=0, address_index=i)
        address = key.address
        
        # Store for .env file
        if amount >= 1000000:
            key_name = f"BITCOIN_ADDRESS_{amount//1000000}M"
        elif amount >= 1000:
            key_name = f"BITCOIN_ADDRESS_{amount//1000}K"
        else:
            key_name = f"BITCOIN_ADDRESS_{amount}"
            
        addresses[key_name] = {
            'address': address,
            'derivation_path': f"m/84'/1'/0'/0/{i}",
            'amount': amount,
            'index': i
        }
        
        print(f"📍 {amount:,} sats: {address}")
        print(f"   Path: m/84'/1'/0'/0/{i}")
        print()
    
    print("📝 ADD TO YOUR .env FILE:")
    print("=" * 70)
    
    for key_name, data in addresses.items():
        print(f"{key_name}={data['address']}")
    
    print()
    print("🔧 WALLET RECOVERY INFO:")
    print("=" * 70)
    print(f"Derivation Standard: BIP84 (Native SegWit)")
    print(f"Network: testnet")
    print(f"Account: 0")
    print(f"Address Type: P2WPKH (bech32)")
    print(f"Derivation Path: m/84'/1'/0'/0/x")
    
    print()
    print("💾 BACKUP CHECKLIST:")
    print("=" * 70)
    print("☐ Write down the 12-word mnemonic")
    print("☐ Verify you wrote it correctly")
    print("☐ Store in fireproof safe")
    print("☐ Create second backup copy")
    print("☐ Test recovery with small amount")
    print("☐ Never take photo or screenshot")
    
    # Clean up wallet
    try:
        Wallet.delete(wallet_name)
    except:
        pass
    
    return addresses, mnemonic

if __name__ == "__main__":
    addresses, seed = generate_testnet_addresses()
