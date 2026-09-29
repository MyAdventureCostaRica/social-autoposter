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
import base64, glob, io, json, os, re, subprocess, sys, time, urllib.parse, urllib.request, urllib.error
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

# Upstash Redis (PRIVATE) — the pending post awaiting approval + the learning log live
# here, never in the public repo. Same DB the responder uses.
UPSTASH_URL = (os.environ.get("UPSTASH_REDIS_REST_URL") or "").rstrip("/")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
WA_PHONE = os.environ.get("WHATSAPP_PHONE")          # CallMeBot WhatsApp ping (optional)
WA_KEY = os.environ.get("WHATSAPP_APIKEY")
DASHBOARD_URL = CFG.get("dashboard_url", "https://social-autoposter-five.vercel.app/")


def _redis(cmd):
    req = urllib.request.Request(
        UPSTASH_URL, data=json.dumps(cmd).encode("utf-8"),
        headers={"Authorization": f"Bearer {UPSTASH_TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def rget(key, default=None):
    if not (UPSTASH_URL and UPSTASH_TOKEN):
        return default
    try:
        res = _redis(["GET", key]).get("result")
        return json.loads(res) if res else default
    except Exception as e:
        print(f"redis get {key} failed:", e); return default


def rset(key, obj):
    if not (UPSTASH_URL and UPSTASH_TOKEN):
        print("Upstash not configured — skipping write of", key); return
    try:
        _redis(["SET", key, json.dumps(obj, ensure_ascii=False)])
    except Exception as e:
        print(f"redis set {key} failed:", e)


def rdel(key):
    try:
        _redis(["DEL", key])
    except Exception as e:
        print(f"redis del {key} failed:", e)


def wa_notify(text):
    """Owner ping — WhatsApp (CallMeBot) + ntfy. The implementation lives in notify.py
    (standard library only) so the workflows' failure-alert step can use the very same
    code: `python notify.py "..."`. See notify.py for the CallMeBot 200-with-error trap
    that hid a 16-day outage."""
    try:
        import notify
        return notify.send(text)
    except Exception as e:
        print("notify failed:", e)
        return False


def strip_location_metadata(keep=()):
    """Public repo + phone photos = GPS coordinates for anyone who clones. The Sep 10 2026
    audit found 111 of 125 source photos carried them (42 within 15 km of home). Published
    renders were always clean (Pillow drops EXIF on save); this cleans the ORIGINALS that
    live in git — source-photos/ and posted/:
      • JPEG/PNG: the GPS block is removed, everything else in EXIF stays (capture time
        drives burst detection, orientation keeps photos upright, camera make is harmless)
      • HEIC: converted to a clean JPEG (Pillow can't rewrite HEIC), longest side capped at
        3000 px like the dashboard uploader already does — plenty for 1080 px renders
      • DNG raws: deleted — the pipeline never reads them, they were pure weight + exposure
    `keep` = file names that are referenced by a staged/pending post and must not change.
    Runs at the start of every prepare(); after the first pass it finds nothing."""
    GPS_IFD, ORIENT, EXIF_IFD, INTEROP = 0x8825, 0x0112, 0x8769, 0xA005
    changed, removed = [], []
    for d in (SRC, POSTED):
        for path in sorted(glob.glob(os.path.join(d, "*"))):
            name = os.path.basename(path); low = name.lower()
            if os.path.isdir(path) or name in keep:
                continue
            if low.endswith(".dng"):
                os.remove(path); removed.append(name); continue
            if not low.endswith((".jpg", ".jpeg", ".png", ".heic", ".heif")):
                continue
            try:
                im = Image.open(path)
                ex = im.getexif()
                if GPS_IFD not in ex and not low.endswith((".heic", ".heif")):
                    continue                                   # nothing to strip
                im.load()
                for tag in (EXIF_IFD, GPS_IFD, INTEROP):       # load sub-IFDs so tobytes() keeps them
                    try: ex.get_ifd(tag)
                    except Exception: pass
                if GPS_IFD in ex:
                    del ex[GPS_IFD]
                if low.endswith((".heic", ".heif")):
                    out = os.path.splitext(path)[0] + ".jpg"
                    if os.path.exists(out):                    # a same-named .jpg twin exists
                        out = os.path.splitext(path)[0] + "-heic.jpg"
                    ex[ORIENT] = 1                             # libheif already applied the rotation
                    rgb = im.convert("RGB"); rgb.thumbnail((3000, 3000))
                    rgb.save(out, "JPEG", quality=92, exif=ex.tobytes())
                    os.remove(path); changed.append(f"{name} -> {os.path.basename(out)}")
                elif low.endswith(".png"):
                    im.save(path, "PNG"); changed.append(name)
                else:
                    im.save(path, "JPEG", quality="keep", exif=ex.tobytes()); changed.append(name)
            except Exception as e:
                print("metadata strip skipped for", name, "->", e)
    if changed or removed:
        print(f"Location metadata stripped from {len(changed)} photo(s); {len(removed)} DNG raw(s) deleted.")
        for c in changed[:20]: print("   ", c)
        commit_push(f"Strip location metadata from {len(changed)} photos"
                    + (f", drop {len(removed)} unused DNG raws" if removed else "") + " [skip ci]")
    return changed, removed


# GitHub Models retired 2026-07-30 (410 Gone) -> Gemini OpenAI-compatible endpoint
# (free tier, vision). Endpoint/model/key are env- and config-overridable.
def cr_today():
    """Today's date in Costa Rica (UTC-6, no DST). The runner's clock is UTC, so an
    evening post stamped with UTC would land on TOMORROW's date and silently cancel
    tomorrow's post ("Already posted today"). Owner's rule (Sep 28 2026): a missed post
    goes out whenever the system can, never left for the next day, and the next day
    still gets its own post."""
    import datetime as _dt
    return (_dt.datetime.utcnow() - _dt.timedelta(hours=6)).strftime("%Y-%m-%d")


MODELS_URL = os.environ.get("CAPTION_API_URL", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")
MODEL = CFG.get("caption_model", "gemini-3.7-flash")
# Google retires/renames models often (2.5-flash died with a 404 within weeks of the
# migration) and free-tier capacity comes and goes (503s). Every caption call walks
# this chain — primary first, then fallbacks — retrying transient errors once each.
CAPTION_MODELS = [MODEL] + [m for m in CFG.get(
    "caption_model_fallbacks", ["gemini-3.5-flash", "gemini-3.1-flash-lite"]) if m != MODEL]
CAPTION_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("CAPTION_API_KEY") or GH_TOKEN

# Which caption languages actually get POSTED. Instagram reads caption language as an
# audience signal, so English-only keeps the feed pointed at international buyers rather
# than at a Costa Rican audience. Both captions are still written by the model; this only
# controls what ships. Set "caption_langs": ["en","es"] in config.json to go bilingual again.
CAPTION_LANGS = [str(l).lower().strip() for l in CFG.get("caption_langs", ["en"])]

def caption_body(meta):
    """Caption text in the configured languages, in order. Returns a list of paragraphs."""
    out = []
    for lang in CAPTION_LANGS:
        txt = (meta.get("caption_" + lang) or "").strip()
        if txt:
            out.append(txt)
    return out

# Accounts we may @mention. name (lowercase) -> exact handle. Filled in over time.
TAGS = {}
_tagfile = os.path.join(HERE, "tags.json")
if os.path.exists(_tagfile):
    try:
        TAGS = json.load(open(_tagfile)).get("handles", {})
    except Exception:
        TAGS = {}

BRAND_PROMPT = r"""You write Instagram captions for My Adventure Costa Rica, a founder-led endurance travel company in Costa Rica (trail running, cycling, hiking, water sports, multi-sport journeys, bespoke private journeys and school programs) whose guests come from abroad. You write in English, as a guide who was there, to one future guest. Plain and warm. Never hype, never exclamation marks, never jokes. The subject is the place, the guest or a decision: never the company, never praise, never the person behind the camera.

== TRUTH ==
Use only: (1) KNOWN FACTS in the user message (the owner's note for this photo), (2) the PUBLISHED FACTS below, (3) what any experienced guide knows is universally true (leave a gate as you found it; wet steel is slippery; cloud forest forms where warm, wet air is pushed up a mountain and cools). Nothing else. No number, species, place name, cause or claim from anywhere else. If the note does not say where the photo was taken, never say or imply where. Never invent operational facts (distance, elevation, difficulty, tides, dates, prices).

== THE PHOTO IS EVIDENCE, NOT THE SUBJECT ==
Never list what is visible. A stranger who has never been to Costa Rica could write that from the picture alone, and it is the surest sign of machine writing. Use at most ONE visible thing, and only as evidence for something the photo cannot show: what to do here, what it costs to be here, what happened before or after, what a guest needs to know.

== PICK ONE ANGLE (one per caption, never two) ==
- A decision: what to do at this exact spot and why (ride it or walk it, fill bottles here or not, start before light).
- A rule of the place: one thing that is true here and what it changes for a runner, rider or walker.
- A moment, only from KNOWN FACTS: when, where, who, what happened.
- The cost: the alarm, the climb, the rain, the heat, the wait.
- Outside the frame: what came before this picture, or after it.
- A question a future guest would ask, answered plainly.
Do not repeat the angle, the opening words or the key nouns of the RECENT CAPTIONS listed in the user message.

== STRUCTURE ==
Line 1 carries the whole idea in 125 characters or fewer: a fact, a decision, a moment or a plain admission. Then 1 to 3 short sentences that pay it off. Stop. One beat per line, with a line break between beats; no long paragraphs. Numbers as numerals (9 days, 25 km, 3,000 m), never spelled out.

== LENGTH ==
Short: 8 to 30 words. Long: 60 to 150 words, only when KNOWN FACTS or PUBLISHED FACTS carry a story or a fact worth teaching. Nothing in between. Never pad.

== POINT OF VIEW ==
Default to "you". "We" only when stating PUBLISHED FACTS on an EXPERIENCE post. "I" only when KNOWN FACTS hold the founder's own experience, with the specific result first. Never "I" for credentials, years of experience or general wisdom.

== ENDINGS ==
Stop on the last concrete thing. About 1 caption in 4: one real question about the reader's own choice or experience. About 1 in 8: one line inviting them to send it to the friend who would do this with them. Never a moral, a summary or a saying.

== SCENERY WITH NO NOTE ==
Keep it short (8 to 30 words): one rule of the place, or one PUBLISHED FACT the image supports.

== THE FOUNDER IN THE PHOTO ==
Write about the task or the moment, not about him. With a note: first person, the specifics, what changed afterwards. Without a note: no "I", one factual line. Never imply a certification or a title he does not hold.

== SELLING (EXPERIENCE posts only, about 1 in 7) ==
One or two lines of PUBLISHED FACTS (route, days, group size, what a day holds), then "Details in the bio." No selling adjectives, no urgency, no prices, no discounts, no dates. No other post names the company.

== PUBLISHED FACTS (the only product facts you may state) ==
- The Trail Running Expedition: 9 days, from the Cordillera de Talamanca (3,000 m) down the Pacific slope through the Dota Valley cloud forest to the central Pacific coast, then south to the Osa Peninsula. 6 to 8 athletes. About 93 km of running and 4,529 m of climbing. Day 2 crosses nine summits above 3,000 m; Day 4 is a 25 km self-supported descent from Providencia to San Isidro; Day 5 is a coastal 10K at Manuel Antonio; Day 6 crosses the Sierpe-Térraba mangroves by boat to Drake Bay; Day 7 runs singletrack on the Osa.
- The Gravel Expedition: 9 days, coast to coast across the Nicoya Peninsula from Paquera to Tamarindo, about 356 km, from three bases: Santa Teresa, Nosara and Tamarindo. 6 to 8 athletes. Day 1 is the welcome dinner in San José; riding starts on Day 2.
- Both are led in person by the founder, Esteban Umaña. Departure dates and prices live on the website: write "Details in the bio", never a date or a price.
- Also offered: hiking, wildlife, water sports (rafting, kayaking, surfing), multi-sport and adventure journeys, bespoke private journeys, and school programs. Caption to what the photo shows: a surfer is surfing, a raft is rafting, a road cyclist is road cycling. Adventure racing is its own sport: never call it a triathlon, XTERRA, duathlon or stage race.
- Regions (name one ONLY if it is unmistakable in the photo or given in KNOWN FACTS; never swap them): the Cordillera de Talamanca and the Dota Valley, the Cerro de la Muerte massif, Manuel Antonio, the Osa Peninsula and Drake Bay, the Nicoya Peninsula (Santa Teresa, Nosara, Tamarindo), Monteverde. Mountains, cloud forest and coast are not interchangeable.

== BANNED (ban the pattern, not just the exact words; if any appears, rewrite before returning) ==
- Listing what is in the frame: "framed by", "a horizon of", "lush", lists of colours, textures or plants.
- Definition or setting openers: "X means…", "X is about…", "In the [region]…", "Out here", "Up here", "nestled", "in the heart of".
- Sayings about pace, rhythm, terrain, mountains or maps ("the terrain sets the pace", "the map is a suggestion").
- "Not this, but that" in any wording: "not X, it's Y", "no longer X; it is Y", "not just… but".
- Lists of three: three adjectives, three nouns, three clauses, a three-beat ending.
- Morals and lessons: "when you slow down…", "you learn quickly…", "reveals itself", "reminds you", "teaches you", "invites you".
- Tone words used as content: quiet, stillness, silence, slow, unhurried, serene, peaceful, calm.
- Invented senses and absolutes: sounds, smells or temperatures not in the note; "the only", "nothing but", "always", "every".
- Empty praise: breathtaking, stunning, vibrant, magical, iconic, hidden gem, paradise, pristine, epic, tapestry, symphony, testament, "journey" as a metaphor.
- Personified nature (forests watching, mountains deciding, roads asking).
- Self-praise or credentials ("personally tested", "years of experience", "we design every route"), corporate voice ("at My Adventure Costa Rica we believe").
- Em dashes, semicolons, emoji, exclamation marks, more than one question, hashtags inside the text.
- Spanish of any kind. ENGLISH ONLY: the account posts no Spanish (a Spanish-caption era grew a Costa Rican audience that does not buy these journeys, and Instagram reads caption language as an audience signal).

== BEFORE YOU RETURN, REWRITE IF ==
- a stranger could have written it from the photo alone;
- line 1 holds no fact, decision or moment;
- a name, number or cause is not in KNOWN FACTS or PUBLISHED FACTS;
- any sentence describes what is visible;
- a banned pattern appears, in any wording;
- a future guest would not send it to a friend.

== PHOTOS OF EVENTS (bibs, podiums, finish lines, medals, sponsor logos) ==
A bib means a real event; a podium or medal means a result; logos mean partners were present. Use these ONLY with KNOWN FACTS. Never invent the event, distance, time or placing. Without facts, write about the moment without specifics and set needs_note to true. Tag only handles from the taggable list, and only the event and real partners.

Look at the photo, then return STRICT JSON (only the object, no prose, no code fences) with:
- "post_worthy": boolean. false if blurry, cluttered (power lines, signage, parked cars, trash, busy backgrounds), a screenshot, a duplicate-feeling snapshot, or below the bar of a premium feed.
- "reason": one short sentence explaining the worthiness call.
- "pillar": one of "KNOWLEDGE" (a rule of the place, or a guest's question answered), "FOUNDER" (only when KNOWN FACTS hold the founder's own story), "ROUTE" (a decision, a cost, or outside-the-frame on a trail, road or river), "EXPERIENCE" (the selling post, about 1 in 7, only when the photo shows something a published journey actually holds).
- "category": the broad discipline, one of "RUNNING","CYCLING","WATER SPORTS","MULTI-SPORT","BESPOKE JOURNEYS","SCHOOL PROGRAMS","COSTA RICA".
- "eyebrow": the most accurate label for what the photo shows + " · COSTA RICA", e.g. "TRAIL RUNNING · COSTA RICA", "GRAVEL · COSTA RICA", "RAFTING · COSTA RICA", "SEA KAYAKING · COSTA RICA"; for a landscape with no activity, "COSTA RICA · SLOWLY". Match the activity actually shown.
- "headline": 3 to 7 words printed on the image: a true fact, the decision, or the moment. Never a tone word, never scenery, never a saying.
- "caption_en": the caption, English only, per every rule above, with line breaks between beats.
- "hashtags": array of 3 to 5 lowercase tags (no #). Always "myadventurecostarica". The rest specific to the activity, the region when it is known, and international travel intent (trailrunning, gravelcycling, costaricatravel, adventuretravel). Never generic ones (nature, love, travel).
- "crop_bias": 0.0 to 1.0 vertical crop focus (0.3 if the subject or horizon sits high, 0.6 to keep people or foreground at the bottom, 0.5 default).
- "format": "single" or "carousel". "carousel" when there are 2 to 4 real beats worth their own slide (a decision with its reasons, a rule and what it changes, a published journey's day). "single" when one line says it all.
- "slides": carousel ONLY: an array of 2 to 4 lines, one per slide, each 18 words or fewer, each a fact, a decision or a step; never scenery, never a moral. Slide 1 is always the photo, so these follow it.
- "cta": carousel ONLY, and ONLY when pillar is EXPERIENCE: one closing line of published fact ("9 days, 6 to 8 athletes. Details in the bio."). Otherwise "".
- "tags": array of exact Instagram handles to @mention, ONLY from the TAGGABLE ACCOUNTS list in the user message, and ONLY when that brand, event or person is clearly in the photo. Empty array if none. Never invent a handle.
- "tag_suggestions": array of brand, event or person NAMES visible in the photo (sponsor logos, race names on bibs or banners) that are NOT in the taggable list, so the owner can add them later. Names only, no @.
- "needs_note": boolean. true if the photo shows a real event or achievement (a bib, a podium, a finish line, a medal, a timing arch) but no KNOWN FACTS were given.
- "note_hint": short string. If needs_note is true, what to add (e.g. "Race bib visible: add the event name and your result").

Return ONLY the JSON object."""


def http_json(url, headers, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


# ---------- the voice guard (Sep 29 2026) ----------
# The owner's verdict on the old captions: "too robotic, it has no essence … describing
# everything on the picture like grass, and metal bridges". Research on the accounts that
# do this well (Pelorus, Eleven Experience, Kilian Jornet, Lael Wilcox, Awasi, Run the Alps)
# says: the photo is evidence, not the subject; one angle; a first line that carries the
# idea; and a list of patterns that mark machine writing. The brief bans them; this check
# catches the ones a regex can see and asks for ONE rewrite before the caption is used.
_BANNED = [
    ("a list of what is in the frame",
     r"\b(?:framed by|a horizon of|in the (?:foreground|background)|dotted with|carpeted (?:in|with)|"
     r"lush|verdant|rolling hills)\b"),
    ("a definition or setting opener",
     r"^\W*(?:(?:in|at|up|out) (?:the heart of|here)|out here|up here|nestled|deep in the|high in the|"
     r"[A-Za-z' ]{2,40}?\b(?:means|is about|is all about)\b)"),
    ("a saying about pace, rhythm, terrain or the map",
     r"\b(?:pace|rhythm|the map is|terrain (?:sets|dictates|decides)|the mountain (?:sets|decides|dictates))\b"),
    ("'not this, but that'",
     r"\b(?:not (?:just|only|merely)\b[^.\n]{1,60}\bbut\b|"
     r"(?:not|isn'?t|isn’t|no longer|never)\b[^.\n,;:]{1,60}[,;:]\s*(?:but|it'?s|it’s|it is)\b)"),
    ("a moral or a lesson",
     r"\b(?:reminds? (?:you|us)|reveals itself|you learn (?:quickly|fast|that)|when you slow down|"
     r"teaches you|invites you|strips (?:everything|it all) away|there'?s a moment when|"
     r"something [a-z]+ about|a kind of)\b"),
    ("a tone word used as content",
     r"\b(?:quiet(?:ly|ness)?|stillness|silen(?:ce|t)|unhurried|serene(?:ly)?|serenity|peaceful(?:ly)?|"
     r"tranquil(?:ity)?|hush(?:ed)?)\b"),
    ("an invented sense or an absolute",
     r"\b(?:the only (?:sound|sounds|thing|things|noise|company)|nothing but|the loudest thing)\b"),
    ("empty praise",
     r"\b(?:breathtaking|stunning|vibrant|magical|iconic|hidden gem|paradise|pristine|majestic|"
     r"awe-inspiring|unforgettable|epic|tapestry|symphony|testament)\b"),
    ("self-praise or credentials",
     r"\b(?:personally tested|years of (?:experience|scouting|guiding)|I have spent years|"
     r"every kilomet(?:re|er)|we design every|we believe)\b"),
    ("an em dash or a semicolon", r"[—–;]"),
    ("an exclamation mark", r"!"),
    ("an emoji", r"[\U0001F300-\U0001FAFF☀-➿]"),
]


def caption_violations(meta, note=""):
    """Names of the banned patterns present in a caption (and its headline, slides and
    cta). Empty list = clean. `note` empty + first person = a made-up founder story."""
    parts = [meta.get("caption_en") or "", meta.get("headline") or "", meta.get("cta") or ""]
    parts += list(meta.get("slides") or [])
    text = "\n".join(p for p in parts if isinstance(p, str))
    found = []
    for name, rx in _BANNED:
        if re.search(rx, text, flags=re.I | re.M):
            found.append(name)
    if text.count("?") > 1:
        found.append("more than one question")
    if not (note or "").strip() and re.search(r"\b(?:I|I'?m|I'?ve|I'?d|my|me|mine)\b", text):
        found.append("first person with no note to back it")
    cap = meta.get("caption_en") or ""
    first = re.split(r"(?<=[.?])\s|\n", cap.strip(), maxsplit=1)[0]
    if len(first) > 125:
        found.append("first sentence longer than 125 characters (it must carry the idea on its own)")
    words = len(re.findall(r"[A-Za-z0-9'’]+", cap))
    if cap and words < 8:
        found.append(f"too short ({words} words)")
    if words > 170:
        found.append(f"too long ({words} words: 150 is the ceiling)")
    if re.search(r"[¿¡]|\b(?:el|la|los|las|una|para|con|que)\b [a-záéíóú]", cap, flags=re.I):
        found.append("Spanish")
    return found


def recent_captions(n=10):
    """The last n feed captions' opening lines (from metrics/posts.json), so the model can
    avoid repeating an angle, an opener or the same nouns day after day."""
    try:
        posts = json.load(open(POSTS_LOG))
    except Exception:
        return []
    out = []
    for p in reversed(posts):
        if str(p.get("base", "")).endswith("-story") or p.get("format") == "story":
            continue
        c = (p.get("caption") or "").strip().replace("\n", " ")
        if c:
            out.append(c[:120])
        if len(out) >= n:
            break
    return out


def _caption_call(system, user_text, b64):
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
    headers = {"Authorization": f"Bearer {CAPTION_KEY}", "Content-Type": "application/json",
               "Accept": "application/json"}
    errs = []
    for m in CAPTION_MODELS:
        payload["model"] = m
        for attempt in (1, 2):
            try:
                res = http_json(MODELS_URL, headers, payload)
                if m != MODEL:
                    print("caption model fallback ->", m)
                txt = res["choices"][0]["message"]["content"].strip()
                if txt.startswith("```"):
                    txt = txt.strip("`")
                    txt = txt[txt.find("{"):txt.rfind("}") + 1]
                return json.loads(txt)
            except urllib.error.HTTPError as e:
                errs.append(f"{m}: HTTP {e.code}")
                if e.code == 404:
                    break                       # model gone — next model immediately
                if e.code in (429, 500, 502, 503, 504) and attempt == 1:
                    time.sleep(6); continue     # transient — one retry, then next model
                break
            except Exception as e:              # bad JSON, timeout, etc. — try next model
                errs.append(f"{m}: {e}")
                break
    raise RuntimeError("all caption models failed: " + "; ".join(errs))


def caption_for(jpeg_bytes, note="", tags_known=None, learn="", hint=""):
    b64 = base64.b64encode(jpeg_bytes).decode()
    system = BRAND_PROMPT
    if learn and learn.strip():
        system += ("\n\n--- WHAT'S RESONATING ON OUR OWN ACCOUNT, BY TODAY'S STANDARDS "
                   "(real but small analytics — a gentle steer, never a formula) ---\n"
                   + learn.strip())
    user_text = "Caption this photo as JSON."
    if note.strip():
        user_text += "\n\nKNOWN FACTS about this photo (true — build the caption around these): " + note.strip()
    else:
        user_text += ("\n\nKNOWN FACTS: none. So: no first person, no place name, no event, "
                      "no number that is not in PUBLISHED FACTS.")
    recent = recent_captions()
    if recent:
        user_text += ("\n\nRECENT CAPTIONS on this account (do not repeat their angle, opening "
                      "words or key nouns):\n" + "\n".join("- " + c for c in recent))
    if tags_known:
        user_text += ("\n\nTAGGABLE ACCOUNTS (only @mention these exact handles, and only "
                      "if you clearly see that brand/event/person in the photo): "
                      + json.dumps(tags_known))
    if hint:
        user_text += "\n\nFORMAT NOTE: " + hint
    meta = _caption_call(system, user_text, b64)
    if not isinstance(meta, dict):
        raise RuntimeError("caption model returned no JSON object")
    bad = caption_violations(meta, note) if meta.get("post_worthy") else []
    if bad:
        # One rewrite, with the exact reasons. The second answer wins only if it is cleaner.
        print("caption check failed:", "; ".join(bad), "— asking for a rewrite")
        redo = (user_text + "\n\nYOUR PREVIOUS CAPTION BROKE THESE RULES: " + "; ".join(bad)
                + ". Write the caption, headline and slides again from scratch for the same "
                  "photo and the same facts, fixing every one of them. Previous caption: \""
                + (meta.get("caption_en") or "")[:500] + "\"")
        try:
            meta2 = _caption_call(system, redo, b64)
            bad2 = caption_violations(meta2, note) if isinstance(meta2, dict) else bad
            if isinstance(meta2, dict) and len(bad2) <= len(bad):
                meta, bad = meta2, bad2
        except Exception as e:
            print("rewrite call failed, keeping the first caption:", e)
        if bad:
            print("caption still flags:", "; ".join(bad))
    meta["_violations"] = bad
    return meta


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


def render_clean(pil_img, out, bias=0.5):
    """The luxury default: a clean square crop of the photograph — no gradient,
    no wordmark, no headline. The words live in the caption, not on the image."""
    im = pil_img.convert("RGB")
    w, h = im.size
    if w >= h:
        left = int((w - h) * 0.5); im = im.crop((left, 0, left + h, h))
    else:
        top = int((h - w) * bias); im = im.crop((0, top, w, top + w))
    im.resize((S, S), Image.LANCZOS).save(out, quality=92)


def render_story_clean(pil_img, out):
    """Clean 9:16 crop for Stories — photo only, no gradient or text."""
    W, H = 1080, 1920
    im = pil_img.convert("RGB")
    w, h = im.size
    tr = W / H
    if w / h > tr:
        nw = int(h * tr); left = (w - nw) // 2; im = im.crop((left, 0, left + nw, h))
    else:
        nh = int(w / tr); top = int((h - nh) * 0.35); im = im.crop((0, top, w, top + nh))
    im.resize((W, H), Image.LANCZOS).save(out, quality=92)


def wants_title_card(note, meta):
    """Text-on-image is OFF by default. It turns on only when a post is deliberately
    flagged as a title card — reserved for the rare, special moment."""
    if os.environ.get("FORCE_TITLE") == "1":
        return True
    if CFG.get("burn_text"):                      # global opt-in (config.json) — default off
        return True
    n = (note or "").strip().lower()
    if n.startswith("!title") or "[title" in n:   # per-photo opt-in via companion .txt note
        return True
    if meta.get("title_card") is True:
        return True
    return False


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
HALFLIFE_DAYS = 90         # recent performance is weighted ~2x each 3 months (June 2026 review)
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


def ingest_image(url, note=""):
    """Prepare user-uploaded image(s) (Cloudinary URLs): caption, clean-render, and
    stage as a pending post for approval. SEVERAL urls uploaded together become ONE
    carousel — the first photo is the cover (and the story), the rest are slides."""
    urls = url if isinstance(url, list) else [url]
    urls = [u for u in urls if u][:10]                     # Instagram's carousel cap
    print(f"Ingesting {len(urls)} uploaded image(s):", (urls[0] or "")[:80])
    imgs = []
    for u in urls:
        data = urllib.request.urlopen(u, timeout=120).read()
        imgs.append(Image.open(io.BytesIO(data)))
    img = imgs[0]                                          # cover drives caption + story
    base = "upload-" + time.strftime("%Y%m%d-%H%M%S")
    buf = io.BytesIO(); pv = img.convert("RGB"); pv.thumbnail((1280, 1280)); pv.save(buf, "JPEG", quality=85)
    learn = performance_brief()
    extra = (" (This will be a photo CAROUSEL of "
             + str(len(imgs)) + " pictures the owner chose together — one moment/story.)") if len(imgs) > 1 else ""
    meta = caption_for(buf.getvalue(), (note or "") + extra, TAGS, learn)
    burn = wants_title_card(note, meta)
    bias = float(meta.get("crop_bias", 0.5))
    outs = []
    out1 = os.path.join(RENDERED, f"{base}_1.jpg")
    if burn: render(img, meta.get("eyebrow", ""), meta.get("headline", ""), out1, bias)
    else:    render_clean(img, out1, bias)
    outs.append(out1)
    for i, sib in enumerate(imgs[1:], start=2):            # slides: clean frames, no text
        o = os.path.join(RENDERED, f"{base}_{i}.jpg")
        render_clean(sib, o, 0.5)
        outs.append(o)
    story_out = None
    if CFG.get("also_story"):
        story_out = os.path.join(RENDERED, f"{base}_story.jpg")
        if burn: render_story(img, meta.get("eyebrow", ""), meta.get("headline", ""), story_out)
        else:    render_story_clean(img, story_out)
    commit_push(f"Render {base} (upload) [skip ci]")
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE).decode().strip()
    def _raw(p):
        return (f"https://raw.githubusercontent.com/{REPO}/{sha}/"
                + urllib.parse.quote(os.path.relpath(p, HERE).replace(os.sep, "/")))
    image_urls = [_raw(o) for o in outs]
    story_url = _raw(story_out) if story_out else None
    hashtags = " ".join("#" + t.lstrip("#") for t in meta.get("hashtags", []))
    mentions = " ".join(m if m.startswith("@") else "@" + m for m in meta.get("tags", []))
    caption = "\n\n".join(p for p in caption_body(meta) + [mentions, hashtags] if p).strip()
    state = {"skip": False, "source": base, "sources": [base], "base": base,
             "image_urls": image_urls, "image_url": image_urls[0], "story_url": story_url,
             "caption": caption,
             "format": "carousel" if len(image_urls) > 1 else "single",
             "category": meta.get("category"),
             "pillar": meta.get("pillar"), "status": "pending",
             "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    json.dump(state, open(STATE, "w"))
    commit_push(f"Stage {base} (upload) for review [skip ci]")
    if (rget("settings", {}) or {}).get("auto_approve"):
        # Owner's rule (Sep 10 2026): he uploaded this HIMSELF, so under auto-approve it
        # posts IMMEDIATELY — no morning hold. The best-hours hold applies only to posts
        # the system picked on its own (see prepare()).
        print("Auto-approve ON — publishing uploaded post now."); publish(state)
        # (never rdel pending_post here: this upload was never stored in the slot, and an
        #  older undecided post may still be waiting there — owner's queue rule)
    else:
        requeue_prev_pending(state)                   # never discard an unapproved pending
        rset("pending_post", state)
        wa_notify(f"Uploaded post ready to approve. Review & approve: {DASHBOARD_URL}")
    summary(f"## Uploaded post — review before it goes live\n\n![preview]({image_urls[0]})\n\n"
            f"**Caption:**\n\n{caption}")
    print("Ingested & staged:", base)


def prepare():
    """Pick a photo, caption it, render it, push it, and stage state.json.
    Does NOT post — that's publish()."""
    git_setup()
    # Privacy pass first (no-op after the first run): never leave GPS in the public repo.
    try:
        _keep = set()
        for _st in [rget("pending_post")] + (rget("pending_queue", []) or []):
            for _n in ((_st or {}).get("sources") or [(_st or {}).get("source")]):
                if _n: _keep.add(_n)
        try:
            _lst = json.load(open(STATE))
            for _n in (_lst.get("sources") or [_lst.get("source")]):
                if _n: _keep.add(_n)
        except Exception:
            pass
        strip_location_metadata(keep=_keep)
    except Exception as e:
        print("metadata strip pass skipped:", e)
    ing = rget("ingest_image", None)
    if ing and (ing.get("url") or ing.get("urls")):
        rdel("ingest_image")
        ingest_image(ing.get("urls") or ing["url"], ing.get("note", ""))
        return
    # Owner hit "New caption" on the dashboard: SAME photo and rendered images,
    # only the words are rewritten (a fresh caption_for pass with an anti-repeat hint).
    if rget("recaption_request"):
        rdel("recaption_request")
        st = rget("pending_post")
        srcp = os.path.join(SRC, st.get("source", "")) if st else ""
        if st and not os.path.exists(srcp):               # uploaded post: recaption from its rendered cover
            _alt = os.path.join(RENDERED, f"{st.get('base', '')}_1.jpg")
            if os.path.exists(_alt):
                srcp = _alt
        if st and not st.get("skip") and os.path.exists(srcp):
            print("Recaption requested — rewriting the caption for", st.get("base"))
            learn = performance_brief()
            note = ""
            _np = os.path.splitext(srcp)[0] + ".txt"
            if os.path.exists(_np):
                try:
                    note = open(_np, encoding="utf-8").read()
                except Exception:
                    note = ""
            img = Image.open(srcp)
            buf = io.BytesIO()
            pv = img.convert("RGB"); pv.thumbnail((1280, 1280)); pv.save(buf, "JPEG", quality=90)
            old = (st.get("caption") or "").split("\n\n")[0]
            hint = ("The owner rejected this caption. Write a COMPLETELY DIFFERENT one: "
                    "a different angle, a different first line, no shared phrases with: \""
                    + old[:400] + "\"")
            try:
                meta = caption_for(buf.getvalue(), note, TAGS, learn, hint=hint)
                hashtags = " ".join("#" + t.lstrip("#") for t in meta.get("hashtags", []))
                mentions = " ".join(m if m.startswith("@") else "@" + m for m in meta.get("tags", []))
                st["caption"] = "\n\n".join(
                    p for p in caption_body(meta) + [mentions, hashtags] if p).strip()
                st["pillar"] = meta.get("pillar", st.get("pillar"))
                st["status"] = "pending"
                st["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                rset("pending_post", st)
                wa_notify("New caption ready for the staged post. Review: " + DASHBOARD_URL)
                summary("### New caption staged\n\n" + st["caption"])
                print("New caption staged.")
            except Exception as e:
                print("Recaption failed:", e)
                summary("### Recaption failed\n" + str(e))
        else:
            print("Recaption requested but no pending post (or its photo) found.")
        return
    # Guard: only one post per day. We run the schedule several times each morning
    # (GitHub skips/delays single crons), so skip if we already posted today.
    lp = os.path.join(HERE, "metrics", "last_posted.txt")
    today = cr_today()
    forced = os.environ.get("FORCE_POST") == "1"   # manual "Force" run overrides the guard
    if forced:
        print("FORCE_POST set — bypassing the once-per-day guard.")
    if not forced and os.path.exists(lp) and open(lp).read().strip() == today:
        json.dump({"skip": True, "why": "already posted today"}, open(STATE, "w"))
        # no commit here: backup slots run several times a day and this is the normal no-op
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

    rejected_bases = set(rget("rejected_bases", []) or [])   # photos you rejected — never re-pick
    target = target_pillar()
    print(f"Content plan — today's target pillar: {target} | recent mix: {_recent_pillars()}")

    def _scan(candidates):
        """Walk the candidates once. Returns (chosen, judged, api_errors): `judged` counts
        photos the captioner actually assessed, `api_errors` the ones it could not reach.
        The two must never be confused — on Sep 28 2026 Gemini answered 503 for all
        eight candidates and the run reported "No post-worthy photo" in green."""
        chosen = fallback = None
        judged = api_errors = 0
        for src in candidates[:PLAN_SCAN]:
            if os.path.splitext(os.path.basename(src))[0] in rejected_bases:
                # Owner's rule (Sep 10 2026): a rejected picture is unwanted — DELETE it
                # immediately, never archive or recycle it for later.
                print("Deleting a photo you rejected:", os.path.basename(src))
                os.remove(src)
                _np = os.path.splitext(src)[0] + ".txt"
                if os.path.exists(_np):
                    os.remove(_np)
                continue
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
                if "caption models failed" in str(e):
                    api_errors += 1                  # the service, not the photo
                continue
            judged += 1
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

        return chosen or fallback, judged, api_errors

    chosen, judged, api_errors = _scan(candidates)
    if not chosen and judged == 0 and api_errors:
        # Every candidate hit a service error — Gemini is down, not the photos. Wait once
        # and try again; 503s are often minutes long.
        print(f"Caption service unavailable for all {api_errors} candidates — waiting 4 min and retrying once.")
        time.sleep(240)
        candidates = sorted(f for f in glob.glob(os.path.join(SRC, "*"))
                            if f.lower().endswith((".jpg", ".jpeg", ".png", ".heic", ".heif")))
        chosen, judged, api_errors = _scan(candidates)
    if not chosen and judged == 0 and api_errors:
        json.dump({"skip": True, "why": "captioner unavailable"}, open(STATE, "w"))
        commit_push("Caption service unavailable — no post staged [skip ci]")
        summary("### Nothing staged — caption service unavailable\n"
                f"Gemini returned errors for all {api_errors} candidate photos (twice, 4 min apart). "
                "The next daily slot retries automatically; the photos are untouched.")
        wa_notify(f"⚠️ No post staged: the caption service (Gemini) returned errors for all "
                  f"{api_errors} photos, even after a 4-minute retry. The next slot retries "
                  f"automatically — nothing to do unless it keeps happening.")
        raise SystemExit(1)                          # red run: this is an outage, not a quiet day
    if not chosen:                                   # genuinely nothing post-worthy this time
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

    # Clean photo is the DEFAULT. Text is burned on only for a deliberate title card
    # (config "burn_text": true, env FORCE_TITLE=1, or a companion note beginning "!title").
    note = ""
    _np = os.path.splitext(src)[0] + ".txt"
    if os.path.exists(_np):
        try:
            with open(_np, encoding="utf-8") as _nf: note = _nf.read()
        except Exception: note = ""
    burn = wants_title_card(note, meta)
    bias = float(meta.get("crop_bias", 0.5))
    outs = []                                   # slide 1 = the photo
    out1 = os.path.join(RENDERED, f"{base}_1.jpg")
    if burn:
        render(img, meta["eyebrow"], meta["headline"], out1, bias)
    else:
        render_clean(img, out1, bias)
    outs.append(out1)
    if burst_imgs:                              # sibling photos in a burst — always clean
        n = 2
        for bi in burst_imgs:
            o = os.path.join(RENDERED, f"{base}_{n}.jpg")
            render_clean(bi, o); outs.append(o); n += 1
    elif burn and fmt == "carousel" and slides:  # editorial text slides only on a flagged title post
        cta = (meta.get("cta") or "").strip()
        total = 1 + len(slides[:4]) + (1 if cta else 0)
        n = 2
        for s in slides[:4]:
            o = os.path.join(RENDERED, f"{base}_{n}.jpg")
            render_text_slide(s, n, total, o); outs.append(o); n += 1
        if cta:
            o = os.path.join(RENDERED, f"{base}_{n}.jpg")
            render_text_slide(cta, n, total, o, kicker="The journey"); outs.append(o)
    if len(outs) == 1:
        fmt = "single"                          # a clean single photo, never a text-slide carousel

    story_out = None
    if CFG.get("also_story"):
        story_out = os.path.join(RENDERED, f"{base}_story.jpg")
        if burn:
            render_story(img, meta["eyebrow"], meta["headline"], story_out)
        else:
            render_story_clean(img, story_out)

    commit_push(f"Render {base} [skip ci]")
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE).decode().strip()

    def raw(p):
        return (f"https://raw.githubusercontent.com/{REPO}/{sha}/"
                f"{urllib.parse.quote(os.path.relpath(p, HERE).replace(os.sep, '/'))}")
    image_urls = [raw(o) for o in outs]
    story_url = raw(story_out) if story_out else None

    hashtags = " ".join("#" + t.lstrip("#") for t in meta.get("hashtags", []))
    mentions = " ".join(m if m.startswith("@") else "@" + m for m in meta.get("tags", []))
    caption = "\n\n".join(p for p in caption_body(meta) + [mentions, hashtags] if p).strip()
    state = {"skip": False, "source": os.path.basename(src), "sources": sources, "base": base,
             "image_urls": image_urls, "image_url": image_urls[0],
             "story_url": story_url, "caption": caption,
             "format": fmt, "category": meta.get("category"),
             "pillar": meta.get("pillar"), "status": "pending",
             "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    json.dump(state, open(STATE, "w"))
    commit_push(f"Stage {base} for review [skip ci]")
    if (rget("settings", {}) or {}).get("auto_approve"):
        # Owner's rule (Sep 28 2026): with auto-approve ON a post goes out the moment there
        # is one — no morning hold, no waiting for the next day. The scheduler's slots
        # already sit in the best hours; a late recovery post is better than none.
        print("Auto-approve is ON — publishing immediately.")
        try:
            publish(state)      # the new post was never stored as pending_post — leave the
                                # slot alone (an older undecided post may still be in it)
        except Exception as e:
            err = str(e)[:300]
            if state.get("_ig_media_id"):
                # Instagram already has it and only a follow-up step failed. Finish the
                # bookkeeping HERE so the next slot cannot post the same photo again.
                print("Post is live on Instagram; a follow-up step failed:", err)
                _archive_and_stamp(state)
                commit_push(f"Posted {base} [skip ci]")
                wa_notify(f"⚠️ Post {base} is live on Instagram, but a follow-up step failed "
                          f"({err}). Bookkeeping was completed, it will not be posted twice.")
            else:
                # Nothing went out. The photo stays in source-photos and the day is not
                # stamped, so the next scheduled slot retries automatically (owner's rule:
                # the post of the day never waits for the next day).
                wa_notify(f"❌ Today's post ({base}) could not be published: {err}. "
                          f"The next slot retries automatically.")
                raise
    else:                                             # human review: stage + ping for approval
        requeue_prev_pending(state)                   # never discard an unapproved pending
        rset("pending_post", state)
        wa_notify(f"Post ready to approve — {(meta.get('pillar') or 'post').title()}, "
                  f"{'carousel ' + str(len(image_urls)) if len(image_urls) > 1 else 'single'}"
                  f"{' + story' if story_url else ''}. Review & approve: {DASHBOARD_URL}")

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
    if meta.get("_violations"):
        notes_md += ("\n\n> ✍️ **Voice check still flags:** " + "; ".join(meta["_violations"])
                     + " (the model was asked once to rewrite; this is the cleaner of the two).")
    learn_md = ("\n\n**What your data says (today's standards):**\n\n> "
                + learn.replace("\n", "\n> ")) if learn else ""
    summary(f"## Today's post — review before it goes live\n\n_{kind}_\n\n{previews}\n\n"
            f"**Caption:**\n\n{caption}\n\n"
            f"Approve the **publish** job to send it to Instagram"
            + (" and Facebook." if "fb" in CFG.get("targets", []) else ".")
            + low + notes_md + learn_md)
    print("Prepared:", base, f"({kind}) | photos remaining:", remaining)


def publish(st=None):
    """Post a staged item — from state.json by default, or a passed dict (an approved post)."""
    if st is None:
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
            print("Instagram carousel OK:", pub.get("id")); st["_ig_media_id"] = pub.get("id")
        else:                                        # single image
            cont = meta_post(f"{ig}/media",
                             {"image_url": image_urls[0], "caption": caption, "access_token": META_TOKEN})
            time.sleep(8)
            pub = meta_post(f"{ig}/media_publish",
                            {"creation_id": cont["id"], "access_token": META_TOKEN})
            print("Instagram OK:", pub.get("id")); st["_ig_media_id"] = pub.get("id")
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
            today = cr_today()
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

    _archive_and_stamp(st)
    # Announce it's LIVE — to the dashboard (Upstash) and WhatsApp, with a direct link.
    # Best-effort: a hiccup here must never stop the archive commit below, because an
    # archive that is not pushed means the next slot would post the same photo again.
    permalink = ""
    try:
        if "ig" in targets and pub.get("id"):
            gv = CFG.get("graph_version", "v23.0")
            with urllib.request.urlopen(
                    f"https://graph.facebook.com/{gv}/{pub['id']}?fields=permalink"
                    f"&access_token={META_TOKEN}", timeout=30) as r:
                permalink = (json.loads(r.read().decode()) or {}).get("permalink", "")
    except Exception as e:
        print("permalink fetch skipped:", e)
    try:
        rset("last_published", {"base": st.get("base"), "pillar": st.get("pillar"),
                                "image": image_urls[0] if image_urls else "",
                                "media_id": pub.get("id"),
                                "permalink": permalink, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
    except Exception as e:
        print("last_published not recorded:", e)
    wa_notify(f"✅ Posted live — {(st.get('pillar') or 'post').title()}. "
              + (f"View: {permalink}" if permalink else "Check Instagram."))
    commit_push(f"Posted {st['base']} [skip ci]")
    print("Done.")


def _archive_and_stamp(st):
    """Bookkeeping once Instagram has the post: move the photo(s) to posted/, keep the
    caption next to them, drop state.json, stamp the Costa Rica day. Idempotent, so the
    auto-approve path can call it again after a failure that happened AFTER the post
    went live (owner's rule: a post never goes out twice)."""
    caption = st.get("caption") or ""
    for sname in (st.get("sources") or [st.get("source")]):   # archive every burst photo used
        if not sname:
            continue
        sp = os.path.join(SRC, sname)
        if os.path.exists(sp):
            os.replace(sp, os.path.join(POSTED, sname))
        note_p = os.path.join(SRC, os.path.splitext(sname)[0] + ".txt")  # its companion note
        if os.path.exists(note_p):
            os.remove(note_p)
    if st.get("base"):
        with open(os.path.join(POSTED, st["base"] + ".txt"), "w", encoding="utf-8") as f:
            f.write(caption)
    if os.path.exists(STATE):
        os.remove(STATE)
    mdir = os.path.join(HERE, "metrics"); os.makedirs(mdir, exist_ok=True)
    open(os.path.join(mdir, "last_posted.txt"), "w").write(cr_today())


def requeue_prev_pending(state):
    """Owner's rule (Sep 10 2026): staging a NEW post never discards an unapproved
    one — the previous pending joins a FIFO queue (pending_queue, capped at 5) and
    comes back as the pending card once the current one is approved or rejected."""
    prev = rget("pending_post")
    # pending OR approved-and-held: on Sep 28 2026 three late runs each overwrote the
    # previous held post, after telling the owner each one "publishes at 8:00 AM".
    if prev and not prev.get("skip") and prev.get("status") in ("pending", "approved") \
            and prev.get("base") != (state or {}).get("base"):
        q = rget("pending_queue", []) or []
        if not any((p or {}).get("base") == prev.get("base") for p in q):
            prev = dict(prev); prev["status"] = "pending"; prev.pop("hold_until", None)
            q.append(prev)
            rset("pending_queue", q[-5:])
            print("Queued the previous post:", prev.get("base"))


def promote_queued_pending():
    """Move the oldest queued post into the pending slot (after approve/reject)."""
    q = rget("pending_queue", []) or []
    while q:
        nxt = q.pop(0)
        rset("pending_queue", q)
        if nxt and not nxt.get("skip"):
            nxt["status"] = "pending"
            rset("pending_post", nxt)
            wa_notify("Next queued post is waiting for your approval: " + DASHBOARD_URL)
            print("Promoted queued post:", nxt.get("base"))
            return
    rset("pending_queue", q)


def publish_pending():
    """Publish the post the owner APPROVED on the dashboard (read from Upstash)."""
    st = rget("pending_post")
    if not st or st.get("skip"):
        print("No pending post to publish."); return
    if st.get("status") != "approved":
        print("Pending post not approved yet (status:", st.get("status"), ") — skipping."); return
    git_setup()                                        # (morning hold removed Sep 28 2026 — owner's rule)
    try:
        publish(st)                                    # reuse the full publish path
    except Exception as e:
        err = str(e)[:300]
        if st.get("_ig_media_id"):
            # Instagram already took it — only the post-processing failed. Don't retry
            # (that would post it twice); clear the slot and say what happened.
            wa_notify(f"⚠️ Post {st.get('base')} went live on Instagram but the follow-up "
                      f"failed ({err}). Check the run: {DASHBOARD_URL}")
            rdel("pending_post"); promote_queued_pending()
        else:
            # Nothing was posted. Put it back in front of the owner with the reason, so the
            # card reappears (Approve = retry, Reject, ↻ New caption) instead of silently
            # retrying every morning.
            st["status"] = "pending"; st.pop("hold_until", None); st["last_error"] = err
            rset("pending_post", st)
            wa_notify(f"❌ Post {st.get('base')} could not be published: {err}. "
                      f"It's back on the dashboard — approve again to retry, or reject it. {DASHBOARD_URL}")
        raise SystemExit(1)                            # keep the run red for the alert step
    decisions = rget("post_decisions", []) or []       # learning: log the approval
    decisions.append({"base": st.get("base"), "pillar": st.get("pillar"),
                      "decision": "approved", "edited": bool(st.get("edited")),
                      "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
    rset("post_decisions", decisions[-200:])
    rdel("pending_post")                               # clear the slot
    promote_queued_pending()                           # next queued post takes the slot
    print("Published approved post:", st.get("base"))


def caption_preview(n=3):
    """Voice calibration (Sep 29 2026): caption the next n candidate photos with the
    current brief and print them to the run summary. Nothing is staged, rendered, posted
    or committed, and the photos are not touched (no rejects, no deletes, no GPS pass)."""
    learn = performance_brief()
    rejected = set(rget("rejected_bases", []) or [])
    cands = [f for f in sorted(glob.glob(os.path.join(SRC, "*")))
             if f.lower().endswith((".jpg", ".jpeg", ".png", ".heic", ".heif"))
             and os.path.splitext(os.path.basename(f))[0] not in rejected]
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE).decode().strip()
    except Exception:
        sha = "main"
    md = [f"## Caption preview — the next {min(n, len(cands))} photos, current brief "
          f"(nothing was posted)\n"]
    for src in cands[:n]:
        name = os.path.basename(src)
        note = ""
        np_ = os.path.splitext(src)[0] + ".txt"
        if os.path.exists(np_):
            try:
                note = open(np_, encoding="utf-8").read()
            except Exception:
                note = ""
        try:
            img = Image.open(src)
            buf = io.BytesIO()
            pv = img.convert("RGB"); pv.thumbnail((1280, 1280)); pv.save(buf, "JPEG", quality=85)
            meta = caption_for(buf.getvalue(), note, TAGS, learn)
        except Exception as e:
            md.append(f"### {name}\n\nCaption error: {e}\n"); continue
        img_md = ""
        if REPO and name.lower().endswith((".jpg", ".jpeg", ".png")):
            img_md = (f"![{name}](https://raw.githubusercontent.com/{REPO}/{sha}/source-photos/"
                      f"{urllib.parse.quote(name)})\n\n")
        md.append(f"### {name}\n\n{img_md}"
                  f"_{'post-worthy' if meta.get('post_worthy') else 'NOT post-worthy'}: "
                  f"{meta.get('reason', '')}_  \n"
                  f"_{meta.get('pillar')} · {meta.get('format')} · headline: "
                  f"**{meta.get('headline', '')}**"
                  + (f" · note: {note.strip()[:120]}" if note.strip() else " · no note") + "_\n\n"
                  + (meta.get("caption_en") or "").strip() + "\n"
                  + ("\n" + "\n".join(f"- slide {i + 2}: {s}" for i, s in enumerate(meta.get("slides") or []))
                     if meta.get("slides") else "")
                  + (f"\n- closing line: {meta['cta']}" if meta.get("cta") else "")
                  + "\n\n" + " ".join("#" + t for t in meta.get("hashtags", []))
                  + (f"\n\n> ✍️ Voice check still flags: {'; '.join(meta['_violations'])}"
                     if meta.get("_violations") else "\n\n> ✍️ Voice check: clean")
                  + "\n")
        print(f"\n=== {name} ===\n{(meta.get('caption_en') or '').strip()}\n")
    # What the account has been posting (the old brief), for the side-by-side.
    try:
        posts = [p for p in json.load(open(POSTS_LOG))
                 if p.get("format") not in ("story", "reel") and not str(p.get("base", "")).endswith("-story")]
        md.append("\n## For comparison — the last 3 captions the account actually posted\n")
        for p in posts[-3:]:
            full = ""
            cp = os.path.join(POSTED, str(p.get("base", "")) + ".txt")
            if os.path.exists(cp):
                full = open(cp, encoding="utf-8").read().split("\n\n#")[0].strip()
            md.append(f"### {p.get('base')} · {p.get('date')}\n\n{full or p.get('caption', '')}\n")
    except Exception as e:
        md.append(f"\n(previous captions not listed: {e})\n")
    summary("\n".join(md))
    print("Preview done.")


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    if phase == "prepare":
        prepare()
    elif phase == "publish":
        publish()
    elif phase == "publish_pending":
        publish_pending()
    elif phase == "preview":
        caption_preview(int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].strip().isdigit() else 3)
    else:  # "all" = legacy immediate post (no approval gate)
        prepare()
        publish()
