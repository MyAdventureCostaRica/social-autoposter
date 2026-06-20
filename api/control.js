/**
 * My Adventure Costa Rica — dashboard control backend (Vercel serverless function).
 *
 * The dashboard is a PUBLIC page, so it can't safely hold your Meta token. This
 * function is the private half: it holds the secrets and performs the privileged
 * actions the dashboard asks for — send a comment/DM reply, reject one, or trigger
 * any GitHub Action. Every call must carry your passphrase (x-dash-key header).
 *
 * Deploy: import this repo as a Vercel project (or add /api to your existing one).
 * It goes live at  https://<project>.vercel.app/api/control
 *
 * Set these in Vercel → Project → Settings → Environment Variables:
 *   META_TOKEN  — the permanent Page token (same value as the GitHub secret)
 *   GH_TOKEN    — a fine-grained GitHub PAT for THIS repo with Actions: Read/Write
 *                 (Contents no longer needed — inbox/resolutions live in Upstash)
 *   DASH_KEY    — a long, RANDOM passphrase (>=32 chars); also pasted into the dashboard
 *   UPSTASH_REDIS_REST_URL   — Upstash Redis REST endpoint (private inbox store)
 *   UPSTASH_REDIS_REST_TOKEN — Upstash Redis REST token
 *   ALLOW_ORIGIN (optional) — defaults to the GitHub Pages origin below
 *
 * Actions are chosen by the JSON body field "action": reply | reject | dispatch.
 */
const crypto = require("crypto");
const V = "v23.0";
const IG = "17841403481255550";                        // Instagram user id
const REPO = "MyAdventureCostaRica/social-autoposter";
const DEFAULT_ORIGIN = "https://myadventurecostarica.github.io";
const WORKFLOWS = {                                     // friendly name -> workflow file
  post: "daily-post.yml", insights: "insights.yml", reel: "reel-post.yml",
  responder: "respond.yml", review: "review.yml",
};

function setCors(res) {
  res.setHeader("Access-Control-Allow-Origin", process.env.ALLOW_ORIGIN || DEFAULT_ORIGIN);
  res.setHeader("Access-Control-Allow-Methods", "POST, GET, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, x-dash-key");
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === "OPTIONS") return res.status(204).end();

  const body = typeof req.body === "string" ? safeParse(req.body) : (req.body || {});
  const action = (req.query && req.query.action) || body.action || "";
  if (action === "ping") return res.json({ ok: true, service: "mac-control" });

  // Throttle every caller (per IP) so DASH_KEY can't be brute-forced.
  if (await rateLimited(req))
    return res.status(429).json({ ok: false, error: "rate limited" });

  // Constant-time passphrase check; fail closed if DASH_KEY is unset.
  if (!process.env.DASH_KEY || !safeEq(req.headers["x-dash-key"] || "", process.env.DASH_KEY))
    return res.status(401).json({ ok: false, error: "unauthorized" });

  try {
    if (action === "inbox") return res.json(await getInbox());
    if (action === "reply") return res.json(await doReply(body));
    if (action === "reject") return res.json(await resolve(body.id, { status: "rejected" }));
    if (action === "dispatch") return res.json(await dispatch(body.workflow));
    return res.status(404).json({ ok: false, error: "unknown action" });
  } catch (e) {
    console.error("control error:", e);                  // detail stays server-side
    return res.status(500).json({ ok: false, error: "internal error" });
  }
}

function safeParse(s) { try { return JSON.parse(s); } catch (e) { return {}; } }

// --- Auth + abuse helpers -----------------------------------------------------
function safeEq(a, b) {
  const ab = Buffer.from(String(a)), bb = Buffer.from(String(b));
  if (ab.length !== bb.length) return false;
  return crypto.timingSafeEqual(ab, bb);
}
async function rateLimited(req) {                          // ~60 requests / minute / IP
  try {
    const ip = String(req.headers["x-forwarded-for"] || "").split(",")[0].trim() || "unknown";
    const j = await redis(["INCR", `rl:${ip}`]);
    const n = Number(j && j.result);
    if (n === 1) await redis(["EXPIRE", `rl:${ip}`, "60"]);
    return n > 60;
  } catch (e) { return false; }                           // never lock the owner out on limiter error
}

// --- Upstash Redis (private store for inbox + resolutions) ---------------------
async function redis(cmd) {
  const r = await fetch(process.env.UPSTASH_REDIS_REST_URL, {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.UPSTASH_REDIS_REST_TOKEN}`,
               "Content-Type": "application/json" },
    body: JSON.stringify(cmd),
  });
  return r.json();
}
async function rget(key, dflt) {
  try { const j = await redis(["GET", key]); return j && j.result ? JSON.parse(j.result) : dflt; }
  catch (e) { console.error("redis get", key, e); return dflt; }
}
async function rset(key, obj) {
  try { const j = await redis(["SET", key, JSON.stringify(obj)]); return !!(j && j.result); }
  catch (e) { console.error("redis set", key, e); return false; }
}
async function getInbox() {
  const [inbox, resolutions] = await Promise.all([rget("inbox", []), rget("resolutions", {})]);
  return { ok: true, inbox, resolutions };
}

// --- Send a reply (comment or DM) via the Graph API, then mark it resolved -----
async function doReply({ id, type, text, recipient }) {
  if (!id || !text) return { ok: false, error: "missing id or text" };
  let g;
  if (type === "dm") {
    if (!recipient) return { ok: false, error: "missing recipient id for DM" };
    g = await fetch(`https://graph.facebook.com/${V}/${IG}/messages`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ recipient: { id: recipient }, message: { text },
                             access_token: process.env.META_TOKEN }),
    });
  } else {                                              // comment reply
    const p = new URLSearchParams({ message: text, access_token: process.env.META_TOKEN });
    g = await fetch(`https://graph.facebook.com/${V}/${id}/replies`, { method: "POST", body: p });
  }
  const gj = await g.json();
  if (gj.error) { console.error("graph error:", gj.error); return { ok: false, error: "Meta rejected the reply" }; }
  await resolve(id, { status: "sent", text });
  return { ok: true, sent: gj.id || true };
}

// --- Persist a resolution (sent/rejected) to Upstash (PRIVATE) -----------------
async function resolve(id, info) {
  if (!id) return { ok: false, error: "missing id" };
  const data = await rget("resolutions", {});
  data[id] = { ...info, ts: new Date().toISOString() };
  const ok = await rset("resolutions", data);
  return ok ? { ok: true, id, status: info.status } : { ok: false, error: "could not persist resolution" };
}

// --- Trigger any of our workflows (workflow_dispatch) --------------------------
async function dispatch(key) {
  const wf = WORKFLOWS[key];
  if (!wf) return { ok: false, error: "unknown workflow: " + key };
  const r = await fetch(
    `https://api.github.com/repos/${REPO}/actions/workflows/${wf}/dispatches`,
    { method: "POST", headers: ghHeaders(), body: JSON.stringify({ ref: "main" }) });
  return { ok: r.status === 204, status: r.status, workflow: wf };
}

// --- GitHub headers (used only to trigger workflow_dispatch) ------------------
function ghHeaders() {
  return {
    Authorization: `Bearer ${process.env.GH_TOKEN}`,
    "User-Agent": "mac-control",
    Accept: "application/vnd.github+json",
    "Content-Type": "application/json",
  };
}
// (GitHub Contents helpers removed — inbox/resolutions now live in Upstash, not git.)
