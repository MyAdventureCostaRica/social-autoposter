# Reels — how they work (videos do NOT go here anymore)

Clips are **not** dropped in this folder. Video lives in **Cloudinary** (the free
video host) because GitHub can't handle large video. To post a reel:

1. Upload the clip into **Cloudinary → Media Library** (any size).
2. The **Post a reel** workflow (Tue & Fri at noon Costa Rica, or run it manually
   from the Actions tab) finds the oldest clip not yet tagged `posted`, captions it
   from a frame in the brand voice + learner, publishes it as a Reel (it also shows
   in the feed), then tags it `posted` so it never reposts.

Auth is the `CLOUDINARY_URL` secret (or the three `CLOUDINARY_CLOUD_NAME` /
`CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` secrets).

## Format
- **Vertical 9:16, 1080×1920** is ideal (Insta360 reframed, or iPhone shot
  vertically). Landscape works but letterboxes. Keep clips under ~90s.

## Music (important)
- No API can add Instagram's **in-app / trending** audio to a reel — that's app-only.
- An auto-posted reel only carries the audio **baked into the video file**. So add
  **royalty-free music in your editor** (Epidemic, Artlist, Instagram-safe packs) and
  export it into the clip.
- For a reel where you specifically want a **trending sound** (and its reach boost),
  post that one **by hand from the app**. Automate the rest.
