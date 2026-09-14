#!/usr/bin/env python3
"""
Owner ping — WhatsApp (CallMeBot) + ntfy, each independent. STANDARD LIBRARY ONLY, so
any workflow can call it even where Pillow/cloudinary aren't installed:

    python notify.py "message"           # from a workflow step (e.g. the failure alert)
    import notify; notify.send("message") # from the Python jobs

Why it reads the CallMeBot body: CallMeBot answers HTTP 200 even when delivery fails
(expired/invalid apikey, lapsed opt-in) and puts the error in the response BODY — that
is how pings died silently for 16 days (Aug 25–Sep 10 2026) while every run was green.
So we read the body, log it loudly, and ALWAYS also try ntfy when it is configured.
Each channel lights up only when its secrets are present:
  WHATSAPP_PHONE + WHATSAPP_APIKEY     CallMeBot WhatsApp
  NTFY_TOPIC (+ NTFY_TOKEN, NTFY_BASE)  ntfy push
"""
import os, sys, urllib.parse, urllib.request

_BAD = ("error", "invalid", "not subscribed", "expired", "not allowed", "blocked")


def send(text, title="My Adventure Costa Rica auto-poster", tags=None):
    """Send `text` on every configured channel. Returns True if at least one accepted it."""
    ok = False
    phone, key = os.environ.get("WHATSAPP_PHONE"), os.environ.get("WHATSAPP_APIKEY")
    if phone and key:
        try:
            q = urllib.parse.urlencode({"phone": phone, "text": text, "apikey": key})
            body = urllib.request.urlopen(
                f"https://api.callmebot.com/whatsapp.php?{q}", timeout=20).read()
            snip = " ".join(body.decode(errors="replace").split())[:300]
            if any(w in snip.lower() for w in _BAD):
                print("WhatsApp notify PROBLEM — CallMeBot said:", snip)
            else:
                print("WhatsApp notify OK — CallMeBot said:", snip[:120]); ok = True
        except Exception as e:
            print("WhatsApp notify failed:", e)
    topic = os.environ.get("NTFY_TOPIC")
    if topic:
        try:
            base = (os.environ.get("NTFY_BASE") or "https://ntfy.sh").rstrip("/")
            if tags is None:                      # failure alerts get the siren, the rest a bell
                tags = "rotating_light" if text.lstrip().startswith(("❌", "⚠️")) else "bell"
            req = urllib.request.Request(
                f"{base}/{topic}", data=text.encode("utf-8"),
                # ASCII-only headers (HTTP headers are latin-1); emoji only via Tags names.
                headers={"Title": title, "Tags": tags,
                         "Priority": "high" if tags == "rotating_light" else "default"})
            tok = os.environ.get("NTFY_TOKEN")
            if tok:
                req.add_header("Authorization", f"Bearer {tok}")
            urllib.request.urlopen(req, timeout=20).read()
            print("ntfy notify OK"); ok = True
        except Exception as e:
            print("ntfy notify failed:", e)
    if not (phone and key) and not topic:
        print("notify: no channel configured (WHATSAPP_* / NTFY_TOPIC). Message was:", text[:200])
    return ok


if __name__ == "__main__":
    send(" ".join(sys.argv[1:]).strip() or "(empty notification)")
