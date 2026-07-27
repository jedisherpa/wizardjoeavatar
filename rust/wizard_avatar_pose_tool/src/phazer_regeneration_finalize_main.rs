use std::path::PathBuf;
use wizard_avatar_pose_tool::{finalize_regenerated_phazer_corpus, PhazerRegenerationCorpusConfig};

fn main() {
    match parse_args().and_then(|config| {
        finalize_regenerated_phazer_corpus(&config).map_err(|error| error.to_string())
    }) {
        Ok(receipt) => println!(
            "{}",
            serde_json::to_string_pretty(&receipt)
                .expect("Phazer regeneration corpus receipt must serialize")
        ),
        Err(error) => {
            eprintln!("wizard-avatar-phazer-regeneration-finalize: {error}");
            eprintln!();
            eprintln!("{}", usage());
            std::process::exit(1);
        }
    }
}

fn parse_args() -> Result<PhazerRegenerationCorpusConfig, String> {
    let mut output_root = None;
    let mut approve_visual_review = false;
    let mut arguments = std::env::args().skip(1);
    while let Some(argument) = arguments.next() {
        match argument.as_str() {
            "--output-root" => {
                output_root = Some(PathBuf::from(
                    arguments.next().ok_or("--output-root requires a path")?,
                ));
            }
            "--approve-visual-review" => approve_visual_review = true,
            "--help" | "-h" => {
                println!("{}", usage());
                std::process::exit(0);
            }
            unknown => return Err(format!("unknown argument {unknown}")),
        }
    }
    Ok(PhazerRegenerationCorpusConfig {
        output_root: output_root.ok_or("--output-root is required")?,
        approve_visual_review,
    })
}

fn usage() -> &'static str {
    "Usage: wizard-avatar-phazer-regeneration-finalize --output-root PATH \\\n+       [--approve-visual-review]\n\
     \n\
     Revalidates all 48 native-detail Phazer poses, builds close-up and authored-mask\n\
     overlay contact sheets, and emits the hash-bound corpus manifest."
}
