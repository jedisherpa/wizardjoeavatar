use std::path::PathBuf;
use wizard_avatar_pose_tool::{promote_phazer_sprite_archive, PhazerPromotionConfig};

fn main() {
    match parse_args().and_then(|config| {
        promote_phazer_sprite_archive(&config).map_err(|error| error.to_string())
    }) {
        Ok(receipt) => println!(
            "{}",
            serde_json::to_string_pretty(&receipt)
                .expect("Phazer promotion receipt must serialize")
        ),
        Err(error) => {
            eprintln!("wizard-avatar-phazer-promote: {error}");
            eprintln!();
            eprintln!("{}", usage());
            std::process::exit(1);
        }
    }
}

fn parse_args() -> Result<PhazerPromotionConfig, String> {
    let mut intake_root = None;
    let mut source_runtime_root = None;
    let mut output_runtime_root = None;
    let mut evidence_root = None;
    let mut arguments = std::env::args().skip(1);
    while let Some(argument) = arguments.next() {
        match argument.as_str() {
            "--intake-root" => {
                intake_root = Some(PathBuf::from(
                    arguments.next().ok_or("--intake-root requires a path")?,
                ));
            }
            "--source-runtime-root" => {
                source_runtime_root = Some(PathBuf::from(
                    arguments
                        .next()
                        .ok_or("--source-runtime-root requires a path")?,
                ));
            }
            "--output-runtime-root" => {
                output_runtime_root = Some(PathBuf::from(
                    arguments
                        .next()
                        .ok_or("--output-runtime-root requires a path")?,
                ));
            }
            "--evidence-root" => {
                evidence_root = Some(PathBuf::from(
                    arguments.next().ok_or("--evidence-root requires a path")?,
                ));
            }
            "--help" | "-h" => {
                println!("{}", usage());
                std::process::exit(0);
            }
            unknown => return Err(format!("unknown argument {unknown}")),
        }
    }
    Ok(PhazerPromotionConfig {
        intake_root: intake_root.ok_or("--intake-root is required")?,
        source_runtime_root: source_runtime_root.ok_or("--source-runtime-root is required")?,
        output_runtime_root: output_runtime_root.ok_or("--output-runtime-root is required")?,
        evidence_root: evidence_root.ok_or("--evidence-root is required")?,
    })
}

fn usage() -> &'static str {
    "Usage: wizard-avatar-phazer-promote \\\n+       --intake-root PATH --source-runtime-root PATH --output-runtime-root PATH \\\n+       --evidence-root PATH\n\
     \n\
     Revalidates all 48 visually reviewed Phazer frames, records their approval, and builds\n\
     a complete 308-pose runtime catalog without modifying the approved 260-pose source."
}
