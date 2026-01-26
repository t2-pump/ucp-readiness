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
        # We keep the raw 'data' to pass it back as metadata later
        data = json.loads(blob)
    except:
        return {"score": 0, "results": {}, "error": "Invalid data format", "metadata": {}}

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
        },
        # ADD THIS: Hand the raw data back to app.py for the GEO auditor
        "metadata": data 
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

def calculate_geo_score(metadata):
    results = {}
    json_ld_list = metadata.get('json-ld') or metadata.get('jsonld') or []
    schema = json_ld_list[0] if json_ld_list and isinstance(json_ld_list, list) else {}
    
    # 1. Schema Richness (40 pts)
    geo_fields = ['brand', 'color', 'material', 'size', 'sku', 'aggregateRating']
    richness_fixes = []
    found_count = 0
    
    for f in geo_fields:
        if f in schema and schema[f]:
            found_count += 1
            # Positive feedback for found items
            richness_fixes.append(f"✅ Found '{f}' in the Product Schema.")
        else:
            # Actionable items for missing fields
            richness_fixes.append(f"❌ Missing '{f}': Add this to improve AI categorization.")
            
    richness_score = int((found_count / len(geo_fields)) * 40)
    results['richness'] = {
        "name": "Schema Richness",
        "points": richness_score,
        "max": 40,
        "status": "Green" if richness_score == 40 else "Yellow" if richness_score > 0 else "Red",
        "msg": f"Found {found_count} of {len(geo_fields)} AI-priority fields.",
        "fixes": richness_fixes
    }

    # 2. Semantic Depth (40 pts)
    desc = schema.get('description', "")
    depth_score = 40 if len(desc) > 200 else 20 if len(desc) > 50 else 0
    depth_fixes = [f"✅ Found description in the Product Schema ({len(desc)} chars)."] if len(desc) > 0 else []
    if depth_score < 40:
        depth_fixes.append("❌ Action: Expand description to 200+ characters for better AI context.")
        
    results['depth'] = {
        "name": "Semantic Depth",
        "points": depth_score,
        "max": 40,
        "status": "Green" if depth_score == 40 else "Yellow" if depth_score == 20 else "Red",
        "msg": f"AI description is {len(desc)} characters.",
        "fixes": depth_fixes
    }

    # 3. Data Integrity (20 pts)
    og_title = metadata.get('opengraph', {}).get('title', "")
    schema_name = schema.get('name', "")
    integrity_score = 20 if og_title and og_title == schema_name and og_title != "" else 0
    
    integrity_fixes = []
    if integrity_score == 20:
        integrity_fixes.append(f"✅ Found matching names: '{schema_name}' matches Meta Title.")
    else:
        integrity_fixes.append("❌ Action: Ensure Schema 'name' matches your HTML Meta Title.")
        
    results['integrity'] = {
        "name": "Data Integrity",
        "points": integrity_score,
        "max": 20,
        "status": "Green" if integrity_score == 20 else "Red",
        "msg": "Meta Title and Schema Name match." if integrity_score == 20 else "Mismatched names detected.",
        "fixes": integrity_fixes
    }

    return {"total": richness_score + depth_score + integrity_score, "breakdown": results}