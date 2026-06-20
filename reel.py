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


def next_clip():
    """Oldest Cloudinary video not yet tagged 'posted'."""
    import cloudinary, cloudinary.api
    if not os.environ.get("CLOUDINARY_URL"):
        raise SystemExit("Missing CLOUDINARY_URL secret.")
    res = cloudinary.api.resources(resource_type="video", type="upload",
                                   max_results=100, tags=True, context=True)
    vids = [r for r in res.get("resources", []) if "posted" not in (r.get("tags") or [])]
    vids.sort(key=lambda r: r.get("created_at", ""))
    return vids[0] if vids else None


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
