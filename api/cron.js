/**
 * Vercel Cron — the reliable scheduler for the WHOLE system.
 *
 * Vercel fires this every 5 minutes (see vercel.json). On each tick we look at the
 * current UTC time and trigger whichever GitHub Actions are due. Vercel's scheduler
 * is dependable, so this gives every workflow a trustworthy cadence that GitHub's own
 * cron can't promise. GitHub's built-in `schedule:` triggers stay on as harmless
 * backups — the Python scripts guard once-per-period (last_posted/last_reel/
 * last_review markers) and the responder is idempotent, so a double trigger never
 * double-acts.
 *
 * Costa Rica is UTC-6 (no DST). Times below are UTC.
 *   responder   every 5 min          (engagement: comments + DMs)
 *   daily post  15:15 UTC = 09:15 CR
 *   insights    16:20 UTC = 10:20 CR
 *   reels       Tue & Fri 18:15 UTC = 12:15 CR
 *   review      1st of month 15:20 UTC
 *
 * Security: if CRON_SECRET is set in Vercel, the platform sends it as
 * `Authorization: Bearer <CRON_SECRET>` and we verify it. Reuses GH_TOKEN.
 */
const REPO = "MyAdventureCostaRica/social-autoposter";

async function dispatch(workflow) {
  try {
    const r = await fetch(
      `https://api.github.com/repos/${REPO}/actions/workflows/${workflow}/dispatches`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${process.env.GH_TOKEN}`,
          "User-Agent": "mac-cron",
          Accept: "application/vnd.github+json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ ref: "main" }),
      }
    );
    return { workflow, ok: r.status === 204, status: r.status };
  } catch (e) {
    return { workflow, ok: false, error: String(e) };
  }
}

module.exports = async function handler(req, res) {
  const secret = process.env.CRON_SECRET;
  if (secret && req.headers.authorization !== `Bearer ${secret}`) {
    return res.status(401).json({ ok: false, error: "unauthorized" });
  }

  const now = new Date();
  const day = now.getUTCDay();      // 0 Sun .. 2 Tue .. 5 Fri
  const date = now.getUTCDate();    // 1..31
  const h = now.getUTCHours();
  const m = now.getUTCMinutes();
  const inSlot = (hr, mn) => h === hr && m >= mn && m < mn + 5;  // the 5-min window

  const due = ["respond.yml"];                                    // responder: every tick
  if (inSlot(15, 15)) due.push("daily-post.yml");                 // 09:15 CR
  if (inSlot(16, 20)) due.push("insights.yml");                   // 10:20 CR
  if ((day === 2 || day === 5) && inSlot(18, 15)) due.push("reel-post.yml"); // Tue/Fri 12:15 CR
  if (date === 1 && inSlot(15, 20)) due.push("review.yml");       // 1st of month

  const results = [];
  for (const wf of due) results.push(await dispatch(wf));
  return res.status(200).json({ ok: true, at: now.toISOString(), triggered: results });
};
