"""
Customer Migration Script
=========================

This script migrates existing customer data from bookings to the new customers collection.

Features:
- Extracts unique customers from bookings (by email)
- Creates customer master records
- Links bookings to customers via customer_id
- Calculates customer statistics (total bookings, last booking date)
- Supports dry-run mode for safety
- Generates detailed migration report

Usage:
    python migrate_customers.py --dry-run    # Preview changes without writing
    python migrate_customers.py              # Execute migration
    python migrate_customers.py --help       # Show help

Requirements:
- Firebase Admin SDK configured
- ServiceAccount.json or Application Default Credentials
"""

import os
import sys
import argparse
import json
from datetime import datetime
from collections import defaultdict
import uuid

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import firebase_admin
from firebase_admin import credentials, firestore
from typing import Dict, List, Tuple


class CustomerMigration:
    """Handles migration of customer data from bookings to customers collection"""

    def __init__(self, dry_run=False):
        """Initialize migration with Firebase connection

        Args:
            dry_run (bool): If True, preview changes without writing to database
        """
        self.dry_run = dry_run
        self.db = None
        self.stats = {
            "bookings_processed": 0,
            "unique_customers_found": 0,
            "customers_created": 0,
            "bookings_updated": 0,
            "errors": [],
            "warnings": [],
            "conflicts": []
        }

        self._init_firebase()

    def _init_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            if not firebase_admin._apps:
                # Try local service account first
                service_account_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    'ServiceAccount.json'
                )

                if os.path.exists(service_account_path):
                    print(f"[KEY] Using service account: {service_account_path}")
                    cred = credentials.Certificate(service_account_path)
                    firebase_admin.initialize_app(cred)
                else:
                    print("[CLOUD] Using Application Default Credentials")
                    firebase_admin.initialize_app()

            self.db = firestore.client()
            print("[SUCCESS] Firebase initialized successfully\n")

        except Exception as e:
            print(f"[ERROR] Error initializing Firebase: {e}")
            sys.exit(1)

    def extract_customers_from_bookings(self) -> Dict[str, Dict]:
        """Extract unique customers from all bookings

        Returns:
            Dict mapping email -> customer data with aggregated info
        """
        print("[STEP 1] Extracting customers from bookings...")

        customers = {}  # email -> customer data
        customer_bookings = defaultdict(list)  # email -> list of booking data

        try:
            bookings_ref = self.db.collection('bookings')
            all_bookings = bookings_ref.stream()

            for booking_doc in all_bookings:
                self.stats["bookings_processed"] += 1
                booking = booking_doc.to_dict()
                booking['id'] = booking_doc.id

                # Extract customer info
                email = booking.get('client_email', '').strip().lower()
                name = booking.get('client_name', '').strip()
                phone = booking.get('client_phone', '').strip()

                # Skip if essential data is missing
                if not email or not name:
                    self.stats["warnings"].append(
                        f"Booking {booking['id']} missing email or name - skipped"
                    )
                    continue

                # Store booking data for this customer
                customer_bookings[email].append({
                    'booking_id': booking['id'],
                    'name': name,
                    'phone': phone,
                    'event_date': booking.get('event_date'),
                    'created_at': booking.get('created_at', datetime.now())
                })

            # Aggregate customer data
            for email, bookings in customer_bookings.items():
                # Use most recent booking for customer data (in case of variations)
                bookings.sort(key=lambda x: x['created_at'], reverse=True)
                latest = bookings[0]
                earliest = bookings[-1]

                # Get last booking date
                booking_dates = [b['event_date'] for b in bookings if b['event_date']]
                last_booking_date = max(booking_dates) if booking_dates else None

                customers[email] = {
                    'email': email,
                    'name': latest['name'],
                    'phone': latest['phone'],
                    'total_bookings': len(bookings),
                    'last_booking_date': last_booking_date,
                    'created_at': earliest['created_at'],
                    'booking_ids': [b['booking_id'] for b in bookings]
                }

                # Check for data variations (name/phone changed across bookings)
                names = set(b['name'] for b in bookings)
                phones = set(b['phone'] for b in bookings if b['phone'])

                if len(names) > 1:
                    self.stats["conflicts"].append(
                        f"Customer {email} has multiple names: {names}"
                    )

                if len(phones) > 1:
                    self.stats["conflicts"].append(
                        f"Customer {email} has multiple phones: {phones}"
                    )

            self.stats["unique_customers_found"] = len(customers)
            print(f"   [OK] Found {len(customers)} unique customers from {self.stats['bookings_processed']} bookings")

            return customers

        except Exception as e:
            error_msg = f"Error extracting customers: {e}"
            self.stats["errors"].append(error_msg)
            print(f"   [ERROR] {error_msg}")
            raise

    def create_customer_documents(self, customers: Dict[str, Dict]) -> Dict[str, str]:
        """Create customer documents in Firestore

        Args:
            customers: Dict of customer data by email

        Returns:
            Dict mapping email -> customer_id
        """
        print(f"\n[STEP 2] Creating customer documents ({len(customers)} customers)...")

        email_to_id = {}

        if self.dry_run:
            print("   [DRY-RUN] No documents will be created")

        try:
            for email, customer_data in customers.items():
                customer_id = str(uuid.uuid4())
                now = datetime.now()

                customer_doc = {
                    'id': customer_id,
                    'name': customer_data['name'],
                    'email': customer_data['email'],
                    'phone': customer_data['phone'],
                    'address': None,
                    'notes': f"Migrated from existing bookings ({customer_data['total_bookings']} bookings)",
                    'total_bookings': customer_data['total_bookings'],
                    'last_booking_date': customer_data['last_booking_date'],
                    'created_at': customer_data['created_at'],
                    'updated_at': now,
                    'is_active': True
                }

                if not self.dry_run:
                    self.db.collection('customers').document(customer_id).set(customer_doc)
                    self.stats["customers_created"] += 1

                email_to_id[email] = customer_id

                # Progress indicator
                if (self.stats["customers_created"] + 1) % 10 == 0:
                    print(f"   ... {self.stats['customers_created'] + 1}/{len(customers)} customers processed")

            if self.dry_run:
                print(f"   [OK] Would create {len(customers)} customer documents")
            else:
                print(f"   [OK] Created {self.stats['customers_created']} customer documents")

            return email_to_id

        except Exception as e:
            error_msg = f"Error creating customer documents: {e}"
            self.stats["errors"].append(error_msg)
            print(f"   [ERROR] {error_msg}")
            raise

    def link_bookings_to_customers(self, customers: Dict[str, Dict], email_to_id: Dict[str, str]):
        """Update all bookings with customer_id reference

        Args:
            customers: Dict of customer data by email
            email_to_id: Dict mapping email -> customer_id
        """
        print(f"\n[STEP 3] Linking bookings to customers...")

        if self.dry_run:
            print("   [DRY-RUN] No bookings will be updated")

        try:
            for email, customer_data in customers.items():
                customer_id = email_to_id[email]

                for booking_id in customer_data['booking_ids']:
                    if not self.dry_run:
                        self.db.collection('bookings').document(booking_id).update({
                            'customer_id': customer_id,
                            'updated_at': datetime.now()
                        })
                        self.stats["bookings_updated"] += 1

            if self.dry_run:
                print(f"   [OK] Would update {sum(c['total_bookings'] for c in customers.values())} bookings")
            else:
                print(f"   [OK] Updated {self.stats['bookings_updated']} bookings with customer_id")

        except Exception as e:
            error_msg = f"Error linking bookings: {e}"
            self.stats["errors"].append(error_msg)
            print(f"   [ERROR] {error_msg}")
            raise

    def generate_report(self):
        """Generate and display migration report"""
        print("\n" + "=" * 60)
        print("MIGRATION REPORT")
        print("=" * 60)
        print(f"Mode: {'DRY RUN (no changes made)' if self.dry_run else 'LIVE MIGRATION'}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        print("Statistics:")
        print(f"  - Bookings processed: {self.stats['bookings_processed']}")
        print(f"  - Unique customers found: {self.stats['unique_customers_found']}")
        print(f"  - Customers created: {self.stats['customers_created']}")
        print(f"  - Bookings updated: {self.stats['bookings_updated']}")
        print()

        if self.stats["warnings"]:
            print(f"[WARNING] Warnings ({len(self.stats['warnings'])}):")
            for warning in self.stats["warnings"][:10]:  # Show first 10
                print(f"  - {warning}")
            if len(self.stats["warnings"]) > 10:
                print(f"  ... and {len(self.stats['warnings']) - 10} more")
            print()

        if self.stats["conflicts"]:
            print(f"[WARNING] Data Conflicts ({len(self.stats['conflicts'])}):")
            for conflict in self.stats["conflicts"][:10]:  # Show first 10
                print(f"  - {conflict}")
            if len(self.stats["conflicts"]) > 10:
                print(f"  ... and {len(self.stats['conflicts']) - 10} more")
            print()

        if self.stats["errors"]:
            print(f"[ERROR] Errors ({len(self.stats['errors'])}):")
            for error in self.stats["errors"]:
                print(f"  - {error}")
            print()

        print("=" * 60)

        # Save report to file
        report_filename = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, default=str)
        print(f"[REPORT] Full report saved to: {report_filename}")

    def run(self):
        """Execute the complete migration process"""
        print("\n" + "=" * 60)
        print("CUSTOMER MIGRATION SCRIPT")
        print("=" * 60)
        print()

        try:
            # Step 1: Extract customers from bookings
            customers = self.extract_customers_from_bookings()

            # Step 2: Create customer documents
            email_to_id = self.create_customer_documents(customers)

            # Step 3: Link bookings to customers
            self.link_bookings_to_customers(customers, email_to_id)

            # Generate report
            self.generate_report()

            if self.dry_run:
                print("\n[SUCCESS] Dry run completed successfully!")
                print("   Run without --dry-run flag to execute migration.")
            else:
                print("\n[SUCCESS] Migration completed successfully!")

            return True

        except Exception as e:
            print(f"\n[ERROR] Migration failed: {e}")
            self.generate_report()
            return False


def main():
    """Main entry point for migration script"""
    parser = argparse.ArgumentParser(
        description="Migrate customer data from bookings to customers collection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate_customers.py --dry-run    # Preview changes
  python migrate_customers.py              # Execute migration
        """
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without writing to database'
    )

    args = parser.parse_args()

    # Run migration
    migration = CustomerMigration(dry_run=args.dry_run)
    success = migration.run()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
