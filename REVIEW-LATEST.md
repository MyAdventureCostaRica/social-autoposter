# Latest review — 2026-08-15

### 1. Readout

By today's standards, our signal pool comprises 39 eligible posts (34 within the last 12 months out of 148 tracked with insights). The live currency for the account is overwhelming **likes (84.3%)** followed distantly by **shares (6.9%)**, while **saves remain near non-existent at 0.8%** and comments sit at 3.8%. High-reach distribution is dominated by video: Reels represent 28 of our 39 eligible posts and power the highest raw reach numbers (e.g., Reach: 238 with 12.18% engagement on 2026-07-23; Reach: 212 on 2026-07-08). Thematically, contemplative journeys that pair endurance with quiet immersion outperform purely descriptive scenes—exemplified by top-performing lines such as *"Some roads feel like they lead nowhere, and yet they take you everywhere"* (2026-07-23) and *"Some trails demand more than just endurance — they ask for resilience, focus..."* (2026-06-19).

---

### 2. Proposed Changes

Given our modest sample size ($n=39$ eligible, 21 unlabeled historical posts), we remain humble and avoid over-fitting.

1. **Retain Learner Thresholds (`REACH_FLOOR: 50`, `HALFLIFE_DAYS: 90`, `SAVES_DEAD: 0.05`):**
   * *Data Justification:* The current `REACH_FLOOR` of 50 captures high-signal posts cleanly (e.g., 2026-07-24 cleared floor at 56 reach; 2026-06-24 at 54 reach). With saves accounting for only 0.8% of total interactions, saves remain well beneath the `SAVES_DEAD` 0.05 (5%) threshold, correctly signaling that saves are not currently a viable optimization target. No threshold delta is required.
2. **Update Captioner Brief Hook Guidance (`BRAND_PROMPT`):**
   * *Data Justification:* Top performers consistently lead with introspective, perspective-shifting observations rather than pure geography. Posts opening with mindset-driven hooks achieved our highest engagement rates: *"Some roads feel like they lead nowhere, and yet they take you everywhere"* (12.18% eng, 238 reach) and *"Some trails demand more than just endurance..."* (13.46% eng, 104 reach).
   * *Proposed Brief Edit:* Instruct the writer to favor reflective, evocative opening hooks focused on the internal journey and elements before grounding the reader in the Costa Rican landscape, maintaining our formal *usted* voice and full brand name, *My Adventure Costa Rica*.
3. **Investigate 90-Day Insight Errors:**
   * *Data Justification:* `errored_posts_90d` currently sits at 11 posts (representing ~7.4% of tracked posts). We should verify media-type permissions and Graph API endpoint handling for non-standard formats to ensure no reach data is dropped.

---

### 3. 3 Experiments (Next 30 Days)

1. **The Introspective Hook in Video Reels (ROUTE & RUNNING / CYCLING)**
   * **Hypothesis:** Opening Reels with a philosophical reflection on movement and nature (e.g., endurance, quiet mornings, solitude) will yield higher shares and double-digit engagement compared to purely descriptive scene openers.
   * **Metric:** Engagement Rate (Total Interactions / Reach) targeting $>8.0\%$, and raw Share count ($>1$ share/post).
   * **Duration:** 30 days.

2. **Multi-Discipline Elevation via 'RUNNING' & 'CYCLING' Pillars**
   * **Hypothesis:** Actively alternating between Cycling ($n=5$, avg eng 5.81%) and Running ($n=5$, avg eng 6.55%) under the *ROUTE* pillar will sustain higher average reach ($>150$) over generic scenic content (*COSTA RICA* category: 4.91% avg eng over $n=7$).
   * **Metric:** Average Reach per post across athletic categories vs. generic landscape posts.
   * **Duration:** 30 days.

3. **Share-Driven Closing Invocations**
   * **Hypothesis:** Since shares represent 6.9% of interactions while saves represent only 0.8%, concluding captions with an evocative, shareable invitation (e.g., invoking the feeling of sharing a quiet dawn or remote ascent with a companion) will lift overall share distribution without compromising our luxury-editorial restraint.
   * **Metric:** Share mix percentage (tracking movement from 6.9% toward $>10.0\%$).
   * **Duration:** 30 days.
