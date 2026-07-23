use std::env;
use std::path::PathBuf;
use wizard_avatar_pose_tool::promote_verified_pose_graphs;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let repo_root = env::args_os()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or(env::current_dir()?);
    let receipt = promote_verified_pose_graphs(&repo_root)?;
    println!("{}", serde_json::to_string_pretty(&receipt)?);
    Ok(())
}
