"""
Financial Synchronization Utilities
Functions for syncing financial data between bookings, events, and consumption
"""
from database import get_db


def sync_booking_financials(booking_id: str, booking_data: dict = None):
    """
    Synchronize financial data from consumption to booking

    Args:
        booking_id: Booking ID
        booking_data: Booking data dict (optional, will fetch if not provided)

    Returns:
        dict: Updated financial data or None if error
    """
    try:
        db = get_db()
        if not db:
            return None

        # Get booking if not provided
        if not booking_data:
            booking_ref = db.collection('bookings').document(booking_id)
            booking_doc = booking_ref.get()
            if not booking_doc.exists:
                return None
            booking_data = booking_doc.to_dict()

        # Get consumption data
        consumption_docs = list(
            db.collection('event_consumption')
            .where('booking_id', '==', booking_id)
            .limit(1)
            .stream()
        )

        if not consumption_docs:
            return None

        consumption_data = consumption_docs[0].to_dict()

        # Get supplies data
        supplies_docs = list(
            db.collection('event_supplies')
            .where('booking_id', '==', booking_id)
            .limit(1)
            .stream()
        )

        supplies_data = supplies_docs[0].to_dict() if supplies_docs else {}

        # Build financial data
        est_supply = float(supplies_data.get('estimated_total_cost', 0) or 0)
        real_supply = float(consumption_data.get('total_supply_cost', 0) or 0)
        other_exp = float(consumption_data.get('total_other_expenses', 0) or 0)

        current_supply = real_supply if real_supply > 0 else est_supply
        total_cost = current_supply + other_exp

        estimated_price = float(booking_data.get('estimated_price', 0) or 0)
        profit = estimated_price - total_cost if estimated_price > 0 else 0

        financials = {
            'estimated_supply_cost': est_supply,
            'supply_cost': real_supply,
            'other_expenses': other_exp,
            'total_expenses': total_cost,
            'income': estimated_price,
            'profit': profit,
            'profit_margin': round((profit / estimated_price * 100), 2) if estimated_price > 0 else 0
        }

        # Update booking with financial data
        db.collection('bookings').document(booking_id).update({
            'financials': financials
        })

        return financials

    except Exception as e:
        print(f"Error syncing booking financials: {e}")
        return None


def compute_booking_costs(booking_id: str, booking_data: dict = None) -> dict:
    """
    Compute current costs for a booking

    Args:
        booking_id: Booking ID
        booking_data: Booking data dict (optional)

    Returns:
        dict: Computed costs breakdown
    """
    try:
        db = get_db()
        if not db:
            return {}

        # Get booking if not provided
        if not booking_data:
            booking_ref = db.collection('bookings').document(booking_id)
            booking_doc = booking_ref.get()
            if not booking_doc.exists:
                return {}
            booking_data = booking_doc.to_dict()

        financials = booking_data.get('financials', {})
        est_supply = float(financials.get('estimated_supply_cost', 0) or 0)
        real_supply = float(financials.get('supply_cost', 0) or 0)
        other_exp = float(financials.get('other_expenses', 0) or 0)

        # Fallback to collections if not in financials
        if real_supply == 0 or (other_exp == 0 and 'other_expenses' not in financials):
            # Get consumption data
            cons_docs = list(
                db.collection('event_consumption')
                .where('booking_id', '==', booking_id)
                .limit(1)
                .stream()
            )
            if cons_docs:
                cons_data = cons_docs[0].to_dict()
                real_supply = float(cons_data.get('total_supply_cost', real_supply) or 0)
                other_exp = float(cons_data.get('total_other_expenses', other_exp) or 0)

        # Get estimated supply if not present
        if est_supply == 0:
            sup_docs = list(
                db.collection('event_supplies')
                .where('booking_id', '==', booking_id)
                .limit(1)
                .stream()
            )
            if sup_docs:
                sup_data = sup_docs[0].to_dict()
                est_supply = float(sup_data.get('estimated_total_cost', est_supply) or 0)

        current_supply = real_supply if real_supply > 0 else est_supply
        total_cost = current_supply + other_exp

        return {
            'estimated_supply_cost': est_supply,
            'real_supply_cost': real_supply,
            'other_expenses_total': other_exp,
            'current_supply_cost': current_supply,
            'total_cost': total_cost,
            'source': 'real' if real_supply > 0 else 'estimated'
        }

    except Exception as e:
        print(f"⚠️ Error computing booking costs: {e}")
        return {}
