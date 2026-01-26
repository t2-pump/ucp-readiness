from logic import find_product_schema, perform_ucp_audit, calculate_geo_score

print("Starting logic check...")
url = "https://schema.org/Product" # Safe test URL
print(f"Extracting from {url}...")
try:
    # 1. Mock JSON data for testing
    blob = '{"json-ld": [{"@type": "Product", "name": "Test Product", "gtin13": "1234567890123", "description": "A very long description that should satisfy the GEO depth requirement and provide semantic hooks for AI agents.", "offers": {"@type": "Offer", "price": "99.99", "priceCurrency": "USD"}}]}'
    
    print("Running UCP Audit...")
    audit_data = perform_ucp_audit(blob)
    print(f"UCP Score: {audit_data['score']}%")
    
    print("Running GEO Audit...")
    geo_results = calculate_geo_score(audit_data.get('metadata', {}))
    print(f"GEO Score: {geo_results['total']}%")

except Exception as e:
    print(f"CRASHED: {e}")
