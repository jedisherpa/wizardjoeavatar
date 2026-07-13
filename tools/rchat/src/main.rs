use std::env;
use std::path::PathBuf;
use std::process::ExitCode;

use wizardjoe_rchat_validator::{validate_gate_path, validate_registry_path, ValidationReport};

fn usage() -> ! {
    eprintln!(
        "usage:\n  wizardjoe-rchat-validator registry <registry.json>\n  wizardjoe-rchat-validator gate <gate.json> [--registry <registry.json>]"
    );
    std::process::exit(2);
}

fn print_report(subject: &str, report: ValidationReport) -> ExitCode {
    if report.is_valid() {
        println!("PASS {subject}");
        return ExitCode::SUCCESS;
    }

    for violation in report.violations {
        eprintln!(
            "{} {}: {}",
            violation.code, violation.path, violation.message
        );
    }
    ExitCode::FAILURE
}

fn main() -> ExitCode {
    let mut args = env::args().skip(1);
    match args.next().as_deref() {
        Some("registry") => {
            let path = PathBuf::from(args.next().unwrap_or_else(|| usage()));
            if args.next().is_some() {
                usage();
            }
            match validate_registry_path(&path) {
                Ok(report) => print_report(&format!("registry {}", path.display()), report),
                Err(error) => {
                    eprintln!("IO {}: {error}", path.display());
                    ExitCode::from(2)
                }
            }
        }
        Some("gate") => {
            let gate_path = PathBuf::from(args.next().unwrap_or_else(|| usage()));
            let mut registry_path = None;
            while let Some(argument) = args.next() {
                if argument != "--registry" || registry_path.is_some() {
                    usage();
                }
                registry_path = Some(PathBuf::from(args.next().unwrap_or_else(|| usage())));
            }

            match validate_gate_path(&gate_path, registry_path.as_deref()) {
                Ok(report) => print_report(&format!("gate {}", gate_path.display()), report),
                Err(error) => {
                    eprintln!("IO {}: {error}", gate_path.display());
                    ExitCode::from(2)
                }
            }
        }
        _ => usage(),
    }
}
