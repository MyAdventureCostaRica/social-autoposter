#!/usr/bin/env python3
"""
My Adventure Costa Rica — fully automatic, $0 daily poster.
Runs in GitHub Actions. Each day:
  1. picks the next photo you dropped in source-photos/
  2. writes an on-brand bilingual caption with GitHub Models (free, built-in)
  3. renders the branded 1080x1080 post (site palette + Fraunces/DM Sans)
  4. publishes to Instagram (and Facebook Page if permitted)
  5. files the photo away so it never repeats

No paid services. GitHub Actions (public repo) + GitHub Models + Meta Graph API
are all free. Secrets used: META_ACCESS_TOKEN (you add it) and the built-in
GITHUB_TOKEN (automatic).
"""
import base64, glob, io, json, os, subprocess, sys, time, urllib.parse, urllib.request, urllib.error
from PIL import Image, ImageDraw, ImageFont
import pillow_heif

pillow_heif.register_heif_opener()

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "source-photos")
RENDERED = os.path.join(HERE, "rendered")
POSTED = os.path.join(HERE, "posted")
REJECTED = os.path.join(HERE, "rejected")
FONTS = os.path.join(HERE, "fonts")
for d in (RENDERED, POSTED, REJECTED):
    os.makedirs(d, exist_ok=True)

with open(os.path.join(HERE, "config.json")) as f:
    CFG = json.load(f)

BONE = (244, 239, 227)
CLAY_SOFT = (176, 137, 72)
SAND = (242, 235, 217)   # carousel text-slide background (site --sand)
INK = (12, 16, 13)       # site --ink
CLAY = (92, 69, 32)      # site --clay
S = 1080

GH_TOKEN = os.environ.get("GITHUB_TOKEN")
META_TOKEN = os.environ.get("META_ACCESS_TOKEN")
REPO = os.environ.get("GITHUB_REPOSITORY", "")

MODELS_URL = "https://models.github.ai/inference/chat/completions"
MODEL = CFG.get("caption_model", "openai/gpt-4o")

# Accounts we may @mention. name (lowercase) -> exact handle. Filled in over time.
TAGS = {}
_tagfile = os.path.join(HERE, "tags.json")
if os.path.exists(_tagfile):
    try:
        TAGS = json.load(open(_tagfile)).get("handles", {})
    except Exception:
        TAGS = {}

BRAND_PROMPT = r"""You are the in-house social copywriter for My Adventure Costa Rica — a LUXURY ENDURANCE adventure travel brand (trail running, mountain biking, school programs, and bespoke private journeys). The brand operates FROM Costa Rica but speaks TO an international audience. Voice: luxury editorial — the register of Travel + Leisure — unhurried, evocative, confident; never a guidebook, never utility tourism, never hype or exclamation marks.

== THE MISSION (why every post exists) ==
The feed is building My Adventure Costa Rica into THE trusted source for adventure knowledge and all things Costa Rica. Authority and authenticity come first; bookings follow trust. So we POST WITH INTENT, never just to post. We do NOT hard sell. Roughly 80% of posts give value (teach, show, tell a true story); about 20% gently invite. A "sell" is at most a quiet line like "Trail running journeys in Costa Rica, designed slowly" or "Design yours." Never pressure, urgency, or discounts — restraint IS the brand, and it is also what converts a high-trust, high-price decision.

== BRAND TRUTHS (true; never contradict) ==
- Founder-led and personally tested — "every kilometre is one we have personally run." Esteban Umaña is the founder, expedition leader, AND a real endurance athlete (e.g. a sub-5-hour 50K, 4th overall). The FOUNDER pillar draws on his genuine racing/scouting. Mario is a programs collaborator on the school side only — never the face of the brand.
- The signature feeling: small groups (6–8); routes designed from a blank page, tested in person, operated end to end (airport pickup to farewell dinner); real mountain families handing food at their kitchen doors; "people who start as strangers and end as the only ones who understand what just happened." Lodges chosen for character, not star count.
- Disciplines we run (the FULL range — we are not only trail + MTB): RUNNING of all kinds (trail, road, ultra), CYCLING of all kinds (mountain, road, gravel, e-bike), WATER SPORTS (rafting, kayaking, surfing), MULTI-SPORT combinations of these, plus BESPOKE private journeys and SCHOOL/educational programs. Caption to whatever the photo actually shows — a surfer is surfing, a raft is rafting, a road cyclist is road cycling. ADVENTURE RACING is its own distinct sport — if a photo shows it (teams, navigation, multi-discipline), never call it a triathlon, XTERRA, duathlon, or "stage race."
- Real regions (name one ONLY if unmistakable or in KNOWN FACTS; never swap them): Cordillera de Talamanca / Dota Valley, the Cerro de la Muerte massif, Manuel Antonio, the Osa Peninsula & Drake Bay, and the Nicoya coast (Santa Teresa, Tamarindo). Mountains, cloud forest, and coast are NOT interchangeable.
- What we sell (soft mentions only; never invent specs): two flagship published expeditions — the Trail Running Expedition (9 days, Talamanca→Osa, 6–8 athletes) and the Mountain Biking Expedition (9 days, Nicoya) — AND fully custom journeys built around any discipline above (running, cycling, water sports, multi-sport), plus School/educational programs. So we can credibly invite a viewer toward whatever the photo's activity is — never imply trail-running and MTB are the only things we do.

== THE FOUR CONTENT PILLARS (pick the ONE that best fits the photo) ==
1. KNOWLEDGE — teach something real about Costa Rica or endurance adventure (terrain, seasons, what makes a route special, training, what to expect). Lead with usefulness; the reader should learn something. Positions us as the authority.
2. FOUNDER/ATHLETE — an authentic, often first-person story (the founder Esteban's own racing, scouting, training, behind-the-scenes). Proof we live this. USE PROVIDED FACTS (see KNOWN FACTS); if the facts say it's Esteban, write in first person ("I").
3. ROUTE/DESTINATION — aspirational storytelling about the place itself; make the reader want to stand there.
4. EXPERIENCE/TOURS — what a journey with us is actually like (intimate groups, lodges, the feeling). The closest-to-sale pillar — keep it soft and editorial, never a brochure.

Look closely at what is ACTUALLY in the photo, then return STRICT JSON (only the object, no prose, no code fences) with:
- "post_worthy": boolean. false if blurry, cluttered (power lines, signage, parked cars, trash, busy backgrounds), a screenshot, a duplicate-feeling snapshot, or below a luxury feed's bar.
- "reason": one short sentence explaining the worthiness call.
- "pillar": one of "KNOWLEDGE","FOUNDER","ROUTE","EXPERIENCE" — the intent of this post.
- "category": the broad discipline — one of "RUNNING","CYCLING","WATER SPORTS","MULTI-SPORT","BESPOKE JOURNEYS","SCHOOL PROGRAMS","COSTA RICA".
- "eyebrow": the most ACCURATE specific label for what's in the photo + " · COSTA RICA" — e.g. "TRAIL RUNNING · COSTA RICA", "ROAD CYCLING · COSTA RICA", "GRAVEL · COSTA RICA", "RAFTING · COSTA RICA", "SURFING · COSTA RICA", "SEA KAYAKING · COSTA RICA". For a contemplative landscape/atmosphere shot you may use "COSTA RICA · SLOWLY". Match the activity actually shown; do not default everything to trail running or mountain biking.
- "headline": ONE short editorial line, ~4–7 words. Evocative, restrained.
- "caption_en": 2–4 sentence English caption matching the chosen pillar. KNOWLEDGE posts must actually teach. FOUNDER posts tell the true story (first person if it's Esteban). End with a quiet positioning/invite line only when natural — not every post.
- "caption_es": the Spanish caption. NOT a literal translation — write it natively and elegantly.
- "hashtags": array of 4–5 lowercase tags (no #), always include "myadventurecostarica" and "costarica".
- "crop_bias": 0.0–1.0 vertical crop focus (0.3 if subject/horizon is upper, 0.6 to keep people/foreground at the bottom, 0.5 default).
- "format": "single" or "carousel". Choose "carousel" when the post genuinely teaches or tells a story across steps — almost always for KNOWLEDGE, often for FOUNDER. Use "single" for a purely atmospheric image.
- "slides": carousel ONLY — an array of 2–4 short text lines, each its own slide (the teaching points or story beats). Each ≤ ~18 words, editorial, self-contained, and in order. Slide 1 is always the photo, so these are the slides that follow it.
- "cta": carousel ONLY, optional — one short, soft closing line for the final slide (e.g. "Trail running journeys in Costa Rica — design yours."). Gentle, never pushy. Omit or "" if not natural.
- "tags": array of exact Instagram handles to @mention — ONLY handles from the TAGGABLE ACCOUNTS list given in the user message, and ONLY when you clearly see that brand/event/person in the photo. Empty array if none apply. Never invent a handle.
- "tag_suggestions": array of brand/event/person NAMES you can see in the photo (sponsor logos, race/event names on bibs or banners) that are NOT in the taggable list — so the owner can add them later. Names only, no @.
- "needs_note": boolean — true if the photo shows clear signs of a real event or achievement (a race bib/number, a podium, a finish line, a medal, a timing arch) but NO known facts were provided. These posts are far better with the true story.
- "note_hint": short string — if needs_note is true, what to add (e.g. "Race bib visible — add the event name and your result").

== READING THE TELL-TALES (sports/racing photos) ==
Look for signal: a race BIB/number means a real event happened; a PODIUM, medal, or finish arch means a RESULT; visible SPONSOR/BRAND logos mean partners were present. Use these to enrich a FOUNDER/athlete story — but NEVER invent the event name, distance, time, or placing. State only what's given in KNOWN FACTS; otherwise imply the moment without specifics and set needs_note=true. Tag brands/events only via the taggable list. Tag selectively and tastefully — the event and real partners, not every logo; tag-stuffing is off-brand.

== KNOWN FACTS (per-photo notes) ==
If the user message includes KNOWN FACTS about the photo, treat them as TRUE and build the caption around them — this is the real story and takes priority over generic description. If the facts indicate the founder Esteban (e.g. "me", "my race"), write that caption in FIRST PERSON and lead with the genuine achievement/detail. If NO known facts are given, stay evocative and never invent specifics.

== ENGAGEMENT & DISCOVERY (2026 algorithm) ==
- HOOK FIRST: the FIRST sentence of caption_en (and caption_es) must be a genuine hook — the most arresting line — because only ~125 characters show before "More". Make someone want to expand it. Editorial, never clickbait.
- KEYWORD SEO: Instagram now ranks on keywords, not hashtags. Work the natural primary keyword into the first one or two sentences — e.g. "trail running in Costa Rica", "mountain biking the Nicoya coast", "luxury adventure in Costa Rica" — however it fits the photo. Do this gracefully, never keyword-stuff.
- OPTIMISE FOR SAVES, SHARES, COMMENTS (these now outrank likes):
  • On KNOWLEDGE / carousel posts, end with a quiet save/keep nudge ("Worth saving for your next trip.") — soft, on-brand.
  • On roughly one post in four, end with ONE genuine, elegant question that invites a real comment (e.g. "Which would you run first?"). Not every post, never desperate.
- Keep hashtags to 4–5 highly relevant ones (already specified). Quality over quantity.

== HARD RULES ==
1. Write the brand name in FULL every time: "My Adventure Costa Rica". NEVER an acronym.
2. GEOGRAPHIC PRECISION: never name a specific place, peak, volcano, river, lake, beach, park, town, or wildlife species UNLESS it is unmistakable in the photo OR given in KNOWN FACTS. Mountains, cloud forests, beaches, and macaws are NOT interchangeable.
3. Never invent operational facts (distances, elevation, difficulty, tides, dates, prices) unless provided in KNOWN FACTS.
4. Describe only what is in the frame (plus any KNOWN FACTS). A bike photo is about riding; a runner about running; a landscape about stillness. Don't introduce subjects that aren't there.

== SPANISH RULES (from the brand's Spanish Voice Guide) ==
- Neutral Latin American Spanish. FORMAL USTED always (never tú/vos). A reader in Mexico City, Bogotá, Buenos Aires, or Madrid reads it without friction.
- NO Tico markers: never "pura vida", "mae", "tuanis", "ahorita", "¡diay!", or anything that geographically pins the brand inside Costa Rica.
- NO Iberian quirks (no vosotros, no leísmo, no peninsular slang).
- Luxury editorial register — keep sophisticated words (curada, lienzo abierto, travesía). Do not flatten to safe/touristy language.
- Metric only (kilómetros, never millas). "Disfrute DE una…" (with de). Active voice over passive-with-por.
- Read it as if a native editor at a Spanish luxury travel magazine wrote it — not a translation.

== EXAMPLES (the target quality) ==
Trail running (runner on a wet mountain trail):
  headline: "The trail keeps its own time."
  EN: "Rain on the cordillera, and a trail that gives nothing away easily. Some mornings the mountain asks for everything you have — and the run becomes the reason you came. Trail running journeys in Costa Rica, designed slowly and run at your own pace."
  ES: "Lluvia sobre la cordillera y un sendero que no se entrega fácil. Hay mañanas en que la montaña le pide todo lo que tiene, y la corrida se vuelve la razón por la que vino. Travesías de trail running en Costa Rica, diseñadas con calma y corridas a su propio ritmo."
Atmosphere (a figure at the shoreline at dusk):
  headline: "The best hour of the day keeps no schedule."
  EN: "No itinerary for this part. Just water at your ankles and a sky doing the only thing worth watching. Costa Rica, slowly — the way the best days are remembered."
  ES: "Para este momento no hay itinerario. Solo el agua en los tobillos y un cielo haciendo lo único que vale la pena mirar. Costa Rica, despacio: como se recuerdan los mejores días."

Return ONLY the JSON object."""


def http_json(url, headers, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def caption_for(jpeg_bytes, note="", tags_known=None, learn=""):
    b64 = base64.b64encode(jpeg_bytes).decode()
    system = BRAND_PROMPT
    if learn and learn.strip():
        system += ("\n\n--- WHAT'S RESONATING ON OUR OWN ACCOUNT, BY TODAY'S STANDARDS "
                   "(real but small analytics — a gentle steer, never a formula) ---\n"
                   + learn.strip())
    user_text = "Caption this photo as JSON."
    if note.strip():
        user_text += "\n\nKNOWN FACTS about this photo (true — build the caption around these): " + note.strip()
    if tags_known:
        user_text += ("\n\nTAGGABLE ACCOUNTS (only @mention these exact handles, and only "
                      "if you clearly see that brand/event/person in the photo): "
                      + json.dumps(tags_known))
    payload = {
        "model": MODEL,
        "temperature": 0.7,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ]},
        ],
    }
    headers = {"Authorization": f"Bearer {GH_TOKEN}", "Content-Type": "application/json",
               "Accept": "application/json"}
    res = http_json(MODELS_URL, headers, payload)
    txt = res["choices"][0]["message"]["content"].strip()
    if txt.startswith("```"):
        txt = txt.strip("`")
        txt = txt[txt.find("{"):txt.rfind("}") + 1]
    return json.loads(txt)


# ---------- rendering ----------
def fr(size, wght=440, opsz=80):
    f = ImageFont.truetype(os.path.join(FONTS, "fraunces-latin-standard-normal.ttf"), size)
    try: f.set_variation_by_axes([opsz, wght])
    except Exception: pass
    return f


def dm(size, wght=600, opsz=24):
    f = ImageFont.truetype(os.path.join(FONTS, "dm-sans-latin-standard-normal.ttf"), size)
    try: f.set_variation_by_axes([opsz, wght])
    except Exception: pass
    return f


def render(pil_img, eyebrow, headline, out, bias=0.5):
    im = pil_img.convert("RGB")
    w, h = im.size
    if w >= h:
        left = int((w - h) * 0.5); im = im.crop((left, 0, left + h, h))
    else:
        top = int((h - w) * bias); im = im.crop((0, top, w, top + w))
    im = im.resize((S, S), Image.LANCZOS)
    grad = Image.new("L", (1, S), 0)
    for y in range(S):
        fy = y / S
        bottom = max(0, (fy - 0.34) / 0.66)
        a = int(232 * (bottom ** 1.25))
        topv = max(0, (0.22 - fy) / 0.22) * 140
        grad.putpixel((0, y), min(255, int(a + topv)))
    im = Image.composite(Image.new("RGB", (S, S), (0, 0, 0)), im, grad.resize((S, S)))
    d = ImageDraw.Draw(im)
    M = 84

    def tracked(xy, text, font, fill, tracking=3):
        x, y = xy
        for ch in text:
            for sx, sy in [(0, 2), (2, 1), (1, 2)]:
                d.text((x + sx, y + sy), ch, font=font, fill=(0, 0, 0))
            d.text((x, y), ch, font=font, fill=fill)
            x += d.textlength(ch, font=font) + tracking

    tracked((M, 72), "MY ADVENTURE COSTA RICA", dm(25, 600), BONE)
    hf = fr(74, 440)
    words, lines, cur = headline.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=hf) <= S - 2 * M: cur = t
        else: lines.append(cur); cur = wd
    if cur: lines.append(cur)
    lh = int(74 * 1.16)
    y = S - M - lh * len(lines)
    d.line([(M, y - 74), (M + 46, y - 74)], fill=CLAY_SOFT, width=3)
    tracked((M, y - 56), eyebrow, dm(25, 600), CLAY_SOFT)
    for ln in lines:
        for off in [(2, 3), (3, 2), (1, 4)]:
            d.text((M + off[0], y + off[1]), ln, font=hf, fill=(0, 0, 0))
        d.text((M, y), ln, font=hf, fill=BONE)
        y += lh
    im.save(out, quality=92)


def render_text_slide(body, idx, total, out, kicker=""):
    """An editorial text slide for carousels: sand background, ink Fraunces text."""
    im = Image.new("RGB", (S, S), SAND)
    d = ImageDraw.Draw(im)
    M = 100

    def tracked(xy, text, font, fill, tracking=3):
        x, y = xy
        for ch in text:
            d.text((x, y), ch, font=font, fill=fill)
            x += d.textlength(ch, font=font) + tracking

    tracked((M, 84), "MY ADVENTURE COSTA RICA", dm(24, 600), INK)
    d.line([(M, 132), (M + 46, 132)], fill=CLAY, width=3)
    if kicker:
        tracked((M, 150), kicker.upper(), dm(22, 600), CLAY)

    bf = fr(58, 420)
    words, lines, cur = body.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=bf) <= S - 2 * M: cur = t
        else: lines.append(cur); cur = wd
    if cur: lines.append(cur)
    lh = int(58 * 1.22)
    y = (S - lh * len(lines)) // 2 + 30
    for ln in lines:
        d.text((M, y), ln, font=bf, fill=INK)
        y += lh

    tracked((M, S - 96), f"{idx} / {total}", dm(22, 600), CLAY)
    im.save(out, quality=92)


def render_story(pil_img, eyebrow, headline, out):
    """A branded 9:16 (1080x1920) Story version — photo + wordmark + headline + a feed nudge."""
    W, H = 1080, 1920
    im = pil_img.convert("RGB")
    w, h = im.size
    tr = W / H
    if w / h > tr:                                   # too wide -> crop width
        nw = int(h * tr); left = (w - nw) // 2; im = im.crop((left, 0, left + nw, h))
    else:                                            # too tall -> crop height (bias up to keep subject)
        nh = int(w / tr); top = int((h - nh) * 0.35); im = im.crop((0, top, w, top + nh))
    im = im.resize((W, H), Image.LANCZOS)
    grad = Image.new("L", (1, H), 0)
    for y in range(H):
        fy = y / H
        bottom = max(0, (fy - 0.45) / 0.55)
        a = int(225 * (bottom ** 1.3))
        topv = max(0, (0.16 - fy) / 0.16) * 120
        grad.putpixel((0, y), min(255, int(a + topv)))
    im = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), im, grad.resize((W, H)))
    d = ImageDraw.Draw(im)
    M = 96

    def tracked(xy, text, font, fill, tracking=3):
        x, y = xy
        for ch in text:
            for sx, sy in [(0, 2), (2, 1)]:
                d.text((x + sx, y + sy), ch, font=font, fill=(0, 0, 0))
            d.text((x, y), ch, font=font, fill=fill)
            x += d.textlength(ch, font=font) + tracking

    tracked((M, 150), "MY ADVENTURE COSTA RICA", dm(26, 600), BONE)   # below top safe zone
    hf = fr(82, 440)
    words, lines, cur = headline.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=hf) <= W - 2 * M: cur = t
        else: lines.append(cur); cur = wd
    if cur: lines.append(cur)
    lh = int(82 * 1.15)
    y = 1430 - lh * len(lines)                       # headline block, above bottom safe zone
    d.line([(M, y - 78), (M + 50, y - 78)], fill=CLAY_SOFT, width=3)
    tracked((M, y - 58), eyebrow, dm(26, 600), CLAY_SOFT)
    for ln in lines:
        for off in [(2, 3), (3, 2)]:
            d.text((M + off[0], y + off[1]), ln, font=hf, fill=(0, 0, 0))
        d.text((M, y), ln, font=hf, fill=BONE)
        y += lh
    tracked((M, 1470), "NEW ON THE FEED  →", dm(26, 600), CLAY_SOFT)  # drives to the feed post
    im.save(out, quality=92)


# ---------- meta posting ----------
def meta_post(path, params):
    url = f"https://graph.facebook.com/{CFG.get('graph_version','v23.0')}/{path}"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Graph API {e.code}: {e.read().decode()}")


STATE = os.path.join(HERE, "state.json")


def git(*args, check=True):
    subprocess.run(["git", *args], cwd=HERE, check=check)


def git_setup():
    git("config", "user.name", "auto-poster")
    git("config", "user.email", "actions@github.com")


def commit_push(msg):
    git("add", "-A")
    subprocess.run(["git", "commit", "-m", msg], cwd=HERE)  # ok if nothing to commit
    # Several workflows now push concurrently (the Vercel cron fires a few at once),
    # so a push can be rejected because the remote moved. Rebase on the remote and
    # retry instead of failing the run.
    for attempt in range(6):
        if subprocess.run(["git", "push"], cwd=HERE).returncode == 0:
            return
        print(f"push rejected (attempt {attempt + 1}) — rebasing on remote, retrying")
        subprocess.run(["git", "pull", "--rebase", "--autostash"], cwd=HERE)
        time.sleep(2 + attempt)
    print("commit_push: push still failing after retries")


def summary(md):
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as f:
            f.write(md + "\n")


# ---------- the learner: read our own analytics, steer the next post ----------
INSIGHTS = os.path.join(HERE, "metrics", "insights.json")
POSTS_LOG = os.path.join(HERE, "metrics", "posts.json")
REACH_FLOOR = 50            # below this, an engagement "rate" is statistical noise
HALFLIFE_DAYS = 180        # recent performance is weighted ~2x each 6 months
SAVES_DEAD = 0.05          # if saves are <5% of interactions, stop chasing them
STOP = frozenset("""
the and for with this that your you our are was has have from into out off over
then than back give gives gave take takes when what where here there will would
could should about after before they them their were been being only also some
more most very just like even your yours ours into onto upon while which whose
una unos unas los las del que con por para como más muy sin son est esta este
esto esos esas pero más y de en el la lo un a o se su sus al es ya tu te me mi
costa rica adventure myadventurecostarica www http https com
""".split())


def _load_json(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default


def performance_brief():
    """Read our own Instagram analytics and return a short, honest 'what's
    resonating now' note for the captioner. Era-aware on purpose: it judges a
    post by engagement rate ONLY above a reach floor (so a 2020 post that reached
    2 people can't masquerade as a hit), weights recent performance far more
    heavily (today's algorithm, today's audience), and refuses to optimize for a
    metric the account doesn't actually earn — e.g. saves, which for this account
    are ~zero. Returns "" when there's too little real data to claim anything."""
    import datetime, collections, re as _re
    rows = _load_json(INSIGHTS, [])
    posts = {p.get("id"): p for p in _load_json(POSTS_LOG, []) if p.get("id")}
    today = datetime.date.today()

    def age(r):
        try:
            return (today - datetime.date.fromisoformat(r["date"])).days
        except Exception:
            return None

    elig = [r for r in rows
            if isinstance(r.get("reach"), int) and r["reach"] >= REACH_FLOOR
            and isinstance(r.get("eng_rate"), (int, float)) and age(r) is not None]
    if len(elig) < 4:
        return ""                          # not enough signal to steer honestly

    def wt(r):
        return 0.5 ** (age(r) / HALFLIFE_DAYS)

    tot = lambda k: sum((r.get(k) or 0) for r in elig)
    inter = max(1, tot("interactions"))
    saves_share = tot("saved") / inter
    currency = "reach and shares" if saves_share < SAVES_DEAD else "saves, reach and shares"

    byf = collections.defaultdict(lambda: [0.0, 0.0])      # format -> [Σw·rate, Σw]
    for r in elig:
        b = byf[r.get("format") or "single"]
        b[0] += wt(r) * r["eng_rate"]; b[1] += wt(r)
    fmt_rank = sorted(((f, s / n) for f, (s, n) in byf.items() if n), key=lambda x: -x[1])

    elig.sort(key=lambda r: -(wt(r) * r["eng_rate"]))      # recency-weighted winners
    top = elig[:max(5, len(elig) // 4)]
    words = collections.Counter()
    for r in top:
        cap = (posts.get(r.get("id"), {}).get("caption") or "")
        for tok in _re.findall(r"#?[a-záéíóúñ']{4,}", cap.lower()):
            t = tok.lstrip("#")
            if t not in STOP:
                words[t] += 1
    themes = [w for w, _ in words.most_common(6)]
    recent12 = sum(1 for r in elig if age(r) <= 365)

    lines = [
        "Judged by TODAY'S standards: recent posts are weighted far above old ones, "
        "because the algorithm and the audience that matter are the current ones.",
        f"Signal pool: {len(elig)} posts with real reach ({recent12} in the last "
        "year). Small — treat as a directional nudge, not a rulebook.",
        (f"This account earns {currency}. Saves are ~zero, so never write "
         "'save this' bait — write lines worth SHARING."
         if saves_share < SAVES_DEAD else
         f"This account earns {currency} — keep earning them."),
    ]
    if fmt_rank:
        lines.append("Formats by engagement (recency-weighted): "
                     + ", ".join(f"{f} {rate*100:.1f}%" for f, rate in fmt_rank[:4]) + ".")
    if themes:
        lines.append("Angles that have travelled recently: " + ", ".join(themes) + ".")
    lines.append("So: aim for a share-worthy, reach-friendly caption — one line a "
                 "reader wants to send a friend. Apply the above only where it fits "
                 "the actual photo; never force a formula.")
    return "\n".join(lines)


# ---------- photo similarity: catch same-moment bursts + near-duplicates ----------
BURST = CFG.get("burst_carousel", True)
BURST_SECONDS = int(CFG.get("burst_seconds", 90))     # EXIF gap that counts as one moment
BURST_HASH = int(CFG.get("burst_hash_distance", 8))   # visual closeness for grouping
BURST_MAX = int(CFG.get("burst_max", 6))              # max photos in an auto carousel
DEDUPE = CFG.get("dedupe_posted", True)
DEDUPE_HASH = int(CFG.get("dedupe_hash_distance", 6)) # stricter: skip if ~identical to a past post


def ahash(pil_img):
    """64-bit DIFFERENCE hash (dHash) — compares each pixel to its right neighbour, so
    it captures real structure and tells different scenes apart far better than an
    average hash (which wrongly made every landscape look identical). Name kept for the
    call sites; used only for the strict "is this a literal repost" dedupe check."""
    g = pil_img.convert("L").resize((9, 8), Image.LANCZOS)
    px = list(g.getdata())
    bits = 0
    idx = 0
    for r in range(8):
        base = r * 9
        for c in range(8):
            if px[base + c] > px[base + c + 1]:
                bits |= (1 << idx)
            idx += 1
    return bits


def hamming(a, b):
    return bin(a ^ b).count("1")


def exif_epoch(pil_img):
    """Capture time (epoch seconds) from EXIF, or None."""
    try:
        ex = pil_img.getexif()
        raw = ex.get(36867) or ex.get(306)            # DateTimeOriginal, then DateTime
        if not raw:
            try:
                raw = ex.get_ifd(0x8769).get(36867)
            except Exception:
                raw = None
        if raw:
            return time.mktime(time.strptime(str(raw)[:19], "%Y:%m:%d %H:%M:%S"))
    except Exception:
        pass
    return None


def open_sig(path):
    """(open PIL image, ahash, exif-epoch) for a file, or None on failure."""
    try:
        im = Image.open(path)
        return im, ahash(im), exif_epoch(im)
    except Exception:
        return None


def same_moment(sig_a, sig_b):
    """Same burst = same CAPTURE TIME. Time is the only reliable signal for "same
    moment" — a visual hash alone wrongly fuses different-day landscapes — so grouping
    is time-based, and a photo with no EXIF time is never auto-grouped."""
    _, _, ta = sig_a
    _, _, tb = sig_b
    return ta is not None and tb is not None and abs(ta - tb) <= BURST_SECONDS


# ---------- content plan: hold the four pillars in their planned proportions ----------
PILLAR_PLAN = CFG.get("pillar_plan", {"KNOWLEDGE": 2, "ROUTE": 2, "FOUNDER": 2, "EXPERIENCE": 1})
PLAN_WINDOW = int(CFG.get("plan_window", 14))   # how many recent posts define "the mix"
PLAN_SCAN = int(CFG.get("plan_scan", 8))        # how many candidates to weigh per day


def _recent_pillars():
    try:
        log = json.load(open(POSTS_LOG))
    except Exception:
        return []
    out = []
    for p in reversed(log):                      # newest first
        pil = (p.get("pillar") or "").upper()
        if pil:
            out.append(pil)
        if len(out) >= PLAN_WINDOW:
            break
    return out


def target_pillar():
    """Today's slot = the pillar most UNDER its planned share over recent posts. This
    holds the KNOWLEDGE/ROUTE/FOUNDER/EXPERIENCE mix in the traffic-first proportions and
    caps the EXPERIENCE soft-sell so it never runs hot. Returns an uppercase pillar."""
    plan = {k.upper(): float(v) for k, v in PILLAR_PLAN.items() if v}
    if not plan:
        return "KNOWLEDGE"
    tot = sum(plan.values())
    target_share = {k: v / tot for k, v in plan.items()}
    recent = _recent_pillars()
    n = len(recent) or 1
    actual = {k: recent.count(k) / n for k in plan}

    def deficit(k):
        if k == "EXPERIENCE" and actual.get(k, 0) >= target_share[k]:
            return -9                            # never exceed the sell cap
        return target_share[k] - actual.get(k, 0)

    return max(plan, key=deficit)


def prepare():
    """Pick a photo, caption it, render it, push it, and stage state.json.
    Does NOT post — that's publish()."""
    git_setup()
    # Guard: only one post per day. We run the schedule several times each morning
    # (GitHub skips/delays single crons), so skip if we already posted today.
    lp = os.path.join(HERE, "metrics", "last_posted.txt")
    today = time.strftime("%Y-%m-%d")
    if os.path.exists(lp) and open(lp).read().strip() == today:
        json.dump({"skip": True, "why": "already posted today"}, open(STATE, "w"))
        commit_push("Already posted today [skip ci]")
        summary("### Already posted today\nA post already went out today — skipping.")
        print("Already posted today; skipping."); return
    learn = performance_brief()          # what our own analytics say is working now
    if learn:
        print("Performance brief:\n" + learn)
    candidates = sorted(
        f for f in glob.glob(os.path.join(SRC, "*"))
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".heic", ".heif"))
    )
    if not candidates:
        json.dump({"skip": True, "why": "no photos"}, open(STATE, "w"))
        commit_push("No photos to post [skip ci]")
        summary("### Nothing to post\nNo photos in `source-photos/`. Add some.")
        return

    posted_hashes = []
    if DEDUPE:
        for p in sorted(glob.glob(os.path.join(POSTED, "*")))[-200:]:
            if p.lower().endswith((".jpg", ".jpeg", ".png", ".heic", ".heif")):
                s = open_sig(p)
                if s:
                    posted_hashes.append(s[1])

    target = target_pillar()
    print(f"Content plan — today's target pillar: {target} | recent mix: {_recent_pillars()}")
    chosen = fallback = None
    for src in candidates[:PLAN_SCAN]:
        # Skip a near-duplicate of something already posted — don't repeat near-twins.
        if DEDUPE and posted_hashes:
            cs = open_sig(src)
            if cs and any(hamming(cs[1], ph) <= DEDUPE_HASH for ph in posted_hashes):
                print("Skipping near-duplicate of an already-posted photo:", os.path.basename(src))
                os.replace(src, os.path.join(REJECTED, os.path.basename(src)))
                continue
        note = ""
        note_path = os.path.splitext(src)[0] + ".txt"   # optional companion note: IMG_123.txt
        if os.path.exists(note_path):
            try:
                with open(note_path, encoding="utf-8") as nf:
                    note = nf.read()
            except Exception:
                note = ""
        try:
            img = Image.open(src)
            buf = io.BytesIO()
            pv = img.convert("RGB"); pv.thumbnail((1280, 1280))
            pv.save(buf, format="JPEG", quality=85)
            meta = caption_for(buf.getvalue(), note, TAGS, learn)
        except Exception as e:
            print("Caption error on", os.path.basename(src), "->", e)
            continue
        if not meta.get("post_worthy"):
            print("Not post-worthy:", os.path.basename(src), "-", meta.get("reason"))
            os.replace(src, os.path.join(REJECTED, os.path.basename(src)))
            continue
        if fallback is None:
            fallback = (src, img, meta)                  # first post-worthy = safety net
        if (meta.get("pillar") or "").upper() == target:
            chosen = (src, img, meta)                    # fills today's plan slot — take it
            print(f"Picked for plan pillar {target}: {os.path.basename(src)}")
            break
        # post-worthy but wrong pillar for today — leave it in the queue for a future day
        print(f"Post-worthy but pillar {meta.get('pillar')} ≠ target {target} — keeping:",
              os.path.basename(src))

    if not chosen:
        chosen = fallback                                # no target match found in the scan
    if not chosen:
        json.dump({"skip": True, "why": "none post-worthy"}, open(STATE, "w"))
        commit_push("No post-worthy photo [skip ci]")
        summary("### Nothing to post\nNo post-worthy photo this run.")
        return

    src, img, meta = chosen
    base = os.path.splitext(os.path.basename(src))[0]
    fmt = meta.get("format", "single")
    slides = meta.get("slides") or []

    # --- Burst rule: gather same-moment sibling photos into one carousel set ---
    burst_imgs, burst_files = [], []
    if BURST:
        chosen_sig = open_sig(src) or (img, ahash(img), exif_epoch(img))
        for other in candidates:
            if other == src or len(burst_files) >= BURST_MAX - 1:
                continue
            if not other.lower().endswith((".jpg", ".jpeg", ".png", ".heic", ".heif")):
                continue
            osig = open_sig(other)
            if not osig or not same_moment(chosen_sig, osig):
                continue
            try:                                    # vet so a blurry burst frame can't sneak in
                b = io.BytesIO(); pv = osig[0].convert("RGB"); pv.thumbnail((1280, 1280))
                pv.save(b, format="JPEG", quality=85)
                vm = caption_for(b.getvalue(), "", TAGS, learn)
            except Exception:
                vm = {"post_worthy": False}
            if vm.get("post_worthy"):
                burst_imgs.append(osig[0]); burst_files.append(other)
        if burst_imgs:
            fmt = "carousel"; slides = []           # a photo carousel, not a text-slide one
            print(f"Burst detected — {1 + len(burst_imgs)} photos grouped into a carousel.")

    sources = [os.path.basename(src)] + [os.path.basename(f) for f in burst_files]

    outs = []                                   # slide 1 = the photo
    out1 = os.path.join(RENDERED, f"{base}_1.jpg")
    render(img, meta["eyebrow"], meta["headline"], out1, float(meta.get("crop_bias", 0.5)))
    outs.append(out1)
    if burst_imgs:                              # framed photo siblings (no headline)
        n = 2
        for bi in burst_imgs:
            o = os.path.join(RENDERED, f"{base}_{n}.jpg")
            render(bi, meta["eyebrow"], "", o); outs.append(o); n += 1
    elif fmt == "carousel" and slides:
        cta = (meta.get("cta") or "").strip()
        total = 1 + len(slides[:4]) + (1 if cta else 0)
        n = 2
        for s in slides[:4]:
            o = os.path.join(RENDERED, f"{base}_{n}.jpg")
            render_text_slide(s, n, total, o); outs.append(o); n += 1
        if cta:
            o = os.path.join(RENDERED, f"{base}_{n}.jpg")
            render_text_slide(cta, n, total, o, kicker="The journey"); outs.append(o)

    story_out = None
    if CFG.get("also_story"):
        story_out = os.path.join(RENDERED, f"{base}_story.jpg")
        render_story(img, meta["eyebrow"], meta["headline"], story_out)

    commit_push(f"Render {base} [skip ci]")
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE).decode().strip()

    def raw(p):
        return (f"https://raw.githubusercontent.com/{REPO}/{sha}/"
                f"{urllib.parse.quote(os.path.relpath(p, HERE).replace(os.sep, '/'))}")
    image_urls = [raw(o) for o in outs]
    story_url = raw(story_out) if story_out else None

    hashtags = " ".join("#" + t.lstrip("#") for t in meta.get("hashtags", []))
    mentions = " ".join(m if m.startswith("@") else "@" + m for m in meta.get("tags", []))
    caption = "\n\n".join(p for p in [meta["caption_en"], meta["caption_es"], mentions, hashtags] if p).strip()
    json.dump({"skip": False, "source": os.path.basename(src), "sources": sources, "base": base,
               "image_urls": image_urls, "image_url": image_urls[0],
               "story_url": story_url, "caption": caption,
               "format": fmt, "category": meta.get("category"),
               "pillar": meta.get("pillar")},
              open(STATE, "w"))
    commit_push(f"Stage {base} for review [skip ci]")

    remaining = len([f for f in glob.glob(os.path.join(SRC, "*"))
                     if f.lower().endswith((".jpg", ".jpeg", ".png", ".heic", ".heif"))]) - 1
    low = ("\n\n> ⚠️ **Low on photos** — about %d left. Add more to `source-photos/`."
           % remaining) if remaining <= 7 else ""
    previews = "\n".join(f"![slide {i+1}]({u})" for i, u in enumerate(image_urls))
    if story_url:
        previews += f"\n\n**Story (9:16):**\n![story]({story_url})"
    kind = f"carousel · {len(image_urls)} slides" if len(image_urls) > 1 else "single image"
    kind += " + story" if story_url else ""
    notes_md = ""
    if meta.get("needs_note"):
        notes_md += ("\n\n> 💡 **Tip:** " + (meta.get("note_hint")
                     or "this looks like a real event/result — next time add a note with the facts."))
    if meta.get("tag_suggestions"):
        notes_md += ("\n\n> 🔖 **Spotted, could tag** (add handles to `tags.json`): "
                     + ", ".join(meta["tag_suggestions"]))
    learn_md = ("\n\n**What your data says (today's standards):**\n\n> "
                + learn.replace("\n", "\n> ")) if learn else ""
    summary(f"## Today's post — review before it goes live\n\n_{kind}_\n\n{previews}\n\n"
            f"**Caption:**\n\n{caption}\n\n"
            f"Approve the **publish** job to send it to Instagram"
            + (" and Facebook." if "fb" in CFG.get("targets", []) else ".")
            + low + notes_md + learn_md)
    print("Prepared:", base, f"({kind}) | photos remaining:", remaining)


def publish():
    """Read staged state.json and actually post it."""
    if not os.path.exists(STATE):
        print("No state.json — nothing staged."); return
    st = json.load(open(STATE))
    if st.get("skip"):
        print("Nothing staged to publish."); return
    if not META_TOKEN:
        sys.exit("Missing META_ACCESS_TOKEN secret.")
    git_setup()
    caption = st["caption"]
    image_urls = st.get("image_urls") or [st["image_url"]]
    targets = CFG.get("targets", ["ig", "fb"])
    if "ig" in targets:
        ig = CFG["ig_user_id"]
        if len(image_urls) > 1:                      # carousel
            child_ids = []
            for u in image_urls[:10]:                # IG carousel max 10
                c = meta_post(f"{ig}/media",
                              {"image_url": u, "is_carousel_item": "true", "access_token": META_TOKEN})
                child_ids.append(c["id"]); time.sleep(3)
            car = meta_post(f"{ig}/media",
                            {"media_type": "CAROUSEL", "children": ",".join(child_ids),
                             "caption": caption, "access_token": META_TOKEN})
            time.sleep(8)
            pub = meta_post(f"{ig}/media_publish",
                            {"creation_id": car["id"], "access_token": META_TOKEN})
            print("Instagram carousel OK:", pub.get("id"))
        else:                                        # single image
            cont = meta_post(f"{ig}/media",
                             {"image_url": image_urls[0], "caption": caption, "access_token": META_TOKEN})
            time.sleep(8)
            pub = meta_post(f"{ig}/media_publish",
                            {"creation_id": cont["id"], "access_token": META_TOKEN})
            print("Instagram OK:", pub.get("id"))
        story_id = None
        if st.get("story_url"):                      # branded vertical Story (drives feed reach)
            try:
                sc = meta_post(f"{ig}/media",
                               {"image_url": st["story_url"], "media_type": "STORIES",
                                "access_token": META_TOKEN})
                time.sleep(6)
                sp = meta_post(f"{ig}/media_publish",
                               {"creation_id": sc["id"], "access_token": META_TOKEN})
                story_id = sp.get("id")
                print("Instagram Story OK:", story_id)
            except Exception as e:
                print("Story skipped:", e)
        # log the feed post (and the Story) so insights can be pulled later
        try:
            mdir = os.path.join(HERE, "metrics"); os.makedirs(mdir, exist_ok=True)
            pj = os.path.join(mdir, "posts.json")
            posts = json.load(open(pj)) if os.path.exists(pj) else []
            today = time.strftime("%Y-%m-%d")
            now = time.strftime("%Y-%m-%dT%H:%M:%S")
            posts.append({"id": pub.get("id"), "date": today, "ts": now, "base": st["base"],
                          "format": st.get("format") or ("carousel" if len(image_urls) > 1 else "single"),
                          "category": st.get("category"), "pillar": st.get("pillar"),
                          "caption": caption[:120]})
            if story_id:                              # Story insights expire in 24h — log it now
                posts.append({"id": story_id, "date": today, "ts": now, "base": st["base"] + "-story",
                              "format": "story", "category": st.get("category"),
                              "pillar": st.get("pillar"), "caption": caption[:120]})
            json.dump(posts, open(pj, "w"), indent=1)
        except Exception as e:
            print("metrics log skipped:", e)
    if "fb" in targets:
        try:
            res = meta_post(f"{CFG['page_id']}/photos",
                            {"url": image_urls[0], "message": caption, "access_token": META_TOKEN})
            print("Facebook OK:", res.get("post_id") or res.get("id"))
        except Exception as e:
            print("Facebook skipped (needs pages_manage_posts):", e)
        story_url = st.get("story_url")              # cross-post the same 9:16 image as a FB Story
        if story_url:
            try:
                up = meta_post(f"{CFG['page_id']}/photos",
                               {"url": story_url, "published": "false", "access_token": META_TOKEN})
                meta_post(f"{CFG['page_id']}/photo_stories",
                          {"photo_id": up["id"], "access_token": META_TOKEN})
                print("Facebook Story OK")
            except Exception as e:
                print("Facebook Story skipped:", e)

    for sname in (st.get("sources") or [st.get("source")]):   # archive every burst photo used
        if not sname:
            continue
        sp = os.path.join(SRC, sname)
        if os.path.exists(sp):
            os.replace(sp, os.path.join(POSTED, sname))
        note_p = os.path.join(SRC, os.path.splitext(sname)[0] + ".txt")  # its companion note
        if os.path.exists(note_p):
            os.remove(note_p)
    with open(os.path.join(POSTED, st["base"] + ".txt"), "w", encoding="utf-8") as f:
        f.write(caption)
    if os.path.exists(STATE):
        os.remove(STATE)
    mdir = os.path.join(HERE, "metrics"); os.makedirs(mdir, exist_ok=True)
    open(os.path.join(mdir, "last_posted.txt"), "w").write(time.strftime("%Y-%m-%d"))
    commit_push(f"Posted {st['base']} [skip ci]")
    print("Done.")


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    if phase == "prepare":
        prepare()
    elif phase == "publish":
        publish()
    else:  # "all" = no approval gate
        prepare()
        publish()
