use std::sync::Arc;
use tokio::time::{timeout, Duration};
use wizard_avatar_engine::codec::{decode_frame, CELL_BYTES};
use wizard_avatar_engine::frame_source::ProceduralWizardFrameSource;
use wizard_avatar_engine::hub::AvatarFrameHub;

#[tokio::test]
async fn wiz_pace_002_healthy_viewers_receive_identical_canonical_packets() {
    let hub = AvatarFrameHub::start(ProceduralWizardFrameSource::default());
    let mut first = hub.subscribe();
    let mut second = hub.subscribe();

    for _ in 0..8 {
        let a = timeout(Duration::from_secs(2), first.recv())
            .await
            .expect("first viewer timed out")
            .expect("first viewer lagged");
        let b = timeout(Duration::from_secs(2), second.recv())
            .await
            .expect("second viewer timed out")
            .expect("second viewer lagged");
        assert_eq!(a.epoch, b.epoch);
        assert_eq!(a.sequence, b.sequence);
        assert!(Arc::ptr_eq(&a.encoded, &b.encoded));
        assert_eq!(a.encoded.as_ref(), b.encoded.as_ref());
    }
}

#[tokio::test]
async fn wiz_resync_001_bootstrap_is_full_and_does_not_reset_canonical_history() {
    let hub = AvatarFrameHub::start(ProceduralWizardFrameSource::default());
    let mut healthy = hub.subscribe();
    let first = timeout(Duration::from_secs(2), healthy.recv())
        .await
        .expect("canonical frame timed out")
        .expect("canonical receiver lagged");
    let (_, first_cells, _) = decode_frame(&first.encoded, None, CELL_BYTES).expect("first full");

    let bootstrap = hub
        .bootstrap()
        .await
        .expect("encode latest bootstrap")
        .expect("latest bootstrap");
    let (bootstrap_sequence, bootstrap_cells, bootstrap_tag) =
        decode_frame(&bootstrap.encoded, None, CELL_BYTES).expect("bootstrap full frame");
    assert_eq!(bootstrap_sequence, bootstrap.sequence);
    assert_eq!(bootstrap_cells.as_slice(), bootstrap.full_cells.as_ref());
    assert_ne!(bootstrap_tag as u8, 2, "bootstrap must never be a delta");

    let next = timeout(Duration::from_secs(2), healthy.recv())
        .await
        .expect("next canonical frame timed out")
        .expect("canonical receiver lagged after bootstrap");
    assert_eq!(next.sequence, first.sequence + 1);
    let (_, next_cells, _) = decode_frame(&next.encoded, Some(&first_cells), CELL_BYTES)
        .expect("healthy history remains decodable");
    assert_eq!(next_cells.as_slice(), next.full_cells.as_ref());
}

#[tokio::test]
async fn wiz_pace_003_slow_viewer_lags_bounded_without_affecting_healthy_cadence() {
    let hub = AvatarFrameHub::start(ProceduralWizardFrameSource::default());
    let mut healthy = hub.subscribe();
    let mut slow = hub.subscribe();
    let mut previous_sequence = None;

    for _ in 0..24 {
        let packet = timeout(Duration::from_secs(2), healthy.recv())
            .await
            .expect("healthy viewer timed out")
            .expect("healthy viewer lagged");
        if let Some(previous) = previous_sequence {
            assert_eq!(packet.sequence, previous + 1);
        }
        previous_sequence = Some(packet.sequence);
    }

    let lag = slow
        .recv()
        .await
        .expect_err("slow viewer must report bounded lag");
    assert!(matches!(
        lag,
        tokio::sync::broadcast::error::RecvError::Lagged(_)
    ));
    let bootstrap = hub
        .bootstrap()
        .await
        .expect("encode lag recovery")
        .expect("lag recovery bootstrap");
    let (_, decoded, tag) =
        decode_frame(&bootstrap.encoded, None, CELL_BYTES).expect("decode lag recovery full frame");
    assert_ne!(tag as u8, 2);
    assert_eq!(decoded.as_slice(), bootstrap.full_cells.as_ref());
}
