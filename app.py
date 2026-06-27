import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import base64
import subprocess
import sys
import nest_asyncio
from pathlib import Path
from datetime import datetime, timedelta
from google.cloud import storage
import uuid
import os
from urllib.parse import urlparse
import google.auth
from google.auth.transport.requests import Request
from ga4 import send_ga4_event
import io



# 0. Set Page Config  (MUST BE THE VERY FIRST STREAMLIT COMMAND)

# Keep this as expanded for desktop users
st.set_page_config(
    page_title="AI-Commerce UCP & GEO Audit | T2 Digital",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# JavaScript for the Mobile "Peek & Contract" behavior
st.html("""
<script>
    // Function to handle the mobile sidebar peek
    function handleMobileSidebar() {
        // Detect if screen width is mobile (typically < 768px)
        const isMobile = window.innerWidth <= 768;
        
        if (isMobile) {
            console.log("Mobile detected: Initiating sidebar peek...");
            
            // Wait 2 seconds (2000ms)
            setTimeout(() => {
                // Find the sidebar close button in the Streamlit DOM
                const buttons = window.parent.document.getElementsByTagName('button');
                for (let i = 0; i < buttons.length; i++) {
                    // Streamlit close button usually has this aria-label
                    if (buttons[i].getAttribute('aria-label') === 'Close sidebar') {
                        buttons[i].click();
                        console.log("Sidebar contracted.");
                        break;
                    }
                }
            }, 2000);
        }
    }

    // Run on load
    handleMobileSidebar();
</script>
""")

# ✅ GA4 server-side heartbeat
send_ga4_event("streamlit_app_loaded", {"app": "ucp_readiness"})



# 1. Silent Auto-Recovery for mobile fetch errors
st.html("""
<script>
window.addEventListener('unhandledrejection', (event) => {
    if (event.reason && event.reason.message && 
        (event.reason.message.includes('Failed to fetch dynamically imported module') || 
         event.reason.message.includes('Loading chunk'))) {
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

def to_bytes(x):
    if isinstance(x, (bytes, bytearray)):
        return bytes(x)
    if isinstance(x, str):
        return x.encode("utf-8")
    raise TypeError(f"Expected str/bytes, got {type(x)}")

GCS_BUCKET = os.getenv("GCS_EXPORT_BUCKET", "t2-ucp-auditor-exports")  # set in env

def upload_csv_and_get_signed_url(csv_data, filename, minutes_valid=15):
    """
    Upload CSV to GCS and return a V4 signed URL that forces download with a friendly filename.
    csv_data can be str or bytes.
    """
    if not isinstance(csv_data, (str, bytes, bytearray)):
        raise TypeError(f"csv_data must be str or bytes, got {type(csv_data)}")

    if not filename.lower().endswith(".csv"):
        filename += ".csv"

    payload = to_bytes(csv_data)

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    object_name = f"exports/{uuid.uuid4().hex}/{filename}"
    blob = bucket.blob(object_name)

    blob.upload_from_string(
        payload,
        content_type="text/csv; charset=utf-8",
    )

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(Request())

    service_account_email = os.getenv("SIGNED_URL_SERVICE_ACCOUNT_EMAIL")
    if not service_account_email:
        raise RuntimeError("SIGNED_URL_SERVICE_ACCOUNT_EMAIL env var is not set")

    signed_url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=minutes_valid),
        method="GET",
        response_disposition=f'attachment; filename="{filename}"',
        response_type="text/csv",
        service_account_email=service_account_email,
        access_token=credentials.token,
    )

    return signed_url

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
    # Clear any previous results when starting a new audit
    st.session_state.pop('audit_blob', None)
    st.session_state.pop('audit_url', None)
    if not url:
        # Optional: track validation failures
        send_ga4_event("audit_submit_missing_url", {"app": "ucp_readiness"})
        st.warning("Please enter a URL.")
    else:
        # ✅ Standardized Domain Extraction for GA4 Tracking
        domain = ""
        path = "/"
        try:
            # Strips 'www.' and paths to get a clean domain string (e.g., 'amazon.com')
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            path = parsed.path or "/"
        except Exception:
            pass

        # Track the initial intent
        send_ga4_event(
            "audit_submit",
            {
                "app": "ucp_readiness",
                "fast_mode": int(bool(fast_mode)),
                "audited_domain": domain,
                "audited_path": path
            }
        )

        try:
            blob = None

            # --- EXECUTION PHASE ---
            if fast_mode:
                with st.spinner("Executing Fast Scan..."):
                    import requests
                    from extruct import extract

                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Cache-Control": "no-cache",
                        "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                        "Sec-Ch-Ua-Mobile": "?0",
                        "Sec-Ch-Ua-Platform": '"Windows"',
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-User": "?1",
                        "Upgrade-Insecure-Requests": "1",
                    }
                    response = requests.get(url, headers=headers, timeout=20)

                    if response.status_code == 200:
                        data = extract(response.text, base_url=url, uniform=True, syntaxes=['json-ld', 'microdata'])
                        blob = json.dumps(data)

                        # ✅ Track success with audited_domain
                        send_ga4_event(
                            "audit_success",
                            {
                                "app": "ucp_readiness", 
                                "fast_mode": 1, 
                                "audited_domain": domain,
                                "audited_path": path
                            }
                        )
                    else:
                        # ✅ Track failure with audited_domain
                        send_ga4_event(
                            "audit_fail_http",
                            {
                                "app": "ucp_readiness", 
                                "fast_mode": 1, 
                                "audited_domain": domain, 
                                "status_code": int(response.status_code)
                            }
                        )
                        st.error(f"Fast Mode Failed: HTTP {response.status_code}. The site may be blocking cloud-based requests. Try Regular Mode instead.")

            else:
                with st.spinner("Launching AI Agent (Playwright)..."):
                    python_exe = sys.executable
                    if python_exe.lower().endswith('streamlit.exe') or python_exe.lower().endswith('streamlit'):
                        python_exe = 'python'

                    result = subprocess.run(
                        [python_exe, "-u", "scraper.py", url],
                        capture_output=True, text=True, timeout=90
                    )

                    blob = result.stdout

                    if result.stderr:
                        sys.stderr.write(result.stderr)

                    # ✅ Track success/failure based on return code
                    if result.returncode == 0 and blob:
                        send_ga4_event(
                            "audit_success",
                            {
                                "app": "ucp_readiness", 
                                "fast_mode": 0, 
                                "audited_domain": domain
                            }
                        )
                    else:
                        send_ga4_event(
                            "audit_fail_scraper",
                            {
                                "app": "ucp_readiness", 
                                "fast_mode": 0, 
                                "audited_domain": domain, 
                                "returncode": int(result.returncode)
                            }
                        )
                        if result.returncode != 0:
                            st.error(f"Playwright Agent Failed (Exit Code {result.returncode})")
                        else:
                            st.error("Playwright Agent returned no data. The site may be blocking cloud-based scraping.")
                        if result.stderr:
                            # Filter out the massive base64 screenshot from the error log display
                            stderr_display = "\n".join(
                                line for line in result.stderr.splitlines()
                                if "DEBUG SCREENSHOT" not in line
                            )
                            if stderr_display.strip():
                                with st.expander("View Error Log"):
                                    st.code(stderr_display[-3000:])  # Last 3KB to avoid UI overload
                        blob = None

        except Exception as e:
            # ✅ Track unexpected exceptions
            send_ga4_event(
                "audit_exception",
                {
                    "app": "ucp_readiness", 
                    "fast_mode": int(bool(fast_mode)), 
                    "audited_domain": domain, 
                    "error_type": type(e).__name__
                }
            )
            st.error(f"System Error during audit execution: {str(e)}")
            blob = None

        # --- CACHE RESULTS IN SESSION STATE ---
        if blob:
            st.session_state['audit_blob'] = blob
            st.session_state['audit_url'] = url

# --- PROCESS RESULTS (persists across reruns) ---
if st.session_state.get('audit_blob'):
    blob = st.session_state['audit_blob']
    url = st.session_state.get('audit_url', '')
    try:
        parsed_test = json.loads(blob) 
        
        if isinstance(parsed_test, dict) and "error" in parsed_test:
            if parsed_test.get('error') == 'cloudflare_blocked':
                st.error("🛡️ **Cloudflare Protection Detected**")
                st.markdown("""
This site uses **Cloudflare bot protection** that blocks cloud-based auditors. 
This is a limitation of running from a cloud server — Cloudflare blocks all major cloud provider IPs (Google Cloud, AWS, Azure).

**What you can do:**
1. **Try Fast Mode** — Toggle "Fast Mode" above and re-audit. It uses a different method that sometimes bypasses Cloudflare.
2. **Run locally** — Clone the repo and run `streamlit run app.py` from your own machine. Your residential IP won't be blocked.
3. **Try a different product URL** — Not all sites use Cloudflare. Sites without bot protection will work perfectly.
                """)
            else:
                st.error(f"Agent Error: {parsed_test['error']}")
            with st.expander("View Raw Output"):
                st.code(blob)
        else:
            if len(blob) < 500:
                st.warning("⚠️ Partial data received. The site may be blocking the agent.")
                with st.expander("View Raw Output"):
                    st.code(blob)
                    
            # 1. RUN AUDITS
            audit_data = perform_ucp_audit(blob)
            geo_results = calculate_geo_score(audit_data.get('metadata', {}))
            st.success("Audit Complete!")

            # (Removed redundant and broken download link block here)
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

            # --- SCHEMA WARNINGS ---
            if audit_data.get('warnings'):
                for warning in audit_data['warnings']:
                    st.warning(warning)

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

            import io, csv

            JOINER = " | "

            def _is_scalar(x):
                return x is None or isinstance(x, (str, int, float, bool))

            def _flatten(obj, prefix="", out=None):
                """
                Flatten nested dict/list into columns like:
                offers-price, brand-name, aggregateRating-ratingValue, etc.
                Lists become joined with " | ".
                """
                if out is None:
                    out = {}

                # Scalar
                if _is_scalar(obj):
                    if prefix:
                        out[prefix] = "" if obj is None else str(obj)
                    return out

                # Dict
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        key = f"{prefix}-{k}" if prefix else str(k)
                        _flatten(v, key, out)
                    return out

                # List
                if isinstance(obj, list):
                    # list of scalars -> join
                    if all(_is_scalar(x) for x in obj):
                        if prefix:
                            out[prefix] = JOINER.join("" if x is None else str(x) for x in obj)
                        return out

                    # list of dicts/mixed -> flatten each, then join per field
                    flattened_items = []
                    for item in obj:
                        if isinstance(item, dict):
                            flattened_items.append(_flatten(item, prefix="", out={}))
                        else:
                            flattened_items.append({"_value": "" if item is None else str(item)})

                    keys = sorted({k for d in flattened_items for k in d.keys()})
                    for k in keys:
                        col = f"{prefix}-{k}" if prefix else k
                        out[col] = JOINER.join(d.get(k, "") for d in flattened_items)

                    return out

                # Fallback
                if prefix:
                    out[prefix] = str(obj)
                return out


            def _collect_entities(metadata_blob):
                """
                Collect entities from json-ld + microdata only; expand @graph.
                RDFa excluded.
                """
                items = []
                for syntax in ["json-ld", "microdata"]:
                    raw = metadata_blob.get(syntax, [])
                    if isinstance(raw, dict):
                        raw = [raw]
                    if isinstance(raw, list):
                        items.extend([x for x in raw if isinstance(x, dict)])

                expanded = []
                for it in items:
                    if "@graph" in it and isinstance(it["@graph"], list):
                        expanded.extend([g for g in it["@graph"] if isinstance(g, dict)])
                    else:
                        expanded.append(it)

                # keep only entities with @type
                return [e for e in expanded if e.get("@type")]


            def generate_metadata_csv_flat(metadata_blob):
                """
                One row per schema entity, with flattened columns.
                Columns vary by site (union of keys across entities).
                """
                entities = _collect_entities(metadata_blob)

                rows = []
                all_cols = set()

                #Skip these items in Schema
                SKIP_TYPES = {"BreadcrumbList", "ProductGroup"}

                for ent in entities:
                    et = ent.get("@type")
                    # @type can be a list sometimes
                    if isinstance(et, list):
                        et_list = set(et)
                        if et_list & SKIP_TYPES:
                            continue
                        et = et[0] if et else ""
                    else:
                        if et in SKIP_TYPES:
                            continue

                    flat = _flatten(ent)
                    flat["entity_typ"] = et or flat.get("@type", "")
                    rows.append(flat)
                    all_cols.update(flat.keys())

                # Put common fields first, rest alpha
                preferred = ["entity_typ", "@context", "@type", "@id", "name", "url", "sku", "image", "description"]
                columns = preferred + sorted(c for c in all_cols if c not in preferred)

                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
                writer.writeheader()
                for r in rows:
                    writer.writerow(r)

                return output.getvalue()



                # --- 1. COLLECT & MERGE STAGE ---
                items_by_id = {}
                typeless_fragments = []
                other_items = []
                
                for syntax in ['json-ld', 'microdata']:
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
                    if isinstance(etyp, list): return 'Product' in etyp or 'IndividualProduct' in etyp
                    return etyp == 'Product' or etyp == 'IndividualProduct'
                    
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

            # --- GENERATE NICE CSV (Exploded Rows) ---
            metadata_raw = audit_data.get('metadata', {})
            rows = []

            # Loop through each metadata type and its list of findings
            for m_type, entries in metadata_raw.items():
                for entry in entries:
                    # Create a flat dictionary for this specific finding
                    flat_row = {'Audit_Type': m_type}
                    if isinstance(entry, dict):
                        flat_row.update(entry) # Expands {'@id': '123'} into columns
                    else:
                        flat_row['Value'] = entry
                    rows.append(flat_row)

            # Build clean, flattened CSV directly from extracted metadata
            metadata_blob = audit_data.get("metadata", {})

            if metadata_blob:
                csv_data = generate_metadata_csv_flat(metadata_blob)
            else:
                csv_data = "Status\nNo Metadata Found\n"

            # iii. Filename: ucp-geo-audit-metadata-[domainname]-[mmddyyyy]-[hh:mm:ss]
            domain = urlparse(url).netloc.replace('www.', '').replace('.', '-')
            now = datetime.now()
            date_str = now.strftime("%m%d%Y")
            time_str = now.strftime("%H-%M-%S") # Use - instead of : for filesystem compatibility
            filename = f"ucp-geo-audit-metadata-{domain}-{date_str}-{time_str}.csv"
            
            # iv. Download Button
            col_dl1, col_dl2 = st.columns([1, 2])

            with col_dl1:
                clicked = st.download_button(
                    label="Download Metadata Report",
                    data=to_bytes(csv_data),
                    file_name=filename,
                    mime="text/csv;charset=utf-8"
                )
                if clicked:
                    send_ga4_event("download_csv_clicked", {"app": "ucp_readiness", "download_type": "builtin"})

            with col_dl2:
                # Only attempt enterprise download if GCS signing is configured
                if os.getenv("SIGNED_URL_SERVICE_ACCOUNT_EMAIL"):
                    try:
                        signed_url = upload_csv_and_get_signed_url(csv_data, filename, minutes_valid=15)

                        send_ga4_event("download_link_generated", {
                            "app": "ucp_readiness",
                            "download_type": "signed_url",
                            "minutes_valid": 15
                        })

                        st.link_button("Download Metadata Report (enterprise-safe link)", signed_url, use_container_width=True)
                        st.caption("If your company blocks in-app downloads, use the enterprise-safe link.")

                    except Exception as e:
                        send_ga4_event("download_link_failed", {
                            "app": "ucp_readiness",
                            "download_type": "signed_url",
                            "error_type": type(e).__name__
                        })

                        st.warning("Enterprise-safe download link unavailable.")
                        st.caption(str(e))

            
            with st.expander("Fallback: Copy Metadata Report CSV if download is blocked"):
                st.text_area("CSV Output", csv_data, height=250)
                st.caption("If your company blocks downloads, copy/paste this into a .csv file locally.")

            st.markdown("---")
            with st.expander("🔍 Debug: View Raw Metadata Found", expanded=False):
                st.json(audit_data.get('metadata', {}), expanded=True)

    except json.JSONDecodeError:
        st.error("Data Corruption: Invalid JSON returned from scraper.")
        with st.expander("View Raw Output"):
            st.text(blob[:1000])


st.divider()
st.caption("T2 Digital © 2026")