"""
messaging.py - SENDING and RECEIVING WhatsApp messages.

Two ways to reach WhatsApp (we pick whichever has keys set; Meta first):
  1. Meta WhatsApp Cloud API (official, by WhatsApp's owner). Free test number, no approval needed.
  2. Twilio WhatsApp (kept as a backup; its free trial only allows fixed template messages).

- send(): logs every outgoing message in our database (so the dashboard + simulator can show it),
  then sends it for real on WhatsApp.
  Demo numbers (starting +91000) are never sent out; they live only inside the simulator.
- send_voice(): sends a voice note (a link to the audio file stored in our app).
- download_meta_media() / download_twilio_media(): fetch a voice note or photo someone sent us.
"""
import os
import hmac
import hashlib
import requests
import db

TWILIO_API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
META_API = "https://graph.facebook.com/{version}"


# ---------- which WhatsApp provider? ----------

def _meta_token():
    return os.environ.get("META_ACCESS_TOKEN", "").strip()


def _meta_phone_id():
    return os.environ.get("META_PHONE_NUMBER_ID", "").strip()


def _meta_base():
    return META_API.format(version=os.environ.get("META_API_VERSION", "v23.0"))


def meta_configured():
    return bool(_meta_token() and _meta_phone_id())


def _sid():
    return os.environ.get("TWILIO_ACCOUNT_SID", "")


def _token():
    return os.environ.get("TWILIO_AUTH_TOKEN", "")


def twilio_configured():
    return bool(_sid() and _token())


def is_configured():
    return meta_configured() or twilio_configured()


def provider_name():
    return "Meta WhatsApp Cloud API" if meta_configured() else ("Twilio" if twilio_configured() else "simulator only")


def public_url():
    """The internet address of this app (Render sets RENDER_EXTERNAL_URL for us)."""
    return (os.environ.get("PUBLIC_URL") or os.environ.get("RENDER_EXTERNAL_URL") or "http://localhost:5000").rstrip("/")


# ---------- voice note links ----------

def clip_signature(clip_id):
    """A short secret 'signature' in the link, so nobody can guess links to other people's voice notes."""
    secret = (os.environ.get("CLIP_SECRET") or os.environ.get("GEMINI_API_KEY") or "wewed-local").encode()
    return hmac.new(secret, str(clip_id).encode(), hashlib.sha256).hexdigest()[:16]


def clip_url(clip_id):
    return f"{public_url()}/audio/{clip_id}/{clip_signature(clip_id)}"


def send_voice(planner_id, phone, audio):
    """Send a voice note. audio = (bytes, mime). We store it and give WhatsApp a public link to it."""
    clip_id = db.save_clip(audio[0], audio[1])
    return send(planner_id, phone, "", media_url=clip_url(clip_id), media_kind=f"audio:{clip_id}")


# ---------- sending ----------

def send(planner_id, phone, body, media_url=None, media_kind=None):
    """Send one WhatsApp message (text, or a photo/voice note link). Returns True if accepted."""
    kind = media_kind or ("image" if media_url else "")
    db.log_message(planner_id, phone, "out", body, kind)
    if not phone or phone.startswith(db.SIMULATED_PREFIX) or not is_configured():
        return True
    if media_url and media_url.startswith("http://localhost"):
        media_url = None  # WhatsApp can't fetch files from a laptop; media only works once deployed online
        if not body:
            return True
    if meta_configured():
        return _send_meta(phone, body, media_url, kind)
    return _send_twilio(phone, body, media_url)


def _send_meta(phone, body, media_url, kind):
    """Meta Cloud API: one POST per message. Text, image (with caption) or audio."""
    to = phone.lstrip("+")
    if media_url and kind.startswith("audio"):
        payload = {"type": "audio", "audio": {"link": media_url}}
    elif media_url:
        payload = {"type": "image", "image": {"link": media_url, "caption": body[:1000]}}
    else:
        payload = {"type": "text", "text": {"body": body[:4000], "preview_url": True}}
    payload.update({"messaging_product": "whatsapp", "to": to})
    try:
        resp = requests.post(f"{_meta_base()}/{_meta_phone_id()}/messages", json=payload,
                             headers={"Authorization": f"Bearer {_meta_token()}"}, timeout=20)
        if resp.status_code >= 300:
            print("Meta send failed:", resp.status_code, resp.text[:400])
            return False
        return True
    except requests.RequestException as e:
        print("Meta send error:", e)
        return False


def _send_twilio(phone, body, media_url):
    data = {
        "From": "whatsapp:" + os.environ.get("TWILIO_WHATSAPP_FROM", "+14155238886"),
        "To": "whatsapp:" + phone,
        "Body": body[:1500],  # Twilio limit is 1600 characters
    }
    if media_url:
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


# ---------- receiving media ----------

def download_meta_media(media_id):
    """Meta gives us a media ID; we ask Meta for its download link, then download it with our token."""
    headers = {"Authorization": f"Bearer {_meta_token()}"}
    info = requests.get(f"{_meta_base()}/{media_id}", headers=headers, timeout=20)
    info.raise_for_status()
    data = requests.get(info.json()["url"], headers=headers, timeout=30)
    data.raise_for_status()
    return data.content


def download_twilio_media(url):
    """Twilio gives us a link to the voice note / photo; download it with our Twilio login."""
    resp = requests.get(url, auth=(_sid(), _token()), timeout=30)
    resp.raise_for_status()
    return resp.content
