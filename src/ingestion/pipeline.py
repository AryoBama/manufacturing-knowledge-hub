import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from schemas.common import CanonicalKnowledgeBase
from src.ingestion.adapter import adapt_file, IngestionBatch
from src.ingestion.validator import validate_batch, validate_knowledge_object
from src.ingestion.metadata import resolve_equipment


def run_ingestion_pipeline(
    input_dir: Path,
    output_base_dir: Optional[Path] = None,
    target_equipment_tag: Optional[str] = None
) -> Dict[str, Any]:
    """
    STEP 15: Ingestion & Normalization Pipeline.
    Orchestrates extraction inputs -> adapter -> 4 canonical objects -> validation -> normalized JSONs.
    Outputs to data/processed/<EQUIPMENT_TAG>/.
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    if output_base_dir is None:
        output_base_dir = BASE_DIR / "data" / "processed"

    print(f"\n================ STARTING INGESTION PIPELINE ================")
    print(f"Source Extracted Directory: {input_dir}")

    # Gather files to adapt (.xlsx, .json)
    # Exclude internal reports or previous processed files
    files_to_process: List[Path] = []
    for p in sorted(input_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in (".xlsx", ".json"):
            if "processed" in p.parts or "report" in p.name.lower() or "invalid" in p.name.lower():
                continue
            files_to_process.append(p)

    print(f"Discovered {len(files_to_process)} candidate extraction file(s).")

    aggregated_batch = IngestionBatch()
    detected_tags = set()

    for file_path in files_to_process:
        print(f"  --> Adapting: {file_path.relative_to(input_dir)}")
        batch = adapt_file(file_path)
        aggregated_batch.extend(batch)

        # Collect equipment tags
        for obj in (
            batch.document_chunks
            + batch.technical_records
            + batch.maintenance_records
            + batch.relationships
        ):
            if obj.equipment_tag:
                detected_tags.add(obj.equipment_tag)

    # Determine primary equipment tag
    primary_tag = target_equipment_tag
    if not primary_tag:
        if len(detected_tags) == 1:
            primary_tag = list(detected_tags)[0]
        elif len(detected_tags) > 1:
            # Fallback: check input directory name
            res = resolve_equipment(input_dir.name)
            if res.get("status") == "resolved":
                primary_tag = res["equipment_tag"]
            else:
                # Most frequent tag
                primary_tag = sorted(list(detected_tags))[0]
        else:
            primary_tag = "UNKNOWN_ASSET"

    dest_dir = output_base_dir / primary_tag
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"Target Processed Knowledge Hub Directory: {dest_dir}")

    # Deduplicate knowledge objects by primary ID to handle mixed formats (.xlsx and mirrored .json)
    dedup_chunks = list({c.chunk_id: c for c in aggregated_batch.document_chunks}.values())
    dedup_tech = list({t.record_id: t for t in aggregated_batch.technical_records}.values())
    dedup_mnt = list({m.event_id: m for m in aggregated_batch.maintenance_records}.values())
    dedup_rels = list({r.relationship_id: r for r in aggregated_batch.relationships}.values())

    # Filter maintenance records by primary_tag if primary_tag is resolved
    if primary_tag and primary_tag != "UNKNOWN_ASSET":
        base_prefix = primary_tag.split("-")[0] + "-" + primary_tag.split("-")[1][:4]
        tag_mnt = [
            m for m in dedup_mnt
            if m.equipment_tag and (
                m.equipment_tag.upper().startswith(primary_tag.upper()) or
                m.equipment_tag.upper().startswith(base_prefix)
            )
        ]
        if tag_mnt:
            dedup_mnt = tag_mnt

    # STEP 13: Validate all objects
    batch_dict = {
        "document_chunks": dedup_chunks,
        "technical_records": dedup_tech,
        "maintenance_records": dedup_mnt,
        "relationships": dedup_rels
    }
    val_report = validate_batch(batch_dict)

    # STEP 14: Quality Report Generation
    missing_rev_count = sum(
        1 for items in batch_dict.values()
        for item in items
        if getattr(item.source, "revision", None) is None
    )
    unmapped_params = sorted(list(set(
        tr.parameter for tr in dedup_tech if tr.canonical_field is None
    )))
    breakdown_count = sum(1 for m in dedup_mnt if m.failure_occurred)
    routine_count = sum(1 for m in dedup_mnt if not m.failure_occurred)

    quality_report = {
        "equipment": primary_tag,
        "source_directory": str(input_dir),
        "total_objects": val_report["total_objects"],
        "valid_objects": val_report["valid_objects"],
        "invalid_objects": val_report["invalid_objects"],
        "validation_passed": val_report["passed"],
        "by_type": {
            "document_chunks": len(dedup_chunks),
            "technical_records": len(dedup_tech),
            "maintenance_records": len(dedup_mnt),
            "relationships": len(dedup_rels)
        },
        "maintenance_semantics": {
            "total_events": len(dedup_mnt),
            "actual_failures_or_breakdowns": breakdown_count,
            "routine_preventive_or_tests": routine_count
        },
        "unmapped_technical_parameters": unmapped_params,
        "warnings": aggregated_batch.warnings + (
            [f"{missing_rev_count} object(s) lack formal revision in source (preserved as null without inferring)"]
            if missing_rev_count > 0 else []
        ),
        "validation_errors": val_report["errors"]
    }

    # STEP 15: Save normalized JSON files
    files_written = {}

    def _save_json(filename: str, obj_list: List[CanonicalKnowledgeBase]):
        out_path = dest_dir / filename
        data = [item.model_dump(mode="json") for item in obj_list]
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        files_written[filename] = len(obj_list)
        print(f"  [SAVED] {filename:<28} ({len(obj_list)} objects)")

    print(f"\nSerializing normalized knowledge objects to {dest_dir}...")
    _save_json("document_chunks.json", dedup_chunks)
    _save_json("technical_records.json", dedup_tech)
    _save_json("maintenance_records.json", dedup_mnt)
    _save_json("relationships.json", dedup_rels)

    report_path = dest_dir / "ingestion_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(quality_report, f, indent=2)
    print(f"  [SAVED] {'ingestion_report.json':<28} (Audit report)")

    print("\n================ INGESTION PIPELINE COMPLETED ================")
    print(f"Total Objects Ingested: {quality_report['total_objects']}")
    print(f"Validation Status: {'PASS' if quality_report['validation_passed'] else 'FAIL'}")
    print("===============================================================\n")

    return {
        "equipment": primary_tag,
        "dest_dir": dest_dir,
        "quality_report": quality_report,
        "files_written": files_written
    }


def run_all_ingestion(
    raw_base_dir: Optional[Path] = None,
    output_base_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Executes the ingestion pipeline across all equipment folders in data/raw.
    """
    if raw_base_dir is None:
        raw_base_dir = BASE_DIR / "data" / "raw"
    if output_base_dir is None:
        output_base_dir = BASE_DIR / "data" / "processed"

    results = {}
    for d in sorted(raw_base_dir.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            tag = d.name
            print(f"\n>>> Running Ingestion Pipeline for: {tag} ({d})")
            res = run_ingestion_pipeline(d, output_base_dir, target_equipment_tag=tag)
            results[tag] = res
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Ingestion Pipeline for Equipment Dataset(s)")
    parser.add_argument("--input-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=BASE_DIR / "data" / "processed")
    parser.add_argument("--equipment-tag", type=str, default=None)
    parser.add_argument("--all", action="store_true", help="Run ingestion for all equipment in data/raw")
    args = parser.parse_args()

    raw_ga = BASE_DIR / "data" / "raw" / "GA-1201A"
    legacy_ga = BASE_DIR / "GA-1201A HEXANE FEED PUMP"

    if args.all or (args.input_dir is None and (BASE_DIR / "data" / "raw").exists()):
        run_all_ingestion(BASE_DIR / "data" / "raw", args.output_dir)
    else:
        inp = args.input_dir or (raw_ga if raw_ga.exists() else legacy_ga)
        run_ingestion_pipeline(inp, args.output_dir, args.equipment_tag)
