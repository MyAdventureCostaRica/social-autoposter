# My Adventure Costa Rica — content strategy (v6, 19 November 2026)

This is the plan the auto-poster works from. The captioner (`autopost.py` BRAND_PROMPT) is loaded
with the same rules. The research behind it is in the website project:
`claude/SOCIAL_VOICE_RESEARCH_2026-11-19.md`.

## Why it changed

Esteban, 19 Nov 2026: the feed "feels too selly, you are just describing days, no value content
seems to come up, there is no real strategy". The numbers agreed: 28 feed posts between 9 Oct and
7 Nov earned 0 shares, 0 comments, 1 save and 0 follows. 5 of every 7 posts were a tour day, and
the only facts the writer had were our own tour pages.

## What companies like ours do (read on their own Instagram, 19 Nov 2026)

- **Run the Alps** (founder-led trail running tours): athletes' first-person stories, a founder
  who writes books and journalism, and plain sell posts that each give a reason. Never day-by-day.
- **Pelorus**: the team's own field stories, people and culture first.
- **Black Tomato**: every post starts from a human idea or question; the trip is the answer.
- **Natural Habitat Adventures**: a wildlife moment plus one fact, guides in first person,
  travellers' videos credited by name.
- **Lapa Rios** (the counter-example): rooms, pools and "Book your stay" — the brochure mode.
- **Instagram (2026)**: ranks on watch time, likes per reach and sends per reach; sends weigh most
  for reaching new people. Carousels earn saves; reels earn reach. About 2 reels + 3–5 feed posts
  a week.

## The mission

The feed is **a Costa Rican guide's field notebook**: the country's wildlife and land, its sports,
its people, its food, history and culture, told by someone who knows them first-hand. The
expeditions appear only where they belong. A reader who never books should learn something true
in every post and want to send it to a friend. Bookings follow trust.

## The five kinds of post (a cycle of 8 feed posts)

| Kind | Share | What it is | Its job |
|---|---|---|---|
| **FIELD** (field notes) | 2 in 8 | One little-known true thing about the living thing or the land in the photo: a habit, a plant, the cloud, the wind, a season, the rock, how the place came to be | Saves and sends |
| **SPORT** (the sport here) | 2 in 8 | What trail running, gravel and hiking are like in Costa Rica: altitude, heat, rain, surfaces, why the roads and trails exist, the races and people of the sport. Esteban in first person only when his published journal tells the story, each story once | Authority |
| **COUNTRY** (the country) | 2 in 8 | Food, drink, history, culture: a dish and where it comes from, a festival, a craft, a date or a law that shaped the country, how a town lives | Value |
| **PEOPLE** | 1 in 8 | A person or family on these routes or in a place's story, only as the note or the journal names them | Trust |
| **EXPEDITION** | 1 in 8 | The only sell. Opens with a fact, a person or a moment from the expedition's ground, then the expedition with its published facts and one reason to go; last line = name, departures, "Details in the bio." | Bookings |

Reels follow the same plan (mostly field notes): one true thing about a place in motion.

## How every caption sounds

- Opens with a person, a little-known fact, a date, a question or a moment. **Never "Day N" or a
  distance** (`caption_violations()` rejects both).
- One subject. The four non-selling kinds never name an expedition, departures, the bio or the
  company (enforced).
- One or two numbers that matter (1955, 98.6%), never a list of kilometres and metres (enforced:
  more than 2 distances/altitudes, 3 on an expedition post, is rejected).
- Names people and places; credits photographers and guests.
- Ends on what the fact means; about 1 in 4 on one real question.
- Kept from every earlier version: no tips or instructions, no praise words, no "send this to", no
  emoji, numerals, English only, nothing invented, first person only from his real stories.

## Where the facts come from

- Each photo's note: `SERIES:` (the kinds it suits, preferred first), `PHOTO:`, `PLACE:` and
  `KNOWN FACTS:` — 1 to 3 checked, little-known facts, each with its source in brackets for
  checking (sources never go into the caption). Esteban strikes anything wrong; his knowledge beats
  any source.
- The expedition-day text and the departures are only in the notes of EXPEDITION photos.
- `brand/knowledge.md` (the site's tour pages, company text and journal) goes only to EXPEDITION
  posts; SPORT and PEOPLE posts get only the journal; FIELD and COUNTRY get neither.
- Only what the facts say (added after caption preview #8, 19 Nov 2026, where 5 of 8 captions joined
  true facts into claims no source made): natural history may describe what is in the photo, but a
  cause, an origin, a first, a record, a comparison or an absolute must stand in one of the facts.
  `caption_violations()` sends a caption back for one rewrite when it uses a claim word (first, only,
  because, built, began, explains, outlasts, never, without stopping…) that the note does not use.
  When a photo invites a wrong link, the note carries a caveat line ("do not say…").

## Cadence

4 photo posts a week (config `post_days`: Sun, Tue, Thu, Sat, Costa Rica time) + 2 reels (Fri and
Sat slots). Esteban chose this on 19 Nov 2026 over a post every day: fewer, stronger posts, and the
44 restocked posts last about 11 weeks instead of 6. A forced run, a dashboard upload or "New
caption" still works any day.

## How to improve it over time

1. **A note on a photo** steers what one post says. A line of your own ("I crossed here on foot in
   2019 when the bridge was out") is worth more than any researched fact.
2. **The brief** (this file + `SOCIAL_VOICE_GUIDE.md` + BRAND_PROMPT) steers every post.
3. **Approve / reject** on the dashboard is the final gate.
4. **Measure** shares and saves per kind in the monthly review: the kinds that get sent and saved
   earn more of the cycle.
