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
S = 1080

GH_TOKEN = os.environ.get("GITHUB_TOKEN")
META_TOKEN = os.environ.get("META_ACCESS_TOKEN")
REPO = os.environ.get("GITHUB_REPOSITORY", "")

MODELS_URL = "https://models.github.ai/inference/chat/completions"
MODEL = CFG.get("caption_model", "openai/gpt-4o")

BRAND_PROMPT = r"""You are the in-house social copywriter for My Adventure Costa Rica — a LUXURY ENDURANCE adventure travel brand (trail running, mountain biking, school programs, and bespoke private journeys). The brand operates FROM Costa Rica but speaks TO an international audience. The voice is luxury editorial — the register of Travel + Leisure — unhurried, evocative, confident, never a guidebook, never utility tourism, never hype or exclamation marks.

You will be shown ONE photo. Look closely at what is ACTUALLY in it, then return STRICT JSON (only the object, no prose, no code fences) with:
- "post_worthy": boolean. false if the photo is blurry, cluttered (power lines, signage, parked cars, trash, busy backgrounds), a screenshot, a duplicate-feeling snapshot, or simply below a luxury feed's bar.
- "reason": one short sentence explaining the worthiness call.
- "category": one of "TRAIL RUNNING","MOUNTAIN BIKING","BESPOKE JOURNEYS","SCHOOL PROGRAMS","COSTA RICA".
- "eyebrow": the category + " · COSTA RICA" (e.g. "TRAIL RUNNING · COSTA RICA"). For a contemplative landscape/atmosphere shot use "COSTA RICA · SLOWLY".
- "headline": ONE short editorial line, ~4–7 words. Evocative, restrained.
- "caption_en": 2–3 sentence English caption in the brand voice. End with a quiet positioning line where natural (e.g. "Trail running journeys in Costa Rica, designed slowly.").
- "caption_es": the Spanish caption. NOT a literal translation — write it natively and elegantly.
- "hashtags": array of 4–5 lowercase tags (no #), always include "myadventurecostarica" and "costarica".
- "crop_bias": 0.0–1.0 vertical crop focus (0.3 if subject/horizon is upper, 0.6 to keep people/foreground at the bottom, 0.5 default).

== HARD RULES ==
1. Write the brand name in FULL every time: "My Adventure Costa Rica". NEVER an acronym.
2. GEOGRAPHIC PRECISION: never name a specific place, peak, volcano, river, lake, beach, park, town, or wildlife species UNLESS it is unmistakable in the photo. Mountains, cloud forests, beaches, and macaws are NOT interchangeable. When unsure, stay evocative with no location claim.
3. Never invent operational facts (distances, elevation, difficulty, tides, dates, prices).
4. Describe only what is in the frame. A bike photo is about riding; a runner is about running; a landscape is about stillness. Do not introduce subjects (animals, people, weather) that aren't visible.

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


def caption_for(jpeg_bytes):
    b64 = base64.b64encode(jpeg_bytes).decode()
    payload = {
        "model": MODEL,
        "temperature": 0.7,
        "messages": [
            {"role": "system", "content": BRAND_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": "Caption this photo as JSON."},
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
    git("push")


def summary(md):
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as f:
            f.write(md + "\n")


def prepare():
    """Pick a photo, caption it, render it, push it, and stage state.json.
    Does NOT post — that's publish()."""
    git_setup()
    candidates = sorted(
        f for f in glob.glob(os.path.join(SRC, "*"))
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".heic", ".heif"))
    )
    if not candidates:
        json.dump({"skip": True, "why": "no photos"}, open(STATE, "w"))
        commit_push("No photos to post [skip ci]")
        summary("### Nothing to post\nNo photos in `source-photos/`. Add some.")
        return

    chosen = None
    for src in candidates[:6]:
        try:
            img = Image.open(src)
            buf = io.BytesIO()
            pv = img.convert("RGB"); pv.thumbnail((1280, 1280))
            pv.save(buf, format="JPEG", quality=85)
            meta = caption_for(buf.getvalue())
        except Exception as e:
            print("Caption error on", os.path.basename(src), "->", e)
            continue
        if meta.get("post_worthy"):
            chosen = (src, img, meta); break
        print("Not post-worthy:", os.path.basename(src), "-", meta.get("reason"))
        os.replace(src, os.path.join(REJECTED, os.path.basename(src)))

    if not chosen:
        json.dump({"skip": True, "why": "none post-worthy"}, open(STATE, "w"))
        commit_push("No post-worthy photo [skip ci]")
        summary("### Nothing to post\nNo post-worthy photo this run.")
        return

    src, img, meta = chosen
    base = os.path.splitext(os.path.basename(src))[0]
    out = os.path.join(RENDERED, base + ".jpg")
    render(img, meta["eyebrow"], meta["headline"], out, float(meta.get("crop_bias", 0.5)))
    commit_push(f"Render {base} [skip ci]")
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE).decode().strip()
    rel = os.path.relpath(out, HERE).replace(os.sep, "/")
    image_url = f"https://raw.githubusercontent.com/{REPO}/{sha}/{urllib.parse.quote(rel)}"

    tags = " ".join("#" + t.lstrip("#") for t in meta.get("hashtags", []))
    caption = f"{meta['caption_en']}\n\n{meta['caption_es']}\n\n{tags}".strip()
    json.dump({"skip": False, "source": os.path.basename(src), "base": base,
               "image_url": image_url, "caption": caption}, open(STATE, "w"))
    commit_push(f"Stage {base} for review [skip ci]")

    remaining = len([f for f in glob.glob(os.path.join(SRC, "*"))
                     if f.lower().endswith((".jpg", ".jpeg", ".png", ".heic", ".heif"))]) - 1
    low = ("\n\n> ⚠️ **Low on photos** — about %d left. Add more to `source-photos/`."
           % remaining) if remaining <= 7 else ""
    summary(f"## Today's post — review before it goes live\n\n"
            f"![preview]({image_url})\n\n**Caption:**\n\n{caption}\n\n"
            f"Approve the **publish** job to send it to Instagram"
            + (" and Facebook." if "fb" in CFG.get("targets", []) else ".")
            + low)
    print("Prepared:", base, "| photos remaining:", remaining)


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
    image_url, caption = st["image_url"], st["caption"]
    targets = CFG.get("targets", ["ig", "fb"])
    if "ig" in targets:
        cont = meta_post(f"{CFG['ig_user_id']}/media",
                         {"image_url": image_url, "caption": caption, "access_token": META_TOKEN})
        time.sleep(8)
        pub = meta_post(f"{CFG['ig_user_id']}/media_publish",
                        {"creation_id": cont["id"], "access_token": META_TOKEN})
        print("Instagram OK:", pub.get("id"))
    if "fb" in targets:
        try:
            res = meta_post(f"{CFG['page_id']}/photos",
                            {"url": image_url, "message": caption, "access_token": META_TOKEN})
            print("Facebook OK:", res.get("post_id") or res.get("id"))
        except Exception as e:
            print("Facebook skipped (needs pages_manage_posts):", e)

    src = os.path.join(SRC, st["source"])
    if os.path.exists(src):
        os.replace(src, os.path.join(POSTED, st["source"]))
    with open(os.path.join(POSTED, st["base"] + ".txt"), "w", encoding="utf-8") as f:
        f.write(caption)
    if os.path.exists(STATE):
        os.remove(STATE)
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
