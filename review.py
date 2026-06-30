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
STOP = frozenset("""
the and for with this that your you our are was has have from into out off over
then than back give gives gave take when what where here there will would could
should about after before they them their were been being only also some more
most very just like even while which whose una unos unas los las del que con por
para como más muy sin son est esta este esto esos esas pero costa rica adventure
myadventurecostarica www http https com
""".split())


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return []


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
            and isinstance(r.get("eng_rate"), (int, float)) and age(r) is not None]

    def wt(r):
        return 0.5 ** (age(r) / HALFLIFE)

    tot = lambda k: sum((r.get(k) or 0) for r in elig)
    inter = max(1, tot("interactions"))
    mix = {k: round(tot(k) / inter, 3) for k in ("saved", "shares", "likes", "comments")}

    byf = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for r in elig:
        b = byf[r.get("format") or "single"]
        b[0] += wt(r) * r["eng_rate"]; b[1] += wt(r); b[2] += 1
    fmt = sorted(([f, round(s / n, 4), c] for f, (s, n, c) in byf.items() if n),
                 key=lambda x: -x[1])

    ranked = sorted(elig, key=lambda r: -(wt(r) * r["eng_rate"]))
    top = [{"date": r["date"], "format": r.get("format"), "reach": r.get("reach"),
            "shares": r.get("shares"), "saved": r.get("saved"),
            "eng_rate": r.get("eng_rate"),
            "caption": (posts.get(r["id"], {}).get("caption") or "")[:120]}
           for r in ranked[:8]]

    words = collections.Counter()
    for r in ranked[:max(5, len(elig) // 4)]:
        for tok in re.findall(r"#?[a-záéíóúñ']{4,}",
                              (posts.get(r["id"], {}).get("caption") or "").lower()):
            t = tok.lstrip("#")
            if t not in STOP:
                words[t] += 1

    dates = sorted(r["date"] for r in rows if r.get("date"))
    queue = len([f for f in glob.glob(os.path.join(SRC, "*"))
                 if f.lower().endswith((".jpg", ".jpeg", ".png", ".heic", ".heif"))])
    return {
        "generated": today.isoformat(),
        "total_posts": len(rows), "with_insights": len(withreach), "eligible": len(elig),
        "eligible_recent_12mo": sum(1 for r in elig if age(r) <= 365),
        "date_range": [dates[0] if dates else None, dates[-1] if dates else None],
        "interaction_mix_pct": mix,
        "format_leaderboard": [{"format": f, "avg_eng_rate": rt, "n": c} for f, rt, c in fmt],
        "top_posts": top, "themes": [w for w, _ in words.most_common(10)],
        "photo_queue": queue, "errored_posts": sum(1 for r in rows if r.get("error")),
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
            + "\n\nWrite the review as MARKDOWN, three sections:\n"
              "1. **Readout** — 4-6 lines on what the data says BY TODAY'S STANDARDS "
              "(recent weighted over old; name the live currency — reach/shares/saves/etc.).\n"
              "2. **Proposed changes** — a numbered list of specific edits to the learner "
              "thresholds (REACH_FLOOR, HALFLIFE_DAYS, SAVES_DEAD) or the captioner brief, "
              "each justified by a number from the data. If data is thin, say so and propose less.\n"
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


def main():
    # Guard: one review per month. We schedule a backup attempt, so skip (and don't
    # open a duplicate issue) if we already reviewed this month.
    month = datetime.date.today().strftime("%Y-%m")
    marker = os.path.join(MET, "last_review.txt")
    if os.path.exists(marker) and open(marker).read().strip() == month:
        print("Review already done this month; skipping."); return
    stats = analyze()
    md = ask_models(stats) or "_No model output this run._"
    os.makedirs(MET, exist_ok=True)
    json.dump({"stats": stats, "markdown": md},
              open(os.path.join(MET, "review-latest.json"), "w"),
              ensure_ascii=False, indent=1)
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
