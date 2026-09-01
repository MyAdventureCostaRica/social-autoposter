# Latest review — 2026-09-01

### 1. Readout: Performance by Today's Standards

With a highly focused signal pool of 46 eligible posts (41 within the last 12 months), our data signals are directional but clear. 

*   **The Live Currency:** Likes dominate raw volume at 84.1% of the interaction mix, but **shares (6.5%)** represent our primary organic distribution currency. **Saves are exceptionally quiet at 0.8%**, indicating that our audience prefers immediate social sharing over archiving.
*   **Format Performance:** Carousels are our most engaging format at an **11.79% average engagement rate**, though the sample size is small (n=4). Singles follow at **7.69% (n=8)**. Reels remain our operational workhorse with **5.21% (n=31)**, proving they are reliable for consistent reach (e.g., a July 23 Reel reached 239 accounts with a 12.13% engagement rate).
*   **Pillar & Category Leaders:** **ROUTE** is our undisputed champion pillar at **6.58% engagement rate (n=19)**. Within categories, **RUNNING (7.06% ER, n=7)** and **CYCLING (6.53% ER, n=8)** lead the portfolio, while general COSTA RICA content trails at **4.87% ER (n=7)**.
*   **Creative Themes:** Our top-performing posts lean heavily into sensory, atmospheric, and quiet luxury. Captions that evoke solitude and nature—such as *"misty mornings,"* *"high, open pastures,"* *"a still moment beneath the towering volcano,"* and *"suspended between the forest floor and the mist"*—consistently outperform purely athletic or promotional copy.

---

### 2. Proposed Changes

Given the thin but highly consistent nature of our recent data, we propose the following adjustments to the learner thresholds and the captioner brief to better align with what is resonating:

#### Learner Threshold Adjustments (Proposed as Deltas)
1.  **SAVES_DEAD: Decrease by -0.03 (New Value: 0.02)**
    *   *Justification:* Saves represent only 0.8% of our interaction mix. The current threshold of 0.05 is too high and risks penalizing high-performing posts that simply reflect our audience's natural aversion to saving content.
2.  **HALFLIFE_DAYS: Increase by +30 days (New Value: 120 days)**
    *   *Justification:* With only 41 eligible posts in the last 12 months, our dataset is sparse. Extending the half-life ensures the learner retains memory of our high-performing summer carousels and reels for a slightly longer period, preventing premature degradation of successful signals.
3.  **REACH_FLOOR: No change (Keep at 50)**
    *   *Justification:* Our top-performing carousels from August 15 had reaches of 53 and 63. Raising this floor would exclude these highly engaging posts (15.09% and 11.11% engagement rates, respectively) from our learning pool.

#### Captioner Brief (`BRAND_PROMPT`) Refinements
*   **Double down on "Quiet Luxury" and Sensory Openings:** Instruct the writer to open captions with atmospheric, sensory imagery rather than action-oriented hooks. Use the top-performing posts as stylistic benchmarks (e.g., referencing the stillness of the dawn, the mist of the cloud forest, or the high pastures).
*   **Optimize for Shares over Saves:** Since shares (6.5%) vastly outpace saves (0.8%), adjust the call-to-value. Instead of prompting users to "save this route," invite them to share the feeling of the journey with someone who appreciates the quiet corners of the world.
*   **Maintain Brand Standards:** Reinforce that all copy must be in elegant Spanish using the formal *usted* voice, and always use the full brand name, **My Adventure Costa Rica**, never an acronym.

---

### 3. Three Experiments for the Next 30 Days

To safely test these insights without disrupting our core consistency, we propose the following three experiments:

#### Experiment 1: The "Atmospheric Carousel" Format Test
*   **Concept:** Post two multi-slide carousels focusing on the **ROUTE** pillar (specifically CYCLING or RUNNING), utilizing misty, high-altitude imagery. The copy will focus entirely on the sensory experience of the terrain rather than technical route details.
*   **Metric of Success:** Engagement Rate (targeting >10.0%) and Reach.
*   **Duration:** 30 days.

#### Experiment 2: Share-Optimized "Usted" Closings
*   **Concept:** In our next four Reels, replace any passive endings with a soft, elegant invitation to share, written in formal Spanish. For example: *"Comparta este rincón de paz con quien comparta su pasión por el camino."*
*   **Metric of Success:** Share Rate (Shares / Total Interactions, targeting >8.0%).
*   **Duration:** 30 days.

#### Experiment 3: Technical Health Restoration
*   **Concept:** Investigate and resolve the 13 errored posts from the last 90 days. This is a high priority to ensure our publishing pipeline is clean and that we are not losing valuable engagement data due to API or media formatting errors.
*   **Metric of Success:** Zero errored posts in the next 30-day window.
*   **Duration:** Immediate / 14 days.
