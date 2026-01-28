import streamlit as st
import json
import base64
import subprocess
import sys
import nest_asyncio
from pathlib import Path
import io



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

# 4. Helpers: Image encoding and CSV generation
def img_to_bytes(img_path):
    try:
        img_bytes = Path(img_path).read_bytes()
        encoded = base64.b64encode(img_bytes).decode()
        return encoded
    except FileNotFoundError:
        return None

def get_csv_download_link(csv_data, filename="audit_results.csv"):
    """
    Generates a link allowing the data to be downloaded directly from the browser.
    This bypasses common "Failed - No file" errors on managed corporate browsers.
    """
    try:
        # If csv_data is a string, encode it. If it's a DataFrame, use .to_csv()
        if hasattr(csv_data, 'to_csv'):
            csv_str = csv_data.to_csv(index=False)
        else:
            csv_str = csv_data
            
        b64 = base64.b64encode(csv_str.encode()).decode() 
        return f'<a href="data:file/csv;base64,{b64}" download="{filename}" style="color: #00acee; font-weight: bold;">Click here to download your Audit CSV</a>'
    except Exception as e:
        return f"Error generating download link: {e}"

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

                        # --- ROBUST DOWNLOAD FIX ---
                        # Create the link using the helper function we added to Section 4
                        # We pass audit_data (or whichever variable contains the exportable table)
                        download_link = get_csv_download_link(audit_data)
                        st.markdown(download_link, unsafe_allow_html=True)
                        st.info("💡 Use the link above if the standard download button fails.")

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
                            """Flattens schema entities while merging fragmented signals (IDs, typeless RDFa) into single rows."""
                            import io
                            import csv
                            
                            def flatten(d, parent_key='', sep='-'):
                                items = []
                                for k, v in d.items():
                                    if k in ['_xpath', '_source']: continue
                                    
                                    # Skip noisy RDFa/Namespace attributes (URIs, URLs, and artifacts)
                                    k_str = str(k).lower()
                                    if 'rsv' in k_str or 'http' in k_str or '://' in k_str or '#' in k_str:
                                        continue
                                    if k_str in ['@value', '@language']:
                                        continue
                                    
                                    if isinstance(v, str) and (v.startswith('_:') or not v.strip()):
                                        continue
                                        
                                    new_key = f"{parent_key}{sep}{k}" if parent_key else k
                                    if isinstance(v, dict):
                                        items.extend(flatten(v, new_key, sep=sep).items())
                                    elif isinstance(v, list):
                                        if not v: continue
                                        if all(isinstance(i, (str, int, float)) for i in v):
                                            clean_v = [str(i) for i in v if not (isinstance(i, str) and i.startswith('_:'))]
                                            if clean_v:
                                                items.append((new_key, " | ".join(clean_v)))
                                                if k == 'sameAs':
                                                    for val in clean_v:
                                                        url_lt = val.lower()
                                                        if 'youtube.com' in url_lt: items.append(('YouTube', val))
                                                        elif 'facebook.com' in url_lt: items.append(('Facebook', val))
                                                        elif 'linkedin.com' in url_lt: items.append(('LinkedIn', val))
                                                        elif 'twitter.com' in url_lt or 'x.com' in url_lt: items.append(('Twitter', val))
                                        else:
                                            aggregator = {}
                                            for obj in v:
                                                if isinstance(obj, dict):
                                                    flat_obj = flatten(obj, '', sep=sep)
                                                    for sub_k, sub_v in flat_obj.items():
                                                        if sub_k not in aggregator: aggregator[sub_k] = []
                                                        aggregator[sub_k].append(str(sub_v))
                                            for sub_k, vals in aggregator.items():
                                                items.append((f"{new_key}{sep}{sub_k}", " | ".join(vals)))
                                    else:
                                        items.append((new_key, v))
                                return dict(items)

                            # --- 1. COLLECT & MERGE STAGE ---
                            items_by_id = {}
                            typeless_fragments = []
                            other_items = []
                            
                            for syntax in ['json-ld', 'microdata', 'rdfa']:
                                raw = metadata_blob.get(syntax, [])
                                items_list = raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])
                                for item in items_list:
                                    if not isinstance(item, dict): continue
                                    if item.get('@type') == 'BreadcrumbList': continue
                                    
                                    iid = item.get('@id')
                                    ityp = item.get('@type')
                                    
                                    if iid:
                                        if iid not in items_by_id: items_by_id[iid] = {}
                                        items_by_id[iid].update(item)
                                    elif not ityp:
                                        typeless_fragments.append(item)
                                    else:
                                        other_items.append(item)

                            merged_all = list(items_by_id.values()) + other_items
                            
                            # Identify Primary Product for greedy merging of typeless fragments
                            def is_prod(etyp):
                                if isinstance(etyp, list): return 'Product' in etyp
                                return etyp == 'Product'
                                
                            primary_prod = next((e for e in merged_all if is_prod(e.get('@type'))), None)
                            
                            if primary_prod and typeless_fragments:
                                for frag in typeless_fragments:
                                    primary_prod.update(frag)
                                typeless_fragments = [] # Consumed
                            
                            final_entity_list = merged_all + typeless_fragments

                            # --- 2. FLATTEN STAGE ---
                            flattened_items = []
                            for entity in final_entity_list:
                                etyp = entity.get('@type', '')
                                display_typ = 'Product' if is_prod(etyp) else (etyp[0] if isinstance(etyp, list) and etyp else etyp)
                                
                                row_data = {"entity_typ": display_typ}
                                row_data.update(flatten(entity))
                                
                                # Skip noise rows with no meaningful data beyond keys/metadata
                                if len(row_data) > 2:
                                    flattened_items.append(row_data)

                            if not flattened_items:
                                return ""

                            # --- 3. CSV GENERATION ---
                            active_keys = set()
                            for row in flattened_items:
                                for k, v in row.items():
                                    if v is not None and str(v).strip(): active_keys.add(k)

                            priority = [
                                'entity_typ', '@context', '@type', '@id', 'name', 'url', 'sku', 'mpn', 'image', 'brand', 'description', 
                                'gtin12', 'gtin13', 'gtin8', 'offers-price', 'offers-priceCurrency', 'offers-availability'
                            ]
                            headers = [p for p in priority if p in active_keys]
                            for s in ['YouTube', 'Facebook', 'LinkedIn', 'Twitter']:
                                if s in active_keys and s not in headers: headers.append(s)
                            
                            others = sorted([k for k in active_keys if k not in headers])
                            headers.extend(others)

                            output = io.StringIO()
                            writer = csv.writer(output)
                            writer.writerow(headers)
                            for row in flattened_items:
                                writer.writerow([row.get(h, '') for h in headers])

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