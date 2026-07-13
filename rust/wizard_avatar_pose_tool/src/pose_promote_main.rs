use flate2::{Compression, GzBuilder};
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::io::Write;
use std::path::{Path, PathBuf};
use wizard_avatar_pose_tool::{
    compile_archive_bytes, compile_archive_with_admission_trace, load_archive, AdmissionRecord,
    CompilerConfig,
};

#[derive(Serialize)]
struct PromotionReport<'a> {
    schema_version: u32,
    compiler_id: &'a str,
    source_manifest_sha256: &'a str,
    archive_sha256: &'a str,
    gzip_sha256: String,
    catalog_records: usize,
    unique_geometries: usize,
    aliases: usize,
    wjfl_admissions: &'a [AdmissionRecord],
}

fn main() {
    if let Err(error) = run() {
        eprintln!("wizard-avatar-pose-promote: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let repo_root = std::env::args_os()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."));
    let repo_root = repo_root.canonicalize()?;
    let asset_path =
        repo_root.join("rust/wizard_avatar_engine/assets/wizard_pose_library.v4.json.gz");
    let report_path =
        repo_root.join("evidence/pose-library-expansion/rust-v4/admission-ledger.json");
    let queue_path = repo_root.join("docs/pose-library-expansion/feelings-queue.json");

    let source = load_archive(&repo_root)?;
    let (compiled, admissions) =
        compile_archive_with_admission_trace(&source, CompilerConfig::default())?;
    let json = compile_archive_bytes(&compiled)?;
    let mut encoder = GzBuilder::new()
        .mtime(0)
        .write(Vec::new(), Compression::best());
    encoder.write_all(&json)?;
    let gzip = encoder.finish()?;
    let gzip_sha256 = sha256_hex(&gzip);
    let report = PromotionReport {
        schema_version: compiled.schema_version,
        compiler_id: &compiled.compiler_id,
        source_manifest_sha256: &compiled.source_manifest_sha256,
        archive_sha256: &compiled.archive_sha256,
        gzip_sha256: gzip_sha256.clone(),
        catalog_records: compiled.catalog_count,
        unique_geometries: compiled.unique_geometry_count,
        aliases: compiled.alias_count,
        wjfl_admissions: &admissions[30..],
    };
    let mut report_bytes = serde_json::to_vec_pretty(&report)?;
    report_bytes.push(b'\n');
    let queue_bytes = integrated_queue(&queue_path, &admissions[30..])?;

    write_atomic(&asset_path, &gzip)?;
    write_atomic(&report_path, &report_bytes)?;
    write_atomic(&queue_path, &queue_bytes)?;
    println!(
        "promoted {} WJFL poses as {} geometries; archive {} gzip {}",
        report.wjfl_admissions.len(),
        report.unique_geometries,
        report.archive_sha256,
        report.gzip_sha256
    );
    Ok(())
}

fn integrated_queue(
    path: &Path,
    admissions: &[AdmissionRecord],
) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut queue: serde_json::Value = serde_json::from_slice(&std::fs::read(path)?)?;
    let semantic_by_candidate = admissions
        .iter()
        .map(|record| (record.candidate_id.as_str(), record.semantic_id.as_str()))
        .collect::<BTreeMap<_, _>>();
    let candidates = queue
        .get_mut("candidates")
        .and_then(serde_json::Value::as_array_mut)
        .ok_or("feelings queue has no candidates array")?;
    for candidate in candidates {
        let id = candidate
            .get("id")
            .and_then(serde_json::Value::as_str)
            .ok_or("feelings queue candidate has no id")?
            .to_string();
        let duplicate_of = candidate
            .get("exact_duplicate_of")
            .and_then(serde_json::Value::as_str)
            .map(str::to_string);
        let semantic_source = duplicate_of.as_deref().unwrap_or(&id);
        let semantic_id = semantic_by_candidate
            .get(semantic_source)
            .ok_or_else(|| format!("{id} has no admitted semantic source {semantic_source}"))?;
        candidate["semantic_id"] = serde_json::Value::String((*semantic_id).to_string());
        candidate["owner"] = serde_json::Value::String("rust/wizard_avatar_pose_tool".to_string());
        candidate["status"] = serde_json::Value::String(
            if duplicate_of.is_some() {
                "DUPLICATE_REFERENCE"
            } else {
                "INTEGRATED_RUST"
            }
            .to_string(),
        );
    }
    queue["queued_count"] = serde_json::Value::from(0);
    queue["integrated_unique_count"] = serde_json::Value::from(50);
    queue["duplicate_reference_count"] = serde_json::Value::from(10);
    queue["updated_at"] = serde_json::Value::String("2026-07-13".to_string());
    let mut bytes = serde_json::to_vec_pretty(&queue)?;
    bytes.push(b'\n');
    Ok(bytes)
}

fn write_atomic(path: &Path, bytes: &[u8]) -> std::io::Result<()> {
    let parent = path
        .parent()
        .ok_or_else(|| std::io::Error::other("output has no parent"))?;
    std::fs::create_dir_all(parent)?;
    let temporary = path.with_extension(format!("tmp-{}", std::process::id()));
    std::fs::write(&temporary, bytes)?;
    std::fs::rename(temporary, path)
}

fn sha256_hex(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}
