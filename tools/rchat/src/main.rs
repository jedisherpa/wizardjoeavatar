use std::env;
use std::fs;
use std::path::PathBuf;
use std::process::ExitCode;

use wizardjoe_rchat_validator::evidence::{
    validate_evidence_paths, write_evidence, EvidenceRun, EvidenceStatus,
};
use wizardjoe_rchat_validator::scope::{validate_scope_path, ScopeOptions, ScopeReport};
use wizardjoe_rchat_validator::{validate_gate_path, validate_registry_path, ValidationReport};

fn usage() -> ! {
    eprintln!(
        "usage:\n  wizardjoe-rchat-validator registry <registry.json>\n  wizardjoe-rchat-validator gate <gate.json> [--registry <registry.json>]\n  wizardjoe-rchat-validator scope <registry.json> <work-id> --base <ref> [--head <ref>] [--committed-only]\n  wizardjoe-rchat-validator evidence write <run.json> --ledger <frames.ndjson> --manifest <manifest.json>\n  wizardjoe-rchat-validator evidence validate <frames.ndjson> <manifest.json>"
    );
    std::process::exit(2);
}

fn print_scope_report(report: ScopeReport) -> ExitCode {
    if report.is_valid() {
        println!(
            "PASS scope {} on {} ({} changed paths)",
            report.work_id,
            report.branch,
            report.changed_paths.len()
        );
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

fn evidence_exit(status: EvidenceStatus, subject: &str) -> ExitCode {
    match status {
        EvidenceStatus::Pass => {
            println!("PASS {subject}");
            ExitCode::SUCCESS
        }
        EvidenceStatus::Fail => {
            eprintln!("FAIL {subject}");
            ExitCode::FAILURE
        }
        EvidenceStatus::Skip => {
            eprintln!("SKIP {subject}");
            ExitCode::from(77)
        }
    }
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
        Some("scope") => {
            let registry_path = PathBuf::from(args.next().unwrap_or_else(|| usage()));
            let work_id = args.next().unwrap_or_else(|| usage());
            let mut base_ref = None;
            let mut head_ref = "HEAD".to_owned();
            let mut include_worktree = true;
            while let Some(argument) = args.next() {
                match argument.as_str() {
                    "--base" if base_ref.is_none() => {
                        base_ref = Some(args.next().unwrap_or_else(|| usage()));
                    }
                    "--head" => head_ref = args.next().unwrap_or_else(|| usage()),
                    "--committed-only" => include_worktree = false,
                    _ => usage(),
                }
            }
            let base_ref = base_ref.unwrap_or_else(|| usage());
            match validate_scope_path(
                &registry_path,
                &work_id,
                ScopeOptions {
                    base_ref: &base_ref,
                    head_ref: &head_ref,
                    include_worktree,
                },
            ) {
                Ok(report) => print_scope_report(report),
                Err(error) => {
                    eprintln!("SCOPE {}: {error}", registry_path.display());
                    ExitCode::from(2)
                }
            }
        }
        Some("evidence") => match args.next().as_deref() {
            Some("write") => {
                let input_path = PathBuf::from(args.next().unwrap_or_else(|| usage()));
                let mut ledger_path = None;
                let mut manifest_path = None;
                while let Some(argument) = args.next() {
                    match argument.as_str() {
                        "--ledger" if ledger_path.is_none() => {
                            ledger_path =
                                Some(PathBuf::from(args.next().unwrap_or_else(|| usage())));
                        }
                        "--manifest" if manifest_path.is_none() => {
                            manifest_path =
                                Some(PathBuf::from(args.next().unwrap_or_else(|| usage())));
                        }
                        _ => usage(),
                    }
                }
                let ledger_path = ledger_path.unwrap_or_else(|| usage());
                let manifest_path = manifest_path.unwrap_or_else(|| usage());
                let result = fs::read(&input_path)
                    .map_err(|error| format!("failed to read {}: {error}", input_path.display()))
                    .and_then(|bytes| {
                        serde_json::from_slice::<EvidenceRun>(&bytes).map_err(|error| {
                            format!("invalid evidence input {}: {error}", input_path.display())
                        })
                    })
                    .and_then(|run| write_evidence(&run, &ledger_path, &manifest_path));
                match result {
                    Ok(manifest) => evidence_exit(manifest.status, "evidence write"),
                    Err(error) => {
                        eprintln!("EVIDENCE {}: {error}", input_path.display());
                        ExitCode::from(2)
                    }
                }
            }
            Some("validate") => {
                let ledger_path = PathBuf::from(args.next().unwrap_or_else(|| usage()));
                let manifest_path = PathBuf::from(args.next().unwrap_or_else(|| usage()));
                if args.next().is_some() {
                    usage();
                }
                match validate_evidence_paths(&ledger_path, &manifest_path) {
                    Ok(manifest) => evidence_exit(manifest.status, "evidence validate"),
                    Err(error) => {
                        eprintln!("EVIDENCE {}: {error}", manifest_path.display());
                        ExitCode::from(2)
                    }
                }
            }
            _ => usage(),
        },
        _ => usage(),
    }
}
