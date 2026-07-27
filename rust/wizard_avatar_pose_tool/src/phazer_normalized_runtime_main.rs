use std::path::PathBuf;
use wizard_avatar_pose_tool::{build_normalized_phazer_runtime, PhazerNormalizedRuntimeConfig};

fn main() {
    match parse_args().and_then(|config| {
        build_normalized_phazer_runtime(&config).map_err(|error| error.to_string())
    }) {
        Ok(receipt) => println!(
            "{}",
            serde_json::to_string_pretty(&receipt)
                .expect("normalized Phazer runtime receipt must serialize")
        ),
        Err(error) => {
            eprintln!("wizard-avatar-phazer-normalized-runtime: {error}");
            eprintln!();
            eprintln!("{}", usage());
            std::process::exit(1);
        }
    }
}

fn parse_args() -> Result<PhazerNormalizedRuntimeConfig, String> {
    let mut source_runtime_root = None;
    let mut normalized_phazer_root = None;
    let mut output_runtime_root = None;
    let mut arguments = std::env::args().skip(1);
    while let Some(argument) = arguments.next() {
        match argument.as_str() {
            "--source-runtime-root" => {
                source_runtime_root = Some(PathBuf::from(
                    arguments
                        .next()
                        .ok_or("--source-runtime-root requires a path")?,
                ));
            }
            "--normalized-phazer-root" => {
                normalized_phazer_root = Some(PathBuf::from(
                    arguments
                        .next()
                        .ok_or("--normalized-phazer-root requires a path")?,
                ));
            }
            "--output-runtime-root" => {
                output_runtime_root = Some(PathBuf::from(
                    arguments
                        .next()
                        .ok_or("--output-runtime-root requires a path")?,
                ));
            }
            "--help" | "-h" => {
                println!("{}", usage());
                std::process::exit(0);
            }
            unknown => return Err(format!("unknown argument {unknown}")),
        }
    }
    Ok(PhazerNormalizedRuntimeConfig {
        source_runtime_root: source_runtime_root.ok_or("--source-runtime-root is required")?,
        normalized_phazer_root: normalized_phazer_root
            .ok_or("--normalized-phazer-root is required")?,
        output_runtime_root: output_runtime_root.ok_or("--output-runtime-root is required")?,
    })
}

fn usage() -> &'static str {
    "Usage: wizard-avatar-phazer-normalized-runtime \\\n+       --source-runtime-root PATH \\\n+       --normalized-phazer-root PATH \\\n+       --output-runtime-root PATH\n\
     \n\
     Pads the approved 260-pose runtime to 1536 and installs the 48 normalized\n\
     Phazer PixelGraphs as a hash-bound v9 runtime."
}
