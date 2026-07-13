use crate::pose::{AnchorId, PoseSample};
use crate::state::{PlantedFoot, WizardState};

pub const HORIZON_RATIO: f32 = 0.48;
pub const FLOOR_RATIO: f32 = 0.95;
const NEAR_ROOT_RATIO: f32 = 0.88;
pub const MAX_CONTACT_CORRECTION: i32 = 2;

#[derive(Clone, Copy, Debug)]
pub struct ProjectedPoseContext {
    pub continuous_root: (f32, f32),
    pub quantized_root: (i32, i32),
    pub continuous_scale: f32,
    pub quantized_scale: f32,
    pub scale_level: i16,
    pub foot_correction: (i32, i32),
    pub horizon_y: f32,
    pub floor_y: f32,
}

#[derive(Clone, Debug, Default)]
struct FootContactSolver {
    active: PlantedFoot,
    target: Option<(i32, i32)>,
    correction: (i32, i32),
}

#[derive(Clone, Debug, Default)]
pub struct ProjectionHistory {
    scale_level: Option<i16>,
    root_cell: Option<(i32, i32)>,
    contacts: FootContactSolver,
}

impl ProjectionHistory {
    #[must_use]
    pub fn project(
        &mut self,
        state: &WizardState,
        pose: &PoseSample,
        width: usize,
        height: usize,
    ) -> ProjectedPoseContext {
        let (root_x, root_y, continuous_scale) = project_world_to_screen(
            state.world_position.x,
            state.world_position.z,
            width,
            height,
        );
        let scaled = continuous_scale * 8.0;
        let desired_level = scaled.round() as i16;
        let scale_level = match self.scale_level {
            None => desired_level,
            Some(previous)
                if desired_level != previous && (scaled - f32::from(previous)).abs() > 0.60 =>
            {
                previous + (desired_level - previous).signum()
            }
            Some(previous) => previous,
        };
        self.scale_level = Some(scale_level);
        let quantized_scale = f32::from(scale_level) / 8.0;
        let uncorrected_root = (root_x.round() as i32, root_y.round() as i32);
        let left = projected_anchor(pose, AnchorId::LeftFoot, root_x, root_y, quantized_scale);
        let right = projected_anchor(pose, AnchorId::RightFoot, root_x, root_y, quantized_scale);
        let active = state.contact_marker.planted_foot();
        let predicted = match active {
            PlantedFoot::Left => Some(left),
            PlantedFoot::Right => Some(right),
            PlantedFoot::Both => Some(((left.0 + right.0) / 2, (left.1 + right.1) / 2)),
            PlantedFoot::None => None,
        };
        if active != self.contacts.active {
            self.contacts.active = active;
            self.contacts.target = predicted.map(|point| {
                (
                    point.0 + self.contacts.correction.0,
                    point.1 + self.contacts.correction.1,
                )
            });
        }
        if let (Some(target), Some(predicted)) = (self.contacts.target, predicted) {
            let desired = (
                (target.0 - predicted.0).clamp(-MAX_CONTACT_CORRECTION, MAX_CONTACT_CORRECTION),
                (target.1 - predicted.1).clamp(-MAX_CONTACT_CORRECTION, MAX_CONTACT_CORRECTION),
            );
            self.contacts.correction.0 += (desired.0 - self.contacts.correction.0).clamp(-1, 1);
            self.contacts.correction.1 += (desired.1 - self.contacts.correction.1).clamp(-1, 1);
        } else {
            self.contacts.correction.0 -= self.contacts.correction.0.signum();
            self.contacts.correction.1 -= self.contacts.correction.1.signum();
        }
        self.contacts.correction.0 = self
            .contacts
            .correction
            .0
            .clamp(-MAX_CONTACT_CORRECTION, MAX_CONTACT_CORRECTION);
        self.contacts.correction.1 = self
            .contacts
            .correction
            .1
            .clamp(-MAX_CONTACT_CORRECTION, MAX_CONTACT_CORRECTION);
        let quantized_root = (
            uncorrected_root.0 + self.contacts.correction.0,
            uncorrected_root.1 + self.contacts.correction.1,
        );
        self.root_cell = Some(quantized_root);
        ProjectedPoseContext {
            continuous_root: (root_x, root_y),
            quantized_root,
            continuous_scale,
            quantized_scale,
            scale_level,
            foot_correction: self.contacts.correction,
            horizon_y: height as f32 * HORIZON_RATIO,
            floor_y: height as f32 * FLOOR_RATIO,
        }
    }
}

#[must_use]
pub fn project_world_to_screen(x: f32, z: f32, width: usize, height: usize) -> (f32, f32, f32) {
    const NEAR: f32 = 1.5;
    const FAR: f32 = 10.0;
    let horizon_y = height as f32 * HORIZON_RATIO;
    let near_y = height as f32 * NEAR_ROOT_RATIO;
    let depth = ((FAR - z) / (FAR - NEAR)).clamp(0.0, 1.0);
    // Keep the complete 96-row pose and its staff-tip effect inside the fixed
    // 270-row stage while retaining a monotonic, visibly useful depth range.
    let scale = 1.4 + depth * 0.8;
    let screen_x = width as f32 * 0.5 + x * width as f32 * 0.075 * scale;
    let screen_y = horizon_y + depth * (near_y - horizon_y);
    (screen_x, screen_y, scale)
}

fn projected_anchor(
    pose: &PoseSample,
    anchor: AnchorId,
    root_x: f32,
    root_y: f32,
    scale: f32,
) -> (i32, i32) {
    let point = pose.anchors[&anchor];
    (
        (root_x + (point.x - pose.root.0 as f32) * scale).round() as i32,
        (root_y + (point.y - pose.root.1 as f32) * scale).round() as i32,
    )
}
