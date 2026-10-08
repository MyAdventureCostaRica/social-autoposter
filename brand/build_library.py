# Builds the curated photo library for the auto-poster from Esteban's OWN originals in the
# website project (never Unsplash, never third-party race frames), with a note per photo
# written from the website's own tour text. Run in the device VM.
import os, re, yaml, json
from PIL import Image, ImageOps
SITE = os.path.expanduser("~/mnt/My Adventure Costa Rica Website")
PICS = os.path.join(SITE, "My Adventure Costa Rica Pictures")
TOURS = os.path.join(SITE, "astro-site/src/content/tours/en")
DEST = os.path.expanduser("~/mnt/social-autoposter/source-photos")
os.makedirs(DEST, exist_ok=True)

def load_tour(name):
    t = open(os.path.join(TOURS, name), encoding="utf-8").read()
    fm = t.split("---")[1]
    return yaml.safe_load(fm)
def plain(s): return re.sub(r"<[^>]+>", "", s or "").replace("\n", " ").strip()
TR, GR, HK = load_tour("trail-running.md"), load_tour("gravel-cycling.md"), load_tour("hiking.md")
NAMES = {"TR": "The Trail Running Expedition (Episode 01, trail running)",
         "GR": "The Gravel Expedition (Episode 02, gravel cycling)",
         "HK": "The Hiking Expedition (Episode 03, hiking)"}
TOUR = {"TR": TR, "GR": GR, "HK": HK}

def day_text(key, n):
    t = TOUR[key]; d = [x for x in t["itinerary"] if x.get("day") == n][0]
    head = f"{NAMES[key]} · Day {n} of {t['durationDays']} · {plain(d.get('title'))} · {d.get('location','')}"
    nums = " · ".join(x for x in [d.get("runningKm", ""), d.get("elevation", ""), f"meals: {d.get('meals','')}" if d.get("meals") else "", f"lodge tonight: {d.get('lodge','')}" if d.get("lodge") else ""] if x)
    return head + "\n" + nums + "\n" + "\n".join(d.get("paragraphs", []))
def highlight_text(key, title_contains):
    t = TOUR[key]
    for h in t.get("highlights", []):
        if title_contains.lower() in plain(h.get("title")).lower():
            return f"Highlight of {NAMES[key]}: {plain(h['title'])} — {h.get('description','')}"
    return ""
def lodge_text(key, name_contains):
    for l in TOUR[key].get("lodges", []):
        if name_contains.lower() in l["name"].lower():
            return f"Lodge on {NAMES[key]}: {l['name']} ({l.get('region','')}) — {l.get('description','')}"
    return ""
def departures(key):
    return "Bookable departures: " + "; ".join(x["label"] for x in TOUR[key].get("departures", [])) + f". Group: {TOUR[key]['groupMin']} to {TOUR[key]['groupMax']} athletes. Details and dates in the bio."

# (original filename, slug, set id, note builder, photo description)
L = []
def add(orig, slug, setid, note, photo): L.append((orig, slug, setid, note, photo))

# --- Trail Running, Day 2: Nine Summits at dawn (Esteban's own frames, Cerro de la Muerte, Dec 2025)
d2 = day_text("TR", 2) + "\n" + highlight_text("TR", "Nine") + "\n" + departures("TR")
add("20251220_054701.jpg.jpeg", "lib-tr-d2-dawn-1", "tr-d2-dawn", d2, "Dawn on the páramo of the Cerro de la Muerte: a hiker in a dark jacket on the ridge trail, gold sky, sea of cloud below. Esteban's own photo, December 2025.")
add("20251220_054651.jpg.jpeg", "lib-tr-d2-dawn-2", "tr-d2-dawn", d2, "First light over the páramo ridges of the Cerro de la Muerte, cloud below. Esteban's own photo, December 2025.")
add("20251220_055141.jpg.jpeg", "lib-tr-d2-dawn-3", "tr-d2-dawn", d2, "Panorama at dawn across the páramo and the ridges of the Talamanca. Esteban's own photo, December 2025.")
d2b = day_text("TR", 2) + "\n" + departures("TR")
add("20251220_071325.jpg.jpeg", "lib-tr-d2-ridge-1", "tr-d2-ridge", d2b, "A runner in a bright jacket on the Nueve Cumbres ridge above a sea of clouds, morning sun. Esteban's own photo, December 2025.")
add("20251220_071305.jpg.jpeg", "lib-tr-d2-ridge-2", "tr-d2-ridge", d2b, "The ridgeline of the Nueve Cumbres, páramo scrub and rock, blue morning. Esteban's own photo.")
add("20251220_075721.jpg.jpeg", "lib-tr-d2-ridge-3", "tr-d2-ridge", d2b, "A hiker standing on a rocky summit of the massif against a deep blue sky. Esteban's own photo.")
add("Cerro Asuncion Sunset.jpeg", "lib-tr-d2-asuncion-sunset", "", day_text("TR", 2) + "\nCerro Asunción is one of the nine summits of the traverse.\n" + departures("TR"), "Sunset over the ridges from Cerro Asunción, orange sky and dark mountain silhouettes. Esteban's own photo.")
# --- Founder on the ridge (journal-backed first person)
add("20251220_071458.jpg", "lib-founder-nine-summits", "", "FOUNDER PHOTO: Esteban Umaña himself, alone on the Nueve Cumbres ridge of the Cerro de la Muerte in December 2025, on the scouting trip that settled the route. Write this one in his first person, paraphrasing ONLY his published journal post 'Nine summits before the valley' (in the knowledge file): 15 years knowing this high country, 4 attempts to get the traverse right, scouting days under rain at 2 °C, nine summits all above 3,000 m, San Gerardo de Dota his favourite town, the agua dulce afterwards. No sentence copied from the journal.\n" + day_text("TR", 2) + "\n" + departures("TR"), "Esteban standing on the páramo ridge, hands on hips, morning light, cloud sea behind. His own frame.")
# --- Hiking, Day 2: the páramo
h2 = day_text("HK", 2) + "\n" + highlight_text("HK", "páramo") + "\n" + highlight_text("HK", "clouds") + "\n" + departures("HK")
add("20251220_070807.jpg.jpeg", "lib-hk-d2-paramo-1", "hk-d2-paramo", h2, "A hiker walking a narrow páramo trail between dwarf bamboo and flowering scrub, morning. Esteban's own photo, December 2025.")
add("20251220_071730.jpg.jpeg", "lib-hk-d2-paramo-2", "hk-d2-paramo", h2, "Two hikers in the páramo scrub of the Cerro de la Muerte, blue sky. Esteban's own photo.")
add("20251220_082920.jpg.jpeg", "lib-hk-d2-paramo-3", "hk-d2-paramo", h2, "Páramo vegetation close up on the ridge: low wind-shaped scrub, dwarf bamboo, lichened rock. Esteban's own photo.")
# --- Trail Running, Day 3: Dota cloud forest, Lauráceas
d3 = day_text("TR", 3) + "\n" + highlight_text("TR", "Lauráceas") + "\n" + highlight_text("TR", "singletrack") + "\n" + lodge_text("TR", "Lauráceas") + "\n" + departures("TR")
add("San Gerardo de Dota 05.jpg", "lib-tr-d3-dota-1", "tr-d3-dota", d3, "A resplendent quetzal perched in the cloud forest of San Gerardo de Dota, red belly and long green tail. Esteban's own photo.")
add("San Gerardo de Dota 04.jpg", "lib-tr-d3-dota-2", "tr-d3-dota", d3, "Cloud forest ridge above the Dota Valley with cloud pouring over it. Esteban's own photo.")
add("San Gerardo de Dota 01.jpg", "lib-tr-d3-dota-3", "tr-d3-dota", d3, "Orange flowers and a hummingbird in the lodge garden at Lauráceas, San Gerardo de Dota. Esteban's own photo.")
add("homepage-intro-dota.jpeg", "lib-tr-d3-dota-4", "tr-d3-dota", d3, "Looking straight up into the oak canopy of the Dota cloud forest, black and white. Esteban's own photo.")
# --- Lodge: Lauráceas (both expeditions)
ll = lodge_text("TR", "Lauráceas") + "\n" + day_text("HK", 2).split("\n")[0] + " and " + day_text("TR", 3).split("\n")[0] + " both sleep here.\n" + highlight_text("HK", "singing") + "\n" + departures("TR") + "\n" + departures("HK")
add("Lauraceas.jpg", "lib-lodge-lauraceas-1", "lodge-lauraceas", ll, "A hummingbird at orange flowers in the garden of Lauráceas Lodge. Esteban's own photo.")
add("San Gerardo de Dota 02.jpg", "lib-lodge-lauraceas-2", "lodge-lauraceas", ll, "A rufous-collared sparrow on a mossy branch at Lauráceas, San Gerardo de Dota. Esteban's own photo.")
# --- Trail Running, Day 4: the Queen Stage
d4 = day_text("TR", 4) + "\n" + highlight_text("TR", "Queen") + "\nThe full story is Esteban's journal post 'The Queen Stage, told slowly' (in the knowledge file): Xinia's kitchen at La Chaqueta, Don Hernán's basket crossing of the Savegre, the last 4 km up the fire road to Ranchos Tinamú.\n" + departures("TR")
add("Queen Stage 1.jpg", "lib-tr-d4-queen-1", "tr-d4-queen", d4, "A bench in misty cloud forest with ferns, on the Queen Stage descent. Esteban's own photo.")
add("Queen Stage 2.jpg", "lib-tr-d4-queen-2", "tr-d4-queen", d4, "A dirt road through forest and open fields on the Queen Stage route. Esteban's own photo.")
# --- Trail Running, Day 5: Manuel Antonio
d5 = day_text("TR", 5) + "\n" + highlight_text("TR", "10K") + "\n" + lodge_text("TR", "Parador") + "\n" + departures("TR")
add("Hotel Parador .jpg", "lib-tr-d5-manuel-antonio-1", "tr-d5-manuel-antonio", d5, "Aerial view of a sand cove with turquoise water and rainforest on the Manuel Antonio coast. Esteban's own photo.")
add("Manuel Antonio.jpg", "lib-tr-d5-manuel-antonio-2", "tr-d5-manuel-antonio", d5, "Hotel Parador's roofs in the rainforest above the Pacific at Manuel Antonio. Esteban's own photo.")
add("day-manuel-antonio.jpeg", "lib-tr-d5-manuel-antonio-3", "tr-d5-manuel-antonio", d5, "Aerial of palms, beach and rocky point on the central Pacific coast near Manuel Antonio. Esteban's own photo.")
# --- Trail Running, Day 6: Sierpe mangroves to Drake Bay
d6 = day_text("TR", 6) + "\n" + highlight_text("TR", "Drake") + "\n" + lodge_text("TR", "Corcovado") + "\n" + departures("TR")
add("Sierpe 01.jpg", "lib-tr-d6-drake-1", "tr-d6-drake", d6, "Aerial of the Sierpe river delta: a village between river channels and mangrove, grey water. Esteban's own photo.")
add("Drake bay.jpg", "lib-tr-d6-drake-2", "tr-d6-drake", d6, "A silhouette with a board at sunset on the beach at Drake Bay, orange sun on the sea. Esteban's own photo.")
add("Corcovado.jpg", "lib-tr-d6-drake-3", "tr-d6-drake", d6, "Aerial of a long dark-sand beach with green surf and rainforest on the Osa Peninsula. Esteban's own photo.")
# --- Trail Running, Day 7: the Osa
d7 = day_text("TR", 7) + "\n" + highlight_text("TR", "Osa") + "\n" + highlight_text("HK", "Lapas") + "\n" + departures("TR")
add("day-osa-macaw.jpeg", "lib-tr-d7-osa-1", "tr-d7-osa", d7, "A scarlet macaw in flight against a pale sky, red, yellow and blue. Esteban's own photo.")
add("journal-queen-stage-macaw.jpeg", "lib-tr-d7-osa-2", "tr-d7-osa", d7, "A scarlet macaw perched in dense green foliage. Esteban's own photo.")
add("day-drake-bay-monkey.jpeg", "lib-tr-d7-osa-3", "tr-d7-osa", d7, "A white-faced capuchin monkey on a branch, looking at the camera. Esteban's own photo.")
# --- Costa Rica: the toucan (knowledge; keep the geography honest)
add("hero-home-toucan.jpeg", "lib-cr-toucan", "", "KNOWLEDGE photo. A keel-billed toucan. In Costa Rica this species lives on the Caribbean slope and in the northern Pacific lowlands (Guanacaste), not on the Osa Peninsula, so do not place it on the Osa or the Talamanca. Use it for a Costa Rica fact, or for the Gravel Expedition's Guanacaste coast, where this toucan can be seen.\n" + departures("GR"), "A keel-billed toucan on a branch, yellow bill with green, orange and red, black body. Esteban's own photo.")
# --- Breakfast / the kitchens (sells the mountain kitchens and what is included)
add("dinner01.jpg", "lib-tr-breakfast", "", "EXPERIENCE photo: a Costa Rican breakfast as served at the lodges: gallo pinto, eggs, fried plantain, tortilla, coffee. Use the published facts: every breakfast is included on all three expeditions; on the Trail Running Expedition, mountain families open their kitchens on the Queen Stage (coffee, agua dulce, fruit, an empanada); on the Hiking Expedition dinner comes from the garden and the trapiche at Armonía Ambiental, La Chaqueta and Los Campesinos.\n" + day_text("TR", 4) + "\n" + departures("TR") + "\n" + departures("HK"), "Overhead photo of a breakfast plate: gallo pinto, eggs, plantain, tortilla, a cup of coffee on a wooden table. Esteban's own photo.")
# --- Gravel
g2 = day_text("GR", 2) + "\n" + day_text("GR", 3) + "\n" + lodge_text("GR", "Fermata") + "\n" + highlight_text("GR", "Santa Teresa") + "\n" + departures("GR")
add("Santa Teresa 02.jpg", "lib-gr-santa-teresa", "", g2, "Palm trees, a beach and forested hills on the Santa Teresa coast, southern Nicoya. Esteban's own photo.")
g45 = day_text("GR", 4) + "\n" + day_text("GR", 5) + "\n" + highlight_text("GR", "queen") + "\n" + highlight_text("GR", "Ostional") + "\n" + lodge_text("GR", "Sendero") + "\n" + departures("GR")
add("Nosara 05.jpg", "lib-gr-nosara-1", "gr-nosara", g45, "Aerial of a small cove with green water, rocks and forest on the Nosara coast. Esteban's own photo.")
add("Nosara 04.jpg", "lib-gr-nosara-2", "gr-nosara", g45, "A person with arms raised on the rocks by the sea at sunrise near Nosara. Esteban's own photo.")
g6 = day_text("GR", 6) + "\n" + day_text("GR", 7) + "\n" + highlight_text("GR", "surf") + "\n" + lodge_text("GR", "Capitán") + "\n" + departures("GR")
add("Tamarindo 06.jpg", "lib-gr-tamarindo-1", "gr-tamarindo", g6, "Aerial of Tamarindo beach with surfers in the water and the town behind. Esteban's own photo.")
add("Tamarindo 07.jpg", "lib-gr-tamarindo-2", "gr-tamarindo", g6, "A surfer walking out of the sea at sunset, Tamarindo, pink light on wet sand. Esteban's own photo.")
add("mtb-hero.jpg", "lib-gr-wild-coast", "", day_text("GR", 4) + "\n" + highlight_text("GR", "wild") + "\nPHOTO LOCATION NOT CONFIRMED: a Pacific coastline; do not name the beach.\n" + departures("GR"), "Aerial of a wild Pacific coast: waves breaking on a rocky point, dense forest to the water. Esteban's own photo.")
add("day-queen-stage.jpeg", "lib-gr-guanacaste-tree", "", "KNOWLEDGE photo: a Guanacaste tree (Enterolobium cyclocarpum), the national tree of Costa Rica, in open cattle country in Guanacaste, the province the Gravel Expedition finishes in (Days 6 and 7, Tamarindo and Brasilito).\n" + day_text("GR", 6) + "\n" + departures("GR"), "A huge spreading Guanacaste tree alone in a green field under a blue sky. Esteban's own photo.")
# --- Hiking Day 6 (bridge) and Day 7 (Playa El Rey)
add("schools-hero.jpeg", "lib-hk-d6-bridge", "", day_text("HK", 6) + "\n" + highlight_text("HK", "cable") + "\nPHOTO LOCATION NOT CONFIRMED: a hanging bridge in Costa Rican rainforest. Write about Day 6 and the 127-metre bridge at Los Campesinos without claiming this photo is that bridge.\n" + departures("HK"), "A person on a long hanging bridge through rainforest canopy, mist. Esteban's own photo.")
add("IMG-20221231-WA0008.jpg.jpeg", "lib-hk-d7-playa-el-rey", "", day_text("HK", 7) + "\n" + highlight_text("HK", "sea") + "\n" + departures("HK"), "A hiker with arms raised on a rocky reef at the Pacific, blue sky, the end of the walk. Esteban's own photo.")
# --- Bespoke / heritage
add("journeys-bespoke-carreta.jpeg", "lib-bespoke-carreta", "", "BESPOKE photo: a painted oxcart (carreta) with two oxen. The painted oxcart is Costa Rica's national labour symbol and its tradition (Sarchí) is on UNESCO's intangible heritage list, 2005. Use it for a Costa Rica fact or for bespoke private journeys (any discipline, built from scratch for a group), never as part of a fixed expedition day. Pointer: bespoke journeys, details in the bio.", "A traditionally painted oxcart pulled by two white oxen on a road. Esteban's own photo.")

index = []
for orig, slug, setid, note, photo in L:
    src = os.path.join(PICS, orig)
    if not os.path.exists(src):
        print("MISSING", orig); continue
    im = Image.open(src); im = ImageOps.exif_transpose(im).convert("RGB")
    w, h = im.size
    if max(w, h) > 2400:
        im.thumbnail((2400, 2400), Image.LANCZOS)
    out = os.path.join(DEST, slug + ".jpg")
    im.save(out, "JPEG", quality=90, optimize=True)      # no EXIF at all: no GPS, nothing
    txt = ("SET: " + setid + "\n" if setid else "") + "PHOTO: " + photo + "\n" + note.strip() + "\n"
    open(os.path.join(DEST, slug + ".txt"), "w", encoding="utf-8").write(txt)
    index.append({"file": slug + ".jpg", "set": setid, "from": orig, "size": im.size})
    print("ok", slug, im.size, os.path.getsize(out) // 1024, "KB")
json.dump(index, open(os.path.expanduser("~/mnt/social-autoposter/_to_delete/build/library_index.json"), "w"), indent=1)
print(len(index), "library photos written")
