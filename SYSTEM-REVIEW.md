# System review prompt — evolve the whole auto-poster

Paste this to Claude on a cadence (monthly is sensible; or whenever a post clearly
over- or under-performs). It is a standing instruction to **improve everything we
have built so far**, grounded in the latest real data — not to redo it from scratch.

Guiding principles (do not violate):
- **By today's standards.** Weight recent performance far above old. Re-derive what
  "success" even means each time — Instagram changes which metric matters (likes →
  saves → shares → sends → reach → watch time). Never optimize to a stale yardstick.
- **Humble on thin data.** With few recent posts carrying real reach, treat signals
  as directional. Don't turn one viral post into "the formula."
- **Never push.** The brand wins by being THE place for adventure knowledge + all
  things Costa Rica; ~80% value, ~20% soft invite. Luxury-editorial voice. Spanish
  in formal usted. Full brand name, never an acronym.
- **Show the math.** Every ranking shows its inputs; every recommendation cites the
  number behind it.

---

## Run this review

**1. Refresh and re-analyse the data.**
- Trigger the Daily insights workflow (or read the latest `metrics/insights.json`
  + `metrics/posts.json`).
- Recompute performance with the reach floor and recency weighting. Report, with
  numbers: signal-pool size, which metric is currently the live *currency*
  (reach / shares / saves / follows / watch-time — whichever this account actually
  earns now), top posts, and breakdowns by **format**, **pillar/category**, **theme/
  keyword**, and **posting time/day**.
- Call out anything that changed since last review (new currency? a format pulling
  ahead? a theme rising or fading?).

**2. Are we measuring the right things?**
- We currently store reach, views, likes, comments, shares, saved, total_interactions.
  Check what *else* the API now returns for our media types (profile_visits,
  follows, reels watch-time/replays, story navigation). The strategic prize is
  **audience growth** — follows + profile-visits per post — which is closer to the
  goal than engagement rate. Propose adding a metric only if there's enough data to
  use it without overfitting.

**3. Re-tune the learner (`autopost.py performance_brief()`).**
- Revisit REACH_FLOOR, HALFLIFE_DAYS, SAVES_DEAD, the STOP list, and the dimensions
  it ranks. Propose concrete edits and explain the data that justifies each.
- Verify it still degrades gracefully (returns "" on thin data) and still detects
  the currency dynamically.

**4. Audit the captioner brief (`BRAND_PROMPT`) against reality.**
- Does what's actually resonating match what the brief tells the writer to do? If
  the data says shares-not-saves, reels-not-stills, a theme that travels — make sure
  the brief reflects it, softly. Propose edits; keep the voice intact.

**5. Health check.**
- Token still valid (TYPE=PAGE, never-expires, carries instagram_manage_insights)?
- Recent `Daily social post` + `Daily insights` runs green? Photo queue not running
  low? Any errored posts in insights.json worth investigating?

**6. Propose 3 experiments.**
- Three specific, testable moves for the next ~30 days (e.g. "post reels of the
  Queen Stage descent — reels carry our reach"; "open with a one-line shareable
  hook on knowledge posts"). Each with the metric we'll judge it by and how long.

**7. Update memory** with anything durable that changed (new currency, new
thresholds, new finding), and tell me — in plain language — the 3 things worth
doing this month and why.

Deliver as: a short data readout (with the numbers), the specific code/brief edits
you'd make, and the 3 experiments. Make the edits only after I approve.
