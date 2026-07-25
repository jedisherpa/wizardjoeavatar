use std::path::PathBuf;
use wizard_avatar_pose_tool::{
    compile_phazer_sprite_archive, PhazerIntakeConfig, DEFAULT_PHAZER_ARCHIVE,
};

fn main() {
    match parse_args().and_then(|config| {
        compile_phazer_sprite_archive(&config).map_err(|error| error.to_string())
    }) {
        Ok(receipt) => println!(
            "{}",
            serde_json::to_string_pretty(&receipt).expect("Phazer receipt must serialize")
        ),
        Err(error) => {
            eprintln!("wizard-avatar-phazer-intake: {error}");
            eprintln!();
            eprintln!("{}", usage());
            std::process::exit(1);
        }
    }
}

fn parse_args() -> Result<PhazerIntakeConfig, String> {
    let mut archive = PathBuf::from(DEFAULT_PHAZER_ARCHIVE);
    let mut output_root = None;
    let mut arguments = std::env::args().skip(1);
    while let Some(argument) = arguments.next() {
        match argument.as_str() {
            "--archive" => {
                archive = PathBuf::from(arguments.next().ok_or("--archive requires a path")?);
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
    Ok(PhazerIntakeConfig {
        archive,
        output_root: output_root.ok_or("--output-root is required")?,
    })
}

fn usage() -> &'static str {
    "Usage: wizard-avatar-phazer-intake --output-root PATH [--archive PATH]\n\
     \n\
     Decodes the pinned WizardJoePhazerSprites archive, isolates each of its 48 authored\n\
     sprite cells, and emits native PixelGraphs plus source-overlay verification evidence."
}
