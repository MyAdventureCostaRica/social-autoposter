#!/usr/bin/env python3
"""
Meta access-token guard. STANDARD LIBRARY ONLY so every job can import it.

Oct 15 2026: Facebook invalidated the token ("the user changed their password or Facebook
has changed the session for security reasons", OAuth code 190 / subcode 460). The daily
post then failed 8 times in a row, each run spending caption calls and a commit before
hitting the dead token, while the hourly responder and the insights job swallowed the
same error and stayed GREEN ("Responder: 0 new"). Nothing could post, read comments or
DMs, and the only honest signal was eight identical ❌ pings.

    import meta_token; meta_token.require(where="daily post")

`require()` asks Graph for /me with the token BEFORE a job does any work. If the token is
dead it tells the owner once (throttled through Upstash so six slots a day plus an hourly
responder do not become 30 pings), writes the reason to the run summary and exits 1 (red
run) — nothing is captioned, rendered or committed on a token that cannot post. Network
hiccups and other errors never block a run: only a definite OAuth 190 does.

The fix is always the owner's (it is a credential): a new token in the GitHub secret
META_ACCESS_TOKEN (Actions) AND in the Vercel env META_TOKEN (dashboard replies).
"""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error

GRAPH_VERSION = "v23.0"
TOKEN_ENV = "META_ACCESS_TOKEN"
ALERT_EVERY_SECONDS = 6 * 3600          # one ping per channel per 6 h while it stays broken
ALERT_KEY = "meta_token_alert_ts"       # Upstash key (private store)

FIX_SHORT = ("🔑 The Meta access token is dead (Facebook: session invalidated after a password change "
             "or security reset). Posts, reels, comments and DMs are all stopped until you replace it: "
             "repeat SETUP.md Part 2 (Graph API Explorer → Page token), then update GitHub secret "
             "META_ACCESS_TOKEN and Vercel env META_TOKEN. The next slot posts on its own once it is in.")
FIX_STEPS = """**Replace the Meta access token** (about 5 minutes; it is a credential, so only you can do it):

1. Get a new non-expiring Page token exactly as in `SETUP.md` Part 2: developers.facebook.com/tools/explorer → app *My Adventure Costa Rica* → Generate Access Token (keep all permissions, select the Page and Instagram) → ⓘ → Open in Access Token Tool → Extend → back in the Explorer pick the **Page** in the User-or-Page dropdown → copy the token.
   Why it died: a Page token made this way is tied to your Facebook login session, and a password change or a Facebook security reset invalidates it (OAuth code 190, subcode 460). A **system-user token** from Meta Business Suite (Business settings → Users → System users → Generate token, same permissions, no expiry) survives password changes; use it if the Page and Instagram account are assigned to your Business.
2. GitHub → social-autoposter → Settings → Secrets and variables → Actions → **META_ACCESS_TOKEN** → Update.
3. Vercel → the social-autoposter project → Settings → Environment Variables → **META_TOKEN** → Edit → then Deployments → Redeploy (the dashboard's comment and DM replies use it).
4. Nothing else to do: every job checks the token first and goes back to normal on the next slot; the hourly responder resumes on its own.
"""


class MetaTokenError(RuntimeError):
    """Graph answered OAuthException code 190: the token itself is dead."""


def is_token_error(err_text):
    """True when a Graph error body says the token is invalid (code 190)."""
    t = (err_text or "")
    return '"code":190' in t.replace(" ", "") or "Error validating access token" in t


def check(token=None):
    """Returns (ok, message). ok=False ONLY for a definite OAuth 190; anything else
    (network, 5xx, rate limit) returns (True, note) so it never blocks a job."""
    token = token or os.environ.get(TOKEN_ENV)
    if not token:
        return True, "no token in env (the job reports that itself)"
    q = urllib.parse.urlencode({"fields": "id", "access_token": token})
    try:
        with urllib.request.urlopen(
                f"https://graph.facebook.com/{GRAPH_VERSION}/me?{q}", timeout=30) as r:
            data = json.loads(r.read().decode() or "{}")
            return True, f"token ok (id {data.get('id', '?')})"
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode(errors="replace")
        except Exception:
            pass
        if is_token_error(body):
            try:
                msg = json.loads(body)["error"]["message"]
            except Exception:
                msg = body[:200]
            return False, msg
        return True, f"graph HTTP {e.code} (not a token error): {body[:120]}"
    except Exception as e:
        return True, f"token check skipped: {e}"


# --- throttle through Upstash (stdlib REST), so a broken token pings once per 6 h ---
def _upstash(cmd):
    url = (os.environ.get("UPSTASH_REDIS_REST_URL") or "").rstrip("/")
    tok = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if not url or not tok:
        return None
    req = urllib.request.Request(url, data=json.dumps(cmd).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {tok}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode()).get("result")


def _should_alert():
    try:
        last = _upstash(["GET", ALERT_KEY])
        if last is not None and time.time() - float(last) < ALERT_EVERY_SECONDS:
            return False
        _upstash(["SET", ALERT_KEY, str(time.time())])
    except Exception as e:
        print("alert throttle unavailable:", e)
    return True


def alert_owner(where, reason):
    text = f"❌ {where}: {FIX_SHORT} Graph said: {reason[:160]}"
    try:
        import notify
        notify.send(text)
    except Exception as e:
        print("notify failed:", e, "\n", text)


def require(where="auto-poster"):
    """Call first thing in a job. Exits 1 with the owner alerted when the token is dead."""
    ok, msg = check()
    if ok:
        print("Meta token:", msg)
        return True
    print(f"Meta token INVALID — {msg}")
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a", encoding="utf-8") as f:
            f.write(f"### ❌ Meta access token invalid\n\n{msg}\n\n{FIX_STEPS}\n")
    if _should_alert():
        alert_owner(where, msg)
    else:
        print("owner already alerted in the last 6 h — not pinging again")
    try:                                   # the workflows' generic "❌ failed" step skips this run
        open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".token_dead"), "w").write(msg)
    except Exception:
        pass
    raise SystemExit(1)


if __name__ == "__main__":
    require(sys.argv[1] if len(sys.argv) > 1 else "auto-poster")
