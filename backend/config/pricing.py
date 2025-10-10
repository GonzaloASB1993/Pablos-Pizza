"""
Pricing configuration constants for Pablo's Pizza
"""

class PricingConfig:
    """Pricing tiers and constants"""

    # Pizzeros en Acción pricing
    PIZZEROS_BASE_PRICE = 13500
    PIZZEROS_MINIMUM = 135000

    PIZZEROS_TIERS = [
        {'min': 0, 'max': 10, 'price': 13500},
        {'min': 11, 'max': 14, 'price': 10500},
        {'min': 15, 'max': 19, 'price': 9500},
        {'min': 20, 'max': float('inf'), 'price': 9000}
    ]

    # Pizza Party pricing (based on pizza quantity)
    PIZZA_PARTY_BASE_PRICE = 11990
    PIZZA_PARTY_DISCOUNT_THRESHOLD = 20
    PIZZA_PARTY_DISCOUNT = 0.10  # 10% discount for 20+ pizzas

    # Pizza calculation
    SLICES_PER_PERSON = 5
    SLICES_PER_PIZZA = 8
    MIN_PIZZAS = 10

    @staticmethod
    def get_pizzeros_price(participants):
        """Get Pizzeros en Acción price per participant"""
        for tier in PricingConfig.PIZZEROS_TIERS:
            if tier['min'] <= participants <= tier['max']:
                return tier['price']
        return PricingConfig.PIZZEROS_TIERS[-1]['price']

    @staticmethod
    def get_pizza_party_price(pizzas):
        """Get Pizza Party price per pizza with discount for bulk orders"""
        if pizzas >= PricingConfig.PIZZA_PARTY_DISCOUNT_THRESHOLD:
            return round(PricingConfig.PIZZA_PARTY_BASE_PRICE * (1 - PricingConfig.PIZZA_PARTY_DISCOUNT))
        return PricingConfig.PIZZA_PARTY_BASE_PRICE

    @staticmethod
    def calculate_suggested_pizzas(guests):
        """Calculate suggested number of pizzas based on guests"""
        if guests <= 0:
            return PricingConfig.MIN_PIZZAS
        suggested = -(-guests * PricingConfig.SLICES_PER_PERSON // PricingConfig.SLICES_PER_PIZZA)  # Ceiling division
        return max(PricingConfig.MIN_PIZZAS, suggested)
