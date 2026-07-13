# Latest review — 2026-07-13

# Performance Review

## **Readout**

By today's standards, **reach** is the clearest live currency, as shares and saves remain negligible (7.3% and 0.8% of interactions, respectively). Recent data highlights a strong performance from **single-image posts**, which lead in engagement rate (0.0769) compared to reels (0.048). However, reels dominate in volume (20 out of 30 eligible posts) and consistently achieve higher reach (e.g., 232 vs. 104 for top single posts). Themes like **mountain biking, trails, and quiet moments in nature** resonate most, with captions emphasizing reflection and connection to the environment. The photo queue is healthy (182), but a significant number of posts (680) lack insights, limiting the dataset.

---

## **Proposed changes**

1. **Adjust REACH_FLOOR to 100 (from 50).**  
   Justification: The lowest-performing posts in the top set (reels with ~130 reach) already exceed the current floor. Raising this threshold will better filter for meaningful insights while still including the majority of eligible posts (25/30 in the past year).

2. **Increase HALFLIFE_DAYS to 60 (from 30).**  
   Justification: Reels dominate recent posts, and their performance often grows over time. Extending the halflife will allow the learner to better account for this delayed engagement pattern.

3. **Refine caption brief to emphasize reflection and connection.**  
   Justification: The top-performing captions (e.g., "Some trails demand more than just endurance — they ask for resilience, focus, and a willingness to embrace the elements") focus on introspective, evocative themes. Update the brief to explicitly encourage this tone, while still maintaining variety.

4. **Add a STOP list for overly generic hashtags.**  
   Justification: Posts with hashtags like `#myadventurecostarica` and `#costarica` underperform (e.g., 0.0388 engagement rate). These should be deprioritized in favor of more specific, niche hashtags tied to adventure, mountain biking, or Costa Rica’s unique landscapes.

---

## **3 experiments**

1. **Test single-image posts with reflective captions.**  
   - **What:** Post 4 single-image posts in the next 30 days, focusing on the themes of mountain biking, trails, and quiet moments in nature. Use captions that evoke resilience, connection to nature, and introspection.  
   - **Metric:** Engagement rate (likes + comments / reach).  

2. **Experiment with reels featuring dynamic action shots.**  
   - **What:** Post 6 reels showcasing action-packed moments (e.g., biking descents, river crossings) with a one-line opening hook in the caption to grab attention.  
   - **Metric:** Reach per reel.  

3. **Hashtag specificity test.**  
   - **What:** For all posts, replace broad hashtags like `#costarica` with niche ones tied to the activity or location (e.g., `#mountainbikingcostarica`, `#puravidatrails`).  
   - **Metric:** Reach and engagement rate compared to past posts using generic hashtags.  

---

Let me know which changes and experiments you'd like to proceed with, and I’ll implement them!
