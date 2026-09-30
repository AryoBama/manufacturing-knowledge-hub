# Chandra Asri Pacific — Manufacturing Knowledge Hub
**CALIBER 2026 Competition — Case 1: AI-Powered Industrial Knowledge Integration**

Platform integrasi pengetahuan operasional pabrik petrokimia yang menghubungkan **SOP, P&ID, Datasheet Teknis, Interlock Cause & Effect, serta Riwayat Kerusakan (SAP PM)** menjadi satu kesatuan *evidence-grounded AI knowledge hub* yang anti-halusinasi, terlacak hingga nomor halaman dokumen, dan siap operasi.

---

## Fitur Utama

1. **Industrial Data Ops & Plant Asset Graph**:
   * Menghubungkan hierarki fisik pabrik (*Plant $\rightarrow$ Area $\rightarrow$ Unit $\rightarrow$ Equipment*).
   * Pelacakan instrumen proteksi (*SIS Trip Setpoints, Start Permissives*).
   * Graf kausal multi-hop (*degradation propagation pathway*, misal: sumbatan orifice $\rightarrow$ dry-run $\rightarrow$ kebocoran seal).
2. **Multi-Signal Hybrid Retrieval Engine**:
   * Kombinasi *Metadata Filtering*, *BM25 / Exact Lexical Search*, dan *Dense Vector Retrieval* lokal berbasis SQLite & TF-IDF.
3. **Evidence Sufficiency Gate & Conflict Resolution**:
   * Audit kepatuhan status approval dokumen (*Approved / Issued for Operation*).
   * Deteksi kontradiksi nilai parameter proses antar revisi dokumen sebelum jawaban dibangkitkan.
4. **Active Failure Memory & RCA Recommendation**:
   * Deteksi dini insiden berulang berdasarkan kemiripan gejala (*symptom similarity search*).
   * Ekstraksi akar penyebab historis (*historical RCA*) dan tindakan korektif terbukti (*proven actions*).
5. **Pluggable LLM Adapter (Grounded Synthesis)**:
   * Mendukung **Google Gemini** (`gemini-3.8-flash`), **DeepSeek** (`deepseek-chat`), **OpenAI**, serta **Offline Mock** deterministik (air-gapped ready).

---

## Prasyarat Sistem (Prerequisites)

* **Python 3.11+**
* **Docker & Docker Compose** (Opsional, jika ingin menjalankan via kontainer)
* Akses Internet (Hanya jika ingin menghubungkan live LLM API seperti Google Gemini atau DeepSeek; untuk pengujian lokal, sistem dapat berjalan 100% offline).

---

## Konfigurasi Lingkungan (`.env`)

Salin file contoh konfigurasi [`.env.example`](.env.example) menjadi `.env`:

```bash
cp .env.example .env
```

Buka file `.env` dan atur provider LLM yang ingin digunakan:

### Opsi 1: Menggunakan Google Gemini (Rekomendasi Utama)
Ambil API key gratis di [Google AI Studio](https://aistudio.google.com/app/apikey):
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-3.8-flash
OFFLINE_MODE=false
```

### Opsi 2: Menggunakan DeepSeek Flash / Chat
Ambil API key di [DeepSeek Platform](https://platform.deepseek.com):
```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com/chat/completions
OFFLINE_MODE=false
```

### Opsi 3: Menjalankan 100% Offline (Tanpa API Key)
```env
OFFLINE_MODE=true
```
*(Sistem akan menggunakan generator deterministik internal berbasis ekstraksi dokumen langsung tanpa koneksi keluar).*

---

## Cara Menjalankan Backend

### Cara 1: Menggunakan Docker Compose (Paling Mudah & Terisolasi)

1. Jalankan build dan start container di background:
   ```bash
   docker compose up --build -d
   ```
2. Periksa status kontainer:
   ```bash
   docker compose ps
   ```
   *(Tunggu hingga status menunjukkan `Up (healthy)`)*
3. Melihat log aplikasi:
   ```bash
   docker compose logs -f
   ```
4. Menghentikan kontainer:
   ```bash
   docker compose down
   ```

---

### Cara 2: Menjalankan Langsung via Python (Local Development)

1. Buat dan aktifkan virtual environment (opsional namun disarankan):
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/Mac:
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Jalankan server FastAPI backend:
   ```bash
   python run_backend.py
   ```
   *Server akan aktif di `http://127.0.0.1:8000`.*

---

## Dokumentasi API Interaktif (Swagger UI)

Setelah backend aktif, buka browser Anda:

* **Interactive Swagger UI**: 👉 **`http://localhost:8000/docs`**
* **ReDoc Specification**: `http://localhost:8000/redoc`

---

## Ringkasan Endpoint Utama

| Endpoint | Method | Fungsi & Penggunaan |
| :--- | :---: | :--- |
| **`/api/query`** | `POST` | **Core Q&A Assistant**: Menjawab pertanyaan spesifikasi teknis, interlock trip, dan SOP dengan sitasi dokumen terverifikasi. |
| **`/api/failure-memory/search`** | `POST` | **Failure Memory**: Mencari histori insiden masa lalu dan akar penyebab (RCA) berdasarkan keluhan gejala kerusakan. |
| **`/api/failure-memory/patterns/{tag}`** | `GET` | Melihat statistik frekuensi kerusakan dan mode kegagalan berulang pada aset. |
| **`/api/failure-memory/rca/{tag}`** | `GET` | Mengambil solusi perbaikan historis dan suku cadang yang pernah digunakan. |
| **`/api/graph/hierarchy/{tag}`** | `GET` | Menelusuri posisi aset dalam hierarki fisik pabrik (*Plant $\rightarrow$ Area $\rightarrow$ Unit*). |
| **`/api/graph/protections/{tag}`** | `GET` | Menampilkan sensor trip interlock, voting logic (2oo3/1oo2), dan start permissives. |
| **`/api/graph/path`** | `POST` | Melacak rantai rambatan kegagalan multi-hop (*degradation propagation pathway*). |
| **`/api/health`** | `GET` | Liveness healthcheck probe. |
| **`/api/ready`** | `GET` | Readiness probe (memvalidasi kesiapan store dokumen, vector DB, dan graph engine). |

---

## Format Response `POST /api/query`

Setiap respon dijamin *evidence-grounded* dan memiliki audit skor kepercayaan yang transparan:

```json
{
  "query": "What is the trip condition and interlock for GA-1201A?",
  "equipment_tag": "GA-1201A",
  "equipment_name": "Hexane Feed Pump",
  "intent": "protection",
  "summary_answer": "Based on verified engineering documents, GA-1201A is protected by PSLL-1201 (< 0.5 barg, 2oo3), VSHH-1201 (> 7.1 mm/s, 1oo2), FSLL-1201 (< 9 m3/h), and TSHH-1201 (> 95 degC).",
  "detailed_points": [
    "PSLL-1201: Suction Pressure Low-Low (< 0.5 barg, 2oo3)",
    "VSHH-1201: DE Bearing Vibration High-High (> 7.1 mm/s RMS, 1oo2)"
  ],
  "confidence": "HIGH",
  "confidence_breakdown": {
    "asset_match_score": 1.0,
    "source_validity_score": 1.0,
    "retrieval_sufficiency_score": 0.96,
    "coverage_score": 1.0,
    "intent_confidence": 1.0,
    "final_score": 0.99,
    "formula": "0.25*Asset + 0.25*Source + 0.25*Sufficiency + 0.15*Coverage + 0.10*Intent - Penalties"
  },
  "citations": [
    {
      "document_id": "INT-1201-REV03",
      "document_type": "INTERLOCK",
      "file_name": "Interlock GA-1201A.xlsx",
      "revision": "Rev.03",
      "status": "Issued for Operation",
      "page": 1,
      "excerpt": "PSLL-1201 Suction Pressure Low-Low (< 0.5 barg)"
    }
  ],
  "recommendations": [],
  "trace": {
    "nlu_latency_ms": 0.8,
    "retrieval_latency_ms": 3.5,
    "sufficiency_latency_ms": 2.7,
    "generation_latency_ms": 850.2,
    "total_latency_ms": 857.2
  },
  "requires_clarification": false
}
```

---

## Menjalankan Showcase CLI & Test Suite

### 1. Showcase Skenario Kompetisi
Untuk mendemokan skenario tanya-jawab otomatis langsung di terminal:
```bash
python demo.py --showcase
```

### 2. Mode Terminal Interaktif
```bash
python demo.py
```

### 3. Menjalankan Automated Test Suite
Sistem dilengkapi dengan 99 unit & integration test komprehensif:
```bash
pytest -v
```

---

## Struktur Proyek

```text
manufacturing-knowledge-hub/
├── configs/                  # Konfigurasi routing, bobot retrieval, dan skor confidence
│   ├── confidence_config.json
│   ├── plant_equipment_registry.json
│   └── retrieval_config.json
├── data/                     # Knowledge store & dokumen pabrik
│   ├── extracted/            # Dokumen hasil ekstraksi terstruktur
│   ├── knowledge/            # Hierarki pabrik dan relasi kausal graf
│   └── processed/            # Master data P&ID, Datasheet, OPL, SAP PM
├── docs/                     # Spesifikasi teknis, rancangan arsitektur, & pitch deck
├── schemas/                  # Pydantic data contracts (Document, Technical, Maintenance, Graph)
├── src/
│   ├── adapters/             # Pluggable LLM Adapters (Gemini, DeepSeek, OpenAI, OfflineMock)
│   ├── api/                  # FastAPI REST API (server, routes, models, exceptions)
│   ├── failure_memory/       # Engine riwayat kegagalan dan rekomendasi RCA
│   ├── generation/           # Evidence fusion, confidence calculator, & synthesizer
│   ├── graph/                # Plant knowledge graph & BFS pathfinder
│   ├── ingestion/            # Pipeline loader dan normalizer dokumen
│   ├── query/                # NLU entity resolution & hybrid intent classifier
│   ├── retrieval/            # Multi-signal hybrid retriever & sufficiency gate
│   └── vector/               # SQLite in-process vector store & TF-IDF dense embedder
├── tests/                    # 99 Automated unit & integration tests
├── Dockerfile                # Hardened container image (non-root appuser)
├── docker-compose.yml        # Orchestration multi-env & volume binding
├── requirements.txt          # Python dependencies
└── run_backend.py            # Local backend entrypoint runner
```