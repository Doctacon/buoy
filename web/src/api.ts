import type {
  ApiError,
  Capabilities,
  ChunkInventory,
  DashboardData,
  NamespaceDetail,
  NamespaceInventory,
  PageInventory,
  PagePreview,
  PlanDetail,
  PlanInventory,
  RemoteSnapshot,
  SearchResponse,
} from './types'

export class RequestError extends Error {
  code: string

  constructor(message: string, code = 'request_failed') {
    super(message)
    this.name = 'RequestError'
    this.code = code
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api/v1${path}`, {
      ...init,
      headers: init?.body ? { 'Content-Type': 'application/json', ...init.headers } : init?.headers,
    })
  } catch {
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
    throw new RequestError(error?.message || 'The request could not be completed.', error?.code)
  }
  return payload as T
}

type Paged<T> = { items: T[]; total: number; offset: number; limit: number }

async function allPages<T, P extends Paged<T>>(path: string): Promise<P> {
  const limit = 100
  const first = await request<P>(`${path}${path.includes('?') ? '&' : '?'}offset=0&limit=${limit}`)
  const items = [...first.items]
  while (items.length < first.total) {
    const page = await request<P>(`${path}${path.includes('?') ? '&' : '?'}offset=${items.length}&limit=${limit}`)
    if (!page.items.length) throw new RequestError('The local inventory response ended before all records were returned.')
    items.push(...page.items)
  }
  return { ...first, items, offset: 0, limit: items.length || limit } as P
}

const guardedPost = { method: 'POST', headers: { 'X-Buoy-Command-Center': '1' } }

export const api = {
  capabilities: () => request<Capabilities>('/capabilities'),
  dashboard: () => request<DashboardData>('/dashboard'),
  namespaces: () => allPages<NamespaceInventory['items'][number], NamespaceInventory>('/namespaces'),
  namespace: (namespace: string) =>
    request<NamespaceDetail>(`/namespaces/${encodeURIComponent(namespace)}`),
  plans: () => allPages<PlanInventory['items'][number], PlanInventory>('/plans'),
  plan: (planId: string) => request<PlanDetail>(`/plans/${encodeURIComponent(planId)}`),
  pages: (planId: string) =>
    allPages<PageInventory['items'][number], PageInventory>(`/plans/${encodeURIComponent(planId)}/pages`),
  page: (planId: string, index: number) =>
    request<PagePreview>(`/plans/${encodeURIComponent(planId)}/pages/${index}`),
  chunks: (planId: string, offset: number) =>
    request<ChunkInventory>(`/plans/${encodeURIComponent(planId)}/chunks?offset=${offset}&limit=10`),
  refreshRemote: () => request<RemoteSnapshot>('/remote/snapshot', guardedPost),
  search: (payload: Record<string, unknown>) =>
    request<SearchResponse>('/search', { ...guardedPost, body: JSON.stringify(payload) }),
}
