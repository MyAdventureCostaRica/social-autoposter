/**
 * My Adventure Costa Rica — dashboard control backend (Cloudflare Worker, free).
 *
 * The dashboard is a PUBLIC page, so it can't safely hold your Meta token. This
 * Worker is the private half: it holds the secrets and performs the privileged
 * actions the dashboard asks for — send a comment/DM reply, reject one, or trigger
 * any GitHub Action. Every call must carry the right passphrase (x-dash-key), and
 * only your dashboard's origin may call it (CORS).
 *
 * Secrets to set in the Cloudflare dashboard (Settings → Variables, "Encrypt"):
 *   META_TOKEN  — the permanent Page token (same value as the GitHub secret)
 *   GH_TOKEN    — a fine-grained GitHub PAT for THIS repo with
 *                 Contents: Read/Write  +  Actions: Read/Write
 *   DASH_KEY    — a long passphrase you also paste into the dashboard's Connect box
 *
 * No other config needed — the repo/account IDs are constants below.
 */
const V = "v23.0";
const IG = "17841403481255550";                       // Instagram user id
const REPO = "MyAdventureCostaRica/social-autoposter";
const ALLOW_ORIGIN = "https://myadventurecostarica.github.io";
const WORKFLOWS = {                                    // friendly name -> workflow file
  post: "daily-post.yml", insights: "insights.yml", reel: "reel-post.yml",
  responder: "respond.yml", review: "review.yml",
};

function cors(extra = {}) {
  return {
    "Access-Control-Allow-Origin": ALLOW_ORIGIN,
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, x-dash-key",
    ...extra,
  };
}
function json(obj, status = 200) {
  return new Response(JSON.stringify(obj),
    { status, headers: { "Content-Type": "application/json", ...cors() } });
}

export default {
  async fetch(req, env) {
    if (req.method === "OPTIONS") return new Response(null, { headers: cors() });
    const url = new URL(req.url);
    if (url.pathname === "/ping") return json({ ok: true, service: "mac-control" });

    // Everything else requires the passphrase.
    if ((req.headers.get("x-dash-key") || "") !== env.DASH_KEY)
      return json({ ok: false, error: "unauthorized" }, 401);

    let body = {};
    try { body = await req.json(); } catch (e) {}
    try {
      if (url.pathname === "/reply") return json(await doReply(env, body));
      if (url.pathname === "/reject") return json(await resolve(env, body.id, { status: "rejected" }));
      if (url.pathname === "/dispatch") return json(await dispatch(env, body.workflow));
      return json({ ok: false, error: "not found" }, 404);
    } catch (e) {
      return json({ ok: false, error: String(e) }, 500);
    }
  },
};

// --- Send a reply (comment or DM) via the Graph API, then mark it resolved -----
async function doReply(env, { id, type, text, recipient }) {
  if (!id || !text) return { ok: false, error: "missing id or text" };
  let g;
  if (type === "dm") {
    if (!recipient) return { ok: false, error: "missing recipient id for DM" };
    g = await fetch(`https://graph.facebook.com/${V}/${IG}/messages`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ recipient: { id: recipient }, message: { text },
                             access_token: env.META_TOKEN }),
    });
  } else {                                              // comment reply
    const p = new URLSearchParams({ message: text, access_token: env.META_TOKEN });
    g = await fetch(`https://graph.facebook.com/${V}/${id}/replies`, { method: "POST", body: p });
  }
  const gj = await g.json();
  if (gj.error) return { ok: false, error: gj.error.message };
  await resolve(env, id, { status: "sent", text });
  return { ok: true, sent: gj.id || true };
}

// --- Persist a resolution (sent/rejected) to metrics/resolutions.json ----------
// Single file the Worker owns; respond.py and the dashboard read it. No race with
// the Action (which writes inbox.json/handled.json — different files).
async function resolve(env, id, info) {
  if (!id) return { ok: false, error: "missing id" };
  for (let attempt = 0; attempt < 3; attempt++) {
    const { sha, data } = await ghGetJson(env, "metrics/resolutions.json");
    data[id] = { ...info, ts: new Date().toISOString() };
    const ok = await ghPutJson(env, "metrics/resolutions.json", data, sha,
                               `resolve ${id} (${info.status}) [skip ci]`);
    if (ok) return { ok: true, id, status: info.status };
    // 409 sha conflict — loop and retry with the fresh sha
  }
  return { ok: false, error: "could not write resolutions.json" };
}

// --- Trigger any of our workflows (workflow_dispatch) --------------------------
async function dispatch(env, key) {
  const wf = WORKFLOWS[key];
  if (!wf) return { ok: false, error: "unknown workflow: " + key };
  const r = await fetch(
    `https://api.github.com/repos/${REPO}/actions/workflows/${wf}/dispatches`,
    { method: "POST", headers: ghHeaders(env), body: JSON.stringify({ ref: "main" }) });
  return { ok: r.status === 204, status: r.status, workflow: wf };
}

// --- GitHub contents helpers (unicode-safe base64) ----------------------------
function ghHeaders(env) {
  return {
    Authorization: `Bearer ${env.GH_TOKEN}`,
    "User-Agent": "mac-control",
    Accept: "application/vnd.github+json",
    "Content-Type": "application/json",
  };
}
async function ghGetJson(env, path) {
  const r = await fetch(`https://api.github.com/repos/${REPO}/contents/${path}`,
                        { headers: ghHeaders(env) });
  if (r.status === 404) return { sha: null, data: {} };
  const j = await r.json();
  let data = {};
  try { data = JSON.parse(decodeURIComponent(escape(atob((j.content || "").replace(/\n/g, ""))))); }
  catch (e) { data = {}; }
  return { sha: j.sha, data };
}
async function ghPutJson(env, path, obj, sha, message) {
  const content = btoa(unescape(encodeURIComponent(JSON.stringify(obj, null, 1))));
  const body = { message, content };
  if (sha) body.sha = sha;
  const r = await fetch(`https://api.github.com/repos/${REPO}/contents/${path}`,
                        { method: "PUT", headers: ghHeaders(env), body: JSON.stringify(body) });
  return r.ok;
}
