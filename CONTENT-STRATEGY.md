# My Adventure Costa Rica — content strategy

This is the plan the auto-poster works from. It's documented here so the intent
is explicit, not accidental. The AI captioner is loaded with these same rules.

## The mission

Build My Adventure Costa Rica into **the trusted source for adventure knowledge
and all things Costa Rica.** Authority and authenticity come first; bookings
follow trust. We post with intent, never just to fill a feed.

## The selling philosophy: ~80% value, ~20% gentle invitation

Endurance travel is a high-trust, high-price decision. Nobody books thousands of
dollars of guided adventure from a hard seller — they book the person they're
convinced is the real expert and the real deal. So:

- **~80%** of posts give value — teach something, show something, tell a true story.
- **~20%** gently invite — a quiet line at most ("Trail running journeys in Costa
  Rica, designed slowly" / "Design yours"). Never urgency, never discounts.
- Restraint *is* the luxury brand, and it's also what converts. Knowledge proves
  authority; the founder's own racing proves authenticity; the soft invite closes
  an audience that already believes.

## The four pillars

The AI picks the ONE that best fits each photo. Over a week, aim for this mix
(of ~5–7 posts) by feeding the right kinds of photos:

1. **KNOWLEDGE (~2/week)** — teach something real: terrain, seasons, what makes a
   route special, training, what to expect. The reader should *learn* something.
   This is what makes us the authority. *Feed it:* landscapes, conditions, gear,
   maps, anything you can attach a fact or insight to (use a note).

2. **FOUNDER / ATHLETE (~1–2/week)** — your own racing, scouting, training,
   behind-the-scenes. Authentic proof you live this. *Feed it:* photos of you out
   there — and add a note with the real facts (e.g. "me, fastest 50K, sub-5h, 4th
   overall") so it's told in first person and true.

3. **ROUTE / DESTINATION (~2/week)** — the places themselves, aspirational. Make
   the reader want to stand there. *Feed it:* your strongest scenery.

4. **EXPERIENCE / TOURS (~1/week)** — what a journey with us is actually like:
   intimate groups, lodges, the feeling. The closest-to-sale pillar — kept soft
   and editorial, never a brochure. *Feed it:* trip moments, lodges, small groups.

## Formats (post types)

- **Single image** — one branded photo + caption. The default for atmospheric/route shots.
- **Carousel** — a photo cover followed by 2–4 editorial text slides (and an optional soft closing slide). The AI chooses this for KNOWLEDGE posts that teach across steps, and often for FOUNDER stories. Slides use the sand/ink/Fraunces house style.
- **Video / reels** — *(next build)* the system can post finished video you or your editors drop in (drone pan shots, one-take talking clips). It never edits — it captions (from a thumbnail + your note) and posts as a reel. Needs a free video host (Cloudinary) because video files are too large for GitHub; that's its own short setup.

The AI picks single vs carousel per photo based on intent.

## How the system uses this

- The AI looks at each photo, picks the fitting pillar, and writes the caption in
  that intent — knowledge posts teach, founder posts tell your story, etc.
- **Notes** (optional `IMG_xxxx.txt` files) give it the true facts for a photo so
  it doesn't guess — essential for founder/athlete and any named place.
- It still never invents places, distances, or facts it wasn't given.

## How you improve it over time (three levers)

1. **A note on a photo** — steers *what one post says* (the true story). Optional,
   only for the photos that need it.
2. **The brief** — steers the *style of every future post*. Tell Claude "do more
   X, never Y, push bespoke harder," and it updates the AI's instructions.
3. **Approve / reject** — your final quality gate on each finished post.

## What to shoot / collect, going forward

To keep all four pillars fed, gather: scenery (route/destination), you in action
(founder), trip and lodge moments (experience), and anything teachable —
conditions, terrain, seasonal change — that you can pair with a one-line fact
(knowledge). Restock the `source-photos` folder before you run low.
