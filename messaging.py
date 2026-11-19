"""
messaging.py - SENDING and RECEIVING WhatsApp messages through Twilio.

- send(): logs every outgoing message in our database (so the dashboard + simulator can show it),
  then sends it for real through Twilio's WhatsApp API.
  Demo numbers (starting +91000) are never sent to Twilio; they live only inside the simulator.
- download_media(): Twilio gives us a link to a voice note / photo; we download the actual file.
"""
import os
import requests
import db

TWILIO_API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


def _sid():
    return os.environ.get("TWILIO_ACCOUNT_SID", "")


def _token():
    return os.environ.get("TWILIO_AUTH_TOKEN", "")


def is_configured():
    return bool(_sid() and _token())


def public_url():
    """The internet address of this app (Render sets RENDER_EXTERNAL_URL for us)."""
    return (os.environ.get("PUBLIC_URL") or os.environ.get("RENDER_EXTERNAL_URL") or "http://localhost:5000").rstrip("/")


def send(planner_id, phone, body, media_url=None):
    """Send one WhatsApp message. Returns True if Twilio accepted it (or it was a simulated number)."""
    db.log_message(planner_id, phone, "out", body, "image" if media_url else "")
    if not phone or phone.startswith(db.SIMULATED_PREFIX) or not is_configured():
        return True
    data = {
        "From": "whatsapp:" + os.environ.get("TWILIO_WHATSAPP_FROM", "+14155238886"),
        "To": "whatsapp:" + phone,
        "Body": body[:1500],  # WhatsApp/Twilio limit is 1600 characters
    }
    if media_url and not media_url.startswith("http://localhost"):
        data["MediaUrl"] = media_url
    try:
        resp = requests.post(TWILIO_API.format(sid=_sid()), data=data, auth=(_sid(), _token()), timeout=20)
        if resp.status_code >= 300:
            print("Twilio send failed:", resp.status_code, resp.text[:300])
            return False
        return True
    except requests.RequestException as e:
        print("Twilio send error:", e)
        return False


def download_media(url):
    """Download a voice note or photo that someone sent us on WhatsApp. Returns the raw bytes."""
    resp = requests.get(url, auth=(_sid(), _token()), timeout=30)
    resp.raise_for_status()
    return resp.content
