use std::path::PathBuf;
use wizard_avatar_pose_tool::promote_verified_newsroom;

fn main() {
    if let Err(error) = run() {
        eprintln!("wizard-avatar-newsroom-promote: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let repo_root = std::env::args_os()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or(std::env::current_dir()?);
    let manifest = promote_verified_newsroom(repo_root)?;
    println!(
        "promoted {} visually approved sources as {} exact native pixel graphs ({} occupied pixels)",
        manifest.source_count, manifest.target_count, manifest.foreground_pixel_count
    );
    Ok(())
}
