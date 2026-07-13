use crate::motion_graph::{MotionGraphV1, RuntimeGeometryAuthority};
use crate::pose::PoseLibrary;
use sha2::{Digest, Sha256};
use std::sync::OnceLock;

const EMBEDDED_MOTION_GRAPH_JSON: &str = include_str!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/assets/wizard_chat_motion_graph_v1.json"
));

pub const EMBEDDED_MOTION_GRAPH_SHA256: &str =
    "04df2b13940e1109555569e93b8610f026425749086c1036328bd30a54a6b19e";

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ShadowMotionCatalog {
    pub graph: MotionGraphV1,
    pub sha256: String,
}

static SHADOW_MOTION_CATALOG: OnceLock<Result<ShadowMotionCatalog, String>> = OnceLock::new();

pub fn shadow_motion_catalog() -> Result<&'static ShadowMotionCatalog, String> {
    SHADOW_MOTION_CATALOG
        .get_or_init(|| {
            load_shadow_motion_catalog(
                EMBEDDED_MOTION_GRAPH_JSON,
                EMBEDDED_MOTION_GRAPH_SHA256,
                runtime_geometry_authority()?,
            )
        })
        .as_ref()
        .map_err(Clone::clone)
}

pub fn load_shadow_motion_catalog(
    json: &str,
    expected_sha256: &str,
    authority: Vec<RuntimeGeometryAuthority>,
) -> Result<ShadowMotionCatalog, String> {
    let sha256 = sha256_hex(json.as_bytes());
    if sha256 != expected_sha256 {
        return Err(format!(
            "embedded motion graph SHA-256 mismatch: expected {expected_sha256}, got {sha256}"
        ));
    }
    let graph = MotionGraphV1::from_json(json).map_err(|error| error.to_string())?;
    graph
        .validate_against_runtime_authority(&authority)
        .map_err(|error| error.to_string())?;
    Ok(ShadowMotionCatalog { graph, sha256 })
}

pub fn runtime_geometry_authority() -> Result<Vec<RuntimeGeometryAuthority>, String> {
    let library = PoseLibrary::reference()?;
    let mut authority = Vec::with_capacity(library.pose_ids().count());
    for pose_id in library.pose_ids() {
        let pose = library
            .for_id(pose_id)
            .ok_or_else(|| format!("runtime pose authority lost pose {pose_id}"))?;
        authority.push(RuntimeGeometryAuthority {
            pose_id: pose.id.clone(),
            source_candidate_id: pose.motion.candidate_id.clone(),
            authored_facing: pose.direction,
        });
    }
    Ok(authority)
}

#[must_use]
pub fn embedded_motion_graph_json() -> &'static str {
    EMBEDDED_MOTION_GRAPH_JSON
}

#[must_use]
pub fn sha256_hex(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
