# Semantic Mapping & Canonical Field Specification

Dokumen ini mendokumentasikan taksonomi ekuivalensi semantik antara label lapangan (*source labels*) dari berbagai dokumen teknik (*Datasheet, P&ID, SAP PM*) dengan medan kanonikal (*canonical fields*) pada sistem Ingestion.

---

## 1. Prinsip Kolaborasi: AI Lead & Chemical Engineer

Sesuai arahan pada **Step 11 & 12**:
* **AI Lead**: Menentukan struktur representasi data (`TechnicalRecord`, tipe data numerik vs string, keterlacakan sumber, dan mekanisme normalisasi satuan).
* **Chemical / Process Engineer**: Memvalidasi ekuivalensi semantik teknis (apakah "Nominal Capacity", "Rated Flow", dan "Q_rated" merujuk pada variabel proses yang sama pada jenis peralatan tertentu).

> [!IMPORTANT]
> **Prinsip Non-Destructive Ingestion**: Ingestion tidak pernah membuang istilah asli sumber dokumen. Setiap `TechnicalRecord` memuat:
> 1. `canonical_field` (misal: `rated_flow`) untuk kemudahan pencarian terstruktur (*structured query*).
> 2. `parameter` & `source_label` (misal: `Rated Capacity`) untuk mempertahankan terminologi asli engineering.
> 3. `value` & `unit` yang telah dinormalisasi.

---

## 2. Kamus Pemetaan Parameter Utama

| Canonical Field | Source Labels yang Divalidasi | Unit Standar | Jenis Alat Relevan | Tim Validasi |
|---|---|---|---|---|
| `rated_flow` | `Rated Flow`, `Rated Capacity`, `Design Flow`, `Nominal Flow`, `Q_rated`, `Capacity` | `m3/h` | Pompa, Kompresor, Blower | Process Engineering |
| `rated_head` | `Rated Head`, `Design Head`, `Total Dynamic Head`, `TDH`, `Head` | `m` | Pompa Sentrifugal | Mechanical Rotating |
| `differential_pressure` | `Differential Pressure`, `Diff Pressure`, `dP`, `Delta P`, `Operating dP` | `bar` | Pompa, Filter, HE | Process Engineering |
| `npsh_required` | `NPSH Required`, `NPSHr`, `NPSH (r)` | `m` | Pompa Sentrifugal | Mechanical Rotating |
| `pumping_temperature` | `Pumping Temperature`, `Operating Temperature`, `Design Temp`, `Fluid Temp` | `degC` | Semua Alat Proses | Process Engineering |
| `motor_power` | `Output Power`, `Motor Power`, `Rated Power`, `Motor Rating`, `Rated Motor Output` | `kW` | Motor Penggerak | Electrical Engineering |
| `motor_speed` | `Speed`, `Rated Speed`, `RPM`, `Rotational Speed` | `rpm` | Motor, Pompa, Kompresor | Electrical Engineering |
| `motor_voltage` | `Voltage`, `Supply Voltage`, `Rated Voltage`, `Operating Voltage` | `V` | Motor Penggerak | Electrical Engineering |
| `grid_reference` | `Grid Reference`, `Grid Ref`, `Plot Grid`, `Coordinates` | - | Seluruh Fasilitas | Civil & Layout |
| `elevation` | `Elevation`, `Grade Elevation`, `EL`, `Baseplate Elevation` | `m` | Seluruh Fasilitas | Civil & Layout |

---

## 3. Contoh Hasil Normalisasi `TechnicalRecord`

Ketika sumber dokumen menuliskan:
```text
Category: Pump Design
Parameter: Rated Flow
Value: 45
Unit: m³/h
```

Normalizer menghasilkan `TechnicalRecord`:
```json
{
  "record_id": "DS-GA1201A-RATED-FLOW",
  "record_type": "technical_parameter",
  "equipment_tag": "GA-1201A",
  "document_id": "TJC-LLD-DS-GA-1201A",
  "document_type": "DATASHEET",
  "category": "Pump Design",
  "parameter": "Rated Flow",
  "canonical_field": "rated_flow",
  "source_label": "Rated Flow",
  "value": 45.0,
  "unit": "m3/h",
  "source": {
    "file_name": "Equipment Datasheet - GA-1201A.pdf",
    "sheet": "Mechanical Data",
    "revision": "Rev.03",
    "status": "Issued for Operation"
  }
}
```

Hal ini memungkinkan sistem menjawab pertanyaan:
* *"What is the rated flow of GA-1201A?"* secara deterministik melalui **Structured Lookup** ($value = 45\text{ m}^3/\text{h}$) tanpa harus bergantung pada probabilitas cosine similarity teks biasa.
