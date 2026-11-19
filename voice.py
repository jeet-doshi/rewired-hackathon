"""
voice.py - talking and listening in Indian languages, using Sarvam AI (an Indian speech AI company).

  transcribe(audio)  -> voice note  -> text + which language it was   (Sarvam "Saarika" speech-to-text)
  speak(text, lang)  -> text        -> a voice note in that language  (Sarvam "Bulbul" text-to-speech)

Why Sarvam: it is built for Indian languages and Indian accents, including mixed Hindi-English ("Hinglish").
Gemini (ai.py) then reads the TEXT and works out who should do what.
"""
import os
import base64
import requests

STT_URL = "https://api.sarvam.ai/speech-to-text"
TTS_URL = "https://api.sarvam.ai/text-to-speech"

# Languages people can choose when they join (Sarvam language codes)
LANGUAGES = [
    ("hi-IN", "Hindi"), ("en-IN", "English"), ("kn-IN", "Kannada"), ("ta-IN", "Tamil"), ("te-IN", "Telugu"),
    ("mr-IN", "Marathi"), ("gu-IN", "Gujarati"), ("bn-IN", "Bengali"), ("ml-IN", "Malayalam"), ("pa-IN", "Punjabi"),
]
LANGUAGE_NAMES = dict(LANGUAGES)


def _key():
    key = os.environ.get("SARVAM_API_KEY", "").strip()
    return "" if key.lower() in ("none", "-", "na") else key  # placeholder means "not set yet"


def is_configured():
    return bool(_key())


def transcribe(audio_bytes, mime):
    """Voice note -> (transcript, language_code). language_code is like 'hi-IN'."""
    mime = (mime or "audio/ogg").split(";")[0]
    ext = {"audio/ogg": "ogg", "audio/opus": "opus", "audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/wav": "wav",
           "audio/x-wav": "wav", "audio/webm": "webm", "audio/mp4": "m4a", "audio/aac": "aac", "audio/amr": "amr"}.get(mime, "ogg")
    resp = requests.post(
        STT_URL,
        headers={"api-subscription-key": _key()},
        files={"file": (f"voice.{ext}", audio_bytes, mime)},
        data={"model": os.environ.get("SARVAM_STT_MODEL", "saarika:v2.5"), "language_code": "unknown"},  # unknown = auto-detect
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Sarvam speech-to-text error {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    return (data.get("transcript") or "").strip(), data.get("language_code") or "unknown"


def speak(text, language_code):
    """Text -> (audio_bytes, mime) spoken in that language. Returns None if it fails (we then just send text)."""
    if not is_configured() or not text:
        return None
    language_code = language_code if language_code in LANGUAGE_NAMES else "en-IN"
    body = {
        "text": text[:1500],
        "target_language_code": language_code,
        "model": os.environ.get("SARVAM_TTS_MODEL", "bulbul:v3"),
        "output_audio_codec": "mp3",  # WhatsApp plays mp3 voice messages; it does not accept wav
    }
    if os.environ.get("SARVAM_SPEAKER"):  # optional: pick a specific voice, otherwise Sarvam's default
        body["speaker"] = os.environ["SARVAM_SPEAKER"]
    try:
        resp = requests.post(TTS_URL, headers={"api-subscription-key": _key()}, json=body, timeout=60)
        if resp.status_code != 200:
            print("Sarvam text-to-speech error:", resp.status_code, resp.text[:300])
            return None
        audio = base64.b64decode(resp.json()["audios"][0])
        mime = "audio/wav" if audio[:4] == b"RIFF" else "audio/mpeg"  # check what we actually got back
        return audio, mime
    except Exception as e:
        print("Sarvam text-to-speech error:", e)
        return None
