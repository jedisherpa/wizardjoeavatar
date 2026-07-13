use std::path::PathBuf;
use wizard_avatar_pose_tool::{
    compile_archive, load_archive, write_compiled_archive, CompilerConfig,
};

fn main() {
    if let Err(error) = run() {
        eprintln!("wizard-avatar-pose-tool: {error}");
        std::process::exit(1);
    }
}

fn run() -> wizard_avatar_pose_tool::Result<()> {
    let mut arguments = std::env::args_os().skip(1);
    let repo_root = arguments
        .next()
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."));
    let output = arguments
        .next()
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("target/pose-tool/compiled-30-poses.json"));
    if arguments.next().is_some() {
        return Err(wizard_avatar_pose_tool::PoseToolError::Archive(
            "usage: wizard-avatar-pose-tool [repo-root] [crate-target-output]".to_string(),
        ));
    }
    let source = load_archive(repo_root)?;
    let compiled = compile_archive(&source, CompilerConfig::default())?;
    let output = write_compiled_archive(&compiled, output)?;
    println!(
        "compiled {} catalog records into {} geometries and {} alias with {} colors to {}",
        compiled.catalog_count,
        compiled.unique_geometry_count,
        compiled.alias_count,
        compiled.palette_color_count,
        output.display()
    );
    Ok(())
}
