use std::collections::BTreeSet;
use wizard_avatar_engine::reference_avatar::{
    reference_pose_ids, reference_pose_library_asset_set_id, reference_pose_library_available,
    reference_pose_library_schema_version, reference_pose_metadata,
    render_reference_avatar_pose_local,
};

#[test]
fn reference_pose_library_loads_schema_v2_metadata() {
    assert!(reference_pose_library_available());
    assert_eq!(reference_pose_library_schema_version(), Some(2));
    assert_eq!(
        reference_pose_library_asset_set_id(),
        Some("wizardjoe-reference-motion-v1")
    );

    let ids = reference_pose_ids().into_iter().collect::<BTreeSet<_>>();
    let required_baseline = BTreeSet::from([
        "back_idle".to_string(),
        "back_left".to_string(),
        "back_right".to_string(),
        "explaining".to_string(),
        "front_idle".to_string(),
        "magic_cast".to_string(),
        "profile_left".to_string(),
        "profile_right".to_string(),
        "walk_front_left".to_string(),
        "walk_front_right".to_string(),
    ]);
    assert!(
        required_baseline.is_subset(&ids),
        "pose library lost baseline poses: {:?}",
        required_baseline.difference(&ids).collect::<Vec<_>>()
    );

    for pose_id in ids {
        let metadata = reference_pose_metadata(&pose_id).expect("pose metadata");
        assert_eq!(metadata.id, pose_id);
        assert_eq!(metadata.cols, 72);
        assert_eq!(metadata.rows, 96);
        assert_eq!(metadata.root_anchor, (36, 95));
        assert_eq!(metadata.anchors.get("root"), Some(&(36, 95)));
        assert!(metadata.facing.is_some(), "{pose_id} has facing");
        assert!(metadata.locomotion.is_some(), "{pose_id} has locomotion");
        assert!(!metadata.actions.is_empty(), "{pose_id} has actions");
        for anchor in [
            "root",
            "mouth",
            "left_eye",
            "right_eye",
            "left_foot",
            "right_foot",
            "left_hand",
            "right_hand",
            "staff_hand",
            "staff_tip",
        ] {
            assert!(
                metadata.anchors.contains_key(anchor),
                "{pose_id} missing {anchor}"
            );
            let (x, y) = metadata.anchors[anchor];
            assert!(
                (0..metadata.cols as i32).contains(&x) && (0..metadata.rows as i32).contains(&y),
                "{pose_id} anchor {anchor} is outside the canonical canvas: ({x}, {y})"
            );
        }

        let rendered = render_reference_avatar_pose_local(&pose_id).expect("render pose");
        assert_eq!(rendered.pose_id, pose_id);
        assert_eq!(rendered.canvas.width, metadata.cols);
        assert_eq!(rendered.canvas.height, metadata.rows);
        assert_eq!(rendered.root_anchor, metadata.root_anchor);
    }
}
