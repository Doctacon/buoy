import { Link, MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import type { PlanSummary, SourceProvenance } from './types'

const diff = {
  first_apply: false,
  pages_added: 1,
  pages_changed: 2,
  pages_unchanged: 3,
  pages_removed: 0,
  chunks_unchanged: 4,
  chunks_to_embed: 5,
  rows_to_upsert: 6,
  stale_rows: 0,
  retained_stale_rows: 0,
}

const source: SourceProvenance = {
  kind: 'website',
  uri: 'https://example.test/docs',
  title: 'example.test',
  repository: null,
  filename: null,
  database_backend: null,
  database_source_id: null,
  database_relation: null,
}

const plan: PlanSummary = {
  plan_id: 'plan-1',
  namespace: 'docs-one',
  site_id: 'example-test',
  created_at: '2026-07-23T12:00:00Z',
  source,
  page_count: 1,
  chunk_count: 12,
  diff,
  payload_verification: 'not_checked',
  source_activity: { credentials_required: true, api_calls_occurred: true },
  warnings: [],
}

const dashboard = {
  plan_count: 1,
  namespace_count: 2,
  applied_namespace_count: 1,
  pending_namespace_count: 1,
  active_row_count: 8,
  artifact_error_count: 0,
  recent_plans: [plan],
  attention_items: [],
  artifact_errors: [],
  artifact_errors_truncated: false,
}

const namespaces = {
  items: [
    {
      namespace: 'docs-one', source, plan_count: 1, latest_plan_id: 'plan-1', latest_plan_created_at: plan.created_at,
      applied: true, active_rows: 8, last_apply_id: 'apply-1', local_status: 'pending_changes', retained_stale_rows: 1,
      latest_planned_upserts: 6, latest_planned_stale_rows: 0, document_count: 1, chunk_count: 12, warnings: [],
    },
    {
      namespace: 'repo-two', source: { ...source, kind: 'github_repo', title: 'owner/repo', repository: 'owner/repo' },
      plan_count: 1, latest_plan_id: 'plan-2', latest_plan_created_at: plan.created_at,
      applied: false, active_rows: null, last_apply_id: null, local_status: 'planned', retained_stale_rows: null,
      latest_planned_upserts: 0, latest_planned_stale_rows: 0, document_count: 1, chunk_count: 12, warnings: [],
    },
  ],
  total: 2, offset: 0, limit: 100, errors: [], error_total: 0, errors_truncated: false,
}

const capabilities = {
  api_version: 'v1', buoy_version: 'test', loopback_only: true, review_routes_read_only: true, local_plan_job_creation: true,
  managed_public_planning_available: true, managed_public_planning_unavailable_reason: null, durable_plan_job_history_available: true,
  remote_mutations: false, remote_snapshot: true, search: true,
  artifacts_root_available: true, state_root_available: true, turbopuffer_credentials_available: true,
  ui_build_available: true, bigquery_extra_installed: false, snowflake_extra_installed: false,
}

const jobId = `planjob_${'b'.repeat(32)}`
const activeJobId = `planjob_${'a'.repeat(32)}`

function planJob(overrides: Record<string, unknown> = {}) {
  return {
    job_id: jobId,
    state: 'running',
    source_kind: 'website',
    source_url: 'https://example.test/docs',
    namespace: 'docs-one',
    plan_id: null,
    created_at: '2026-07-23T12:00:00Z',
    updated_at: '2026-07-23T12:00:01Z',
    event_sequence: 2,
    started_at: '2026-07-23T12:00:01Z',
    completed_at: null,
    latest_progress: { stage: 'crawl', message: 'Crawling credential-free HTTP(S) website content.', counts: { pages: 3 } },
    error: null,
    request_summary: { max_pages_or_files: 20, max_chunks: 100, namespace: 'docs-one', include_path_count: 1, exclude_path_count: 1 },
    ...overrides,
  }
}

class FakeEventSource {
  static instances: FakeEventSource[] = []
  url: string
  onopen: (() => void) | null = null
  onerror: (() => void) | null = null
  close = vi.fn()
  private listeners = new Map<string, (event: MessageEvent<string>) => void>()

  constructor(url: string | URL) {
    this.url = String(url)
    FakeEventSource.instances.push(this)
  }

  addEventListener(name: string, listener: EventListenerOrEventListenerObject) {
    this.listeners.set(name, listener as (event: MessageEvent<string>) => void)
  }

  emit(name: string, data: unknown) {
    this.listeners.get(name)?.(new MessageEvent(name, { data: JSON.stringify(data) }))
  }
}

const remote = {
  state: 'ready', credentials_required: true, api_calls_occurred: true, writes_occurred: false,
  namespaces: [
    { namespace: 'docs-one', local_present: true, live: true, card_present: true, status: 'eligible', title: 'Docs', source_kind: 'website', tags: ['docs'] },
    { namespace: 'repo-two', local_present: true, live: false, card_present: false, status: 'local_only', title: null, source_kind: null, tags: [] },
  ],
  namespace_total: 2, namespaces_truncated: false, counts: { eligible_count: 1 }, request_counts: { namespace_list_pages: 1 }, snapshot_revision: 'rev-1', error: null,
}

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
}

function mockApi(
  handler: (path: string, init?: RequestInit) => unknown | Promise<unknown>,
  capabilityPayload: unknown = capabilities,
) {
  const mock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input)
    let result = path.includes('/capabilities') ? capabilityPayload : await handler(path, init)
    if (result === undefined && path.includes('/stale-rows')) {
      result = { items: [], total: 0, offset: 0, limit: 10 }
    }
    if (
      result && !(result instanceof Response) && typeof result === 'object'
      && /\/namespaces\/[^/?]+\?plan_offset=0&plan_limit=20$/.test(path) && 'summary' in result && 'plans' in result
    ) {
      const detail = result as { plans: unknown[] }
      result = { plan_total: detail.plans.length, plan_offset: 0, plan_limit: 20, plans_truncated: false, ...result }
    }
    if (
      result && !(result instanceof Response) && typeof result === 'object'
      && /\/plans\/[^/?]+\/review\?/.test(path) && 'detail' in result
    ) {
      const review = result as { detail: Record<string, unknown> }
      result = {
        ...result,
        detail: {
          originating_job_id: null,
          payload_verification: 'verified',
          applied_state_present: false,
          applied_state_hash: 'b'.repeat(64),
          ...review.detail,
        },
      }
    }
    if (
      result && !(result instanceof Response) && typeof result === 'object'
      && path.includes('/chunks') && 'items' in result
    ) {
      result = { ...result, items: (result as { items: Array<Record<string, unknown>> }).items.map((item) => ({ action: 'changed', ...item })) }
    }
    return result instanceof Response ? result : json(result)
  })
  vi.stubGlobal('fetch', mock)
  return mock
}

function renderRoute(route: string) {
  return render(<MemoryRouter initialEntries={[route]}><App /></MemoryRouter>)
}

function renderRouteWithLink(route: string, target: string, label = 'Test route change') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Link to={target}>{label}</Link>
      <App />
    </MemoryRouter>,
  )
}

function HistoryControls() {
  const navigate = useNavigate()
  const location = useLocation()
  return <>
    <button type="button" onClick={() => navigate(-1)}>Browser back</button>
    <button type="button" onClick={() => navigate(1)}>Browser forward</button>
    <output aria-label="Current location">{location.pathname}{location.search}</output>
  </>
}

function renderRouteWithHistory(route: string) {
  return render(
    <MemoryRouter initialEntries={['/graphs', route]} initialIndex={1}>
      <HistoryControls />
      <App />
    </MemoryRouter>,
  )
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason: unknown) => void
  const promise = new Promise<T>((next, fail) => { resolve = next; reject = fail })
  return { promise, resolve, reject }
}

function detailFor(summary = plan, overrides: Record<string, unknown> = {}) {
  return {
    summary,
    namespace_candidate: summary.namespace,
    artifact_hash: 'a'.repeat(64),
    originating_job_id: null,
    payload_verification: 'verified',
    applied_state_present: false,
    applied_state_hash: 'b'.repeat(64),
    retrieval: null,
    source_activity: { credentials_required: false, api_calls_occurred: false },
    ...overrides,
  }
}

function chunksAt(offset = 0, total = 0, items: Array<Record<string, unknown>> = []) {
  return { items, total, offset, limit: 10 }
}

function staleAt(offset = 0, total = 0, items: Array<Record<string, unknown>> = []) {
  return { items, total, offset, limit: 10 }
}

function reviewFor(detail = detailFor(), chunks = chunksAt(), staleRows = staleAt()) {
  return { detail, chunks, stale_rows: staleRows }
}

afterEach(() => {
  cleanup()
  FakeEventSource.instances = []
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('Command Center', () => {
  it('shows dashboard loading and empty states without automatic remote activity', async () => {
    let resolveDashboard: (value: Response) => void = () => undefined
    const mock = mockApi((path) => path.includes('/dashboard') ? new Promise<Response>((resolve) => { resolveDashboard = resolve }) : remote)
    renderRoute('/')

    expect(screen.getByRole('status')).toHaveTextContent('Loading local dashboard')
    expect(screen.getByText(/Remote status: Not checked/i)).toBeInTheDocument()
    expect(mock).toHaveBeenCalledTimes(2)
    expect(mock.mock.calls.every((call) => call[1]?.method === undefined)).toBe(true)

    resolveDashboard(json({ ...dashboard, plan_count: 0, recent_plans: [], attention_items: [] }))
    expect(await screen.findByText(/Saved plans will appear here/)).toBeInTheDocument()
    expect(screen.getByText(/No local warnings require attention/)).toBeInTheDocument()
  })

  it('performs remote refresh only after explicit activation and reports exact activity', async () => {
    const user = userEvent.setup()
    const mock = mockApi((path) => path.includes('/remote/snapshot') ? remote : dashboard)
    renderRoute('/')
    await screen.findByText('plan-1')
    for (const label of ['Review routes read only', 'Managed public planning', 'Durable plan-job history', 'Unavailable reason', 'Remote mutations', 'Artifacts root available', 'State root available', 'turbopuffer credentials configured', 'UI build available', 'BigQuery extra installed', 'Snowflake extra installed', 'Pending changes', 'Artifact errors']) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
    expect(mock).toHaveBeenCalledTimes(2)

    await user.click(screen.getByRole('button', { name: 'Refresh remote status' }))

    expect(await screen.findByText(/Remote status: ready/i)).toBeInTheDocument()
    expect(screen.getByText(/Credentials required: Yes\. API calls occurred: Yes\. Writes occurred: No/)).toBeInTheDocument()
    expect(mock).toHaveBeenCalledTimes(3)
    expect(mock.mock.calls[2][1]?.method).toBe('POST')
    expect(mock.mock.calls[2][1]?.headers).toMatchObject({ 'X-Buoy-Command-Center': '1' })
  })

  it('renders an actionable dashboard error and retries', async () => {
    const user = userEvent.setup()
    let calls = 0
    mockApi(() => {
      calls += 1
      return calls === 1 ? json({ error: { code: 'internal_error', message: 'Local inventory failed.' } }, 500) : dashboard
    })
    renderRoute('/')
    expect(await screen.findByRole('alert')).toHaveTextContent('Local inventory failed')
    await user.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('plan-1')).toBeInTheDocument()
  })

  it('renders only the bounded artifact-error sample on ordinary inventory screens', async () => {
    const sample = Array.from({ length: 20 }, (_, index) => ({
      code: `error_${index}`,
      message: `Safe diagnostic ${index}`,
      artifact_id: `artifact-${index}`,
    }))
    mockApi((path) => {
      if (path.includes('/dashboard')) return { ...dashboard, artifact_error_count: 10_000, artifact_errors: sample, artifact_errors_truncated: true }
      if (path.startsWith('/api/v1/namespaces?')) return { ...namespaces, errors: sample, error_total: 10_000, errors_truncated: true }
      if (path.startsWith('/api/v1/plans?')) return { items: [plan], total: 1, offset: 0, limit: 50, errors: sample, error_total: 10_000, errors_truncated: true }
      throw new Error(`Unexpected path ${path}`)
    })

    for (const route of ['/', '/plans', '/namespaces']) {
      const view = renderRoute(route)
      const sampleLabel = await screen.findByText('Showing 20 of 10,000 local artifact errors.')
      const panel = sampleLabel.closest('section')
      expect(panel).not.toBeNull()
      expect(within(panel as HTMLElement).getAllByRole('listitem')).toHaveLength(20)
      expect(within(panel as HTMLElement).getByRole('link', { name: 'View artifact diagnostics' })).toHaveAttribute('href', '/artifact-errors')
      view.unmount()
    }
  })

  it('renders distinct artifact errors without duplicate React keys when code and artifact ID match', async () => {
    const errors = [
      { code: 'malformed_plan', message: 'First sanitized diagnostic', artifact_id: 'shared-artifact' },
      { code: 'malformed_plan', message: 'Second sanitized diagnostic', artifact_id: 'shared-artifact' },
    ]
    mockApi((path) => {
      if (path.includes('/dashboard')) return { ...dashboard, artifact_error_count: 2, artifact_errors: errors }
      if (path.startsWith('/api/v1/artifact-errors?')) return { items: errors, total: 2, offset: 0, limit: 50 }
      throw new Error(`Unexpected path ${path}`)
    })
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    try {
      const dashboardView = renderRoute('/')
      expect(await screen.findByText((_, element) => element?.tagName === 'LI' && element.textContent === 'malformed_plan: First sanitized diagnostic')).toBeInTheDocument()
      expect(screen.getByText((_, element) => element?.tagName === 'LI' && element.textContent === 'malformed_plan: Second sanitized diagnostic')).toBeInTheDocument()
      dashboardView.unmount()

      renderRoute('/artifact-errors')
      expect(await screen.findByRole('table')).toBeInTheDocument()
      expect(screen.getByText('First sanitized diagnostic')).toBeInTheDocument()
      expect(screen.getByText('Second sanitized diagnostic')).toBeInTheDocument()
      expect(consoleError.mock.calls.flat().join(' ')).not.toContain('same key')
    } finally {
      consoleError.mockRestore()
    }
  })

  it('requests and renders only one artifact-diagnostics page and resets offset on search', async () => {
    const user = userEvent.setup()
    const mock = mockApi((path) => {
      if (!path.startsWith('/api/v1/artifact-errors?')) throw new Error(`Unexpected path ${path}`)
      const parameters = new URL(`http://localhost${path}`).searchParams
      const offset = Number(parameters.get('offset') ?? 0)
      const query = parameters.get('q') ?? ''
      const total = query ? 1 : 10_000
      const count = Math.min(50, Math.max(0, total - offset))
      return {
        items: Array.from({ length: count }, (_, index) => ({
          code: query ? 'needle_code' : `error_${offset + index}`,
          message: query ? 'Needle diagnostic' : `Safe diagnostic ${offset + index}`,
          artifact_id: query ? 'needle-artifact' : `artifact-${offset + index}`,
        })),
        total,
        offset,
        limit: 50,
      }
    })
    renderRoute('/artifact-errors?offset=50')

    const table = await screen.findByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(51)
    expect(screen.getByText('51–100 of 10000')).toBeInTheDocument()
    expect(mock.mock.calls.map(([path]) => String(path)).filter((path) => path.startsWith('/api/v1/artifact-errors?'))).toEqual([
      '/api/v1/artifact-errors?offset=50&limit=50',
    ])

    await user.click(screen.getByRole('button', { name: 'Next' }))
    expect(await screen.findByText('101–150 of 10000')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Previous' }))
    expect(await screen.findByText('51–100 of 10000')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Search artifact errors'), { target: { value: 'needle' } })
    expect(await screen.findByText('needle-artifact')).toBeInTheDocument()
    expect(screen.getByText('1–1 of 1')).toBeInTheDocument()
    expect(mock.mock.calls.map(([path]) => String(path)).filter((path) => path.startsWith('/api/v1/artifact-errors?'))).toEqual([
      '/api/v1/artifact-errors?offset=50&limit=50',
      '/api/v1/artifact-errors?offset=100&limit=50',
      '/api/v1/artifact-errors?offset=50&limit=50',
      '/api/v1/artifact-errors?offset=0&q=needle&limit=50',
    ])
    expect(screen.queryByRole('button', { name: /show all/i })).not.toBeInTheDocument()
  })

  it('does not let a stale artifact-diagnostics response replace a newer search', async () => {
    const old = deferred<unknown>()
    const mock = mockApi((path) => {
      if (!path.startsWith('/api/v1/artifact-errors?')) throw new Error(`Unexpected path ${path}`)
      const query = new URL(`http://localhost${path}`).searchParams.get('q')
      if (query === 'old') return old.promise
      return { items: [{ code: 'current', message: 'Current diagnostic', artifact_id: 'current-artifact' }], total: 1, offset: 0, limit: 50 }
    })
    renderRoute('/artifact-errors?offset=50&q=old')
    await waitFor(() => expect(mock.mock.calls.map(([path]) => String(path)).filter((path) => path.startsWith('/api/v1/artifact-errors?'))).toEqual([
      '/api/v1/artifact-errors?offset=50&q=old&limit=50',
    ]))
    fireEvent.change(screen.getByLabelText('Search artifact errors'), { target: { value: 'current' } })
    expect(await screen.findByText('current-artifact')).toBeInTheDocument()
    old.resolve({ items: [{ code: 'stale', message: 'Stale diagnostic', artifact_id: 'stale-artifact' }], total: 1, offset: 50, limit: 50 })
    await act(async () => { await old.promise })
    expect(screen.getByText('current-artifact')).toBeInTheDocument()
    expect(screen.queryByText('stale-artifact')).not.toBeInTheDocument()
  })

  it('uses URL-backed server filters for one bounded local namespace page, including source-less errors as unknown', async () => {
    const user = userEvent.setup()
    const sourceLessError = {
      ...namespaces.items[0],
      namespace: 'error-namespace',
      source: null,
      local_status: 'error',
    }
    const mock = mockApi((path) => {
      const parameters = new URL(`http://localhost${path}`).searchParams
      const sourceKind = parameters.get('source_kind')
      const localStatus = parameters.get('local_status')
      const items = [...namespaces.items, sourceLessError].filter((item) => (
        (sourceKind == null || (item.source?.kind ?? 'unknown') === sourceKind)
        && (localStatus == null || item.local_status === localStatus)
      ))
      return { ...namespaces, items, total: items.length, offset: Number(parameters.get('offset') ?? 0), limit: 50 }
    })
    renderRoute('/namespaces?offset=50')
    expect(await screen.findByRole('link', { name: 'docs-one' })).toBeInTheDocument()
    expect(mock.mock.calls.filter(([path]) => String(path).startsWith('/api/v1/namespaces?'))).toHaveLength(1)

    await user.selectOptions(screen.getByLabelText('Local source kind'), 'github_repo')
    expect(await screen.findByRole('link', { name: 'repo-two' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'docs-one' })).not.toBeInTheDocument()
    expect(String(mock.mock.calls.at(-1)?.[0])).toContain('offset=0')
    expect(String(mock.mock.calls.at(-1)?.[0])).toContain('source_kind=github_repo')

    await user.selectOptions(screen.getByLabelText('Local source kind'), 'unknown')
    expect(await screen.findByRole('link', { name: 'error-namespace' })).toBeInTheDocument()
    expect(screen.getByText('Unknown source')).toBeInTheDocument()
    expect(String(mock.mock.calls.at(-1)?.[0])).toContain('source_kind=unknown')

    await user.selectOptions(screen.getByLabelText('Local status'), 'error')
    expect(await screen.findByRole('link', { name: 'error-namespace' })).toBeInTheDocument()
    expect(String(mock.mock.calls.at(-1)?.[0])).toContain('source_kind=unknown')
    expect(String(mock.mock.calls.at(-1)?.[0])).toContain('local_status=error')
    expect(mock.mock.calls.filter(([path]) => String(path).startsWith('/api/v1/namespaces?'))).toHaveLength(4)
  })

  it('restores practical Plans and Namespaces filter history with coalesced text and meaningful select/page entries', async () => {
    const user = userEvent.setup()
    mockApi((path) => {
      if (path.startsWith('/api/v1/plans?')) {
        const parameters = new URL(`http://localhost${path}`).searchParams
        const offset = Number(parameters.get('offset') ?? 0)
        return { items: [{ ...plan, plan_id: `plan-${offset}` }], total: 120, offset, limit: 50, errors: [], error_total: 0, errors_truncated: false }
      }
      if (path.startsWith('/api/v1/namespaces?')) {
        const parameters = new URL(`http://localhost${path}`).searchParams
        const offset = Number(parameters.get('offset') ?? 0)
        const items = Array.from({ length: 50 }, (_, index) => ({ ...namespaces.items[0], namespace: `namespace-${offset + index}` }))
        return { ...namespaces, items, total: 120, offset, limit: 50 }
      }
      throw new Error(`Unexpected path ${path}`)
    })

    const planView = renderRouteWithHistory('/plans?q=old')
    expect(await screen.findByLabelText('Search plans')).toHaveValue('old')
    fireEvent.change(screen.getByLabelText('Search plans'), { target: { value: 'new' } })
    fireEvent.change(screen.getByLabelText('Namespace'), { target: { value: 'docs' } })
    fireEvent.change(screen.getByLabelText('Namespace'), { target: { value: 'docs-current' } })
    await waitFor(() => expect(screen.getByLabelText('Current location')).toHaveTextContent('/plans?q=new&namespace=docs-current'))
    await user.selectOptions(screen.getByLabelText('Source kind'), 'website')
    await waitFor(() => expect(screen.getByLabelText('Current location')).toHaveTextContent('/plans?q=new&namespace=docs-current&source_kind=website'))

    await user.click(screen.getByRole('button', { name: 'Browser back' }))
    await waitFor(() => expect(screen.getByLabelText('Source kind')).toHaveValue('all'))
    expect(screen.getByLabelText('Search plans')).toHaveValue('new')
    expect(screen.getByLabelText('Namespace')).toHaveValue('docs-current')
    await user.click(screen.getByRole('button', { name: 'Browser back' }))
    expect(await screen.findByRole('heading', { name: 'Evidence-backed semantic graphs' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Browser forward' }))
    await waitFor(() => expect(screen.getByLabelText('Namespace')).toHaveValue('docs-current'))
    await user.click(screen.getByRole('button', { name: 'Browser forward' }))
    await waitFor(() => expect(screen.getByLabelText('Source kind')).toHaveValue('website'))
    planView.unmount()

    renderRouteWithHistory('/namespaces?q=old')
    expect(await screen.findByLabelText('Local namespace')).toHaveValue('old')
    fireEvent.change(screen.getByLabelText('Local namespace'), { target: { value: 'new' } })
    fireEvent.change(screen.getByLabelText('Local namespace'), { target: { value: 'newer' } })
    await user.selectOptions(screen.getByLabelText('Local status'), 'applied')
    const pagination = await screen.findByRole('navigation', { name: 'Local namespaces pagination' })
    await user.click(within(pagination).getByRole('button', { name: 'Next' }))
    await waitFor(() => expect(screen.getByLabelText('Current location')).toHaveTextContent('/namespaces?q=newer&local_status=applied&offset=50'))

    await user.click(screen.getByRole('button', { name: 'Browser back' }))
    await waitFor(() => expect(screen.getByLabelText('Current location')).toHaveTextContent('/namespaces?q=newer&local_status=applied'))
    await user.click(screen.getByRole('button', { name: 'Browser back' }))
    await waitFor(() => expect(screen.getByLabelText('Local status')).toHaveValue('all'))
    expect(screen.getByLabelText('Local namespace')).toHaveValue('newer')
    await user.click(screen.getByRole('button', { name: 'Browser back' }))
    expect(await screen.findByRole('heading', { name: 'Evidence-backed semantic graphs' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Browser forward' }))
    await waitFor(() => expect(screen.getByLabelText('Local namespace')).toHaveValue('newer'))
    await user.click(screen.getByRole('button', { name: 'Browser forward' }))
    await waitFor(() => expect(screen.getByLabelText('Local status')).toHaveValue('applied'))
    await user.click(screen.getByRole('button', { name: 'Browser forward' }))
    await waitFor(() => expect(screen.getByLabelText('Current location')).toHaveTextContent('/namespaces?q=newer&local_status=applied&offset=50'))
  })

  it('ignores stale URL-backed inventory responses and keeps one exact current-page request per change', async () => {
    const oldNamespaces = deferred<unknown>()
    const oldPlans = deferred<unknown>()
    const mock = mockApi((path) => {
      const parameters = new URL(`http://localhost${path}`).searchParams
      if (path.startsWith('/api/v1/namespaces?')) {
        if (parameters.get('q') === 'old') return oldNamespaces.promise
        return { ...namespaces, items: [{ ...namespaces.items[0], namespace: 'current-namespace' }], total: 1, offset: 0, limit: 50 }
      }
      if (path.startsWith('/api/v1/plans?')) {
        if (parameters.get('q') === 'old') return oldPlans.promise
        return { items: [{ ...plan, plan_id: 'current-plan' }], total: 1, offset: 0, limit: 50, errors: [], error_total: 0, errors_truncated: false }
      }
      throw new Error(`Unexpected path ${path}`)
    })

    const namespaceView = renderRoute('/namespaces?offset=50&q=old&source_kind=website&local_status=applied')
    await waitFor(() => expect(mock.mock.calls.map(([path]) => String(path)).filter((path) => path.startsWith('/api/v1/namespaces?'))).toEqual([
      '/api/v1/namespaces?offset=50&q=old&source_kind=website&local_status=applied&limit=50',
    ]))
    fireEvent.change(screen.getByLabelText('Local namespace'), { target: { value: 'current' } })
    expect(await screen.findByRole('link', { name: 'current-namespace' })).toBeInTheDocument()
    expect(mock.mock.calls.map(([path]) => String(path)).filter((path) => path.startsWith('/api/v1/namespaces?'))).toEqual([
      '/api/v1/namespaces?offset=50&q=old&source_kind=website&local_status=applied&limit=50',
      '/api/v1/namespaces?offset=0&q=current&source_kind=website&local_status=applied&limit=50',
    ])
    oldNamespaces.resolve({ ...namespaces, items: [{ ...namespaces.items[0], namespace: 'stale-namespace' }], total: 1, offset: 50, limit: 50 })
    await act(async () => { await oldNamespaces.promise })
    expect(screen.getByRole('link', { name: 'current-namespace' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'stale-namespace' })).not.toBeInTheDocument()
    namespaceView.unmount()

    renderRoute('/plans?offset=50&q=old&namespace=docs-one&source_kind=website')
    await waitFor(() => expect(mock.mock.calls.map(([path]) => String(path)).filter((path) => path.startsWith('/api/v1/plans?'))).toEqual([
      '/api/v1/plans?offset=50&q=old&namespace=docs-one&source_kind=website&limit=50',
    ]))
    fireEvent.change(screen.getByLabelText('Search plans'), { target: { value: 'current' } })
    expect(await screen.findByRole('link', { name: 'current-plan' })).toBeInTheDocument()
    expect(mock.mock.calls.map(([path]) => String(path)).filter((path) => path.startsWith('/api/v1/plans?'))).toEqual([
      '/api/v1/plans?offset=50&q=old&namespace=docs-one&source_kind=website&limit=50',
      '/api/v1/plans?offset=0&q=current&namespace=docs-one&source_kind=website&limit=50',
    ])
    oldPlans.resolve({ items: [{ ...plan, plan_id: 'stale-plan' }], total: 1, offset: 50, limit: 50, errors: [], error_total: 0, errors_truncated: false })
    await act(async () => { await oldPlans.promise })
    expect(screen.getByRole('link', { name: 'current-plan' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'stale-plan' })).not.toBeInTheDocument()
  })

  it('enriches only matching current local rows from an explicit remote snapshot', async () => {
    const user = userEvent.setup()
    mockApi((path) => path.includes('/dashboard') ? dashboard : path.includes('/remote/snapshot') ? remote : path.includes('/namespaces/docs-one?') ? {
      summary: namespaces.items[0], plans: [plan], state: null, retrieval: null,
    } : namespaces)
    renderRoute('/')
    await screen.findByText('plan-1')
    await user.click(screen.getByRole('button', { name: 'Refresh remote status' }))
    await user.click(screen.getByRole('link', { name: 'Namespaces' }))
    const docsRow = await screen.findByRole('row', { name: /docs-one/ })
    expect(within(docsRow).getByText('eligible')).toBeInTheDocument()
    expect(within(docsRow).getByText('Yes')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Remote namespaces without a local snapshot' })).toBeInTheDocument()
    expect(screen.getByText(/No remote-only namespaces match/)).toBeInTheDocument()
    await user.click(within(docsRow).getByRole('link', { name: 'docs-one' }))
    expect(await screen.findByRole('heading', { name: 'docs-one' })).toBeInTheDocument()
    expect(screen.getByText('Remote status').nextElementSibling).toHaveTextContent('eligible')
    expect(screen.getByText('Catalog status').nextElementSibling).toHaveTextContent('Present')
  })

  it('renders and filters a checked remote row with unknown catalog presence as not checked', async () => {
    const user = userEvent.setup()
    const nullableCatalogRemote = {
      ...remote,
      namespaces: remote.namespaces.map((item) => item.namespace === 'docs-one'
        ? { ...item, status: 'not_checked', card_present: null }
        : item),
    }
    mockApi((path) => path.includes('/dashboard') ? dashboard : path.includes('/remote/snapshot') ? nullableCatalogRemote : namespaces)
    renderRoute('/')
    await screen.findByText('plan-1')
    await user.click(screen.getByRole('button', { name: 'Refresh remote status' }))
    await screen.findByText(/Remote status: ready/i)
    await user.click(screen.getByRole('link', { name: 'Namespaces' }))

    const row = await screen.findByRole('row', { name: /docs-one/ })
    expect(within(row).getByText('Not checked')).toBeInTheDocument()
    expect(screen.queryByLabelText('Catalog card')).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Remote-only catalog card'), 'not-checked')
    expect(screen.getByRole('link', { name: 'docs-one' })).toBeInTheDocument()
  })

  it('renders namespace detail, provenance, retrieval, plans, search entry, and graph placeholder', async () => {
    mockApi(() => ({
      summary: namespaces.items[0],
      plans: [plan],
      state: { namespace: 'docs-one', site_id: 'example-test', source, updated_at: '2026-07-23T13:00:00Z', last_plan_id: 'plan-1', last_apply_id: 'apply-1', active_rows: 8, retained_stale_rows: 1 },
      retrieval: { embedding_model: 'BAAI/bge-small-en-v1.5', embedding_precision: 'float32', ranking_mode: 'page', ranking_profile: 'none', ranking_pool: 25, ranking_aggregation: 'max', region: 'aws-us-east-1' },
    }))
    renderRoute('/namespaces/docs-one')
    expect(await screen.findByRole('heading', { name: 'docs-one' })).toBeInTheDocument()
    expect(screen.getByText('Safe source provenance')).toBeInTheDocument()
    expect(screen.getByText('BAAI/bge-small-en-v1.5')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Search this namespace' })).toHaveAttribute('href', '/search?namespace=docs-one')
    expect(screen.getByText('Evidence-backed semantic graph')).toBeInTheDocument()
    expect(screen.getByText('No knowledge graph has been built for this namespace.')).toBeInTheDocument()
    expect(screen.getAllByText('Retained stale rows').length).toBeGreaterThan(0)
    expect(screen.getByText('Documents / pages')).toBeInTheDocument()
    expect(screen.getByText('Retrieval region')).toBeInTheDocument()
    expect(screen.getByText('aws-us-east-1')).toBeInTheDocument()
    for (const label of ['Latest plan', 'Latest apply', 'Planned upserts', 'Planned stale', 'Chunks']) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
  })

  it('describes duplicate applied-state identity conflicts without claiming no state exists', async () => {
    mockApi(() => ({
      summary: {
        ...namespaces.items[0],
        active_rows: null,
        last_apply_id: null,
        local_status: 'conflict',
        retained_stale_rows: null,
        warnings: [{ code: 'namespace_identity_conflict', message: 'Multiple local identities claim this namespace; applied counts are unknown.' }],
      },
      plans: [plan],
      state: null,
      retrieval: null,
    }))
    renderRoute('/namespaces/docs-one')

    expect(await screen.findByText(/Multiple applied-state identities claim this namespace/)).toBeInTheDocument()
    expect(screen.getByText(/row counts and last-apply details are unknown/)).toBeInTheDocument()
    expect(screen.queryByText(/No applied state is present/)).not.toBeInTheDocument()
  })

  it('requests bounded namespace history and links truncated history to its URL-backed plan filter', async () => {
    const history = Array.from({ length: 20 }, (_, index) => ({ ...plan, plan_id: `history-${index}` }))
    const mock = mockApi(() => ({
      summary: namespaces.items[0],
      plans: history,
      plan_total: 21,
      plan_offset: 0,
      plan_limit: 20,
      plans_truncated: true,
      state: null,
      retrieval: null,
    }))
    renderRoute('/namespaces/docs-one')
    expect(await screen.findByText('1–20 of 21')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'View all plans for this namespace' })).toHaveAttribute('href', '/plans?namespace=docs-one')
    expect(mock.mock.calls.map(([path]) => String(path)).filter((path) => path.includes('/namespaces/docs-one'))).toEqual([
      '/api/v1/namespaces/docs-one?plan_offset=0&plan_limit=20',
    ])
    expect(screen.getAllByRole('link', { name: /^history-/ })).toHaveLength(20)
  })

  it('renders deterministic plan history metadata and an empty plan state', async () => {
    mockApi(() => ({ items: [plan], total: 1, offset: 0, limit: 100, errors: [], error_total: 0, errors_truncated: false }))
    const view = renderRoute('/plans')
    expect(await screen.findByRole('link', { name: 'plan-1' })).toBeInTheDocument()
    expect(within(screen.getByRole('row', { name: /plan-1/ })).getByText('Website')).toBeInTheDocument()
    expect(screen.getByText('6')).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'First apply' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Source credentials' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Source API calls' })).toBeInTheDocument()

    view.unmount()
    mockApi(() => ({ items: [], total: 0, offset: 0, limit: 100, errors: [], error_total: 0, errors_truncated: false }))
    renderRoute('/plans')
    expect(await screen.findByText(/No saved plans match/)).toBeInTheDocument()
  })

  it('renders verified plan provenance, warehouse notice, bounded deltas, and escaped content', async () => {
    const warehousePlan: PlanSummary = { ...plan, source: { ...source, kind: 'database', uri: 'bigquery://warehouse', title: 'warehouse (docs)', database_backend: 'bigquery', database_source_id: 'warehouse', database_relation: 'dataset.docs' } }
    mockApi((path) => {
      const offset = Number(new URL(`http://localhost${path}`).searchParams.get('offset') ?? 0)
      const detail = detailFor(warehousePlan, { retrieval: { embedding_model: 'model', embedding_precision: 'float32', ranking_mode: 'page', ranking_profile: 'none', ranking_pool: 25, ranking_aggregation: 'max' }, source_activity: { credentials_required: true, api_calls_occurred: true } })
      const chunks = chunksAt(offset, 12, [{ index: offset, action: 'changed', row_id: `row-${offset}`, title: 'Chunk title', canonical_url: 'https://example.test/page', section_path: 'Intro', chunk_index: offset, content: '<img src=x onerror=alert(1)>', truncated: false }])
      const staleRows = staleAt(0, 1, [{ index: 0, category: 'stale', row_id: 'stale-row', canonical_url: 'https://example.test/old', prior_status: 'active', reason: 'not_in_desired_source' }])
      if (path.includes('/review?')) return reviewFor(detail, chunks, staleRows)
      if (path.includes('/chunks')) return chunks
      throw new Error(`Unexpected path ${path}`)
    })
    renderRoute('/plans/plan-1')
    expect(await screen.findByText(/reviewed without reconnecting to the source warehouse/i)).toBeInTheDocument()
    expect(screen.getByText(/Read-only review/)).toBeInTheDocument()
    expect(screen.getByText('verified')).toBeInTheDocument()
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeInTheDocument()
    expect(screen.getByText('stale-row')).toBeInTheDocument()
    expect(document.querySelector('img[src="x"]')).toBeNull()
    const next = screen.getByRole('button', { name: 'Next chunks' })
    expect(next).toBeEnabled()
    await userEvent.click(next)
    expect(await screen.findByText('11–11 of 12')).toBeInTheDocument()
  })

  it('validates explicit search before performing remote activity', async () => {
    const user = userEvent.setup()
    const mock = mockApi(() => { throw new Error('should not run') })
    renderRoute('/search')
    await user.click(screen.getByLabelText('Explicit namespaces'))
    await user.type(screen.getByLabelText('Query'), 'How does it work?')
    await user.click(screen.getByRole('button', { name: 'Run search' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Enter at least one explicit namespace')
    expect(mock.mock.calls.every(([path]) => String(path).includes('/capabilities'))).toBe(true)
  })

  it('submits bounded explicit search and renders escaped citation-rich results with activity disclosure', async () => {
    const user = userEvent.setup()
    const mock = mockApi((_path, init) => {
      const payload = JSON.parse(String(init?.body))
      expect(payload).toMatchObject({ query: 'anchors', automatic: false, namespaces: ['docs-one', 'repo-two'], top_k: 5, candidates: 200 })
      return {
        state: 'success', credentials_required: true, api_calls_occurred: true, writes_occurred: false, automatic: false,
        namespaces: ['docs-one', 'repo-two'], diagnostics: { fusion: 'rrf' }, error: null,
        hits: [{ namespace: 'docs-one', title: 'Anchored answer', citation: 'https://example.test/citation', section: 'Safety', content_preview: '<script>not executable</script>', content_truncated: false, tags: ['docs'], score: { rank: 1 } }],
      }
    })
    renderRoute('/search')
    await user.click(screen.getByLabelText('Explicit namespaces'))
    await user.type(screen.getByLabelText('Query'), 'anchors')
    await user.type(screen.getByLabelText(/^Namespaces/), 'docs-one, repo-two')
    await user.click(screen.getByRole('button', { name: 'Run search' }))

    expect(await screen.findByRole('heading', { name: 'Anchored answer' })).toBeInTheDocument()
    expect(screen.getByText('<script>not executable</script>')).toBeInTheDocument()
    expect(document.querySelector('script')).toBeNull()
    expect(screen.getByRole('link', { name: /https:\/\/example.test\/citation/ })).toHaveAttribute('rel', 'noreferrer')
    expect(screen.getByText(/Routing: Explicit\. Credentials required: Yes\. API calls occurred: Yes\. Writes occurred: No/)).toBeInTheDocument()
    expect(screen.getByLabelText('Search diagnostics')).toHaveTextContent('"fusion": "rrf"')
    expect(screen.getByLabelText('Score for Anchored answer')).toHaveTextContent('"rank": 1')
    const searchCall = mock.mock.calls.find(([path]) => String(path).includes('/search'))
    expect(searchCall?.[1]?.headers).toMatchObject({ 'X-Buoy-Command-Center': '1' })
    expect(mock).toHaveBeenCalledTimes(2)
  })

  it('shows a missing-credentials search failure with accurate no-call activity', async () => {
    const user = userEvent.setup()
    mockApi(() => ({ state: 'error', credentials_required: true, api_calls_occurred: false, writes_occurred: false, automatic: true, namespaces: [], hits: [], diagnostics: {}, error: { code: 'remote_credentials_missing', message: 'Remote search is not configured for this process.', details: { phase: 'credentials' } } }))
    renderRoute('/search')
    await user.type(screen.getByLabelText('Query'), 'anchors')
    await user.click(screen.getByRole('button', { name: 'Run search' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Remote search is not configured')
    expect(screen.getByText(/API calls occurred: No\. Writes occurred: No/)).toBeInTheDocument()
  })

  it('merges remote-only namespaces into inventory without inventing local detail', async () => {
    const user = userEvent.setup()
    const remoteOnly = {
      ...remote,
      namespace_total: 3,
      namespaces: [...remote.namespaces, { namespace: 'remote-three', local_present: false, live: true, card_present: true, status: 'eligible', title: 'Remote docs', source_kind: 'website', tags: ['remote'] }],
    }
    mockApi((path) => path.includes('/dashboard') ? dashboard : path.includes('/remote/snapshot') ? remoteOnly : namespaces)
    renderRoute('/')
    await screen.findByText('plan-1')
    await user.click(screen.getByRole('button', { name: 'Refresh remote status' }))
    await user.click(screen.getByRole('link', { name: 'Namespaces' }))
    expect(await screen.findByText('remote-three')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Remote namespaces without a local snapshot' })).toBeInTheDocument()
    expect(screen.queryByText('No local snapshot')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'remote-three' })).not.toBeInTheDocument()
    expect(screen.getByText(/Remote docs/)).toBeInTheDocument()
  })

  it('paginates the accurately scoped remote-only section independently of local requests', async () => {
    const user = userEvent.setup()
    const remoteOnlyItems = Array.from({ length: 120 }, (_, index) => ({
      namespace: `remote-${String(index).padStart(3, '0')}`,
      local_present: false,
      live: true,
      card_present: true,
      status: 'eligible' as const,
      title: `Remote ${index}`,
      source_kind: 'website',
      tags: ['remote'],
    }))
    const snapshot = {
      ...remote,
      namespaces: [
        { ...remote.namespaces[0], local_present: false, status: 'missing_card' as const, card_present: false },
        ...remoteOnlyItems,
      ],
      namespace_total: 121,
    }
    const mock = mockApi((path) => path.includes('/dashboard') ? dashboard : path.includes('/remote/snapshot') ? snapshot : namespaces)
    renderRoute('/')
    await screen.findByText('plan-1')
    await user.click(screen.getByRole('button', { name: 'Refresh remote status' }))
    await user.click(screen.getByRole('link', { name: 'Namespaces' }))

    const localTable = await screen.findByLabelText('2 current-page local namespaces of 2')
    expect(within(localTable).getByRole('row', { name: /docs-one/ })).toHaveTextContent('not checked')
    const localPagination = screen.getByRole('navigation', { name: 'Local namespaces pagination' })
    const remotePagination = screen.getByRole('navigation', { name: 'Remote-only namespaces pagination' })
    expect(within(localPagination).getByRole('button', { name: 'Next' })).toBeDisabled()
    expect(within(remotePagination).getByRole('button', { name: 'Next' })).toBeEnabled()
    const remoteTable = screen.getByLabelText('50 current-page remote-only namespaces')
    expect(within(remoteTable).getAllByRole('row')).toHaveLength(51)
    expect(screen.getByText('remote-000')).toBeInTheDocument()
    expect(screen.queryByText('remote-119')).not.toBeInTheDocument()
    expect(mock.mock.calls.filter(([path]) => String(path).startsWith('/api/v1/namespaces?'))).toHaveLength(1)

    await user.click(within(remotePagination).getByRole('button', { name: 'Next' }))
    expect(screen.getByText('remote-050')).toBeInTheDocument()
    expect(screen.queryByText('remote-000')).not.toBeInTheDocument()
    expect(within(localTable).getByRole('link', { name: 'docs-one' })).toBeInTheDocument()
    expect(mock.mock.calls.filter(([path]) => String(path).startsWith('/api/v1/namespaces?'))).toHaveLength(1)

    fireEvent.change(screen.getByLabelText('Remote-only namespace'), { target: { value: 'remote-119' } })
    expect(screen.getByText('remote-119')).toBeInTheDocument()
    expect(screen.getByText('1–1 of 1')).toBeInTheDocument()
    expect(mock.mock.calls.filter(([path]) => String(path).startsWith('/api/v1/namespaces?'))).toHaveLength(1)
  })

  it('marks a failed latest refresh as failed and discloses snapshot truncation', async () => {
    const user = userEvent.setup()
    let refreshes = 0
    mockApi((path) => {
      if (path.includes('/dashboard')) return dashboard
      refreshes += 1
      if (refreshes === 1) return { ...remote, namespaces_truncated: true, namespace_total: 1001 }
      throw new Error('transport failed')
    })
    renderRoute('/')
    await screen.findByText('plan-1')
    await user.click(screen.getByRole('button', { name: 'Refresh remote status' }))
    expect(await screen.findByText(/Showing 2 of 1001 namespaces; snapshot truncated/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Refresh remote status' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Latest refresh failed')
    expect(screen.queryByText(/Remote status: ready/i)).not.toBeInTheDocument()
  })

  it('renders only one 50-row inventory page and makes one focused request per transition', async () => {
    const namespaceItems = Array.from({ length: 1_000 }, (_, index) => ({ ...namespaces.items[0], namespace: `namespace-${index}` }))
    const planItems = Array.from({ length: 1_000 }, (_, index) => ({ ...plan, plan_id: `plan-${index}` }))
    const mock = mockApi((path) => {
      const offset = Number(new URL(`http://localhost${path}`).searchParams.get('offset') ?? 0)
      if (path.startsWith('/api/v1/namespaces?')) return { ...namespaces, items: namespaceItems.slice(offset, offset + 50), total: 1_000, offset, limit: 50 }
      if (path.startsWith('/api/v1/plans?')) return { items: planItems.slice(offset, offset + 50), total: 1_000, offset, limit: 50, errors: [], error_total: 0, errors_truncated: false }
      const detail = detailFor({ ...plan, plan_id: 'plan-many' })
      const chunks = chunksAt(offset, 11, [{ index: offset, action: 'changed', row_id: `row-${offset}`, title: `Changed ${offset + 1}`, canonical_url: 'https://example.test/page', section_path: 'Intro', chunk_index: offset, content: `changed ${offset + 1}`, truncated: false }])
      const staleRows = staleAt(offset, 11, [{ index: offset, category: 'stale', row_id: `stale-${offset}`, canonical_url: 'https://example.test/old', prior_status: 'active', reason: 'not_in_desired_source' }])
      if (path.includes('/plans/plan-many/review?')) return reviewFor(detail, chunksAt(0, 11, [{ index: 0, action: 'changed', row_id: 'row-0', title: 'Changed 1', canonical_url: 'https://example.test/page', section_path: 'Intro', chunk_index: 0, content: 'changed 1', truncated: false }]), staleAt(0, 11, [{ index: 0, category: 'stale', row_id: 'stale-0', canonical_url: 'https://example.test/old', prior_status: 'active', reason: 'not_in_desired_source' }]))
      if (path.includes('/plans/plan-many/chunks')) return chunks
      if (path.includes('/plans/plan-many/stale-rows')) return staleRows
      throw new Error(`Unexpected path ${path}`)
    })

    const namespaceView = renderRoute('/namespaces')
    expect(await screen.findByRole('link', { name: 'namespace-0' })).toBeInTheDocument()
    expect(screen.getByLabelText('50 current-page local namespaces of 1000')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'namespace-999' })).not.toBeInTheDocument()
    expect(mock.mock.calls.map(([path]) => String(path)).filter((path) => path.startsWith('/api/v1/namespaces?'))).toEqual(['/api/v1/namespaces?offset=0&limit=50'])
    await userEvent.click(within(screen.getByRole('navigation', { name: 'Local namespaces pagination' })).getByRole('button', { name: 'Next' }))
    expect(await screen.findByRole('link', { name: 'namespace-50' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'namespace-0' })).not.toBeInTheDocument()
    expect(mock.mock.calls.map(([path]) => String(path)).filter((path) => path.startsWith('/api/v1/namespaces?'))).toEqual(['/api/v1/namespaces?offset=0&limit=50', '/api/v1/namespaces?offset=50&limit=50'])
    namespaceView.unmount()

    const planView = renderRoute('/plans')
    expect(await screen.findByRole('link', { name: 'plan-0' })).toBeInTheDocument()
    expect(screen.getByLabelText('50 current-page plans of 1000')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'plan-999' })).not.toBeInTheDocument()
    expect(mock.mock.calls.map(([path]) => String(path)).filter((path) => path.startsWith('/api/v1/plans?'))).toEqual(['/api/v1/plans?offset=0&limit=50'])
    await userEvent.click(within(screen.getByRole('navigation', { name: 'Plans pagination' })).getByRole('button', { name: 'Next' }))
    expect(await screen.findByRole('link', { name: 'plan-50' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'plan-0' })).not.toBeInTheDocument()
    planView.unmount()

    mock.mockClear()
    const reviewPaths = () => mock.mock.calls.map(([path]) => String(path)).filter((path) => path.startsWith('/api/v1/plans/plan-many'))
    renderRoute('/plans/plan-many')
    expect(await screen.findByText('changed 1')).toBeInTheDocument()
    expect(screen.getByText('stale-0')).toBeInTheDocument()
    expect(reviewPaths()).toEqual(['/api/v1/plans/plan-many/review?chunk_offset=0&chunk_limit=10&max_chars=2000&stale_offset=0&stale_limit=10'])
    mock.mockClear()
    await userEvent.click(screen.getByRole('button', { name: 'Next chunks' }))
    expect(await screen.findByText('changed 11')).toBeInTheDocument()
    expect(screen.getByText('stale-0')).toBeInTheDocument()
    expect(reviewPaths()).toEqual(['/api/v1/plans/plan-many/chunks?offset=10&limit=10&max_chars=2000'])
    mock.mockClear()
    await userEvent.click(screen.getByRole('button', { name: 'Next stale rows' }))
    expect(await screen.findByText('stale-10')).toBeInTheDocument()
    expect(screen.getByText('changed 11')).toBeInTheDocument()
    expect(reviewPaths()).toEqual(['/api/v1/plans/plan-many/stale-rows?offset=10&limit=10'])
  })

  it('retries a failed initial plan load with only the same combined review request', async () => {
    let reviews = 0
    const mock = mockApi((path) => {
      if (!path.includes('/plans/plan-1/review?')) throw new Error(`Unexpected path ${path}`)
      reviews += 1
      return reviews === 1
        ? json({ error: { code: 'review_failed', message: 'Combined review failed.' } }, 500)
        : reviewFor(detailFor(), chunksAt(0, 1, [{ index: 0, action: 'changed', row_id: 'recovered', title: 'Recovered', canonical_url: '', section_path: '', chunk_index: 0, content: 'recovered combined content', truncated: false }]))
    })
    renderRoute('/plans/plan-1')
    expect(await screen.findByRole('alert')).toHaveTextContent('Combined review failed.')
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('recovered combined content')).toBeInTheDocument()
    expect(mock.mock.calls.map(([path]) => String(path)).filter((path) => path.includes('/plans/plan-1'))).toEqual([
      '/api/v1/plans/plan-1/review?chunk_offset=0&chunk_limit=10&max_chars=2000&stale_offset=0&stale_limit=10',
      '/api/v1/plans/plan-1/review?chunk_offset=0&chunk_limit=10&max_chars=2000&stale_offset=0&stale_limit=10',
    ])
  })

  it('keeps detail and unaffected review sections visible through focused errors and exact retries', async () => {
    let chunkRequests = 0
    let staleRequests = 0
    const mock = mockApi((path) => {
      if (path.includes('/plans/plan-1/review?')) return reviewFor(
        detailFor(),
        chunksAt(0, 11, [{ index: 0, action: 'changed', row_id: 'chunk-zero', title: 'Initial chunk', canonical_url: '', section_path: '', chunk_index: 0, content: 'initial chunk content', truncated: false }]),
        staleAt(0, 11, [{ index: 0, category: 'stale', row_id: 'stale-zero', canonical_url: '', prior_status: 'active', reason: 'not_in_desired_source' }]),
      )
      if (path.includes('/chunks?offset=10')) {
        chunkRequests += 1
        return chunkRequests === 1
          ? json({ error: { code: 'chunk_failed', message: 'Changed chunk page failed.' } }, 500)
          : chunksAt(10, 11, [{ index: 10, action: 'changed', row_id: 'chunk-ten', title: 'Retried chunk', canonical_url: '', section_path: '', chunk_index: 10, content: 'retried chunk content', truncated: false }])
      }
      if (path.includes('/stale-rows?offset=10')) {
        staleRequests += 1
        return staleRequests === 1
          ? json({ error: { code: 'stale_failed', message: 'Stale row page failed.' } }, 500)
          : staleAt(10, 11, [{ index: 10, category: 'stale', row_id: 'stale-ten', canonical_url: '', prior_status: 'active', reason: 'not_in_desired_source' }])
      }
      throw new Error(`Unexpected path ${path}`)
    })
    renderRoute('/plans/plan-1')
    expect(await screen.findByText('initial chunk content')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Next chunks' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Changed chunk page failed.')
    expect(screen.getByRole('heading', { name: 'plan-1' })).toBeInTheDocument()
    expect(screen.getByText('initial chunk content')).toBeInTheDocument()
    expect(screen.getByText('stale-zero')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Retry this section' }))
    expect(await screen.findByText('retried chunk content')).toBeInTheDocument()
    expect(screen.queryByText('Changed chunk page failed.')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Next stale rows' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Stale row page failed.')
    expect(screen.getByText('retried chunk content')).toBeInTheDocument()
    expect(screen.getByText('stale-zero')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Retry this section' }))
    expect(await screen.findByText('stale-ten')).toBeInTheDocument()

    expect(mock.mock.calls.map(([path]) => String(path)).filter((path) => path.includes('/plans/plan-1'))).toEqual([
      '/api/v1/plans/plan-1/review?chunk_offset=0&chunk_limit=10&max_chars=2000&stale_offset=0&stale_limit=10',
      '/api/v1/plans/plan-1/chunks?offset=10&limit=10&max_chars=2000',
      '/api/v1/plans/plan-1/chunks?offset=10&limit=10&max_chars=2000',
      '/api/v1/plans/plan-1/stale-rows?offset=10&limit=10',
      '/api/v1/plans/plan-1/stale-rows?offset=10&limit=10',
    ])
  })

  it('accepts only one rapid focused request and cross-disables chunk and stale pagination', async () => {
    const focusedChunks = deferred<unknown>()
    const mock = mockApi((path) => {
      if (path.includes('/review?')) return reviewFor(
        detailFor(),
        chunksAt(0, 11, [{ index: 0, action: 'changed', row_id: 'initial-chunk', title: 'Initial chunk', canonical_url: '', section_path: '', chunk_index: 0, content: 'initial chunk window', truncated: false }]),
        staleAt(0, 11, [{ index: 0, category: 'stale', row_id: 'initial-stale', canonical_url: '', prior_status: 'active', reason: 'not_in_desired_source' }]),
      )
      if (path.includes('/chunks?offset=10')) return focusedChunks.promise
      if (path.includes('/stale-rows')) throw new Error('A stale request must not be accepted while chunks are loading.')
      throw new Error(`Unexpected path ${path}`)
    })
    renderRoute('/plans/plan-1')
    expect(await screen.findByText('initial chunk window')).toBeInTheDocument()

    const previousChunks = screen.getByRole('button', { name: 'Previous chunks' })
    const nextChunks = screen.getByRole('button', { name: 'Next chunks' })
    const previousStale = screen.getByRole('button', { name: 'Previous stale rows' })
    const nextStale = screen.getByRole('button', { name: 'Next stale rows' })
    act(() => {
      nextChunks.dispatchEvent(new MouseEvent('click', { bubbles: true }))
      nextChunks.dispatchEvent(new MouseEvent('click', { bubbles: true }))
      nextStale.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })

    expect(screen.getByRole('status')).toHaveTextContent('Loading changed chunks')
    for (const control of [previousChunks, nextChunks, previousStale, nextStale]) expect(control).toBeDisabled()
    expect(screen.getByRole('heading', { name: 'plan-1' })).toBeInTheDocument()
    expect(screen.getByText('initial chunk window')).toBeInTheDocument()
    expect(screen.getByText('initial-stale')).toBeInTheDocument()
    expect(mock.mock.calls.filter(([path]) => String(path).includes('/chunks?'))).toHaveLength(1)
    expect(mock.mock.calls.filter(([path]) => String(path).includes('/stale-rows?'))).toHaveLength(0)

    focusedChunks.resolve(chunksAt(10, 11, [{ index: 10, action: 'changed', row_id: 'chunk-ten', title: 'Accepted chunk', canonical_url: '', section_path: '', chunk_index: 10, content: 'accepted chunk window', truncated: false }]))
    expect(await screen.findByText('accepted chunk window')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Previous chunks' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Next stale rows' })).toBeEnabled()
  })

  it('cross-disables focused retry, clears the guard after failure, and accepts one later request', async () => {
    const focusedStale = deferred<unknown>()
    const retriedChunks = deferred<unknown>()
    let chunkRequests = 0
    let staleRequests = 0
    const mock = mockApi((path) => {
      if (path.includes('/review?')) return reviewFor(
        detailFor(),
        chunksAt(0, 11, [{ index: 0, action: 'changed', row_id: 'initial-chunk', title: 'Initial chunk', canonical_url: '', section_path: '', chunk_index: 0, content: 'initial chunk window', truncated: false }]),
        staleAt(0, 11, [{ index: 0, category: 'stale', row_id: 'initial-stale', canonical_url: '', prior_status: 'active', reason: 'not_in_desired_source' }]),
      )
      if (path.includes('/chunks?offset=10')) {
        chunkRequests += 1
        return chunkRequests === 1
          ? json({ error: { code: 'chunk_failed', message: 'Changed chunk page failed.' } }, 500)
          : retriedChunks.promise
      }
      if (path.includes('/stale-rows?offset=10')) {
        staleRequests += 1
        return focusedStale.promise
      }
      if (path.includes('/stale-rows?offset=0')) {
        staleRequests += 1
        return staleAt(0, 11, [{ index: 0, category: 'stale', row_id: 'returned-stale', canonical_url: '', prior_status: 'active', reason: 'not_in_desired_source' }])
      }
      throw new Error(`Unexpected path ${path}`)
    })
    renderRoute('/plans/plan-1')
    expect(await screen.findByText('initial chunk window')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Next chunks' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Changed chunk page failed.')
    const retry = screen.getByRole('button', { name: 'Retry this section' })
    expect(retry).toBeEnabled()

    await userEvent.click(screen.getByRole('button', { name: 'Next stale rows' }))
    expect(screen.getByRole('status')).toHaveTextContent('Loading stale rows')
    expect(retry).toBeDisabled()
    for (const name of ['Previous chunks', 'Next chunks', 'Previous stale rows', 'Next stale rows']) {
      expect(screen.getByRole('button', { name })).toBeDisabled()
    }
    expect(screen.getByRole('heading', { name: 'plan-1' })).toBeInTheDocument()
    expect(screen.getByText('initial chunk window')).toBeInTheDocument()
    expect(screen.getByText('initial-stale')).toBeInTheDocument()
    fireEvent.click(retry)
    expect(chunkRequests).toBe(1)
    expect(staleRequests).toBe(1)

    focusedStale.resolve(staleAt(10, 11, [{ index: 10, category: 'stale', row_id: 'accepted-stale', canonical_url: '', prior_status: 'active', reason: 'not_in_desired_source' }]))
    expect(await screen.findByText('accepted-stale')).toBeInTheDocument()
    expect(retry).toBeEnabled()

    act(() => {
      retry.dispatchEvent(new MouseEvent('click', { bubbles: true }))
      retry.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    })
    expect(screen.getByRole('status')).toHaveTextContent('Loading changed chunks')
    expect(chunkRequests).toBe(2)
    expect(staleRequests).toBe(1)
    retriedChunks.resolve(chunksAt(10, 11, [{ index: 10, action: 'changed', row_id: 'retried-chunk', title: 'Retried chunk', canonical_url: '', section_path: '', chunk_index: 10, content: 'retried chunk window', truncated: false }]))
    expect(await screen.findByText('retried chunk window')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Previous stale rows' }))
    expect(await screen.findByText('returned-stale')).toBeInTheDocument()
    expect(chunkRequests).toBe(2)
    expect(staleRequests).toBe(2)
  })

  it('invalidates a focused request on plan-ID change, clears the guard, and rejects old results', async () => {
    const oldFocused = deferred<unknown>()
    const newFocused = deferred<unknown>()
    const mock = mockApi((path) => {
      if (path.includes('/plans/plan-1/review?')) return reviewFor(
        detailFor(),
        chunksAt(0, 11, [{ index: 0, action: 'changed', row_id: 'plan-one-chunk', title: 'Plan one', canonical_url: '', section_path: '', chunk_index: 0, content: 'plan one chunk zero', truncated: false }]),
        staleAt(0, 11, [{ index: 0, category: 'stale', row_id: 'plan-one-stale', canonical_url: '', prior_status: 'active', reason: 'not_in_desired_source' }]),
      )
      if (path.includes('/plans/plan-1/chunks?offset=10')) return oldFocused.promise
      if (path.includes('/plans/plan-2/review?')) return reviewFor(
        detailFor({ ...plan, plan_id: 'plan-2' }),
        chunksAt(0, 11, [{ index: 0, action: 'changed', row_id: 'plan-two-chunk', title: 'Plan two', canonical_url: '', section_path: '', chunk_index: 0, content: 'plan two chunk zero', truncated: false }]),
        staleAt(0, 11, [{ index: 0, category: 'stale', row_id: 'plan-two-stale', canonical_url: '', prior_status: 'active', reason: 'not_in_desired_source' }]),
      )
      if (path.includes('/plans/plan-2/chunks?offset=10')) return newFocused.promise
      throw new Error(`Unexpected path ${path}`)
    })
    renderRouteWithLink('/plans/plan-1', '/plans/plan-2')
    expect(await screen.findByText('plan one chunk zero')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Next chunks' }))
    expect(screen.getByRole('status')).toHaveTextContent('Loading changed chunks')
    await userEvent.click(screen.getByRole('link', { name: 'Test route change' }))
    expect(await screen.findByText('plan two chunk zero')).toBeInTheDocument()
    expect(screen.getByText('plan-two-stale')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next chunks' })).toBeEnabled()

    await userEvent.click(screen.getByRole('button', { name: 'Next chunks' }))
    expect(screen.getByRole('status')).toHaveTextContent('Loading changed chunks')
    expect(mock.mock.calls.filter(([path]) => String(path).includes('/plans/plan-2/chunks?'))).toHaveLength(1)
    newFocused.resolve(chunksAt(10, 11, [{ index: 10, action: 'changed', row_id: 'new-focused', title: 'New focused', canonical_url: '', section_path: '', chunk_index: 10, content: 'new focused plan-two content', truncated: false }]))
    expect(await screen.findByText('new focused plan-two content')).toBeInTheDocument()

    oldFocused.resolve(chunksAt(10, 11, [{ index: 10, action: 'changed', row_id: 'old-focused', title: 'Old focused', canonical_url: '', section_path: '', chunk_index: 10, content: 'old focused plan-one content', truncated: false }]))
    await act(async () => { await oldFocused.promise })
    expect(screen.getByText('new focused plan-two content')).toBeInTheDocument()
    expect(screen.queryByText('old focused plan-one content')).not.toBeInTheDocument()
    expect(mock.mock.calls.map(([path]) => String(path)).filter((path) => path.includes('/plans/'))).toEqual([
      '/api/v1/plans/plan-1/review?chunk_offset=0&chunk_limit=10&max_chars=2000&stale_offset=0&stale_limit=10',
      '/api/v1/plans/plan-1/chunks?offset=10&limit=10&max_chars=2000',
      '/api/v1/plans/plan-2/review?chunk_offset=0&chunk_limit=10&max_chars=2000&stale_offset=0&stale_limit=10',
      '/api/v1/plans/plan-2/chunks?offset=10&limit=10&max_chars=2000',
    ])
  })

  it('ignores an old combined review after the plan route changes and resets windows', async () => {
    const oldReview = deferred<unknown>()
    mockApi((path) => {
      if (path.includes('/plans/plan-1/review?')) return oldReview.promise
      if (path.includes('/plans/plan-2/review?')) return reviewFor(
        detailFor({ ...plan, plan_id: 'plan-2' }),
        chunksAt(0, 1, [{ index: 0, action: 'changed', row_id: 'row-2', title: 'Current', canonical_url: '', section_path: '', chunk_index: 0, content: 'current plan content', truncated: false }]),
      )
      throw new Error(`Unexpected path ${path}`)
    })
    renderRouteWithLink('/plans/plan-1', '/plans/plan-2')
    await userEvent.click(screen.getByRole('link', { name: 'Test route change' }))
    expect(await screen.findByText('current plan content')).toBeInTheDocument()
    oldReview.resolve(reviewFor(detailFor({ ...plan, plan_id: 'plan-1' }), chunksAt(0, 1, [{ index: 0, action: 'changed', row_id: 'old', title: 'Old', canonical_url: '', section_path: '', chunk_index: 0, content: 'old plan content', truncated: false }])))
    await act(async () => { await oldReview.promise })
    expect(screen.getByText('current plan content')).toBeInTheDocument()
    expect(screen.queryByText('old plan content')).not.toBeInTheDocument()
  })

  it('keeps read-only routes available and makes managed routes inert when planning is unsupported', async () => {
    const unavailable = {
      ...capabilities,
      local_plan_job_creation: false,
      managed_public_planning_available: false,
      managed_public_planning_unavailable_reason: 'platform_unsupported',
      durable_plan_job_history_available: false,
    }
    const mock = mockApi((path) => {
      if (path.includes('/dashboard')) return dashboard
      if (path.includes('/plans?')) return { items: [plan], total: 1, offset: 0, limit: 100, errors: [], error_total: 0, errors_truncated: false }
      throw new Error(`Managed request was not expected: ${path}`)
    }, unavailable)

    const dashboardView = renderRoute('/')
    expect(await screen.findByText(/Read-only Command Center features remain available on this platform/i)).toBeInTheDocument()
    dashboardView.unmount()

    for (const route of ['/plans/new', '/plan-jobs', `/plan-jobs/${jobId}`]) {
      const view = renderRoute(route)
      expect(await screen.findByRole('heading', { name: 'Managed planning unavailable' })).toBeInTheDocument()
      expect(screen.getByText('Managed public-source planning is unavailable on this platform.')).toBeInTheDocument()
      expect(screen.getByText(/saved plan review, namespace inventory/i)).toBeInTheDocument()
      expect(screen.queryByRole('form')).not.toBeInTheDocument()
      view.unmount()
    }

    expect(mock.mock.calls.some(([path]) => String(path).includes('/csrf-token'))).toBe(false)
    expect(mock.mock.calls.some(([path]) => String(path).includes('/plan-jobs'))).toBe(false)
    expect(mock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(false)
    expect(FakeEventSource.instances).toHaveLength(0)
  })

  it('submits website and GitHub requests with a fresh in-memory CSRF token and same-origin JSON', async () => {
    const user = userEvent.setup()
    const payloads: Array<Record<string, unknown>> = []
    const mock = mockApi((path, init) => {
      if (path.endsWith('/csrf-token')) return { csrf_token: 'process-token' }
      if (path.endsWith('/plan-jobs') && init?.method === 'POST') {
        payloads.push(JSON.parse(String(init.body)))
        return planJob({ state: 'queued', event_sequence: 1, latest_progress: { stage: 'queued', message: 'Plan job queued.', counts: {} } })
      }
      if (path.includes(`/plan-jobs/${jobId}`)) return planJob()
      throw new Error(`Unexpected path ${path}`)
    })

    const websiteView = renderRoute('/plans/new')
    expect(await screen.findByText(/does not embed content, call turbopuffer, or modify a namespace/i)).toBeInTheDocument()
    await user.type(await screen.findByLabelText(/Credential-free HTTP\(S\) website or public GitHub repository root URL/), 'https://example.test/docs')
    await user.type(screen.getByLabelText('Maximum pages or files'), '20')
    await user.type(screen.getByLabelText('Maximum chunks'), '100')
    await user.type(screen.getByLabelText(/^Namespace/), 'docs-one')
    await user.type(screen.getByLabelText(/^Include paths/), 'docs/\napi/')
    await user.type(screen.getByLabelText(/^Exclude paths/), 'private/')
    await user.click(screen.getByRole('button', { name: 'Start plan' }))
    expect(await screen.findByRole('heading', { name: jobId })).toBeInTheDocument()
    websiteView.unmount()

    renderRoute('/plans/new')
    await user.type(await screen.findByLabelText(/Credential-free HTTP\(S\) website or public GitHub repository root URL/), 'https://github.com/owner/repository')
    await user.click(screen.getByRole('button', { name: 'Start plan' }))
    expect(await screen.findByRole('heading', { name: jobId })).toBeInTheDocument()

    expect(payloads).toEqual([
      { source_url: 'https://example.test/docs', max_pages_or_files: 20, max_chunks: 100, namespace: 'docs-one', include_paths: ['docs/', 'api/'], exclude_paths: ['private/'] },
      { source_url: 'https://github.com/owner/repository' },
    ])
    const posts = mock.mock.calls.filter(([, init]) => init?.method === 'POST')
    expect(posts).toHaveLength(2)
    for (const [, init] of posts) {
      expect(init?.headers).toMatchObject({ 'Content-Type': 'application/json', 'X-Buoy-CSRF-Token': 'process-token' })
      expect(String(posts[0][0])).toMatch(/^\/api\/v1\//)
    }
    expect(mock.mock.calls.filter(([path]) => String(path).endsWith('/csrf-token'))).toHaveLength(2)
  })

  it('validates plan fields before CSRF fetch and links a 409 conflict to the active job', async () => {
    const user = userEvent.setup()
    const mock = mockApi((path) => {
      if (path.endsWith('/csrf-token')) return { csrf_token: 'process-token' }
      if (path.endsWith('/plan-jobs')) return json({ error: { code: 'active_job_conflict', message: 'Another plan job is already active.', details: { active_job_id: activeJobId } } }, 409)
      throw new Error(`Unexpected path ${path}`)
    })
    renderRoute('/plans/new')
    await user.type(await screen.findByLabelText(/Credential-free HTTP\(S\) website or public GitHub repository root URL/), 'file:///tmp/private')
    await user.click(screen.getByRole('button', { name: 'Start plan' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('credential-free HTTP(S) URL')
    expect(mock.mock.calls.every(([path]) => String(path).includes('/capabilities'))).toBe(true)

    await user.clear(screen.getByLabelText(/Credential-free HTTP\(S\) website or public GitHub repository root URL/))
    await user.type(screen.getByLabelText(/Credential-free HTTP\(S\) website or public GitHub repository root URL/), 'https://example.test')
    await user.clear(screen.getByLabelText('Maximum chunks'))
    await user.type(screen.getByLabelText('Maximum chunks'), '0')
    await user.click(screen.getByRole('button', { name: 'Start plan' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Maximum chunks must be a whole number')
    expect(mock.mock.calls.every(([path]) => String(path).includes('/capabilities'))).toBe(true)

    await user.clear(screen.getByLabelText('Maximum chunks'))
    await user.click(screen.getByRole('button', { name: 'Start plan' }))
    const conflictLink = await screen.findByRole('link', { name: 'View active plan job' })
    expect(conflictLink).toHaveAttribute('href', `/plan-jobs/${activeJobId}`)
  })

  it('rejects an oversized UTF-8 serialized request before fetching CSRF', async () => {
    const mock = mockApi(() => { throw new Error('No request expected') })
    renderRoute('/plans/new')
    fireEvent.change(await screen.findByLabelText(/Credential-free HTTP\(S\) website or public GitHub repository root URL/), { target: { value: 'https://example.test' } })
    fireEvent.change(screen.getByLabelText(/^Include paths/), { target: { value: Array.from({ length: 40 }, () => 'é'.repeat(400)).join('\n') } })
    await userEvent.click(screen.getByRole('button', { name: 'Start plan' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('at most 16 KiB of UTF-8 JSON')
    expect(mock.mock.calls.every(([path]) => String(path).includes('/capabilities'))).toBe(true)
  })

  it('renders bounded recent job history with progress and review links', async () => {
    mockApi(() => ({ items: [planJob({ state: 'succeeded', plan_id: 'plan-1', completed_at: '2026-07-23T12:00:03Z', latest_progress: { stage: 'succeeded', message: 'Done.', counts: {} } }), planJob({ job_id: activeJobId, source_kind: 'github_repo', source_url: 'https://github.com/owner/repository' })], total: 72, offset: 0, limit: 50 }))
    renderRoute('/plan-jobs')
    expect(await screen.findByLabelText('2 recent plan jobs of 72')).toBeInTheDocument()
    expect(screen.getByText('GitHub repository')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Review plan' })).toHaveAttribute('href', '/plans/plan-1')
    expect(screen.getAllByRole('link', { name: 'Progress' })).toHaveLength(2)
  })

  it('replays escaped persisted events, keeps native EventSource for Last-Event-ID reconnect, and closes on success', async () => {
    let current = planJob()
    mockApi((path) => {
      if (path.includes(`/plan-jobs/${jobId}`)) return current
      throw new Error(`Unexpected path ${path}`)
    })
    vi.stubGlobal('EventSource', FakeEventSource)
    renderRoute(`/plan-jobs/${jobId}`)
    expect(await screen.findByRole('heading', { name: jobId })).toBeInTheDocument()
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1))
    const stream = FakeEventSource.instances[0]
    expect(stream.url).toBe(`/api/v1/plan-jobs/${jobId}/events`)
    stream.onerror?.()
    expect(await screen.findByText('reconnecting')).toBeInTheDocument()
    expect(stream.close).not.toHaveBeenCalled()

    stream.emit('plan-job-event', { sequence: 1, timestamp: '2026-07-23T12:00:00Z', stage: 'queued', message: '<img src=x onerror=alert(1)> queued', counts: { queued: 1 } })
    stream.emit('plan-job-event', { sequence: 2, timestamp: '2026-07-23T12:00:01Z', stage: 'crawl', message: 'Crawling credential-free HTTP(S) website content.', counts: { pages: 3 } })
    stream.emit('plan-job-event', { sequence: 2, timestamp: '2026-07-23T12:00:01Z', stage: 'crawl', message: 'Crawling credential-free HTTP(S) website content.', counts: { pages: 3 } })
    current = planJob({ state: 'succeeded', plan_id: 'plan-1', completed_at: '2026-07-23T12:00:03Z', event_sequence: 3, latest_progress: { stage: 'succeeded', message: 'Plan artifacts verified successfully.', counts: {} } })
    stream.emit('plan-job-event', { sequence: 3, timestamp: '2026-07-23T12:00:03Z', stage: 'succeeded', message: 'Plan artifacts verified successfully.', counts: {} })

    expect(await screen.findByText('<img src=x onerror=alert(1)> queued')).toBeInTheDocument()
    expect(document.querySelector('img[src="x"]')).toBeNull()
    expect(await screen.findByRole('link', { name: 'Review plan' })).toHaveAttribute('href', '/plans/plan-1')
    expect(screen.getByText('3 persisted/live events')).toBeInTheDocument()
    expect(stream.close).toHaveBeenCalled()
  })

  it('falls back to polling after repeated SSE errors and exposes failed terminal recovery without replay', async () => {
    let calls = 0
    mockApi((path) => {
      if (path.includes(`/plan-jobs/${jobId}`)) {
        calls += 1
        return calls === 1 ? planJob() : planJob({ state: 'failed', completed_at: '2026-07-23T12:00:02Z', event_sequence: 3, latest_progress: { stage: 'failed', message: '<script>safe failure</script>', counts: {} }, error: { code: 'source_failed', message: '<script>safe failure</script>' } })
      }
      throw new Error(`Unexpected path ${path}`)
    })
    vi.stubGlobal('EventSource', FakeEventSource)
    renderRoute(`/plan-jobs/${jobId}`)
    expect(await screen.findByRole('heading', { name: jobId })).toBeInTheDocument()
    const stream = FakeEventSource.instances[0]
    stream.onerror?.()
    stream.onerror?.()

    expect(await screen.findByRole('link', { name: 'Start a new plan' })).toHaveAttribute('href', '/plans/new')
    expect(screen.getAllByText('<script>safe failure</script>').length).toBeGreaterThan(0)
    expect(document.querySelector('script')).toBeNull()
    expect(stream.close).toHaveBeenCalled()
    expect(screen.getByText('closed')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /retry/i })).not.toBeInTheDocument()
  })

  it('ignores callbacks queued by an old EventSource after a job route switch', async () => {
    mockApi((path) => {
      if (path.includes(`/plan-jobs/${jobId}`)) return planJob()
      if (path.includes(`/plan-jobs/${activeJobId}`)) return planJob({ job_id: activeJobId, source_url: 'https://example.test/current' })
      throw new Error(`Unexpected path ${path}`)
    })
    vi.stubGlobal('EventSource', FakeEventSource)
    renderRouteWithLink(`/plan-jobs/${jobId}`, `/plan-jobs/${activeJobId}`)
    expect(await screen.findByRole('heading', { name: jobId })).toBeInTheDocument()
    const oldSource = FakeEventSource.instances[0]

    await userEvent.click(screen.getByRole('link', { name: 'Test route change' }))
    expect(await screen.findByRole('heading', { name: activeJobId })).toBeInTheDocument()
    expect(FakeEventSource.instances).toHaveLength(2)
    expect(oldSource.close).toHaveBeenCalled()
    oldSource.onopen?.()
    oldSource.emit('plan-job-event', { sequence: 99, timestamp: '2026-07-23T12:00:09Z', stage: 'succeeded', message: 'Old source event', counts: {} })
    oldSource.onerror?.()

    expect(screen.getByText('connecting')).toBeInTheDocument()
    expect(screen.queryByText('Old source event')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Review plan' })).not.toBeInTheDocument()
  })

  it('clears the polling interval on unmount', async () => {
    vi.useFakeTimers()
    mockApi((path) => {
      if (path.includes(`/plan-jobs/${jobId}`)) return planJob()
      throw new Error(`Unexpected path ${path}`)
    })
    vi.stubGlobal('EventSource', FakeEventSource)
    const clearInterval = vi.spyOn(window, 'clearInterval')
    const view = renderRoute(`/plan-jobs/${jobId}`)
    await act(async () => { await Promise.resolve() })
    const stream = FakeEventSource.instances[0]
    act(() => { stream.onerror?.(); stream.onerror?.() })
    expect(screen.getByText('polling')).toBeInTheDocument()

    view.unmount()
    expect(clearInterval).toHaveBeenCalled()
  })

  it('clears a transient polling error after a successful refresh', async () => {
    vi.useFakeTimers()
    let calls = 0
    mockApi((path) => {
      if (path.includes(`/plan-jobs/${jobId}`)) {
        calls += 1
        if (calls === 2) return json({ error: { code: 'temporary', message: 'Temporary polling failure.' } }, 500)
        return planJob({ event_sequence: calls, latest_progress: { stage: 'crawl', message: `Poll ${calls}`, counts: { pages: calls } } })
      }
      throw new Error(`Unexpected path ${path}`)
    })
    vi.stubGlobal('EventSource', FakeEventSource)
    renderRoute(`/plan-jobs/${jobId}`)
    await act(async () => { await Promise.resolve() })
    const stream = FakeEventSource.instances[0]
    await act(async () => { stream.onerror?.(); stream.onerror?.(); await Promise.resolve() })
    expect(screen.getByRole('alert')).toHaveTextContent('Temporary polling failure')

    await act(async () => { await vi.advanceTimersByTimeAsync(2_000) })
    expect(screen.queryByText('Temporary polling failure.')).not.toBeInTheDocument()
    expect(screen.getByText('Poll 3')).toBeInTheDocument()
  })

  it('keeps the newest polling error when deferred errors settle in reverse order', async () => {
    let poll: () => void = () => undefined
    vi.spyOn(window, 'setInterval').mockImplementation((handler: TimerHandler) => {
      poll = handler as () => void
      return 1
    })
    const olderError = deferred<unknown>()
    const newerError = deferred<unknown>()
    let calls = 0
    mockApi((path) => {
      if (path.includes(`/plan-jobs/${jobId}`)) {
        calls += 1
        if (calls === 1) return planJob()
        if (calls === 2) return olderError.promise
        if (calls === 3) return newerError.promise
      }
      throw new Error(`Unexpected path ${path}`)
    })
    vi.stubGlobal('EventSource', FakeEventSource)
    renderRoute(`/plan-jobs/${jobId}`)
    await act(async () => { await Promise.resolve() })
    const stream = FakeEventSource.instances[0]
    act(() => { stream.onerror?.(); stream.onerror?.() })
    act(() => { poll() })
    expect(calls).toBe(3)

    newerError.resolve(json({ error: { code: 'newer_failure', message: 'Newer polling failure.' } }, 500))
    expect(await screen.findByRole('alert')).toHaveTextContent('Newer polling failure.')

    olderError.resolve(json({ error: { code: 'older_failure', message: 'Older polling failure.' } }, 500))
    await act(async () => { await Promise.resolve(); await Promise.resolve() })
    expect(screen.getByRole('alert')).toHaveTextContent('Newer polling failure.')
    expect(screen.queryByText('Older polling failure.')).not.toBeInTheDocument()
  })

  it('uses one request-order marker across deferred polling errors and successes', async () => {
    let poll: () => void = () => undefined
    vi.spyOn(window, 'setInterval').mockImplementation((handler: TimerHandler) => {
      poll = handler as () => void
      return 1
    })
    const olderSuccess = deferred<unknown>()
    const newerError = deferred<unknown>()
    let calls = 0
    mockApi((path) => {
      if (path.includes(`/plan-jobs/${jobId}`)) {
        calls += 1
        if (calls === 1) return planJob()
        if (calls === 2) return olderSuccess.promise
        if (calls === 3) return newerError.promise
      }
      throw new Error(`Unexpected path ${path}`)
    })
    vi.stubGlobal('EventSource', FakeEventSource)
    renderRoute(`/plan-jobs/${jobId}`)
    await act(async () => { await Promise.resolve() })
    const stream = FakeEventSource.instances[0]
    act(() => { stream.onerror?.(); stream.onerror?.() })
    act(() => { poll() })
    expect(calls).toBe(3)

    newerError.resolve(json({ error: { code: 'newer_failure', message: 'Newest mixed polling failure.' } }, 500))
    expect(await screen.findByRole('alert')).toHaveTextContent('Newest mixed polling failure.')

    olderSuccess.resolve(planJob({
      event_sequence: 9,
      latest_progress: { stage: 'crawl', message: 'Older mixed success.', counts: { pages: 9 } },
    }))
    await act(async () => { await Promise.resolve(); await Promise.resolve() })
    expect(screen.getByRole('alert')).toHaveTextContent('Newest mixed polling failure.')
    expect(screen.queryByText('Older mixed success.')).not.toBeInTheDocument()
  })

  it('keeps terminal polling state sticky against deferred stale successes and errors', async () => {
    let poll: () => void = () => undefined
    vi.spyOn(window, 'setInterval').mockImplementation((handler: TimerHandler) => {
      poll = handler as () => void
      return 1
    })
    const staleSuccess = deferred<unknown>()
    const staleError = deferred<unknown>()
    const terminal = deferred<unknown>()
    let calls = 0
    mockApi((path) => {
      if (path.includes(`/plan-jobs/${jobId}`)) {
        calls += 1
        if (calls === 1) return planJob()
        if (calls === 2) return staleSuccess.promise
        if (calls === 3) return staleError.promise
        if (calls === 4) return terminal.promise
      }
      throw new Error(`Unexpected path ${path}`)
    })
    vi.stubGlobal('EventSource', FakeEventSource)
    renderRoute(`/plan-jobs/${jobId}`)
    await act(async () => { await Promise.resolve() })
    const stream = FakeEventSource.instances[0]
    act(() => { stream.onerror?.(); stream.onerror?.() })
    act(() => { poll(); poll() })
    expect(calls).toBe(4)

    terminal.resolve(planJob({
      state: 'succeeded',
      plan_id: 'plan-1',
      completed_at: '2026-07-23T12:00:05Z',
      event_sequence: 5,
      latest_progress: { stage: 'succeeded', message: 'Terminal result.', counts: {} },
    }))
    await act(async () => { await Promise.resolve() })
    expect(await screen.findByRole('link', { name: 'Review plan' })).toHaveAttribute('href', '/plans/plan-1')
    expect(screen.getByText('Terminal result.')).toBeInTheDocument()
    expect(screen.getByText('closed')).toBeInTheDocument()

    staleSuccess.resolve(planJob({
      event_sequence: 3,
      latest_progress: { stage: 'crawl', message: 'Stale running result.', counts: { pages: 3 } },
    }))
    staleError.reject(new Error('Stale polling failure.'))
    await act(async () => { await Promise.resolve(); await Promise.resolve() })
    expect(screen.getByRole('link', { name: 'Review plan' })).toHaveAttribute('href', '/plans/plan-1')
    expect(screen.getByText('Terminal result.')).toBeInTheDocument()
    expect(screen.queryByText('Stale running result.')).not.toBeInTheDocument()
    expect(screen.queryByText('Stale polling failure.')).not.toBeInTheDocument()
  })

  it('shows the new-plan link for an interrupted terminal job without automatic replay controls', async () => {
    mockApi((path) => {
      if (path.includes(`/plan-jobs/${jobId}`)) return planJob({ state: 'interrupted', completed_at: '2026-07-23T12:00:02Z', latest_progress: { stage: 'interrupted', message: 'Planning was interrupted by a local service restart.', counts: {} }, error: { code: 'job_interrupted', message: 'Planning was interrupted by a local service restart.' } })
      throw new Error(`Unexpected path ${path}`)
    })
    renderRoute(`/plan-jobs/${jobId}`)
    expect(await screen.findByRole('link', { name: 'Start a new plan' })).toHaveAttribute('href', '/plans/new')
    expect(screen.queryByRole('button', { name: /retry|resume|replay/i })).not.toBeInTheDocument()
  })

  it('shows a durable originating job even when it is older than any history list window', async () => {
    const mock = mockApi((path) => {
      if (path.includes('/plans/plan-1/review?')) return reviewFor(detailFor(plan, { originating_job_id: jobId }))
      throw new Error(`Unexpected path ${path}`)
    })
    renderRoute('/plans/plan-1')
    expect(await screen.findByText('Originating plan job')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: jobId })).toHaveAttribute('href', `/plan-jobs/${jobId}`)
    expect(mock.mock.calls.some(([path]) => String(path).includes('/plan-jobs?'))).toBe(false)
  })

  it('omits the originating-job row when artifact metadata is unavailable', async () => {
    mockApi((path) => {
      if (path.includes('/plans/plan-1/review?')) return reviewFor(detailFor())
      throw new Error(`Unexpected path ${path}`)
    })
    renderRoute('/plans/plan-1')
    await screen.findByRole('heading', { name: 'plan-1' })
    expect(screen.queryByText('Originating plan job')).not.toBeInTheDocument()
  })

  it('provides a keyboard skip link to the main content', () => {
    renderRoute('/graphs')
    expect(screen.getByRole('link', { name: 'Skip to main content' })).toHaveAttribute('href', '#main-content')
  })

  it('labels the graph placeholder flow without generated graph controls or data', () => {
    renderRoute('/graphs')
    expect(screen.getByRole('heading', { name: 'Evidence-backed semantic graphs' })).toBeInTheDocument()
    const flow = screen.getByLabelText('Future evidence-backed graph flow')
    expect(within(flow).getByText('Select namespaces')).toBeInTheDocument()
    expect(within(flow).getByText('Derive an evidence-backed graph snapshot')).toBeInTheDocument()
    expect(within(flow).getByText('Explore taxonomy and ontology')).toBeInTheDocument()
    expect(screen.getByText(/No graph data exists/)).toBeInTheDocument()
  })

  it('keeps managed-route read reloads distinct from plan-job execution or replay controls', async () => {
    const mock = mockApi(() => json({ error: { code: 'temporary_read_failure', message: 'Temporary read failure.' } }, 500))
    for (const route of ['/plan-jobs', `/plan-jobs/${jobId}`, '/plans/plan-1']) {
      const view = renderRoute(route)
      expect(await screen.findByRole('alert')).toHaveTextContent('Temporary read failure')
      const controls = [...screen.queryAllByRole('button'), ...screen.queryAllByRole('link')]
      expect(controls.map((control) => control.textContent ?? '')).not.toEqual(
        expect.arrayContaining([expect.stringMatching(/retry plan job|replay|resume|re-execute/i)]),
      )
      expect(mock.mock.calls.every(([, init]) => !init?.method || init.method === 'GET')).toBe(true)
      view.unmount()
    }
    expect(mock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(false)
  })

  it('exposes no prohibited controls or browser storage across every route', async () => {
    const storageSet = vi.spyOn(Storage.prototype, 'setItem')
    mockApi((path) => {
      if (path.includes('/dashboard')) return dashboard
      if (path.includes('/artifact-errors')) return { items: [], total: 0, offset: 0, limit: 50 }
      if (path === '/api/v1/namespaces/docs-one?plan_offset=0&plan_limit=20') return { summary: namespaces.items[0], plans: [plan], state: null, retrieval: null }
      if (path === `/api/v1/plan-jobs/${jobId}`) return planJob({ state: 'interrupted', completed_at: '2026-07-23T12:00:02Z', latest_progress: { stage: 'interrupted', message: 'Interrupted.', counts: {} } })
      if (path.includes('/plan-jobs')) return { items: [planJob()], total: 1, offset: 0, limit: 50 }
      if (path.includes('/namespaces')) return namespaces
      if (path.includes('/plans/plan-1/review?')) return reviewFor()
      if (path.includes('/plans')) return { items: [plan], total: 1, offset: 0, limit: 50, errors: [], error_total: 0, errors_truncated: false }
      throw new Error(`Unexpected path ${path}`)
    })
    for (const route of ['/', '/namespaces', '/namespaces/docs-one', '/plans', '/plans/new', '/plans/plan-1', '/artifact-errors', '/plan-jobs', `/plan-jobs/${jobId}`, '/search', '/graphs']) {
      const view = renderRoute(route)
      await screen.findByText('Local command center')
      const prohibitedControl = /\b(?:apply|approve|cancel|delete|retry plan job|replay|resume|register catalog|crawl source|manage namespace|manage source)\b/i
      expect(screen.queryByRole('button', { name: prohibitedControl })).not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: prohibitedControl })).not.toBeInTheDocument()
      view.unmount()
    }
    expect(storageSet).not.toHaveBeenCalled()
  })
})
