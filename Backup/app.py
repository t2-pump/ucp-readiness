import streamlit as st
import json
import base64
import subprocess
import sys
import nest_asyncio
from pathlib import Path
from logic import perform_ucp_audit  # Centralized logic function

#0. Set Page Config
st.set_page_config(page_title="AI-Commerce UCP & GEO Audit | T2 Digital", page_icon="🤖", layout="wide")

#1. Fix for Streamlit/Playwright event loop conflict
nest_asyncio.apply()

#2. Define the function to convert images to base64
def img_to_bytes(img_path):
    img_bytes = Path(img_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()
    return encoded

#3. Define the variable (Make sure 't2_logo.png' is in your folder)
# If your file has a different name, change it here.
try:
    logo_base64 = img_to_bytes("t2_logo.png")
except FileNotFoundError:
    logo_base64 = "" # Fallback if file is missing
    
#4. Inject CSS for mobile-specific font sizing
st.html("""
<style>
    /* Desktop Headline Size (Default) */
    .responsive-headline {
        font-size: 2.5rem;
        font-weight: 700;
        margin-top: 10px;
        color: #31333F;
    }

    /* Mobile Headline Size (Screens smaller than 768px) */
    @media (max-width: 768px) {
        .responsive-headline {
            font-size: 1.5rem; /* Smaller font for mobile */
            line-height: 1.2;
        }
    }
</style>
""")

#5. Render Logo and Headline (Stacked)
st.html(f"""
<style>
    /* Default Logo Size for Desktop */
    .logo-container img {{
        width: 120px;
        transition: width 0.3s ease; /* Smooth transition if window is resized */
    }}

    /* Desktop Headline Size */
    .responsive-headline {{
        font-size: 2.5rem;
        font-weight: 700;
        margin-top: 10px;
        color: #31333F;
    }}

    /* Mobile-Specific Adjustments (Screens < 768px) */
    @media (max-width: 768px) {{
        .logo-container img {{
            width: 60px; /* 50% smaller than 120px */
        }}
        .responsive-headline {{
            font-size: 1.5rem;
            line-height: 1.2;
        }}
    }}
</style>

<div class="logo-container" style="margin-bottom: 15px;">
    <a href="https://www.t2-digital.com" target="_blank">
        <img src="data:image/png;base64,{logo_base64}">
    </a>
</div>

<div class="responsive-headline">
    AI-Commerce UCP & GEO Audit
</div>
""")

# 5. Add Subtitle
st.markdown("Compliance testing for the **2026 Universal Commerce Protocol.**")

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    #st.image("logo.png", width=100) # Optional: Adds your T2 Digital logo to the sidebar
    st.title("UCP Strategy & Support")
    st.info("""
    **Need help with your UCP Strategy?**
    If your store is scoring below 80%, your AI-Commerce discoverability may be at risk.
    """)
    st.link_button("Contact Me", "https://www.t2-digital.com/connect", use_container_width=True)
    st.markdown("---")
    
    st.info("""
    **Pro Tip:** If Regular Mode is timing out, ensure you are using a direct product URL and not a category page.
    """)

# 6. Helper Functions
def img_to_bytes(img_path):
    try:
        img_bytes = Path(img_path).read_bytes()
        encoded = base64.b64encode(img_bytes).decode()
        return encoded
    except FileNotFoundError:
        return None

# 7. Input Form
with st.form("audit_form"):
    url = st.text_input("Enter Product URL to Audit:", placeholder="https://example.com/product/123")
    fast_mode = st.toggle("Fast Mode", value=False, help="Bypasses browser for speed. May fail on high-security sites.")
    submitted = st.form_submit_button("Audit URL", type="primary")

if submitted:
    if not url:
        st.warning("Please enter a URL.")
    else:
        try:
            blob = None
            
            if fast_mode:
                # --- FAST MODE PATH ---
                with st.spinner("Executing Fast Scan..."):
                    # Log the search URL explicitly for Cloud Run tracking
                    sys.stdout.write(f"--- STARTING AUDIT: {url} ---\n")
                    
                    import requests
                    from extruct import extract
                    
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                    }
                    
                    try:
                        response = requests.get(url, headers=headers, timeout=15)
                    
                        if response.status_code == 200:
                            # Extract directly from the raw HTML
                            data = extract(response.text, base_url=url, uniform=True, syntaxes=['json-ld', 'microdata'])
                            blob = json.dumps(data)
                        elif response.status_code == 403:
                            st.error("Fast Mode Blocked (403): This site requires the AI Agent to bypass security. Please disable 'Fast Mode' and try again.")
                        else:
                            st.error(f"Fast Mode Failed: Site returned status {response.status_code}")
                    except Exception as req_err:
                        st.error(f"Fast Mode Connection Error: {str(req_err)}")
            
            else:
                # --- AGENTIC MODE PATH ---
                with st.spinner("Launching AI Agent..."):
                    # Log the search URL explicitly for Cloud Run tracking
                    sys.stdout.write(f"--- STARTING AUDIT: {url} ---\n")

                    try:
                        # We use '-u' for unbuffered logs and 90s for Cloud Run headroom
                        result = subprocess.run(
                            [sys.executable, "-u", "scraper.py", url], 
                            capture_output=True, 
                            text=True, 
                            shell=False, 
                            encoding='utf-8', 
                            timeout=90
                        )

                        blob = result.stdout
                        stderr = result.stderr

                        # CRITICAL: Forward EVERYTHING to Cloud Logs so you can see the DEBUG lines
                        if blob:
                            sys.stdout.write(f"--- SCRAPER STDOUT ---\n{blob}\n")
                        if stderr:
                            sys.stderr.write(f"--- SCRAPER STDERR ---\n{stderr}\n")

                        # Standard Streamlit UI logic
                        if result.returncode != 0:
                            st.error(f"AI Agent Error (Code {result.returncode})")
                            with st.expander("View Technical Details"):
                                st.code(stderr if stderr else "No error logs returned.")
                        elif not blob:
                            st.warning("The agent finished but no metadata was found. This site may be using advanced bot-detection.")

                    except subprocess.TimeoutExpired:
                        st.error("The audit timed out (90s limit reached).")
                        sys.stderr.write("--- ERROR: Subprocess reached 90s timeout limit ---\n")
            
            # --- PROCESS RESULTS ---
            if blob:
                # 1. Check if the returned data is suspiciously small (indicating an empty page)
                if len(blob) < 500:
                    st.warning("⚠️ The site responded too slowly for a deep scan. Try disabling 'Fast Mode' or running the audit again.")
                    with st.expander("Debug: Raw Fragment Captured"):
                        st.text(blob)
                else:
                    # 2. Proceed to the centralized auditor in logic.py
                    audit_data = perform_ucp_audit(blob)  

                    # 3. Handle cases where the site loaded but 'Product' schema was missing
                    if audit_data.get("score") == 0:
                        st.warning("⚠️ No UCP-compatible Product data was found on this page.")
                        with st.expander("Debug: See what the scraper found"):
                            try:
                                # Ensure we can parse the blob before listing keys
                                raw_data = json.loads(blob)
                                st.write("Raw Metadata Keys Found:", list(raw_data.keys()))
                                st.json(raw_data)
                            except:
                                st.write("Raw Output (Unstructured):")
                                st.text(blob)
                    else:
                        # 4. Success state
                        st.success("Audit Complete!")
                        
                        # --- NEW: DISPLAY RESULTS ON SCREEN ---
                        col1, col2 = st.columns([1, 2])
                    
                        with col1:
                            st.subheader("Readiness Score")
                            score = audit_data['score']
                            st.metric(label="UCP Readiness", value=f"{score}%")
                        
                            if score == 100:
                                st.success("Perfect Score! 🚀")
                            elif score >= 80:
                                st.info("Good to go! Minor gaps.")
                            elif score >= 50:
                                st.warning("Needs work.")
                            else:
                                st.error("Critical deficiencies.")

                        with col2:
                            st.subheader("Core Requirements")
                            
                            for key, item in audit_data['results'].items():
                                label = f"**{item['name']}**"
                                score_str = f"({item['points']}/{item['max_points']})"

                                # 1. Render Status Bar
                                if item['status'] == 'Green':
                                    st.success(f"✅ {label} (Passed) {score_str}")
                                elif item['status'] == 'Yellow':
                                    st.warning(f"⚠️ {label}: {item['msg']} {score_str}")
                                else:
                                    st.error(f"❌ {label}: {item['msg']} {score_str}")

                                # 2. Render Instructions ONLY for non-Green items
                                if item['status'] != 'Green':
                                    with st.expander(f"How to fix {item['name']}?", expanded=False):
                                        if key == "gtin":
                                            st.markdown("""
                                            **Missing Identifiers**
                                            AI agents require unique IDs to verify products. Please add **ONE** of the following:
                                            - **UPC (GTIN-12)**: Standard North American barcode.
                                            - **EAN (GTIN-13)**: International/European barcode.
                                            - **ISBN**: For books and publications.
                                            """)
                                        elif key == "brand":
                                            st.markdown("""
                                            **Missing Brand or Images**
                                            Ensure your Schema includes a `brand` string or object and at least one valid `image` URL. AI agents use these for visual verification and trust.
                                            """)
                                        elif key == "org":
                                            st.markdown("""
                                            **Missing Organization Link**
                                            Connect your product to your store. Add a `seller` or `offeredBy` object within your **Offer** that includes your store's name and official URL.
                                            """)
                                        elif key == "shipping":
                                            st.markdown("""
                                            **Missing Shipping Details**
                                            Agents cannot calculate "landed cost" without structured shipping rates. Add a `shippingDetails` object to your **Offer** schema.
                                            """)
                                        elif key == "returns":
                                            st.markdown("""
                                            **Missing Return Policy**
                                            Machine-readable return policies are required for autonomous transactions. Add a `hasMerchantReturnPolicy` object to your **Offer**.
                                            """)
                                        elif key == "ucp_comp":
                                            st.markdown("""
                                            **Option A: Standard AI-Friendly**
                                            ```json
                                            "isAIFriendly": true
                                            ```
                                            **Option B: Full UCP Certification**
                                            ```json
                                            "ucpCompatibility": "Full"
                                            ```
                                            """)
                                        elif key == "ucp_use":
                                            st.markdown("""
                                            **Option A: Standard Retail Actions**
                                            ```json
                                            "ucpUseCase": ["Purchase", "PriceCheck", "InventoryVerify"]
                                            ```
                                            **Option B: Autonomous Agentic Intent**
                                            Use a direct intent definition URI:
                                            ```json
                                            "intentDefinition": "[https://ucp.org/intents/one-time-purchase](https://ucp.org/intents/one-time-purchase)"
                                            ```
                                            """)
                        st.markdown("---")
                    with st.expander("Debug: Full UCP Manifest Preview"):
                        st.json(audit_data)
        
        except subprocess.TimeoutExpired:
            st.error("The scan timed out after 30 seconds. This site may be too heavy for the cloud server.")
        except Exception as e:
            st.error(f"System Error: {str(e)}")
            st.exception(e) # Provides a traceback for debugging during development

st.markdown("---")
st.caption("T2 Digital © 2026")





