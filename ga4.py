import os
import uuid
import requests
import streamlit as st

def get_or_set_client_id() -> str:
    """Stable-ish client_id stored in Streamlit session."""
    if "ga_client_id" not in st.session_state:
        st.session_state.ga_client_id = str(uuid.uuid4())
    return st.session_state.ga_client_id

#GA4 Debug Mode 
DEBUG_GA = False  # flip to True when needed

def _build_payload(event_name: str, params: dict | None = None) -> dict:
    event_params = dict(params or {})
    if DEBUG_GA:
        event_params["debug_mode"] = 1

    return {
        "client_id": get_or_set_client_id(),
        "events": [{
            "name": event_name,
            "params": event_params
        }]
    }

def send_ga4_event(event_name: str, params: dict | None = None):
    """Send GA4 event to the real collection endpoint."""
    mid = os.getenv("GA4_MEASUREMENT_ID")
    secret = os.getenv("GA4_API_SECRET")
    if not mid or not secret:
        print("GA4 MP not configured: missing GA4_MEASUREMENT_ID or GA4_API_SECRET")
        return

    url = f"https://www.google-analytics.com/mp/collect?measurement_id={mid}&api_secret={secret}"
    payload = _build_payload(event_name, params)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code >= 300:
            print("GA4 MP HTTP error:", r.status_code, r.text)
        else:
            print("GA4 MP OK:", event_name, r.status_code)
    except Exception as e:
        print("GA4 MP exception:", repr(e))

def send_ga4_event_debug(event_name: str, params: dict | None = None) -> dict:
    """Send GA4 event to debug endpoint and return validation JSON."""
    mid = os.getenv("GA4_MEASUREMENT_ID")
    secret = os.getenv("GA4_API_SECRET")
    if not mid or not secret:
        return {"error": "missing GA4_MEASUREMENT_ID or GA4_API_SECRET"}

    url = f"https://www.google-analytics.com/mp/debug/collect?measurement_id={mid}&api_secret={secret}"
    payload = _build_payload(event_name, params)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    r = requests.post(url, json=payload, headers=headers, timeout=10)
    try:
        return r.json()
    except Exception:
        return {"status_code": r.status_code, "text": r.text}
