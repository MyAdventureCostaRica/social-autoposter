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
import os, json, time, urllib.request, urllib.parse, urllib.error
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
    """Oldest video in the Cloudinary 'reels' folder not yet tagged 'posted', that is
    long enough and hasn't been rejected. Scoped to the folder ON PURPOSE so stock
    SAMPLE videos can never post. Skips clips shorter than reel_min_seconds (super-short
    clips were slipping through) and any clip you've rejected from the dashboard."""
    import cloudinary, cloudinary.search
    min_s = float(ap.CFG.get("reel_min_seconds", 5))
    rejected = set(ap.rget("rejected_clips", []) or [])
    try:
        r = (cloudinary.search.Search()
             .expression("resource_type:video AND (folder:Reels OR folder:reels) AND -tags:posted")
             .sort_by("created_at", "asc").max_results(50).execute())
    except Exception as e:
        print("Cloudinary search error (no reel posted):", e)
        return None
    for v in r.get("resources", []):
        dur = float(v.get("duration") or 0)
        if dur and dur < min_s:                       # too short for good reach — evict it
            pid = v.get("public_id")
            print(f"Too-short clip ({dur:.1f}s < {min_s}s) — moving out of the Reels folder:", pid)
            try:
                import cloudinary.uploader
                cloudinary.uploader.rename(pid, "reels-too-short/" + pid.split("/")[-1],
                                           resource_type="video")
            except Exception as e:
                print("evict skipped (left in place):", e)
            continue
        if v.get("public_id") in rejected:
            print("Skipping a rejected clip:", v.get("public_id")); continue
        return v
    return None


def thumb_bytes(public_id):
    import cloudinary.utils
    url = cloudinary.utils.cloudinary_url(public_id, resource_type="video",
                                          format="jpg", start_offset="1", secure=True)[0]
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def wait_until_ready(url, tries=12, wait=15):
    """Cloudinary builds the H.264 mp4 on the FIRST request for that delivery URL. Until
    it is done the URL answers 423/5xx — and Instagram, which fetches it exactly once,
    reports "Media upload has failed with error code 2207076" (Sep 11–12 2026, same clip
    two mornings running). So we ask for the first byte ourselves and only hand the URL
    to Instagram once it is actually servable."""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                if r.status in (200, 206):
                    if i:
                        print(f"Video URL ready after ~{i * wait}s")
                    return True
                last = r.status
        except urllib.error.HTTPError as e:
            last = e.code
            if e.code not in (423, 425, 429, 500, 502, 503, 504):
                print(f"Video URL answered HTTP {e.code} — not a transcode wait, giving up")
                return False
        except Exception as e:
            last = str(e)[:80]
        print(f"Video not servable yet ({last}) — waiting {wait}s…")
        time.sleep(wait)
    return False


def publish_reel(video_url, caption, attempts=3):
    """Create the reel container, wait for Instagram to process it, publish. Retries the
    whole thing (a fresh container) on an upload/processing error — those are usually
    transient on Meta's side or a not-yet-transcoded delivery URL."""
    if not wait_until_ready(video_url):
        raise RuntimeError("video URL never became servable (Cloudinary transcode?) — "
                           "not handing it to Instagram")
    last_err = None
    for attempt in range(1, attempts + 1):
        try:
            cont = ap.meta_post(f"{IG}/media",
                                {"media_type": "REELS", "video_url": video_url,
                                 "caption": caption, "share_to_feed": "true",
                                 "access_token": TOKEN})
            cid = cont["id"]
            code, status = None, ""
            for _ in range(36):                   # reels transcode async; poll up to ~6 min
                time.sleep(10)
                st = get(cid, {"fields": "status_code,status", "access_token": TOKEN})
                code, status = st.get("status_code"), st.get("status")
                if code in ("FINISHED", "ERROR"):
                    break
            if code != "FINISHED":                # ERROR, or still processing after 6 min
                raise RuntimeError(f"Reel processing {'failed' if code == 'ERROR' else 'timed out'}: "
                                   f"{status or code}")
            pub = ap.meta_post(f"{IG}/media_publish",
                               {"creation_id": cid, "access_token": TOKEN})
            return pub.get("id")
        except Exception as e:
            last_err = e
            print(f"Reel publish attempt {attempt}/{attempts} failed: {e}")
            if attempt < attempts:
                time.sleep(45 * attempt)          # 45 s, then 90 s
    raise RuntimeError(f"Reel publish failed after {attempts} attempts: {last_err}")


def publish_fb_reel(video_url, caption):
    """Cross-post the same clip as a Facebook Page Reel (hosted-file upload:
    start -> upload-by-url -> finish/publish). Best-effort: never blocks the IG reel."""
    if "fb" not in ap.CFG.get("targets", []):
        return None
    page = ap.CFG["page_id"]
    try:
        start = ap.meta_post(f"{page}/video_reels",
                             {"upload_phase": "start", "access_token": TOKEN})
        vid, upload_url = start["video_id"], start["upload_url"]
        req = urllib.request.Request(
            upload_url, method="POST",
            headers={"Authorization": f"OAuth {TOKEN}", "file_url": video_url})
        with urllib.request.urlopen(req, timeout=120) as r:
            r.read()
        time.sleep(8)                              # let FB ingest the hosted file
        ap.meta_post(f"{page}/video_reels",
                     {"upload_phase": "finish", "video_id": vid,
                      "video_state": "PUBLISHED", "description": caption,
                      "access_token": TOKEN})
        print("Facebook Reel OK:", vid)
        return vid
    except Exception as e:
        print("Facebook Reel skipped:", e)
        return None


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
    # Guard: one reel per day. We schedule a backup attempt, so skip if already done.
    lr = os.path.join(HERE, "metrics", "last_reel.txt")
    today = time.strftime("%Y-%m-%d")
    if os.path.exists(lr) and open(lr).read().strip() == today:
        print("Already posted a reel today; skipping."); return
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
    meta = ap.caption_for(thumb_bytes(pid), note, ap.TAGS, learn,
                          hint="This caption is for a REEL. Keep it SHORT — 1-3 sentences, "
                               "under 400 characters (long reel captions reduce reach). "
                               "Same voice, just compact.")
    hashtags = " ".join("#" + t.lstrip("#") for t in meta.get("hashtags", []))
    mentions = " ".join(m if m.startswith("@") else "@" + m for m in meta.get("tags", []))
    caption = "\n\n".join(p for p in ap.caption_body(meta) + [mentions, hashtags] if p).strip()

    print("Publishing reel…")
    mid = publish_reel(video_url, caption)
    print("Reel published:", mid)
    publish_fb_reel(video_url, caption)            # cross-post to Facebook Reels

    cloudinary.uploader.add_tag("posted", pid, resource_type="video")
    base = pid.split("/")[-1]
    log_post(mid, base, meta)
    os.makedirs(os.path.join(HERE, "metrics"), exist_ok=True)
    open(os.path.join(HERE, "metrics", "last_reel.txt"), "w").write(today)
    ap.git_setup()
    ap.commit_push(f"Posted reel {base} [skip ci]")
    print("Done.")


def _do_publish_reel(state):
    """Actually publish a reel (IG + FB), tag it posted, log it, announce it live."""
    import cloudinary, cloudinary.uploader
    config_cloudinary()
    video_url, caption, pid = state["video_url"], state["caption"], state["public_id"]
    print("Publishing reel…")
    mid = publish_reel(video_url, caption)
    state["_ig_media_id"] = mid                       # marker: Instagram has it from here on
    print("Reel published:", mid)
    publish_fb_reel(video_url, caption)                # cross-post to Facebook Reels
    try:
        cloudinary.uploader.add_tag("posted", pid, resource_type="video")
    except Exception as e:
        print("tag 'posted' skipped:", e)
    base = state.get("base") or pid.split("/")[-1]
    log_post(mid, base, {"category": state.get("category"), "pillar": state.get("pillar"),
                         "caption_en": state.get("_caption_en", "")})
    os.makedirs(os.path.join(HERE, "metrics"), exist_ok=True)
    open(os.path.join(HERE, "metrics", "last_reel.txt"), "w").write(time.strftime("%Y-%m-%d"))
    perm = ""
    try:
        with urllib.request.urlopen(
                f"https://graph.facebook.com/{V}/{mid}?fields=permalink&access_token={TOKEN}",
                timeout=30) as r:
            perm = (json.loads(r.read().decode()) or {}).get("permalink", "")
    except Exception as e:
        print("permalink skipped:", e)
    ap.rset("last_published", {"base": base, "pillar": state.get("pillar"), "format": "reel",
                               "image": state.get("thumb_url", ""), "media_id": mid,
                               "permalink": perm, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
    ap.wa_notify(f"✅ Reel live — {(state.get('pillar') or 'reel').title()}. "
                 + (f"View: {perm}" if perm else "Check Instagram."))
    ap.git_setup()
    ap.commit_push(f"Posted reel {base} [skip ci]")
    print("Done.")


def stage_reel():
    """Find the next clip, caption it, and STAGE it for approval (publish now only if
    auto-approve is on). Never posts on its own."""
    if not TOKEN:
        raise SystemExit("Missing META_ACCESS_TOKEN.")
    lr = os.path.join(HERE, "metrics", "last_reel.txt")
    today = time.strftime("%Y-%m-%d")
    force = os.environ.get("FORCE_POST") == "1"
    if not force and os.path.exists(lr) and open(lr).read().strip() == today:
        print("Already staged/posted a reel today; skipping."); return
    config_cloudinary()
    ing = ap.rget("ingest_video", None)
    if ing and ing.get("public_id"):
        ap.rdel("ingest_video")
        import cloudinary.api, cloudinary.utils
        try: info = cloudinary.api.resource(ing["public_id"], resource_type="video")
        except Exception: info = {}
        # Always hand Instagram an H.264 .mp4 delivery URL. The browser-side compressor
        # may emit .webm, which Instagram will not accept; Cloudinary transcodes on delivery.
        clip = {"public_id": ing["public_id"],
                "secure_url": cloudinary.utils.cloudinary_url(
                    ing["public_id"], resource_type="video", secure=True,
                    format="mp4", video_codec="h264")[0],
                "duration": info.get("duration") or 0}
        print("Ingesting uploaded reel:", ing["public_id"])
    else:
        clip = next_clip()
    manual = bool(ing and ing.get("public_id"))   # the owner uploaded this clip himself
    if not clip:
        print("No eligible clips (none long enough, or all posted/rejected)."); return
    pid = clip["public_id"]
    dur = float(clip.get("duration") or 0)
    note = ((clip.get("context") or {}).get("custom") or {}).get("note", "")
    print("Clip:", pid, f"({dur:.1f}s)")
    learn = ap.performance_brief()
    meta = ap.caption_for(thumb_bytes(pid), note, ap.TAGS, learn,
                          hint="This caption is for a REEL. Keep it SHORT — 1-3 sentences, "
                               "under 400 characters (long reel captions reduce reach). "
                               "Same voice, just compact.")
    hashtags = " ".join("#" + t.lstrip("#") for t in meta.get("hashtags", []))
    mentions = " ".join(m if m.startswith("@") else "@" + m for m in meta.get("tags", []))
    caption = "\n\n".join(p for p in ap.caption_body(meta) + [mentions, hashtags] if p).strip()
    import cloudinary.utils
    thumb_url = cloudinary.utils.cloudinary_url(pid, resource_type="video", format="jpg",
                                                start_offset="1", secure=True)[0]
    state = {"type": "reel", "public_id": pid, "video_url": clip["secure_url"],
             "thumb_url": thumb_url, "duration": round(dur, 1), "caption": caption,
             "pillar": meta.get("pillar"), "category": meta.get("category"),
             "base": pid.split("/")[-1], "status": "pending",
             "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "_caption_en": meta.get("caption_en", "")}
    if (ap.rget("settings", {}) or {}).get("auto_approve"):
        # Owner's rule (Sep 10/14 2026): a clip he uploaded himself, OR a "Prepare a reel"
        # button press (FORCE_POST), is HIM asking — it posts now. The morning hold applies
        # only to clips the scheduler picked on its own.
        human = manual or os.environ.get("FORCE_POST") == "1"
        hold = None if human else ap.morning_hold_iso()
        if hold:
            state["status"] = "approved"; state["hold_until"] = hold
            _requeue_prev_reel(state)                 # never discard what's already waiting
            ap.rset("pending_reel", state)
            ap.git_setup()
            open(os.path.join(HERE, "metrics", "last_reel.txt"), "w").write(today)
            ap.commit_push("Stage reel (auto-approved, held for morning) [skip ci]")
            ap.wa_notify("Reel auto-approved — publishes at 8:00 AM (best-hours window). " + ap.DASHBOARD_URL)
            print("Auto-approve ON but outside the 08–15 CR window — reel held until", hold)
            return
        print("Auto-approve ON — publishing reel now.")
        _do_publish_reel(state)
        # (this reel was never stored in the slot — an older undecided reel may still be
        #  waiting there; never wipe it)
    else:
        _requeue_prev_reel(state)                     # owner's queue rule
        ap.rset("pending_reel", state)
        ap.git_setup()
        open(os.path.join(HERE, "metrics", "last_reel.txt"), "w").write(today)  # don't double-stage
        ap.commit_push("Stage reel for review [skip ci]")
        ap.wa_notify(f"Reel ready to approve — {(meta.get('pillar') or 'reel').title()}, "
                     f"{round(dur, 1)}s. Review & approve: {ap.DASHBOARD_URL}")


def publish_pending_reel():
    """Publish the reel the owner APPROVED on the dashboard (read from Upstash)."""
    state = ap.rget("pending_reel")
    if not state or state.get("status") != "approved":
        print("No approved reel to publish."); return
    hu = state.get("hold_until")
    if hu:
        try:
            import datetime as _dt
            if time.time() < _dt.datetime.fromisoformat(hu.replace("Z", "+00:00")).timestamp():
                print(f"Approved reel held for the morning window (until {hu}) — skipping."); return
        except Exception:
            pass
    try:
        _do_publish_reel(state)
    except Exception as e:
        err = str(e)[:300]
        if state.get("_ig_media_id"):
            # Instagram already has the reel — only the follow-up failed. Never retry
            # (double post); free the slot and say what happened.
            ap.wa_notify(f"⚠️ Reel {state.get('base')} is live on Instagram but the follow-up "
                         f"failed ({err}). Check the run: {ap.DASHBOARD_URL}")
            ap.rdel("pending_reel"); _promote_next_reel()
        else:
            # Nothing posted. Hand it back to the owner WITH the reason — the card reappears
            # (Approve = retry, Reject, ↻ New caption) instead of failing silently at 08:05
            # every morning, which is what happened on Sep 11–12 2026.
            state["status"] = "pending"; state.pop("hold_until", None); state["last_error"] = err
            ap.rset("pending_reel", state)
            ap.wa_notify(f"❌ Reel {state.get('base')} could not be published: {err}. "
                         f"It's back on the dashboard — approve again to retry, or reject it. "
                         f"{ap.DASHBOARD_URL}")
        raise SystemExit(1)                       # keep the run red so the alert step fires too
    dec = ap.rget("post_decisions", []) or []
    dec.append({"base": state.get("base"), "pillar": state.get("pillar"), "format": "reel",
                "decision": "approved", "edited": bool(state.get("edited")),
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
    ap.rset("post_decisions", dec[-200:])
    ap.rdel("pending_reel")
    _promote_next_reel()                              # next queued reel takes the slot
    print("Published approved reel:", state.get("base"))


def _promote_next_reel():
    q = ap.rget("pending_reel_queue", []) or []
    while q:
        nxt = q.pop(0)
        ap.rset("pending_reel_queue", q)
        if nxt:
            nxt["status"] = "pending"; nxt.pop("hold_until", None)
            ap.rset("pending_reel", nxt)
            ap.wa_notify("Next queued reel is waiting for your approval: " + ap.DASHBOARD_URL)
            print("Promoted queued reel:", nxt.get("base"))
            return
    ap.rset("pending_reel_queue", q)


def _requeue_prev_reel(state):
    """Owner's queue rule ("reel, carousel, post, any type — you queue"): staging a new
    reel never discards the one already in the slot — pending OR approved-and-held — it
    joins pending_reel_queue (FIFO, 5). The held path used to overwrite it: on Sep 10–11
    2026 three evening reels were staged and two vanished."""
    prev = ap.rget("pending_reel")
    if prev and prev.get("status") in ("pending", "approved") and prev.get("base") != state.get("base"):
        q = ap.rget("pending_reel_queue", []) or []
        if not any((p or {}).get("base") == prev.get("base") for p in q):
            prev = dict(prev); prev["status"] = "pending"; prev.pop("hold_until", None)
            q.append(prev)
            ap.rset("pending_reel_queue", q[-5:])
            print("Queued the previous reel:", prev.get("base"))


if __name__ == "__main__":
    import sys
    phase = sys.argv[1] if len(sys.argv) > 1 else "stage"
    if phase == "publish_pending_reel":
        publish_pending_reel()
    elif phase == "all":
        main()                                    # legacy: find + publish immediately
    else:
        stage_reel()
