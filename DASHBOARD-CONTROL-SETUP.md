# Dashboard mission control — one-time setup (Vercel, free)

This turns the dashboard into a control panel: approve / edit / reject replies and
trigger any workflow (post, insights, reel, message check) with a button. The
buttons call a tiny private backend (`/api/control.js`) you host on **Vercel** —
the account you already use for myadventurecostarica.com. The dashboard stays
public; the token lives only in Vercel.

You set this up once. ~10 minutes.

## 1. Make a GitHub token for the backend
The backend only needs to trigger workflows. (The inbox and resolutions now live in
Upstash Redis — never in the repo — so the token no longer needs Contents access.)

1. GitHub → **Settings → Developer settings → Fine-grained personal access tokens → Generate new token**.
2. **Resource owner:** MyAdventureCostaRica. **Repository access:** Only select repos → `social-autoposter`.
3. **Permissions:** *Actions* → **Read and write**. (No Contents access needed.)
4. Generate, copy the token (starts `github_pat_…`). You'll paste it as `GH_TOKEN` below.

## 2. Deploy the backend on Vercel
1. Vercel → **Add New… → Project → Import** the `social-autoposter` repo.
2. **Framework Preset:** Other. **Build Command:** leave empty. **Output Directory:** leave default. Click **Deploy**.
   (Vercel auto-detects `/api/control.js` as a serverless function — nothing to build.)
3. After it deploys, note the project URL, e.g. `https://social-autoposter-xxxx.vercel.app`.

## 2b. Create the private inbox store (Upstash Redis, free)
1. Sign in at **upstash.com** → **Create Database** (Redis) → pick a region near your Vercel region.
2. On the database page, open **REST API** and copy **UPSTASH_REDIS_REST_URL** and **UPSTASH_REDIS_REST_TOKEN**.
3. Add the same two values as **GitHub Actions secrets** (Settings → Secrets and variables → Actions) so the responder can write the inbox.

## 3. Add the secrets in Vercel
Project → **Settings → Environment Variables** → add each (Production), then **Redeploy**:

| Name         | Value |
|--------------|-------|
| `META_TOKEN` | the permanent Page token (exact same value as the GitHub `META_ACCESS_TOKEN` secret) |
| `GH_TOKEN`   | the fine-grained token from step 1 (Actions: R/W only) |
| `DASH_KEY`   | a long, RANDOM passphrase (**>=32 chars**) — this is what protects the buttons |
| `UPSTASH_REDIS_REST_URL`   | from Upstash (step 2b) |
| `UPSTASH_REDIS_REST_TOKEN` | from Upstash (step 2b) |

Optional: `ALLOW_ORIGIN` — defaults to `https://myadventurecostarica.github.io`. Only change it if you serve the dashboard from a different URL.

## 4. Connect the dashboard
1. Open the dashboard, click the **⚙** (top-right of the Mission control bar).
2. Paste your **Vercel URL** and the **DASH_KEY** passphrase. **Save**, then **Test** → should say *Connected ✓*.
3. Done. Approve/edit/reject buttons and the trigger buttons are now live. The
   connection is stored only in your browser — re-enter it on a new device.

## How it works / safety
- **Approve & send** posts your (possibly edited) reply via the Graph API, then records the item as *sent* in Upstash so it never re-appears.
- **Reject** records it as *dismissed* — no reply sent, won't resurface.
- **Trigger buttons** call GitHub's `workflow_dispatch` for that workflow.
- Every action requires the `DASH_KEY` passphrase and your dashboard origin (CORS). The Meta token and GitHub token never leave Vercel — they're never in the public page.
- Recommended: put **Vercel Authentication** in front of the project for a Google-login gate; the passphrase still applies underneath.
- The inbox (customer usernames + message text) lives only in Upstash and is served only through this authenticated backend — it is never written to the public repo, public Issues, or `raw.githubusercontent`.

## Files involved
- `api/control.js` — the Vercel function (the backend).
- `respond.py` — reads/writes the inbox, handled-set, and resolutions in **Upstash** (never the repo); sent/rejected items never resurface; logs the DM sender id so DM replies can send.
- `index.html` — the Mission control bar + per-message Approve/Edit/Reject buttons.
