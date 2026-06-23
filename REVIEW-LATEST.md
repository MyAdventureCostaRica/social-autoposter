# Latest review — 2026-06-23

# Monthly Social Media Performance Review

## **1. Readout**
The data indicates that **reach** is the dominant currency for performance, with shares and saves contributing minimally (8% and 0.9% of interactions, respectively). Recent posts show that **single-image posts** are outperforming other formats in engagement rate (0.0811 vs. 0.0695 for carousels and 0.0496 for reels). However, historical data suggests that **reels have the highest potential for reach**, with the top-performing posts in the last year being reels that achieved the highest reach (e.g., 990 on 2025-10-25). The **top themes** revolve around adventure, Costa Rica’s natural beauty, and endurance-focused activities like trail running. The **photo queue is healthy** with 216 images, but the high number of errored posts (675) suggests some past issues with posting consistency or system errors.

---

## **2. Proposed changes**
1. **Adjust REACH_FLOOR**:  
   Current reach floor is likely too high given that only **24 posts are eligible** and only **19 in the past 12 months**. Propose lowering the floor to **50 reach** to increase the pool of eligible posts for analysis. This would include more recent posts and help the system learn from current trends.  

2. **Revisit HALFLIFE_DAYS**:  
   The current top-performing posts are from October 2025 and earlier, indicating that older posts are still relevant but may be over-weighted. Propose reducing the half-life to **90 days** to better prioritize recent trends while still accounting for older performance.  

3. **Update captioner brief to emphasize single-image posts**:  
   Single-image posts have the highest engagement rate (0.0811) and should be prioritized for themes like Costa Rica’s natural beauty, adventure, and trail running. Update the brief to reflect this by encouraging evocative descriptions of single images, focusing on storytelling and emotional connection.  

4. **Deprioritize saves as a metric (SAVES_DEAD)**:  
   Saves are contributing only 0.9% to the interaction mix and are not a meaningful signal. Propose increasing SAVES_DEAD to **5%** to deprioritize this metric in performance calculations.  

---

## **3. Experiments**
1. **Test single-image posts with strong storytelling captions**:  
   Post 4 single-image posts over the next 30 days, each with a focus on storytelling and vivid descriptions of Costa Rica’s natural beauty or adventure themes. Use **engagement rate** as the primary metric to evaluate success.  

2. **Experiment with reels optimized for reach**:  
   Post 3 reels over the next 30 days, focusing on visually striking content (e.g., dramatic landscapes, wildlife, or action shots of trail running). Use **reach** as the primary metric to evaluate success, as reels historically have the highest reach potential.  

3. **Test call-to-action for shares**:  
   In 2 posts (1 single image, 1 reel), include a subtle call-to-action encouraging users to share (e.g., “Share this with someone who needs a little adventure in their life”). Use **shares** as the primary metric to evaluate success.  

---

Let me know if you'd like to approve these changes and experiments, or if further adjustments are needed!
