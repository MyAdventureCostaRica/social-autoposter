# Latest review — 2026-06-30

# Monthly Performance Review: June 2026

## Readout

The data suggests that **reach** is the live currency for measuring success, as it is the most consistently available and meaningful metric across formats. Engagement metrics (likes, comments, shares, saves) skew heavily toward likes (82% of total interactions), but shares (8%) and saves (0.8%) are more indicative of audience value. Among formats, **single posts** lead in average engagement rate (0.0712) when excluding the single-story post. **Reels**, while underperforming in engagement rate (0.0412), have the highest potential for reach, as evidenced by the top-performing post (2,908 reach). Themes around Costa Rica’s natural beauty, wildlife, and adventure resonate well, with captions emphasizing reflection, wonder, and discovery.

## Proposed Changes

1. **Adjust REACH_FLOOR to 200**: The current top-performing posts in the past 12 months have a reach of 200+ (e.g., 228, 277, 2,908). This threshold will better filter for meaningful performance.
   
2. **Increase HALFLIFE_DAYS to 90**: Reels, which dominate reach, often gain traction over a longer period. Extending the half-life will better account for their delayed performance curve.

3. **Refine captioner brief to emphasize shareable insights and wonder**: The top-performing captions focus on moments of reflection, discovery, and awe (e.g., "a fleeting glimpse of squirrel monkeys" or "hidden in plain sight"). Update the brief to prioritize these tones and themes, emphasizing Costa Rica’s natural beauty and adventure.

4. **Deprioritize saves (SAVES_DEAD = 0)**: Saves account for only 0.8% of interaction mix and are not significant enough to warrant optimization. Focus instead on reach and shares.

## 3 Experiments

1. **Test shareable hooks in captions**  
   - **Action**: Begin captions with a one-line, shareable hook that sparks curiosity or awe (e.g., "Most people would walk right past this… 👀🐍").  
   - **Metric**: Shares per post.  
   - **Duration**: 30 days.

2. **Prioritize single posts for reach and engagement**  
   - **Action**: Post 3-4 single image posts per week, focusing on themes of reflection, preparation, and Costa Rica’s natural wonders.  
   - **Metric**: Engagement rate (likes + comments / reach).  
   - **Duration**: 30 days.

3. **Experiment with Reels featuring wildlife and action**  
   - **Action**: Create Reels showcasing Costa Rica’s wildlife (e.g., squirrel monkeys, snakes) and adventure activities (e.g., mountain biking), with captions that highlight fleeting moments of wonder.  
   - **Metric**: Reach per Reel.  
   - **Duration**: 30 days.

---

Let me know if you approve these changes and experiments, and I’ll implement the updates to the system.
