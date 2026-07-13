use serde::{Deserialize, Serialize};
use serde_json::Value;

pub const EVIDENCE_SCHEMA_VERSION: u16 = 1;
pub const EVIDENCE_SIMULATION_HZ: u32 = 60;
pub const EVIDENCE_RENDER_HZ: u32 = 24;

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct ReplayCommandSpec {
    #[serde(rename = "type")]
    pub command_type: String,
    #[serde(default)]
    pub payload: Value,
}

impl ReplayCommandSpec {
    #[must_use]
    pub fn new(command_type: impl Into<String>, payload: Value) -> Self {
        Self {
            command_type: command_type.into(),
            payload,
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct ReplayTransition {
    pub id: String,
    pub ledger_transition: String,
    pub category: String,
    pub setup: Vec<ReplayCommandSpec>,
    pub boundary: Vec<ReplayCommandSpec>,
    pub force_full_at_boundary: bool,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct ReplayManifest {
    pub schema_version: u16,
    pub simulation_hz: u32,
    pub render_hz: u32,
    pub pre_boundary_frames: u32,
    pub post_boundary_frames: u32,
    pub transitions: Vec<ReplayTransition>,
}

#[derive(Clone, Copy, Debug, Default)]
pub struct ExactRenderClock {
    accumulated: u32,
    render_hz: u32,
    simulation_hz: u32,
}

impl ExactRenderClock {
    #[must_use]
    pub const fn new(simulation_hz: u32, render_hz: u32) -> Self {
        Self {
            accumulated: 0,
            render_hz,
            simulation_hz,
        }
    }

    #[must_use]
    pub fn simulation_tick(&mut self) -> bool {
        self.accumulated += self.render_hz;
        if self.accumulated >= self.simulation_hz {
            self.accumulated -= self.simulation_hz;
            true
        } else {
            false
        }
    }
}

#[must_use]
pub fn stable_hash64(bytes: &[u8]) -> String {
    let mut hash = 0xcbf2_9ce4_8422_2325_u64;
    for byte in bytes {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
    }
    format!("{hash:016x}")
}

#[must_use]
pub fn crc32(bytes: &[u8]) -> String {
    format!("{:08x}", crc32fast::hash(bytes))
}

#[must_use]
pub fn cell_rgb_bytes(cells: &[u8]) -> Vec<u8> {
    cells
        .chunks_exact(4)
        .flat_map(|cell| [cell[1], cell[2], cell[3]])
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exact_render_clock_emits_twenty_four_samples_per_sixty_ticks() {
        let mut clock = ExactRenderClock::new(60, 24);
        let ticks = (1..=60)
            .filter(|_| clock.simulation_tick())
            .collect::<Vec<_>>();
        assert_eq!(ticks.len(), 24);
        assert!(ticks
            .windows(2)
            .all(|pair| matches!(pair[1] - pair[0], 2 | 3)));
    }

    #[test]
    fn replay_manifest_round_trips_without_semantic_drift() {
        let manifest = ReplayManifest {
            schema_version: EVIDENCE_SCHEMA_VERSION,
            simulation_hz: EVIDENCE_SIMULATION_HZ,
            render_hz: EVIDENCE_RENDER_HZ,
            pre_boundary_frames: 12,
            post_boundary_frames: 16,
            transitions: vec![ReplayTransition {
                id: "idle-to-walk".to_string(),
                ledger_transition: "idle -> walk".to_string(),
                category: "locomotion-directions".to_string(),
                setup: Vec::new(),
                boundary: vec![ReplayCommandSpec::new(
                    "move",
                    serde_json::json!({"x": 2.0, "z": 5.0}),
                )],
                force_full_at_boundary: false,
            }],
        };
        let encoded = serde_json::to_vec(&manifest).expect("serialize manifest");
        let decoded: ReplayManifest = serde_json::from_slice(&encoded).expect("decode manifest");
        assert_eq!(decoded, manifest);
    }

    #[test]
    fn evidence_hashes_are_stable_and_rgb_excludes_glyph_bytes() {
        let cells = [b'#', 1, 2, 3, b'@', 4, 5, 6];
        assert_eq!(stable_hash64(&cells), stable_hash64(&cells));
        assert_eq!(crc32(&cells), crc32(&cells));
        assert_eq!(cell_rgb_bytes(&cells), vec![1, 2, 3, 4, 5, 6]);
    }
}
