# Query Contract (Sub-Phase 2A)

Spesifikasi kontrak query input dan output pemahaman query untuk Manufacturing Knowledge Hub.

## 1. Input Contract: `QueryRequest`
```json
{
  "query": "What should I check when GA-1201A has high vibration?",
  "equipment_tag": null,
  "session_context": {
    "current_page": "equipment_dashboard",
    "last_mentioned_tag": "GA-1201A"
  }
}
```

## 2. Output Contract: `QueryUnderstanding`
```json
{
  "query": "What should I check when GA-1201A has high vibration?",
  "intent": "troubleshooting",
  "equipment_tag": "GA-1201A",
  "resolution": {
    "source": "explicit_query",
    "confidence": "high"
  },
  "entities": {
    "equipment_tag": "GA-1201A",
    "symptom": "high vibration"
  },
  "knowledge_types": [
    "operating_procedure",
    "process_logic",
    "protection_logic",
    "failure_history"
  ],
  "requires_clarification": false,
  "clarification_reason": null
}
```

---

## 3. Aturan Desain Inti:
1. **`knowledge_types` $\ne$ `document_types`**:
   * `knowledge_types` menyatakan **jenis informasi** yang dicari (`operating_procedure`, `protection_logic`, `failure_history`).
   * Knowledge Router di layer berikutnya yang bertugas memetakan jenis informasi ini ke dokumen fisik (`OPL`, `PID`, `INTERLOCK`, `MAINTENANCE`).
2. **`resolution.confidence`**:
   * Tingkat keyakinan dalam **mengidentifikasi aset/alat** (`high`, `medium`, `low`, `none`), **bukan** tingkat keyakinan jawaban engineering AI.
3. **`resolution.source` (Enum)**:
   * `explicit_query`: Tag alat terdeteksi langsung di dalam teks pertanyaan.
   * `ui_context`: Tag alat diperoleh dari state UI atau halaman aktif saat ini.
   * `conversation_context`: Tag alat diperoleh dari riwayat dialog sebelumnya.
   * `inferred`: Tag alat diasosiasikan secara inferensi.
   * `none`: Tag alat tidak ditemukan / ambigu $\rightarrow$ memicu `requires_clarification: true`.
