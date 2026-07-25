# Joeville World and Set Design Bible

**Status:** design-development specification, not final scenic art  
**Owners:** showrunner/worldbuilding director, production designer, supervising art director, director of photography, continuity supervisor  
**Map authority:** `design/MAP_SPEC.md`  
**Scope of this document:** visual thesis, district identity, recurring set roster, scenic requirements, camera/blocking grammar, and visual continuity

## 1. Evidence, assumptions, and approval gates

### Confirmed local evidence

- The inspectable Wizard Joe reference is a compact, block-built cartoon figure with a strong dark outline, square/pixel-like surface units, broad frontal readability, saturated blue/gold/magenta costume colors, rainbow wings, a tall hat, a staff, and soft contact shadow.
- His reference local grid is 72 × 96 with the root at the bottom center. The existing runtime projection uses a horizon at 56% of frame height, a near floor near 95%, world depth from 1.5 to 10, and depth-dependent scale.
- The current documented environment is a fixed white studio void with a faint perspective floor. It explicitly does **not** yet prove support for illustrated backgrounds, parallax, occlusion mattes, camera moves, or environmental video.
- Wizard Joe is present in the primary checkout. CrystAIl is now runtime-ready and measured on the dedicated `codex/crystail-character` branch, with a 63-pose package and two-character registry verified by focused tests. Eleven further character sources, the full lineup, Castle references, and an approved environment reference are not yet present in the package intake.

### Working assumptions (must not be mistaken for verified inputs)

1. Joeville is a fictional town, not a literal reproduction of Boulder. Recognizable Boulder geography is translated into a stable west-high/east-low foothill town.
2. The world uses a **crafted block-diorama** scenic language that belongs beside Wizard Joe and CrystAIl: simplified planes, chunky silhouettes, selective square-cell texture, controlled outlines, clear value grouping, and limited micro-detail. This remains provisional until the other 11 characters are inspected.
3. Sets are authored first as locked 16:9 compositions compatible with a fixed camera. Layered and moving-camera deliverables are optional expansions until runtime support is demonstrated.
4. The scenic master scale unit is `1 JU` (Joeville unit). Until the 13-character lineup exists, a nominal standing adult body is 1.0 CU (character unit), Wizard Joe’s hat is allowed to extend to 1.18 CU, his staff to 1.25 CU, and wings to 1.65 CU wide. Environment dimensions below use CU so they can be rescaled without redesign.
5. Castle Grace is wholly fictional unless a user-supplied canonical reference supersedes this design.

### Hard gates before final scenic production

- Inspect and measure all 13 characters front/profile, including hats, wings, staffs, hair, mobility aids, seated poses, and maximum action silhouettes.
- Confirm visualizer resolution, aspect ratios, scene-change behavior, background formats, z-order, occlusion masks, parallax, video, prop attachment, shadow handling, and camera behavior.
- Approve Castle Grace silhouette and plan.
- Approve fictional brand names and clearance strategy.
- Cross-check final art against the completed Boulder research dossier and source ledger. This document makes creative decisions; factual authority remains the research dossier.

## 2. Joeville visual thesis

Joeville is a sunlit foothill town where civic life and interior life visibly touch: warm masonry streets and creek bridges gather at the base of bold, westward stone fins, while a curious hilltop castle watches without dominating. The town feels handmade, legible, generous, and slightly enchanted—its buildings are assembled from chunky stone, timber, brick, glass, and painted metal in simple silhouettes that match Wizard Joe’s block-built body; saturated character colors remain the sharpest accents against sage, sandstone, creek-blue, cream, and dusk-violet scenery. Nature is never wallpaper: water, slopes, weather, cottonwoods, meadow grass, and mountain light organize travel and story. Magic appears as a restrained response of the world—small prism glints, star perforations, rainbow refractions, and warm lantern rhythms—while doors, chairs, paths, counters, stairs, and public spaces remain physically coherent and playable.

### Dramatic promise

- **Downtown is social:** encounters, jokes, commerce, performance, disagreement.
- **The creek is connective:** walking talks, transitions, reflection, chance meetings.
- **The meadow is communal:** picnics, public rituals, introductions, gentle ensemble scenes.
- **The mountains are testing:** effort, discovery, solitude, weather, perspective.
- **Castle Grace is consequential:** council, hospitality, secrets, celebration, moral choice.
- **Food/wellness interiors are intimate:** listening, ritual, comfort, comic etiquette.
- **Residential Joeville is ordinary:** stakes feel real because characters have somewhere to return.

## 3. Visual language

### Shape hierarchy

- **Land:** long triangular westward ridges, broad horizontal meadow/creek bands, stepped rock planes.
- **Civic architecture:** low rectangular masses, softened square arches, sawtooth rooflines, deep door/window reveals.
- **Castle:** stacked asymmetrical rectangles around one calm central tower; never a spiky fantasy fortress.
- **Props:** simple, graspable silhouettes; one iconic shape per object; no filigree that collapses at visualizer scale.
- **Magic:** circles, arcs, seven-color stepped prisms, small four-point stars. Avoid generic swirling runes.

### Palette architecture

The environment must support, not compete with, Wizard Joe’s saturated costume.

| Role | Color family | Use |
|---|---|---|
| Sky/light | warm white, pale cyan, cool blue-violet | broad low-detail fields |
| Stone | buff sandstone, dusty rose, warm gray | mountains, retaining walls, Castle base |
| Built neutral | cream, pale putty, charcoal | walls, trim, roofs, outlines |
| Vegetation | sage, meadow gold, cottonwood green | district identity and seasons |
| Water | desaturated turquoise/blue-gray | creek and falls; brighter only in highlights |
| Civic accent | oxidized teal, brick red, mustard | doors, awnings, street furniture |
| Night practicals | honey amber, soft coral | welcoming pools; not global orange wash |
| Magical accent | Joe cyan, gold, restrained rainbow | rare story beats, never ambient clutter |

Black scenic outlines should be softer and lighter than character outlines. Reserve the darkest `#17191C`-like value for near foreground silhouettes and essential architecture. Background edges lose contrast with depth.

### Materials and surface treatment

- Regional-feeling stone, rough timber, warm brick, limewashed plaster, matte painted steel, clear glass, board-formed concrete, wool, canvas, and glazed ceramic.
- Translate texture into **clusters**, not noise: 2–5 large block marks imply grain or stone; do not uniformly pixel-dither every surface.
- Reflections are graphic value shapes, not photoreal ray-traced mirrors.
- Snow caps horizontal surfaces consistently. Rain darkens stone/wood and adds limited puddle reflections; it does not make every plane glossy.

### Architecture

- Downtown: two- and three-story mixed-era storefront fabric, recessed entries, brick/stone party walls, human-scale awnings.
- Creek/wellness: lighter timber, glass, planted courtyards, covered walks.
- Residential: modest porches, varied but related rooflines, native front gardens; never luxury subdivision uniformity.
- Meadow: civic-lodge language with deep porch and low roof.
- Castle Grace: adaptive-reuse feeling—old stone base, timber communal additions, selective modern glass—suggesting it grew with the community.

### Graphics and signage

- Joeville identity: a simple westward ridge above a creek arc, with a small offset star.
- Street signs: dark teal blades, cream lettering, square end caps.
- Shop signs: controlled vector/text pass after scenic generation. No generated lettering in final plates.
- Posters and menus live on separate replaceable layers. Dates, prices, and event names are continuity props.
- Real brands and distinctive trade dress are excluded by default. “Whole Foods” becomes the fictional **Joeville Commons Market** unless clearance explicitly approves branded use.

### Lighting language

- **Dawn:** cool town, peach ridge rims, long east-cast shadows.
- **Midday:** high, clear, restrained contrast; shadows fall generally north/east depending on approved seasonal sun chart.
- **Golden hour:** west light from the ridge side can silhouette the mountains; use warm rim, not sepia wash.
- **Blue hour:** cool exterior planes, warm interior windows.
- **Night:** district-specific pools of light; retain readable ground planes and exits.
- **Magic:** motivated by a character/action; cyan/gold prism response affects adjacent surfaces and disappears when action ends.

## 4. District design

District codes and exact topology are controlled by `MAP_SPEC.md`.

| ID | District | Visual identity | Story function | Typical density |
|---|---|---|---|---|
| D1 | Ridge Gate / town edge | road, entry marker, open sky, low scrub | arrival, departure, exposition | low |
| D2 | Hearthside Residential | porches, gardens, modest roofs, bikes | homecoming, neighborhood comedy | low–medium |
| D3 | Downtown / Lantern Walk | brick, stone, awnings, public art, narrow shop rhythm | chance meetings, commerce, performance | medium–high |
| D4 | Creek Thread | water, cottonwoods, bridges, multi-use path | walking dialogue, transitions, reflection | low–medium |
| D5 | Wellhouse Quarter | timber/glass, courtyards, edible planting, wellness signs | food, health, ritual, interpersonal intimacy | medium |
| D6 | Meadow Commons | broad grass plane, lodge porch, Flatiron analogue view | ensemble, celebration, public calm | scalable |
| D7 | High Trails | forest, rock, exposed switchbacks, overlooks | tests, solitude, revelation | low |
| D8 | Grace Ridge | stone walls, orchard/garden, Castle silhouette | consequence, council, hospitality, wonder | controlled |

## 5. Scale and stageability standard

Until the final lineup is measured, every production angle must reserve:

- standing silhouette height: 1.25 CU clear (includes Wizard Joe hat/staff allowance);
- individual width: 1.75 CU for winged/action poses; 1.0 CU for neutral standing;
- door clear opening: 1.5 CU wide × 1.55 CU high minimum;
- public corridor: 2.5 CU minimum; hero group circulation: 4 CU;
- two-character dialogue bay: 4 CU wide × 2.5 CU deep;
- five-character bay: 8 CU wide × 4 CU deep;
- 13-character ensemble platform: 18 CU wide × 7 CU deep, with three staggered depth bands;
- chair/stool variants: separate prop assets until seated root/hip anchors are measured;
- counter height: provisional 0.55 CU; tables 0.45 CU; bench seat 0.28 CU;
- foreground occluders never cover the bottom-center root of a speaking character unless the shot is explicitly authored for it.

All public sets need a staff-and-wing turn radius of 2 CU at primary entrances. Narrow historical-looking doors may appear only as non-playable background doors.

## 6. Principal recurring sets

Each principal set is a **set family**, not one image. “Required plates” means empty scenic plates; character blocking composites are separate review assets.

### JV-00 — Joeville town overview

- **District/function:** townwide orientation, montage, transitions, weather and time passage.
- **Canonical composition:** camera east/southeast of town looking west/northwest; mountains occupy west horizon, Castle sits above the southwest shoulder, downtown is central, creek runs northwest-to-southeast below it, meadow lies west, Wellhouse east of downtown.
- **Needs:** elevated day master; sunrise, golden hour, blue hour, night; summer, autumn, snow; closer downtown-over-creek vista; Castle-to-town reverse POV.
- **Layers:** sky/weather, far ridges, Castle ridge, town mass, creek/meadow, near vegetation, light windows, atmospheric effects.
- **Blocking:** no dialogue staging; transition silhouettes only. Maintain uncluttered central/lower third for titles when requested.
- **Continuity:** no set may contradict this mountain/creek/Castle relationship.

### JV-10 — Lantern Walk (Pearl-inspired pedestrian district)

- **District/function:** D3; social engine, buskers, dining, commerce, civic gathering.
- **Plan:** three continuous blocks: West Gate → Commons Court → East Arcade. A north–south cross street meets Commons Court. Service alleys run behind north and south storefronts.
- **Recurring zones:** west approach, busker circle, public-art bench, dining terrace, storefront run, cross-street corner, east transition toward Wellhouse.
- **Needs:** clean early-morning master; day active master; night practicals; winter; rain shelter; empty controlled plates for each block; storefront/sign overlays; near/far pedestrian shadow layers if crowd loops are later approved.
- **Camera:** eye-level 24–28 mm-equivalent masters down the walking axis; 35–50 mm dialogue angles across, never directly down, the busiest background; 70 mm-equivalent inserts for signage/public art. Reverse angles must preserve storefront order.
- **Blocking:** central 3 CU travel lane remains open; static conversations move to benches, tree wells, or facade setbacks. Full 13 use Commons Court only, in a shallow arc with two entry lanes.
- **Exits:** west to meadow/Chautauqua shuttle approach; east to Wellhouse; south to creek bridge; north to residential/civic cross street.

### JV-11 — Lantern & Lark Coffee

- **District/function:** D3 south edge; recurring intimate/public interior.
- **Exterior:** corner storefront facing Lantern Walk, creek glimpsed down south side street; cream masonry, teal frame, mustard canopy.
- **Interior plan:** south-facing public windows; west entry with 2 CU landing; counter along north wall; service/back room northeast; quiet banquette east; communal table center-east; two-top window rail south; small outdoor terrace south/west.
- **Needs:** exterior front, three-quarter arrival, interior master from southwest, reverse from northeast, counter angle, window two-shot, banquette OTS pair, communal five-shot, terrace, doorway inserts; AM rush, quiet afternoon, rainy evening, night close.
- **Camera walls:** southwest and northeast corners are removable; avoid crossing the counter eyeline without a bridge shot. Window views always show D3 side street/creekward light, never mountains directly.
- **Blocking:** entry → order rail → pickup → seating is clockwise. Keep center-left 3 CU path clear. Maximum credible dialogue cast: 5 at communal table; 8 for a standing after-hours event; not a 13-character regular interior.
- **Props:** modular cups, pastry case, menu panels, laptop/book, bus tub, plant, receipt device; all separable for continuity.

### JV-20 — Chautauqua analogue: Grace Meadow and Hearth Lodge

- **District/function:** D6; communal breath, trail departure, public ritual, picnic, ensemble.
- **Plan:** Meadow bowl slopes gently west; Hearth Lodge at northeast edge; porch faces southwest; trailhead exits west/northwest; picnic grove east; gathering circle south-central.
- **Needs:** mountain-facing meadow wide; lodge/porch; trailhead; picnic grove; character-eye arrival; dawn mist, midday, sunset, snow, storm approach; empty full-ensemble plate.
- **Camera:** low 24 mm-equivalent wide makes grass a usable stage; 35 mm lateral walking coverage; 50 mm porch dialogue. Mountains remain west/northwest in every angle.
- **Blocking:** mower-width central swale doubles as 5 CU movement lane. Full 13 form a broken semicircle, not a straight lineup; leave one gap toward camera and one toward trailhead.

### JV-21 — Thirteen Stones Meditation Circle

- **District/function:** D6 south rise; sacred but public, intimate-to-ensemble reflection.
- **Plan:** 15 CU-diameter oval within scrub and pines; low central stone/optional contained fire bowl; 13 removable cushion/stone anchors; east arrival path; west view slit to mountains; north service/safety path hidden by planting.
- **Needs:** empty day, dawn, sunset, moonlit, controlled firelight; configurations for 2, 5, 13; altar/fire inserts; no permanent spiritual text or appropriated sacred symbols.
- **Camera:** 28 mm circle master from east; 35 mm cross-circle; 50–70 mm intimate two-shots with simple vegetation; high 35 mm diagrammatic ensemble only when story needs geometry.
- **Blocking:** 13 anchors numbered clockwise M01–M13; M01 west/northwest. Keep center clear unless ritual action calls for it. No character is forced to sit; standing/wheel-accessible outer anchors are provided.

### JV-30 — Current Hall (ecstatic dance)

- **District/function:** D5; release, comedy, conflict through movement, community ritual.
- **Exterior/lobby:** converted light-industrial hall; covered east entry, shoe/coat zone north, water station south, acoustic vestibule.
- **Interior plan:** 20 × 14 CU clear sprung floor; low stage/DJ deck on west wall; quiet decompression alcove southeast behind a partial acoustic screen; side seating north/south; two wide east exits plus northwest service exit.
- **Needs:** exterior day/night; lobby; empty daylight master; warm-up; active lighting; closing circle; elevated wide; stage reverse; side coverage; water/coat/feet/light inserts; clean floor and lighting passes separate.
- **Camera:** 24 mm masters from east and northwest; 35 mm side tracking grammar; elevated 28 mm; 50 mm decompression corner. Active light beams must not obscure faces or create strobing hazards.
- **Blocking:** 13-character circle is 10 CU diameter with 2 CU safety ring. Solo zone center; partner lanes on diagonals; entrance kept visually readable. Maximum 13 plus a sparse implied crowd layer; do not bake extras into master plates.

### JV-31 — Brightroot Juice Bar

- **District/function:** D5; quick daylight encounters and comic ordering.
- **Plan:** east storefront; counter north; prep behind; six stools; two window two-tops south; shared courtyard west exit.
- **Needs:** exterior, counter master/reverse, window two-shot, three-shot, ingredient/juice inserts, busy and quiet dressing variants.
- **Camera/blocking:** bright 35 mm interior master from southeast. Order queue runs along east/north and never bisects seated dialogue. Comfortable maximum 5; background suggestion up to 8.

### JV-32 — Juniper Tonic House

- **District/function:** D5 courtyard; slower evening ritual, confidential conversation.
- **Plan:** entry east from shared courtyard; curved bar north/west; apothecary display behind locked/glazed panels; preparation sink northwest; three booths south; ceremonial service niche west; staff exit north.
- **Needs:** exterior/shared entrance, daylight master, evening amber master, bar two-shot, booth OTS pair, preparation/steam/glass/herb inserts.
- **Camera/blocking:** 40–50 mm, more compressed and calm than Juice Bar. Curved bar supports profile two-shot and three-shot. Maximum credible cast 5; never full ensemble.
- **Continuity/legal:** no medical claims on signs or labels; invented preparations; avoid imitating a specific real wellness business.

### JV-33 — Riverstone Sushi

- **District/function:** D3/D4 south edge; meals, dates, celebrations.
- **Plan:** west host entry; sushi counter north; kitchen pass northeast; booths south; 14-seat flexible group table center/east with removable leaves; creek-facing east windows.
- **Needs:** exterior, lunch master, dinner master, counter, booth OTS pair, group-table ensemble, host/entry, kitchen pass, food/table inserts; table dressing reset maps.
- **Camera/blocking:** 35 mm masters, 50–70 mm intimate coverage. Full 13 fits only at reserved group table with two service aisles and a wide room master; normal episode dressing breaks it into smaller tables.
- **Legal:** fictional restaurant and graphics; cuisine represented respectfully; production food references require specialist review.

### JV-34 — Joeville Commons Market

- **District/function:** D5 eastern edge; ordinary errands, surprise encounters, comic choices.
- **Plan:** north-facing entry from parking/bike court; produce west; prepared foods south; four broad east–west aisles; checkout north/east; small café southwest; service/back wall south/east.
- **Needs:** fictional exterior, arrival/bike rack, vestibule, produce, aisle two-shot, prepared food, checkout, café, quiet opening and busy modular variants. Crowd/product layers are optional and replaceable.
- **Camera/blocking:** 28–35 mm aisle coverage with 2.5 CU clear width; 50 mm shelf inserts. Dialogue uses aisle ends or produce islands so carts can pass. Maximum recurring scene group 5; larger encounter belongs in entry plaza, not an aisle.
- **Clearance:** default is fully fictional. Do not use Whole Foods name, logo, distinctive signage, uniforms, packaging, or copied interior layout without written clearance.

### JV-40 — Joeville Creek / Ribbon Path

- **District/function:** D4; connective spine and walking-dialogue workhorse.
- **Set family:** Stone Arch Bridge, Cottonwood Bend, Downtown Steps, Quiet Bank, East Footbridge, winter bank.
- **Needs:** left/right side-scroll plates, forward approach, bridge master/reverse, two-shot rests, creek inserts, rain/high-water and snow variants.
- **Camera/blocking:** 35 mm side two-shot with 3 CU path; 28 mm approach; 50 mm rest point. Creek always flows generally northwest → southeast. Railings and trees can be foreground occlusion masks, never baked over the only character plane.

### JV-50 — High Trail system

- **District/function:** D7; physical/emotional progression.
- **Segments:** T1 Meadow Link (easy), T2 Pine Fold (forested), T3 Split Rock Junction, T4 Stone Ladder (rocky ascent), T5 Cloud Shelf Overlook, T6 Silver Thread Crossing, T7 North Spur toward Falls.
- **Needs:** each segment gets direction A/B masters and one dialogue bay; sunrise, midday, golden hour; storm approach; winter for T1/T2/T5; foot/rock/water inserts.
- **Camera/blocking:** ordinary walking paths ≥2.5 CU; passing/dialogue bays ≥4 CU every set segment. Use 35–50 mm lateral coverage for conversation, 24–28 mm for exposure/effort. Never stage characters on cliff lips or active water channels.
- **Continuity:** ascent west/northwest raises elevation; return east/southeast descends. Vegetation thins and rock exposure increases with elevation.

### JV-51 — Joeville Falls

- **District/function:** D7 north spur; awe, intimacy, contemplation, weather power.
- **Plan:** arrival trail from southeast; fenced/viewing shelf east of water; intimate alcove farther southeast; falls descend west/northwest rock face into pool/stream flowing southeast.
- **Needs:** approach, safe wide, medium shelf, mist/rock/water inserts, alcove two-shot, meditation view, high-water rain, winter ice. Water/mist are separate animation/effects passes.
- **Camera/blocking:** 24–28 mm wide, 50 mm intimate shelf. Keep characters behind safety edge; no standing on wet boulders. Sound and mist intensity drop at alcove.

### JV-60 — Castle Grace

- **District/function:** D8; moral/emotional center, hospitality, council, wonder, ensemble finale.
- **Canonical silhouette (provisional):** stepped buff-stone base, off-center square tower, deep blue-gray roof planes, timber/glass communal wing, one lantern-like upper window, garden terraces. No random turrets between angles.
- **Campus plan:** arrival road from east/southeast; gate court; front door east; great room south/west; kitchen/dining north/east; library north/west; council room tower base; meditation room south; terrace west/southwest; garden/amphitheater downhill south; service court north/east.
- **Needs:** town-view establishing, road approach, gate, entry, night exterior, garden/terrace, amphitheater; interior entry, great room master/reverse/firelight/celebration, dining, kitchen, library, council, meditation; corridor/door inserts. Private bedrooms are not designed until story requires them.
- **Camera:** 24 mm exterior, 28–35 mm great room, 50 mm council/library. East-facing arrival cameras see facade and high-country sky; west-facing terrace cameras see ridge, not downtown. A dedicated Castle-to-town overlook is on the south terrace axis.
- **Blocking:** great room clear zone 18 × 8 CU; 13 arranged in three shallow depth bands or a horseshoe. Dining uses a 14-seat U/oval table with 3 CU service perimeter. Amphitheater uses two stepped arcs with accessible side route.
- **Props:** Grace crest, long table sections, chairs, hearth implements, books, map table, lanterns, serving ware, garden banners; all inventory-controlled.
- **Gate:** user Castle references supersede this provisional design; no concept plate should be treated as canon before approval.

## 7. Supporting and connective sets

| Set ID | Set | Why it exists | Minimum coverage |
|---|---|---|---|
| JV-01 | Ridge Gate / town sign | arrivals, departures, season/time transitions | inbound, outbound reverse, sign insert, night/snow |
| JV-02 | Hearthside residential street | ordinary life, home exteriors without inventing 13 homes | east/west walk, porch two-shot, rain/snow |
| JV-03 | Transit/bike court | solves believable travel to meadow/market | master, shelter, rack, arrival/departure |
| JV-04 | Civic bridge | joins downtown and Wellhouse across creek | both directions, side wide, under-bridge insert |
| JV-05 | Downtown service alley | confidential/comic back-door scenes | north/south masters, door inserts, night/rain |
| JV-06 | Commons Court plaza | scalable public gathering outside tight interiors | master/reverse, stage edge, 13 blocking, night |
| JV-07 | Mountain road / pullout | Castle/Falls travel compression | uphill/downhill, pullout overlook, weather |
| JV-08 | Trail parking / kiosk | gear-up and safe transition to wilderness | lot master, kiosk/map, trail entrance |
| JV-09 | Creek rain shelter | dialogue during weather and transition refuge | exterior, sheltered two-shot, rain layer |

Character-specific home interiors/exteriors are intentionally deferred until character biographies and ownership logic are supplied. Generic vehicle interiors are also deferred; walking, bike arrival, shuttle shelter, and transition plates cover current needs without expanding the library prematurely.

## 8. Camera and blocking grammar

### Frame classes

1. **Geographic master (24–28 mm equivalent):** declares exits, landmark orientation, and usable ground. Start a new set family or changed geography here.
2. **Action wide (28–35 mm):** shows complete body/action and two or more paths. Preferred for Wizard Joe’s hat, staff, wings, dance, and locomotion.
3. **Dialogue medium (40–55 mm):** simple background, stable eyeline, headroom for tall accessories.
4. **Intimate/insert (65–85 mm):** compressed background, prop or emotion; environment remains recognizable through one motif.
5. **Elevated diagram (24–35 mm):** only for dance, meditation, ensemble geography, or town orientation—not a default style.

These are compositional equivalents, not assertions that the current runtime has a physical camera.

### Axis rules

- Establish the primary room/street/trail axis in a master. Maintain screen direction across cuts.
- Crossing the 180-degree line requires a neutral center shot, visible character movement across the line, or an overhead/elevated bridge shot.
- Town travel west/northwest generally means “toward mountains / uphill”; east/southeast means “toward market / out of town / downhill.” Screen direction should reinforce this when practical.
- Do not flip plates to create reverses: signage, mountain light, Castle silhouette, creek flow, staff handedness, and asymmetric architecture would invert.

### Character-safe composition

- Keep the lower 8% free of critical roots and props for crop/UI uncertainty.
- Keep dialogue heads and tall accessories within the central 80% width and upper 85% height unless an approved safe-area spec supersedes this.
- A character bay is a labeled ground polygon with a root anchor, allowed facing range, scale range, and occlusion status.
- Every major angle carries: horizon, vanishing point, ground grid, camera ID, root anchors, entry/exit splines, and foreground matte IDs.
- Winged characters require explicit “wings open” envelopes; staff-bearing characters need a prop clearance side. Do not solve overlaps by shrinking characters inconsistently.

### Cast-size patterns

| Cast | Default pattern | Camera | Notes |
|---|---|---|---|
| 1 | thirds placement with visible destination/negative space | medium or action wide | preserve gesture and prop side |
| 2 | open V or profile pair | 35–55 mm | shared ground band; clean eyeline |
| 3 | shallow triangle | 35–50 mm | speaker can rotate without crossing axis |
| 5 | broken arc / 2+3 depth | 28–40 mm | no equal-spaced lineup |
| 8 | two staggered clusters | 24–35 mm | motivate subgroup relationships |
| 13 | three bands, horseshoe, circle, or amphitheater | 24–28 mm / elevated | only approved ensemble sets |

### Walking dialogue

- Author A→B and B→A plates separately; no mirror reuse.
- Provide a 3 CU uninterrupted midground path and 4 CU pause bay.
- Trees, poles, railings, and signs pass on controlled foreground layers. No repeated occluder may cover a face longer than a brief beat.
- For a fixed runtime, simulate travel with three matched plates (approach, lateral, arrival) rather than inventing unsupported camera tracking.

### Full-cast approved sets

Castle great room/dining/amphitheater, Current Hall, Thirteen Stones Circle, Grace Meadow, Commons Court, and Riverstone Sushi’s reserved group configuration. Lantern Walk supports 13 only at Commons Court. Coffee, Juice, Tonic, market aisles, and most trail segments do not.

## 9. Scenic deliverable standard per recurring set

Every principal set family must ship with:

1. canonical plan/elevation or exterior massing diagram;
2. one locked geographic master and reverse where plausible;
3. entrance-facing and destination-facing coverage;
4. required dialogue angles with clear character bays;
5. empty clean plate for each angle;
6. foreground occlusion mattes (when supported);
7. shadow receiver/ground contact guide;
8. practical-light and window overlays;
9. modular signage and story-prop layers;
10. day plus narratively justified night/weather/season variants;
11. set dressing reset sheet and prop inventory;
12. camera sheet with horizon, vanishing point, root anchors, and safe crop;
13. continuity thumbnail showing adjacency and screen direction;
14. separate blocking composite for 1, 2, 5, and maximum approved cast;
15. inspection record proving no baked characters, garbled text, impossible doors/stairs, or blocked paths.

## 10. Continuity bible

### Geographic invariants

- Mountains/high country are west/northwest. Town falls east/southeast.
- Joeville Creek enters from northwest/high country and exits southeast.
- Downtown sits north of the creek at the central crossing; Wellhouse sits east/southeast; Meadow lies west/southwest; Castle Grace lies southwest and above the meadow; Falls lie northwest on the north mountain spur.
- Castle may be visible from designated town/meadow vistas only. It is not pasted into every mountain view.
- Travel times and legal adjacencies come from `MAP_SPEC.md`. A cut that violates them needs a transition card/clip or explicit narrative device.

### Exterior/interior invariants

- Window orientation is logged per set. A north wall window cannot show a south/east landmark.
- Exterior door location, hinge, width, color, sign, awning, and threshold match the interior entrance.
- Sun and practical light direction match across entry cuts.
- Floor level and stair counts are stable. Accessible routes remain visible/credible.
- Service doors never become public entrances for convenience without story acknowledgement.

### Scenic continuity

- Each building has one silhouette sheet, material key, window count, roofline, and graphics master.
- Set dressing exists in three ledgers: **fixed** (architecture), **reset** (returns every scene), and **story state** (changes with plot).
- Chairs, cups, cushions, menus, posters, produce displays, table settings, and coats get numbered placements when continuity matters.
- Damage, construction, seasonal decor, event posters, and magical residue require start/end episode records.

### Natural continuity

- Creek/falls flow direction never reverses. Water level variants are named and used consistently within a sequence.
- Vegetation follows elevation: cottonwoods/willows at creek; meadow grass/shrubs at commons; denser pine/mixed woodland in Pine Fold; sparse wind-shaped vegetation at Cloud Shelf.
- Snowline, leaf state, meadow dryness, creek volume, and trail mud are season-package choices, not independently randomized per shot.
- Weather travels coherently across adjacent sets. Rain at downtown should appear at the creek and Wellhouse unless the scene establishes a localized shower or time jump.

### Character/environment continuity

- Root anchor, depth scale, contact shadow, and horizon projection must come from the same camera sheet.
- Never reduce a character below the camera’s established depth scale merely to fit a door or table.
- Hats, wings, staffs, and action poses are part of collision/occlusion checks.
- Characters remain separate from clean plates. Blocking images are labeled `REF_BLOCKING_ONLY`.

### Editorial continuity checklist

Before approving a sequence, answer:

1. Where are we on the map, and which way is west/uphill?
2. Which door/path did each character use, and does the reverse angle preserve it?
3. Are mountains, creek flow, Castle, windows, sun, and weather on their legal sides?
4. Are character roots, scale, eyelines, shadows, and occlusions consistent?
5. Did any modular sign/prop/food/cushion/chair change unintentionally?
6. Is travel time plausible, or is a transition missing?
7. Is this a clean plate, a dressing variant, or a blocking composite—and is it named correctly?

## 11. Priority production order from a design standpoint

1. 13-character lineup and collision envelopes.
2. Runtime environment capability audit.
3. Map approval and one town massing model.
4. Joeville palette/material/graphics test beside all 13 characters.
5. Town overview, creek crossing, Lantern Walk, and one residential connector.
6. Castle Grace silhouette/plan approval, then great room ensemble test.
7. Coffee shop as the small-interior production prototype.
8. Meadow + Meditation Circle + Current Hall as 13-character staging tests.
9. Creek path and trail system as movement prototypes.
10. Food/wellness interiors and fictional market.
11. Time/weather/season packages only after base angles lock.

## 12. Open decisions

- What are the identities, dimensions, silhouette hazards, locomotion modes, and home/work relationships of the other 11 characters?
- Is the final style true ASCII/glyph rendering, square-cell color rendering, pixel-diorama illustration, or a hybrid?
- Does the visualizer accept one flat image only, or layered stills/video with alpha and occlusion?
- What Castle reference is canonical?
- Which locations must use real names, and which must remain fictional?
- Should Joeville contain cars as routine background life, or emphasize walking/bikes/shuttles?
- What accessibility needs are canonical for the cast?
- Which episode/sequence is the first production target? That choice should determine which set family reaches final art first.

## 13. Honest completion statement

This document completes a coherent **design-development** world thesis, set roster, per-set scenic needs, camera/blocking grammar, and continuity system. The package now also includes the Boulder research dossier, production-map art, blocking diagrams, manifests, prompts, technical audit and six inspected concepts. It does not claim completion of the 13-character lineup, production-final layered plates, complete plan/perspective set, environment clips, or visualizer integration; those remain gated by missing canonical inputs and runtime capabilities.
