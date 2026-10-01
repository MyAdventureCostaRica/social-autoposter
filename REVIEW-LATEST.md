# Latest review — 2026-10-01

### 1. Data Readout (October 2026)

* **The Live Currency:** Shares (5.8% of the interaction mix) are our primary organic growth driver, while Saves (0.8%) are practically dormant. Likes remain the baseline interaction at 84.5%.
* **Format Performance:** Carousels are our clear editorial leader with a **13.16% average engagement rate** ($n=6$), while Reels act as our primary reach vehicle, pulling in our peak reach of 240 on 2026-07-23 despite a lower average engagement rate of 5.41% ($n=36$).
* **Pillar & Category Strength:** The **ROUTE** pillar is our most reliable asset with a **6.26% average engagement rate** across a robust sample size ($n=24$). **CYCLING** (8.81% ER, $n=10$) and **RUNNING** (7.05% ER, $n=10$) heavily outperform general **COSTA RICA** travel content (3.86% ER, $n=10$).
* **Narrative Themes:** Our top-performing posts are deeply personal, reflective, and visceral. Captions focusing on physical resilience (e.g., racing after a heart attack, pushing through the last 10km of a 50K) and the philosophy of exploration (e.g., "the mountain sets the pace," "scouting unmarked routes") consistently generate engagement rates between 10.9% and 16.3%.
* **Timing Patterns:** Saturday is our premier publishing day, averaging **548 reach and 11 shares** ($n=10$). Mondays are exceptionally weak, averaging just 93 reach ($n=4$). The midday window between 11:00 and 15:00 CR time yields the highest concentration of shares.

---

### 2. Proposed System Adjustments

#### A. Learner Threshold Updates (`autopost.py`)
1. **Lower `SAVES_DEAD` from `0.05` to `0.01` (1%):** 
   * *Justification:* Saves represent only 0.8% of our total interaction mix. The current 5% threshold is too punitive for highly successful posts that simply do not generate saves. Lowering this to 1% prevents the algorithm from discarding high-reach, highly shared posts.
2. **Maintain `REACH_FLOOR` at `50` and `HALFLIFE_DAYS` at `90`:**
   * *Justification:* Our top-performing recent posts (such as the 2026-09-25 carousel at 55 reach and the 2026-09-13 carousel at 52 reach) sit just above the floor of 50. Raising it would starve the learner of our best qualitative data, while lowering it would introduce too much low-engagement noise. A 90-day halflife remains perfectly balanced for our current volume of 51 eligible posts over the last 12 months.

#### B. Captioner Brief Updates (`BRAND_PROMPT`)
To align our automated writer with what actually resonates, we propose updating the `BRAND_PROMPT` instructions:

* **Incorporate Visceral Philosophy:** Shift the tone from descriptive luxury travel to a more reflective, poetic, and athletic perspective. The terrain of Costa Rica should not merely be described; it should be treated as an active participant that "sets the pace" (*la montaña impone el ritmo*).
* **Elevate the Founder's Voice:** When writing under the **FOUNDER** or **ROUTE** pillars, use a tone of humble expertise. Frame challenges not as conquests, but as lessons in resilience, patience, and respect for the natural world.
* **Strict Brand & Language Guardrails:** Re-emphasize that the brand must always be referred to as **My Adventure Costa Rica** (never abbreviated). All Spanish copy must strictly use the formal *usted* to maintain an elegant, respectful, and high-end editorial distance.

---

### 3. Three Experiments for the Next 30 Days

#### Experiment 1: The "Visceral Hook" Format
* **Hypothesis:** Opening captions with a short, poetic, single-sentence philosophical statement in formal Spanish (inspired by our top-performing "the mountain sets the pace" posts) will increase carousel swipe-through rates and engagement.
* **Execution:** For the next 4 carousel posts, structure the caption to begin with a bold, italicized, one-line reflection on endurance or nature before introducing the specific route.
* **Metric of Success:** Engagement Rate (Target: >12%).

#### Experiment 2: Saturday Morning Route Showcases
* **Hypothesis:** Since Saturdays yield our highest average reach (548, $n=10$) and shares, publishing our highest-quality **ROUTE** carousels during this window will maximize organic distribution.
* **Execution:** Schedule our premier cycling or running ROUTE carousel specifically for Saturday mornings at 08:00 CR time.
* **Metric of Success:** Reach (Target: >400) and Shares per post.

#### Experiment 3: The "Resilience" Narrative (FOUNDER Pillar)
* **Hypothesis:** Audiences connect deeply with raw, human vulnerability over polished marketing. Introducing a post that touches on overcoming physical adversity or the mental battle of endurance will drive higher sharing.
* **Execution:** Generate a post under the FOUNDER pillar focusing on the quiet, demanding moments of trail preparation or recovery, emphasizing the mental discipline required by the Costa Rican topography.
* **Metric of Success:** Shares and Comments (Target: >8% combined interaction share).
