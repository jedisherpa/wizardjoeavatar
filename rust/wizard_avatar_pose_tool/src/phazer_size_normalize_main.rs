use std::path::PathBuf;
use wizard_avatar_pose_tool::{normalize_regenerated_phazer_corpus, PhazerSizeNormalizationConfig};

fn main() {
    match parse_args().and_then(|config| {
        normalize_regenerated_phazer_corpus(&config).map_err(|error| error.to_string())
    }) {
        Ok(receipt) => println!(
            "{}",
            serde_json::to_string_pretty(&receipt)
                .expect("Phazer size normalization receipt must serialize")
        ),
        Err(error) => {
            eprintln!("wizard-avatar-phazer-size-normalize: {error}");
            eprintln!();
            eprintln!("{}", usage());
            std::process::exit(1);
        }
    }
}

fn parse_args() -> Result<PhazerSizeNormalizationConfig, String> {
    let mut source_root = None;
    let mut runtime_manifest = None;
    let mut output_root = None;
    let mut arguments = std::env::args().skip(1);
    while let Some(argument) = arguments.next() {
        match argument.as_str() {
            "--source-root" => {
                source_root = Some(PathBuf::from(
                    arguments.next().ok_or("--source-root requires a path")?,
                ));
            }
            "--runtime-manifest" => {
                runtime_manifest = Some(PathBuf::from(
                    arguments
                        .next()
                        .ok_or("--runtime-manifest requires a path")?,
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
    Ok(PhazerSizeNormalizationConfig {
        source_root: source_root.ok_or("--source-root is required")?,
        runtime_manifest: runtime_manifest.ok_or("--runtime-manifest is required")?,
        output_root: output_root.ok_or("--output-root is required")?,
    })
}

fn usage() -> &'static str {
    "Usage: wizard-avatar-phazer-size-normalize \\\n+       --source-root PATH \\\n+       --runtime-manifest PATH \\\n+       --output-root PATH\n\
     \n\
     Measures Joe's central hat brim, normalizes scale by camera facing around the\n\
     runtime body anchor, applies the shared Phazer catalog-scale correction,\n\
     recompiles exact PixelGraphs, and emits fixed-canvas review sheets."
}
