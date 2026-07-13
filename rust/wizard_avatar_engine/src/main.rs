use std::net::SocketAddr;
use wizard_avatar_engine::frame_source::ProceduralWizardFrameSource;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let addr: SocketAddr = std::env::var("WIZARD_AVATAR_ADDR")
        .unwrap_or_else(|_| "127.0.0.1:8787".to_string())
        .parse()?;
    println!("wizard avatar rust server listening on http://{addr}");
    wizard_avatar_engine::server::serve(addr, ProceduralWizardFrameSource::default()).await
}
