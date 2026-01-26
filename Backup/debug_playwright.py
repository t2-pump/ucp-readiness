from logic import extract_metadata, find_product_schema, analyze_ucp_readiness

print("Starting Playwright logic check...")
url = "https://www.carhartt.com/c/men-vests?icid=2025-10-09_plp_shops-tool_rank2_clickable_plp_evrgn_m-ow-wdgt-vsts_allvisitors_copy_18585"
print(f"Extracting from {url}...")
try:
    data = extract_metadata(url)
    if "error" in data:
        print(f"FAILED: {data['error']}")
    else:
        print("Extraction successful.")
        print(f"Keys: {data.keys()}")
        
        product = find_product_schema(data)
        print(f"Product found: {product is not None}")

except Exception as e:
    print(f"CRASHED: {e}")
