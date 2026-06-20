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
 *   GH_TOKEN    — a fine-grained GitHub PAT for THIS repo with
 *                 Contents: Read/Write  +  Actions: Read/Write
 *   DASH_KEY    — a long passphrase you also paste into the dashboard's Connect box
 *   ALLOW_ORIGIN (optional) — defaults to the GitHub Pages origin below
 *
 * Actions are chosen by the JSON body field "action": reply | reject | dispatch.
 */
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

  if ((req.headers["x-dash-key"] || "") !== process.env.DASH_KEY)
    return res.status(401).json({ ok: false, error: "unauthorized" });

  try {
    if (action === "reply") return res.json(await doReply(body));
    if (action === "reject") return res.json(await resolve(body.id, { status: "rejected" }));
    if (action === "dispatch") return res.json(await dispatch(body.workflow));
    return res.status(404).json({ ok: false, error: "unknown action: " + action });
  } catch (e) {
    return res.status(500).json({ ok: false, error: String(e) });
  }
}

function safeParse(s) { try { return JSON.parse(s); } catch (e) { return {}; } }

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
  if (gj.error) return { ok: false, error: gj.error.message };
  await resolve(id, { status: "sent", text });
  return { ok: true, sent: gj.id || true };
}

// --- Persist a resolution (sent/rejected) to metrics/resolutions.json ----------
// Single file this backend owns; respond.py and the dashboard read it. No race
// with the Action (which writes inbox.json/handled.json — different files).
async function resolve(id, info) {
  if (!id) return { ok: false, error: "missing id" };
  for (let attempt = 0; attempt < 3; attempt++) {
    const { sha, data } = await ghGetJson("metrics/resolutions.json");
    data[id] = { ...info, ts: new Date().toISOString() };
    const ok = await ghPutJson("metrics/resolutions.json", data, sha,
                               `resolve ${id} (${info.status}) [skip ci]`);
    if (ok) return { ok: true, id, status: info.status };
    // 409 sha conflict — loop and retry with the fresh sha
  }
  return { ok: false, error: "could not write resolutions.json" };
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

// --- GitHub contents helpers (base64 via Buffer) ------------------------------
function ghHeaders() {
  return {
    Authorization: `Bearer ${process.env.GH_TOKEN}`,
    "User-Agent": "mac-control",
    Accept: "application/vnd.github+json",
    "Content-Type": "application/json",
  };
}
async function ghGetJson(path) {
  const r = await fetch(`https://api.github.com/repos/${REPO}/contents/${path}`,
                        { headers: ghHeaders() });
  if (r.status === 404) return { sha: null, data: {} };
  const j = await r.json();
  let data = {};
  try { data = JSON.parse(Buffer.from(j.content || "", "base64").toString("utf8")); }
  catch (e) { data = {}; }
  return { sha: j.sha, data };
}
async function ghPutJson(path, obj, sha, message) {
  const content = Buffer.from(JSON.stringify(obj, null, 1), "utf8").toString("base64");
  const body = { message, content };
  if (sha) body.sha = sha;
  const r = await fetch(`https://api.github.com/repos/${REPO}/contents/${path}`,
                        { method: "PUT", headers: ghHeaders(), body: JSON.stringify(body) });
  return r.ok;
}
