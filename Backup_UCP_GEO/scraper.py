import sys
import json
import os
import asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
from playwright_stealth import Stealth
from playwright.async_api import async_playwright
import extruct
from w3lib.html import get_base_url


# Pre-deployment check: Installs browser if missing in a Linux environment (Cloud)
if os.environ.get('STREAMLIT_RUNTIME_CHECK') or not os.name == 'nt':
    if not os.path.exists("/home/adminuser/.cache/ms-playwright"):
        os.system("playwright install chromium > /dev/null 2>&1")

async def main(url):
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    
    try:
        async with async_playwright() as p:
            # 1. Consolidated Launch: Use all your cloud flags here
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage", # REQUIRED: Prevents memory crashes in Cloud Run
                    "--single-process",        # REQUIRED: Keeps memory footprint low
                    "--no-zygote"
                ]
            )
            
            # 2. Create context and page
            context = await browser.new_context(user_agent=user_agent)
            page = await context.new_page()

            # 3. Apply Stealth to the active page using Jan 2026 Stealth class
            await Stealth().apply_stealth_async(page)

            # 4. RESOURCE ABORT (Optimized for Cloud)
            # Aborts images/CSS to save significant RAM and speed up the audit
            await page.route("**/*.{png,jpg,jpeg,gif,webp,svg,css,woff,woff2}", lambda route: route.abort())

            # --- ASYNC GOTO & DEBUG CAPTURE ---
            import base64
            
            try:
                # 1. We increase the timeout to 60s for Cloud Run and use 'domcontentloaded'
                # This ensures the HTML is fully parsed before we try to extract metadata.
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # 2. Add a short buffer for JavaScript-heavy sites (Under Armour, etc.)
                await page.wait_for_timeout(5000) 
                
                # 3. CLOUD EYES: Capture a screenshot and print it to logs as a Base64 string
                # You can copy the resulting string from your Google Logs to see what the bot sees.
                screenshot = await page.screenshot(type='jpeg', quality=50)
                base64_image = base64.b64encode(screenshot).decode('utf-8')
                sys.stderr.write(f"--- DEBUG SCREENSHOT ---: data:image/jpeg;base64,{base64_image}\n")
                
            except Exception as e:
                sys.stderr.write(f"--- DEBUG: Navigation failed or timed out: {str(e)} ---\n")
                pass # Continue to extract whatever HTML has managed to arrive

            html_content = await page.content()
            current_url = page.url
            
            # LOCAL DEBUG PRINT (Only shows in your local terminal)
            if not os.environ.get('STREAMLIT_RUNTIME_CHECK'):
                page_title = await page.title()
                sys.stderr.write(f"--- DEBUG: Scraped Title: {page_title} ---\n")
            
            await browser.close()
            
            # --- METADATA EXTRACTION ---
            base_url = get_base_url(html_content, current_url)
            data = extruct.extract(
                html_content, 
                base_url=base_url, 
                uniform=True,
                syntaxes=['json-ld', 'microdata']
            )

            # Fast Regex Fallback for embedded JSON-LD
            if not data.get('json-ld'):
                import re
                matches = re.findall(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', html_content, re.DOTALL | re.IGNORECASE)
                fallback = []
                for m in matches:
                    try:
                        parsed = json.loads(m.strip())
                        if isinstance(parsed, list): fallback.extend(parsed)
                        else: fallback.append(parsed)
                    except: continue
                if fallback:
                    data['json-ld'] = fallback

            # Output JSON to stdout for app.py to capture
            sys.stdout.write(json.dumps(data))

    except Exception as e:
        sys.stdout.write(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Use asyncio.run to execute the async main function
        asyncio.run(main(sys.argv[1]))
    else:
        sys.stdout.write(json.dumps({"error": "No URL provided"}))