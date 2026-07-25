# Joeville Map Specification

**Status:** canonical production geography, version 0.1 (approval required)  
**Purpose:** give every writer, storyboard artist, environment artist, animator, editor, and continuity checker one stable answer to “where is it, what is next to it, and which way are we facing?”

## 1. Map contract

This specification defines fictional Joeville. It is Boulder-inspired but is not a navigational or factual map of Boulder. Once approved, coordinates, adjacencies, creek flow, elevation order, landmark sightlines, and building orientations are locked until a versioned map revision is approved.

The map exists at three levels:

1. **Town map:** story geography and approximate travel.
2. **District/set map:** exact doors, paths, bridges, and exterior relationships.
3. **Camera map:** horizon, view bearing, screen direction, and legal landmark views.

No scenic image may establish new geography by accident.

## 2. Coordinate, bearing, and elevation system

- Town origin `(0,0)` is the center of **Commons Court** in Downtown.
- `+X` = east/down-valley; `-X` = west/toward mountains.
- `+Y` = north/upstream; `-Y` = south.
- Bearings use true map north for internal consistency; scenic sun direction is tracked separately by season/time.
- Coordinates are fictional kilometers from origin; they are for continuity, not real-world distance.
- Elevation datum `E0 = 0` is Commons Court. Elevations below are relative fictional meters.
- Major drainage is west/northwest → east/southeast. Joeville Creek must never appear to flow uphill or reverse in an angle.

### Camera bearing notation

`CAM-WNW` means the camera looks west-northwest; objects west-northwest of the set may appear in the background if terrain and architecture permit. A plate may not show a landmark simply because it is aesthetically convenient.

## 3. Townwide schematic

```text
                                      N / upstream
                                           ^
                                           |
                 JV-51 FALLS               |       D7 HIGH TRAILS
                  (-3.6,+3.5)              |    T7 North Spur
                       \                    |   /
                        T6 Creek Crossing--T3 Split Rock--T4--T5 OVERLOOK
                              \            /                 (-4.0,+1.3)
                               T2 Pine Fold
                                    |
        D8 GRACE RIDGE          T1 Meadow Link
        JV-60 CASTLE                 |
        (-3.4,-1.7)----garden----JV-20 SUNSTEP MEADOW / HEARTH LODGE
             |                      (-2.1,-0.7)
             | mountain road             |
             JV-07 Pullout          west gate
                   \                     |
                    \       D3 LANTERN WALK / DOWNTOWN
                     \  West Gate--Commons Court--East Arcade------D2 RESIDENTIAL north/east
                      \              (0,0)              \
                       \               | south street    \ JV-11 COFFEE
                        \          JV-04 CIVIC BRIDGE      \
                         \              |                   \
       D4 JOE CREEK: NW/upstream =======+=====================> SE/downstream
                                         \ Cottonwood Bend       \
                                          \                       D5 WELLHOUSE QUARTER
                                           \                      JV-31/32/34
                                            JV-33 SUSHI                  |
                                                   \                 JV-01 RIDGE GATE
                                                    \                   (+3.6,-1.3)
                                                     v S / out-valley connector
```

The schematic shows topology, not scale. Node coordinates and approved routes below are authoritative.

## 4. District polygons and identity

| ID | District | Approximate bounds (km) | Elevation band | Principal access | Landmark rule |
|---|---|---:|---:|---|---|
| D1 | Ridge Gate / town edge | X +2.8…+4.2, Y -1.8…+0.3 | E -25…-5 | East Road | mountains visible west; Castle usually occluded |
| D2 | Hearthside Residential | X +0.4…+2.7, Y +0.2…+1.8 | E +5…+35 | North Street, East Arcade | partial mountain views at street ends |
| D3 | Downtown / Lantern Walk | X -0.8…+0.9, Y -0.1…+0.8 | E -5…+15 | West Gate, East Arcade, Civic Bridge | mountains visible west-axis; Castle only at one southwest vista |
| D4 | Creek Thread | X -2.8…+2.8 along drainage | E +35 west to -20 east | path/bridges | creek flow NW→SE always legible in masters |
| D5 | Wellhouse Quarter | X +0.8…+2.5, Y -1.0…+0.2 | E -15…+5 | East Arcade, Civic Bridge, East Road | open west mountain view across low roofs |
| D6 | Meadow Commons | X -2.9…-1.1, Y -1.2…+0.4 | E +45…+95 | Lantern West Gate, shuttle/bike court, T1 | broad west/northwest ridge view; Castle visible southwest |
| D7 | High Trails | X -4.5…-1.8, Y +0.3…+4.0 | E +100…+520 | T1, mountain road, north spur | town disappears in forest; returns at overlook only |
| D8 | Grace Ridge | X -4.0…-2.7, Y -2.3…-1.0 | E +180…+270 | mountain road, garden footpath | town visible east/southeast from designated terrace |

## 5. Canonical nodes

| Node | Set / place | Coordinate | Elev. | Public arrival side | Primary facing / view |
|---|---|---:|---:|---|---|
| N00 | Commons Court | (0.0, 0.0) | E0 | all sides | Lantern Walk E–W |
| N01 | Lantern West Gate | (-0.75, +0.05) | +8 | east/west | west to meadow approach |
| N02 | Lantern East Arcade | (+0.75, +0.05) | -3 | east/west | east to Wellhouse |
| N03 | Lantern & Lark Coffee | (+0.35, -0.05) | -2 | west/south corner | south windows toward creek side street |
| N04 | Civic Bridge | (+0.10, -0.45) | -8 | north/south | spans creek; south to Wellhouse |
| N05 | Stone Arch / creek downtown | (-0.55, -0.48) | -5 | path E/W | creek NW→SE |
| N06 | Grace Meadow center | (-2.10, -0.70) | +65 | east | mountains W/NW |
| N07 | Hearth Lodge | (-1.65, -0.35) | +72 | east/north | porch SW across meadow |
| N08 | Thirteen Stones Circle | (-2.10, -1.10) | +82 | east | view slit W/NW |
| N09 | Trailhead / T1 | (-2.35, +0.05) | +100 | east/south | ascent W/NW |
| N10 | Split Rock Junction / T3 | (-3.15, +1.35) | +270 | SE | forks N and W |
| N11 | Cloud Shelf Overlook / T5 | (-4.00, +1.30) | +500 | east | town E/SE |
| N12 | Joeville Falls shelf | (-3.60, +3.50) | +355 | southeast | falls face W/NW |
| N13 | Castle Grace gate | (-3.15, -1.55) | +220 | east/southeast | facade westward beyond court |
| N14 | Castle Grace main hall | (-3.40, -1.70) | +235 | east | terrace view E/SE from south/west wing |
| N15 | Castle amphitheater | (-3.20, -2.00) | +205 | north/east | stage NW, audience SE |
| N16 | Current Hall | (+1.25, -0.35) | -5 | east | stage west |
| N17 | Brightroot Juice | (+1.45, -0.10) | -6 | east | courtyard west exit |
| N18 | Juniper Tonic | (+1.40, -0.35) | -7 | east/courtyard | bar north/west |
| N19 | Riverstone Sushi | (+0.55, -0.65) | -10 | west | creek windows east/southeast |
| N20 | Joeville Commons Market | (+2.20, -0.45) | -12 | north | bike/parking court north |
| N21 | Ridge Gate / town sign | (+3.60, -1.30) | -25 | east/west road | arrival looks W/NW |
| N22 | Hearthside residential center | (+1.45, +0.85) | +20 | local grid | mountain glimpses west street ends |
| N23 | Transit / bike court | (-1.10, -0.20) | +25 | east/west | meadow shuttle west |
| N24 | Mountain-road pullout | (-2.80, -1.10) | +145 | road east/west | town view E/SE |

## 6. Canonical routes and travel chart

Travel times are narrative approximations under ordinary conditions. Dialogue-heavy walking can expand time; montage can compress it, but the route must remain plausible.

| Route ID | From → to | Mode | Time | Required intermediate geography |
|---|---|---|---:|---|
| R01 | Commons Court → Lantern & Lark Coffee | walk | 2 min | east half-block, south corner |
| R02 | Commons Court → Civic Bridge | walk | 4 min | south side street |
| R03 | Commons Court → Wellhouse courtyard | walk | 8 min | East Arcade or Civic Bridge; establish chosen route |
| R04 | Commons Court → Joeville Commons | walk/bike | 14 / 6 min | East Arcade, Wellhouse spine |
| R05 | Commons Court → Grace Meadow | walk/bike/shuttle | 18 / 8 / 7 min | Lantern West Gate, transit court/meadow approach |
| R06 | Meadow → Thirteen Stones Circle | walk | 5 min | south meadow path |
| R07 | Meadow → Trailhead T1 | walk | 6 min | northwestern meadow edge |
| R08 | Trailhead → Split Rock T3 | hike | 35 min | T1 Meadow Link, T2 Pine Fold |
| R09 | Split Rock → Cloud Shelf T5 | hike | 28 min | T4 Stone Ladder |
| R10 | Split Rock → Joeville Falls | hike | 42 min | T6 crossing, T7 north spur |
| R11 | Commons Court → Castle Grace | drive/shuttle | 18 min | west connector, mountain road, pullout, gate |
| R12 | Meadow → Castle Grace | hike/drive | 35 / 12 min | garden ridge trail or mountain road; not a direct cut |
| R13 | Ridge Gate → Commons Court | drive/bike | 12 / 22 min | East Road, Wellhouse edge, downtown approach |
| R14 | Coffee → Riverstone Sushi | walk | 7 min | south side street, creek bend |
| R15 | Creek downtown → Quiet Bank / East Footbridge | walk | 12 min | Cottonwood Bend then east path |
| R16 | Residential → Downtown | walk/bike | 10 / 4 min | North Street to East Arcade or Commons Court |
| R17 | Wellhouse → Current Hall | walk | 3 min | shared courtyard lane |
| R18 | Joeville Commons → Ridge Gate | drive/bike | 8 / 12 min | East Road |

### Transition rule

- Trips ≤5 min may cut directly after a clear exit/arrival match.
- Trips 6–15 min should include one connective shot, sound bridge, map cue, or time ellipsis when geography matters.
- Trips >15 min require a travel transition, explicit time cut, or dialogue acknowledgment.
- Mountain/trail changes always require an ascent/descent cue; characters cannot exit downtown and appear at Falls on the next continuous beat.

## 7. Road, path, and drainage hierarchy

- **East Road:** Ridge Gate → Joeville Commons/Wellhouse edge → downtown east. Main vehicular arrival.
- **North Street:** residential grid → Commons Court cross street.
- **West Connector:** downtown west → transit/bike court → meadow edge.
- **Grace Road:** branches from west connector below meadow, climbs south/west past JV-24 pullout to Castle gate. It does not run through the meadow.
- **Ribbon Path:** continuous creek multi-use path from high-country west/northwest through Downtown Steps and Cottonwood Bend to East Footbridge.
- **T1–T7:** walking trails only unless a separately designated service route is shown.
- **Creek tributary from Falls:** joins Joeville Creek upstream of downtown, off the most-used scenic map. It never crosses Lantern Walk.

## 8. Landmark visibility matrix

Legend: `Y` expected in a suitable open bearing; `L` limited/designated vista only; `N` normally occluded or wrong bearing.

| Viewer location | Mountains | Castle Grace | Downtown | Creek | Falls |
|---|---:|---:|---:|---:|---:|
| Ridge Gate | Y west | N | L west | N | N |
| Residential | L at west street ends | N | L southwest | N | N |
| Commons Court | Y down west axis | L southwest vista | — | N | N |
| Civic Bridge | Y west/northwest | N | Y north | Y | N |
| Wellhouse | Y west | L far southwest roofline only | L west | L at south/west edge | N |
| Grace Meadow | Y | Y southwest | L east | N | N |
| Thirteen Stones Circle | Y through west slit | L only from arrival edge | N | N | N |
| Pine Fold | N/L through trees | N | N | L at crossing | N |
| Cloud Shelf | Y | L south | Y east | L as valley trace | N |
| Falls shelf | Y/rock face | N | N | Y as outflow | — |
| Castle terrace | Y west edge | — | Y east/southeast | L valley trace | N |

Artists must satisfy both visibility and camera bearing. `Y` does not authorize a landmark behind the camera.

## 9. Building orientation ledger

| Set | Public facade / entry | Major windows | Service exit | Non-negotiable exterior relationship |
|---|---|---|---|---|
| Lantern & Lark Coffee | west/south corner | south | northeast | creekward side-street light, no direct mountain panorama |
| Current Hall | east | high north/south clerestories | northwest | west stage wall has no public entry |
| Brightroot Juice | east | south | north | west door opens to shared courtyard |
| Juniper Tonic | east/courtyard | south booths | north | linked courtyard, distinct facade from Juice |
| Riverstone Sushi | west | east/southeast creek | northeast | creek lies beyond windows, not street traffic |
| Joeville Commons | north | north vestibule/café west | south/east | bike/parking court north, service edge away from public plaza |
| Hearth Lodge | east/north entry | southwest porch | north | porch overlooks meadow |
| Castle Grace | east gate/front door | great room south/west; terrace east/southeast views by wing | northeast | main arrival cannot jump to terrace side |

## 10. District-to-district screen-direction convention

These are editorial defaults, not permission to mirror art.

- Travel **toward mountains/meadow/trails/Castle** tends screen-right→left after an establishing map shot.
- Travel **toward downtown/Wellhouse/Ridge Gate** tends screen-left→right.
- Joeville Creek flow tends screen-left→right in the canonical south-bank lateral master; the north-bank reverse must visibly establish the changed bank rather than pretending flow reversed.
- Trail ascent tends into frame left/up; descent tends right/down. Switchbacks may reverse locally, but a junction master resets direction.
- Castle approach climbs from east/southeast toward west/northwest. Castle departure reverses.

## 11. Camera-map requirements for every plate

Every scenic plate metadata record must include:

```yaml
set_id: JV-XX
camera_id: JV-XX-C##
map_coordinate: [x_km, y_km, relative_elevation_m]
look_bearing_deg: 0
shot_class: geographic_master | action_wide | dialogue | insert | elevated
horizon_y_normalized: 0.56
primary_vanishing_point: [x_normalized, y_normalized]
ground_anchor_ids: []
entry_edges: []
exit_edges: []
visible_landmarks: []
occluded_landmarks: []
sun_package: dawn | midday | golden | blue_hour | night
season_package: spring | summer | autumn | winter
weather_package: clear | cloud | rain | snow | storm
continuity_map_version: JV-MAP-0.1
mirror_prohibited: true
```

The `horizon_y_normalized: 0.56` value is inherited from current runtime evidence and remains provisional for scenic plates until the environment-capability audit is approved.

## 12. Set-level mapping package

Before a set is locked, create:

- a north-up plan with 1 CU grid and world-coordinate tie point;
- all public/service entries and one-way constraints;
- accessible routes and minimum clear widths;
- character bays and ensemble zones;
- camera positions and look cones;
- wall/foreground occlusion IDs;
- window view cones cross-checked against the landmark matrix;
- sun arrows for approved time/season packages;
- a route thumbnail connecting the set to adjacent production sets;
- a change log when any door, path, or landmark view moves.

## 13. Geography violation tests

A continuity reviewer must reject a plate or sequence if any answer is “yes” without an approved story explanation:

1. Does the creek flow southeast in one shot and northwest in its reverse?
2. Are the mountains east of a set that is not itself west of the range?
3. Is Castle Grace visible from a node marked `N`, or on the wrong bearing?
4. Did a window view move to a different wall?
5. Did a public entrance become a service door or swap sides?
6. Did a character reach Falls, Cloud Shelf, or Castle without adequate travel/ascent?
7. Did a mirrored plate reverse text, architecture, staff side, creek, or sunlight?
8. Did snow/leaf state/water level change across adjacent locations in continuous time?
9. Did a trail segment change its uphill direction without a switchback/junction master?
10. Did the Castle silhouette, tower position, roof count, terrace, or approach road change between views?

## 14. Map artifact status

The approved map team should derive, not reinvent, these from this specification:

1. `JV-MAP-PRODUCTION-v001` — **created at design-development level** as `../maps/JOEVILLE_PRODUCTION_MAP.svg`; coordinate/elevation/view-cone detail remains in this specification.
2. `JV-MAP-AUDIENCE-v001` — simplified illustrated town map without production metadata.
3. `JV-MAP-TRAVEL-v001` — transition times and montage routes.
4. `JV-MAP-CASTLE-v001` — campus, road, garden path, terrace and amphitheater.
5. `JV-MAP-TRAILS-v001` — T1–T7 topology, difficulty, safety/dialogue bays.
6. `JV-MAP-DOWNTOWN-v001` — Lantern Walk block/storefront order and bridge links.

The production overview is complete for design development. The audience, travel-detail, Castle, trail and downtown derivative maps remain planned.

## 15. Approval and revision protocol

- Approval creates `JV-MAP-1.0`.
- Later changes require a map change request listing affected sets, cameras, scripts, plates, clips, window views, travel times, and episode continuity.
- Cosmetic scenery may change without a map version only if it does not alter navigation, silhouette recognition, entrances, views, or travel.
- Emergency episode-specific geography is labeled a non-canonical cheat and cannot silently enter the reusable library.

## 16. Outstanding map decisions

- Confirm whether Castle Grace remains southwest of town or moves to a user-supplied canonical site.
- Confirm whether the Falls should connect to the main creek watershed visibly on the audience map.
- Confirm preferred degree of vehicular presence and whether a shuttle system is story-canonical.
- Confirm whether each of the 13 characters has a fixed home/work node, which would require a character-distribution overlay.
- Confirm whether the town name is styled “Joeville,” “Joe Ville,” or another user-approved mark on graphics.
