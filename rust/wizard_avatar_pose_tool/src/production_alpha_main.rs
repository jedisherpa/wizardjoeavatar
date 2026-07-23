use std::path::PathBuf;
use wizard_avatar_pose_tool::{
    compile_production_alpha, ProductionAlphaConfig, DEFAULT_BASE_ARCHIVE, DEFAULT_FLIGHT_ARCHIVE,
};

fn main() {
    match parse_args()
        .and_then(|config| compile_production_alpha(&config).map_err(|error| error.to_string()))
    {
        Ok(receipt) => {
            println!(
                "{}",
                serde_json::to_string_pretty(&receipt)
                    .expect("production alpha receipt must serialize")
            );
        }
        Err(error) => {
            eprintln!("wizard-avatar-production-alpha: {error}");
            eprintln!();
            eprintln!("{}", usage());
            std::process::exit(1);
        }
    }
}

fn parse_args() -> Result<ProductionAlphaConfig, String> {
    let mut base_archive = PathBuf::from(DEFAULT_BASE_ARCHIVE);
    let mut flight_archive = PathBuf::from(DEFAULT_FLIGHT_ARCHIVE);
    let mut output_root = None;
    let mut arguments = std::env::args().skip(1);
    while let Some(argument) = arguments.next() {
        match argument.as_str() {
            "--base-archive" => {
                base_archive =
                    PathBuf::from(arguments.next().ok_or("--base-archive requires a path")?);
            }
            "--flight-archive" => {
                flight_archive =
                    PathBuf::from(arguments.next().ok_or("--flight-archive requires a path")?);
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
    Ok(ProductionAlphaConfig {
        base_archive,
        flight_archive,
        output_root: output_root.ok_or("--output-root is required")?,
    })
}

fn usage() -> &'static str {
    "Usage: wizard-avatar-production-alpha --output-root PATH [--base-archive PATH] [--flight-archive PATH]\n\
     \n\
     The archive arguments default to the two pinned Wizard Joe v001 alpha packages. Both archives\n\
     are accepted only when their complete ZIP SHA-256 values match the compiler's fixed values."
}
