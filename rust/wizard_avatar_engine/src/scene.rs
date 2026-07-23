use crate::cell::{Cell, CellCanvas};
use crate::palette::Rgb;
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;
use thiserror::Error;

pub const SCENE_SCHEMA_VERSION: u32 = 1;
const MAX_SCENE_DIMENSION: usize = 4096;

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SceneLayerKind {
    Background,
    SetPiece,
    Prop,
    Character,
    Effect,
    Foreground,
    BroadcastOverlay,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ScenePixel {
    pub glyph: u8,
    pub rgb: [u8; 3],
}

impl From<Cell> for ScenePixel {
    fn from(cell: Cell) -> Self {
        Self {
            glyph: cell.glyph,
            rgb: [cell.rgb.0, cell.rgb.1, cell.rgb.2],
        }
    }
}

impl From<ScenePixel> for Cell {
    fn from(pixel: ScenePixel) -> Self {
        Self::new(pixel.glyph, Rgb(pixel.rgb[0], pixel.rgb[1], pixel.rgb[2]))
    }
}

/// A contiguous horizontal run of opaque colored cells. Missing cells are transparent.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SceneCellRun {
    pub y: usize,
    pub x_start: usize,
    pub pixels: Vec<ScenePixel>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SceneElement {
    pub id: String,
    pub layer: SceneLayerKind,
    pub order: i32,
    pub origin: [i32; 2],
    pub width: usize,
    pub height: usize,
    pub visible: bool,
    pub runs: Vec<SceneCellRun>,
}

impl SceneElement {
    #[must_use]
    pub fn from_canvas(
        id: impl Into<String>,
        layer: SceneLayerKind,
        order: i32,
        canvas: &CellCanvas,
    ) -> Self {
        let mut runs = Vec::new();
        let occupied = canvas.occupied_cells().collect::<Vec<_>>();
        let mut cursor = 0;
        while cursor < occupied.len() {
            let (x, y, cell) = occupied[cursor];
            let x_start = x as usize;
            let mut last_x = x;
            let mut pixels = vec![cell.into()];
            cursor += 1;
            while cursor < occupied.len() {
                let (next_x, next_y, next_cell) = occupied[cursor];
                if next_y != y || next_x != last_x + 1 {
                    break;
                }
                pixels.push(next_cell.into());
                last_x = next_x;
                cursor += 1;
            }
            runs.push(SceneCellRun {
                y: y as usize,
                x_start,
                pixels,
            });
        }
        Self {
            id: id.into(),
            layer,
            order,
            origin: [0, 0],
            width: canvas.width,
            height: canvas.height,
            visible: true,
            runs,
        }
    }

    pub fn validate(&self) -> Result<(), SceneError> {
        validate_id("element", &self.id)?;
        validate_dimensions(self.width, self.height, &self.id)?;
        let mut occupied = BTreeSet::new();
        for (run_index, run) in self.runs.iter().enumerate() {
            if run.pixels.is_empty() {
                return Err(SceneError::EmptyRun {
                    element: self.id.clone(),
                    run: run_index,
                });
            }
            if run.y >= self.height
                || run.x_start >= self.width
                || run.x_start + run.pixels.len() > self.width
            {
                return Err(SceneError::RunOutOfBounds {
                    element: self.id.clone(),
                    run: run_index,
                });
            }
            for x in run.x_start..run.x_start + run.pixels.len() {
                if !occupied.insert((x, run.y)) {
                    return Err(SceneError::OverlappingRuns {
                        element: self.id.clone(),
                        x,
                        y: run.y,
                    });
                }
            }
        }
        Ok(())
    }

    fn paint(&self, canvas: &mut CellCanvas) {
        if !self.visible {
            return;
        }
        for run in &self.runs {
            for (offset, pixel) in run.pixels.iter().copied().enumerate() {
                let x = self.origin[0] + (run.x_start + offset) as i32;
                let y = self.origin[1] + run.y as i32;
                let cell: Cell = pixel.into();
                canvas.set(x, y, cell.glyph, cell.rgb);
            }
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SceneDefinition {
    pub schema_version: u32,
    pub id: String,
    pub width: usize,
    pub height: usize,
    pub clear_rgb: [u8; 3],
    pub elements: Vec<SceneElement>,
}

impl SceneDefinition {
    pub fn validate(&self) -> Result<(), SceneError> {
        if self.schema_version != SCENE_SCHEMA_VERSION {
            return Err(SceneError::UnsupportedSchema(self.schema_version));
        }
        validate_id("scene", &self.id)?;
        validate_dimensions(self.width, self.height, &self.id)?;
        validate_elements(&self.elements)
    }

    pub fn compose(&self) -> Result<CellCanvas, SceneError> {
        self.validate()?;
        let color = Rgb(self.clear_rgb[0], self.clear_rgb[1], self.clear_rgb[2]);
        let base = CellCanvas::filled(self.width, self.height, Cell::new(b' ', color));
        compose_over(base, &self.elements)
    }
}

pub fn compose_over(
    mut base: CellCanvas,
    elements: &[SceneElement],
) -> Result<CellCanvas, SceneError> {
    validate_dimensions(base.width, base.height, "runtime_scene")?;
    validate_elements(elements)?;
    let mut ordered = elements.iter().collect::<Vec<_>>();
    ordered.sort_by(|left, right| {
        (left.layer, left.order, left.id.as_str()).cmp(&(
            right.layer,
            right.order,
            right.id.as_str(),
        ))
    });
    for element in ordered {
        element.paint(&mut base);
    }
    Ok(base)
}

fn validate_elements(elements: &[SceneElement]) -> Result<(), SceneError> {
    let mut ids = BTreeSet::new();
    for element in elements {
        if !ids.insert(element.id.as_str()) {
            return Err(SceneError::DuplicateElement(element.id.clone()));
        }
        element.validate()?;
    }
    Ok(())
}

fn validate_dimensions(width: usize, height: usize, id: &str) -> Result<(), SceneError> {
    if width == 0 || height == 0 || width > MAX_SCENE_DIMENSION || height > MAX_SCENE_DIMENSION {
        return Err(SceneError::InvalidDimensions {
            id: id.to_string(),
            width,
            height,
        });
    }
    Ok(())
}

fn validate_id(kind: &'static str, id: &str) -> Result<(), SceneError> {
    if id.is_empty()
        || !id
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'_')
    {
        return Err(SceneError::InvalidId {
            kind,
            id: id.to_string(),
        });
    }
    Ok(())
}

#[derive(Debug, Error, PartialEq, Eq)]
pub enum SceneError {
    #[error("unsupported scene schema version {0}")]
    UnsupportedSchema(u32),
    #[error("invalid {kind} id {id:?}; use lowercase ASCII, digits, and underscores")]
    InvalidId { kind: &'static str, id: String },
    #[error("{id} has invalid scene dimensions {width}x{height}")]
    InvalidDimensions {
        id: String,
        width: usize,
        height: usize,
    },
    #[error("duplicate scene element id {0}")]
    DuplicateElement(String),
    #[error("{element} run {run} is empty")]
    EmptyRun { element: String, run: usize },
    #[error("{element} run {run} is outside its local canvas")]
    RunOutOfBounds { element: String, run: usize },
    #[error("{element} cell ({x}, {y}) appears in more than one run")]
    OverlappingRuns { element: String, x: usize, y: usize },
}

#[cfg(test)]
mod tests {
    use super::*;

    fn one_pixel(id: &str, layer: SceneLayerKind, order: i32, rgb: [u8; 3]) -> SceneElement {
        SceneElement {
            id: id.to_string(),
            layer,
            order,
            origin: [1, 1],
            width: 1,
            height: 1,
            visible: true,
            runs: vec![SceneCellRun {
                y: 0,
                x_start: 0,
                pixels: vec![ScenePixel { glyph: b'#', rgb }],
            }],
        }
    }

    #[test]
    fn categories_are_composed_in_cinematic_order() {
        let foreground = one_pixel("desk_front", SceneLayerKind::Foreground, 0, [3, 3, 3]);
        let character = one_pixel("wizard_joe", SceneLayerKind::Character, 0, [2, 2, 2]);
        let background = one_pixel("newsroom_wall", SceneLayerKind::Background, 0, [1, 1, 1]);
        let frame = compose_over(CellCanvas::new(3, 3), &[foreground, character, background])
            .expect("compose");
        assert_eq!(frame.get(1, 1).expect("cell").rgb, Rgb(3, 3, 3));
    }

    #[test]
    fn absent_cells_remain_transparent_to_lower_layers() {
        let mut character_canvas = CellCanvas::new(3, 1);
        character_canvas.set(0, 0, b'#', Rgb(2, 2, 2));
        character_canvas.set(2, 0, b'#', Rgb(2, 2, 2));
        let character = SceneElement::from_canvas(
            "wizard_joe",
            SceneLayerKind::Character,
            0,
            &character_canvas,
        );
        let base = CellCanvas::filled(3, 1, Cell::new(b' ', Rgb(1, 1, 1)));
        let frame = compose_over(base, &[character]).expect("compose");
        assert_eq!(frame.get(1, 0).expect("base cell").rgb, Rgb(1, 1, 1));
    }

    #[test]
    fn input_order_does_not_change_the_frame() {
        let low = one_pixel("character_body", SceneLayerKind::Character, 0, [1, 2, 3]);
        let high = one_pixel("character_face", SceneLayerKind::Character, 10, [4, 5, 6]);
        let first =
            compose_over(CellCanvas::new(3, 3), &[low.clone(), high.clone()]).expect("compose");
        let second = compose_over(CellCanvas::new(3, 3), &[high, low]).expect("compose");
        assert_eq!(first.to_frame_bytes(), second.to_frame_bytes());
    }

    #[test]
    fn serialized_scene_rejects_render_asset_shortcuts() {
        let json = r#"{
            "schema_version":1,
            "id":"newsroom",
            "width":3,
            "height":3,
            "clear_rgb":[255,255,255],
            "elements":[],
            "png":"flattened-scene.png"
        }"#;
        assert!(serde_json::from_str::<SceneDefinition>(json).is_err());
    }

    #[test]
    fn overlapping_runs_are_rejected() {
        let mut element = one_pixel("bad_prop", SceneLayerKind::Prop, 0, [1, 2, 3]);
        element.runs.push(element.runs[0].clone());
        assert!(matches!(
            element.validate(),
            Err(SceneError::OverlappingRuns { .. })
        ));
    }
}
