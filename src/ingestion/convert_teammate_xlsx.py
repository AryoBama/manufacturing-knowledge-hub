import argparse
import datetime
import json
import shutil
import sys
from pathlib import Path
from typing import List, Dict, Any

import openpyxl

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from schemas.common import DocumentSource, DocumentStatus, DocumentType
from schemas.document import DocumentChunk
from schemas.maintenance import MaintenanceRecord
from src.ingestion.maintenance_loader import parse_maintenance_excel


def convert_datasheet(file_path: Path) -> DocumentChunk:
    wb = openpyxl.load_workbook(file_path, data_only=True)
    meta: Dict[str, str] = {}
    if "Metadata" in wb.sheetnames:
        ws = wb["Metadata"]
        for r in range(1, ws.max_row + 1):
            k = ws.cell(r, 1).value
            v = ws.cell(r, 2).value
            if k and v:
                meta[str(k).strip()] = str(v).strip()

    doc_id = meta.get("doc_no", "TJC-LLD-DS-GA-1201A")
    tag = meta.get("equipment_tag", "GA-1201A")
    rev = meta.get("revision", "Rev 3")
    status_str = meta.get("revision_status", "Issued for Operation")
    source_file = meta.get("source_file", "Equipment Datasheet - GA-1201A.pdf")

    mech_lines = []
    if "Mechanical Data" in wb.sheetnames:
        ws = wb["Mechanical Data"]
        for r in range(2, ws.max_row + 1):
            param = ws.cell(r, 2).value
            val = ws.cell(r, 3).value
            unit = ws.cell(r, 4).value
            if param and val and str(param).lower() != "parameter":
                unit_str = f" {unit}" if unit and str(unit).strip() not in ("-", "—", "") else ""
                mech_lines.append(f"{param}: {val}{unit_str}")

    motor_lines = []
    if "Motor Data" in wb.sheetnames:
        ws = wb["Motor Data"]
        for r in range(2, ws.max_row + 1):
            param = ws.cell(r, 2).value
            val = ws.cell(r, 3).value
            unit = ws.cell(r, 4).value
            if param and val and str(param).lower() != "parameter":
                unit_str = f" {unit}" if unit and str(unit).strip() not in ("-", "—", "") else ""
                motor_lines.append(f"{param}: {val}{unit_str}")

    content_parts = [
        f"EQUIPMENT DATASHEET: {tag} ({meta.get('equipment_name', 'HEXANE FEED PUMP')}).",
        f"Document No: {doc_id}, Revision: {rev}, Status: {status_str}.",
        f"Equipment Type: {meta.get('equipment_type', 'Centrifugal Pump (API 610 OH2)')}.",
        f"Plant Unit: {meta.get('plant_unit', 'Linear Low Density Polyethylene (LLDPE) Unit')}, Area: {meta.get('area', '1200 – Feed Preparation & Purification')}.",
        f"Functional Location: {meta.get('functional_location', 'TJC-LLD-1200-01')}, Criticality: {meta.get('criticality', 'High Critical')}.",
        f"Service: {meta.get('service', 'Hexane feed transfer to 1st Polymerization Reactor DC-4501')}.",
        "MECHANICAL SPECIFICATIONS:",
        "; ".join(mech_lines),
        "MOTOR & ELECTRICAL SPECIFICATIONS:",
        "; ".join(motor_lines),
        f"CROSS REFERENCES: P&ID: {meta.get('pid_reference', 'TJC-LLD-PID-1201')}, Interlock: {meta.get('interlock_reference', 'SEQ-1201')}."
    ]
    content = "\n".join(content_parts)

    return DocumentChunk(
        chunk_id=f"{doc_id}-P01-C01",
        document_id=doc_id,
        document_type=DocumentType.DATASHEET,
        title=f"Equipment Datasheet - {meta.get('equipment_name', 'Hexane Feed Pump')} ({tag})",
        equipment_tag=tag,
        content=content,
        source=DocumentSource(
            file_name=source_file,
            page=1,
            revision=rev,
            status=DocumentStatus.ISSUED_FOR_OPERATION
        )
    )


def convert_interlock(file_path: Path) -> DocumentChunk:
    wb = openpyxl.load_workbook(file_path, data_only=True)
    meta: Dict[str, str] = {}
    if "Metadata" in wb.sheetnames:
        ws = wb["Metadata"]
        for r in range(1, ws.max_row + 1):
            k = ws.cell(r, 1).value
            v = ws.cell(r, 2).value
            if k and v:
                meta[str(k).strip()] = str(v).strip()

    doc_id = meta.get("doc_no", "TJC-LLD-IL-GA-1201A")
    tag = meta.get("equipment_tag", "GA-1201A")
    rev = meta.get("revision", "Rev 3")
    logic_no = meta.get("logic_no", "SEQ-1201")
    source_file = meta.get("source_file", "Interlock Logic Diagram - GA-1201A.pdf")

    trips = []
    if "Cause Effect" in wb.sheetnames:
        ws = wb["Cause Effect"]
        for r in range(3, ws.max_row + 1):
            trip_id = ws.cell(r, 2).value
            desc = ws.cell(r, 3).value
            tag_inst = ws.cell(r, 4).value
            sp = ws.cell(r, 5).value
            voting = ws.cell(r, 6).value
            if trip_id and str(trip_id).startswith("T") and len(str(trip_id)) <= 3:
                effs = []
                if ws.cell(r, 7).value in ("X", "x"):
                    effs.append("Trip Motor (EFF-1)")
                if ws.cell(r, 8).value in ("X", "x"):
                    effs.append("Close Discharge XV-1201 (EFF-2)")
                if ws.cell(r, 9).value in ("X", "x"):
                    effs.append("Open Min-Flow FV-1201 (EFF-3)")
                if ws.cell(r, 10).value in ("X", "x"):
                    effs.append("DCS Alarm (EFF-4)")
                if ws.cell(r, 11).value in ("X", "x"):
                    effs.append("Start Standby Pump GA-1201B (EFF-5)")
                actions = ", ".join(effs)
                trips.append(f"- {trip_id}: {desc} ({tag_inst} {sp}, {voting}) -> Actions: {actions}")

    permissives = []
    if "Start Permissive" in wb.sheetnames:
        ws = wb["Start Permissive"]
        for r in range(3, ws.max_row + 1):
            p_id = ws.cell(r, 2).value
            desc = ws.cell(r, 3).value
            sig = ws.cell(r, 4).value
            gate = ws.cell(r, 5).value
            if p_id and desc:
                permissives.append(f"- {p_id}: {desc} ({sig}, Gate Logic: {gate})")

    content_parts = [
        f"INTERLOCK LOGIC & CAUSE EFFECT MATRIX: {logic_no} ({meta.get('logic_description', 'Hexane Feed Pump Shutdown Logic')}).",
        f"Document No: {doc_id}, Revision: {rev}, SIL Level: {meta.get('sil_level', 'SIL 1')}.",
        f"Equipment: {tag}, Functional Location: {meta.get('functional_location', 'TJC-LLD-1200-01')}.",
        "CAUSE & EFFECT MATRIX (TRIPS):",
        "\n".join(trips),
        "START PERMISSIVES (AND-gate conditions to start pump):",
        "\n".join(permissives),
        f"CROSS REFERENCES: P&ID: {meta.get('pid_reference', 'TJC-LLD-PID-1201')}, Datasheet: {meta.get('datasheet_reference', 'TJC-LLD-DS-GA-1201A')}."
    ]
    content = "\n".join(content_parts)

    return DocumentChunk(
        chunk_id=f"{doc_id}-P01-C01",
        document_id=doc_id,
        document_type=DocumentType.INTERLOCK,
        title=f"Interlock Logic & Cause Effect Matrix - {tag} ({logic_no})",
        equipment_tag=tag,
        content=content,
        source=DocumentSource(
            file_name=source_file,
            page=1,
            revision=rev,
            status=DocumentStatus.ISSUED_FOR_OPERATION
        )
    )


def convert_pid(file_path: Path) -> DocumentChunk:
    wb = openpyxl.load_workbook(file_path, data_only=True)
    meta: Dict[str, str] = {}
    if "Metadata" in wb.sheetnames:
        ws = wb["Metadata"]
        for r in range(1, ws.max_row + 1):
            k = ws.cell(r, 1).value
            v = ws.cell(r, 2).value
            if k and v:
                meta[str(k).strip()] = str(v).strip()

    doc_id = "TJC-LLD-PID-1201"
    tag = meta.get("equipment_tag", "GA-1201A")
    rev = "Rev 0"
    source_file = meta.get("source_file", "PID_Set_01.png")

    inst_lines = []
    if "Instrument List" in wb.sheetnames:
        ws = wb["Instrument List"]
        for r in range(3, ws.max_row + 1):
            itag = ws.cell(r, 1).value
            desc = ws.cell(r, 2).value
            itype = ws.cell(r, 3).value
            sp = ws.cell(r, 4).value
            unit = ws.cell(r, 5).value
            fn = ws.cell(r, 6).value
            rel_il = ws.cell(r, 7).value
            loc = ws.cell(r, 8).value
            if itag:
                sp_str = f" [Setpoint: {sp} {unit}]" if sp and str(sp).strip() not in ("-", "—", "") else ""
                inst_lines.append(f"- {itag}: {desc} ({itype}){sp_str}. Function: {fn}. Location: {loc}. Interlock: {rel_il}")

    content_parts = [
        f"PIPING & INSTRUMENTATION DIAGRAM (P&ID) REGISTER: {tag} ({meta.get('equipment_name', 'HEXANE FEED PUMP')}).",
        f"Document No: {doc_id}, Title: {meta.get('title', 'Hexane Feed System – GA-1201A')}.",
        f"Area: {meta.get('area', '1200 – Hexane Feed System')}, Functional Location: {meta.get('functional_location', 'TJC-LLD-1200-01')}.",
        "INSTRUMENT & PROCESS CONTROL LOOPS:",
        "\n".join(inst_lines),
        f"CROSS REFERENCES: Datasheet: {meta.get('datasheet_reference', 'TJC-LLD-DS-GA-1201A')}, Interlock: {meta.get('interlock_reference', 'SEQ-1201')}."
    ]
    content = "\n".join(content_parts)

    return DocumentChunk(
        chunk_id=f"{doc_id}-P01-C01",
        document_id=doc_id,
        document_type=DocumentType.PID,
        title=f"Piping & Instrumentation Diagram Register - {tag}",
        equipment_tag=tag,
        content=content,
        source=DocumentSource(
            file_name=source_file,
            page=1,
            revision=rev,
            status=DocumentStatus.ISSUED_FOR_OPERATION
        )
    )


def convert_plot_plan(file_path: Path) -> DocumentChunk:
    wb = openpyxl.load_workbook(file_path, data_only=True)
    meta: Dict[str, str] = {}
    if "Metadata" in wb.sheetnames:
        ws = wb["Metadata"]
        for r in range(1, ws.max_row + 1):
            k = ws.cell(r, 1).value
            v = ws.cell(r, 2).value
            if k and v:
                meta[str(k).strip()] = str(v).strip()

    doc_id = meta.get("doc_no", "TJC-LLD-PP-GA-1201A")
    tag = meta.get("equipment_tag", "GA-1201A")
    rev = meta.get("revision", "Rev 0")
    source_file = meta.get("source_file", "Plot Plan - GA-1201A.pdf")

    loc_params = []
    nearby = []
    if "Location Data" in wb.sheetnames:
        ws = wb["Location Data"]
        for r in range(3, 15):
            param = ws.cell(r, 1).value
            val = ws.cell(r, 2).value
            unit = ws.cell(r, 3).value
            if param and val:
                unit_str = f" {unit}" if unit and str(unit).strip() not in ("-", "—", "") else ""
                loc_params.append(f"{param}: {val}{unit_str}")
        for r in range(17, ws.max_row + 1):
            etag = ws.cell(r, 1).value
            ename = ws.cell(r, 2).value
            area_code = ws.cell(r, 3).value
            area_name = ws.cell(r, 4).value
            el = ws.cell(r, 5).value
            if etag:
                name_str = f" ({ename})" if ename and str(ename).strip() not in ("-", "—", "") else ""
                nearby.append(f"- {etag}{name_str}: Area {area_code} ({area_name}), Elevation {el}")

    content_parts = [
        f"PLOT PLAN & EQUIPMENT LOCATION DATA: {tag} ({meta.get('equipment_name', 'HEXANE FEED PUMP')}).",
        f"Document No: {doc_id}, Revision: {rev}, Status: {meta.get('revision_status', 'Issued for Construction')}.",
        f"Area: {meta.get('area', '1200 – Feed Preparation & Purification')}, Functional Location: {meta.get('functional_location', 'TJC-LLD-1200-01')}.",
        "LOCATION SPECIFICATIONS & COORDINATES:",
        "; ".join(loc_params),
        "NEARBY PLANT EQUIPMENT & ELEVATIONS:",
        "\n".join(nearby)
    ]
    content = "\n".join(content_parts)

    return DocumentChunk(
        chunk_id=f"{doc_id}-P01-C01",
        document_id=doc_id,
        document_type=DocumentType.PLOT_PLAN,
        title=f"Plot Plan & Location Data - {tag}",
        equipment_tag=tag,
        content=content,
        source=DocumentSource(
            file_name=source_file,
            page=1,
            revision=rev,
            status=DocumentStatus.ISSUED_FOR_CONSTRUCTION
        )
    )


def convert_opl(file_path: Path) -> List[DocumentChunk]:
    wb = openpyxl.load_workbook(file_path, data_only=True)
    chunks = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        meta: Dict[str, str] = {}
        for r in range(1, 20):
            k = ws.cell(r, 1).value
            v = ws.cell(r, 2).value
            if k and v:
                meta[str(k).strip()] = str(v).strip()

        doc_id = meta.get("opl_no")
        if not doc_id:
            continue
        title = meta.get("opl_title", sheet_name)
        tag = meta.get("equipment_tag", "GA-1201A")
        disc = meta.get("discipline", "Mechanical")
        source_file = meta.get("source_file", f"{doc_id}.pdf")

        purpose = ""
        precautions = []
        tools = []
        steps = []
        problems = []
        learnings = []

        current_problem = {}

        for r in range(21, ws.max_row + 1):
            sec = ws.cell(r, 1).value
            sub = ws.cell(r, 2).value
            val = ws.cell(r, 3).value
            sec_str = str(sec).strip() if sec else ""
            sub_str = str(sub).strip() if sub else ""
            val_str = str(val).strip() if val else ""

            if "Purpose" in sec_str:
                purpose = val_str or sub_str
            elif "Safety" in sec_str:
                if val_str:
                    precautions.append(f"- {sub_str}: {val_str}")
            elif "Tools" in sec_str:
                if val_str:
                    tools.append(f"- {sub_str}: {val_str}")
            elif "Procedure" in sec_str:
                if val_str:
                    steps.append(f"- {sub_str}: {val_str}")
            elif "Common Problems" in sec_str:
                if "Symptom" in sub_str:
                    if current_problem:
                        problems.append(current_problem)
                    current_problem = {"symptom": val_str, "cause": "", "action": ""}
                elif "Cause" in sub_str:
                    current_problem["cause"] = val_str
                elif "Action" in sub_str:
                    current_problem["action"] = val_str
            elif "Learning" in sec_str:
                if val_str:
                    learnings.append(f"- {sub_str}: {val_str}")

        if current_problem:
            problems.append(current_problem)

        prob_lines = [
            f"- Symptom: {p.get('symptom')} | Likely Cause: {p.get('cause')} | Action: {p.get('action')}"
            for p in problems if p.get("symptom")
        ]

        content_parts = [
            f"ONE POINT LESSON (OPL): {doc_id} - {title}.",
            f"Equipment: {tag} ({meta.get('equipment_name', 'HEXANE FEED PUMP')}), Discipline: {disc}, Area: {meta.get('area_unit', '1200')}.",
            f"Related Interlock: {meta.get('related_interlock', 'SEQ-1201')}, P&ID: {meta.get('pid_reference', 'TJC-LLD-PID-1201')}.",
            f"PURPOSE & OBJECTIVE:\n{purpose}",
            "SAFETY PRECAUTIONS:\n" + "\n".join(precautions),
            "TOOLS & MATERIALS:\n" + "\n".join(tools),
            "STEP-BY-STEP PROCEDURE:\n" + "\n".join(steps),
            "COMMON PROBLEMS & TROUBLESHOOTING:\n" + "\n".join(prob_lines),
            "KEY LEARNING POINTS:\n" + "\n".join(learnings)
        ]
        content = "\n\n".join(content_parts)

        chunk = DocumentChunk(
            chunk_id=f"{doc_id}-P01-C01",
            document_id=doc_id,
            document_type=DocumentType.OPL,
            title=f"One Point Lesson - {title} ({doc_id})",
            equipment_tag=tag,
            content=content,
            source=DocumentSource(
                file_name=source_file,
                page=1,
                revision="Rev 0",
                status=DocumentStatus.ISSUED_FOR_OPERATION
            )
        )
        chunks.append(chunk)

    return chunks


def convert_all(
    input_dir: Path,
    output_dir: Path,
    copy_to_input_folder: bool = True
) -> Dict[str, Any]:
    print(f"Converting Excel files from: {input_dir}")
    print(f"Target extracted directory: {output_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    opl_dir = output_dir / "opl"
    opl_dir.mkdir(parents=True, exist_ok=True)

    results_summary = {}

    # 1. Datasheet
    ds_file = input_dir / "Equipment Datasheet - GA-1201A.xlsx"
    if ds_file.exists():
        print(f"  [+] Parsing Datasheet: {ds_file.name}")
        ds_chunk = convert_datasheet(ds_file)
        out_ds = output_dir / "datasheet.json"
        with open(out_ds, "w", encoding="utf-8") as f:
            json.dump(ds_chunk.model_dump(mode="json"), f, indent=2)
        results_summary["datasheet"] = str(out_ds)

    # 2. Interlock
    il_file = input_dir / "Interlock GA-1201A.xlsx"
    if il_file.exists():
        print(f"  [+] Parsing Interlock: {il_file.name}")
        il_chunk = convert_interlock(il_file)
        out_il = output_dir / "interlock.json"
        with open(out_il, "w", encoding="utf-8") as f:
            json.dump(il_chunk.model_dump(mode="json"), f, indent=2)
        results_summary["interlock"] = str(out_il)

    # 3. PID Register
    pid_file = input_dir / "PID Register GA-1201A.xlsx"
    if pid_file.exists():
        print(f"  [+] Parsing PID Register: {pid_file.name}")
        pid_chunk = convert_pid(pid_file)
        out_pid = output_dir / "pid.json"
        with open(out_pid, "w", encoding="utf-8") as f:
            json.dump(pid_chunk.model_dump(mode="json"), f, indent=2)
        results_summary["pid"] = str(out_pid)

    # 4. Plot Plan
    pp_file = input_dir / "Plot Plan GA-1201A.xlsx"
    if pp_file.exists():
        print(f"  [+] Parsing Plot Plan: {pp_file.name}")
        pp_chunk = convert_plot_plan(pp_file)
        out_pp = output_dir / "plot_plan.json"
        with open(out_pp, "w", encoding="utf-8") as f:
            json.dump(pp_chunk.model_dump(mode="json"), f, indent=2)
        results_summary["plot_plan"] = str(out_pp)

    # 5. OPL (7 sheets)
    opl_file = input_dir / "OPL GA-1201A-HEXANE_FEED_PUMP.xlsx"
    if opl_file.exists():
        print(f"  [+] Parsing OPL Sheets: {opl_file.name}")
        opl_chunks = convert_opl(opl_file)
        saved_opls = []
        for c in opl_chunks:
            chunk_file = opl_dir / f"{c.document_id}.json"
            with open(chunk_file, "w", encoding="utf-8") as f:
                json.dump(c.model_dump(mode="json"), f, indent=2)
            saved_opls.append(str(chunk_file))
        results_summary["opl_chunks"] = len(opl_chunks)

    # 6. Maintenance History
    mnt_file = input_dir / "Maintenance History GA-1201A.xlsx"
    if mnt_file.exists():
        print(f"  [+] Parsing Maintenance History: {mnt_file.name}")
        records = parse_maintenance_excel(mnt_file)
        out_mnt = output_dir / "maintenance_history.json"
        with open(out_mnt, "w", encoding="utf-8") as f:
            json.dump([r.model_dump(mode="json") for r in records], f, indent=2)
        results_summary["maintenance_records"] = len(records)

    # Optionally copy to input folder under json/
    if copy_to_input_folder:
        input_json_dir = input_dir / "json"
        print(f"  [+] Mirroring JSON copies to: {input_json_dir}")
        input_json_dir.mkdir(parents=True, exist_ok=True)
        for item in output_dir.iterdir():
            dest = input_json_dir / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

    print("\nConversion completed successfully!")
    return results_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert GA-1201A teammate Excel files to AI contract JSON")
    parser.add_argument("--input-dir", type=Path, default=BASE_DIR / "GA-1201A HEXANE FEED PUMP")
    parser.add_argument("--output-dir", type=Path, default=BASE_DIR / "data" / "extracted" / "Set_01_GA-1201A")
    args = parser.parse_args()

    convert_all(args.input_dir, args.output_dir)
