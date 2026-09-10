# Latest review — 2026-09-10

### 1. Readout
The data reveals a clear shift in performance: **Carousels** are currently our most potent format, commanding an engagement rate of 11.79% (n=4) compared to Reels at 5.21% (n=31). While Reels drive higher absolute reach (e.g., 239), the **live currency is Engagement Rate via Carousel storytelling**. Our audience is currently signaling a preference for "ROUTE" content (19 posts, 6.57% eng. rate) that focuses on the sensory experience of the landscape—specifically the "misty mornings" and "high, open pastures" identified in our top-performing captions. We are currently under-indexing on "KNOWLEDGE" content, which requires a pivot to ensure we remain the authority on Costa Rica, not just a gallery of its views.

### 2. Proposed Changes
Given the thin data on non-Reel formats (n=4 for carousels), we should remain humble and avoid aggressive re-tuning.

1.  **Learner Thresholds:** 
    *   **Keep `REACH_FLOOR` at 50:** While we have some high-performers, our average reach is still volatile; maintaining this floor ensures we only learn from posts that have cleared the "noise" threshold.
    *   **Keep `HALFLIFE_DAYS` at 90:** With only 41 eligible posts in the last 12 months, we need a longer window to ensure seasonal or evergreen content isn't prematurely discarded.
    *   **Keep `SAVES_DEAD` at 0.05:** Our current interaction mix is heavily skewed toward Likes (84.1%). Until we see a consistent rise in Saves (currently 0.8%), this metric is too thin to serve as a primary filter.
2.  **Captioner Brief (`BRAND_PROMPT`):**
    *   **Adjustment:** Explicitly instruct the writer to favor the "Carousel" format for "ROUTE" and "EXPERIENCE" pillars. 
    *   **Justification:** The 11.79% engagement rate for carousels significantly outperforms the 5.21% for reels. The brief should encourage a "narrative arc" across the slides (e.g., Slide 1: The Hook/View, Slide 2: The Technical Challenge, Slide 3: The Reward/Knowledge).

### 3. 3 Experiments (Next 30 Days)

1.  **The "Carousel Narrative" Test:** Convert 3 upcoming "ROUTE" posts from single/reel format into 4-slide carousels. Use the first slide for a high-impact visual and the final slide for a specific, actionable piece of "KNOWLEDGE" about the route.
    *   *Success Metric:* Compare the engagement rate of these carousels against our current 11.79% benchmark.
2.  **The "Knowledge-First" Hook:** In the next 5 posts, start the caption with a specific, non-obvious fact about Costa Rica (e.g., "The reason the mist clings to this specific valley is..."). 
    *   *Success Metric:* Monitor for an increase in "Shares" (currently 6.5%) as a proxy for value-add content.
3.  **The "Usted" Invitation:** In the final sentence of every caption, include a soft, formal invitation in Spanish: *"¿Le gustaría explorar esta ruta con nosotros?"* (Would you like to explore this route with us?).
    *   *Success Metric:* Track profile visits/follows per post to see if this formal, editorial tone drives higher conversion than our previous, more passive captions.

***

*Note: These proposals are for your review and approval. No automated changes have been applied to the system.*
