use std::path::PathBuf;
use wizard_avatar_pose_tool::{
    build_source_ledger, default_ledger_path, write_source_ledger, SourceLedgerError,
};

fn main() {
    if let Err(error) = run() {
        eprintln!("wizard-avatar-source-ledger: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), SourceLedgerError> {
    let mut arguments = std::env::args_os().skip(1);
    let repo_root = arguments
        .next()
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."));
    let downloads_dir = arguments
        .next()
        .map(PathBuf::from)
        .unwrap_or_else(default_downloads_dir);
    let output_path = arguments
        .next()
        .map(PathBuf::from)
        .unwrap_or_else(|| default_ledger_path(&repo_root));
    if arguments.next().is_some() {
        return Err(SourceLedgerError::Inventory(
            "usage: wizard-avatar-source-ledger [repo-root] [downloads-dir] [output-json]"
                .to_string(),
        ));
    }

    let ledger = build_source_ledger(&downloads_dir)?;
    let output_path = write_source_ledger(&ledger, output_path)?;
    println!(
        "wrote {} source records from {} archives ({} pose candidates, {} style reference, {} unique hashes) to {}",
        ledger.record_count,
        ledger.archive_count,
        ledger.pose_candidate_count,
        ledger.style_reference_count,
        ledger.unique_content_count,
        output_path.display()
    );
    Ok(())
}

fn default_downloads_dir() -> PathBuf {
    std::env::var_os("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("/Users/paul"))
        .join("Downloads")
}
