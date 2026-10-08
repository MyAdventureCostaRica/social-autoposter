# brand/ — the website writes the feed

Since October 8 2026 the auto-poster does not caption random photos. It posts the
expeditions the way the website sells them, in the founder's voice, from two inputs:

1. **`knowledge.md`** — generated from the website's own published text: the three
   expedition pages (`astro-site/src/content/tours/en/*.md`: prologue, highlights, day by
   day, lodges, included, FAQs, bookable departures), the company lines from the About,
   home and bespoke pages, and the founder's **published** journal posts. It is appended
   to the captioner's system prompt on every call. Prices are left out on purpose.
2. **The photo library in `source-photos/`** — Esteban's own photos from the website
   project (never Unsplash, never third-party race frames), named `lib-<expedition>-<day>-<n>.jpg`,
   each with a companion note `lib-….txt` that says which expedition day or highlight
   the photo illustrates, in the site's words, plus a `SET:` line. Photos that share a
   `SET` are posted together as one photo carousel (the slides are the photos, the
   caption is the day).

The captioner (`autopost.py`, `BRAND_PROMPT`) then writes one of five posts — a day of an
expedition, the expedition itself, a place or nature fact tied to a day, a founder post
paraphrasing the journal, or the kitchens and the long table — and every post names the
expedition and ends with "Details in the bio." A regex guard (`caption_violations`)
rejects instructions and safety tips, inventories of the frame, morals, praise words,
"send this to" lines, sentences copied from the site, and captions with no product line,
and asks the model for one rewrite.

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

Each daily post consumes one set (or one single). With ~21 sets the library lasts about
three weeks. To restock: add new own photos with a note (`SET:` optional), or re-run
`build_library.py` after removing the old copies from `posted/` so the best days come
round again — a feed can repeat its best imagery with a new angle.

## What never goes in

Race-issued items and event apparatus (bibs, podiums, sponsor arches, finish lines),
hospital or medical photos, documents and screenshots, artworks, stock photos, and
anything whose location is not known — unless the note says exactly what it is.
