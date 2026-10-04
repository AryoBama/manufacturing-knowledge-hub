export type Confidence = 'HIGH' | 'MEDIUM' | 'LOW' | 'UNVERIFIED'

export interface SourceCitation {
  evidence_id: string
  document_id: string
  document_type: string
  file_name: string
  revision: string | null
  status: string | null
  page: number | null
  sheet: string | null
  excerpt: string | null
}

export interface Recommendation {
  action: string
  basis: string
  evidence_id: string | null
  priority: string
  applicability: string | null
}

export interface GeneratedAnswer {
  query: string
  equipment_tag: string | null
  equipment_name: string | null
  intent: string
  summary_answer: string
  detailed_points: string[]
  confidence: Confidence
  confidence_reason: string
  citations: SourceCitation[]
  /** 1-based indices into `citations`; absent on answers saved before attribution existed. */
  summary_citations?: number[]
  /** Parallel to detailed_points. */
  point_citations?: number[][]
  recommendations: Recommendation[]
  requires_clarification: boolean
  clarification_prompt: string | null
  query_id: string | null
  trace?: { timestamp: string } | null
}

export interface DocumentSummary {
  document_id: string
  title: string
  document_type: string
  equipment_tag: string | null
  equipment_name: string | null
  area: string | null
  file_name: string
  revision: string | null
  status: string | null
  chunk_count: number
}

export interface DocumentChunkView {
  chunk_id: string
  title: string
  page: number | null
  sheet: string | null
  content: string
}

export interface Effect {
  action: string
  target: string | null
  kind: string
}
export interface Trip {
  id: string | null
  initiator: string
  description: string
  setpoint: string | null
  voting: string | null
  sil: string | null
  effects: Effect[]
}
export interface Permissive {
  id: string | null
  source: string
  description: string
  gate: string | null
}
export interface MaintenanceEvent {
  event_id: string
  date: string
  failure_occurred: boolean
  failure_mode: string | null
  symptom: string | null
  root_cause: string | null
  corrective_action: string | null
  downtime_hours: number | null
  parts_replaced: string[]
}

/** Typed, structured rendering of a document; absent when only text was extracted. */
export type StructuredView =
  | { kind: 'datasheet'; groups: { category: string; rows: { parameter: string; value: string; unit: string | null }[] }[] }
  | { kind: 'interlock'; trips: Trip[]; permissives: Permissive[] }
  | {
      kind: 'pid'
      rows: { tag: string | null; instrument_type: string | null; description: string | null; setpoint: string; unit: string | null; function: string | null }[]
    }
  | { kind: 'maintenance'; events: MaintenanceEvent[] }
  | { kind: 'plot_plan'; rows: { parameter: string; value: string; unit: string | null }[] }
  | { kind: 'opl'; header: string[]; sections: { title: string; lines: string[] }[] }

export interface DocumentDetail extends DocumentSummary {
  chunks: DocumentChunkView[]
  structured: StructuredView | null
}

export interface EquipmentView {
  tag: string
  name: string
  type: string
  area: string
  symbol: string
  has_diagram: boolean
  logic_tag: string | null
  trips: Trip[]
  permissives: Permissive[]
  instruments: { tag: string; role: string; instrument_type: string | null; description: string; related_interlock: string | null }[]
  components: { tag: string; description: string; level: string }[]
  maintenance: { events: number; failures: number; last_date: string | null }
  document_count: number
}

export interface PlantEquipment {
  tag: string
  name: string
  type: string
  document_count: number
  maintenance_events: number
  failure_count: number
}

export interface FailureModeFrequency {
  failure_mode: string
  count: number
  percentage: number
  sample_event_ids: string[]
}
export interface FailurePattern {
  equipment_tag: string
  total_maintenance_records: number
  failure_count: number
  non_failure_count: number
  top_failure_modes: FailureModeFrequency[]
  total_downtime_hours: number
  earliest_record_date: string | null
  latest_record_date: string | null
}
export interface SimilarFailureCase {
  event_id: string
  equipment_tag: string
  date: string
  similarity_score: number
  symptom: string | null
  failure_mode: string | null
  root_cause: string | null
  corrective_action: string | null
  parts_replaced: string[]
  source_file: string
  document_id: string
}
export interface RcaInsight {
  equipment_tag: string
  root_causes: string[]
  proven_actions: string[]
  replacement_parts_used: string[]
  reference_work_orders: string[]
}
export interface FailureMemoryReport {
  equipment_tag: string
  query_symptom: string | null
  has_historical_precedent: boolean
  pattern_summary: FailurePattern | null
  similar_cases: SimilarFailureCase[]
  rca_insights: RcaInsight | null
  disclaimer: string
}

export interface PlantArea {
  area: string
  name: string
  equipment: PlantEquipment[]
}

export interface PlantTree {
  plant: string
  areas: PlantArea[]
}

type Fetch = typeof fetch

async function request<T>(f: Fetch, path: string, init?: RequestInit): Promise<T> {
  const res = await f(path, init)
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

/** Pass SvelteKit's `fetch` from load functions so requests are tracked and deduplicated. */
export const createApi = (f: Fetch = (...a) => fetch(...a)) => ({
  ask: (query: string) =>
    request<GeneratedAnswer>(f, '/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    }),
  documents: (params: { document_type?: string; equipment_tag?: string; q?: string } = {}) => {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => v && qs.set(k, v))
    return request<DocumentSummary[]>(f, `/api/repository/documents?${qs}`)
  },
  document: (id: string, tag?: string | null) =>
    request<DocumentDetail>(
      f,
      `/api/repository/documents/${encodeURIComponent(id)}${tag ? `?equipment_tag=${encodeURIComponent(tag)}` : ''}`,
    ),
  plant: () => request<PlantTree>(f, '/api/repository/plant'),
  failurePatterns: (tag: string) => request<FailurePattern>(f, `/api/failure-memory/patterns/${encodeURIComponent(tag)}`),
  failureSearch: (query: string, tag: string) =>
    request<FailureMemoryReport>(f, '/api/failure-memory/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, equipment_tag: tag, top_k: 8 }),
    }),
  equipment: (tag: string) => request<EquipmentView>(f, `/api/repository/equipment/${encodeURIComponent(tag)}`),
})

export const api = createApi()

export function documentPath(documentId: string, tag?: string | null) {
  return `/repository/document/${encodeURIComponent(documentId)}${tag ? `?tag=${encodeURIComponent(tag)}` : ''}`
}
