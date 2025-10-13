"""
Pagination utility for Firestore queries
Provides consistent pagination across all endpoints
"""

def paginate_query(query, page=1, limit=20):
    """
    Paginate a Firestore query

    Args:
        query: Firestore query object
        page: Page number (1-indexed)
        limit: Items per page

    Returns:
        tuple: (paginated_docs, has_more, total_showing)
    """
    try:
        page = max(1, int(page))  # Ensure page >= 1
        limit = max(1, min(100, int(limit)))  # Limit between 1-100

        # Calculate offset
        offset = (page - 1) * limit

        # Get one extra to check if there are more pages
        docs = query.limit(limit + 1).offset(offset).stream()

        # Convert to dict and include document ID
        items = []
        for doc in docs:
            item = doc.to_dict()
            item['id'] = doc.id  # Add document ID
            items.append(item)

        # Check if there are more items
        has_more = len(items) > limit

        # Return only the requested number of items
        if has_more:
            items = items[:limit]

        return items, has_more, len(items)

    except Exception as e:
        print(f"[ERROR] Pagination error: {e}")
        # Return empty result on error
        return [], False, 0


def create_pagination_response(items, page, limit, has_more, total_showing):
    """
    Create standardized pagination response

    Args:
        items: List of items
        page: Current page number
        limit: Items per page
        has_more: Boolean indicating if more pages exist
        total_showing: Number of items in current page

    Returns:
        dict: Standardized pagination response
    """
    return {
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "showing": total_showing,
            "has_more": has_more,
            "next_page": page + 1 if has_more else None
        }
    }
