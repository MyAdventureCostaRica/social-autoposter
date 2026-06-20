# Roadmap — My Adventure Costa Rica auto-poster

A living backlog. The system today is a strong *content* loop, but it optimizes the
middle of the funnel. The top (reach) and the bottom (bookings) are where the
leverage now is. Ordered by leverage, not effort.

## Shipped
- Daily auto-posting to Instagram (feed + Story) and Facebook, $0, hands-off.
- Captioner that writes to the four content pillars, ~80/20 value-to-invite.
- Full Instagram history backfilled (745 posts); daily insights refresh.
- **Learner** — each post is written *after* reading our own analytics, by today's
  standards (reach floor, recency-weighted, currency detected dynamically).
- Dashboard with reach/shares ranking + a "Latest review" panel.
- **Monthly review** in the cloud (GitHub Action + GitHub Models) → opens an issue
  that emails us + posts to the dashboard. Proposals stay human-approved.

## Now building
- **[1] Reels.** Our own data says reels are the winning format, but the poster can
  only do stills + carousels (video is blocked by GitHub's file-size cap). Add a
  free video host (Cloudinary) and a reels publishing path. *Highest leverage — the
  data is begging for it.*

## Prioritized next
- **[2] Booking funnel visibility.** We measure engagement (a proxy). Nothing tracks
  profile-visits → link taps → enquiries → bookings — the thing that actually pays.
  Start by capturing profile_visits + follows per post (the API exposes them), then
  link-click tracking. *Connects the system to the $1M goal.*
- **[3] Profile optimization** *(quick win)*. Posts drive people to a profile that was
  never tuned — bio, the link to myadventurecostarica.com, Story Highlights, action
  buttons. The bridge from reach to enquiry. Plan already written in
  PROFILE-OPTIMIZATION.md; just needs applying.
- **[4] Engage back, don't just broadcast.** No replies to comments/DMs, no engaging
  with others. Instagram rewards interaction, and DMs are where enquiries happen. A
  "where can I book this?" comment currently sits unanswered.
- **[5] Best-time-to-post** *(quick win once data exists)*. We post at a fixed 9am;
  the API knows when our followers are actually online. Free reach left on the table.
- **[6] Failure alarm** *(quick win)*. If the token dies or Meta changes something and
  posting silently breaks, we might not notice for days. Add a "post failed" alert.

## Backlog
- TikTok + YouTube Shorts (where short-video reach compounds).
- A light human eye before fully-unattended posts go public (optional review pause).
- Content *planning* (what to shoot next), not just caption tuning of what exists.
- Alt-text (accessibility + SEO) — API can't set it on publish; manual for now.

_Reviewed and re-prioritized as the monthly review surfaces new evidence._
