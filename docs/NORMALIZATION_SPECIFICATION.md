# Normalization Engine Specification & Architecture

Dokumen ini menjelaskan arsitektur teknis modul **Ingestion & Normalization** pada sistem *Manufacturing Knowledge Hub* (Chandra Asri CALIBER 2026).

---

## 1. Arsitektur Aliran Data (Data Flow Pipeline)

```text
       EXTRACTOR TEMAN (PDF / Excel Workbooks)
                         │
                         ▼
             [ src/ingestion/adapter.py ]
    (Deteksi DocumentType secara agnostik tanpa hardcode)
                         │
        ┌────────────────┼────────────────┬────────────────┐
        ▼                ▼                ▼                ▼
  Datasheet        OPL Normalizer   Interlock/P&ID    Maintenance
  Normalizer                        Normalizer        Normalizer
        │                │                │                │
        └────────────────┼────────────────┴────────────────┘
                         │
                         ▼
             4 CANONICAL KNOWLEDGE OBJECTS
  (DocumentChunk, TechnicalRecord, MaintenanceRecord, RelationshipRecord)
                         │
                         ▼
             [ src/ingestion/validator.py ]
            (Pydantic Rigorous Validation)
                         │
                         ▼
                 NORMALIZED STORAGE
            data/processed/<EQUIPMENT_TAG>/
            ├── document_chunks.json
            ├── technical_records.json
            ├── maintenance_records.json
            ├── relationships.json
            └── ingestion_report.json
                         │
                         ▼
          PHASE 2 HYBRID RETRIEVAL & STRUCTURED LOOKUP
```

---

## 2. 4 Canonical Knowledge Objects

1. **`DocumentChunk`** ([schemas/document.py](file:///C:/Users/AryoBama/Lomba/CALIBER/manufacturing-knowledge-hub/schemas/document.py)):
   * Digunakan untuk teks naratif, SOP, lembar OPL, dan ringkasan layout.
   * Mendukung pencarian semantik teks (*BM25 + 3-gram fuzzy character matching*).
2. **`TechnicalRecord`** ([schemas/technical.py](file:///C:/Users/AryoBama/Lomba/CALIBER/manufacturing-knowledge-hub/schemas/technical.py)):
   * Digunakan untuk data berpasangan `parameter`, `value`, dan `unit`.
   * Mempertahankan `source_label` asli sekaligus memetakan ke `canonical_field` (misal: `rated_flow`, `rated_head`, `motor_power`).
   * Memungkinkan **Deterministic Structured Lookup** untuk pertanyaan engineering numerik.
3. **`MaintenanceRecord`** ([schemas/maintenance.py](file:///C:/Users/AryoBama/Lomba/CALIBER/manufacturing-knowledge-hub/schemas/maintenance.py)):
   * Digunakan untuk log perawatan berbasis SAP PM / CMMS.
   * Mencatat tanggal ISO, durasi downtime, riwayat kerusakan (*failure mode*, *root cause*, *corrective action*), dan suku cadang yang diganti.
4. **`RelationshipRecord`** ([schemas/relationship.py](file:///C:/Users/AryoBama/Lomba/CALIBER/manufacturing-knowledge-hub/schemas/relationship.py)):
   * Memodelkan topologi pabrik, loop instrumen P&ID, dan matriks interlock cause-effect.
   * Predikat hubungan: `triggers_trip`, `permissive_for`, `monitors`, `controls`, `protects`.

---

## 3. Prinsip Anti-Hardcoding & Agnostisisme Peralatan

* Modul [src/ingestion/adapter.py](file:///C:/Users/AryoBama/Lomba/CALIBER/manufacturing-knowledge-hub/src/ingestion/adapter.py) **sama sekali tidak memiliki pengecekan hardcode** seperti `if equipment == "GA-1201A": ...`.
* Seluruh percabangan alur normalizer didasarkan murni pada **`DocumentType`** (`DATASHEET`, `OPL`, `PID`, `INTERLOCK`, `PLOT_PLAN`, `MAINTENANCE`).
* Hal ini menjamin bahwa extractor untuk unit peralatan ke-2 (misal: `YD-2301`) hingga unit ke-8 dapat diproses melalui pipeline yang sama persis tanpa perlu modifikasi kode logika.

---

## 4. Pelaporan Audit Mutu (*Ingestion Quality Report*)

Setiap eksekusi pipeline menghasilkan berkas `ingestion_report.json` yang memuat:
* Jumlah total objek yang diproses.
* Rincian objek per kategori canonical.
* Validitas Pydantic (*Pass / Fail*).
* Daftar peringatan (*warnings*) jika terdapat metadata yang tidak tersedia pada dokumen sumber (*misal: missing formal revision*).
