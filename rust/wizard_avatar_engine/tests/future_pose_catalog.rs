use std::path::PathBuf;
use wizard_avatar_engine::pose_archive::future_pose_catalog;

#[test]
fn all_future_pose_sources_are_present_and_hash_exact() {
    let repository_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("repository root");
    let catalog = future_pose_catalog().expect("future pose catalog");
    catalog.validate(&repository_root).expect("valid catalog");
    assert_eq!(catalog.image_count, 30);
    assert_eq!(
        catalog.packs[0].image_count + catalog.packs[1].image_count,
        30
    );
}
