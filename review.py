#!/usr/bin/env python3
"""
Monthly system review — runs in GitHub Actions (the cloud; no app needed).

Computes the performance picture DETERMINISTICALLY in Python (so the numbers are
trustworthy), then asks GitHub Models to turn it into a readable readout +
proposed improvements, following SYSTEM-REVIEW.md. Writes REVIEW-LATEST.md and
metrics/review-latest.json (the dashboard reads this), and opens a GitHub Issue
that tags the owner so they get an email/notification. Applying any change stays
a human decision — this only proposes.
"""
import json, os, glob, re, datetime, collections, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MET = os.path.join(HERE, "metrics")
INS = os.path.join(MET, "insights.json")
POSTS = os.path.join(MET, "posts.json")
SRC = os.path.join(HERE, "source-photos")
TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = os.environ.get("GITHUB_REPOSITORY", "")          # owner/repo
MODEL = "openai/gpt-4o"
MODELS_URL = "https://models.github.ai/inference/chat/completions"
REACH_FLOOR = 50
HALFLIFE = 90              # ~2x weight each 3 months — favor current trends (June 2026 review)
SAVES_DEAD = 0.05          # mirror of autopost.py; learner_thresholds() re-reads the live values
MIN_AGE_DAYS = 2           # a post published hours before the review has noise-level numbers
                           # and max recency weight — let insights mature before it can rank
# (the caption word-frequency STOP list is gone with the "themes" counter —
# pillar_leaderboard + top_posts captions are the theme evidence now)


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return []


def learner_thresholds():
    """The learner's ACTUAL live values, read from autopost.py, so the narrative
    model is told what the knobs are set to. (July 2026 review proposed 'lowering'
    REACH_FLOOR from 100 and 'extending' HALFLIFE from 30 — both invented, because
    the prompt named the knobs without their current values.)"""
    vals = {"REACH_FLOOR": REACH_FLOOR, "HALFLIFE_DAYS": HALFLIFE, "SAVES_DEAD": SAVES_DEAD}
    try:
        src = open(os.path.join(HERE, "autopost.py")).read()
        for k in vals:
            m = re.search(rf"^{k}\s*=\s*([0-9.]+)", src, re.M)
            if m:
                v = float(m.group(1))
                vals[k] = int(v) if v == int(v) else v
    except Exception:
        pass
    return vals


def analyze():
    rows = load(INS)
    posts = {p.get("id"): p for p in load(POSTS) if p.get("id")}
    today = datetime.date.today()

    def age(r):
        try:
            return (today - datetime.date.fromisoformat(r["date"])).days
        except Exception:
            return None

    withreach = [r for r in rows if isinstance(r.get("reach"), int)]
    elig = [r for r in withreach if r["reach"] >= REACH_FLOOR
            and isinstance(r.get("eng_rate"), (int, float))
            and age(r) is not None and age(r) >= MIN_AGE_DAYS]

    def wt(r):
        return 0.5 ** (age(r) / HALFLIFE)

    tot = lambda k: sum((r.get(k) or 0) for r in elig)
    inter = max(1, tot("interactions"))
    # TRUE percentages (7.2 means 7.2%) — as fractions, gpt-4o read 0.072 as "0.072%"
    mix = {k: round(100.0 * tot(k) / inter, 1) for k in ("saved", "shares", "likes", "comments")}

    byf = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for r in elig:
        b = byf[r.get("format") or "single"]
        b[0] += wt(r) * r["eng_rate"]; b[1] += wt(r); b[2] += 1
    fmt = sorted(([f, round(s / n, 4), c] for f, (s, n, c) in byf.items() if n),
                 key=lambda x: -x[1])

    ranked = sorted(elig, key=lambda r: -(wt(r) * r["eng_rate"]))
    top = [{"date": r["date"], "format": r.get("format"),
            "pillar": posts.get(r["id"], {}).get("pillar"),
            "reach": r.get("reach"), "interactions": r.get("interactions"),
            "shares": r.get("shares"), "saved": r.get("saved"),
            "eng_rate": r.get("eng_rate"),
            "caption": (posts.get(r["id"], {}).get("caption") or "")[:120]}
           for r in ranked[:8]]

    # Pillar + category leaderboards (logged at publish since June 20 2026) — the
    # strategic axes. Replace the old caption word-frequency "themes", which
    # surfaced editorial filler ("through", "winds") as if it were a theme.
    # Pre-pillar-era posts are counted separately, not shown as a pseudo-pillar.
    byp = collections.defaultdict(lambda: [0.0, 0.0, 0])
    byc = collections.defaultdict(lambda: [0.0, 0.0, 0])
    unlabeled = 0
    for r in elig:
        meta = posts.get(r["id"], {})
        pil = (meta.get("pillar") or "").upper()
        cat = (meta.get("category") or "").upper()
        if pil:
            b = byp[pil]; b[0] += wt(r) * r["eng_rate"]; b[1] += wt(r); b[2] += 1
        else:
            unlabeled += 1
        if cat:
            b = byc[cat]; b[0] += wt(r) * r["eng_rate"]; b[1] += wt(r); b[2] += 1
    rank = lambda d: sorted(([k, round(s / n, 4), c] for k, (s, n, c) in d.items() if n),
                            key=lambda x: -x[1])
    pillars, cats = rank(byp), rank(byc)

    dates = sorted(r["date"] for r in rows if r.get("date"))
    queue = len([f for f in glob.glob(os.path.join(SRC, "*"))
                 if f.lower().endswith((".jpg", ".jpeg", ".png", ".heic", ".heif"))])
    return {
        "generated": today.isoformat(),
        "current_learner_thresholds": learner_thresholds(),
        "min_age_days": MIN_AGE_DAYS,
        "total_posts": len(rows), "with_insights": len(withreach), "eligible": len(elig),
        "eligible_recent_12mo": sum(1 for r in elig if age(r) <= 365),
        "date_range": [dates[0] if dates else None, dates[-1] if dates else None],
        "interaction_mix_pct": mix,
        "format_leaderboard": [{"format": f, "avg_eng_rate": rt, "n": c} for f, rt, c in fmt],
        "pillar_leaderboard": [{"pillar": p, "avg_eng_rate": rt, "n": c} for p, rt, c in pillars],
        "category_leaderboard": [{"category": k, "avg_eng_rate": rt, "n": c} for k, rt, c in cats],
        "unlabeled_history_n": unlabeled,
        "top_posts": top,
        "photo_queue": queue,
        # only recent failures are actionable — the ~679 pre-2020 media that
        # Instagram will never report on are expected, not a system failure
        "errored_posts_90d": sum(1 for r in rows if r.get("error")
                                 and age(r) is not None and age(r) <= 90),
    }


def ask_models(stats):
    if not TOKEN:
        return None
    try:
        method = open(os.path.join(HERE, "SYSTEM-REVIEW.md")).read()
    except Exception:
        method = "Review the auto-poster's performance and propose improvements."
    user = ("Computed performance data (TRUST these numbers; never invent others):\n\n"
            + json.dumps(stats, indent=1, ensure_ascii=False)
            + "\n\nHow to read it:\n"
              "- current_learner_thresholds are the ACTUAL live values of REACH_FLOOR, "
              "HALFLIFE_DAYS and SAVES_DEAD. Propose a threshold change ONLY as a delta "
              "from these values; if your idea equals the current value, drop it. Never "
              "state a current value that isn't in this data.\n"
              "- interaction_mix_pct values are already percentages (7.2 means 7.2%).\n"
              "- Any theme/topic observation must quote evidence from the top_posts "
              "captions; do not infer themes from single words.\n"
              "- avg_eng_rate rows with n<3 are anecdotes — never build a proposal or "
              "experiment on them alone.\n"
              "- unlabeled_history_n counts eligible posts from before pillar labeling "
              "existed (pre-June-2026 history). They shape the format numbers but are "
              "absent from the pillar/category leaderboards — not a cohort to optimize.\n"
              "\nWrite the review as MARKDOWN, three sections:\n"
              "1. **Readout** — 4-6 lines on what the data says BY TODAY'S STANDARDS "
              "(recent weighted over old; name the live currency — reach/shares/saves/etc.).\n"
              "2. **Proposed changes** — a numbered list of specific edits to the learner "
              "thresholds (REACH_FLOOR, HALFLIFE_DAYS, SAVES_DEAD) or the captioner brief, "
              "each justified by a number from the data. If data is thin, say so and propose "
              "less — proposing nothing is a valid outcome.\n"
              "3. **3 experiments** for the next 30 days, each with the metric to judge it.\n"
              "Voice: luxury-editorial, never pushy; full name 'My Adventure Costa Rica'; "
              "Spanish in usted. Humble on thin data. Do NOT tell anyone to apply changes "
              "automatically — these are for the owner to approve.")
    payload = {"model": MODEL, "temperature": 0.4,
               "messages": [{"role": "system", "content": method},
                            {"role": "user", "content": user}]}
    req = urllib.request.Request(
        MODELS_URL, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"_Automated narrative unavailable ({e}). The data table is in metrics/review-latest.json._"


def open_issue(title, body):
    if not (TOKEN and REPO):
        return
    owner = REPO.split("/")[0]
    full = (f"@{owner} — your monthly auto-poster review is ready. "
            "Read it below (also on the dashboard), then reply in Claude to apply anything you approve.\n\n"
            + body)
    data = json.dumps({"title": title, "body": full[:60000]}).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/issues", data=data,
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json", "User-Agent": "autoposter-review"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print("Opened issue:", json.loads(r.read().decode()).get("html_url"))
    except Exception as e:
        print("Issue creation skipped:", e)


def _redis_set(key, obj):
    """Mirror the review into Upstash so the dashboard reads it instantly through the
    backend (the public raw.githubusercontent URL is CDN-cached for minutes)."""
    url = (os.environ.get("UPSTASH_REDIS_REST_URL") or "").rstrip("/")
    tok = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if not (url and tok):
        return
    try:
        req = urllib.request.Request(
            url, data=json.dumps(["SET", key, json.dumps(obj, ensure_ascii=False)]).encode(),
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=20).read()
    except Exception as e:
        print("redis set (review) failed:", e)


def main():
    # Guard: one review per month. We schedule a backup attempt, so skip (and don't
    # open a duplicate issue) if we already reviewed this month.
    month = datetime.date.today().strftime("%Y-%m")
    marker = os.path.join(MET, "last_review.txt")
    force = os.environ.get("FORCE_POST") == "1"     # manual "Run review" overrides the monthly guard
    if force:
        print("FORCE_POST set — regenerating the review on demand.")
    if not force and os.path.exists(marker) and open(marker).read().strip() == month:
        print("Review already done this month; skipping."); return
    stats = analyze()
    md = ask_models(stats) or "_No model output this run._"
    os.makedirs(MET, exist_ok=True)
    payload = {"stats": stats, "markdown": md}
    json.dump(payload, open(os.path.join(MET, "review-latest.json"), "w"),
              ensure_ascii=False, indent=1)
    _redis_set("review_latest", payload)        # served instantly via the backend (no CDN cache)
    header = f"# Latest review — {stats['generated']}\n\n"
    open(os.path.join(HERE, "REVIEW-LATEST.md"), "w").write(header + md + "\n")
    sp = os.environ.get("GITHUB_STEP_SUMMARY")
    if sp:
        open(sp, "a").write(header + md + "\n")
    open_issue(f"Monthly review — {stats['generated']}", header + md)
    open(marker, "w").write(month)
    print("Review generated for", stats["generated"],
          f"| eligible={stats['eligible']} recent12={stats['eligible_recent_12mo']}")


if __name__ == "__main__":
    main()
