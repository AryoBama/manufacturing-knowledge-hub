# Data Contract Specification (Phase 1)

Panduan ekstraksi data untuk tim. Semua file hasil ekstraksi disimpan di folder `data/extracted/Set_XX_<TAG>/` dalam format JSON.

---

## 1. Traceability Invariant (Prinsip Utama)

Setiap `DocumentChunk` **wajib dapat berdiri sendiri sebagai bukti teknis (*evidence*)** yang dapat ditelusuri kembali ke dokumen aslinya:
$$\text{Chunk ID} \longrightarrow \text{Document ID} \longrightarrow \text{File Name} \longrightarrow \text{Page} \longrightarrow \text{Revision} \longrightarrow \text{Status}$$

---

## 2. Dokumen Teknis (Datasheet, Interlock, OPL, Drawing, P&ID)

Setiap file dokumen menghasilkan objek JSON dengan skema `DocumentChunk`:

```json
{
  "chunk_id": "TJC-LLD-DS-GA-1201A-P01-C01",
  "document_id": "TJC-LLD-DS-GA-1201A",
  "document_type": "DATASHEET",
  "title": "Centrifugal Pump Data Sheet - GA-1201A",
  "equipment_tag": "GA-1201A",
  "content": "PUMP TYPE: HORIZONTAL, END SUCTION, SINGLE STAGE. Rated flow: 45 m3/h. Rated head: 120 m. Design pressure: 8.6 bar diff. Fluid: n-Hexane at 40 degC. Material Casing: ASTM A351 CF8M (SS316). Mechanical Seal: John Crane T2100 with API Plan 11 + 62. Motor: 30 kW, 2970 rpm, 380 V, Ex nA IIC T3 Gc.",
  "source": {
    "file_name": "Equipment Datasheet - GA-1201A.pdf",
    "page": 1,
    "revision": "Rev 3",
    "status": "Issued for Operation"
  }
}
```

### Aturan Wajib & Naming Rule:
| Field | Tipe | Format / Aturan | Keterangan |
|---|---|---|---|
| `chunk_id` | `string` | `<document_id>-P<page>-C<idx>` | **Wajib**: Awali dengan `document_id`, e.g. `TJC-LLD-DS-GA-1201A-P01-C01` |
| `document_id` | `string` | Nomor dokumen pabrik | e.g. `TJC-LLD-DS-GA-1201A` |
| `document_type` | `enum / string` | `DATASHEET`, `PID`, `OPL`, `INTERLOCK`, `GA_DRAWING`, `PLOT_PLAN`, `SOP` | Jenis dokumen |
| `title` | `string` | Judul seksi/dokumen | e.g. `Centrifugal Pump Data Sheet` |
| `equipment_tag` | `string` (opsional) | Tag alat | e.g. `GA-1201A` |
| `content` | `string` | Teks teknis mandiri | Minimal 10 karakter |
| `source.file_name` | `string` | Nama file PDF fisik | e.g. `Equipment Datasheet - GA-1201A.pdf` |
| `source.page` | `int` | Nomor halaman dokumen fisik | e.g. `1` |
| `source.revision` | `string` | Nomor revisi | e.g. `Rev 3` |
| `source.status` | `enum` | Salah satu dari: `Approved`, `Issued for Operation`, `Issued for Review`, `Issued for Construction`, `Draft`, `Obsolete` | Status rilis dokumen |

---

## 3. Riwayat Perawatan (Maintenance Record)

Jika mengekstrak baris event perbaikan / kerusakan:

```json
{
  "event_id": "MNT-GA1201A-2025-01",
  "equipment_tag": "GA-1201A",
  "date": "2025-08-14",
  "failure_mode": "High vibration",
  "symptom": "VSHH-1201 triggered alarm at 7.3 mm/s",
  "root_cause": "Coupling misalignment and worn drive-end bearing (7310 BECBM)",
  "corrective_action": "Realigned pump-motor shaft and replaced DE bearing",
  "downtime_hours": 3.5,
  "parts_replaced": ["7310 BECBM bearing", "Flexible spacer coupling"]
}
```
*Catatan: Kolom `date` wajib berformat kalender ISO valid: `YYYY-MM-DD`.*

---

## 4. Cara Mandiri Menjalankan Validator

Sebelum data disetor ke repository, jalankan validator di terminal:
```bash
python -m src.ingestion.contract_validator data/extracted
```
Jika muncul `[PASS]`, data lolos verifikasi kontrak AI.
