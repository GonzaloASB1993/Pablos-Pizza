"""Fuzzy lookup of inventory items by name (used by the AI agent before creating or buying anything)"""
from utils.text_matching import calculate_similarity, normalize_text

INVENTORY = 'inventory'
SIMILAR_THRESHOLD = 0.6   # shown as a candidate
DUPLICATE_THRESHOLD = 0.9  # exact or one name contains the other: very likely the same item


def _classify(score):
    if score >= 1.0:
        return 'exact'
    if score >= DUPLICATE_THRESHOLD:
        return 'contains'
    return 'similar'


def _summary(item_id, item, score):
    return {
        'id': item_id,
        'name': item.get('name'),
        'category': item.get('category'),
        'unit': item.get('unit'),
        'current_stock': item.get('current_stock', 0),
        'cost_per_unit': item.get('weighted_avg_cost', item.get('cost_per_unit', 0)),
        'score': round(score, 2),
        'match': _classify(score),
    }


def search_items(db, query, limit=5, threshold=SIMILAR_THRESHOLD):
    """Best matches first. Accent- and case-insensitive."""
    needle = normalize_text(query)
    if not needle:
        return []
    scored = []
    for snapshot in db.collection(INVENTORY).stream():
        item = snapshot.to_dict()
        score = calculate_similarity(needle, normalize_text(item.get('name', '')))
        if score >= threshold:
            scored.append((score, snapshot.id, item))
    scored.sort(key=lambda row: (-row[0], normalize_text(row[2].get('name', ''))))
    return [_summary(item_id, item, score) for score, item_id, item in scored[:limit]]


def find_duplicates(db, name):
    """Items that are very likely the same product as `name`"""
    return search_items(db, name, limit=3, threshold=DUPLICATE_THRESHOLD)


def catalog_vocabulary(db):
    """Categories and units already in use, so new items follow the existing vocabulary"""
    categories, units = set(), set()
    for snapshot in db.collection(INVENTORY).stream():
        item = snapshot.to_dict()
        if item.get('category'):
            categories.add(item['category'])
        if item.get('unit'):
            units.add(item['unit'])
    return sorted(categories), sorted(units)
