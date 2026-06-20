#!/usr/bin/env python3
"""
Post an Instagram Reel from a clip stored in Cloudinary — the format our own data
says wins.

Cloudinary is the video warehouse (no git, no file-size limits). You upload clips
into Cloudinary's Media Library; this job finds the oldest clip not yet tagged
"posted", captions it from a frame through the SAME brand captioner + learner the
photo poster uses, publishes it as a Reel (with status polling), tags it "posted"
in Cloudinary, and logs it. No video ever touches GitHub.

Secrets:
  META_ACCESS_TOKEN  (the permanent Page token — already set)
  CLOUDINARY_URL     (cloudinary://<key>:<secret>@<cloud> — repo secret)

Optional: give a clip a caption hint by setting a Cloudinary context field
`note` on the asset (Media Library → asset → Context). Otherwise it captions from
the frame alone.
"""
import os, json, time, urllib.request, urllib.parse
import autopost as ap                       # caption_for, performance_brief, meta_post, CFG, TAGS

HERE = ap.HERE
TOKEN = ap.META_TOKEN
IG = ap.CFG["ig_user_id"]
V = ap.CFG.get("graph_version", "v23.0")


def get(path, params):
    url = f"https://graph.facebook.com/{V}/{path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode())


def config_cloudinary():
    """Configure Cloudinary. Prefer three separate secrets (foolproof — no URL to
    assemble); fall back to a CLOUDINARY_URL, sanitised of common paste mistakes."""
    import cloudinary
    if os.environ.get("CLOUDINARY_API_KEY"):
        cloudinary.config(
            cloud_name=(os.environ.get("CLOUDINARY_CLOUD_NAME") or "").strip(),
            api_key=(os.environ.get("CLOUDINARY_API_KEY") or "").strip(),
            api_secret=(os.environ.get("CLOUDINARY_API_SECRET") or "").strip(),
            secure=True)
    elif os.environ.get("CLOUDINARY_URL"):
        v = os.environ["CLOUDINARY_URL"].strip().strip('"').strip("'")
        if "cloudinary://" in v:
            v = v[v.index("cloudinary://"):]          # drop any CLOUDINARY_URL= prefix
        os.environ["CLOUDINARY_URL"] = v
        cloudinary.config()
    else:
        raise SystemExit("No Cloudinary credentials. Add CLOUDINARY_CLOUD_NAME, "
                         "CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET as repo secrets.")


def next_clip():
    """Oldest video in the Cloudinary 'reels' folder not yet tagged 'posted'.
    Scoped to a folder ON PURPOSE so Cloudinary's stock SAMPLE videos (which live
    outside it) can never be posted. Upload your own clips into a folder named
    'reels' in the Cloudinary Media Library."""
    import cloudinary, cloudinary.search
    try:
        r = (cloudinary.search.Search()
             .expression("resource_type:video AND (folder:Reels OR folder:reels) AND -tags:posted")
             .sort_by("created_at", "asc").max_results(50).execute())
        vids = r.get("resources", [])
        return vids[0] if vids else None
    except Exception as e:
        print("Cloudinary search error (no reel posted):", e)
        return None


def thumb_bytes(public_id):
    import cloudinary.utils
    url = cloudinary.utils.cloudinary_url(public_id, resource_type="video",
                                          format="jpg", start_offset="1", secure=True)[0]
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def publish_reel(video_url, caption):
    cont = ap.meta_post(f"{IG}/media",
                        {"media_type": "REELS", "video_url": video_url,
                         "caption": caption, "share_to_feed": "true",
                         "access_token": TOKEN})
    cid = cont["id"]
    for _ in range(36):                       # reels transcode async; poll up to ~6 min
        time.sleep(10)
        st = get(cid, {"fields": "status_code,status", "access_token": TOKEN})
        code = st.get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"Reel processing failed: {st.get('status')}")
    pub = ap.meta_post(f"{IG}/media_publish",
                       {"creation_id": cid, "access_token": TOKEN})
    return pub.get("id")


def log_post(mid, base, meta):
    mdir = os.path.join(HERE, "metrics"); os.makedirs(mdir, exist_ok=True)
    pj = os.path.join(mdir, "posts.json")
    posts = json.load(open(pj)) if os.path.exists(pj) else []
    posts.append({"id": mid, "date": time.strftime("%Y-%m-%d"), "base": base,
                  "format": "reel", "category": meta.get("category"),
                  "pillar": meta.get("pillar"),
                  "caption": (meta.get("caption_en") or "")[:120]})
    json.dump(posts, open(pj, "w"), indent=1)


def main():
    if not TOKEN:
        raise SystemExit("Missing META_ACCESS_TOKEN.")
    import cloudinary, cloudinary.uploader
    config_cloudinary()
    clip = next_clip()
    if not clip:
        print("No un-posted clips in Cloudinary. Nothing to do.")
        return
    pid = clip["public_id"]
    video_url = clip["secure_url"]
    note = ((clip.get("context") or {}).get("custom") or {}).get("note", "")
    print("Clip:", pid)

    learn = ap.performance_brief()
    meta = ap.caption_for(thumb_bytes(pid), note, ap.TAGS, learn)
    hashtags = " ".join("#" + t.lstrip("#") for t in meta.get("hashtags", []))
    mentions = " ".join(m if m.startswith("@") else "@" + m for m in meta.get("tags", []))
    caption = "\n\n".join(p for p in [meta.get("caption_en", ""), meta.get("caption_es", ""),
                                      mentions, hashtags] if p).strip()

    print("Publishing reel…")
    mid = publish_reel(video_url, caption)
    print("Reel published:", mid)

    cloudinary.uploader.add_tag("posted", pid, resource_type="video")
    base = pid.split("/")[-1]
    log_post(mid, base, meta)
    ap.git_setup()
    ap.commit_push(f"Posted reel {base} [skip ci]")
    print("Done.")


if __name__ == "__main__":
    main()
