export interface ApiError {
  error: {
    code: string
    message: string
    details?: { phase?: string; issues?: Array<{ location: string; message: string }> }
  }
}

export interface Warning {
  code: string
  message: string
}

export interface ArtifactError extends Warning {
  artifact_id: string
}

export interface SourceProvenance {
  kind: 'website' | 'github_repo' | 'document' | 'database' | 'unknown'
  uri: string | null
  title: string | null
  repository?: string | null
  filename?: string | null
  database_backend?: string | null
  database_source_id?: string | null
  database_relation?: string | null
}

export interface RetrievalSettings {
  embedding_model: string | null
  embedding_precision: string | null
  ranking_mode: string | null
  ranking_profile: string | null
  ranking_pool: number | null
  ranking_aggregation: string | null
  region: string | null
}

export interface DiffSummary {
  first_apply: boolean | null
  pages_added: number | null
  pages_changed: number | null
  pages_unchanged: number | null
  pages_removed: number | null
  chunks_unchanged: number | null
  chunks_to_embed: number | null
  rows_to_upsert: number | null
  stale_rows: number | null
  retained_stale_rows: number | null
}

export interface PlanSummary {
  plan_id: string
  namespace: string
  site_id: string
  created_at: string | null
  source: SourceProvenance
  page_count: number | null
  chunk_count: number | null
  diff: DiffSummary
  source_activity: {
    credentials_required: boolean | null
    api_calls_occurred: boolean | null
  }
  warnings: Warning[]
}

export interface PlanDetail {
  summary: PlanSummary
  namespace_candidate: string
  artifact_hash: string | null
  retrieval: RetrievalSettings
  source_activity: {
    credentials_required: boolean | null
    api_calls_occurred: boolean | null
  }
}

export interface PlanInventory {
  items: PlanSummary[]
  total: number
  offset: number
  limit: number
  errors: ArtifactError[]
}

export type LocalNamespaceStatus = 'planned' | 'applied' | 'pending_changes' | 'conflict' | 'error'

export interface NamespaceSummary {
  namespace: string
  source: SourceProvenance | null
  plan_count: number
  latest_plan_id: string | null
  latest_plan_created_at: string | null
  applied: boolean
  active_rows: number | null
  last_apply_id: string | null
  local_status: LocalNamespaceStatus
  retained_stale_rows: number | null
  latest_planned_upserts: number | null
  latest_planned_stale_rows: number | null
  document_count: number | null
  chunk_count: number | null
  warnings: Warning[]
}

export interface NamespaceDetail {
  summary: NamespaceSummary
  plans: PlanSummary[]
  state: {
    namespace: string
    site_id: string
    source: SourceProvenance
    updated_at: string | null
    last_plan_id: string | null
    last_apply_id: string | null
    active_rows: number
    retained_stale_rows: number
  } | null
  retrieval: RetrievalSettings | null
}

export interface NamespaceInventory {
  items: NamespaceSummary[]
  total: number
  offset: number
  limit: number
  errors: ArtifactError[]
}

export interface DashboardData {
  plan_count: number
  namespace_count: number
  applied_namespace_count: number
  pending_namespace_count: number
  active_row_count: number | null
  artifact_error_count: number
  recent_plans: PlanSummary[]
  attention_items: Warning[]
  artifact_errors: ArtifactError[]
}

export interface Capabilities {
  api_version: string
  buoy_version: string
  loopback_only: boolean
  read_only: boolean
  remote_snapshot: boolean
  search: boolean
  mutations: boolean
  artifacts_root_available: boolean
  state_root_available: boolean
  turbopuffer_credentials_available: boolean
  ui_build_available: boolean
  bigquery_extra_installed: boolean
  snowflake_extra_installed: boolean
}

export interface PageSummary {
  index: number
  title: string
  canonical_url: string
  status: number | null
  content_type: string
}

export interface PageInventory {
  items: PageSummary[]
  total: number
  offset: number
  limit: number
}

export interface PagePreview {
  page: PageSummary
  markdown: string
  truncated: boolean
}

export interface ChunkPreview {
  index: number
  row_id: string
  title: string
  canonical_url: string
  section_path: string
  chunk_index: number
  content: string
  truncated: boolean
}

export interface ChunkInventory {
  items: ChunkPreview[]
  total: number
  offset: number
  limit: number
}

export type RemoteStatus =
  | 'not_checked'
  | 'local_only'
  | 'eligible'
  | 'missing_card'
  | 'stale_target'
  | 'disabled'
  | 'incompatible'

export interface RemoteNamespaceStatus {
  namespace: string
  local_present: boolean
  live: boolean | null
  card_present: boolean | null
  status: RemoteStatus
  title: string | null
  source_kind: string | null
  tags: string[]
}

export interface RemoteSnapshot {
  state: 'not_checked' | 'not_configured' | 'ready' | 'error'
  credentials_required: boolean
  api_calls_occurred: boolean
  writes_occurred: boolean
  namespaces: RemoteNamespaceStatus[]
  namespace_total: number
  namespaces_truncated: boolean
  counts: Record<string, number>
  request_counts: Record<string, number>
  snapshot_revision: string | null
  error: ApiError['error'] | null
}

export interface SearchHit {
  namespace: string
  title: string
  citation: string
  section: string
  content_preview: string
  content_truncated: boolean
  tags: string[]
  score: Record<string, unknown>
}

export interface SearchResponse {
  state: 'success' | 'error'
  credentials_required: boolean
  api_calls_occurred: boolean
  writes_occurred: boolean
  automatic: boolean
  namespaces: string[]
  hits: SearchHit[]
  diagnostics: Record<string, unknown>
  error: ApiError['error'] | null
}
