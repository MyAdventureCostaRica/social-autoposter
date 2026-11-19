# Writes brand/knowledge.md for the captioner from the website's own published text:
# the three expeditions (content/tours/en), the published journal posts, and the About /
# home / bespoke lines. Re-run whenever the site changes.
import os, re, yaml
SITE = os.path.expanduser("~/mnt/My Adventure Costa Rica Website/astro-site/src")
OUT = os.path.expanduser("~/mnt/social-autoposter/brand/knowledge.md")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
def plain(s): return re.sub(r"<[^>]+>", "", s or "").replace("\n", " ").strip()
def tour(name):
    t = open(os.path.join(SITE, "content/tours/en", name), encoding="utf-8").read()
    return yaml.safe_load(t.split("---")[1])
import datetime
parts = ["# My Adventure Costa Rica — what the website says (the captioner's only product source)",
         f"Generated from the live site's own text on {datetime.date.today().isoformat()}. Everything here is published and approved by the founder. Prices are deliberately left out of the feed: say \"details in the bio\".", ""]
ORDER = ["trail-running.md", "gravel-cycling.md", "hiking.md", "wildlife.md", "watersports.md"]
names = [n for n in ORDER if os.path.exists(os.path.join(SITE, "content/tours/en", n))] + sorted(
    n for n in os.listdir(os.path.join(SITE, "content/tours/en")) if n.endswith(".md") and n not in ORDER)
for name in names:
    t = tour(name)
    if not t.get("published"): continue
    tag = ", ".join(x for x in [t.get('episode', ''), t.get('discipline', '')] if x)
    parts.append(f"## {t['title']}" + (f" ({tag})" if tag else ""))
    parts.append(f"Tagline: {plain(t.get('tagline'))} — {t.get('subhead','')}")
    parts.append(f"Region: {t.get('region','')}. {t['durationDays']} days, {t['groupMin']} to {t['groupMax']} athletes" + (f", about {t['distanceKm']} km" if t.get('distanceKm') else "") + ".")
    deps = t.get("departures", []) or []
    sale = [d["label"] for d in deps if d.get("available", True) is not False]
    shown = [d["label"] for d in deps if d.get("available", True) is False]
    parts.append("Bookable departures: " + ("; ".join(sale) if sale else "none on sale right now") + ".")
    if shown: parts.append("Shown on the site but NOT for sale (never offer these): " + "; ".join(shown) + ".")
    p = t.get("prologue", {})
    if p.get("pullQuote"): parts.append(f"Founder's line: \"{p['pullQuote']}\" ({p.get('pullQuoteBy','')})")
    if p.get("regionDescription"): parts.append("Where: " + p["regionDescription"])
    for n in p.get("narrative", []): parts.append(n)
    for season, ed in (t.get("editions") or {}).items():
        parts.append(f"### {ed.get('title','')}: {ed.get('lede','')}")
        for lit in ed.get("literature", []): parts.append(lit)
    parts.append("### Highlights")
    for h in t.get("highlights", []): parts.append(f"- {plain(h['title'])} {h.get('description','')}")
    parts.append("### Day by day")
    for d in t.get("itinerary", []):
        nums = " · ".join(x for x in [d.get("runningKm",""), d.get("elevation",""), f"lodge: {d.get('lodge','')}" if d.get("lodge") else "", f"meals: {d.get('meals','')}" if d.get("meals") else ""] if x)
        parts.append(f"- Day {d['day']} · {plain(d.get('title'))} ({d.get('location','')}) · {nums}")
        for para in d.get("paragraphs", []): parts.append("  " + para)
    parts.append("### Lodges")
    for l in t.get("lodges", []): parts.append(f"- {l['name']} ({l.get('region','')}): {l.get('description','')}")
    parts.append("### Included: " + "; ".join(t.get("included", [])))
    parts.append("### On request: " + "; ".join(t.get("availableOnRequest", [])))
    parts.append("### Not included: " + "; ".join(t.get("notIncluded", [])))
    parts.append("### Questions guests ask")
    for q in t.get("faqs", []): parts.append(f"- {q['question']} {q['answer']}")
    parts.append("")
parts += ["## The company, in the site's words",
 "Founder-led, with a handful of trusted guides and seventeen years of routes learned on foot — and a quiet rule that we never sell a journey we haven't first run ourselves.",
 "The brief we set ourselves was simple. No groups larger than eight. No itinerary we hadn't field-tested ourselves. Every kilometre of trail is one we've personally run, hiked, or ridden. Every meal has an origin we can name.",
 "Esteban Umaña, founder and expedition leader: on a mountain bike since 1994, running trails since 2008, in the water since school and under it, scuba certified, at fifteen; has worked Costa Rica's outdoor sport circuit since 2009 supporting races of every kind, became a guide in 2014, and from 2017 spent years as a full-time travel concierge designing bespoke journeys. Guides as a Wilderness First Responder; whitewater, diving and rope work are operated by licensed local outfitters. The blueprint came from adventure racing: a team of four crossing a place on foot, on bike, on water, by map and compass. The hosted version is what this company became.",
 "Costa Rica fits less than one tenth of one percent of the world's land area and holds nearly five percent of its biodiversity. The trails change ecosystem every two hours of walking: cloud forest at dawn, dry tropical at lunch, coastal singletrack by dusk.",
 "Two professional guides, one dedicated photographer, and a group small enough to share a long table at the end of the day. The lodges are chosen for character and location, not their star count. The food leans on what the valleys we run through can grow, and the route is built on the relationships Esteban has with the mountain families who live along it.",
 "Bespoke private journeys: for travellers with a specific vision (fitness, dates, regions, comfort, occasion), designed from a blank page, hand-tested by us, operated end to end; a 20-minute call, then a costed draft itinerary within 7 days, revised together until it is right. School programs: bespoke educational and global-service programs for international schools and universities, every route scouted before students arrive.",
 ""]
# Published journal posts (the founder's own voice; FOUNDER posts paraphrase these only)
jdir = os.path.join(SITE, "content/journal/en")
parts.append("## The founder's journal (published posts, his own words — paraphrase, never copy)")
for f in sorted(os.listdir(jdir)):
    t = open(os.path.join(jdir, f), encoding="utf-8").read()
    fm, body = t.split("---")[1], "---".join(t.split("---")[2:])
    meta = yaml.safe_load(fm)
    if not meta.get("published"): continue
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S).strip()
    parts.append(f"### \"{meta['title']}\" ({meta.get('publishDate')}, {meta.get('category')})")
    parts.append(body)
    parts.append("")
open(OUT, "w", encoding="utf-8").write("\n".join(parts))
print("wrote", OUT, os.path.getsize(OUT), "bytes")
