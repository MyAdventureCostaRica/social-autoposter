# Drop reel clips here

Put finished video clips (`.mp4` / `.mov`, ideally 9:16, under ~90s and under 100MB)
in this folder. Optionally add a same-named `.txt` note with true facts about the
clip (e.g. `descent.mp4` + `descent.txt`), exactly like the photo flow.

The **Post a reel** workflow takes the next clip, captions it from a frame using the
same brand voice + learner the photo poster uses, uploads it to Cloudinary, publishes
it as an Instagram Reel, and moves it to `posted-videos/`.

Needs the `CLOUDINARY_URL` repo secret (a free Cloudinary account). Runs Tue & Fri at
noon Costa Rica, or on demand from the Actions tab.
