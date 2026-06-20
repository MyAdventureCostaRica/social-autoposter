#!/usr/bin/env python3
"""
Pull Instagram insights for the WHOLE account -> metrics/insights.json.

Two phases:
  1) discover_media(): enumerate EVERY post on the IG account (paginated) and
     merge into metrics/posts.json. This backfills the entire history and keeps
     finding posts made by hand, outside the auto-poster.
  2) fetch insights for each post, resilient to Instagram's ever-changing metric
     set (impressions->views, plays deprecated, likes hidden, etc.). We try a
     broad metric set and fall back progressively so a single deprecated metric
     never blanks a post.

Older posts barely change once matured, so we refresh only the most recent posts
each run and cache the rest — every post still ends up in insights.json for the
learner to read. Needs META_ACCESS_TOKEN to carry instagram_manage_insights.
"""
import json, os, time, urllib.parse, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "config.json")))
TOKEN = os.environ.get("META_ACCESS_TOKEN")
V = CFG.get("graph_version", "v23.0")
IG = CFG["ig_user_id"]
MET = os.path.join(HERE, "metrics")
POSTS = os.path.join(MET, "posts.json")
OUT = os.path.join(MET, "insights.json")

# Refresh insights for this many most-recent posts each run; older ones are
# pulled once and cached (their numbers have settled).
REFRESH_RECENT = 60

# Per media type, RICHEST set first. The API rejects the whole call if any metric
# is invalid for that type, so we try a comprehensive set and fall back — but we
# keep EVERY metric that comes back (we want every number we can get).
METRIC_SETS = {
    "feed": [
        "reach,likes,comments,saved,shares,total_interactions,views,profile_visits,follows",
        "reach,saved,shares,comments,likes,total_interactions,views",
        "reach,saved,likes,comments", "reach,likes,comments", "reach"],
    "reel": [
        "reach,likes,comments,saved,shares,total_interactions,views,ig_reels_avg_watch_time,ig_reels_video_view_total_time,clips_replays_count",
        "reach,likes,comments,saved,shares,total_interactions,views",
        "reach,likes,comments,views", "reach,views", "reach"],
    "story": [
        "reach,replies,shares,total_interactions,views,profile_visits,follows,navigation",
        "reach,replies,shares,total_interactions,views",
        "reach,replies,views", "reach"],
}


def metric_sets_for(fmt):
    if fmt == "reel":
        return METRIC_SETS["reel"]
    if fmt == "story":
        return METRIC_SETS["story"]
    return METRIC_SETS["feed"]


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


def _api(path, params):
    return _get(f"https://graph.facebook.com/{V}/{path}?" + urllib.parse.urlencode(params))


def load_list(p):
    try:
        return json.load(open(p))
    except Exception:
        return []


def discover_media():
    """Walk the whole feed and merge every post into posts.json (dedupe by id)."""
    existing = load_list(POSTS)
    by_id = {p["id"]: p for p in existing if p.get("id")}
    url = f"https://graph.facebook.com/{V}/{IG}/media?" + urllib.parse.urlencode({
        "fields": "id,timestamp,media_type,media_product_type,caption",
        "limit": "50", "access_token": TOKEN})
    pages, found = 0, 0
    while url and pages < 60:                      # up to ~3000 posts
        r = _get(url)
        if r.get("error"):
            print("discover error:", r["error"].get("message")); break
        for m in r.get("data", []):
            mid = m.get("id")
            if not mid:
                continue
            mt, pt = m.get("media_type"), m.get("media_product_type")
            fmt = ("reel" if pt == "REELS" else
                   "carousel" if mt == "CAROUSEL_ALBUM" else
                   "video" if mt == "VIDEO" else "single")
            row = {"id": mid, "date": (m.get("timestamp") or "")[:10],
                   "base": "ig-" + mid[-6:], "format": fmt,
                   "caption": (m.get("caption") or "")[:140]}
            if mid in by_id:
                # keep any auto-poster fields (base/category/pillar); refresh meta
                by_id[mid].update({k: v for k, v in row.items()
                                   if k in ("date", "caption") or not by_id[mid].get(k)})
            else:
                by_id[mid] = row; found += 1
        url = (r.get("paging") or {}).get("next")
        pages += 1
    out = sorted(by_id.values(), key=lambda p: p.get("date", ""))
    os.makedirs(MET, exist_ok=True)
    json.dump(out, open(POSTS, "w"), indent=1)
    print(f"Discovered {found} new post(s); {len(out)} total in posts.json")
    return out


def pull_one(p):
    """Insights for one media id, trying metric sets until one sticks."""
    mid = p["id"]
    row = {"id": mid, "date": p.get("date"), "base": p.get("base"),
           "format": p.get("format"), "category": p.get("category"),
           "pillar": p.get("pillar")}
    last_err = None
    for mset in metric_sets_for(p.get("format")):
        r = _api(f"{mid}/insights", {"metric": mset, "access_token": TOKEN})
        if r.get("error"):
            last_err = r["error"].get("message"); continue
        for m in (r.get("data") or []):
            try:
                row[m["name"]] = m["values"][0]["value"]
            except Exception:
                pass
        last_err = None
        break
    if last_err:
        row["error"] = last_err
    # One comparable signal: interactions per reach (resilient to which metrics
    # exist), so posts from different eras can be ranked fairly.
    reach = row.get("reach") or 0
    inter = row.get("total_interactions")
    if inter is None:
        inter = (row.get("likes") or 0) + (row.get("comments") or 0) + \
                (row.get("saved") or 0) + (row.get("shares") or 0)
    row["interactions"] = inter
    row["eng_rate"] = round(inter / reach, 4) if reach else None
    return row


def main():
    if not TOKEN:
        raise SystemExit("Missing META_ACCESS_TOKEN.")
    posts = discover_media()
    if not posts:
        print("No posts found."); json.dump([], open(OUT, "w")); return

    cached = {x["id"]: x for x in load_list(OUT) if x.get("id")}
    recent_ids = {p["id"] for p in posts[-REFRESH_RECENT:]}
    out, fetched = {}, 0
    for p in posts:
        mid = p["id"]
        # Use the cached value for any post that isn't in the recent window — even
        # if it errored. Old posts (pre-business-account) never gain insights, so
        # re-pulling all ~670 of them every run is what made this take ~40 min.
        # We only re-fetch the most recent posts (numbers still maturing) + anything
        # we've never seen before.
        c = cached.get(mid)
        # Keep the cached value for any non-recent post, AND for a story we've
        # already captured — story numbers disappear after 24h, so we must never
        # re-pull and overwrite a good value with a later error.
        if c and (mid not in recent_ids
                  or (p.get("format") == "story" and not c.get("error"))):
            c.update({k: p.get(k) for k in ("date", "base", "format",
                                            "category", "pillar") if p.get(k)})
            out[mid] = c
            continue
        out[mid] = pull_one(p); fetched += 1
        time.sleep(0.5)

    rows = sorted(out.values(), key=lambda x: x.get("date") or "")
    json.dump(rows, open(OUT, "w"), indent=1)
    print(f"Insights: {len(rows)} posts ({fetched} freshly pulled) -> insights.json")

    ranked = sorted([x for x in rows if isinstance(x.get("eng_rate"), float)],
                    key=lambda x: -x["eng_rate"])[:5]
    if ranked:
        print("Top by engagement rate:")
        for t in ranked:
            print(f"  rate={t['eng_rate']}  reach={t.get('reach')}  "
                  f"saves={t.get('saved')}  {t.get('format')}  {t.get('date')}")
    elif rows and rows[-1].get("error"):
        print("Insights errored — token may lack instagram_manage_insights:",
              rows[-1]["error"])


if __name__ == "__main__":
    main()
