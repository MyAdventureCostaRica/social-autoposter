# Social Voice Guide — My Adventure Costa Rica

*v4, September 29 2026. Rewritten after the owner's verdict on the September captions ("too robotic, it has no essence… describing everything on the picture like grass, and metal bridges") and a study of the accounts that do this well. This file is the canonical reference; `autopost.py`'s BRAND_PROMPT enforces it and `caption_violations()` checks every caption against the banned patterns before it is used. What did not change from v3 (August 2026): the reader is "you", the register is plain and warm, nothing is sold except on EXPERIENCE posts and there only with published facts, and there is no first person without a note.*

## The voice in one paragraph

Written in English, as a guide who was there, to one future guest. The subject is the place, the guest or a decision: never the company, never praise, never the person behind the camera. Every caption takes ONE angle and says it in the first line. The photo is evidence for something it cannot show on its own; it is never the subject.

## The diagnosis (why the September captions read as machine writing)

One test catches them all: could someone who has never been to Costa Rica write this from the photo alone? Each went setting, then a list of what is visible, then a lesson. "Pace" and "quiet" recurred. Long balanced sentences, semicolons, em dashes, no line breaks. No person, no time of day, no decision, nothing at stake. The old brief caused most of it: it asked for "two concrete things in the photo", "what is ACTUALLY in the photo" and "the lesson", it carried tone words that leaked into the captions, and its example captions were copied almost word for word.

## The rules (mirrored in BRAND_PROMPT)

1. **Truth.** Only the photo's note, the PUBLISHED FACTS block, and what any experienced guide knows is universally true. No number, species, place or cause from anywhere else. No place unless the note gives it.
2. **The photo is evidence, not the subject.** Never list what is visible. At most one visible thing, and only as evidence for something the photo cannot show.
3. **One angle per caption:** a decision · a rule of the place · a moment (from the note) · the cost · outside the frame · a question a future guest would ask. Never repeat the angle, the opener or the key nouns of the last 10 captions (they are passed to the model).
4. **Structure.** Line 1 carries the whole idea in 125 characters or fewer. Then 1 to 3 short sentences that pay it off. One beat per line. Numerals, never spelled-out numbers.
5. **Length.** Short: 8 to 30 words. Long: 60 to 150 words, only when the note or the published facts carry a story or a fact worth teaching. Never padding.
6. **Point of view.** "You" by default. "We" only for published facts on an EXPERIENCE post. "I" only when the note holds the founder's own experience, with the specific result first. Never "I" for credentials or general wisdom.
7. **Endings.** Stop on the last concrete thing. About 1 in 4: one real question about the reader's own choice or experience. About 1 in 8: one line inviting them to send it to a friend. Never a moral or a summary.
8. **Scenery with no note:** short, one rule of the place or one published fact the image supports.
9. **The founder in the photo:** the task or the moment, not him. Never a title or certification he does not hold.
10. **Selling** (EXPERIENCE posts only, about 1 in 7): one or two lines of published facts, then "Details in the bio." No dates, no prices, no urgency.

## Banned patterns (the pattern, not just the words)

Listing the frame ("framed by", "a horizon of", "lush") · definition or setting openers ("X means…", "Out here", "Up here", "nestled", "in the heart of") · sayings about pace, rhythm, terrain or maps · "not this, but that" in any wording · lists of three · morals ("reveals itself", "reminds you", "you learn quickly") · tone words used as content (quiet, stillness, silence, slow, unhurried, serene, peaceful) · invented senses and absolutes ("the only sound", "nothing but") · empty praise (breathtaking, stunning, vibrant, magical, iconic, hidden gem, paradise, pristine, epic) · personified nature · self-praise or credentials · em dashes, semicolons, emoji, exclamation marks, more than one question · Spanish.

`caption_violations()` catches what a regex can see (all of the above plus first person without a note, a first sentence over 125 characters, fewer than 8 words, more than 170) and asks the model for ONE rewrite with the reasons; the cleaner of the two answers is used and the run summary reports anything still flagged. `Caption preview (voice check)` in the Actions tab captions the next few photos without posting, for calibration.

## The voice, demonstrated (register only; never copy a line)

**A decision (steel footbridge on a bike route):**
> Ride it or walk it?
> Dry deck: ride it, eyes on the far end, not your front wheel. Wet deck: walk it. Wet steel and cleats are a bad mix.
> Walking costs you a minute. A fall costs you the day.

**A rule of the place (highland pasture):**
> Pasture rule, on a bike or on foot: leave every gate as you found it. This is someone's farm before it is anyone's view.

**The cost (river at dawn):**
> Why the alarm before sunrise?
> There are no long summer evenings this close to the equator. The sun sets around 5 to 6 p.m. all year, so the good hours sit at the front of the day.
> Paddle out while the water still looks like this.

**A moment, from a note (the founder fixing a bike; every specific comes from the note):**
> Km 38 of the Nosara loop, a torn sidewall on the descent. 12 minutes to boot it and fit a tube while the group waited in the shade across the road.
> Tyre boots have lived in my saddlebag ever since.

**EXPERIENCE (the only sell):**
> 9 days from the Cordillera de Talamanca to the Osa Peninsula, 6 to 8 athletes, about 93 km of running. Day 4 is a 25 km self-supported descent from Providencia to San Isidro.
> Details in the bio.

## The biggest lever

A one-line note next to the photo (`IMG_123.txt`: where, when, who, what happened, what you decided). That is how the accounts studied get captions from people who were there. Without a note the caption can only be a rule of the place or a published fact, and it stays short.

## Sources

**Captions studied (Sep 2026):** Pelorus (Greenland scouting), Eleven Experience (Irwin), Montane on Jenny Tough, Kilian Jornet, Lael Wilcox, Awasi (Paraná), Alastair Humphreys, Run the Alps (2027 tours), Rickey Gates (Pecos). **Research:** John Smock, "Writing photo captions" (IJNet) · Chekhov's 1886 letter on small details · Lottie Gross, Talking Travel Writing (2025) · Packard & Berger, *Journal of Consumer Research* 2021 (concrete language raised purchases about 13%) · Nat Geo's first-person captions (Campaign, 2017) · Black Tomato (Shorty Awards) · Sendible on the 125-character fold · Socialinsider caption-length study (9.1 million posts, 2023: under 30 words performed best) · Hootsuite long-caption experiment (2021) · Mosseri on "sends per reach" · Wikipedia, "Signs of AI writing" · Raptive study on trust in AI-written content (2025). **Kept from v3:** Berger & Milkman, *What Makes Online Content Viral?* · the 2026 slow-travel and quiet-luxury trend pieces that justify the calm register.
