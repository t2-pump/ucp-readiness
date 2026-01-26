import json

def find_product_schema(data):
    """Locates the Product schema from extracted JSON data."""
    def search_in_items(items):
        for item in items:
            if item.get('@type') == 'Product':
                return item
            if isinstance(item.get('@type'), list) and 'Product' in item.get('@type'):
                return item
        return None

    if 'json-ld' in data:
        product = search_in_items(data['json-ld'])
        if product: return product
            
    if 'microdata' in data:
        product = search_in_items(data['microdata'])
        if product: return product
            
    return None

def perform_ucp_audit(blob):
    """The centralized auditor expected by app.py."""
    try:
        data = json.loads(blob)
    except:
        return {"score": 0, "results": {}, "error": "Invalid data format"}

    product_data = find_product_schema(data)
    
    # Initialize results matching the keys in your app.py display loop
    audit_data = {
        "score": 0,
        "results": {
            "gtin": {"name": "Global Product Identifiers (GTIN)", "status": "Red", "points": 0, "max_points": 20, "msg": "Missing GTIN"},
            "shipping": {"name": "Shipping Details", "status": "Red", "points": 0, "max_points": 20, "msg": "Missing policy"},
            "returns": {"name": "Merchant Return Policy", "status": "Red", "points": 0, "max_points": 20, "msg": "Missing policy"},
            "brand": {"name": "Brand & Images", "status": "Red", "points": 0, "max_points": 10, "msg": "Missing brand/images"},
            "offer": {"name": "Offers", "status": "Red", "points": 0, "max_points": 10, "msg": "Missing price data"},
            "org": {"name": "Organization Link", "status": "Red", "points": 0, "max_points": 10, "msg": "Missing seller link"},
            "ucp_comp": {"name": "UCP Compatibility", "status": "Red", "points": 0, "max_points": 5, "msg": "Missing AI flags"},
            "ucp_use": {"name": "UCP Use Case", "status": "Red", "points": 0, "max_points": 5, "msg": "Missing intent"}
        }
    }

    if not product_data:
        return audit_data

    # --- Weighted Scoring Logic ---
    # GTIN - 20 pts
    if any(product_data.get(k) for k in ["gtin", "gtin13", "gtin12", "isbn"]):
        audit_data["results"]["gtin"].update({"status": "Green", "points": 20})

    # Shipping - 20 pts
    offers = product_data.get('offers', {})
    first_offer = offers[0] if isinstance(offers, list) and offers else (offers if isinstance(offers, dict) else {})
    if product_data.get('shippingDetails') or first_offer.get('shippingDetails'):
        audit_data["results"]["shipping"].update({"status": "Green", "points": 20})

    # Return Policy - 20 pts
    if product_data.get('hasMerchantReturnPolicy') or first_offer.get('hasMerchantReturnPolicy'):
        audit_data["results"]["returns"].update({"status": "Green", "points": 20})

    # Brand/Offer/Org - 10 pts each
    if product_data.get('brand') and product_data.get('image'):
        audit_data["results"]["brand"].update({"status": "Green", "points": 10})
    if product_data.get('offers'):
        audit_data["results"]["offer"].update({"status": "Green", "points": 10})
    if first_offer.get('seller') or first_offer.get('offeredBy'):
        audit_data["results"]["org"].update({"status": "Green", "points": 10})

    # UCP Flags - 5 pts each
    if product_data.get('ucpCompatibility') or product_data.get('isAIFriendly'):
        audit_data["results"]["ucp_comp"].update({"status": "Green", "points": 5})
    if product_data.get('ucpUseCase') or product_data.get('intentDefinition'):
        audit_data["results"]["ucp_use"].update({"status": "Green", "points": 5})

    audit_data["score"] = sum(v["points"] for v in audit_data["results"].values())
    return audit_data