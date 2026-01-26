import streamlit as st
import json
import base64
import subprocess
import sys
import nest_asyncio
from pathlib import Path


# 0. Set Page Config (MUST BE THE VERY FIRST STREAMLIT COMMAND)
st.set_page_config(
    page_title="AI-Commerce UCP & GEO Audit | T2 Digital", 
    page_icon="🤖", 
    layout="wide"
)
# 1. Silent Auto-Recovery for mobile fetch errors
st.html("""
<script>
window.addEventListener('unhandledrejection', (event) => {
    if (event.reason && event.reason.message && 
        (event.reason.message.includes('Failed to fetch dynamically imported module') || 
         event.reason.message.includes('Loading chunk'))) {
        console.log('Mobile module fetch failed. Forcing refresh...');
        window.location.reload();
    }
});
</script>
""")

# 2. IMPORTANT: Ensure these functions exist in your logic.py
from logic import perform_ucp_audit, calculate_geo_score



# 3. Fix for Streamlit/Playwright event loop conflict
nest_asyncio.apply()

# 4. Helper: Convert images to base64 for embedding
def img_to_bytes(img_path):
    try:
        img_bytes = Path(img_path).read_bytes()
        encoded = base64.b64encode(img_bytes).decode()
        return encoded
    except FileNotFoundError:
        return None

# 5. Load Logo
logo_base64 = img_to_bytes("t2_logo.png")

# 6. Header & Responsive CSS
st.html(f"""
<style>
    .logo-container img {{
        width: 120px;
        transition: width 0.3s ease;
    }}
    .responsive-headline {{
        font-size: 2.5rem;
        font-weight: 700;
        margin-top: 10px;
        color: #FFFFFFBF;
    }}
    @media (max-width: 768px) {{
        .logo-container img {{ width: 60px; }}
        .responsive-headline {{ font-size: 1.5rem; line-height: 1.2; }}
    }}
</style>
<div class="logo-container" style="margin-bottom: 15px;">
    <a href="https://www.t2-digital.com" target="_blank">
        <img src="data:image/png;base64,{logo_base64 if logo_base64 else ''}">
    </a>
</div>
<h1 class="responsive-headline">AI-Commerce UCP & GEO Audit</h1>
""")

st.markdown("**Compliance testing for the 2026 Universal Commerce Protocol and Generative Engine Optimization.**")

# 7. SIDEBAR
with st.sidebar:
    st.title("Strategy & Support")
    st.info("""
    **Need help with your AI-Commerce Readiness Strategy?** 
    
    A score below 80% indicates critical gaps in your metadata that block AI agents from verifying your products.
    """)
    st.link_button("Contact Me", "https://www.t2-digital.com/connect", use_container_width=True)
    st.markdown("---")    
    st.info("""
    **Pro Tip:** If Regular Mode is timing out, ensure you are using a direct product URL and not a category page.
    """)
    st.markdown("---")   
    # --- DATA DICTIONARY SECTION ---
    st.subheader("📚 UCP Data Dictionary")
    st.caption("Technical definitions for 2026 AI-Commerce standards.")
    
    with st.sidebar.expander("🆔 Product Identifiers (GTIN)"):
        st.write("""
        **Requirement**: One of `gtin12`, `gtin13`, or `isbn`.

        **Why**: AI agents use these as 'Primary Keys' to verify that the product on your page is the exact item requested by the user.
        """)
        
    with st.sidebar.expander("🚚 Shipping & Returns"):
        st.write("""
        **Requirement**: `shippingDetails` and `hasMerchantReturnPolicy`.

        **Why**: For autonomous transactions, agents must calculate 'Landed Cost' and risk profiles without human intervention.
        """)
        
    with st.sidebar.expander("🤖 UCP AI Flags"):
        st.write("""
        **Requirement**: `isAIFriendly` (Boolean) or `ucpUseCase`.

        **Why**: These 2026 flags grant explicit permission for AI agents to interact with your checkout flow.
        """)
        
    with st.sidebar.expander("🔍 What is GEO?"):
        st.write("""
        **GEO**: Optimization for Generative Engines. Focuses on 'Fact Density' and 'Semantic Depth' so LLMs can summarize your product accurately.
        """)
    st.markdown("---")
    st.caption("T2 Digital © 2026")

# 8. INPUT FORM
with st.form("audit_form"):
    url = st.text_input("Enter Product URL to Audit:", placeholder="https://example.com/product/123")
    fast_mode = st.toggle("Fast Mode", value=False, help="Bypasses browser. Best for sites without bot protection.")
    submitted = st.form_submit_button("Audit URL", type="primary")

if submitted:
    if not url:
        st.warning("Please enter a URL.")
    else:
        try:
            blob = None
            # --- EXECUTION PHASE ---
            if fast_mode:
                with st.spinner("Executing Fast Scan..."):
                    import requests
                    from extruct import extract
                    headers = {"User-Agent": "Mozilla/5.0"}
                    response = requests.get(url, headers=headers, timeout=15)
                    if response.status_code == 200:
                        data = extract(response.text, base_url=url, uniform=True, syntaxes=['json-ld', 'microdata', 'rdfa'])
                        blob = json.dumps(data)
                    else:
                        st.error(f"Fast Mode Failed: Status {response.status_code}")
            else:
                with st.spinner("Launching AI Agent (Playwright)..."):
                    result = subprocess.run(
                        [sys.executable, "-u", "scraper.py", url], 
                        capture_output=True, text=True, timeout=90
                    )
                    blob = result.stdout
                    if result.stderr:
                        sys.stderr.write(result.stderr)

            # --- PROCESS RESULTS ---
            if blob:
                try:
                    parsed_test = json.loads(blob) 
                    
                    if len(blob) < 500:
                        st.warning("⚠️ Partial data received. The site may be blocking the agent.")
                    else:
                        # 1. RUN AUDITS
                        audit_data = perform_ucp_audit(blob)
                        geo_results = calculate_geo_score(audit_data.get('metadata', {}))

                        st.success("Audit Complete!")

                        # --- SECTION 1: GEO SUMMARY ---
                        st.header("1. GEO Readiness Summary")
                        g_col1, g_col2 = st.columns([1, 2])

                        with g_col1:
                            st.metric("Total GEO Score", f"{geo_results['total']}%")
                            if geo_results['total'] >= 80:
                                st.success("High AI Authority")
                            elif geo_results['total'] >= 50:
                                st.warning("Needs Optimization")
                            else:
                                st.error("Invisible to AI")

                        with g_col2:
                            for key in ['richness', 'depth', 'integrity']:
                                item = geo_results['breakdown'][key]
                                label = f"**{item['name']}** ({item['points']}/{item['max']})"
        
                                if item['status'] == 'Green':
                                    st.success(f"✅ {label}: {item['msg']}")
                                elif item['status'] == 'Yellow':
                                    st.warning(f"⚠️ {label}: {item['msg']}")
                                else:
                                    st.error(f"❌ {label}: {item['msg']}")
        
                                with st.expander(f"View {item['name']} Details"):
                                    for fix in item['fixes']:
                                        st.write(fix)

                        st.divider()

                        # --- SECTION 2: UCP SUMMARY ---
                        st.header("2. UCP Readiness Summary")
                        u_col1, u_col2 = st.columns([1, 2])

                        with u_col1:
                            ucp_score = audit_data['score']
                            st.metric("Total UCP Score", f"{ucp_score}%")
                            if ucp_score >= 80:
                                st.success("UCP Compliant")
                            elif ucp_score >= 50:
                                st.warning("UCP Partial")
                            else:
                                st.error("Critical Deficiencies")

                        with u_col2:
                            st.subheader("Core Requirements")
                            for u_key, u_item in audit_data['results'].items():
                                u_label = f"**{u_item['name']}**"
                                score_str = f"({u_item['points']}/{u_item['max_points']})"

                                if u_item['status'] == 'Green':
                                    st.success(f"✅ {u_label} (Found) {score_str}")
                                elif u_item['status'] == 'Yellow':
                                    st.warning(f"⚠️ {u_label}: {u_item['msg']} {score_str}")
                                else:
                                    st.error(f"❌ {u_label}: {u_item['msg']} {score_str}")

                                # Fix: Instructions only show for Yellow/Red items
                                if u_item['status'] != 'Green':
                                    with st.expander(f"How to fix {u_item['name']}?", expanded=False):
                                        if u_key == "gtin":
                                            st.markdown("""
                                            AI agents require unique IDs to verify products. Please add **ONE** of the following:
                                            - **UPC (GTIN-12)**: Standard North American barcode.
                                            - **EAN (GTIN-13)**: International/European barcode.
                                            - **ISBN**: For books and publications.
                                            """)
                                        elif u_key == "brand":
                                            st.markdown("""
                                            **Missing Brand or Images**
                                            AI agents use these for visual verification. Ensure your Schema includes:
                                            - A `brand` string or object.
                                            - At least one valid `image` URL.
                                            """)
                                        elif u_key == "org":
                                            st.markdown("""
                                            **Connect your offer to your store.** AI agents need to verify the merchant's identity before authorizing a transaction. 
    
                                            ```json
                                            {
                                                "offers": {
                                                    "@type": "Offer",
                                                    "seller": {
                                                        "@type": "Organization",
                                                        "name": "Your Store Name",
                                                        "url": "https://yourstore.com"
                                                    }
                                                }
                                            }
                                            ```
                                            """)
                                        elif u_key == "offer":
                                            if u_item['status'] == 'Yellow':
                                                st.markdown("""
                                                **AggregateOffer Detected (Dropdown Issue)**
                                                Your store provides a price range. While transparent, a UCP agent needs a **firm price** for a specific selection to checkout.
                                                
                                                **How to fix for AI-Commerce:**
                                                - **Option A**: Use `priceSpecification` to define the price for every individual variant (Size/Color).
                                                - **Option B**: Provide a unique URL for each dropdown option (e.g., `product-url?size=large`) that loads a single `price` in the metadata.
                                                """)
                                            else:
                                                st.markdown("Ensure your `Offer` contains a valid `price` and `priceCurrency`.")
                                        elif u_key == "shipping":
                                            st.markdown("""
                                            **Connect your shipping rates to your offer.** AI agents cannot calculate the final 'landed cost' without structured shipping data. 
    
                                            Add a `shippingDetails` object **nested directly within the Offer**:
                                            ```json
                                            {
                                                "offers": {
                                                    "@type": "Offer",
                                                    "shippingDetails": {
                                                        "@type": "OfferShippingDetails",
                                                        "shippingRate": {
                                                            "@type": "MonetaryAmount",
                                                            "value": "15.00",
                                                            "currency": "USD"
                                                        },
                                                        "shippingDestination": {
                                                            "@type": "DefinedRegion",
                                                            "addressCountry": "US"
                                                        }
                                                    }
                                                }
                                            }
                                            ```
                                            """)
                                        elif u_key == "returns":
                                            st.markdown("""
                                            **Connect your return policy to your offer.** For autonomous transactions, agents must evaluate risk profiles-including return windows and fees-before committing to a purchase.
    
                                            Add a `hasMerchantReturnPolicy` object **nested directly within the Offer**:
                                            ```json
                                            "offers": {
                                                "@type": "Offer",
                                                "hasMerchantReturnPolicy": {
                                                    "@type": "MerchantReturnPolicy",
                                                    "returnPolicyCategory": "[https://schema.org/MerchantReturnFiniteReturnPeriod](https://schema.org/MerchantReturnFiniteReturnPeriod)",
                                                    "merchantReturnDays": 30,
                                                    "returnFees": "[https://schema.org/FreeReturn](https://schema.org/FreeReturn)"
                                                }
                                            }
                                            ```
                                            > **Pro Tip:** Using the standard Schema.org URIs for `returnPolicyCategory` allows agents to instantly categorize your policy without needing to parse natural language.
                                            """)
                                        elif u_key == "ucp_comp":
                                            st.markdown("""
                                            ### **Integration Paths**
                                            
                                            **Option A: Behavioral Mapping (Retail Standard)**
                                            *Best for apps where you want to explicitly define supported user actions using schema.org properties.*
                                            ```json
                                            "ucpUseCase": ["Purchase", "PriceCheck", "InventoryVerify"]
                                            ```
                                            > **Note:** This maps directly to `BuyAction`, `CheckAction`, and `SearchAction` in your page metadata.

                                            **Option B: Semantic Intent (Agentic Standard)**
                                            *Best for autonomous systems requiring a machine-readable URI to define intent.*
                                            ```json
                                            "intentDefinition": "https://ucp.org/intents/one-time-purchase"
                                            ```
                                            """)
                                        elif u_key == "ucp_use":
                                            st.markdown("""
                                            **Option A: Standard Retail Actions**
                                            ```json
                                            "ucpUseCase": ["Purchase", "PriceCheck", "InventoryVerify"]
                                            ```
                                            **Option B: Autonomous Agentic Intent**
                                            Use a direct intent definition URI:
                                            ```json
                                            "intentDefinition": "https://ucp.org/intents/one-time-purchase"
                                            ```
                                            """)
                                        else:
                                            st.write(f"Requirement: {u_item['msg']}")
 
                        # --- ENHANCED METADATA CSV LOGIC ---
                        import io
                        import csv
                        from datetime import datetime
                        from urllib.parse import urlparse
                        
                        def generate_metadata_csv(metadata_blob):
                            """Flattens all schema entities into the requested CSV format."""
                            output = io.StringIO()
                            writer = csv.writer(output)
                            
                            # Define headers as seen in the user's example
                            headers = [
                                'entity_typ', '@context', '@type', '@id', 'name', 'url', 'sku', 'mpn', 'image', 'category', 'brand', 'color', 'description', 
                                'gtin12', 'gtin13', 'gtin8', 'offers', 'offers-url', 'offers-price', 'offers-priceCurrency', 'offers-availability', 'first-item-offer-image',
                                'telephone', 'faxNumber', 'email', 'address', 'addressLocality', 'addressRegion', 'addressCountry', 'postalCode',
                                'YouTube', 'Facebook', 'LinkedIn', 'Twitter', 'Other_url'
                            ]
                            writer.writerow(headers)
                            
                            # Collect all top-level items from all syntaxes
                            items = []
                            for syntax in ['json-ld', 'microdata', 'rdfa']:
                                raw = metadata_blob.get(syntax, [])
                                if isinstance(raw, list): items.extend(raw)
                                elif isinstance(raw, dict): items.append(raw)
                            
                            for item in items:
                                if not isinstance(item, dict): continue
                                
                                # Flatten Logic
                                row = []
                                row.append(item.get('@type', '')) # entity_typ
                                row.append(item.get('@context', '')) 
                                row.append(item.get('@type', ''))
                                row.append(item.get('@id', ''))
                                row.append(item.get('name', ''))
                                row.append(item.get('url', ''))
                                row.append(item.get('sku', ''))
                                row.append(item.get('mpn', ''))
                                
                                # Image handle
                                img = item.get('image', '')
                                if isinstance(img, list): row.append(img[0] if img else '')
                                elif isinstance(img, dict): row.append(img.get('url', ''))
                                else: row.append(img)
                                
                                row.append(item.get('category', ''))
                                
                                # Brand handle
                                b = item.get('brand', '')
                                if isinstance(b, dict): row.append(b.get('name', ''))
                                else: row.append(b)
                                
                                row.append(item.get('color', ''))
                                row.append(item.get('description', ''))
                                row.append(item.get('gtin12', ''))
                                row.append(item.get('gtin13', item.get('gtin', ''))) # Map gtin to gtin13 if needed
                                row.append(item.get('gtin8', ''))
                                
                                # Offers handle
                                offers = item.get('offers', {})
                                first_off = offers[0] if isinstance(offers, list) and offers else (offers if isinstance(offers, dict) else {})
                                row.append(first_off.get('@type', '')) # offers type
                                row.append(first_off.get('url', ''))
                                row.append(first_off.get('price', ''))
                                row.append(first_off.get('priceCurrency', ''))
                                row.append(first_off.get('availability', ''))
                                
                                off_img = first_off.get('image', '')
                                if isinstance(off_img, list): row.append(off_img[0] if off_img else '')
                                elif isinstance(off_img, dict): row.append(off_img.get('url', ''))
                                else: row.append(off_img)
                                
                                # Org/Contact
                                row.append(item.get('telephone', ''))
                                row.append(item.get('faxNumber', ''))
                                row.append(item.get('email', ''))
                                
                                addr = item.get('address', {})
                                if isinstance(addr, dict):
                                    row.append(addr.get('streetAddress', ''))
                                    row.append(addr.get('addressLocality', ''))
                                    row.append(addr.get('addressRegion', ''))
                                    row.append(addr.get('addressCountry', ''))
                                    row.append(addr.get('postalCode', ''))
                                else:
                                    row.extend([''] * 5)
                                    
                                # Social / sameAs
                                same_as = item.get('sameAs', [])
                                if isinstance(same_as, str): same_as = [same_as]
                                youtube = next((s for s in same_as if 'youtube.com' in s), '')
                                facebook = next((s for s in same_as if 'facebook.com' in s), '')
                                linkedin = next((s for s in same_as if 'linkedin.com' in s), '')
                                twitter = next((s for s in same_as if 'twitter.com' in s or 'x.com' in s), '')
                                other = next((s for s in same_as if s not in [youtube, facebook, linkedin, twitter]), '')
                                
                                row.extend([youtube, facebook, linkedin, twitter, other])
                                
                                writer.writerow(row)
                                
                            return output.getvalue()
 
                        # Generate CSV
                        csv_data = generate_metadata_csv(audit_data.get('metadata', {}))
                        
                        # Filename: ucp-geo-audit-metadata-[domainname]-[mmddyyyy]-[hh:mm:ss]
                        domain = urlparse(url).netloc.replace('www.', '').replace('.', '-')
                        now = datetime.now()
                        date_str = now.strftime("%m%d%Y")
                        time_str = now.strftime("%H-%M-%S") # Use - instead of : for filesystem compatibility
                        filename = f"ucp-geo-audit-metadata-{domain}-{date_str}-{time_str}.csv"
 
                        st.download_button(
                            label="Download Metadata Report",
                            data=csv_data,
                            file_name=filename,
                            mime="text/csv"
                        )

                        st.markdown("---")
                        with st.expander("🔍 Debug: View Raw Metadata Found", expanded=False):
                            st.json(audit_data.get('metadata', {}), expanded=True)

                except json.JSONDecodeError:
                    st.error("Data Corruption: Invalid JSON returned from scraper.")
                    with st.expander("View Raw Output"):
                        st.text(blob[:1000])

        except Exception as e:
            st.error(f"System Error: {str(e)}")

st.divider()
st.caption("T2 Digital © 2026")