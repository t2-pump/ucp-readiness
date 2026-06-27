import json

def find_product_schema(data):
    """Locates the Product schema from extracted JSON data."""
    def search_in_items(items):
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list): return None
        for item in items:
            if not isinstance(item, dict): continue
            
            # Check for @graph wrapping
            if '@graph' in item and isinstance(item['@graph'], list):
                found = search_in_items(item['@graph'])
                if found: return found
                
            # Handle both string and list types for @type
            obj_type = item.get('@type', '')
            if obj_type == 'Product' or obj_type == 'IndividualProduct' or (isinstance(obj_type, list) and ('Product' in obj_type or 'IndividualProduct' in obj_type)):
                return item
        return None

    for syntax in ['json-ld', 'microdata', 'rdfa']:
        if syntax in data:
            product = search_in_items(data[syntax])
            if product: return product
            
    return None

def perform_ucp_audit(blob):
    """Centralized auditor for UCP 2026 Compliance."""
    try:
        data = json.loads(blob)
    except:
        return {"score": 0, "results": {}, "error": "Invalid JSON", "metadata": {}}

    product_data = find_product_schema(data)
    
    # Initialize dictionary with singular 'offer' key to match your app.py
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
        "warnings": [],
        "metadata": data 
    }

    if not product_data:
        return audit_data

    # Check for Schema Warnings
    p_type = product_data.get('@type', '')
    if p_type == 'IndividualProduct' or (isinstance(p_type, list) and 'IndividualProduct' in p_type):
        audit_data["warnings"].append(
            "⚠️ **Schema Warning:**\n\n"
            "**Detected type:** `IndividualProduct`\n\n"
            "**Recommended type:** `Product`\n\n"
            "**Risk:** The structured data implementation appears non-standard and may limit eligibility for product rich results and AI-driven product discovery."
        )

    # --- 1. GTIN Scoring ---
    if any(product_data.get(k) for k in ["gtin", "gtin13", "gtin12", "gtin8", "isbn"]):
        audit_data["results"]["gtin"].update({"status": "Green", "points": 20, "msg": "Verified"})

    # --- 2. Offer & Aggregate Selection Logic ---
    offers = product_data.get('offers', {})
    # Normalize offers to a list for processing
    offer_list = offers if isinstance(offers, list) else ([offers] if isinstance(offers, dict) else [])
    first_offer = offer_list[0] if offer_list else {}
    
    # Check for AggregateOffer (Range/Dropdown)
    is_aggregate = any(o.get('@type') == 'AggregateOffer' for o in offer_list)
    price = first_offer.get('price') or first_offer.get('lowPrice')
    currency = first_offer.get('priceCurrency')

    if is_aggregate and price and currency:
        # Trigger the Option A/B instructions in app.py
        audit_data["results"]["offer"].update({
            "status": "Yellow", 
            "points": 5, 
            "msg": "Incomplete price data"
        })
    elif price and currency:
        audit_data["results"]["offer"].update({"status": "Green", "points": 10, "msg": "Verified"})
    else:
        audit_data["results"]["offer"].update({"status": "Red", "points": 0, "msg": "Missing price/currency"})

    # --- 3. Shipping & Returns ---
    if product_data.get('shippingDetails') or first_offer.get('shippingDetails'):
        audit_data["results"]["shipping"].update({"status": "Green", "points": 20, "msg": "Verified"})

    if product_data.get('hasMerchantReturnPolicy') or first_offer.get('hasMerchantReturnPolicy'):
        audit_data["results"]["returns"].update({"status": "Green", "points": 20, "msg": "Verified"})

    # --- 4. Brand, Images & Org ---
    if (product_data.get('brand') or first_offer.get('brand')) and product_data.get('image'):
        audit_data["results"]["brand"].update({"status": "Green", "points": 10, "msg": "Verified"})
        
    if first_offer.get('seller') or first_offer.get('offeredBy'):
        audit_data["results"]["org"].update({"status": "Green", "points": 10, "msg": "Verified"})

    # --- 5. UCP Flags ---
    if any(product_data.get(k) for k in ['ucpCompatibility', 'isAIFriendly']):
        audit_data["results"]["ucp_comp"].update({"status": "Green", "points": 5, "msg": "Verified"})
        
    if any(product_data.get(k) for k in ['ucpUseCase', 'intentDefinition']):
        audit_data["results"]["ucp_use"].update({"status": "Green", "points": 5, "msg": "Verified"})

    # Calculate Total
    audit_data["score"] = sum(v["points"] for v in audit_data["results"].values())
    return audit_data

def calculate_geo_score(metadata):
    """GEO Audit: Optimizing for AI Inference Advantage."""
    # IMPROVEMENT: Use the robust finder instead of metadata['json-ld'][0]
    schema = find_product_schema(metadata) or {}
    
    results = {}
    
    # 1. Schema Richness (40 pts) - Essential for AI "Fact-Density"
    geo_fields = ['brand', 'color', 'material', 'size', 'sku', 'aggregateRating']
    richness_fixes = []
    found_count = 0
    
    for f in geo_fields:
        if f in schema and schema[f]:
            found_count += 1
            richness_fixes.append(f"✅ Found '{f}' in the Product Schema.")
        else:
            richness_fixes.append(f"❌ Missing '{f}': AI agents use this for high-confidence filtering.")
            
    richness_score = int((found_count / len(geo_fields)) * 40)
    results['richness'] = {
        "name": "Schema Richness",
        "points": richness_score,
        "max": 40,
        "status": "Green" if richness_score == 40 else "Yellow" if richness_score > 0 else "Red",
        "msg": f"Found {found_count} of {len(geo_fields)} AI-priority fields.",
        "fixes": richness_fixes
    }

    # 2. Semantic Depth (40 pts) - Optimization for LLM "Summary Summarization"
    desc = schema.get('description', "")
    depth_score = 40 if len(desc) > 200 else 20 if len(desc) > 50 else 0
    depth_fixes = [f"✅ Found description ({len(desc)} chars)."] if len(desc) > 0 else []
    if depth_score < 40:
        depth_fixes.append("❌ Action: Agents need 'semantic hooks'. Expand to 200+ characters.")
        
    results['depth'] = {
        "name": "Semantic Depth",
        "points": depth_score,
        "max": 40,
        "status": "Green" if depth_score == 40 else "Yellow" if depth_score == 20 else "Red",
        "msg": f"AI description depth is {len(desc)} characters.",
        "fixes": depth_fixes
    }

    # 3. Data Integrity (20 pts) - Ensuring cross-channel signal consistency
    og_title = metadata.get('opengraph', {}).get('title', "")
    schema_name = schema.get('name', "")
    integrity_score = 20 if og_title and og_title == schema_name and og_title != "" else 0
    
    integrity_fixes = []
    if integrity_score == 20:
        integrity_fixes.append(f"✅ Consistency check passed: '{schema_name}' matches Meta Title.")
    else:
        integrity_fixes.append("❌ Action: Mismatch detected. Ensure Schema 'name' and Meta Title are identical.")
        
    results['integrity'] = {
        "name": "Data Integrity",
        "points": integrity_score,
        "max": 20,
        "status": "Green" if integrity_score == 20 else "Red",
        "msg": "Meta signals align with Schema." if integrity_score == 20 else "Signal mismatch may confuse AI engines.",
        "fixes": integrity_fixes
    }

    return {"total": richness_score + depth_score + integrity_score, "breakdown": results}