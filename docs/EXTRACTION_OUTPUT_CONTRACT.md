# Extraction Output Contract (Version 1.0)

Dokumen ini mendefinisikan **Data Contract resmi** antara modul **Extractor** (dikerjakan oleh rekan tim data extraction) dan modul **Ingestion / Normalization Engine** (dikerjakan oleh tim AI Ingestion) pada sistem *Manufacturing Knowledge Hub* (Chandra Asri CALIBER 2026).

---

## 1. Prinsip Dasar & Filosofi Integrasi

1. **Prinsip Extractor**:
   * Extractor berfokus merekam data persis sebagaimana ditemukan pada dokumen sumber asli (PDF, P&ID drawing, scan OPL, SAP PM export).
   * Extractor **tidak dibebani** keharusan menyatukan schema global atau memformat istilah teknik menjadi satu canonical taxonomy.
   * Extractor mempertahankan label asli dari kolom/tabel sumber (*e.g.* `Rated Flow`, `Nominal Capacity`, `Q_rated`).

2. **Prinsip Ingestion**:
   * Ingestion bertugas membaca struktur extractor, memvalidasi metadata sumber, dan menyatukannya menjadi **4 Canonical Knowledge Objects**:
     * `DocumentChunk`
     * `TechnicalRecord`
     * `MaintenanceRecord`
     * `RelationshipRecord`
   * Seluruh knowledge object hasil ingestion wajib memiliki **Common Metadata** untuk memastikan keterlacakan (*traceability*) 100% ke nomor dokumen fisik dan revisinya.

---

## 2. Format Masukan (*Input Format*)

Extractor dapat menyerahkan data dalam dua mode yang didukung sepenuhnya oleh Ingestion:
* **Mode A (Extraction JSON)**: Satu berkas JSON per dokumen/kategori, atau JSON manifest per unit peralatan.
* **Mode B (Multi-sheet Excel Workbook)**: Berkas `.xlsx` terstruktur yang memuat sheet `Metadata` dan sheet data tabular (seperti yang telah diuji pada unit `GA-1201A`).

Struktur direktori penyerahan standar:
```text
data/extracted/
└── <EQUIPMENT_TAG>/              # Contoh: GA-1201A, YD-2301, KC-4501
    ├── extraction_manifest.json   # (Opsional) Ringkasan berkas yang diekstrak
    ├── datasheet.json / .xlsx
    ├── interlock.json / .xlsx
    ├── pid.json / .xlsx
    ├── plot_plan.json / .xlsx
    ├── opl/                       # Berkas atau lembar OPL (OPL-01 .. OPL-07)
    └── maintenance_history.json / .xlsx
```

---

## 3. Identifikasi Peralatan (*Equipment Identification*)

Setiap payload ekstraksi wajib memuat referensi tag peralatan:
* **Field Wajib**: `equipment_tag` (atau `tag_no`, `asset_tag`, `tag`)
* **Format Nilai Canonical**: Standar penamaan Chandra Asri Petrochemical:
  * Pompa: `GA-1201A`, `GA-1201B`
  * Dryer: `YD-2301`
  * Reaktor / Tangki: `DC-3401A`, `DC-4501`
  * Kompresor: `KC-4501`
  * Heat Exchanger: `EA-5601`
  * Kolom Separasi: `LV-6701`, `FA-8901`
  * Cooling Tower: `CT-7801`
* **Handling Variasi**:
  * Ingestion dilengkapi modul `resolve_equipment()` yang secara otomatis memetakan alias (misal: `ga1201a`, `Hexane Feed Pump`, `feed pump A`) ke tag canonical `GA-1201A`.
  * Jika extractor mendeteksi referensi yang ambigu (contoh: hanya tertulis `Feed Pump` tanpa penanda A/B), extractor diperbolehkan memberikan list kandidat atau menandai `is_ambiguous: true`.

---

## 4. Metadata Sumber & Keterlacakan (*Source Metadata*)

Setiap dokumen wajib menyertakan blok metadata sumber:

| Field | Tipe | Status | Nilai yang Diizinkan / Contoh | Deskripsi |
|---|---|---|---|---|
| `document_id` / `doc_no` | string | **Wajib** | `TJC-LLD-DS-GA-1201A`, `SEQ-1201` | Nomor resmi engineering document |
| `document_type` | string | **Wajib** | `DATASHEET`, `PID`, `OPL`, `INTERLOCK`, `PLOT_PLAN`, `MAINTENANCE` | Tipe kategori dokumen (lihat Section 5) |
| `file_name` | string | **Wajib** | `Equipment Datasheet - GA-1201A.pdf` | Nama berkas dokumen fisik asal |
| `page` | integer | Opsional | `1`, `2` (Default: `1`) | Halaman fisik bukti |
| `sheet` | string | Opsional | `Mechanical Data`, `Cause Effect` | Nama lembar kerja jika bersumber dari spreadsheet |
| `revision` | string | Opsional | `Rev 3`, `Rev.03`, `Rev 0`, `Rev B` | Penanda nomor revisi engineering |
| `status` | string | Opsional | `Approved`, `Issued for Operation`, `Issued for Construction`, `Draft` | Status approval dokumen |

> [!IMPORTANT]
> **Aturan Integritas**: Extractor dilarang mengarang nilai `revision` atau `status` jika dokumen asli tidak menuliskannya. Kirimkan nilai `null` daripada data palsu. Ingestion Engine akan mencatat nilai `null` tersebut dalam laporan audit (*Ingestion Quality Report*).

---

## 5. Taksonomi Tipe Dokumen (*Document Types*)

Peta normalisasi tipe dokumen dari extractor ke canonical enum:

| Label Masukan Extractor | Canonical `DocumentType` | Target Knowledge Object Utama |
|---|---|---|
| `Equipment Datasheet`, `datasheet`, `DS` | `DATASHEET` | `TechnicalRecord` (parameter/value/unit) |
| `One Point Lesson`, `OPL`, `SOP`, `procedure` | `OPL` | `DocumentChunk` (tahapan langkah, safety, troubleshooting) |
| `Piping & Instrumentation Diagram`, `P&ID`, `PID` | `PID` | `RelationshipRecord` (loop & trip link) + `TechnicalRecord` (setpoint) |
| `Interlock Logic Diagram`, `Cause Effect`, `IL` | `INTERLOCK` | `RelationshipRecord` (initiator $\rightarrow$ action) + `DocumentChunk` |
| `Plot Plan`, `Equipment Location`, `layout` | `PLOT_PLAN` | `TechnicalRecord` (grid, elevasi) + `DocumentChunk` |
| `Maintenance History`, `SAP PM`, `work_orders` | `MAINTENANCE` | `MaintenanceRecord` (failure, symptom, root cause, downtime) |
| Format lain di luar daftar | `OTHER` / `UNKNOWN` | Masuk ke *Unresolved Ingestion Report* |

---

## 6. Spesifikasi Payload per Kategori Dokumen

### A. Dokumen Spesifikasi Teknik (Datasheet)
* **Karakteristik**: Berisi parameter, nilai nominal/desain, dan satuan ukur (*unit*).
* **Field yang Dibutuhkan**:
  ```json
  {
    "document_id": "TJC-LLD-DS-GA-1201A",
    "document_type": "DATASHEET",
    "equipment_tag": "GA-1201A",
    "source": {
      "file_name": "Equipment Datasheet - GA-1201A.pdf",
      "revision": "Rev 3",
      "status": "Issued for Operation"
    },
    "parameters": [
      {
        "category": "Pump Design",
        "parameter": "Rated Flow",
        "value": 45,
        "unit": "m3/h"
      },
      {
        "category": "Pump Design",
        "parameter": "Rated Head",
        "value": 120,
        "unit": "m"
      }
    ]
  }
  ```

### B. Dokumen Prosedur & Pengetahuan Tacit (OPL)
* **Karakteristik**: Prosedur langkah-demi-langkah, safety precautions, dan troubleshooting tacit.
* **Field yang Dibutuhkan**:
  ```json
  {
    "document_id": "OPL-GA-1201A-01",
    "document_type": "OPL",
    "title": "Mechanical Seal Flush (API Plan 11) Verification",
    "equipment_tag": "GA-1201A",
    "discipline": "Mechanical",
    "source": {
      "file_name": "OPL-GA-1201A-01.pdf",
      "revision": "Rev 0",
      "status": "Approved"
    },
    "sections": {
      "purpose": "Prosedur verifikasi sirkulasi seal flush Plan 11...",
      "safety_precautions": ["Gunakan APD lengkap", "Pastikan pompa terisolasi"],
      "tools": ["Kunci pas 17mm", "Pressure gauge kalibrasi"],
      "steps": [
        {"step": 1, "action": "Periksa dP pada PDI-1201", "check": "dP > 1.5 bar"}
      ],
      "troubleshooting": [
        {
          "symptom": "Kebocoran hexane pada seal gland",
          "cause": "Orifice RO-1201 tersumbat",
          "action": "Bersihkan orifice dan ganti seal cartridge"
        }
      ]
    }
  }
  ```

### C. Dokumen Logika Proteksi & Interlock
* **Karakteristik**: Hubungan sebab-akibat (*Cause & Effect*) antara initiator switch/transmitter dan final element trip.
* **Field yang Dibutuhkan**:
  ```json
  {
    "document_id": "TJC-LLD-IL-GA-1201A",
    "logic_no": "SEQ-1201",
    "document_type": "INTERLOCK",
    "equipment_tag": "GA-1201A",
    "sil_level": "SIL 1",
    "source": {
      "file_name": "Interlock Logic - GA-1201A.pdf",
      "revision": "Rev 3",
      "status": "Issued for Operation"
    },
    "trips": [
      {
        "trip_id": "T3",
        "initiator_tag": "VSHH-1201",
        "condition": "Bearing Vibration HIGH-HIGH",
        "setpoint": "> 7.1 mm/s RMS",
        "voting": "1oo2",
        "actions": ["Trip Motor GA-1201A", "Close Discharge XV-1201", "DCS Alarm"]
      }
    ],
    "permissives": [
      {
        "permissive_id": "P1",
        "description": "Suction valve OPEN",
        "signal_tag": "ZSO-1201",
        "gate": "AND"
      }
    ]
  }
  ```

### D. Dokumen Riwayat Perawatan (Maintenance History)
* **Karakteristik**: Riwayat record berbasis SAP PM / CMMS.
* **Field yang Dibutuhkan**:
  ```json
  {
    "event_id": "WO-240003",
    "notification_no": "NT-2024-560012",
    "equipment_tag": "GA-1201A",
    "report_date": "2025-02-23",
    "work_type": "Corrective Maintenance",
    "breakdown": "Yes",
    "problem_description": "GA-1201A tripped on VSHH-1201 high vibration 7.4 mm/s",
    "root_cause": "Angular misalignment 0.12 mm/100mm after foundation settlement",
    "corrective_action": "Laser re-aligned pump/motor, re-shimmed motor feet",
    "downtime_hours": 8.5,
    "spare_parts_used": ["Shim pack SS316", "Coupling bolts"]
  }
  ```

---

## 7. Batasan yang Diketahui (*Known Limitations*)

1. **Struktur Campuran (Hybrid Table-Text)**:
   * Dokumen seperti P&ID memuat teks instrumen sekaligus relasi topologi pipa. Ingestion memisahkan data ini menjadi `RelationshipRecord` (keterkaitan loop) dan `TechnicalRecord` (setpoint alarm).
2. **Missing Metadata Fields**:
   * Jika tanggal pada maintenance record hanya mencantumkan bulan dan tahun, ingestion menetapkan tanggal default ke hari pertama bulan tersebut dan memberi catatan warning pada Ingestion Report.
3. **Variasi Istilah Satuan Ukur**:
   * Satuan seperti `m³/h`, `m3/h`, `M3/HR`, `m^3/h` akan distandarisasi oleh normalizer menjadi canonical unit `m3/h`.

---

## 8. Definisi Selesai (*Definition of Done*)
Kontrak ini dinyatakan terpenuhi ketika extractor rekan tim menyerahkan berkas untuk unit peralatan baru (misal: `YD-2301`) dan:
1. Ingestion Engine dapat membaca seluruh metadata tanpa kegagalan parsing (*Zero KeyErrors*).
2. Tercipta pemisahan bersih ke 4 canonical objects.
3. Seluruh unit dan parameter dapat terlacak kembali ke nomor dokumen sumber.
