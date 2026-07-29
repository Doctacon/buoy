import type {
  ApiError,
  ArtifactErrorInventory,
  Capabilities,
  ChunkInventory,
  DashboardData,
  LocalNamespaceStatus,
  NamespaceDetail,
  NamespaceInventory,
  PlanInventory,
  PlanJob,
  PlanJobInventory,
  PlanJobRequest,
  PlanReview,
  RemoteSnapshot,
  SearchResponse,
  SourceProvenance,
  StaleRowInventory,
} from './types'

export class RequestError extends Error {
  code: string
  details: ApiError['error']['details']

  constructor(message: string, code = 'request_failed', details?: ApiError['error']['details']) {
    super(message)
    this.name = 'RequestError'
    this.code = code
    this.details = details
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api/v1${path}`, {
      ...init,
      headers: init?.body ? { 'Content-Type': 'application/json', ...init.headers } : init?.headers,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new RequestError('The local Buoy server could not be reached. Check that it is running, then retry.')
  }

  let payload: T | ApiError
  try {
    payload = (await response.json()) as T | ApiError
  } catch {
    throw new RequestError('The local Buoy server returned an unreadable response.')
  }
  if (!response.ok) {
    const error = (payload as ApiError).error
    throw new RequestError(error?.message || 'The request could not be completed.', error?.code, error?.details)
  }
  return payload as T
}

const guardedPost = { method: 'POST', headers: { 'X-Buoy-Command-Center': '1' } }
const PAGE_LIMIT = 50

function queryPath(path: string, values: Record<string, string | number | undefined>) {
  const parameters = new URLSearchParams()
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value !== '') parameters.set(key, String(value))
  }
  return `${path}?${parameters}`
}

export type PlanFilters = {
  offset: number
  q?: string
  namespace?: string
  source_kind?: SourceProvenance['kind']
}

export type NamespaceFilters = {
  offset: number
  q?: string
  source_kind?: SourceProvenance['kind']
  local_status?: LocalNamespaceStatus
}

export type ArtifactErrorFilters = {
  offset: number
  q?: string
}

export const api = {
  capabilities: () => request<Capabilities>('/capabilities'),
  dashboard: () => request<DashboardData>('/dashboard'),
  artifactErrors: (filters: ArtifactErrorFilters) => request<ArtifactErrorInventory>(queryPath('/artifact-errors', { ...filters, limit: PAGE_LIMIT })),
  namespaces: (filters: NamespaceFilters) => request<NamespaceInventory>(queryPath('/namespaces', { ...filters, limit: PAGE_LIMIT })),
  namespace: (namespace: string) =>
    request<NamespaceDetail>(`/namespaces/${encodeURIComponent(namespace)}?plan_offset=0&plan_limit=20`),
  plans: (filters: PlanFilters) => request<PlanInventory>(queryPath('/plans', { ...filters, limit: PAGE_LIMIT })),
  review: (planId: string) => request<PlanReview>(
    `/plans/${encodeURIComponent(planId)}/review?chunk_offset=0&chunk_limit=10&max_chars=2000&stale_offset=0&stale_limit=10`,
  ),
  planJobs: () => request<PlanJobInventory>('/plan-jobs?offset=0&limit=50'),
  planJob: (jobId: string) => request<PlanJob>(`/plan-jobs/${encodeURIComponent(jobId)}`),
  startPlanJob: async (payload: PlanJobRequest) => {
    // The process-local token remains scoped to this submission and is never persisted.
    const token = await request<{ csrf_token: string }>('/csrf-token')
    return request<PlanJob>('/plan-jobs', {
      method: 'POST',
      headers: { 'X-Buoy-CSRF-Token': token.csrf_token },
      body: JSON.stringify(payload),
    })
  },
  chunks: (planId: string, offset: number) =>
    request<ChunkInventory>(`/plans/${encodeURIComponent(planId)}/chunks?offset=${offset}&limit=10&max_chars=2000`),
  staleRows: (planId: string, offset: number) =>
    request<StaleRowInventory>(`/plans/${encodeURIComponent(planId)}/stale-rows?offset=${offset}&limit=10`),
  refreshRemote: () => request<RemoteSnapshot>('/remote/snapshot', guardedPost),
  search: (payload: Record<string, unknown>) =>
    request<SearchResponse>('/search', { ...guardedPost, body: JSON.stringify(payload) }),
}
