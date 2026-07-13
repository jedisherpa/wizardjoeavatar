use futures_util::{SinkExt, StreamExt};
use tokio::net::TcpListener;
use tokio_tungstenite::connect_async;
use tokio_tungstenite::tungstenite::Message;
use wizard_avatar_engine::codec::{decode_frame, CodecTag, CELL_BYTES};
use wizard_avatar_engine::frame_source::{
    ProceduralWizardFrameSource, DEFAULT_COLS, DEFAULT_FPS, DEFAULT_ROWS,
};
use wizard_avatar_engine::server;

#[tokio::test]
async fn adaptive_websocket_reconstructs_wizard_frame() {
    let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
    let addr = listener.local_addr().expect("local addr");
    let app = server::app(ProceduralWizardFrameSource::default());
    let server_task = tokio::spawn(async move {
        axum::serve(listener, app).await.expect("test server");
    });

    let (mut socket, _) = connect_async(format!("ws://{addr}/ws/avatar/wizard?codec=adaptive"))
        .await
        .expect("connect websocket");

    let init = socket.next().await.expect("init message").expect("init ok");
    match init {
        Message::Text(text) => {
            assert!(text.starts_with(&format!(
                "INIT:{DEFAULT_FPS}:5:{DEFAULT_COLS}:{DEFAULT_ROWS}:0:0:0.000"
            )));
            assert!(text.contains(":EPOCH:"));
            assert!(text.ends_with(":CELL_BYTES:4:CODEC:1"));
        }
        other => panic!("expected INIT text, got {other:?}"),
    }

    let frame_message = socket
        .next()
        .await
        .expect("frame message")
        .expect("frame ok");
    let Message::Binary(bytes) = frame_message else {
        panic!("expected binary frame");
    };
    let (_frame_index, decoded, tag) = decode_frame(&bytes, None, CELL_BYTES).expect("decode");
    assert_ne!(tag, CodecTag::Delta);
    assert_eq!(decoded.len(), DEFAULT_COLS * DEFAULT_ROWS * CELL_BYTES);
    assert!(decoded.chunks_exact(CELL_BYTES).any(|cell| cell[0] == b'#'));

    socket.close(None).await.expect("close websocket");
    server_task.abort();
}

#[tokio::test]
async fn reconnect_and_explicit_resync_do_not_corrupt_a_healthy_viewer() {
    let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
    let addr = listener.local_addr().expect("local addr");
    let app = server::app(ProceduralWizardFrameSource::default());
    let server_task = tokio::spawn(async move {
        axum::serve(listener, app).await.expect("test server");
    });

    let (mut healthy, _) = connect_async(format!("ws://{addr}/ws/avatar/wizard?codec=adaptive"))
        .await
        .expect("connect healthy viewer");
    let _healthy_init = healthy
        .next()
        .await
        .expect("healthy init")
        .expect("healthy init ok");
    let healthy_first = next_binary(&mut healthy).await;
    let (_, mut healthy_previous, _) =
        decode_frame(&healthy_first, None, CELL_BYTES).expect("healthy bootstrap");

    let (mut reconnecting, _) =
        connect_async(format!("ws://{addr}/ws/avatar/wizard?codec=adaptive"))
            .await
            .expect("connect second viewer");
    let _second_init = reconnecting
        .next()
        .await
        .expect("second init")
        .expect("second init ok");
    let second_bootstrap = next_binary(&mut reconnecting).await;
    let (_, _, second_tag) =
        decode_frame(&second_bootstrap, None, CELL_BYTES).expect("second viewer full bootstrap");
    assert_ne!(second_tag as u8, 2);

    reconnecting
        .send(Message::Text(
            serde_json::json!({
                "type": "resync",
                "payload": {
                    "epoch": 0,
                    "last_valid_sequence": 0,
                    "reason": "missing_delta"
                }
            })
            .to_string(),
        ))
        .await
        .expect("request resync");

    let mut saw_resync_full = false;
    for _ in 0..6 {
        let bytes = next_binary(&mut reconnecting).await;
        if bytes[4] != 2 {
            let (_, _, tag) = decode_frame(&bytes, None, CELL_BYTES).expect("resync full frame");
            assert_ne!(tag as u8, 2);
            saw_resync_full = true;
            break;
        }
    }
    assert!(saw_resync_full, "explicit resync returns a full frame");

    for _ in 0..6 {
        let bytes = next_binary(&mut healthy).await;
        let (_, decoded, _) = decode_frame(&bytes, Some(&healthy_previous), CELL_BYTES)
            .expect("healthy canonical chain remains valid");
        healthy_previous = decoded;
    }

    reconnecting.close(None).await.expect("close second viewer");
    let (mut reconnected, _) =
        connect_async(format!("ws://{addr}/ws/avatar/wizard?codec=adaptive"))
            .await
            .expect("reconnect second viewer");
    let _reconnect_init = reconnected
        .next()
        .await
        .expect("reconnect init")
        .expect("reconnect init ok");
    let reconnect_bootstrap = next_binary(&mut reconnected).await;
    decode_frame(&reconnect_bootstrap, None, CELL_BYTES).expect("reconnect full bootstrap");

    let healthy_after_reconnect = next_binary(&mut healthy).await;
    decode_frame(
        &healthy_after_reconnect,
        Some(&healthy_previous),
        CELL_BYTES,
    )
    .expect("healthy history survives another viewer reconnect");

    healthy.close(None).await.expect("close healthy viewer");
    reconnected
        .close(None)
        .await
        .expect("close reconnected viewer");
    server_task.abort();
}

async fn next_binary(
    socket: &mut tokio_tungstenite::WebSocketStream<
        tokio_tungstenite::MaybeTlsStream<tokio::net::TcpStream>,
    >,
) -> Vec<u8> {
    loop {
        let message = socket
            .next()
            .await
            .expect("websocket message")
            .expect("websocket message ok");
        if let Message::Binary(bytes) = message {
            return bytes;
        }
    }
}

#[tokio::test]
async fn websocket_accepts_semantic_commands_and_streams_updated_frames() {
    let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
    let addr = listener.local_addr().expect("local addr");
    let app = server::app(ProceduralWizardFrameSource::default());
    let server_task = tokio::spawn(async move {
        axum::serve(listener, app).await.expect("test server");
    });

    let (mut socket, _) = connect_async(format!("ws://{addr}/ws/avatar/wizard?codec=adaptive"))
        .await
        .expect("connect websocket");
    let _init = socket.next().await.expect("init message").expect("init ok");
    let first = socket
        .next()
        .await
        .expect("first frame")
        .expect("first frame ok");
    let Message::Binary(first_bytes) = first else {
        panic!("expected first binary frame");
    };
    let (_first_index, first_decoded, _) =
        decode_frame(&first_bytes, None, CELL_BYTES).expect("decode first");

    socket
        .send(Message::Text(
            serde_json::json!({
                "type": "action",
                "payload": {"action": "magic_cast", "duration_ms": 500}
            })
            .to_string(),
        ))
        .await
        .expect("send action");

    let mut previous = Some(first_decoded);
    let mut saw_cyan_magic = false;
    for _ in 0..8 {
        let message = socket
            .next()
            .await
            .expect("command frame")
            .expect("command frame ok");
        let Message::Binary(bytes) = message else {
            continue;
        };
        let (_index, decoded, _) =
            decode_frame(&bytes, previous.as_deref(), CELL_BYTES).expect("decode command frame");
        saw_cyan_magic |= decoded
            .chunks_exact(CELL_BYTES)
            .any(|cell| cell[0] == b'*' && cell[1] == 0x26 && cell[2] == 0xd7 && cell[3] == 0xe8);
        previous = Some(decoded);
    }

    assert!(saw_cyan_magic);
    socket.close(None).await.expect("close websocket");
    server_task.abort();
}
