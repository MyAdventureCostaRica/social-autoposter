#!/usr/bin/env python3
"""
Pull Instagram insights for recent posts -> metrics/insights.json.
Runs weekly in GitHub Actions. Needs META_ACCESS_TOKEN to include the
`instagram_manage_insights` permission (refresh the token to add it).

Reach, saves, shares, comments, likes, total interactions per post. The monthly
strategy review reads this file to learn what's actually working.
"""
import json, os, time, urllib.parse, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "config.json")))
TOKEN = os.environ.get("META_ACCESS_TOKEN")
V = CFG.get("graph_version", "v23.0")
MET = os.path.join(HERE, "metrics")
POSTS = os.path.join(MET, "posts.json")
OUT = os.path.join(MET, "insights.json")


def get(path, params):
    url = f"https://graph.facebook.com/{V}/{path}?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return {"error": json.loads(e.read().decode()).get("error", {})}
        except Exception:
            return {"error": {"message": f"HTTP {e.code}"}}


def main():
    if not TOKEN:
        raise SystemExit("Missing META_ACCESS_TOKEN.")
    posts = json.load(open(POSTS)) if os.path.exists(POSTS) else []
    if not posts:
        print("No posts logged yet (metrics/posts.json empty). Nothing to pull.")
        os.makedirs(MET, exist_ok=True)
        json.dump([], open(OUT, "w"))
        return

    full = "reach,saved,shares,comments,likes,total_interactions"
    out = []
    for p in posts[-60:]:                      # last ~60 posts
        mid = p.get("id")
        if not mid:
            continue
        row = {"id": mid, "date": p.get("date"), "base": p.get("base"),
               "format": p.get("format")}
        r = get(f"{mid}/insights", {"metric": full, "access_token": TOKEN})
        if r.get("error"):                     # some metrics aren't valid for some media types
            r = get(f"{mid}/insights", {"metric": "reach,likes,comments", "access_token": TOKEN})
        for m in (r.get("data") or []):
            try:
                row[m["name"]] = m["values"][0]["value"]
            except Exception:
                pass
        if r.get("error"):
            row["error"] = r["error"].get("message")
        out.append(row)
        time.sleep(1)

    os.makedirs(MET, exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"Pulled insights for {len(out)} posts -> metrics/insights.json")
    ranked = sorted([x for x in out if isinstance(x.get("saved"), int)],
                    key=lambda x: -x["saved"])[:5]
    if ranked:
        print("Top by saves:")
        for t in ranked:
            print(f"  saves={t.get('saved')} reach={t.get('reach')} {t.get('base')}")
    elif out and out[0].get("error"):
        print("Insights returned an error — likely the token lacks "
              "instagram_manage_insights. Refresh the token with that permission.")


if __name__ == "__main__":
    main()
