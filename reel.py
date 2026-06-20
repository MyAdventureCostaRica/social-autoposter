#!/usr/bin/env python3
"""
Post a finished video clip from source-videos/ as an Instagram Reel — the format
our own data says wins.

Free pipeline, no GitHub file-size problem: the clip is uploaded to Cloudinary
(which gives a public URL Meta can fetch), captioned from a representative frame
through the SAME brand captioner + learner the photo poster uses, published via
the Reels API (with status polling), then archived to posted-videos/.

Secrets needed:
  META_ACCESS_TOKEN  (already set — the permanent Page token)
  CLOUDINARY_URL     (cloudinary://<api_key>:<api_secret>@<cloud_name> — one line,
                      copied from the Cloudinary dashboard, added as a repo secret)

Drop .mp4/.mov clips into source-videos/ (optionally a same-named .txt note with
true facts, like the photo flow). Short clips (<100MB) are fine in the repo; they
move to posted-videos/ after publishing.
"""
import os, glob, json, time, subprocess, urllib.parse, urllib.request, urllib.error
import autopost as ap                      # reuse caption_for, performance_brief, meta_post, CFG, TAGS

HERE = ap.HERE
SRCV = os.path.join(HERE, "source-videos")
POSTEDV = os.path.join(HERE, "posted-videos")
os.makedirs(SRCV, exist_ok=True)
os.makedirs(POSTEDV, exist_ok=True)
TOKEN = ap.META_TOKEN
IG = ap.CFG["ig_user_id"]
V = ap.CFG.get("graph_version", "v23.0")
VIDEO_EXT = (".mp4", ".mov", ".m4v")


def get(path, params):
    url = f"https://graph.facebook.com/{V}/{path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode())


def frame_bytes(video):
    """Grab a representative frame (~1s in) to caption from."""
    out = "/tmp/reel_frame.jpg"
    subprocess.run(["ffmpeg", "-y", "-ss", "1", "-i", video, "-vframes", "1",
                    "-q:v", "3", out], check=True, capture_output=True)
    return open(out, "rb").read()


def upload_to_cloudinary(video):
    import cloudinary, cloudinary.uploader      # configures itself from CLOUDINARY_URL
    if not os.environ.get("CLOUDINARY_URL"):
        raise SystemExit("Missing CLOUDINARY_URL secret — create a free Cloudinary "
                         "account and add it as a repo secret.")
    res = cloudinary.uploader.upload(video, resource_type="video", folder="reels")
    return res["secure_url"]


def publish_reel(video_url, caption):
    cont = ap.meta_post(f"{IG}/media",
                        {"media_type": "REELS", "video_url": video_url,
                         "caption": caption, "share_to_feed": "true",
                         "access_token": TOKEN})
    cid = cont["id"]
    for _ in range(36):                          # reels transcode async; poll up to ~6 min
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
    posts = ap._load_json(pj, []) if hasattr(ap, "_load_json") else (
        json.load(open(pj)) if os.path.exists(pj) else [])
    posts.append({"id": mid, "date": time.strftime("%Y-%m-%d"), "base": base,
                  "format": "reel", "category": meta.get("category"),
                  "pillar": meta.get("pillar"),
                  "caption": (meta.get("caption_en") or "")[:120]})
    json.dump(posts, open(pj, "w"), indent=1)


def main():
    if not TOKEN:
        raise SystemExit("Missing META_ACCESS_TOKEN.")
    vids = sorted(f for f in glob.glob(os.path.join(SRCV, "*"))
                  if f.lower().endswith(VIDEO_EXT))
    if not vids:
        print("No videos in source-videos/. Nothing to post.")
        return
    ap.git_setup()
    video = vids[0]
    base = os.path.splitext(os.path.basename(video))[0]
    note = ""
    npath = os.path.splitext(video)[0] + ".txt"
    if os.path.exists(npath):
        note = open(npath, encoding="utf-8").read()

    learn = ap.performance_brief()
    meta = ap.caption_for(frame_bytes(video), note, ap.TAGS, learn)

    hashtags = " ".join("#" + t.lstrip("#") for t in meta.get("hashtags", []))
    mentions = " ".join(m if m.startswith("@") else "@" + m for m in meta.get("tags", []))
    caption = "\n\n".join(p for p in [meta.get("caption_en", ""), meta.get("caption_es", ""),
                                      mentions, hashtags] if p).strip()

    print("Uploading clip to Cloudinary…")
    url = upload_to_cloudinary(video)
    print("Publishing reel…")
    mid = publish_reel(url, caption)
    print("Reel published:", mid)

    log_post(mid, base, meta)
    os.replace(video, os.path.join(POSTEDV, os.path.basename(video)))
    if os.path.exists(npath):
        os.replace(npath, os.path.join(POSTEDV, os.path.basename(npath)))
    with open(os.path.join(POSTEDV, base + ".caption.txt"), "w", encoding="utf-8") as f:
        f.write(caption)
    ap.commit_push(f"Posted reel {base} [skip ci]")
    print("Done.")


if __name__ == "__main__":
    main()
