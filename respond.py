#!/usr/bin/env python3
"""
Engagement responder — the "stop just broadcasting, engage back" loop.

Runs in GitHub Actions (the cloud; no app open). Each run it:
  1. reads NEW comments on recent Instagram posts (instagram_manage_comments),
     and NEW direct messages where the token permits it (instagram_manage_messages);
  2. drafts a reply in the My Adventure Costa Rica voice with GitHub Models
     (free, built-in) — mirroring the writer's language, Spanish always in usted;
  3. classifies each one: a SAFE simple appreciation, or something that needs you
     (a question, a booking signal, a complaint);
  4. writes metrics/inbox.json (the dashboard Inbox reads this) and opens/updates a
     GitHub Issue that tags you, so the sensitive ones reach you with a draft ready;
  5. optionally AUTO-SENDS replies to SAFE comments only — but ONLY if you set
     "auto_reply_comments": true in config.json. Default is OFF: it drafts, you send.

Bulletproof + idempotent: every id we've already handled is recorded in
metrics/handled.json, so re-runs never double-reply and a flaky cron is harmless.

Never auto-sends DMs (too personal, and Meta's 24h window makes timing tricky) —
DMs are always surfaced for you. Secrets: META_ACCESS_TOKEN (you add it),
GITHUB_TOKEN (built-in, powers drafting + the issue).
"""
import json, os, time, datetime, urllib.parse, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "config.json")))
MET = os.path.join(HERE, "metrics")
os.makedirs(MET, exist_ok=True)
HANDLED = os.path.join(MET, "handled.json")
INBOX = os.path.join(MET, "inbox.json")
RESOL = os.path.join(MET, "resolutions.json")   # written by the dashboard backend

TOKEN = os.environ.get("META_ACCESS_TOKEN")
GH_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = os.environ.get("GITHUB_REPOSITORY", "")
V = CFG.get("graph_version", "v23.0")
IG = CFG["ig_user_id"]
MODEL = CFG.get("caption_model", "openai/gpt-4o")
MODELS_URL = "https://models.github.ai/inference/chat/completions"

# How far back to scan, and how many posts. Comments on old posts are rare; this
# keeps every run fast and within the recent window that actually gets activity.
RECENT_MEDIA = int(CFG.get("respond_recent_media", 25))
AUTO_REPLY = bool(CFG.get("auto_reply_comments", False))   # default OFF — drafts only

# --- Notification fan-out (comments/DMs are PRIORITY — reach the human ASAP) ---
# Every channel is optional: it fires only if its secret is set, and each is wrapped
# so one failing never blocks the others. Fastest+most reliable first.
DASH = CFG.get("dashboard_url", "https://myadventurecostarica.github.io/social-autoposter/")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")                   # phone push (ntfy.sh, free, instant)
WA_PHONE = os.environ.get("WHATSAPP_PHONE")                 # WhatsApp via CallMeBot (free)
WA_KEY = os.environ.get("WHATSAPP_APIKEY")
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")             # Telegram (free, instant)
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID")
SLACK_WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL")         # Slack/Discord incoming webhook

REPLY_SYSTEM = (
    "You write public replies and direct-message replies for My Adventure Costa Rica, "
    "a LUXURY ENDURANCE adventure travel brand operating FROM Costa Rica for an "
    "international audience (trail running, cycling, water sports, multi-sport, bespoke "
    "journeys, school programs). Voice: warm, gracious, editorial — the register of "
    "Travel + Leisure — unhurried and human, never salesy, never hype, no exclamation "
    "marks, no emoji unless the writer used one first. LANGUAGE: write the reply in the "
    "same language the person CLEARLY wrote in; if the comment has no clear language — "
    "an emoji, a name, punctuation, '🔥', 'nice' — or you are at all unsure, DEFAULT TO "
    "ENGLISH (the brand speaks to an international audience). Only write Spanish when the "
    "person plainly wrote Spanish, and then address them with the "
    "formal USTED, never tú. Keep it to ONE short sentence. Thank genuinely; if they "
    "asked something you can answer briefly and truthfully, do; if it needs real detail "
    "(dates, prices, custom planning) invite them warmly to send a message or note that "
    "the team will follow up — never invent specifics. Always write the full name "
    "'My Adventure Costa Rica', never an abbreviation."
)


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return {"error": json.loads(e.read().decode()).get("error", {})}
        except Exception:
            return {"error": {"message": f"HTTP {e.code}"}}
    except Exception as e:
        return {"error": {"message": str(e)}}


def _post(path, params):
    data = urllib.parse.urlencode(params).encode()
    try:
        with urllib.request.urlopen(
                urllib.request.Request(f"https://graph.facebook.com/{V}/{path}", data=data),
                timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return {"error": json.loads(e.read().decode()).get("error", {})}
        except Exception:
            return {"error": {"message": f"HTTP {e.code}"}}
    except Exception as e:
        return {"error": {"message": str(e)}}


def load(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default


def draft_reply(text, kind):
    """Ask GitHub Models for a classification + a drafted reply. Resilient: if the
    model or token is unavailable, we still surface the item with an empty draft."""
    if not GH_TOKEN:
        return {"reply": "", "intent": "other", "sentiment": "neutral",
                "safe": False, "note": "no GITHUB_TOKEN — draft unavailable"}
    user = (
        f"A {kind} on our Instagram reads:\n\n\"{text}\"\n\n"
        "Return STRICT JSON only (no prose, no code fences) with keys:\n"
        '  "language": the language the person wrote in (e.g. "English","Spanish"),\n'
        '  "sentiment": one of "positive","neutral","negative",\n'
        '  "intent": one of "appreciation","question","booking","complaint","spam","other",\n'
        '  "safe": true ONLY if this is simple appreciation with no question and nothing '
        "for a human to decide (so an automatic thank-you is clearly fine), else false,\n"
        '  "reply": the one-sentence reply in the brand voice, in the writer\'s language.'
    )
    payload = {"model": MODEL, "temperature": 0.5,
               "messages": [{"role": "system", "content": REPLY_SYSTEM},
                            {"role": "user", "content": user}]}
    req = urllib.request.Request(
        MODELS_URL, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {GH_TOKEN}", "Content-Type": "application/json",
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            raw = json.loads(r.read().decode())["choices"][0]["message"]["content"].strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        d = json.loads(raw)
        d["safe"] = bool(d.get("safe")) and d.get("intent") == "appreciation" \
            and d.get("sentiment") in ("positive", "neutral") and "?" not in text
        d["reply"] = (d.get("reply") or "").strip()
        return d
    except Exception as e:
        return {"reply": "", "intent": "other", "sentiment": "neutral",
                "safe": False, "note": f"draft error: {e}"}


def me_username():
    r = _get(f"https://graph.facebook.com/{V}/{IG}?fields=username&access_token={TOKEN}")
    return (r or {}).get("username", "")


def scan_comments(handled, items):
    """Pull comments on recent posts; draft a reply for each new one."""
    mine = me_username()
    media = _get(f"https://graph.facebook.com/{V}/{IG}/media?"
                 + urllib.parse.urlencode({"fields": "id,permalink,caption,timestamp",
                                           "limit": str(RECENT_MEDIA), "access_token": TOKEN}))
    if media.get("error"):
        print("comments: media list error:", media["error"].get("message")); return
    for m in media.get("data", []):
        mid = m.get("id")
        cs = _get(f"https://graph.facebook.com/{V}/{mid}/comments?"
                  + urllib.parse.urlencode({"fields": "id,text,username,timestamp",
                                            "limit": "50", "access_token": TOKEN}))
        if cs.get("error"):
            continue
        for c in cs.get("data", []):
            cid = c.get("id")
            if not cid or cid in handled:
                continue
            if mine and c.get("username") == mine:        # don't reply to ourselves
                handled[cid] = "self"; continue
            text = (c.get("text") or "").strip()
            if not text:
                handled[cid] = "empty"; continue
            d = draft_reply(text, "comment")
            item = {"type": "comment", "id": cid, "media_id": mid,
                    "permalink": m.get("permalink"), "user": c.get("username"),
                    "text": text, "ts": c.get("timestamp"),
                    "intent": d.get("intent"), "sentiment": d.get("sentiment"),
                    "language": d.get("language"), "reply": d.get("reply"),
                    "note": d.get("note", ""), "status": "pending"}
            if AUTO_REPLY and d.get("safe") and d.get("reply"):
                res = _post(f"{cid}/replies", {"message": d["reply"], "access_token": TOKEN})
                if res.get("error"):
                    item["note"] = "auto-send failed: " + res["error"].get("message", "")
                else:
                    item["status"] = "auto-sent"; handled[cid] = "auto-sent"
            if item["status"] == "pending":
                handled[cid] = "surfaced"
            items.append(item)
            time.sleep(0.4)


def scan_dms(handled, items):
    """Surface NEW direct messages (never auto-send). Gracefully no-ops if the token
    doesn't carry instagram_manage_messages yet."""
    convos = _get(f"https://graph.facebook.com/{V}/{IG}/conversations?"
                  + urllib.parse.urlencode({"platform": "instagram",
                                            "fields": "id,updated_time,messages.limit(5)"
                                            "{id,from,message,created_time}",
                                            "limit": "25", "access_token": TOKEN}))
    if convos.get("error"):
        print("dms: skipped (", convos["error"].get("message"), ")"); return
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
    for conv in convos.get("data", []):
        msgs = (conv.get("messages") or {}).get("data", [])
        for msg in msgs:                                   # newest first
            frm = (msg.get("from") or {})
            if str(frm.get("id")) == str(IG):              # our own message — stop
                break
            mid = msg.get("id")
            if not mid or mid in handled:
                continue
            try:
                t = datetime.datetime.fromisoformat(
                    (msg.get("created_time") or "").replace("Z", "+00:00"))
                if t < cutoff:                              # outside the 24h reply window
                    handled[mid] = "stale"; continue
            except Exception:
                pass
            text = (msg.get("message") or "").strip()
            if not text:
                handled[mid] = "empty"; continue
            d = draft_reply(text, "direct message")
            items.append({"type": "dm", "id": mid, "convo_id": conv.get("id"),
                          "recipient": frm.get("id"),   # IGSID — needed to send a DM reply
                          "user": frm.get("username") or frm.get("name"),
                          "text": text, "ts": msg.get("created_time"),
                          "intent": d.get("intent"), "sentiment": d.get("sentiment"),
                          "language": d.get("language"), "reply": d.get("reply"),
                          "note": d.get("note", ""), "status": "pending"})
            handled[mid] = "surfaced"
            time.sleep(0.4)
            break                                          # only the latest inbound per convo


def _fire(req, label):
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"notify {label}: ok ({getattr(r, 'status', 200)})")
    except Exception as e:
        print(f"notify {label}: failed ({e})")


def notify(pending):
    """Fan an alert out to every configured channel at once. Each is optional and
    isolated — comments/DMs are priority, so we ping all of them in parallel intent."""
    if not pending:
        return
    n = len(pending)
    first = pending[0]
    who = first.get("user") or "someone"
    kind = "DM" if first.get("type") == "dm" else "comment"
    snippet = (first.get("text") or "").strip()[:90]
    title = f"🔔 {n} {'reply' if n == 1 else 'replies'} need you"
    body = (f"{kind} from @{who}: {snippet}"
            + (f"  (+{n-1} more)" if n > 1 else "")
            + f"\nReply: {DASH}")

    # 1) Phone push — ntfy.sh (free, no account, near-instant, most reliable).
    # HTTP headers must be latin-1, so the Title header can't hold the emoji — strip it
    # and let ntfy draw the bell via the Tags header instead. The body (UTF-8) keeps any
    # emoji fine.
    if NTFY_TOPIC:
        ascii_title = (title.encode("ascii", "ignore").decode().strip()
                       or "New replies need you")
        _fire(urllib.request.Request(
            f"https://ntfy.sh/{NTFY_TOPIC}", data=body.encode("utf-8"),
            headers={"Title": ascii_title, "Priority": "high",
                     "Tags": "bell", "Click": DASH}), "ntfy")
    # 2) WhatsApp — CallMeBot (free; one-time opt-in gives you an apikey)
    if WA_PHONE and WA_KEY:
        q = urllib.parse.urlencode({"phone": WA_PHONE,
                                    "text": f"{title}\n{body}", "apikey": WA_KEY})
        _fire(urllib.request.Request(
            f"https://api.callmebot.com/whatsapp.php?{q}"), "whatsapp")
    # 3) Telegram — instant, very reliable (bot token + chat id)
    if TG_TOKEN and TG_CHAT:
        q = urllib.parse.urlencode({"chat_id": TG_CHAT, "text": f"{title}\n{body}",
                                    "disable_web_page_preview": "true"})
        _fire(urllib.request.Request(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage?{q}"), "telegram")
    # 4) Slack / Discord — incoming webhook (paste a Discord webhook + "/slack")
    if SLACK_WEBHOOK:
        _fire(urllib.request.Request(
            SLACK_WEBHOOK, data=json.dumps({"text": f"*{title}*\n{body}"}).encode(),
            headers={"Content-Type": "application/json"}), "slack")
    # 5) Email is covered by the GitHub Issue below (it emails repo watchers).


def open_issue(pending):
    if not (GH_TOKEN and REPO and pending):
        return
    owner = REPO.split("/")[0]
    lines = [f"@{owner} — {len(pending)} message(s) waiting for you. Drafts are ready; "
             "approve by replying on Instagram (or in Claude). The full list is on your "
             "dashboard Inbox.\n"]
    for p in pending:
        where = p.get("permalink") or "(direct message)"
        lines.append(f"- **{p.get('user','?')}** · {p.get('intent','')} · {p.get('type')}\n"
                     f"  > {p.get('text','')[:200]}\n"
                     f"  _Draft:_ {p.get('reply') or '(none — needs your words)'}\n"
                     f"  {where}")
    body = "\n".join(lines)[:60000]
    title = f"Engagement — {len(pending)} to reply · {datetime.date.today().isoformat()}"
    data = json.dumps({"title": title, "body": body}).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/issues", data=data,
        headers={"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json", "User-Agent": "autoposter-respond"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print("Opened issue:", json.loads(r.read().decode()).get("html_url"))
    except Exception as e:
        print("Issue skipped:", e)


def main():
    if not TOKEN:
        raise SystemExit("Missing META_ACCESS_TOKEN.")
    # On-demand test: fire a sample alert through every configured channel so you can
    # confirm ntfy/WhatsApp/etc. work without waiting for a real comment. Triggered by
    # running the workflow with the "Send a test alert" box checked.
    if os.environ.get("TEST_NOTIFY"):
        notify([{"type": "comment", "user": "test",
                 "text": "Test alert from your responder — if you got this, alerts work.",
                 "intent": "test", "permalink": DASH}])
        print("Sent a test notification to all configured channels.")
        return
    handled = load(HANDLED, {})
    if not isinstance(handled, dict):
        handled = {}
    # Anything you've already sent or rejected from the dashboard is recorded in
    # resolutions.json — seed it into handled so it never re-surfaces or gets
    # re-drafted.
    resolved = load(RESOL, {})
    if not isinstance(resolved, dict):
        resolved = {}
    for rid, info in resolved.items():
        handled.setdefault(rid, (info or {}).get("status", "resolved"))
    items = []
    scan_comments(handled, items)
    scan_dms(handled, items)

    # Inbox = everything still needing you (auto-sent items drop off). Keep newest first
    # and cap so the dashboard stays light. Carry forward yesterday's still-pending ones.
    prev = [x for x in load(INBOX, []) if x.get("status") == "pending"]
    prev_ids = {x["id"] for x in items}
    merged = items + [x for x in prev if x["id"] not in prev_ids]
    pending = [x for x in merged
               if x.get("status") == "pending" and x["id"] not in resolved]
    pending.sort(key=lambda x: x.get("ts") or "", reverse=True)
    json.dump(pending[:100], open(INBOX, "w"), ensure_ascii=False, indent=1)
    json.dump(handled, open(HANDLED, "w"), indent=1)

    new_pending = [x for x in items if x.get("status") == "pending"]
    if new_pending:
        notify(new_pending)        # fan out to every fast channel first
        open_issue(new_pending)    # + GitHub Issue (the email channel, audit trail)
    sent = sum(1 for x in items if x.get("status") == "auto-sent")
    print(f"Responder: {len(items)} new ({sent} auto-sent, {len(new_pending)} for you); "
          f"{len(pending)} pending in inbox.")


if __name__ == "__main__":
    main()
