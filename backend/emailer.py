import os
import re
import time
import logging
from typing import Optional, Dict, Any, Tuple, List

import requests

log = logging.getLogger("service")

# --- Config from environment ---
BREVO_API_KEY      = os.getenv("BREVO_API_KEY", "").strip()
BREVO_BASE_URL     = os.getenv("BREVO_BASE_URL", "https://api.brevo.com/v3").rstrip("/")
BREVO_TIMEOUT_S    = float(os.getenv("BREVO_TIMEOUT_S", "20"))
BREVO_MAX_RETRIES  = int(os.getenv("BREVO_MAX_RETRIES", "3"))
BREVO_BACKOFF_BASE = float(os.getenv("BREVO_BACKOFF_BASE", "1.5"))

# Sender identity
BREVO_SENDER_EMAIL = (os.getenv("BREVO_SENDER_EMAIL") or "").strip()
BREVO_SENDER_NAME  = (os.getenv("BREVO_SENDER_NAME") or "").strip()

# Backward-compat: allow using your old SMTP_FROM="Name <email>" if present
SMTP_FROM = os.getenv("SMTP_FROM", "").strip()

def _parse_from_address(s: str) -> Tuple[Optional[str], str]:
    """
    Accepts 'Name <email@domain>' or 'email@domain' and returns (name, email).
    """
    if not s:
        return (None, "")
    m = re.match(r'\s*(?:"?([^"]*)"?\s*)?<\s*([^>]+)\s*>\s*$', s)
    if m:
        name = (m.group(1) or "").strip() or None
        email = m.group(2).strip()
        return (name, email)
    return (None, s.strip())

def _resolve_sender() -> Dict[str, str]:
    name = BREVO_SENDER_NAME
    email = BREVO_SENDER_EMAIL
    if not email and SMTP_FROM:
        n, e = _parse_from_address(SMTP_FROM)
        if e:
            email = e
        if n and not name:
            name = n
    if not email:
        # Brevo requires a verified sender; fail loudly if missing
        raise RuntimeError("BREVO_SENDER_EMAIL (or SMTP_FROM) is required for Brevo API emails.")
    return {"email": email, **({"name": name} if name else {})}

def _backoff_delay(attempt: int) -> float:
    # 1st retry ~1.5s, then ~2.25s, then ~3.375s… capped to 30s
    delay = min(30.0, (BREVO_BACKOFF_BASE ** max(0, attempt)))
    return delay

def _brevo_headers() -> Dict[str, str]:
    if not BREVO_API_KEY:
        raise RuntimeError("BREVO_API_KEY is not set")
    return {
        "api-key": BREVO_API_KEY,
        "accept": "application/json",
        "content-type": "application/json",
    }

def _brevo_payload(
    to_email: str,
    subject: str,
    html: str,
    to_name: Optional[str] = None,
    text: Optional[str] = None,
    reply_to_email: Optional[str] = None,
    reply_to_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    sender = _resolve_sender()
    payload: Dict[str, Any] = {
        "sender": sender,
        "to": [{"email": to_email, **({"name": to_name} if to_name else {})}],
        "subject": subject,
        "htmlContent": html if html is not None else "",
    }
    if text:
        payload["textContent"] = text
    if reply_to_email:
        payload["replyTo"] = {"email": reply_to_email, **({"name": reply_to_name} if reply_to_name else {})}
    if tags:
        payload["tags"] = tags
    return payload

def send_email(
    to_email: str,
    subject: str,
    html: str,
    *,
    to_name: Optional[str] = None,
    text: Optional[str] = None,
    reply_to_email: Optional[str] = None,
    reply_to_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> bool:
    """
    Send a transactional email via Brevo REST API.
    Returns True on success, False on final failure.
    Raises when misconfigured (e.g., missing API key/sender).
    """
    url = f"{BREVO_BASE_URL}/smtp/email"
    headers = _brevo_headers()
    data = _brevo_payload(
        to_email=to_email,
        subject=subject,
        html=html,
        to_name=to_name,
        text=text,
        reply_to_email=reply_to_email,
        reply_to_name=reply_to_name,
        tags=tags,
    )

    last_err = None
    for attempt in range(BREVO_MAX_RETRIES + 1):
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=BREVO_TIMEOUT_S)
            # Success: 201 Created
            if 200 <= resp.status_code < 300:
                log.info("Brevo email sent to %s (status %s)", to_email, resp.status_code)
                return True

            # Retry on 429 and 5xx
            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                last_err = f"{resp.status_code} {resp.reason} - {resp.text[:300]}"
                if attempt < BREVO_MAX_RETRIES:
                    delay = _backoff_delay(attempt)
                    log.warning("Brevo email transient failure; retrying in %.1fs: %s", delay, last_err)
                    time.sleep(delay)
                    continue

            # Non-retryable error
            log.error("Brevo email failed (%s): %s", resp.status_code, resp.text)
            return False

        except requests.RequestException as e:
            last_err = str(e)
            if attempt < BREVO_MAX_RETRIES:
                delay = _backoff_delay(attempt)
                log.warning("Brevo email request error; retrying in %.1fs: %s", delay, last_err)
                time.sleep(delay)
                continue
            log.error("Brevo email request failed: %s", last_err)
            return False

    # Shouldn’t reach here
    if last_err:
        log.error("Brevo email failed after retries: %s", last_err)
    return False
    

def build_results_email_html(link: str, session_id: str = "") -> str:
    return f"""\
        <html>
        <body style="font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif; line-height:1.5">
            <p>Hi,</p>
            <p>Your <strong>ABM validation</strong> results for session <em>{session_id}</em> are ready and will be available for the next 14 days.</p>
            <p>
                <a href="{link}"
                    style="background:#2563eb;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none;display:inline-block">
                    Open results
                </a>
            </p>
            <p>If the button doesn't work, copy this URL:<br>
                <a href="{link}">{link}</a>
            </p>
            <hr style="border:none;border-top:1px solid #e5e7eb;margin:16px 0">
            <p style="color:#6b7280;font-size:12px">This is an automated message. Please do not reply.</p>
        </body>
        </html>
        """