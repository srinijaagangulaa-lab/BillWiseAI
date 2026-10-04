"""
app.py - BillWise AI
Multimodal AI Receipt Analyzer, Expense Tracker, and Smart Bill Splitter.

Workshop-style architecture inspired by MacroSnap:
Onboarding -> Gemini Chat -> Receipt Image -> Structured JSON Extraction ->
Python Arithmetic Validation -> Bill Splitting -> Conversation -> Summary -> Action Layer.
"""

import os
import io
import json
import re
import time
import random
import smtplib
import urllib.parse
import hashlib
import uuid
import textwrap
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List
from twilio.rest import Client

import streamlit as st
import pandas as pd
from PIL import Image, ImageOps
from pydantic import BaseModel, Field
import requests

from email.message import EmailMessage

from google import genai
from google.genai import types
from google.genai import errors

from prompts import (
    SYSTEM_PROMPT,
    RECEIPT_EXTRACTION_PROMPT,
    SUMMARY_REQUEST_PROMPT,
    WELCOME_MESSAGE_TEMPLATE,
)

# =====================================================================
# 1. CONFIGURATION
# =====================================================================
DEFAULT_MODEL_NAME = "gemini-3-flash-preview"


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieve secret safely from Streamlit secrets, session_state, or environment variables."""
    try:
        if hasattr(st, "secrets") and key in st.secrets and st.secrets[key]:
            val = str(st.secrets[key]).strip()
            if val and not val.startswith("your-") and val != "YOUR_GEMINI_API_KEY":
                return val
    except Exception:
        pass
    
    if hasattr(st, "session_state") and key in st.session_state and st.session_state[key]:
        return str(st.session_state[key]).strip()
        
    return os.environ.get(key, default)


def get_configured_model() -> str:
    """Retrieve the configured Gemini model name."""
    return get_secret("GEMINI_MODEL", DEFAULT_MODEL_NAME) or DEFAULT_MODEL_NAME


MODEL_NAME = get_configured_model()

st.set_page_config(
    page_title="BillWise AI - Snap it. Understand it. Split it.",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================================================================
# BILLWISE AI - PREMIUM UI STYLING
# ================================================================
st.markdown(
    """
    <style>

    :root {
        --bw-bg: #090b11;
        --bw-panel: #11151f;
        --bw-border: #262d3a;
        --bw-text: #f5f7fb;
        --bw-muted: #929bad;
        --bw-purple: #8b5cf6;
        --bw-pink: #ec4899;
    }

    .stApp {
        background:
            radial-gradient(circle at 50% -12%, rgba(139,92,246,.18), transparent 34%),
            radial-gradient(circle at 100% 35%, rgba(236,72,153,.08), transparent 28%),
            var(--bw-bg);
        color: var(--bw-text);
    }

    .block-container {
        max-width: 1220px;
        padding-top: 2.2rem;
        padding-bottom: 4rem;
    }

    .bw-hero {
        text-align: center;
        padding: 1.2rem 0 1.6rem;
        animation: bw-fade-up .65s ease-out both;
    }

    .bw-logo {
        width: 72px;
        height: 72px;
        margin: 0 auto .7rem;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 22px;
        background: linear-gradient(145deg, rgba(139,92,246,.18), rgba(236,72,153,.12));
        border: 1px solid rgba(167,139,250,.25);
        box-shadow: 0 18px 50px rgba(139,92,246,.16);
        font-size: 2.3rem;
        animation: bw-float 4s ease-in-out infinite;
    }

    .bw-title {
        margin: 0;
        font-size: clamp(2.35rem, 5vw, 3.6rem);
        line-height: 1;
        font-weight: 850;
        letter-spacing: -.055em;
        background: linear-gradient(100deg, #c4b5fd 5%, #a78bfa 42%, #f9a8d4 95%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .bw-subtitle { margin-top: .8rem; color: #c5cad6; font-size: 1.05rem; font-weight: 600; }
    .bw-tagline { margin-top: .4rem; color: var(--bw-muted); font-size: .9rem; }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #11141c 0%, #0d1017 100%);
        border-right: 1px solid #202633;
    }

    section[data-testid="stSidebar"] > div { padding: 1.15rem .95rem 1.5rem; }
    section[data-testid="stSidebar"] h1 { font-size: 1.4rem !important; font-weight: 800 !important; }
    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { font-weight: 750 !important; }
    section[data-testid="stSidebar"] hr { border-color: #252b37; margin: 1rem 0; }

    .bw-sidebar-brand { padding: .55rem .2rem .25rem; animation: bw-fade-in .5s ease-out both; }
    .bw-sidebar-brand-title {
        font-size: 1.4rem; font-weight: 820;
        background: linear-gradient(90deg, #c4b5fd, #f9a8d4);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    }
    .bw-sidebar-brand-sub { color: #858d9d; font-size: .78rem; margin-top: .25rem; }

    .bw-side-card {
        background: linear-gradient(145deg, #141923, #10141c);
        border: 1px solid #282f3c; border-radius: 14px; padding: .85rem .9rem;
        margin: .45rem 0; box-shadow: 0 10px 25px rgba(0,0,0,.14);
    }
    .bw-side-label { color: #7f899b; font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; font-weight: 700; }
    .bw-side-value { color: #e7eaf0; font-weight: 650; margin-top: .18rem; word-break: break-word; }

    .stButton > button, .stLinkButton > a, button[kind="primary"] {
        border-radius: 11px !important; min-height: 44px; font-weight: 700 !important;
        transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease !important;
    }
    .stButton > button:hover, .stLinkButton > a:hover {
        transform: translateY(-2px); border-color: rgba(139,92,246,.75) !important;
        box-shadow: 0 10px 25px rgba(139,92,246,.13);
    }
    button[kind="primary"] {
        background: linear-gradient(100deg, #7c3aed, #db2777) !important;
        border: 0 !important; color: white !important; box-shadow: 0 8px 22px rgba(124,58,237,.18);
    }

    button[data-baseweb="tab"] { color: #8f98aa !important; font-weight: 700 !important; font-size: .88rem !important; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #c4b5fd !important; }
    div[data-baseweb="tab-highlight"] { background: linear-gradient(90deg, #8b5cf6, #ec4899) !important; height: 3px !important; border-radius: 99px !important; }

    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, div[data-baseweb="textarea"] > div {
        background: #141923 !important; border: 1px solid #2b3240 !important; border-radius: 10px !important;
    }
    div[data-baseweb="input"] > div:focus-within, div[data-baseweb="select"] > div:focus-within, div[data-baseweb="textarea"] > div:focus-within {
        border-color: #8b5cf6 !important; box-shadow: 0 0 0 1px rgba(139,92,246,.7) !important;
    }
    input, textarea { color: #f5f7fb !important; }
    label { color: #d5d9e2 !important; font-weight: 650 !important; }

    section[data-testid="stFileUploaderDropzone"] {
        background: linear-gradient(145deg, #141923, #10141c) !important;
        border: 1px dashed #3a4354 !important; border-radius: 16px !important; min-height: 145px; transition: all .2s ease;
    }
    section[data-testid="stFileUploaderDropzone"]:hover { border-color: #8b5cf6 !important; background: #171c27 !important; transform: translateY(-1px); }
    div[data-testid="stCameraInput"] { border-radius: 16px; overflow: hidden; border: 1px solid #2a303d; }

    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #141923, #10141c); border: 1px solid #282f3c;
        border-radius: 14px; padding: 1rem; box-shadow: 0 10px 25px rgba(0,0,0,.10);
    }
    div[data-testid="stMetricLabel"] { color: #858ea0 !important; }
    div[data-testid="stMetricValue"] { color: #f7f8fb !important; }
    div[data-testid="stExpander"] { background: #11161f; border: 1px solid #282f3c; border-radius: 12px; }
    div[data-testid="stAlert"] { border-radius: 11px !important; }

    .bw-onboarding { max-width: 760px; margin: 1rem auto 0; animation: bw-fade-up .65s ease-out both; }
    .bw-onboarding-hero { text-align: center; padding: 1rem 0 1.4rem; }
    .bw-onboarding-title {
        font-size: clamp(2.2rem, 5vw, 3.4rem); font-weight: 850; letter-spacing: -.055em;
        background: linear-gradient(100deg, #c4b5fd, #f9a8d4); -webkit-background-clip: text;
        -webkit-text-fill-color: transparent; background-clip: text;
    }
    .bw-onboarding-subtitle { color: #8f98a8; margin-top: .65rem; font-size: .98rem; }
    .bw-form-card {
        background: linear-gradient(145deg, rgba(19,24,34,.97), rgba(13,17,24,.98));
        border: 1px solid #2b3240; border-radius: 20px; padding: 2rem;
        box-shadow: 0 25px 80px rgba(0,0,0,.35), 0 0 45px rgba(139,92,246,.055);
    }
    div[data-testid="stForm"] {
        background: linear-gradient(145deg, rgba(19,24,34,.97), rgba(13,17,24,.98));
        border: 1px solid #2b3240;
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 25px 80px rgba(0,0,0,.35), 0 0 45px rgba(139,92,246,.055);
    }
    .bw-form-title { text-align: center; font-size: 1.55rem; font-weight: 800; color: #f4f6fa; }
    .bw-form-subtitle { text-align: center; color: #838c9d; font-size: .88rem; margin: .4rem 0 1.4rem; }
    .bw-feature-row { display: flex; justify-content: center; gap: .65rem; flex-wrap: wrap; margin: .9rem 0 1.2rem; }
    .bw-feature-pill { border: 1px solid #2c3442; background: #121720; color: #b6becd; border-radius: 999px; padding: .4rem .7rem; font-size: .75rem; }

    .share-card {
        background: linear-gradient(145deg, #151a24, #11151d); border: 1px solid #2c3442;
        border-left: 3px solid #8b5cf6; padding: 1rem; border-radius: 12px; margin: .8rem 0;
    }

    @keyframes bw-fade-up { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes bw-fade-in { from { opacity: 0; } to { opacity: 1; } }
    @keyframes bw-float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }

    @media (max-width: 800px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        .bw-form-card { padding: 1.3rem; }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =====================================================================
# 2. DATA SCHEMAS & MODELS
# =====================================================================
class ReceiptItem(BaseModel):
    """Represents an individual item on a receipt."""
    name: str = Field(description="Name or description of the purchased item")
    quantity: float = Field(default=1.0, description="Quantity of items purchased")
    unit_price: Optional[float] = Field(default=None, description="Unit price per item if visible")
    total_price: float = Field(description="Total price for this line item")


class ReceiptData(BaseModel):
    """Structured receipt data extracted by Gemini."""
    is_receipt: bool = Field(default=True, description="True if image contains a valid receipt/bill")
    merchant: Optional[str] = Field(default=None, description="Merchant, vendor, or store name")
    receipt_number: Optional[str] = Field(default=None, description="Receipt, invoice, or order number if visible")
    date: Optional[str] = Field(default=None, description="Transaction date in YYYY-MM-DD or printed format")
    time: Optional[str] = Field(default=None, description="Transaction time if printed on receipt")
    currency: str = Field(default="₹", description="Currency symbol or 3-letter code")
    items: List[ReceiptItem] = Field(default_factory=list, description="List of itemized purchases")
    subtotal: Optional[float] = Field(default=None, description="Pre-tax subtotal amount")
    tax: Optional[float] = Field(default=None, description="Total tax amount")
    discount: Optional[float] = Field(default=0.0, description="Total discount applied")
    tip_or_service_charge: Optional[float] = Field(default=0.0, description="Service charge, tip, or fee")
    total: Optional[float] = Field(default=None, description="Grand total payable printed on receipt")
    payment_method: Optional[str] = Field(default=None, description="Payment method if printed")
    notes_or_uncertainties: Optional[str] = Field(default=None, description="Any unreadable or ambiguous parts")


class ReceiptValidationResult(BaseModel):
    """Result of deterministic Python arithmetic validation."""
    status: str  # "VERIFIED", "MISMATCH", "MISSING_TOTAL", "NOT_A_RECEIPT"
    is_valid: bool
    items_sum: float
    expected_subtotal: float
    expected_total: float
    detected_total: Optional[float]
    difference: float
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class PersonShare(BaseModel):
    """Represents an individual's share of the split bill."""
    name: str
    items_subtotal: float = 0.0
    assigned_items: List[Dict[str, Any]] = Field(default_factory=list)
    tax_share: float = 0.0
    discount_share: float = 0.0
    tip_or_service_share: float = 0.0
    total_share: float = 0.0


class BillSplitResult(BaseModel):
    """Result of bill splitting calculation."""
    mode: str  # "equal" or "item_based"
    total_bill: float
    currency: str
    num_people: int
    allocation_rule: str
    shares: List[PersonShare]
    reconciled: bool
    reconciled_sum: float
    notes: Optional[str] = None


class ActionResult(BaseModel):
    """Result returned by the action/sharing layer."""
    success: bool
    provider: str
    message: str
    action_url: Optional[str] = None
    details: Dict[str, Any] = {}


# =====================================================================
# 3. GEMINI CLIENT & ERROR DIAGNOSTICS
# =====================================================================
def log_gemini_diagnostic(event: str, **kwargs):
    """Safe diagnostic logging for development (NEVER logs sensitive API key values)."""
    details = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    print(f"[BillWise Gemini Diagnostic] Event: {event} | {details}")


def get_api_key() -> Optional[str]:
    """Retrieve Gemini API Key safely without exposing it."""
    return get_secret("GEMINI_API_KEY")


@st.cache_resource(show_spinner=False)
def get_gemini_client(api_key: Optional[str] = None) -> genai.Client:
    """Get or create a cached Google GenAI Client instance."""
    key = api_key or get_api_key()
    configured_model = get_configured_model()
    if not key or key in ("YOUR_GEMINI_API_KEY", "your-gemini-api-key-here"):
        log_gemini_diagnostic("client_init", initialized=False, reason="No key configured")
        raise ValueError(
            "Gemini API configuration is missing. "
            "Please configure GEMINI_API_KEY in .streamlit/secrets.toml or enter it during onboarding."
        )
    log_gemini_diagnostic("client_init", initialized=True, model=configured_model)
    return genai.Client(api_key=key)


def extract_error_details(error: Exception) -> tuple[Optional[int], Optional[str], str]:
    """Extract (status_code, status_name, clean_message) from an exception."""
    code = getattr(error, "code", None)
    status = getattr(error, "status", None)
    msg = getattr(error, "message", str(error)) or str(error)

    if code is None:
        err_str = str(error)
        code_match = re.search(r"\b(400|401|403|404|408|429|500|502|503|504)\b", err_str)
        if code_match:
            try:
                code = int(code_match.group(1))
            except (ValueError, TypeError):
                code = None

    if status is None:
        err_upper = str(error).upper()
        for candidate in ["UNAVAILABLE", "RESOURCE_EXHAUSTED", "UNAUTHENTICATED", "PERMISSION_DENIED", "NOT_FOUND", "INVALID_ARGUMENT"]:
            if candidate in err_upper:
                status = candidate
                break

    return code, status, msg


def is_daily_quota_error(e: Exception) -> bool:
    """Check if exception represents daily free-tier request quota exhaustion."""
    err_str = (str(e) + " " + getattr(e, "message", "")).lower()
    daily_quota_indicators = [
        "generaterequestsperday",
        "generate_content_free_tier_requests",
        "daily quota",
        "quota exceeded",
        "generaterequestsperdayperprojectpermodel-freetier",
        "free_tier_requests"
    ]
    return any(ind in err_str for ind in daily_quota_indicators)


def is_transient_error(e: Exception) -> bool:
    """Check if exception is a transient Google server/quota error eligible for retry."""
    # Permanent errors and confirmed daily quota exhaustion must NOT be retried
    if isinstance(e, ValueError) and "API key" in str(e):
        return False
        
    if is_daily_quota_error(e):
        return False

    code, status, _ = extract_error_details(e)
    
    # Permanent HTTP statuses
    if code in (400, 401, 403, 404):
        return False
    if status in ("UNAUTHENTICATED", "PERMISSION_DENIED", "NOT_FOUND", "INVALID_ARGUMENT"):
        return False
        
    # Transient HTTP statuses (excluding daily quota exhaustion checked above)
    if code in (408, 429, 500, 502, 503, 504):
        return True
    if status in ("UNAVAILABLE", "RESOURCE_EXHAUSTED"):
        return True
    
    err_str = (str(e) + " " + type(e).__name__).lower()
    transient_indicators = [
        "503", "unavailable", "high demand", "temporarily busy",
        "429", "resource_exhausted", "quota", "rate limit",
        "500", "internal server error",
        "502", "bad gateway",
        "504", "gateway timeout",
        "408", "request timeout",
        "servererror", "remoteprotocolerror", "connection reset",
        "connection closed", "connecterror", "readtimeout",
        "protocol error"
    ]
    return any(ind in err_str for ind in transient_indicators)


def format_gemini_error(error: Exception) -> str:
    """
    Format exceptions into distinct, clear, actionable, and user-friendly messages.
    Categorized into:
    A. Configuration error
    B. Authentication / API key error
    C. Invalid request
    D. Unsupported model
    E. Rate limit & Daily Quota
    F. Temporary Gemini service unavailable / 503
    G. Image processing error
    H. Unexpected error
    """
    if isinstance(error, ValueError) and "API key" in str(error):
        return (
            "⚙️ **Configuration Error:** Gemini API configuration is missing. "
            "Please configure the `GEMINI_API_KEY` in `.streamlit/secrets.toml` or enter it during onboarding."
        )

    # Check for daily quota exhaustion first
    if is_daily_quota_error(error):
        return (
            "🚫 **Gemini Daily Quota Reached:** Your Gemini API project's daily free-tier request quota has been reached. "
            "You can use 🧪 **Demo/Test Mode** to continue testing BillWise without making Gemini API requests."
        )

    code, status, msg = extract_error_details(error)
    err_lower = (msg or str(error)).lower()
    
    # A. Configuration Error
    if "api key is not configured" in err_lower or "api_key not found" in err_lower:
        return (
            "⚙️ **Configuration Error:** Gemini API configuration is missing. "
            "Please configure `GEMINI_API_KEY` in `.streamlit/secrets.toml`."
        )

    # B. Authentication / API key error (401, 403, UNAUTHENTICATED, PERMISSION_DENIED)
    if code in (401, 403) or status in ("UNAUTHENTICATED", "PERMISSION_DENIED") or "api_key_invalid" in err_lower or "invalid api key" in err_lower or "unauthenticated" in err_lower or "permission_denied" in err_lower:
        return (
            "🔑 **Authentication Error:** Gemini authentication failed. "
            "Please check that your API key in `.streamlit/secrets.toml` is active and correct."
        )

    # C. Invalid Request (400, INVALID_ARGUMENT)
    if code == 400 or status == "INVALID_ARGUMENT" or "invalid_argument" in err_lower or "bad request" in err_lower:
        return "📄 **Invalid Request:** The receipt analysis request could not be processed. Please try uploading a different photo."

    # D. Unsupported / Unavailable Model (404, NOT_FOUND)
    if code == 404 or status == "NOT_FOUND" or "not_found" in err_lower or ("model" in err_lower and "not found" in err_lower):
        current_model = get_configured_model()
        return f"🤖 **Unsupported Model:** The configured Gemini model (`{current_model}`) is unavailable or not found."

    # E. Rate limit (429, RESOURCE_EXHAUSTED)
    if code == 429 or status == "RESOURCE_EXHAUSTED" or "resource_exhausted" in err_lower or "quota" in err_lower or "rate limit" in err_lower:
        return "⏳ **Gemini Rate Limit Reached:** Gemini request limit reached. Please wait and try again."

    # F. Temporary Gemini service unavailable / 503 (503, UNAVAILABLE, 500, 502, 504, ServerError)
    if (
        code in (503, 500, 502, 504)
        or status == "UNAVAILABLE"
        or "temporarily unavailable" in err_lower
        or "high demand" in err_lower
        or "busy" in err_lower
        or "servererror" in err_lower
        or "server error" in err_lower
    ):
        return "⚠️ **Gemini Service Busy:** Gemini is temporarily unavailable. Please try again in a few seconds."

    # G. Image processing error
    if "image" in err_lower and ("cannot identify" in err_lower or "unsupported" in err_lower or "corrupt" in err_lower):
        return "🖼️ **Image Processing Error:** Unable to decode receipt image. Please upload a valid JPG, JPEG, or PNG."

    # H. Unexpected error
    clean_err = msg if len(msg) < 120 else msg[:117] + "..."
    return f"❌ **Receipt Analysis Error:** {clean_err}"


def prepare_receipt_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> tuple[bytes, str]:
    """
    Validate and normalize receipt image bytes.
    Ensures image is valid, handles EXIF orientation, and preserves high-clarity text.
    """
    if not image_bytes:
        raise ValueError("No image data provided.")
    
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # Correct phone photo orientation via EXIF transpose
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        # Normalize alpha channel if saving as JPEG
        is_png = "png" in mime_type.lower()
        if not is_png and img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                bg.paste(img, mask=img.split()[3])
            else:
                bg.paste(img.convert("RGB"))
            img = bg
        elif not is_png and img.mode != "RGB":
            img = img.convert("RGB")

        out_buf = io.BytesIO()
        if is_png:
            img.save(out_buf, format="PNG", optimize=True)
            normalized_mime = "image/png"
        else:
            img.save(out_buf, format="JPEG", quality=95, optimize=True)
            normalized_mime = "image/jpeg"

        return out_buf.getvalue(), normalized_mime
    except Exception:
        # Fallback to raw bytes if PIL fails, maintaining original mime
        norm_mime = "image/png" if "png" in mime_type.lower() else "image/jpeg"
        return image_bytes, norm_mime


def build_image_part(image_bytes: bytes, mime_type: str = "image/jpeg") -> types.Part:
    """Convert raw image bytes into a Gemini types.Part."""
    clean_bytes, clean_mime = prepare_receipt_image(image_bytes, mime_type)
    return types.Part.from_bytes(data=clean_bytes, mime_type=clean_mime)


def create_gemini_chat_session(
    client: Optional[genai.Client] = None,
    model_name: Optional[str] = None,
    system_prompt: str = SYSTEM_PROMPT
):
    """Create a new conversational chat session with BillWise system prompt."""
    if client is None:
        client = get_gemini_client()
    if model_name is None:
        model_name = get_configured_model()

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.3,
    )
    return client.chats.create(model=model_name, config=config)


def test_gemini_connectivity(
    model_name: Optional[str] = None,
    client: Optional[genai.Client] = None
) -> Dict[str, Any]:
    """
    Perform a minimal, isolated text-only connectivity test to diagnose Gemini API health.
    Does NOT trigger automatically on normal Streamlit reruns.
    """
    if model_name is None:
        model_name = get_configured_model()
    if client is None:
        try:
            client = get_gemini_client()
        except Exception as e:
            return {
                "success": False,
                "message": f"Client initialization failed: {str(e)}",
                "status_code": None,
                "status_name": None,
                "error_type": type(e).__name__
            }

    log_gemini_diagnostic(
        "connectivity_test_started",
        model=model_name,
        client_initialized=client is not None
    )

    try:
        config = types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            temperature=0.1
        )
        response = client.models.generate_content(
            model=model_name,
            contents="Respond with 'PONG' to test API connectivity.",
            config=config
        )
        resp_text = (response.text or "").strip()
        log_gemini_diagnostic(
            "connectivity_test_success",
            model=model_name,
            response_snippet=resp_text[:50]
        )
        return {
            "success": True,
            "message": f"Connected successfully to Gemini (`{model_name}`). Response: {resp_text}",
            "status_code": 200
        }
    except Exception as e:
        code, status_name, msg = extract_error_details(e)
        log_gemini_diagnostic(
            "connectivity_test_failed",
            model=model_name,
            error_type=type(e).__name__,
            status_code=code,
            status_name=status_name,
            error_message=str(msg)[:150]
        )
        return {
            "success": False,
            "message": f"Gemini connectivity failed ({type(e).__name__}): {msg}",
            "status_code": code,
            "status_name": status_name,
            "error_type": type(e).__name__
        }


# =====================================================================
# 4. RECEIPT PARSING & DETERMINISTIC PYTHON VALIDATION
# =====================================================================
def parse_receipt_json(raw_text: str) -> ReceiptData:
    """Safely parse raw text or JSON response from Gemini into a validated ReceiptData instance."""
    if not raw_text or not raw_text.strip():
        return ReceiptData(is_receipt=False, notes_or_uncertainties="Empty response received")

    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError as err:
                return ReceiptData(is_receipt=False, notes_or_uncertainties=f"JSON Parse Error: {str(err)}")
        else:
            return ReceiptData(is_receipt=False, notes_or_uncertainties="No valid JSON structure found in AI response")

    items_raw = data.get("items", [])
    parsed_items: List[ReceiptItem] = []
    
    for item in items_raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "Unknown Item")).strip()
        try:
            qty = float(item.get("quantity", 1.0) or 1.0)
        except (ValueError, TypeError):
            qty = 1.0
        
        unit_p = None
        if item.get("unit_price") is not None:
            try:
                unit_p = float(item["unit_price"])
            except (ValueError, TypeError):
                unit_p = None

        tot_p = 0.0
        if item.get("total_price") is not None:
            try:
                tot_p = float(item["total_price"])
            except (ValueError, TypeError):
                tot_p = 0.0
        elif unit_p is not None:
            tot_p = unit_p * qty

        parsed_items.append(ReceiptItem(
            name=name,
            quantity=qty,
            unit_price=unit_p,
            total_price=tot_p
        ))

    def safe_float(val: Any, default: Optional[float] = None) -> Optional[float]:
        if val is None or val == "" or str(val).lower() in ("null", "none", "unknown", "unclear"):
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    curr = data.get("currency", "₹")
    if curr in ["INR", "Rupees", "Rs", "Rs.", "₹"]:
        curr = "₹"
    elif curr in ["USD", "$"]:
        curr = "$"
    elif curr in ["EUR", "€"]:
        curr = "€"
    elif curr in ["GBP", "£"]:
        curr = "£"

    return ReceiptData(
        is_receipt=bool(data.get("is_receipt", True)),
        merchant=data.get("merchant"),
        receipt_number=data.get("receipt_number"),
        date=data.get("date"),
        time=data.get("time"),
        currency=curr,
        items=parsed_items,
        subtotal=safe_float(data.get("subtotal")),
        tax=safe_float(data.get("tax")),
        discount=safe_float(data.get("discount"), default=0.0) or 0.0,
        tip_or_service_charge=safe_float(data.get("tip_or_service_charge"), default=0.0) or 0.0,
        total=safe_float(data.get("total")),
        payment_method=data.get("payment_method"),
        notes_or_uncertainties=data.get("notes_or_uncertainties")
    )


def validate_receipt_arithmetic(receipt: ReceiptData, tolerance: float = 0.50) -> ReceiptValidationResult:
    """
    Perform deterministic arithmetic validation in Python on extracted receipt data.
    Rule: AI extracts. Python calculates.
    """
    if not receipt.is_receipt:
        return ReceiptValidationResult(
            status="NOT_A_RECEIPT",
            is_valid=False,
            items_sum=0.0,
            expected_subtotal=0.0,
            expected_total=0.0,
            detected_total=receipt.total,
            difference=0.0,
            message="The uploaded image does not appear to be a recognized receipt or bill.",
            details={"is_receipt": False}
        )

    items_sum = round(sum(item.total_price for item in receipt.items), 2)
    expected_subtotal = round(receipt.subtotal if receipt.subtotal is not None else items_sum, 2)
    tax = receipt.tax if receipt.tax is not None else 0.0
    discount = receipt.discount if receipt.discount is not None else 0.0
    tip = receipt.tip_or_service_charge if receipt.tip_or_service_charge is not None else 0.0
    calculated_total = round(expected_subtotal + tax + tip - discount, 2)

    if receipt.total is None:
        return ReceiptValidationResult(
            status="MISSING_TOTAL",
            is_valid=False,
            items_sum=items_sum,
            expected_subtotal=expected_subtotal,
            expected_total=calculated_total,
            detected_total=None,
            difference=0.0,
            message=f"Total payable amount was not clearly visible on receipt. Calculated sum of items is {receipt.currency}{calculated_total:.2f}.",
            details={
                "items_sum": items_sum,
                "subtotal": receipt.subtotal,
                "tax": receipt.tax,
                "discount": receipt.discount,
                "tip": receipt.tip_or_service_charge,
                "calculated_total": calculated_total
            }
        )

    detected_total = round(receipt.total, 2)
    difference = round(abs(detected_total - calculated_total), 2)
    subtotal_mismatch = (receipt.subtotal is not None and abs(round(receipt.subtotal, 2) - items_sum) > tolerance)

    if difference <= tolerance:
        status = "VERIFIED"
        is_valid = True
        msg = f"✅ Total verified ({receipt.currency}{detected_total:.2f} matches itemized sum + taxes/fees)."
    else:
        status = "MISMATCH"
        is_valid = False
        msg = (
            f"⚠️ Possible total mismatch: Extracted total is {receipt.currency}{detected_total:.2f}, "
            f"but calculated total is {receipt.currency}{calculated_total:.2f} (Difference: {receipt.currency}{difference:.2f})."
        )

    return ReceiptValidationResult(
        status=status,
        is_valid=is_valid,
        items_sum=items_sum,
        expected_subtotal=expected_subtotal,
        expected_total=calculated_total,
        detected_total=detected_total,
        difference=difference,
        message=msg,
        details={
            "items_sum": items_sum,
            "detected_subtotal": receipt.subtotal,
            "subtotal_mismatch": subtotal_mismatch,
            "tax": receipt.tax,
            "discount": receipt.discount,
            "tip_or_service_charge": receipt.tip_or_service_charge,
            "detected_total": detected_total,
            "calculated_total": calculated_total,
            "difference": difference
        }
    )


def get_demo_receipt() -> ReceiptData:
    """
    Return a pre-validated sample receipt for demo/offline testing without calling Gemini.
    Uses Pydantic ReceiptData.model_validate to ensure strict schema adherence.
    """
    demo_dict = {
        "is_receipt": True,
        "merchant": "FreshMart Supermarket",
        "receipt_number": "FM-2026-1042",
        "date": "2026-09-30",
        "time": "14:30",
        "currency": "₹",
        "items": [
            {
                "name": "Milk",
                "quantity": 2,
                "unit_price": 30,
                "total_price": 60
            },
            {
                "name": "Bread",
                "quantity": 1,
                "unit_price": 45,
                "total_price": 45
            },
            {
                "name": "Eggs",
                "quantity": 1,
                "unit_price": 72,
                "total_price": 72
            },
            {
                "name": "Apples",
                "quantity": 1,
                "unit_price": 120,
                "total_price": 120
            }
        ],
        "subtotal": 297,
        "tax": 15,
        "discount": 12,
        "tip_or_service_charge": 0,
        "total": 300,
        "payment_method": "UPI",
        "notes_or_uncertainties": None
    }
    return ReceiptData.model_validate(demo_dict)


def analyze_receipt_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    model_name: Optional[str] = None,
    client: Optional[genai.Client] = None,
    max_retries: int = 4,
    status_callback: Optional[Any] = None,
    request_id: Optional[str] = None
) -> ReceiptData:
    """
    Send receipt image to Gemini Vision with structured JSON schema output,
    automatic function calling disabled, and transient error exponential backoff.
    """
    if model_name is None:
        model_name = get_configured_model()

    if client is None:
        client = get_gemini_client()

    image_part = build_image_part(image_bytes, mime_type)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=ReceiptData,
        temperature=0.1,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    base_delays = [0, 2.0, 4.0, 8.0]
    last_exception = None

    log_gemini_diagnostic(
        "receipt_analysis_started",
        request_id=request_id,
        model=model_name,
        mime_type=mime_type,
        byte_size=len(image_bytes)
    )

    log_gemini_diagnostic(
        "receipt_analysis_request_payload",
        request_id=request_id,
        model=model_name,
        mime_type=mime_type,
        byte_size=len(image_bytes),
        client_initialized=client is not None,
        has_response_schema=bool(config.response_schema),
        response_mime_type=config.response_mime_type,
        afc_disabled=bool(config.automatic_function_calling and config.automatic_function_calling.disable)
    )

    for attempt in range(max_retries):
        attempt_num = attempt + 1
        if attempt > 0:
            base_d = base_delays[attempt] if attempt < len(base_delays) else 8.0
            jitter = random.uniform(0.1, 0.5)
            delay = round(base_d + jitter, 2)
            if status_callback:
                try:
                    status_callback(f"Gemini is temporarily busy. Retrying ({attempt_num}/{max_retries}) in {delay:.1f}s...")
                except Exception:
                    pass
            time.sleep(delay)
        else:
            delay = 0.0

        try:
            log_gemini_diagnostic(
                "receipt_analysis_attempt",
                request_id=request_id,
                model=model_name,
                attempt=attempt_num,
                max_retries=max_retries,
                delay=delay
            )
            response = client.models.generate_content(
                model=model_name,
                contents=[image_part, RECEIPT_EXTRACTION_PROMPT],
                config=config,
            )
            parsed = parse_receipt_json(response.text or "")
            log_gemini_diagnostic(
                "receipt_analysis_success",
                request_id=request_id,
                model=model_name,
                attempt=attempt_num,
                is_receipt=parsed.is_receipt,
                merchant=parsed.merchant,
                items_count=len(parsed.items),
                total=parsed.total
            )
            return parsed
        except Exception as e:
            last_exception = e
            code, status, _ = extract_error_details(e)
            transient = is_transient_error(e)
            log_gemini_diagnostic(
                "receipt_analysis_error",
                request_id=request_id,
                model=model_name,
                attempt=attempt_num,
                error_type=type(e).__name__,
                status_code=code,
                status_name=status,
                is_transient=transient,
                delay_before_retry=delay
            )
            
            # Permanent errors (auth, invalid request, unsupported model) must NOT be retried
            if not transient:
                raise e

            if attempt == max_retries - 1:
                log_gemini_diagnostic(
                    "receipt_analysis_exhausted",
                    request_id=request_id,
                    model=model_name,
                    total_attempts=max_retries,
                    final_http_status=code,
                    final_status_name=status,
                    final_exception_type=type(e).__name__,
                    final_exception_message=str(last_exception)[:150]
                )
                break

    if last_exception is not None:
        code, status, _ = extract_error_details(last_exception)
        log_gemini_diagnostic(
            "receipt_analysis_final_failure",
            request_id=request_id,
            model=model_name,
            total_attempts=max_retries,
            final_http_status=code,
            final_status_name=status,
            final_exception_type=type(last_exception).__name__,
            final_exception_message=str(last_exception)[:150]
        )
        raise last_exception
    raise RuntimeError("Gemini is temporarily unavailable. Please try again in a few seconds.")


# =====================================================================
# 5. DETERMINISTIC BILL SPLITTING ENGINE
# =====================================================================
def calculate_equal_split(
    total_amount: float,
    num_people: int = 1,
    names: Optional[List[str]] = None,
    currency: str = "₹"
) -> BillSplitResult:
    """Split the bill equally among N people with exact rounding reconciliation."""
    if num_people < 1:
        raise ValueError("Number of people must be at least 1.")
    if total_amount < 0:
        raise ValueError("Total amount cannot be negative.")

    total_amount = round(total_amount, 2)
    if not names or len(names) != num_people:
        names = [f"Person {i+1}" for i in range(num_people)]

    base_share_cents = int((total_amount * 100) // num_people)
    remainder_cents = int(round(total_amount * 100)) - (base_share_cents * num_people)

    shares: List[PersonShare] = []
    for i, name in enumerate(names):
        cents = base_share_cents + (1 if i < remainder_cents else 0)
        share_val = round(cents / 100.0, 2)
        shares.append(PersonShare(
            name=name.strip() or f"Person {i+1}",
            items_subtotal=share_val,
            total_share=share_val
        ))

    reconciled_sum = round(sum(s.total_share for s in shares), 2)
    reconciled = (reconciled_sum == total_amount)

    return BillSplitResult(
        mode="equal",
        total_bill=total_amount,
        currency=currency,
        num_people=num_people,
        allocation_rule=f"Total {currency}{total_amount:.2f} divided equally among {num_people} people.",
        shares=shares,
        reconciled=reconciled,
        reconciled_sum=reconciled_sum
    )


def calculate_item_split(
    receipt: ReceiptData,
    names: List[str],
    item_assignments: Dict[int, List[str]],
    tax_allocation: str = "proportional"
) -> BillSplitResult:
    """Split the bill based on individual item assignments with proportional or equal tax/fee allocation."""
    if not names:
        raise ValueError("At least one person name must be provided.")

    clean_names = [n.strip() for n in names if n.strip()]
    if not clean_names:
        clean_names = ["Person 1"]
    num_people = len(clean_names)

    person_data: Dict[str, PersonShare] = {
        name: PersonShare(name=name) for name in clean_names
    }

    unassigned_items: List[str] = []

    for idx, item in enumerate(receipt.items):
        assigned_to = item_assignments.get(idx, [])
        valid_assigned = [p for p in assigned_to if p in person_data]
        
        if not valid_assigned:
            unassigned_items.append(item.name)
            valid_assigned = clean_names

        split_count = len(valid_assigned)
        item_cost_per_person = round(item.total_price / split_count, 2)
        
        for p_name in valid_assigned:
            person_data[p_name].items_subtotal = round(
                person_data[p_name].items_subtotal + item_cost_per_person, 2
            )
            person_data[p_name].assigned_items.append({
                "item_name": item.name,
                "full_price": item.total_price,
                "shared_among": split_count,
                "cost": item_cost_per_person
            })

    total_items_subtotal = round(sum(p.items_subtotal for p in person_data.values()), 2)
    total_tax = receipt.tax if receipt.tax is not None else 0.0
    total_discount = receipt.discount if receipt.discount is not None else 0.0
    total_tip = receipt.tip_or_service_charge if receipt.tip_or_service_charge is not None else 0.0
    
    if receipt.total is not None and receipt.total > 0:
        target_grand_total = round(receipt.total, 2)
    else:
        target_grand_total = round(total_items_subtotal + total_tax + total_tip - total_discount, 2)

    for p_name, p_share in person_data.items():
        if total_items_subtotal > 0 and tax_allocation == "proportional":
            proportion = p_share.items_subtotal / total_items_subtotal
        else:
            proportion = 1.0 / num_people

        p_share.tax_share = round(total_tax * proportion, 2)
        p_share.discount_share = round(total_discount * proportion, 2)
        p_share.tip_or_service_share = round(total_tip * proportion, 2)
        p_share.total_share = round(
            p_share.items_subtotal + p_share.tax_share + p_share.tip_or_service_share - p_share.discount_share, 2
        )

    shares_list = list(person_data.values())
    current_sum = round(sum(s.total_share for s in shares_list), 2)
    diff_cents = int(round((target_grand_total - current_sum) * 100))

    if diff_cents != 0 and shares_list:
        sorted_indices = sorted(range(len(shares_list)), key=lambda i: shares_list[i].total_share, reverse=True)
        step = 1 if diff_cents > 0 else -1
        for i in range(abs(diff_cents)):
            target_idx = sorted_indices[i % len(sorted_indices)]
            shares_list[target_idx].total_share = round(shares_list[target_idx].total_share + (0.01 * step), 2)

    final_sum = round(sum(s.total_share for s in shares_list), 2)
    reconciled = (final_sum == target_grand_total)

    rule_desc = (
        f"Item costs assigned individually. Shared items split equally. "
        f"Taxes ({receipt.currency}{total_tax:.2f}), fees ({receipt.currency}{total_tip:.2f}), "
        f"and discounts ({receipt.currency}{total_discount:.2f}) allocated {tax_allocation}ly based on item subtotals."
    )
    
    notes = None
    if unassigned_items:
        notes = f"Unassigned items ({', '.join(unassigned_items[:3])}{'...' if len(unassigned_items) > 3 else ''}) were shared equally among all participants."

    return BillSplitResult(
        mode="item_based",
        total_bill=target_grand_total,
        currency=receipt.currency,
        num_people=num_people,
        allocation_rule=rule_desc,
        shares=shares_list,
        reconciled=reconciled,
        reconciled_sum=final_sum,
        notes=notes
    )


# =====================================================================
# 6. DETERMINISTIC CHAT ANSWERS & GEMINI CHAT ASSISTANT
# =====================================================================
def try_answer_receipt_with_python(
    user_prompt: str,
    receipt: Optional[ReceiptData],
    split_result: Optional[BillSplitResult] = None
) -> Optional[str]:
    """
    Attempt to answer factual receipt questions deterministically in pure Python.
    Returns markdown response string if answered, or None if Gemini should handle it.
    """
    if not receipt or not receipt.is_receipt:
        return None

    p_clean = user_prompt.strip().lower()
    p_clean = re.sub(r"[?!.,]+$", "", p_clean).strip()
    curr = receipt.currency

    # 1. Most expensive item
    if any(k in p_clean for k in ["most expensive", "highest price", "highest cost", "costliest", "max price", "maximum price", "most costly"]):
        if not receipt.items:
            return "No items were found on this receipt."
        max_item = max(receipt.items, key=lambda x: x.total_price)
        unit_str = f" @ {curr}{max_item.unit_price:.2f}/ea" if max_item.unit_price else ""
        return (
            f"💰 **Most Expensive Item:**\n\n"
            f"• **{max_item.name}** — **{curr}{max_item.total_price:.2f}** "
            f"(Qty: {max_item.quantity:g}{unit_str})"
        )

    # 2. Cheapest / Least expensive item
    if any(k in p_clean for k in ["cheapest", "least expensive", "lowest price", "lowest cost", "min price", "minimum price", "least costly"]):
        if not receipt.items:
            return "No items were found on this receipt."
        min_item = min(receipt.items, key=lambda x: x.total_price)
        unit_str = f" @ {curr}{min_item.unit_price:.2f}/ea" if min_item.unit_price else ""
        return (
            f"🏷️ **Cheapest Item:**\n\n"
            f"• **{min_item.name}** — **{curr}{min_item.total_price:.2f}** "
            f"(Qty: {min_item.quantity:g}{unit_str})"
        )

    # 3. Total bill amount
    if any(k in p_clean for k in ["total bill", "total amount", "grand total", "what is the total", "what's the total", "how much is the total", "how much is the bill", "what is my total", "total cost", "total spent"]):
        tot_str = f"{curr}{receipt.total:.2f}" if receipt.total is not None else "Not explicitly printed"
        lines = [f"🧾 **Grand Total:** **{tot_str}**\n"]
        if receipt.subtotal is not None:
            lines.append(f"• **Subtotal:** {curr}{receipt.subtotal:.2f}")
        if receipt.tax is not None:
            lines.append(f"• **Tax:** {curr}{receipt.tax:.2f}")
        if receipt.discount and receipt.discount > 0:
            lines.append(f"• **Discount:** -{curr}{receipt.discount:.2f}")
        if receipt.tip_or_service_charge and receipt.tip_or_service_charge > 0:
            lines.append(f"• **Service Charge / Tip:** +{curr}{receipt.tip_or_service_charge:.2f}")
        return "\n".join(lines)

    # 4. Tax amount
    if any(k in p_clean for k in ["how much tax", "what is the tax", "tax amount", "taxes did i pay", "tax did we pay", "total tax", "how much taxes"]):
        if receipt.tax is not None:
            pct_str = ""
            if receipt.subtotal and receipt.subtotal > 0:
                pct = (receipt.tax / receipt.subtotal) * 100
                pct_str = f" (~{pct:.1f}% of subtotal)"
            return f"🏛️ **Tax Amount:** **{curr}{receipt.tax:.2f}**{pct_str}"
        return "ℹ️ No separate tax amount was detected on this receipt."

    # 5. Subtotal
    if any(k in p_clean for k in ["subtotal", "sub-total", "pre-tax", "pre tax", "amount before tax"]):
        items_sum = sum(it.total_price for it in receipt.items)
        sub = receipt.subtotal if receipt.subtotal is not None else items_sum
        return f"📋 **Subtotal:** **{curr}{sub:.2f}**"

    # 6. Discount
    if any(k in p_clean for k in ["discount", "savings", "saved", "how much discount"]):
        if receipt.discount and receipt.discount > 0:
            return f"🎉 **Discount Applied:** **-{curr}{receipt.discount:.2f}**"
        return "ℹ️ No discount was applied on this receipt."

    # 7. Service charge / Tip
    if any(k in p_clean for k in ["service charge", "tip", "gratuity", "service fee"]):
        if receipt.tip_or_service_charge and receipt.tip_or_service_charge > 0:
            return f"🍽️ **Service Charge / Tip:** **+{curr}{receipt.tip_or_service_charge:.2f}**"
        return "ℹ️ No separate service charge or tip was detected on this receipt."

    # 8. How many items / List items
    if any(k in p_clean for k in ["how many items", "how many item", "number of items", "item count", "total items", "count of items", "what did i buy", "what did we buy", "list all items", "list items"]):
        lines = [f"🛒 **Receipt Items ({len(receipt.items)} total):**\n"]
        for idx, item in enumerate(receipt.items, 1):
            lines.append(f"{idx}. **{item.name}** (Qty: {item.quantity:g}) — {curr}{item.total_price:.2f}")
        return "\n".join(lines)

    # 9. Split bill between N people (e.g. "Split this bill between 4 people")
    split_match = re.search(r"split.*?(?:between|among|for|into)\s+(\d+)\s*(?:people|persons|friends|ways)?", p_clean)
    if not split_match:
        split_match = re.search(r"divide.*?(?:between|among|by|for)\s+(\d+)", p_clean)
    
    if split_match:
        n_people = int(split_match.group(1))
        if n_people >= 1:
            eff_total = receipt.total if receipt.total is not None else sum(it.total_price for it in receipt.items)
            split_res = calculate_equal_split(eff_total, n_people, currency=curr)
            lines = [f"🧮 **Equal Split for {n_people} People (Total: {curr}{eff_total:.2f}):**\n"]
            for s in split_res.shares:
                lines.append(f"• **{s.name}:** {curr}{s.total_share:.2f}")
            lines.append(f"\n*Each person pays {curr}{split_res.shares[0].total_share:.2f}* (Reconciled: {curr}{split_res.reconciled_sum:.2f})")
            return "\n".join(lines)

    # 10. Items costing more/less than X (e.g. "items over 100", "cost more than 200")
    more_match = re.search(r"(?:cost|price|items?).*?(?:more|greater|higher|over|above)\s*(?:than)?\s*[₹$€£]?\s*(\d+(?:\.\d+)?)", p_clean)
    if more_match:
        threshold = float(more_match.group(1))
        matches = [it for it in receipt.items if it.total_price >= threshold]
        if matches:
            lines = [f"🔍 **Items costing {curr}{threshold:.2f} or more:**\n"]
            for it in matches:
                lines.append(f"• **{it.name}** — {curr}{it.total_price:.2f}")
            return "\n".join(lines)
        return f"ℹ️ No items cost more than {curr}{threshold:.2f}."

    return None


def build_receipt_context_string(
    receipt: Optional[ReceiptData] = None,
    split_result: Optional[BillSplitResult] = None
) -> str:
    """Build a deterministic text summary of receipt context to ground Gemini responses."""
    if not receipt:
        return "No receipt has been uploaded yet."

    lines = [
        "--- CURRENT ACTIVE RECEIPT CONTEXT ---",
        f"Merchant: {receipt.merchant or 'Unknown'}",
        f"Date: {receipt.date or 'Unknown'}",
        f"Currency: {receipt.currency}",
        f"Items Count: {len(receipt.items)}",
        "Itemized Purchases:"
    ]
    for idx, item in enumerate(receipt.items, 1):
        unit_str = f" @ {receipt.currency}{item.unit_price:.2f}/ea" if item.unit_price else ""
        lines.append(f"  {idx}. {item.name} (Qty: {item.quantity}{unit_str}) -> {receipt.currency}{item.total_price:.2f}")

    if receipt.subtotal is not None:
        lines.append(f"Subtotal: {receipt.currency}{receipt.subtotal:.2f}")
    if receipt.tax is not None:
        lines.append(f"Tax: {receipt.currency}{receipt.tax:.2f}")
    if receipt.discount and receipt.discount > 0:
        lines.append(f"Discount: -{receipt.currency}{receipt.discount:.2f}")
    if receipt.tip_or_service_charge and receipt.tip_or_service_charge > 0:
        lines.append(f"Service Charge / Tip: +{receipt.currency}{receipt.tip_or_service_charge:.2f}")
    if receipt.total is not None:
        lines.append(f"Grand Total: {receipt.currency}{receipt.total:.2f}")
    if receipt.notes_or_uncertainties:
        lines.append(f"OCR Notes/Uncertainties: {receipt.notes_or_uncertainties}")

    if split_result:
        lines.append("\n--- ACTIVE BILL SPLIT BREAKDOWN ---")
        lines.append(f"Split Mode: {split_result.mode}")
        lines.append(f"People Count: {split_result.num_people}")
        lines.append(f"Allocation Rule: {split_result.allocation_rule}")
        lines.append("Individual Shares:")
        for share in split_result.shares:
            lines.append(f"  - {share.name}: {receipt.currency}{share.total_share:.2f}")

    lines.append("--------------------------------------")
    return "\n".join(lines)


def ask_receipt_assistant(
    chat_session,
    user_prompt: str,
    receipt: Optional[ReceiptData] = None,
    split_result: Optional[BillSplitResult] = None,
    max_retries: int = 4,
    status_callback: Optional[Any] = None
) -> str:
    """Send user question to Gemini chat with exponential backoff for transient errors."""
    context_str = build_receipt_context_string(receipt, split_result)
    full_message = f"{context_str}\n\nUser Question: {user_prompt}"

    base_delays = [0, 2.0, 4.0, 8.0]
    last_exception = None
    model_name = get_configured_model()

    for attempt in range(max_retries):
        attempt_num = attempt + 1
        if attempt > 0:
            base_d = base_delays[attempt] if attempt < len(base_delays) else 8.0
            jitter = random.uniform(0.1, 0.5)
            delay = round(base_d + jitter, 2)
            if status_callback:
                status_callback(f"Gemini is temporarily busy. Retrying chat ({attempt_num}/{max_retries})...")
            time.sleep(delay)
        else:
            delay = 0.0

        try:
            log_gemini_diagnostic(
                "chat_send_message_attempt",
                model=model_name,
                attempt=attempt_num,
                max_retries=max_retries
            )
            response = chat_session.send_message(full_message)
            return response.text or "I reviewed the receipt, but couldn't generate a text response."
        except Exception as e:
            last_exception = e
            code, status, _ = extract_error_details(e)
            transient = is_transient_error(e)
            log_gemini_diagnostic(
                "chat_send_message_error",
                model=model_name,
                attempt=attempt_num,
                error_type=type(e).__name__,
                status_code=code,
                status_name=status,
                is_transient=transient,
                delay_before_retry=delay
            )
            if not transient:
                raise e
            if attempt == max_retries - 1:
                break

    if last_exception is not None:
        raise last_exception
    raise RuntimeError("Gemini is temporarily unavailable. Please try again in a few seconds.")


# =====================================================================
# 7. EXPENSE SUMMARY GENERATION
# =====================================================================
def generate_expense_summary(
    receipt: ReceiptData,
    split_result: Optional[BillSplitResult] = None,
    client: Optional[genai.Client] = None,
    model_name: Optional[str] = None
) -> str:
    """Generate final concise expense summary using Gemini with deterministic fallback."""
    if model_name is None:
        model_name = get_configured_model()

    curr = receipt.currency
    subtotal_line = f"• Subtotal: {curr}{receipt.subtotal:.2f}\n" if receipt.subtotal is not None else ""
    tax_line = f"• Tax: {curr}{receipt.tax:.2f}\n" if receipt.tax is not None else ""
    disc_line = f"• Discount: -{curr}{receipt.discount:.2f}\n" if receipt.discount and receipt.discount > 0 else ""
    tip_line = f"• Service/Tip: +{curr}{receipt.tip_or_service_charge:.2f}\n" if receipt.tip_or_service_charge and receipt.tip_or_service_charge > 0 else ""
    tot_val = f"{curr}{receipt.total:.2f}" if receipt.total is not None else "Not detected"

    split_block = "Split: Not configured yet"
    if split_result:
        shares_lines = "\n".join([f"  • {s.name}: {curr}{s.total_share:.2f}" for s in split_result.shares])
        split_block = f"Split ({split_result.mode.replace('_', ' ').title()} - {split_result.num_people} people):\n{shares_lines}"

    fallback_summary = (
        f"🧾 *BILLWISE AI EXPENSE SUMMARY*\n\n"
        f"🏪 *Merchant:* {receipt.merchant or 'Unknown'}\n"
        f"📅 *Date:* {receipt.date or 'Not specified'}\n"
        f"💰 *Total:* {tot_val}\n\n"
        f"{subtotal_line}{tax_line}{disc_line}{tip_line}\n"
        f"{split_block}\n\n"
        f"🔍 *Verification:* {'Passed ✅' if receipt.total is not None else 'Unverified ⚠️'}\n"
        f"Generated by BillWise AI"
    )

    try:
        if client is None:
            client = get_gemini_client()

        context_str = build_receipt_context_string(receipt, split_result)
        prompt = f"{SUMMARY_REQUEST_PROMPT}\n\nReceipt Data:\n{context_str}"

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt],
            config=config
        )
        if response.text and len(response.text.strip()) > 20:
            return response.text.strip()
        return fallback_summary
    except Exception:
        return fallback_summary


# =====================================================================
# 8. ACTION & SHARING DISPATCH LAYER
# =====================================================================
def send_whatsapp_twilio(destination: str, summary_text: str) -> ActionResult:
    """Send WhatsApp message through Twilio WhatsApp Trial template."""

    account_sid = get_secret("TWILIO_ACCOUNT_SID")
    auth_token = get_secret("TWILIO_AUTH_TOKEN")
    from_number = get_secret("TWILIO_WHATSAPP_FROM")
    content_sid = get_secret("TWILIO_CONTENT_SID")

    clean_dest = destination.strip()

    if not clean_dest.startswith("whatsapp:"):
        clean_num = clean_dest.replace(" ", "").replace("-", "")

        if not clean_num.startswith("+"):
            clean_num = "+" + clean_num

        dest_formatted = f"whatsapp:{clean_num}"
    else:
        dest_formatted = clean_dest

    if not account_sid or not auth_token:
        return ActionResult(
            success=False,
            provider="whatsapp",
            message="Twilio credentials are not configured."
        )

    if not from_number or not content_sid:
        return ActionResult(
            success=False,
            provider="whatsapp",
            message="Twilio WhatsApp template settings are not configured."
        )

    try:
        client = Client(account_sid, auth_token)

        message = client.messages.create(
            from_=from_number,
            to=dest_formatted,
            content_sid=content_sid,
        )

        return ActionResult(
            success=True,
            provider="whatsapp",
            
            message=(
            f"📨 Twilio accepted the message.\n\n"
            f"Status: {message.status}\n"
            f"Message SID: {message.sid}"
            ),
            details={
                "message_sid": message.sid,
                "status": message.status,
                "mode": "twilio_trial_template"
            }
        )

    except Exception as error:
        return ActionResult(
            success=False,
            provider="whatsapp",
            message=f"Twilio WhatsApp failed: {error}"
        )


def send_twilio_test_message(destination: Optional[str] = None):
    """Send the configured Twilio trial template to the current destination for testing."""
    try:
        account_sid = get_secret("TWILIO_ACCOUNT_SID")
        auth_token = get_secret("TWILIO_AUTH_TOKEN")
        from_number = get_secret("TWILIO_WHATSAPP_FROM")
        content_sid = get_secret("TWILIO_CONTENT_SID")

        if not account_sid or not auth_token:
            return False, "Twilio credentials are not configured."
        if not from_number or not content_sid:
            return False, "Twilio WhatsApp template settings are not configured."

        clean_dest = (destination or "").strip()
        clean_dest = clean_dest.replace("whatsapp:", "").replace(" ", "").replace("-", "")
        if not clean_dest:
            return False, "No WhatsApp destination is configured."
        if not clean_dest.startswith("+"):
            clean_dest = "+" + clean_dest

        client = Client(account_sid, auth_token)
        message = client.messages.create(
            from_=from_number,
            to=f"whatsapp:{clean_dest}",
            content_sid=content_sid,
        )
        return True, message.sid

    except Exception as e:
        return False, str(e)


def send_email_smtp(
    destination: str,
    summary_text: str,
    subject: str = "BillWise AI Expense Summary"
) -> ActionResult:
    """Send the actual BillWise summary through Gmail SMTP."""

    smtp_user = get_secret("GMAIL_SENDER_EMAIL")
    smtp_pass = get_secret("GMAIL_APP_PASSWORD")
    smtp_host = get_secret("SMTP_HOST", "smtp.gmail.com")
    smtp_port_raw = get_secret("SMTP_PORT", "587")

    try:
        smtp_port = int(smtp_port_raw)
    except (ValueError, TypeError):
        smtp_port = 587

    # Direct email-app fallback link
    encoded_subj = urllib.parse.quote(subject)
    encoded_body = urllib.parse.quote(summary_text)
    mailto_link = (
        f"mailto:{destination}"
        f"?subject={encoded_subj}"
        f"&body={encoded_body}"
    )

    if not smtp_user or not smtp_pass:
        return ActionResult(
            success=False,
            provider="email",
            message="Gmail credentials are not configured.",
            action_url=mailto_link,
            details={"configured": False}
        )

    try:
        msg = EmailMessage()

        msg["From"] = smtp_user
        msg["To"] = destination
        msg["Subject"] = subject

        # This is the ACTUAL BillWise summary
        msg.set_content(summary_text)

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        return ActionResult(
            success=True,
            provider="email",
            message=f"✅ BillWise summary sent successfully to {destination}!",
            action_url=None,
            details={
                "recipient": destination,
                "method": "gmail_smtp"
            }
        )

    except Exception as e:
        return ActionResult(
            success=False,
            provider="email",
            message=f"❌ Gmail SMTP Error: {str(e)}",
            action_url=mailto_link,
            details={
                "error": str(e),
                "method": "gmail_smtp"
            }
        )

def send_telegram_message(destination: str, summary_text: str) -> ActionResult:
    """Send Telegram message via Bot API with direct t.me link fallback."""
    bot_token = get_secret("TELEGRAM_BOT_TOKEN")
    encoded_text = urllib.parse.quote(summary_text)
    telegram_share_url = f"https://t.me/share/url?url=&text={encoded_text}"

    if not bot_token:
        return ActionResult(
            success=False,
            provider="telegram",
            message="Telegram Bot Token not configured. Use the direct Telegram share link below!",
            action_url=telegram_share_url,
            details={"configured": False}
        )

    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": destination,
        "text": summary_text,
        "parse_mode": "Markdown"
    }

    try:
        resp = requests.post(api_url, json=payload, timeout=10)
        if resp.status_code == 200:
            return ActionResult(
                success=True,
                provider="telegram",
                message=f"✅ Summary sent to Telegram chat {destination}!",
                action_url=telegram_share_url,
                details=resp.json()
            )
        else:
            err_msg = resp.json().get("description", resp.text)
            return ActionResult(
                success=False,
                provider="telegram",
                message=f"Telegram API Error: {err_msg}. You can share using the link below.",
                action_url=telegram_share_url,
                details={"error": err_msg}
            )
    except Exception as e:
        return ActionResult(
            success=False,
            provider="telegram",
            message=f"Telegram connection failed: {str(e)}",
            action_url=telegram_share_url,
            details={"error": str(e)}
        )

def format_whatsapp_summary(text: str) -> str:
    """Convert BillWise summary into a clean WhatsApp-friendly format."""

    if not text:
        return "No expense summary available."

    # Remove Markdown bold markers
    text = text.replace("**", "")

    # Replace Markdown separators
    text = text.replace("***", "━━━━━━━━━━━━━━━━━━━━")

    # Clean up common headings
    text = text.replace("🧾 BILLWISE AI EXPENSE SUMMARY", "🧾 BILLWISE AI")

    # Improve section names
    text = text.replace("📊 Financial Breakdown:", "📊 BILL BREAKDOWN")
    text = text.replace("👥 Split Details:", "👥 BILL SPLIT")
    text = text.replace("✅ Verification Status:", "✅ PAYMENT CHECK")

    # Remove unnecessary sentence
    text = text.replace(
        "Generated by BillWise AI. Hope you had a great meal! Please settle your shares at your earliest convenience.",
        "🤖 Generated by BillWise AI"
    )

    # Clean extra blank lines
    lines = [line.rstrip() for line in text.splitlines()]

    cleaned = []
    previous_blank = False

    for line in lines:
        if not line.strip():
            if not previous_blank:
                cleaned.append("")
            previous_blank = True
        else:
            cleaned.append(line)
            previous_blank = False

    return "\n".join(cleaned).strip()


def send_summary(provider: str, destination: str, summary_text: str) -> ActionResult:
    """Universal dispatch function for the action layer."""

    if not summary_text or not summary_text.strip():
        return ActionResult(
            success=False,
            provider=provider,
            message="Cannot send an empty summary."
        )

    provider_clean = (provider or "whatsapp").lower().strip()

    if provider_clean == "whatsapp":

        return send_whatsapp_twilio(
            destination=destination,
            summary_text=summary_text
        )
    elif provider_clean == "email":
        return send_email_smtp(destination, summary_text)

    elif provider_clean == "telegram":
        return send_telegram_message(destination, summary_text)

    else:
        return ActionResult(
            success=False,
            provider=provider_clean,
            message=f"Unknown action provider: {provider}"
        )
# =====================================================================
# 9. SESSION STATE & HELPER FUNCTIONS
# =====================================================================
def init_session_state():
    """Ensure all required session state variables exist."""
    if "onboarded" not in st.session_state:
        st.session_state.onboarded = False
    if "name" not in st.session_state:
        st.session_state.name = ""
    if "action_provider" not in st.session_state:
        st.session_state.action_provider = "WhatsApp"
    if "action_destination" not in st.session_state:
        st.session_state.action_destination = ""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "receipt_data" not in st.session_state:
        st.session_state.receipt_data = None
    if "validation_result" not in st.session_state:
        st.session_state.validation_result = None
    if "split_result" not in st.session_state:
        st.session_state.split_result = None
    if "generated_summary" not in st.session_state:
        st.session_state.generated_summary = ""
    if "chat_session" not in st.session_state:
        st.session_state.chat_session = None
    if "image_bytes" not in st.session_state:
        st.session_state.image_bytes = None
    if "image_mime" not in st.session_state:
        st.session_state.image_mime = "image/jpeg"
    if "image_fingerprint" not in st.session_state:
        st.session_state.image_fingerprint = None
    if "analysis_in_progress" not in st.session_state:
        st.session_state.analysis_in_progress = False
    if "analysis_request_id" not in st.session_state:
        st.session_state.analysis_request_id = None
    if "demo_mode" not in st.session_state:
        st.session_state.demo_mode = False
    if "participant_details" not in st.session_state:
        st.session_state.participant_details = []


init_session_state()

def test_twilio_connection():
    try:
        account_sid = st.secrets["TWILIO_ACCOUNT_SID"]
        auth_token = st.secrets["TWILIO_AUTH_TOKEN"]

        client = Client(account_sid, auth_token)

        account = client.api.accounts(account_sid).fetch()

        return True, f"Twilio connected successfully! Status: {account.status}"

    except Exception as e:
        return False, str(e)

def add_message(role: str, kind: str, content: Any):
    """Add a structured message to session history."""
    st.session_state.messages.append({
        "role": role,
        "kind": kind,
        "content": content
    })


def reset_app_session():
    """Reset session for a new receipt analysis while preserving onboarding info."""
    st.session_state.receipt_data = None
    st.session_state.validation_result = None
    st.session_state.split_result = None
    st.session_state.generated_summary = ""
    st.session_state.participant_details = []
    st.session_state.chat_session = None
    st.session_state.image_bytes = None
    st.session_state.image_mime = "image/jpeg"
    st.session_state.image_fingerprint = None
    st.session_state.analysis_in_progress = False
    st.session_state.analysis_request_id = None
    st.session_state.messages = [{
        "role": "assistant",
        "kind": "text",
        "content": WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name or "Friend")
    }]
    st.rerun()

def test_gmail_connection():
    try:
        sender_email = st.secrets["GMAIL_SENDER_EMAIL"]
        app_password = st.secrets["GMAIL_APP_PASSWORD"]

        message = EmailMessage()
        message["Subject"] = "BillWise AI - Gmail Test"
        message["From"] = sender_email
        message["To"] = sender_email
        message.set_content(
            "Hello!\n\n"
            "This is a test email from BillWise AI.\n\n"
            "Gmail SMTP connection is working successfully."
        )

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(message)

        return True, "Test email sent successfully!"

    except Exception as e:
        return False, str(e)
# =====================================================================
# 10. ONBOARDING SCREEN
# =====================================================================
def render_onboarding():
    """Render the clean, centered BillWise AI onboarding experience."""

    st.markdown(
        """
        <div class="bw-onboarding">
            <div class="bw-onboarding-hero">
                <div class="bw-logo">🧾</div>
                <div class="bw-onboarding-title">BillWise AI</div>
                <div class="bw-onboarding-subtitle">
                    Snap it. Understand it. Split it. Share it.
                </div>
                <div class="bw-feature-row">
                    <span class="bw-feature-pill">✨ AI Receipt Analysis</span>
                    <span class="bw-feature-pill">🧮 Smart Splitting</span>
                    <span class="bw-feature-pill">📤 Easy Sharing</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    api_key = get_api_key()
    if not api_key:
        st.warning(
            "⚠️ **Gemini API Key Required:** Configure `GEMINI_API_KEY` in "
            "`.streamlit/secrets.toml` or enter it for this session."
        )
        custom_key = st.text_input(
            "Gemini API Key (Session only)",
            type="password",
            placeholder="Paste your Gemini API key"
        )
        if custom_key:
            st.session_state["GEMINI_API_KEY"] = custom_key.strip()
            st.success("Gemini API key stored for this session.")

    with st.form("onboarding_form", clear_on_submit=False):
        st.markdown(
            """
            <div class="bw-form-title">👤 Set Up Your Profile</div>
            <div class="bw-form-subtitle">
                Add your details once and BillWise will use them for sharing.
            </div>
            """,
            unsafe_allow_html=True
        )

        name = st.text_input(
            "Your Name *",
            placeholder="e.g. Srinija, Alex, Priya"
        )

        col1, col2 = st.columns(2, gap="large")

        with col1:
            provider = st.selectbox(
                "Preferred Sharing Channel *",
                ["WhatsApp", "Email", "Telegram"],
                help="Choose where you would like to send final expense summaries."
            )

        with col2:
            if provider == "WhatsApp":
                dest_label = "Recipient Phone Number *"
                dest_placeholder = "+91XXXXXXXXXX"
            elif provider == "Email":
                dest_label = "Recipient Email Address *"
                dest_placeholder = "friend@example.com"
            else:
                dest_label = "Telegram Chat ID / Username *"
                dest_placeholder = "@username or chat_id"

            destination = st.text_input(
                dest_label,
                placeholder=dest_placeholder
            )

        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

        submitted = st.form_submit_button(
            "🚀 Get Started",
            width="stretch",
            type="primary"
        )

        if submitted:
            if not name.strip():
                st.error("Please enter your name to continue.")
            elif not destination.strip():
                st.error(
                    f"Please enter a valid {provider} destination to continue."
                )
            else:
                st.session_state.name = name.strip()
                st.session_state.action_provider = provider
                st.session_state.action_destination = destination.strip()
                st.session_state.onboarded = True

                try:
                    client = get_gemini_client()
                    st.session_state.chat_session = create_gemini_chat_session(
                        client,
                        model_name=get_configured_model()
                    )
                except Exception:
                    st.session_state.chat_session = None

                st.session_state.messages = []
                welcome_text = WELCOME_MESSAGE_TEMPLATE.format(
                    name=st.session_state.name
                )
                add_message("assistant", "text", welcome_text)

                st.success("Welcome to BillWise AI! Loading your workspace...")
                time.sleep(0.35)
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# =====================================================================
# 11. MAIN APPLICATION INTERFACE
# =====================================================================
def render_main_app():
    """Render the primary BillWise AI application."""
    active_model = get_configured_model()

    # =====================================================
    # SIDEBAR
    # =====================================================
    with st.sidebar:

        st.markdown(
            """
            <div class="bw-sidebar-brand">
                <div class="bw-sidebar-brand-title">🧾 BillWise AI</div>
                <div class="bw-sidebar-brand-sub">
                    Snap it · Understand it · Split it
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.divider()

        demo_mode_val = st.checkbox(
            "🧪 Demo / Test Mode",
            value=st.session_state.get("demo_mode", False),
            key="demo_mode_checkbox",
            help=(
                "Use a pre-configured receipt without uploading an image "
                "or calling Gemini."
            )
        )
        st.session_state.demo_mode = demo_mode_val

        if demo_mode_val:
            st.success("Demo mode is ON")

        st.divider()

        st.markdown(
            f"""
            <div class="bw-side-card">
                <div class="bw-side-label">User</div>
                <div class="bw-side-value">{st.session_state.name or 'Not set'}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div class="bw-side-card">
                <div class="bw-side-label">Sharing Channel</div>
                <div class="bw-side-value">{st.session_state.action_provider}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div class="bw-side-card">
                <div class="bw-side-label">Destination</div>
                <div class="bw-side-value">{st.session_state.action_destination}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.divider()

        # =================================================
        # INTEGRATIONS
        # =================================================
        st.subheader("🔌 Integrations")

        st.markdown(
            """
            <div class="bw-side-card">
                <div style="font-size:1.05rem;font-weight:750;color:#e8ebf2;">
                    🟢 Twilio WhatsApp
                </div>
                <div style="color:#8f98a8;font-size:.78rem;margin-top:.25rem;">
                    Connected and ready to test
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button(
            "📲 Test Twilio WhatsApp",
            width="stretch",
            key="test_twilio_sidebar"
        ):
            with st.spinner("Testing Twilio WhatsApp..."):
                success, result = send_twilio_test_message(
                    destination=st.session_state.action_destination
                )

            if success:
                st.success("✅ Twilio WhatsApp is working!")
                st.caption(f"Message SID: {result}")
            else:
                st.error(f"❌ Twilio test failed: {result}")

        if st.button(
            "📧 Test Gmail SMTP",
            width="stretch",
            key="test_gmail_sidebar"
        ):
            with st.spinner("Testing Gmail SMTP..."):
                success, message = test_gmail_connection()

            if success:
                st.success(message)
            else:
                st.error(f"❌ Gmail test failed: {message}")

        st.divider()

        # =================================================
        # ACTIVE RECEIPT
        # =================================================
        if st.session_state.receipt_data:
            receipt = st.session_state.receipt_data
            st.subheader("📋 Active Receipt")
            st.write(f"**Store:** {receipt.merchant or 'Unknown'}")
            st.write(f"**Date:** {receipt.date or 'Unknown'}")

            tot = (
                f"{receipt.currency}{receipt.total:.2f}"
                if receipt.total is not None
                else "Missing"
            )
            st.metric("Receipt Total", tot)

            if st.session_state.validation_result:
                val = st.session_state.validation_result
                if val.status == "VERIFIED":
                    st.success("✅ Arithmetic Verified")
                elif val.status == "MISMATCH":
                    st.warning(
                        f"⚠️ Mismatch: {receipt.currency}{val.difference:.2f}"
                    )
                else:
                    st.info(f"ℹ️ Status: {val.status}")
        else:
            st.info("No active receipt loaded.")

        st.divider()

        with st.expander(
            "🧪 Gemini API Connectivity Check",
            expanded=False
        ):
            st.caption(
                "Run an on-demand text-only Gemini connectivity check."
            )

            if st.button(
                "Run Health Check",
                key="btn_ping_gemini",
                width="stretch"
            ):
                with st.spinner("Testing Gemini connectivity..."):
                    res = test_gemini_connectivity()

                if res["success"]:
                    st.success(res["message"])
                else:
                    st.error(res["message"])

        st.divider()

        if st.button(
            "🔄 New Receipt / Reset Session",
            width="stretch",
            key="reset_session_sidebar"
        ):
            reset_app_session()

        if st.button(
            "⚙️ Edit Profile / Re-onboard",
            width="stretch",
            key="re_onboard_sidebar"
        ):
            st.session_state.onboarded = False
            st.rerun()

    # =====================================================
    # MAIN HERO — OUTSIDE SIDEBAR
    # =====================================================
    st.markdown(
        """
        <div class="bw-hero">
            <div class="bw-logo">🧾</div>
            <div class="bw-title">BillWise AI</div>
            <div class="bw-subtitle">
                Multimodal AI Receipt Analyzer · Smart Bill Splitter
            </div>
            <div class="bw-tagline">
                Snap it. Understand it. Split it. Share it.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    tab_receipt, tab_split, tab_chat, tab_summary = st.tabs([
        "📸 1. Receipt & Analysis",
        "🧮 2. Bill Splitter",
        "💬 3. AI Receipt Chat",
        "📤 4. Summary & Share"
    ])

    # ==========================================
    # TAB 1: RECEIPT UPLOAD & ANALYSIS
    # ==========================================
    with tab_receipt:
        if st.session_state.get("demo_mode", False):
            st.info("🧪 Demo Receipt Mode: Using sample receipt data. Gemini Vision is not being called.")
            
            if st.session_state.receipt_data is None:
                st.subheader("🛒 Sample Demo Receipt: FreshMart Supermarket")
                st.write(
                    "Click the button below to load the structured sample receipt and test the entire "
                    "BillWise pipeline (deterministic arithmetic validation, equal & itemized splitting, "
                    "receipt chat queries, and expense summary sharing) without making any Gemini API calls."
                )
                if st.button("🧪 Load Demo Receipt", type="primary", width="stretch", key="btn_load_demo_receipt"):
                    demo_receipt = get_demo_receipt()
                    validation = validate_receipt_arithmetic(demo_receipt)
                    
                    st.session_state.receipt_data = demo_receipt
                    st.session_state.validation_result = validation
                    st.session_state.image_bytes = None
                    st.session_state.image_mime = "image/jpeg"
                    st.session_state.image_fingerprint = "demo_receipt_fingerprint"
                    st.session_state.split_result = None
                    st.session_state.generated_summary = ""
                    
                    intro_msg = (
                        f"Loaded demo receipt from **{demo_receipt.merchant}**.\n"
                        f"- **Items detected:** {len(demo_receipt.items)}\n"
                        f"- **Total:** {demo_receipt.currency}{demo_receipt.total:.2f}\n"
                        f"- **Validation:** {validation.message}"
                    )
                    add_message("assistant", "text", intro_msg)
                    st.success("Demo receipt loaded successfully!")
                    st.rerun()
        else:
            st.subheader("Upload or Snap Receipt Image")
            
            col_up1, col_up2 = st.columns([1, 1])
            with col_up1:
                uploaded_file = st.file_uploader(
                    "Upload receipt image (JPG, JPEG, PNG)",
                    type=["jpg", "jpeg", "png"],
                    key="receipt_uploader"
                )
            with col_up2:
                camera_file = st.camera_input("Or take a photo with camera", key="camera_input")

            active_file = uploaded_file or camera_file

            if active_file is not None:
                file_bytes = active_file.getvalue()
                mime_type = active_file.type or "image/jpeg"
                current_fingerprint = hashlib.sha256(file_bytes).hexdigest()[:16]
                
                if st.session_state.get("image_fingerprint") != current_fingerprint:
                    st.session_state.image_bytes = file_bytes
                    st.session_state.image_mime = mime_type
                    st.session_state.image_fingerprint = current_fingerprint
                    st.session_state.receipt_data = None
                    st.session_state.validation_result = None
                    st.session_state.split_result = None
                    st.session_state.generated_summary = ""
                    st.session_state.analysis_request_id = None
                    st.session_state.analysis_in_progress = False

                img_col, action_col = st.columns([1, 2])
                with img_col:
                    st.image(file_bytes, caption="Uploaded Receipt", width="stretch")

                with action_col:
                    if st.session_state.receipt_data is None:
                        is_in_progress = st.session_state.get("analysis_in_progress", False)
                        st.info(f"Image ready for AI Multimodal Analysis via `{active_model}`.")
                        
                        btn_analyze = st.button(
                            "🤖 Analyze Receipt with Gemini Vision",
                            type="primary",
                            width="stretch",
                            disabled=is_in_progress,
                            key="btn_analyze_receipt"
                        )

                        if btn_analyze:
                            if st.session_state.get("analysis_in_progress", False):
                                req_id = st.session_state.get("analysis_request_id") or "unknown"
                                log_gemini_diagnostic(
                                    "receipt_analysis_lock_rejected",
                                    reason="analysis_already_in_progress",
                                    request_id=req_id
                                )
                                st.warning("Receipt analysis is already in progress. Please wait for the current request to finish.")
                            else:
                                request_id = f"req_{int(time.time())}_{uuid.uuid4().hex[:6]}"
                                st.session_state.analysis_in_progress = True
                                st.session_state.analysis_request_id = request_id
                                log_gemini_diagnostic(
                                    "receipt_analysis_lock_acquired",
                                    request_id=request_id,
                                    model=active_model
                                )
                                
                                analysis_success = False
                                start_time = time.time()

                                with st.status("Analyzing receipt with Gemini Vision...", expanded=True) as status_box:
                                    try:
                                        status_box.write("🔍 Preparing and validating receipt image...")
                                        client = get_gemini_client()
                                        
                                        status_box.write(f"🤖 Sending receipt to Gemini Vision (`{active_model}`)...")
                                        
                                        def on_retry_status(retry_msg: str):
                                            status_box.write(f"⏳ {retry_msg}")

                                        receipt = analyze_receipt_image(
                                            image_bytes=file_bytes,
                                            mime_type=mime_type,
                                            model_name=active_model,
                                            client=client,
                                            status_callback=on_retry_status,
                                            request_id=request_id
                                        )
                                        status_box.write("🧮 Validating arithmetic with deterministic Python engine...")
                                        validation = validate_receipt_arithmetic(receipt)
                                        
                                        # Verify request ID and image fingerprint before committing to state
                                        if (
                                            st.session_state.get("analysis_request_id") == request_id
                                            and st.session_state.get("image_fingerprint") == current_fingerprint
                                        ):
                                            st.session_state.receipt_data = receipt
                                            st.session_state.validation_result = validation

                                            add_message("user", "image", file_bytes)
                                            intro_msg = (
                                                f"Analyzed receipt from **{receipt.merchant or 'Vendor'}**.\n"
                                                f"- **Items detected:** {len(receipt.items)}\n"
                                                f"- **Total:** {receipt.currency}{receipt.total if receipt.total is not None else 'Unclear'}\n"
                                                f"- **Validation:** {validation.message}"
                                            )
                                            add_message("assistant", "text", intro_msg)
                                            status_box.update(label="✅ Receipt analyzed successfully!", state="complete", expanded=False)
                                            st.success("Receipt successfully analyzed!")
                                            analysis_success = True
                                        else:
                                            log_gemini_diagnostic(
                                                "receipt_analysis_discarded",
                                                reason="stale_request_or_image_changed",
                                                request_id=request_id,
                                                active_request_id=st.session_state.get("analysis_request_id")
                                            )
                                            status_box.update(label="⚠️ Image changed during analysis. Analysis discarded.", state="error", expanded=True)

                                    except Exception as e:
                                        status_box.update(label="⚠️ Receipt analysis failed", state="error", expanded=True)
                                        err_display = format_gemini_error(e)
                                        st.error(err_display)
                                    finally:
                                        st.session_state.analysis_in_progress = False
                                        elapsed = round(time.time() - start_time, 2)
                                        log_gemini_diagnostic(
                                            "receipt_analysis_finished",
                                            request_id=request_id,
                                            success=analysis_success,
                                            elapsed_seconds=elapsed
                                        )

                                if analysis_success:
                                    st.rerun()

        if st.session_state.receipt_data is not None:
            receipt: ReceiptData = st.session_state.receipt_data
            val: ReceiptValidationResult = st.session_state.validation_result
            
            st.divider()
            st.subheader(f"📊 Receipt Details: {receipt.merchant or 'Store'}")

            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            with m_col1:
                st.metric("Merchant", receipt.merchant or "Unknown")
            with m_col2:
                st.metric("Date", receipt.date or "Not specified")
            with m_col3:
                curr_tot = f"{receipt.currency}{receipt.total:.2f}" if receipt.total is not None else "Missing"
                st.metric("Detected Total", curr_tot)
            with m_col4:
                st.metric("Items Count", str(len(receipt.items)))

            if val:
                if val.status == "VERIFIED":
                    st.success(val.message)
                elif val.status == "MISMATCH":
                    st.warning(val.message)
                    st.caption(
                        f"Items Sum: {receipt.currency}{val.items_sum:.2f} | "
                        f"Taxes: +{receipt.currency}{receipt.tax or 0.0:.2f} | "
                        f"Tip/Fees: +{receipt.currency}{receipt.tip_or_service_charge or 0.0:.2f} | "
                        f"Discounts: -{receipt.currency}{receipt.discount or 0.0:.2f} | "
                        f"Calculated Total: {receipt.currency}{val.expected_total:.2f}"
                    )
                elif val.status == "MISSING_TOTAL":
                    st.info(val.message)
                elif val.status == "NOT_A_RECEIPT":
                    st.error(val.message)

            st.markdown("#### 🛒 Itemized Breakdown")
            if receipt.items:
                table_rows = []
                for idx, item in enumerate(receipt.items, 1):
                    unit_p_str = f"{receipt.currency}{item.unit_price:.2f}" if item.unit_price is not None else "-"
                    table_rows.append({
                        "#": idx,
                        "Item Name": item.name,
                        "Quantity": item.quantity,
                        f"Unit Price ({receipt.currency})": unit_p_str,
                        f"Total Price ({receipt.currency})": f"{receipt.currency}{item.total_price:.2f}"
                    })
                df = pd.DataFrame(table_rows)
                st.dataframe(df, width="stretch", hide_index=True)
            else:
                st.write("No individual items were identified on this receipt.")

            st.markdown("#### 💰 Financial Summary")
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                st.write(f"• **Items Sum:** {receipt.currency}{val.items_sum:.2f}" if val else "")
                if receipt.subtotal is not None:
                    st.write(f"• **Detected Subtotal:** {receipt.currency}{receipt.subtotal:.2f}")
                if receipt.tax is not None:
                    st.write(f"• **Taxes:** {receipt.currency}{receipt.tax:.2f}")
            with f_col2:
                if receipt.discount and receipt.discount > 0:
                    st.write(f"• **Discount:** -{receipt.currency}{receipt.discount:.2f}")
                if receipt.tip_or_service_charge and receipt.tip_or_service_charge > 0:
                    st.write(f"• **Service Charge / Tip:** +{receipt.currency}{receipt.tip_or_service_charge:.2f}")
                tot_display = f"{receipt.currency}{receipt.total:.2f}" if receipt.total is not None else "Not detected"
                st.write(f"• **Grand Total:** **{tot_display}**")

            if receipt.notes_or_uncertainties:
                st.caption(f"📝 **OCR Notes:** {receipt.notes_or_uncertainties}")


    # ==========================================
    # TAB 2: BILL SPLITTER
    # ==========================================

    with tab_split:

        st.subheader("🧮 Smart Bill Splitter")

        if not st.session_state.receipt_data:

            st.info("Please upload or load a receipt first.")

        else:

            receipt: ReceiptData = st.session_state.receipt_data
            val: ReceiptValidationResult = st.session_state.validation_result

            # ------------------------------------------
            # USE DETECTED TOTAL
            # ------------------------------------------

            effective_total = receipt.total or 0.0

            if effective_total <= 0:

                st.error(
                    "Unable to split the bill because the total amount "
                    "is missing or invalid."
                )

            else:

                st.markdown(
                    f"### 💰 Total Bill: "
                    f"{receipt.currency}{effective_total:.2f}"
                )

                # ------------------------------------------
                # SPLIT MODE
                # ------------------------------------------

                split_mode = st.radio(
                    "Choose Split Method",
                    [
                        "Equal Split",
                        "Item-Based Split"
                    ],
                    horizontal=True
                )

                # ==========================================
                # EQUAL SPLIT
                # ==========================================

                if split_mode == "Equal Split":

                    st.markdown("#### 👥 People Sharing This Bill")

                    num_people = st.number_input(
                        "Number of people",
                        min_value=1,
                        max_value=20,
                        value=2,
                        step=1,
                        key="equal_split_people"
                    )

                    # --------------------------------------
                    # PARTICIPANT DETAILS
                    # --------------------------------------

                    st.markdown("### 👤 Participant Details")

                    participant_details = []

                    # --------------------------------------
                    # CREATE DEFAULT PARTICIPANT NAMES
                    # --------------------------------------

                    participant_names = [
                        f"Person {i + 1}"
                        for i in range(int(num_people))
                    ]

                    # --------------------------------------
                    # CALCULATE EQUAL SPLIT
                    # --------------------------------------

                    split_res = calculate_equal_split(
                        total_amount=effective_total,
                        num_people=int(num_people),
                        names=participant_names,
                        currency=receipt.currency
                    )

                    st.session_state.split_result = split_res

                    # --------------------------------------
                    # COLLECT PARTICIPANT INFORMATION
                    # --------------------------------------

                    for idx, share in enumerate(split_res.shares):

                        with st.expander(
                            f"👤 Person {idx + 1} — "
                            f"{receipt.currency}{share.total_share:.2f}",
                            expanded=True
                        ):

                            p_col1, p_col2 = st.columns(2)

                            with p_col1:

                                participant_name = st.text_input(
                                    "Name",
                                    value=f"Person {idx + 1}",
                                    key=f"participant_name_{idx}"
                                )

                            with p_col2:

                                participant_email = st.text_input(
                                    "Email",
                                    placeholder="example@gmail.com",
                                    key=f"participant_email_{idx}"
                                )

                            participant_whatsapp = st.text_input(
                                "WhatsApp Number",
                                placeholder="+919876543210",
                                key=f"participant_whatsapp_{idx}"
                            )

                            st.caption(
                                f"💰 Individual Share: "
                                f"{receipt.currency}"
                                f"{share.total_share:.2f}"
                            )

                            participant_details.append(
                                {
                                    "name": participant_name,
                                    "email": participant_email,
                                    "whatsapp": participant_whatsapp,
                                    "share": share.total_share
                                }
                            )

                    # --------------------------------------
                    # SAVE PARTICIPANT DETAILS
                    # --------------------------------------

                    st.session_state.participant_details = (
                        participant_details
                    )

                    # --------------------------------------
                    # SPLIT SUMMARY
                    # --------------------------------------

                    st.markdown("### 📊 Split Summary")

                    st.write(
                        f"**Total Bill:** "
                        f"{receipt.currency}{split_res.total_bill:.2f}"
                    )

                    st.write(
                        f"**Number of People:** "
                        f"{split_res.num_people}"
                    )

                    st.write(
                        f"**Average Share:** "
                        f"{receipt.currency}"
                        f"{split_res.total_bill / split_res.num_people:.2f}"
                    )

                    st.divider()

                    for idx, share in enumerate(split_res.shares):

                        participant_name = (
                            participant_details[idx]["name"]
                            if idx < len(participant_details)
                            else f"Person {idx + 1}"
                        )

                        st.write(
                            f"👤 **{participant_name}** — "
                            f"{receipt.currency}{share.total_share:.2f}"
                        )

                    # --------------------------------------
                    # VERIFICATION
                    # --------------------------------------

                    if split_res.reconciled:

                        st.success(
                            f"✅ Split verified. "
                            f"Total of all shares = "
                            f"{receipt.currency}"
                            f"{split_res.reconciled_sum:.2f}"
                        )

                    else:

                        st.warning(
                            "⚠️ Split shares do not exactly match "
                            "the bill total."
                        )

                # ==========================================
                # ITEM-BASED SPLIT
                # ==========================================

                else:

                    st.markdown("#### 🛒 Assign Items to People")

                    if not receipt.items:

                        st.warning(
                            "No individual items were detected, "
                            "so item-based splitting is unavailable."
                        )

                    else:

                        num_people = st.number_input(
                            "Number of people",
                            min_value=1,
                            max_value=20,
                            value=2,
                            step=1,
                            key="item_split_people"
                        )

                        st.info(
                            "Select which person is responsible "
                            "for each item."
                        )

                        # --------------------------------------
                        # CREATE PEOPLE
                        # --------------------------------------

                        item_people = [
                            f"Person {i + 1}"
                            for i in range(int(num_people))
                        ]

                        # --------------------------------------
                        # ASSIGN ITEMS
                        # --------------------------------------

                        assignments = {}

                        for idx, item in enumerate(receipt.items):

                            person = st.selectbox(
                                f"{item.name} "
                                f"({receipt.currency}"
                                f"{item.total_price:.2f})",

                                options=item_people,

                                key=f"item_assignment_{idx}"
                            )

                            assignments[idx] = [person]

                        # --------------------------------------
                        # CALCULATE ITEM-BASED SPLIT
                        # --------------------------------------

                        if st.button(
                            "🧮 Calculate Item-Based Split",
                            type="primary",
                            width="stretch"
                        ):

                            item_split_result = calculate_item_split(
                                receipt=receipt,
                                names=item_people,
                                item_assignments=assignments
                            )

                            st.session_state.split_result = (
                                item_split_result
                            )

                            st.session_state.item_split_totals = {
                                share.name: share.total_share
                                for share in item_split_result.shares
                            }

                        # --------------------------------------
                        # DISPLAY ITEM SPLIT
                        # --------------------------------------

                        if st.session_state.get(
                            "item_split_totals"
                        ):

                            st.markdown(
                                "### 📊 Item-Based Split Summary"
                            )

                            for person, amount in st.session_state.item_split_totals.items():

                                st.write(
                                    f"👤 **{person}** — "
                                    f"{receipt.currency}"
                                    f"{amount:.2f}"
                                )

                            # ----------------------------------
                            # VERIFY ITEM SPLIT
                            # ----------------------------------

                            item_result = (
                                st.session_state.split_result
                            )

                            if item_result and item_result.reconciled:

                                st.success(
                                    f"✅ Item split verified. "
                                    f"Total = "
                                    f"{receipt.currency}"
                                    f"{item_result.reconciled_sum:.2f}"
                                )    
    # ==========================================
    # TAB 3: AI RECEIPT CHAT
    # ==========================================
    with tab_chat:
        st.subheader("💬 AI Bill Assistant")
        st.caption(f"Ask questions about your analyzed receipt or bill splitting (Powered by `{active_model}`).")

        st.markdown("**Quick Prompts:**")
        q_cols = st.columns(4)
        quick_prompts = [
            "What is the most expensive item?",
            "How much tax did I pay?",
            "What is the total bill amount?",
            "Split this bill between 4 people."
        ]
        chosen_prompt = None
        for i, qp in enumerate(quick_prompts):
            with q_cols[i]:
                if st.button(qp, key=f"qp_{i}", width="stretch"):
                    chosen_prompt = qp

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                if msg.get("kind") == "image":
                    st.image(msg["content"], width=300, caption="Uploaded Receipt")
                else:
                    st.markdown(msg["content"])

        user_input = st.chat_input("Ask a question about the receipt...") or chosen_prompt

        if user_input:
            add_message("user", "text", user_input)
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                # 1. Deterministic Python Answer first for factual receipt queries
                python_answer = try_answer_receipt_with_python(
                    user_prompt=user_input,
                    receipt=st.session_state.receipt_data,
                    split_result=st.session_state.split_result
                )

                if python_answer is not None:
                    st.markdown(python_answer)
                    add_message("assistant", "text", python_answer)
                elif st.session_state.get("demo_mode", False):
                    # Gemini conversational calls bypassed in Demo Mode
                    demo_chat_info = (
                        "ℹ️ **Gemini Conversational Chat is disabled in Demo Mode.**\n\n"
                        "Deterministic receipt calculations are fully active! Try asking:\n"
                        "- *\"What is the total bill amount?\"*\n"
                        "- *\"How much tax did I pay?\"*\n"
                        "- *\"What is the most expensive item?\"*\n"
                        "- *\"What is the cheapest item?\"*\n"
                        "- *\"Split this bill between 4 people.\"*\n"
                        "- *\"List all items.\"*"
                    )
                    st.info(demo_chat_info)
                    add_message("assistant", "text", demo_chat_info)
                else:
                    # 2. Natural language reasoning / conversational questions delegated to Gemini with retry
                    with st.spinner("Thinking..."):
                        try:
                            client = get_gemini_client()
                            if st.session_state.chat_session is None:
                                st.session_state.chat_session = create_gemini_chat_session(client, model_name=active_model)
                            
                            response_text = ask_receipt_assistant(
                                chat_session=st.session_state.chat_session,
                                user_prompt=user_input,
                                receipt=st.session_state.receipt_data,
                                split_result=st.session_state.split_result
                            )
                            st.markdown(response_text)
                            add_message("assistant", "text", response_text)
                        except Exception as e:
                            err_msg = format_gemini_error(e)
                            st.error(err_msg)
                            add_message("assistant", "text", err_msg)

    # ==========================================
    # TAB 4: SUMMARY & SHARING ACTION
    # ==========================================
    with tab_summary:
        st.subheader("📤 Expense Summary & Sharing")
        
        if not st.session_state.receipt_data:
            st.info("Please upload or load a receipt first to generate an expense summary.")
        else:
            receipt: ReceiptData = st.session_state.receipt_data
            split_res: BillSplitResult = st.session_state.split_result

            if st.button("✨ Generate / Refresh Final Summary", type="primary"):
                if st.session_state.get("demo_mode", False):
                    summary_text = generate_expense_summary(receipt, split_res, client=None, model_name=active_model)
                    st.session_state.generated_summary = summary_text
                else:
                    with st.spinner(f"Generating formatted expense summary via `{active_model}`..."):
                        try:
                            client = get_gemini_client()
                        except Exception:
                            client = None
                        summary_text = generate_expense_summary(receipt, split_res, client=client, model_name=active_model)
                        st.session_state.generated_summary = summary_text

            if not st.session_state.generated_summary:
                st.session_state.generated_summary = generate_expense_summary(receipt, split_res, client=None, model_name=active_model)

            st.markdown("##### Review and Edit Summary Before Sending:")
            editable_summary = st.text_area(
                "Summary Text",
                value=st.session_state.generated_summary,
                height=250,
                key="summary_text_area"
            )

            st.divider()
            st.markdown("##### 🚀 Dispatch to Configured Channel")

            d_col1, d_col2 = st.columns([1, 2])

            with d_col1:
                channel = st.selectbox(
                    "Channel",
                    ["WhatsApp", "Email", "Telegram"],
                    index=(
                        ["WhatsApp", "Email", "Telegram"].index(
                            st.session_state.action_provider
                        )
                        if st.session_state.action_provider
                        in ["WhatsApp", "Email", "Telegram"]
                        else 0
                    )
                )

            # =========================================================
            # EMAIL
            # =========================================================

            if channel == "Email":

                email_mode = st.radio(
                    "What do you want to send?",
                    [
                        "📋 Full Bill Summary",
                        "👤 Individual Shares"
                    ],
                    horizontal=True
                )

                # -----------------------------------------------------
                # FULL BILL SUMMARY
                # -----------------------------------------------------

                if email_mode == "📋 Full Bill Summary":

                    dest = st.text_input(
                        "Email Address",
                        value=st.session_state.action_destination,
                        placeholder="example@gmail.com",
                        help="Enter the email address that should receive the complete BillWise summary."
                    )

                    if st.button(
                        "📨 Send Full Bill Summary via Email",
                        type="primary",
                        width="stretch"
                    ):

                        if not dest.strip():

                            st.error(
                                "Please enter a valid email address."
                            )

                        elif "@" not in dest.strip():

                            st.error(
                                "Please enter a valid email address."
                            )

                        else:

                            with st.spinner(
                                "Sending full BillWise summary..."
                            ):

                                result = send_summary(
                                    provider="email",
                                    destination=dest.strip(),
                                    summary_text=editable_summary
                                )

                            if result.success:

                                st.success(
                                    result.message
                                )

                            else:

                                st.error(
                                    result.message
                                )

                # -----------------------------------------------------
                # INDIVIDUAL SHARES
                # -----------------------------------------------------

                else:

                    st.markdown(
                        "### 👥 Individual Share Emails"
                    )

                    participants = st.session_state.get(
                        "participant_details",
                        []
                    )

                    if not participants:

                        st.warning(
                            "No participant details found. "
                            "Please go to the Bill Splitter tab "
                            "and add participant details first."
                        )

                    else:

                        st.info(
                            "BillWise will send each participant "
                            "a separate email containing only "
                            "their individual share."
                        )

                        # -------------------------------------------------
                        # DISPLAY PARTICIPANTS
                        # -------------------------------------------------

                        for idx, participant in enumerate(
                            participants
                        ):

                            participant_name = participant.get(
                                "name",
                                f"Person {idx + 1}"
                            )

                            participant_email = participant.get(
                                "email",
                                ""
                            )

                            participant_share = participant.get(
                                "share",
                                0
                            )

                            participant_currency = participant.get(
                                "currency",
                                receipt.currency
                            )

                            st.write(
                                f"👤 **{participant_name}** | "
                                f"📧 {participant_email or 'Email not provided'} | "
                                f"💰 {participant_currency}"
                                f"{participant_share:.2f}"
                            )

                        st.divider()

                        # -------------------------------------------------
                        # SEND INDIVIDUAL EMAILS
                        # -------------------------------------------------

                        if st.button(
                            "📨 Send Individual Shares to Everyone",
                            type="primary",
                            width="stretch"
                        ):

                            sent_count = 0
                            failed_count = 0

                            with st.spinner(
                                "Sending individual share emails..."
                            ):

                                for idx, participant in enumerate(
                                    participants
                                ):

                                    participant_name = participant.get(
                                        "name",
                                        f"Person {idx + 1}"
                                    )

                                    participant_email = participant.get(
                                        "email",
                                        ""
                                    ).strip()

                                    participant_share = participant.get(
                                        "share",
                                        0
                                    )

                                    participant_currency = participant.get(
                                        "currency",
                                        receipt.currency
                                    )

                                    # -----------------------------
                                    # CHECK EMAIL
                                    # -----------------------------

                                    if not participant_email:

                                        st.warning(
                                            f"⚠️ {participant_name} "
                                            f"does not have an email address."
                                        )

                                        failed_count += 1
                                        continue

                                    # -----------------------------
                                    # CREATE PERSONAL MESSAGE
                                    # -----------------------------

                                    individual_message = (
                                        f"Hello {participant_name},\n\n"
                                        f"🧾 BillWise AI\n\n"
                                        f"You need to pay "
                                        f"{participant_currency}"
                                        f"{participant_share:.2f} "
                                        f"for the bill.\n\n"
                                        f"Merchant: "
                                        f"{receipt.merchant or 'Unknown'}\n"
                                        f"Date: "
                                        f"{receipt.date or 'Unknown'}\n"
                                        f"Total Bill: "
                                        f"{receipt.currency}"
                                        f"{receipt.total:.2f}\n"
                                        f"Split Among: "
                                        f"{len(participants)} people\n\n"
                                        f"Your Share: "
                                        f"{participant_currency}"
                                        f"{participant_share:.2f}\n\n"
                                        f"— Generated by BillWise AI"
                                    )

                                    # -----------------------------
                                    # SEND EMAIL
                                    # -----------------------------

                                    result = send_email_smtp(
                                        destination=participant_email,
                                        summary_text=individual_message,
                                        subject=(
                                            "BillWise AI - "
                                            f"Your Share: "
                                            f"{participant_currency}"
                                            f"{participant_share:.2f}"
                                        )
                                    )

                                    if result.success:

                                        sent_count += 1

                                        st.success(
                                            f"✅ Sent to "
                                            f"{participant_name} "
                                            f"({participant_email})"
                                        )

                                    else:

                                        failed_count += 1

                                        st.error(
                                            f"❌ Failed for "
                                            f"{participant_name}: "
                                            f"{result.message}"
                                        )

                            st.divider()

                            # -----------------------------
                            # FINAL RESULT
                            # -----------------------------

                            if sent_count > 0:

                                st.success(
                                    f"🎉 Successfully sent "
                                    f"{sent_count} individual "
                                    f"share email(s)!"
                                )

                            if failed_count > 0:

                                st.warning(
                                    f"⚠️ {failed_count} participant(s) "
                                    f"could not be emailed."
                                )

            # =========================================================
            # WHATSAPP / TELEGRAM
            # =========================================================

            else:

                with d_col2:

                    dest = st.text_input(
                        "Destination",
                        value=st.session_state.action_destination,
                        placeholder="+919876543210",
                        help="Enter the recipient's WhatsApp or Telegram number."
                    )

                if st.button(
                    f"📨 Send Summary via {channel}",
                    type="primary",
                    width="stretch"
                ):

                    if not dest.strip():

                        st.error(
                            "Please enter a valid destination "
                            "address or phone number."
                        )

                    else:

                        with st.spinner(
                            f"Sending summary via {channel}..."
                        ):

                            result = send_summary(
                                provider=channel.lower(),
                                destination=dest.strip(),
                                summary_text=editable_summary
                            )

                        if result.success:

                            st.success(
                                result.message
                            )

                        else:

                            st.warning(
                                result.message
                            )

                        if result.action_url:

                            st.markdown(
                                f"""
                                <div class='share-card'>
                                    🔗 <b>Direct Action Link:</b><br/>
                                    <a href="{result.action_url}"
                                       target="_blank"
                                       style="text-decoration:none;
                                              font-weight:bold;
                                              color:#2563EB;">
                                        👉 Click here to open and share in {channel}
                                    </a>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

            # =========================================================
            # WHATSAPP WEB — ACTUAL BILLWISE SUMMARY
            # =========================================================
            # =========================================================
            # WHATSAPP WEB — ACTUAL BILLWISE SUMMARY
            # =========================================================

            if channel == "WhatsApp":

                st.markdown(
                    "### 💬 Share Actual BillWise Summary"
                )

                whatsapp_dest = dest.strip()

                whatsapp_dest = (
                    whatsapp_dest
                    .replace(" ", "")
                    .replace("-", "")
                )

                if whatsapp_dest.startswith("whatsapp:"):

                    whatsapp_dest = whatsapp_dest.replace(
                        "whatsapp:",
                        ""
                    )

                if (
                    whatsapp_dest
                    and not whatsapp_dest.startswith("+")
                ):

                    whatsapp_dest = "+" + whatsapp_dest

                if whatsapp_dest:

                    phone_only = whatsapp_dest.replace(
                        "+",
                        ""
                    )

                    whatsapp_summary = format_whatsapp_summary(
                        editable_summary
                    )

                    encoded_summary = urllib.parse.quote(
                        whatsapp_summary
                    )

                    whatsapp_link = (
                        f"https://wa.me/" 
                        f"{phone_only}" 
                        f"?text={encoded_summary}" 
                    ) 
 
                    st.info( 
                        "💬 Your BillWise summary is ready " 
                        "to send through WhatsApp." 
                    ) 
 
                    st.link_button( 
                        "👉 Open WhatsApp with BillWise Summary", 
                        whatsapp_link, 
                        width="stretch" 
                    )

# ===================================================================== 
# 12. APPLICATION ENTRYPOINT 
# ===================================================================== 
def main(): 
    if not st.session_state.onboarded: 
        render_onboarding() 
    else: 
        render_main_app() 
 
 
if __name__ == "__main__": 
    main()
