# Fully automatic posting — setup ($0, no payment method anywhere)

What this does: every day, a free cloud job picks the next photo you've added,
writes an on-brand bilingual caption (using GitHub's built-in free AI, loaded
with your Spanish Voice Guide and brand rules), renders the branded post, shows
it to you for a one-tap approval, and publishes it to Instagram (and Facebook).

Cost: **$0.** Public GitHub repo = unlimited free Actions minutes; captions use
GitHub's free built-in AI (no key, no card); the Meta API is free. Nothing here
attaches a payment method.

Your IDs are already filled in (`config.json`):
Facebook Page 1495946694015283 · Instagram @myadventurecostarica 17841403481255550.

---

## Part 1 — Put the code on GitHub (one time, ~10 min)

1. Make a free account at **github.com** (skip if you have one).
2. **New repository** → name `social-autoposter` → **Public** (required so
   Instagram can fetch the images; only finished posts live here, never your token)
   → **Create repository**.
3. On the repo page: **uploading an existing file**.
4. Open this `gh-poster` folder and drag **everything inside it** into the browser:
   `autopost.py`, `config.json`, the `fonts` folder, the `source-photos` folder,
   and the **`.github`** folder (it holds the schedule — make sure it goes up; if
   the browser won't take it, tell me and I'll give you a one-line alternative).
5. **Commit changes.**

## Part 2 — Get a non-expiring access token (one time, ~5 min)

1. Go to **developers.facebook.com/tools/explorer**.
2. Meta App = *My Adventure Costa Rica* → **Generate Access Token** → approve
   (keep all permissions on; select your Page and Instagram).
3. Click the **ⓘ** next to the token → **Open in Access Token Tool**.
4. Click **Extend Access Token** (makes it long-lived).
5. Back in the Explorer, in the **User or Page** dropdown pick your **Page
   (My Adventure Costa Rica)**. The token shown is now a non-expiring Page token.
6. Copy it. (Optional: paste into the Access Token Tool — "Expires" should say **Never**.)

## Part 3 — Store the token as a secret (one time, ~2 min)

1. Repo → **Settings → Secrets and variables → Actions → New repository secret**.
2. Name `META_ACCESS_TOKEN` · Value = the token from Part 2 · **Add secret**.

## Part 4 — Turn on the approval "training wheels"

1. Repo → **Settings → Environments → New environment** → name it exactly
   **`review`** → Configure.
2. Check **Required reviewers**, add **yourself**, **Save protection rules**.

Now each day the post will pause and wait for your approval. When you're confident
in the quality, come back here and remove yourself as a reviewer (or delete the
`review` environment) — then it's fully hands-off forever.

---

## How a day works

1. At **9:00 AM Costa Rica time** the **prepare** job builds tomorrow's post and
   writes a preview (the image + the exact caption) into the run summary.
2. You get a GitHub email: *deployment waiting for review*.
3. Open the run → read the caption, see the image → if good, **Approve**. The
   **publish** job posts it. If you don't like it, reject — nothing is posted, and
   the photo stays in the queue.
4. Once approval is off (Part 4 reversed), step 2–3 vanish and it just posts.

**Test it right now:** repo → **Actions** tab → **Daily social post** →
**Run workflow**. Watch the prepare job, check the preview, approve, and confirm
the post appears on Instagram.

## Your only ongoing job: add photos

Upload photos to the **`source-photos`** folder whenever you restock (repo →
`source-photos` → **Add file → Upload files** → drag from phone/computer →
Commit). JPG, PNG, and HEIC all work. The daily job takes the oldest first,
skips weak shots automatically, and moves used ones to `posted/`.

## Notes

- **Facebook feed**: Instagram works immediately. Posting to the Facebook *Page
  feed* also needs the `pages_manage_posts` permission on the app — if FB posts
  don't show, tell me; it's a 2-minute add. Instagram is unaffected.
- **Change the time**: edit the `cron` line in `.github/workflows/daily-post.yml`
  (it's in UTC; 15:00 UTC = 9 AM Costa Rica).
- **If captions ever look wrong or a run fails**: open the Actions run to read the
  message, and tell me — the caption model is set in `config.json` ("caption_model")
  and is easy to adjust.
