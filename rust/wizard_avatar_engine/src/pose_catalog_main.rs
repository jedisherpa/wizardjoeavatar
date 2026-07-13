use anyhow::Context;
use serde_json::json;
use std::path::PathBuf;
use wizard_avatar_engine::pose_archive::future_pose_catalog;

fn main() -> anyhow::Result<()> {
    let repository_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .context("resolve repository root")?;
    let catalog = future_pose_catalog().map_err(anyhow::Error::msg)?;
    catalog
        .validate(&repository_root)
        .map_err(anyhow::Error::msg)?;
    println!(
        "{}",
        serde_json::to_string_pretty(&json!({
            "schema_version": catalog.schema_version,
            "image_count": catalog.image_count,
            "packs": catalog.packs.iter().map(|pack| json!({
                "id": pack.id,
                "images": pack.image_count,
                "archive": pack.archive_name,
            })).collect::<Vec<_>>(),
            "status": "validated_reference_only",
        }))?
    );
    Ok(())
}
