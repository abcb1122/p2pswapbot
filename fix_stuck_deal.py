#!/usr/bin/env python3
"""
Manual Deal Recovery Script
Use this script to manually fix stuck deals when needed

Usage:
    python3 fix_stuck_deal.py --deal-id 3 --action reset_to_bitcoin_confirmed
    python3 fix_stuck_deal.py --deal-id 5 --action cancel_and_reactivate
    python3 fix_stuck_deal.py --list-stuck
"""

import os
import sys
import argparse
from datetime import datetime, timezone, timedelta

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from database.models import get_db, Deal, Offer
except ImportError:
    print("❌ Error: Could not import database models. Make sure you're in the project directory.")
    sys.exit(1)

def list_stuck_deals():
    """List all potentially stuck deals"""
    db = get_db()
    try:
        # Find deals that might be stuck
        stuck_states = [
            'lightning_invoice_received',
            'awaiting_bitcoin_address',
            'bitcoin_confirmed',
            'retrying_lnproxy',
            'bitcoin_sent'
        ]

        stuck_deals = db.query(Deal).filter(
            Deal.status.in_(stuck_states)
        ).all()

        if not stuck_deals:
            print("✅ No stuck deals found")
            return

        print(f"📋 Found {len(stuck_deals)} potentially stuck deals:")
        print("=" * 80)

        for deal in stuck_deals:
            print(f"Deal #{deal.id}")
            print(f"  Status: {deal.status}")
            print(f"  Stage: {deal.current_stage}")
            print(f"  Seller ID: {deal.seller_id}")
            print(f"  Buyer ID: {deal.buyer_id}")
            print(f"  Amount: {deal.amount_sats} sats")
            print(f"  Created: {deal.created_at}")
            if deal.stage_expires_at:
                expired = deal.stage_expires_at < datetime.now(timezone.utc)
                status = "EXPIRED" if expired else "Active"
                print(f"  Stage expires: {deal.stage_expires_at} ({status})")
            print()

    finally:
        db.close()

def reset_deal_to_bitcoin_confirmed(deal_id):
    """Reset a deal to bitcoin_confirmed status so it can request Lightning invoice again"""
    db = get_db()
    try:
        deal = db.query(Deal).filter(Deal.id == deal_id).first()

        if not deal:
            print(f"❌ Deal #{deal_id} not found")
            return False

        print(f"📋 Current status of Deal #{deal_id}:")
        print(f"  Status: {deal.status}")
        print(f"  Stage: {deal.current_stage}")
        print(f"  Seller ID: {deal.seller_id}")
        print(f"  Buyer ID: {deal.buyer_id}")

        # Reset to bitcoin_confirmed status
        deal.status = 'bitcoin_confirmed'
        deal.current_stage = 'invoice_required'
        deal.stage_expires_at = datetime.now(timezone.utc) + timedelta(hours=2)

        # Clear any previous Lightning invoice data
        deal.lightning_invoice = None
        deal.payment_hash = None

        db.commit()

        print(f"✅ Deal #{deal_id} reset to bitcoin_confirmed status")
        print(f"  New status: {deal.status}")
        print(f"  New stage: {deal.current_stage}")
        print(f"  Stage expires: {deal.stage_expires_at}")
        print()
        print("🔄 The buyer will now receive a new request for Lightning invoice")
        print("🔄 The new network validation will reject mainnet invoices")

        return True

    except Exception as e:
        print(f"❌ Error resetting deal: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def cancel_deal_and_reactivate(deal_id):
    """Cancel a deal and reactivate the associated offer"""
    db = get_db()
    try:
        deal = db.query(Deal).filter(Deal.id == deal_id).first()

        if not deal:
            print(f"❌ Deal #{deal_id} not found")
            return False

        print(f"📋 Cancelling Deal #{deal_id}:")
        print(f"  Current status: {deal.status}")

        # Cancel the deal
        deal.status = 'cancelled'
        deal.timeout_reason = 'Manual recovery action'

        # Reactivate the offer if it exists
        offer = db.query(Offer).filter(Offer.id == deal.offer_id).first()
        if offer:
            # Check if original 48-hour expiration time has passed
            if offer.expires_at and datetime.now(timezone.utc) > offer.expires_at:
                offer.status = 'expired'
                print(f"  Associated offer #{offer.id} marked as expired (original 48h limit passed)")
            else:
                offer.status = 'active'
                offer.taken_by = None
                offer.taken_at = None
                print(f"  Associated offer #{offer.id} reactivated")

        db.commit()

        print(f"✅ Deal #{deal_id} cancelled successfully")

        return True

    except Exception as e:
        print(f"❌ Error cancelling deal: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description='Manual Deal Recovery Script')
    parser.add_argument('--deal-id', type=int, help='Deal ID to fix')
    parser.add_argument('--action', choices=['reset_to_bitcoin_confirmed', 'cancel_and_reactivate'],
                       help='Action to perform on the deal')
    parser.add_argument('--list-stuck', action='store_true', help='List all stuck deals')

    args = parser.parse_args()

    if args.list_stuck:
        list_stuck_deals()
    elif args.deal_id and args.action:
        if args.action == 'reset_to_bitcoin_confirmed':
            reset_deal_to_bitcoin_confirmed(args.deal_id)
        elif args.action == 'cancel_and_reactivate':
            cancel_deal_and_reactivate(args.deal_id)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()