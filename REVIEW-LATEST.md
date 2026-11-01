# Latest review — 2026-11-01

### 1. Readout

* **Data pool & currency:** The analysis relies on a tight pool of 63 eligible posts (48 within the past 12 months out of 962 total posts). By today’s standards, **likes (86.2%)** dominate raw interaction volume, while **shares (5.1%)** act as the primary active distribution engine—outpacing **saves (0.7%)** by more than 7x. Saves are currently an inactive metric for audience expansion.
* **Format hierarchy:** Carousels lead in engagement rate at **13.02%** ($n=6$), followed closely by single images at **10.86%** ($n=13$). Reels average **4.89%** ($n=39$), indicating that while video represents our highest posting frequency, static and multi-slide visual storytelling delivers higher relative audience response per reach.
* **Pillars & Categories:** **FOUNDER** narratives achieve the highest engagement rate at **12.62%** ($n=4$), followed by **EXPERIENCE** (**6.17%**, $n=5$), **KNOWLEDGE** (**6.13%**, $n=5$), and **ROUTE** (**5.51%**, $n=26$). Among primary categories with sufficient data, **CYCLING** leads at **8.48%** ($n=12$), outperforming broader **COSTA RICA** content (**3.58%**, $n=10$).
* **Top Post Narrative Pattern:** Top-performing posts feature authentic personal endurance and scouting context—such as returning to racing at Moon Run Arenal (**14.81%** eng rate, reach 81) or midday heat adaptation on the coast (**18.37%** eng rate, reach 98).
* **Timing & Reach:** Weekend posting captures peak distribution, led by Saturday (avg reach **581**, 11 total shares, $n=12$) and Friday (avg reach **284**, 11 total shares, $n=15$). Weekdays lag substantially (e.g., Monday avg reach **94**, 0 shares, $n=4$).
* **Operational Alert:** The `photo_queue` currently sits at **0**, and **12 posts errored** over the past 90 days. Pipeline replenishment and token/API error resolution require immediate attention.

---

### 2. Proposed Changes

1. **Keep Learner Thresholds Unchanged (`REACH_FLOOR`: 50, `HALFLIFE_DAYS`: 90, `SAVES_DEAD`: 0.05)**
   * *Data Justification:* With 48 eligible posts in the 12-month window, keeping `HALFLIFE_DAYS` at 90 prevents severe data starvation. `REACH_FLOOR` at 50 preserves valuable carousel and route data points (e.g., top posts with reach 52–57). `SAVES_DEAD` at 0.05 (5%) accurately reflects the current 0.7% save rate without needing threshold adjustments. Proposing zero threshold deltas is the correct choice under current thin data conditions.

2. **Refine Captioner Brief (`BRAND_PROMPT`) — Prioritize Founder Experience & Shareable Knowledge**
   * *Data Justification:* `FOUNDER` content yields **12.62%** avg eng rate vs. `COSTA RICA` at **3.58%**. Furthermore, shares (**5.1%**) far exceed saves (**0.7%**).
   * *Proposed Edit:* Adjust prompt guidance to lean into first-person scouting notes, physical preparation, and honest reflection on the terrain of My Adventure Costa Rica. Softly prompt for content sharing (sending to a training partner) rather than bookmarking for later. Use formal Spanish (*usted*) whenever regional phrasing is integrated.

3. **Queue & Error Resolution Priority**
   * *Data Justification:* `photo_queue` = 0; `errored_posts_90d` = 12.
   * *Proposed Edit:* Audit scheduled asset pipeline and verify Instagram Graph API token permissions prior to initiating new prompt variations.

---

### 3. Experiments for Next 30 Days

* **Experiment 1: Founder-Led Carousel Storytelling**
  * **Hypothesis:** Combining our highest-performing pillar (**FOUNDER**, 12.62% eng rate) with our top format (**Carousel**, 13.02% eng rate) around **CYCLING** route scouting will exceed a 12.0% average engagement rate.
  * **Metric:** Engagement Rate & Shares per post.
  * **Scope:** 4 carousel posts over 30 days.

* **Experiment 2: Weekend Publishing Concentration**
  * **Hypothesis:** Scheduling high-value feature posts strictly on Friday and Saturday windows (Saturday avg reach **581** vs. weekday average reach **<220**) will increase average post reach by >35%.
  * **Metric:** Average Reach per post.
  * **Scope:** 8 posts (Fri/Sat schedule) over 30 days.

* **Experiment 3: Peer-Share Hook Structure for KNOWLEDGE Posts**
  * **Hypothesis:** Opening **KNOWLEDGE** captions with immediate personal physical reflections (e.g., midday heat, trail water crossings) rather than general advice will increase the share ratio beyond the current **5.1%** interaction baseline.
  * **Metric:** Shares per Reach ratio.
  * **Scope:** 4 KNOWLEDGE posts over 30 days.
