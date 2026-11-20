# brand/ — what the captioner knows

**v6, 19 November 2026 — a guide's field notebook** (plan and research: `CONTENT-STRATEGY.md`).
The feed's subject is Costa Rica — its wildlife and land, its sports, its people, its food,
history and culture. The expeditions appear only in EXPEDITION posts, 1 in 8. Two inputs:

1. **`knowledge.md`** — generated from the website's own published text: the expedition
   pages (prologue, highlights, day by day, lodges, included, FAQs, bookable departures),
   the company lines from the About, home and bespoke pages, and the founder's **published**
   journal posts. Prices are left out on purpose. Since v6 it is NOT in every call: the whole
   file goes only to EXPEDITION captions; SPORT and PEOPLE captions get only the journal part;
   FIELD and COUNTRY captions get neither (feeding every call the tour pages is what made
   every post a tour day, Oct–Nov 2026).
2. **The photo library in `source-photos/`** — Esteban's own photos (never Unsplash, never
   third-party race frames), each with a companion note `lib-….txt`:
   - `SET:` (photos that share it post together as one photo carousel),
   - `SERIES:` the kinds of post the photo suits, preferred first
     (FIELD, SPORT, COUNTRY, PEOPLE, EXPEDITION — `likely_pillar()` / `fits()` read it),
   - `PHOTO:` and `PLACE:`,
   - `KNOWN FACTS` — 1 to 3 checked, little-known facts, each with its source in brackets
     for checking (never for the caption), plus any caution (species not identified,
     location not confirmed),
   - the expedition-day text and the bookable departures ONLY on EXPEDITION photos.

The captioner (`autopost.py`, `BRAND_PROMPT`) writes the kind of post the plan asks for
today (`target_pillar()`, config `pillar_plan`): 2 FIELD, 2 SPORT, 2 COUNTRY, 1 PEOPLE,
1 EXPEDITION in every 8. A regex guard (`caption_violations`) rejects instructions and
safety tips, inventories of the frame, morals, praise words, "send this to" lines, links,
sentences copied from the site, "Day N" and distance openers, lists of distances, any
selling on the four non-selling kinds, and an EXPEDITION post with no pointer line, and asks
the model for one rewrite.

## Refreshing when the website changes

Both generators need the website project folder (`~/Documents/Claude/Projects/My Adventure
Costa Rica Website`) and run on the Mac (Cowork device shell or Claude Code):

- `python3 brand/build_knowledge.py` → rewrites `brand/knowledge.md` (new departures,
  prices, days, a new journal post).
- `python3 brand/build_library.py` → re-exports the library photos and notes into
  `source-photos/` (edit the list in the script to add or drop photos; a photo already in
  `posted/` is not re-added by hand — see below).

Commit and push; the next daily run uses the new files.

## When the library runs out

Each post consumes one set (or one single). Since v6 the feed posts 4 photo posts a week
(config `post_days`), so the 44 sets restocked on 19 Nov 2026 last about 11 weeks. To
restock: add new own photos with a note (`SERIES:` + checked facts; `SET:` optional), or re-run
`build_library.py` after removing the old copies from `posted/` so the best days come
round again — a feed can repeat its best imagery with a new angle.

## What never goes in

Race-issued items and event apparatus (bibs, podiums, sponsor arches, finish lines),
hospital or medical photos, documents and screenshots, artworks, stock photos, and
anything whose location is not known — unless the note says exactly what it is.
