from logic import extract_metadata, find_product_schema, analyze_ucp_readiness

print("Starting logic check...")
url = "https://schema.org/Product" # Safe test URL
print(f"Extracting from {url}...")
try:
    data = extract_metadata(url)
    print("Extraction successful.")
    print(f"Keys: {data.keys()}")
    
    product = find_product_schema(data)
    print(f"Product found: {product is not None}")
    
    if product:
        analysis = analyze_ucp_readiness(product)
        print("Analysis successful.")
        print(analysis)
    else:
        print("No product found to analyze, but code didn't crash.")

except Exception as e:
    print(f"CRASHED: {e}")
