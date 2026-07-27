use std::path::PathBuf;
use wizard_avatar_pose_tool::{admit_regenerated_phazer_pose, PhazerRegenerationConfig};

fn main() {
    match parse_args().and_then(|config| {
        admit_regenerated_phazer_pose(&config).map_err(|error| error.to_string())
    }) {
        Ok(receipt) => println!(
            "{}",
            serde_json::to_string_pretty(&receipt)
                .expect("Phazer regeneration receipt must serialize")
        ),
        Err(error) => {
            eprintln!("wizard-avatar-phazer-regenerate-one: {error}");
            eprintln!();
            eprintln!("{}", usage());
            std::process::exit(1);
        }
    }
}

fn parse_args() -> Result<PhazerRegenerationConfig, String> {
    let mut pose_id = None;
    let mut authored_source = None;
    let mut generated_candidate = None;
    let mut output_root = None;
    let mut arguments = std::env::args().skip(1);
    while let Some(argument) = arguments.next() {
        match argument.as_str() {
            "--pose-id" => pose_id = Some(arguments.next().ok_or("--pose-id requires a value")?),
            "--authored-source" => {
                authored_source = Some(PathBuf::from(
                    arguments
                        .next()
                        .ok_or("--authored-source requires a path")?,
                ));
            }
            "--generated-candidate" => {
                generated_candidate = Some(PathBuf::from(
                    arguments
                        .next()
                        .ok_or("--generated-candidate requires a path")?,
                ));
            }
            "--output-root" => {
                output_root = Some(PathBuf::from(
                    arguments.next().ok_or("--output-root requires a path")?,
                ));
            }
            "--help" | "-h" => {
                println!("{}", usage());
                std::process::exit(0);
            }
            unknown => return Err(format!("unknown argument {unknown}")),
        }
    }
    Ok(PhazerRegenerationConfig {
        pose_id: pose_id.ok_or("--pose-id is required")?,
        authored_source: authored_source.ok_or("--authored-source is required")?,
        generated_candidate: generated_candidate.ok_or("--generated-candidate is required")?,
        output_root: output_root.ok_or("--output-root is required")?,
    })
}

fn usage() -> &'static str {
    "Usage: wizard-avatar-phazer-regenerate-one \\\n+       --pose-id WJPS-0001 \\\n+       --authored-source PATH \\\n+       --generated-candidate PATH \\\n+       --output-root PATH\n\
     \n\
     Removes the generated chroma matte, aligns the high-detail candidate to the authored\n\
     pose, locks the original silhouette and anchors, and emits a lossless PixelGraph plus\n\
     transparent-overlay verification evidence."
}
