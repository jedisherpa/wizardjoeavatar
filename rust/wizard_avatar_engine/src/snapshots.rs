use anyhow::{bail, Context};
use serde::Serialize;
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use wizard_avatar_engine::codec::CELL_BYTES;
use wizard_avatar_engine::frame_source::{render_state_to_cells, DEFAULT_COLS, DEFAULT_ROWS};
use wizard_avatar_engine::state::{
    Action, ContactMarker, Direction, Expression, Locomotion, MouthShape, StaffState,
    UpperBodyAction, Velocity, WizardState,
};

const COLS: usize = DEFAULT_COLS;
const ROWS: usize = DEFAULT_ROWS;
const TILE_W: usize = 1;
const TILE_H: usize = 1;

#[derive(Clone, Copy, Debug)]
enum SnapshotKind {
    Direction(Direction),
    Expression(Expression),
    Action(Action),
    WalkPhase(f32),
}

#[derive(Clone, Debug)]
struct SnapshotSpec {
    id: &'static str,
    description: &'static str,
    kind: SnapshotKind,
}

#[derive(Debug, Serialize)]
struct SnapshotRecord {
    id: &'static str,
    description: &'static str,
    ppm_path: String,
    frame_bytes: usize,
    non_background_cells: usize,
    glyph_counts: BTreeMap<String, usize>,
    color_counts: BTreeMap<String, usize>,
}

#[derive(Debug, Serialize)]
struct SnapshotManifest {
    cols: usize,
    rows: usize,
    tile_width: usize,
    tile_height: usize,
    snapshots: Vec<SnapshotRecord>,
}

fn main() -> anyhow::Result<()> {
    let root =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../evidence/wizard/rust-snapshots");
    std::fs::create_dir_all(&root)
        .with_context(|| format!("failed to create {}", root.display()))?;

    let mut records = Vec::new();
    for spec in snapshot_specs() {
        let mut state = state_for(spec.kind);
        let cells = render_state_to_cells(&mut state, COLS, ROWS);
        validate_frame(&cells, spec.id)?;
        let file_name = format!("{}.ppm", spec.id);
        let path = root.join(&file_name);
        write_ppm(&path, &cells).with_context(|| format!("failed to write {}", path.display()))?;
        records.push(SnapshotRecord {
            id: spec.id,
            description: spec.description,
            ppm_path: file_name,
            frame_bytes: cells.len(),
            non_background_cells: count_non_background(&cells),
            glyph_counts: glyph_counts(&cells),
            color_counts: color_counts(&cells),
        });
    }

    let manifest = SnapshotManifest {
        cols: COLS,
        rows: ROWS,
        tile_width: TILE_W,
        tile_height: TILE_H,
        snapshots: records,
    };
    let json_path = root.join("manifest.json");
    let md_path = root.join("README.md");
    std::fs::write(&json_path, serde_json::to_vec_pretty(&manifest)?)
        .with_context(|| format!("failed to write {}", json_path.display()))?;
    std::fs::write(&md_path, render_markdown(&manifest))
        .with_context(|| format!("failed to write {}", md_path.display()))?;
    println!("wrote {}", json_path.display());
    println!("wrote {}", md_path.display());
    println!("wrote {} PPM snapshots", manifest.snapshots.len());
    Ok(())
}

fn snapshot_specs() -> Vec<SnapshotSpec> {
    vec![
        SnapshotSpec {
            id: "direction-south",
            description: "front idle",
            kind: SnapshotKind::Direction(Direction::South),
        },
        SnapshotSpec {
            id: "direction-southwest",
            description: "front-left idle",
            kind: SnapshotKind::Direction(Direction::SouthWest),
        },
        SnapshotSpec {
            id: "direction-west",
            description: "left idle",
            kind: SnapshotKind::Direction(Direction::West),
        },
        SnapshotSpec {
            id: "direction-northwest",
            description: "back-left idle",
            kind: SnapshotKind::Direction(Direction::NorthWest),
        },
        SnapshotSpec {
            id: "direction-north",
            description: "back idle",
            kind: SnapshotKind::Direction(Direction::North),
        },
        SnapshotSpec {
            id: "direction-northeast",
            description: "back-right idle",
            kind: SnapshotKind::Direction(Direction::NorthEast),
        },
        SnapshotSpec {
            id: "direction-east",
            description: "right idle",
            kind: SnapshotKind::Direction(Direction::East),
        },
        SnapshotSpec {
            id: "direction-southeast",
            description: "front-right idle",
            kind: SnapshotKind::Direction(Direction::SouthEast),
        },
        SnapshotSpec {
            id: "expression-neutral",
            description: "neutral expression",
            kind: SnapshotKind::Expression(Expression::Neutral),
        },
        SnapshotSpec {
            id: "expression-happy",
            description: "happy expression",
            kind: SnapshotKind::Expression(Expression::Happy),
        },
        SnapshotSpec {
            id: "expression-thinking",
            description: "thinking expression",
            kind: SnapshotKind::Expression(Expression::Thinking),
        },
        SnapshotSpec {
            id: "expression-surprised",
            description: "surprised expression",
            kind: SnapshotKind::Expression(Expression::Surprised),
        },
        SnapshotSpec {
            id: "expression-worried",
            description: "worried expression",
            kind: SnapshotKind::Expression(Expression::Worried),
        },
        SnapshotSpec {
            id: "expression-amused",
            description: "amused expression",
            kind: SnapshotKind::Expression(Expression::Amused),
        },
        SnapshotSpec {
            id: "expression-confident",
            description: "confident expression",
            kind: SnapshotKind::Expression(Expression::Confident),
        },
        SnapshotSpec {
            id: "expression-focused",
            description: "focused expression",
            kind: SnapshotKind::Expression(Expression::Focused),
        },
        SnapshotSpec {
            id: "expression-skeptical",
            description: "skeptical expression",
            kind: SnapshotKind::Expression(Expression::Skeptical),
        },
        SnapshotSpec {
            id: "expression-explaining",
            description: "explaining expression",
            kind: SnapshotKind::Expression(Expression::Explaining),
        },
        SnapshotSpec {
            id: "action-idle",
            description: "idle action",
            kind: SnapshotKind::Action(Action::Idle),
        },
        SnapshotSpec {
            id: "action-speaking",
            description: "speaking action",
            kind: SnapshotKind::Action(Action::Speaking),
        },
        SnapshotSpec {
            id: "action-explaining",
            description: "explaining action",
            kind: SnapshotKind::Action(Action::Explaining),
        },
        SnapshotSpec {
            id: "action-walking",
            description: "walking action",
            kind: SnapshotKind::Action(Action::Walking),
        },
        SnapshotSpec {
            id: "action-thinking",
            description: "thinking action",
            kind: SnapshotKind::Action(Action::Thinking),
        },
        SnapshotSpec {
            id: "action-pointing",
            description: "pointing action",
            kind: SnapshotKind::Action(Action::Pointing),
        },
        SnapshotSpec {
            id: "action-magic-cast",
            description: "magic cast action",
            kind: SnapshotKind::Action(Action::MagicCast),
        },
        SnapshotSpec {
            id: "action-reaction",
            description: "reaction action",
            kind: SnapshotKind::Action(Action::Reaction),
        },
        SnapshotSpec {
            id: "walk-phase-000",
            description: "walk phase 0.00",
            kind: SnapshotKind::WalkPhase(0.0),
        },
        SnapshotSpec {
            id: "walk-phase-025",
            description: "walk phase 0.25",
            kind: SnapshotKind::WalkPhase(0.25),
        },
        SnapshotSpec {
            id: "walk-phase-050",
            description: "walk phase 0.50",
            kind: SnapshotKind::WalkPhase(0.5),
        },
        SnapshotSpec {
            id: "walk-phase-075",
            description: "walk phase 0.75",
            kind: SnapshotKind::WalkPhase(0.75),
        },
    ]
}

fn state_for(kind: SnapshotKind) -> WizardState {
    let mut state = WizardState {
        time_seconds: 0.33,
        ..WizardState::default()
    };
    match kind {
        SnapshotKind::Direction(direction) => {
            state.facing = direction;
        }
        SnapshotKind::Expression(expression) => {
            state.expression = expression;
            state.mouth = mouth_for_expression(expression);
        }
        SnapshotKind::Action(action) => apply_action_state(&mut state, action),
        SnapshotKind::WalkPhase(phase) => {
            state.action = Action::Walking;
            state.locomotion = Locomotion::Walking;
            state.walk_phase = phase;
            state.speed_ratio = 1.0;
            state.contact_marker = ContactMarker::from_phase(phase);
            state.planted_foot = state.contact_marker.planted_foot();
            state.velocity = Velocity { x: 1.0, z: 0.0 };
        }
    }
    state
}

fn apply_action_state(state: &mut WizardState, action: Action) {
    state.action = action;
    match action {
        Action::Idle => {}
        Action::Speaking => {
            state.upper_body_action = UpperBodyAction::Explain;
            state.mouth = MouthShape::OpenMedium;
            state.speech_id = Some("snapshot-speech".to_string());
            state.speech_until = 3.0;
        }
        Action::Explaining => {
            state.upper_body_action = UpperBodyAction::Explain;
            state.expression = Expression::Explaining;
            state.mouth = MouthShape::OpenSmall;
        }
        Action::Walking => {
            state.locomotion = Locomotion::Walking;
            state.walk_phase = 0.25;
            state.speed_ratio = 1.0;
            state.contact_marker = ContactMarker::from_phase(state.walk_phase);
            state.planted_foot = state.contact_marker.planted_foot();
            state.velocity = Velocity { x: 1.0, z: 0.0 };
        }
        Action::Thinking => {
            state.upper_body_action = UpperBodyAction::Think;
            state.expression = Expression::Thinking;
        }
        Action::Pointing => {
            state.upper_body_action = UpperBodyAction::Point;
            state.staff_state = StaffState::Point;
        }
        Action::MagicCast => {
            state.upper_body_action = UpperBodyAction::Cast;
            state.staff_state = StaffState::Cast;
            state.time_seconds = 0.42;
        }
        Action::Reaction => {
            state.upper_body_action = UpperBodyAction::React;
            state.expression = Expression::Surprised;
        }
    }
}

fn mouth_for_expression(expression: Expression) -> MouthShape {
    match expression {
        Expression::Happy | Expression::Amused | Expression::Confident => MouthShape::Smile,
        Expression::Surprised => MouthShape::OpenWide,
        Expression::Worried | Expression::Skeptical => MouthShape::Frown,
        Expression::Explaining => MouthShape::OpenSmall,
        Expression::Neutral | Expression::Thinking | Expression::Focused => MouthShape::Closed,
    }
}

fn validate_frame(cells: &[u8], id: &str) -> anyhow::Result<()> {
    if cells.len() != COLS * ROWS * CELL_BYTES {
        bail!("{id} produced wrong frame length: {}", cells.len());
    }
    let reference_fill_count = cells
        .chunks_exact(CELL_BYTES)
        .filter(|cell| cell[0] == b'#')
        .count();
    let has_blue = cells
        .chunks_exact(CELL_BYTES)
        .any(|cell| cell[1] < 40 && cell[2] > 90 && cell[3] > 140);
    let has_warm_or_rainbow = cells
        .chunks_exact(CELL_BYTES)
        .any(|cell| cell[1] > 180 && cell[2] > 80 && cell[3] < 80);
    // Side and back silhouettes intentionally occupy fewer cells than the
    // front pose, so visual identity checks must not encode one front-view
    // area threshold. Every authored view still has thousands of direct
    // reference cells plus the defining blue and warm/rainbow palette bands.
    if reference_fill_count < 5_000 || !has_blue || !has_warm_or_rainbow {
        bail!("{id} missing expected reference-avatar visual signals");
    }
    Ok(())
}

fn write_ppm(path: &Path, cells: &[u8]) -> anyhow::Result<()> {
    let width = COLS * TILE_W;
    let height = ROWS * TILE_H;
    let mut out = Vec::new();
    out.extend_from_slice(format!("P6\n{width} {height}\n255\n").as_bytes());
    for row in 0..ROWS {
        for tile_y in 0..TILE_H {
            for col in 0..COLS {
                let offset = (row * COLS + col) * CELL_BYTES;
                let glyph = cells[offset];
                let rgb = [cells[offset + 1], cells[offset + 2], cells[offset + 3]];
                for tile_x in 0..TILE_W {
                    let mark_pixel =
                        glyph != b' ' && (tile_x == TILE_W / 2 || tile_y == TILE_H / 2);
                    if mark_pixel {
                        out.extend_from_slice(&rgb);
                    } else {
                        out.extend_from_slice(&lighten(rgb));
                    }
                }
            }
        }
    }
    std::fs::write(path, out)?;
    Ok(())
}

fn lighten(rgb: [u8; 3]) -> [u8; 3] {
    [
        ((rgb[0] as u16 + 255 * 3) / 4) as u8,
        ((rgb[1] as u16 + 255 * 3) / 4) as u8,
        ((rgb[2] as u16 + 255 * 3) / 4) as u8,
    ]
}

fn count_non_background(cells: &[u8]) -> usize {
    cells
        .chunks_exact(CELL_BYTES)
        .filter(|cell| !(cell[0] == b' ' && cell[1] == 255 && cell[2] == 255 && cell[3] == 255))
        .count()
}

fn glyph_counts(cells: &[u8]) -> BTreeMap<String, usize> {
    let mut counts = BTreeMap::new();
    for cell in cells.chunks_exact(CELL_BYTES) {
        let glyph = String::from_utf8_lossy(&[cell[0]]).to_string();
        *counts.entry(glyph).or_insert(0) += 1;
    }
    counts
}

fn color_counts(cells: &[u8]) -> BTreeMap<String, usize> {
    let mut counts = BTreeMap::new();
    for cell in cells.chunks_exact(CELL_BYTES) {
        let color = format!("#{:02X}{:02X}{:02X}", cell[1], cell[2], cell[3]);
        *counts.entry(color).or_insert(0) += 1;
    }
    counts
}

fn render_markdown(manifest: &SnapshotManifest) -> String {
    let mut out = String::new();
    out.push_str("# Rust Wizard Avatar Snapshots\n\n");
    out.push_str(&format!(
        "- grid: `{} x {}` cells\n- tile expansion: `{} x {}` pixels per cell\n- snapshots: `{}`\n\n",
        manifest.cols,
        manifest.rows,
        manifest.tile_width,
        manifest.tile_height,
        manifest.snapshots.len()
    ));
    out.push_str("## Files\n\n");
    for snapshot in &manifest.snapshots {
        out.push_str(&format!(
            "- `{}` - `{}` - {} non-background cells - `{}`\n",
            snapshot.id, snapshot.ppm_path, snapshot.non_background_cells, snapshot.description
        ));
    }
    out
}
