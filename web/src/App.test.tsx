import { MemoryRouter } from 'react-router-dom'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

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

const source = {
  kind: 'website',
  uri: 'https://example.test/docs',
  title: 'example.test',
  repository: null,
  filename: null,
  database_backend: null,
  database_source_id: null,
  database_relation: null,
}

const plan = {
  plan_id: 'plan-1',
  namespace: 'docs-one',
  site_id: 'example-test',
  created_at: '2026-07-23T12:00:00Z',
  source,
  page_count: 1,
  chunk_count: 12,
  diff,
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
  total: 2, offset: 0, limit: 100, errors: [],
}

const capabilities = {
  api_version: 'v1', buoy_version: 'test', loopback_only: true, read_only: true, remote_snapshot: true, search: true, mutations: false,
  artifacts_root_available: true, state_root_available: true, turbopuffer_credentials_available: true,
  ui_build_available: true, bigquery_extra_installed: false, snowflake_extra_installed: false,
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

function mockApi(handler: (path: string, init?: RequestInit) => unknown | Promise<unknown>) {
  const mock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input)
    const result = path.includes('/capabilities') ? capabilities : await handler(path, init)
    return result instanceof Response ? result : json(result)
  })
  vi.stubGlobal('fetch', mock)
  return mock
}

function renderRoute(route: string) {
  return render(<MemoryRouter initialEntries={[route]}><App /></MemoryRouter>)
}

afterEach(() => {
  cleanup()
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
    for (const label of ['Artifacts root available', 'State root available', 'turbopuffer credentials configured', 'UI build available', 'BigQuery extra installed', 'Snowflake extra installed', 'Pending changes', 'Artifact errors']) {
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

  it('filters namespaces by source and local status while remote values remain not checked', async () => {
    const user = userEvent.setup()
    mockApi(() => namespaces)
    renderRoute('/namespaces')
    expect(await screen.findByRole('link', { name: 'docs-one' })).toBeInTheDocument()
    expect(screen.getAllByText('not checked').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/example\.test/).length).toBeGreaterThan(0)
    expect(screen.getByRole('columnheader', { name: 'Retained stale' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Planned upserts' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Planned stale' })).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('Source kind'), 'github_repo')
    expect(screen.queryByRole('link', { name: 'docs-one' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'repo-two' })).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Local status'), 'pending_changes')
    expect(screen.getByText(/No namespaces match/)).toBeInTheDocument()
  })

  it('shares an explicitly refreshed remote snapshot with namespace filters', async () => {
    const user = userEvent.setup()
    mockApi((path) => path.includes('/dashboard') ? dashboard : path.includes('/remote/snapshot') ? remote : path.endsWith('/namespaces/docs-one') ? {
      summary: namespaces.items[0], plans: [plan], state: null, retrieval: null,
    } : namespaces)
    renderRoute('/')
    await screen.findByText('plan-1')
    await user.click(screen.getByRole('button', { name: 'Refresh remote status' }))
    await screen.findByText(/Remote status: ready/i)
    await user.click(screen.getByRole('link', { name: 'Namespaces' }))
    await screen.findByRole('link', { name: 'docs-one' })
    await user.selectOptions(screen.getByLabelText('Remote status'), 'eligible')
    expect(screen.getByRole('link', { name: 'docs-one' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'repo-two' })).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Catalog card'), 'present')
    expect(screen.getByText('Yes')).toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: 'docs-one' }))
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
    await user.selectOptions(screen.getByLabelText('Catalog card'), 'not-checked')
    expect(screen.getByRole('link', { name: 'docs-one' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'repo-two' })).not.toBeInTheDocument()
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

  it('renders deterministic plan history metadata and an empty plan state', async () => {
    mockApi(() => ({ items: [plan], total: 1, offset: 0, limit: 100, errors: [] }))
    const view = renderRoute('/plans')
    expect(await screen.findByRole('link', { name: 'plan-1' })).toBeInTheDocument()
    expect(screen.getByText('Website')).toBeInTheDocument()
    expect(screen.getByText('6')).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'First apply' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Source credentials' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Source API calls' })).toBeInTheDocument()

    view.unmount()
    mockApi(() => ({ items: [], total: 0, offset: 0, limit: 100, errors: [] }))
    renderRoute('/plans')
    expect(await screen.findByText(/Saved plan history will appear/)).toBeInTheDocument()
  })

  it('renders plan provenance, warehouse review notice, bounded chunks, and escaped Markdown', async () => {
    const warehousePlan = { ...plan, source: { ...source, kind: 'database', uri: 'bigquery://warehouse', title: 'warehouse (docs)', database_backend: 'bigquery', database_source_id: 'warehouse', database_relation: 'dataset.docs' } }
    mockApi((path) => {
      if (path.endsWith('/plans/plan-1')) return { summary: warehousePlan, namespace_candidate: 'docs-one', artifact_hash: 'a'.repeat(64), retrieval: { embedding_model: 'model', embedding_precision: 'float32', ranking_mode: 'page', ranking_profile: 'none', ranking_pool: 25, ranking_aggregation: 'max' }, source_activity: { credentials_required: true, api_calls_occurred: true } }
      if (path.includes('/pages/0')) return { page: { index: 0, title: 'Unsafe markdown', canonical_url: 'https://example.test/page', status: 200, content_type: 'text/markdown' }, markdown: '<script>alert("unsafe")</script> **plain text**', truncated: false }
      if (path.includes('/pages')) return { items: [{ index: 0, title: 'Unsafe markdown', canonical_url: 'https://example.test/page', status: 200, content_type: 'text/markdown' }], total: 1, offset: 0, limit: 100 }
      if (path.includes('/chunks')) return { items: [{ index: 0, row_id: 'row-1', title: 'Chunk title', canonical_url: 'https://example.test/page', section_path: 'Intro', chunk_index: 0, content: '<img src=x onerror=alert(1)>', truncated: false }], total: 12, offset: 0, limit: 10 }
      throw new Error(`Unexpected path ${path}`)
    })
    renderRoute('/plans/plan-1')
    expect(await screen.findByText(/reviewed without reconnecting to the source warehouse/i)).toBeInTheDocument()
    expect(screen.getByText('<script>alert("unsafe")</script> **plain text**')).toBeInTheDocument()
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeInTheDocument()
    expect(document.querySelector('script')).toBeNull()
    expect(document.querySelector('img[src="x"]')).toBeNull()
    expect(screen.getByText('1–1 of 12')).toBeInTheDocument()
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
    expect(mock).not.toHaveBeenCalled()
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
    expect(mock.mock.calls[0][1]?.headers).toMatchObject({ 'X-Buoy-Command-Center': '1' })
    expect(mock).toHaveBeenCalledTimes(1)
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
    expect(screen.getAllByText('No local snapshot')).toHaveLength(2)
    expect(screen.queryByRole('link', { name: 'remote-three' })).not.toBeInTheDocument()
    expect(screen.getByText(/Remote docs/)).toBeInTheDocument()
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

  it('loads complete inventories beyond 100 records and paginates the page selector', async () => {
    const namespaceItems = Array.from({ length: 101 }, (_, index) => ({ ...namespaces.items[0], namespace: `namespace-${index}` }))
    const planItems = Array.from({ length: 101 }, (_, index) => ({ ...plan, plan_id: `plan-${index}` }))
    const pageItems = Array.from({ length: 101 }, (_, index) => ({ index, title: `Page ${index + 1}`, canonical_url: `https://example.test/${index}`, status: 200, content_type: 'text/markdown' }))
    const mock = mockApi((path) => {
      const offset = Number(new URL(`http://localhost${path}`).searchParams.get('offset') ?? 0)
      if (path.includes('/namespaces')) return { ...namespaces, items: namespaceItems.slice(offset, offset + 100), total: 101 }
      if (path === '/api/v1/plans?offset=0&limit=100' || path === '/api/v1/plans?offset=100&limit=100') return { items: planItems.slice(offset, offset + 100), total: 101, offset, limit: 100, errors: [] }
      if (path.endsWith('/plans/plan-many')) return { summary: { ...plan, plan_id: 'plan-many' }, namespace_candidate: 'docs-one', artifact_hash: 'a'.repeat(64), retrieval: null, source_activity: { credentials_required: false, api_calls_occurred: false } }
      if (path.includes('/plans/plan-many/pages?')) return { items: pageItems.slice(offset, offset + 100), total: 101, offset, limit: 100 }
      if (path.includes('/plans/plan-many/pages/')) return { page: pageItems[0], markdown: 'preview', truncated: false }
      if (path.includes('/plans/plan-many/chunks')) return { items: [], total: 0, offset: 0, limit: 10 }
      throw new Error(`Unexpected path ${path}`)
    })

    const namespaceView = renderRoute('/namespaces')
    expect(await screen.findByRole('link', { name: 'namespace-100' })).toBeInTheDocument()
    namespaceView.unmount()
    const planView = renderRoute('/plans')
    expect(await screen.findByRole('link', { name: 'plan-100' })).toBeInTheDocument()
    planView.unmount()
    renderRoute('/plans/plan-many')
    expect(await screen.findByText('1–20 of 101')).toBeInTheDocument()
    const user = userEvent.setup()
    for (let index = 0; index < 5; index += 1) await user.click(screen.getByRole('button', { name: 'Next pages' }))
    expect(await screen.findByRole('button', { name: '101. Page 101' })).toBeInTheDocument()
    expect(mock.mock.calls.some(([path]) => String(path).includes('offset=100&limit=100'))).toBe(true)
  })

  it('retains a later selected page preview across chunk pagination', async () => {
    const pages = Array.from({ length: 25 }, (_, index) => ({ index, title: `Page ${index + 1}`, canonical_url: `https://example.test/${index + 1}`, status: 200, content_type: 'text/markdown' }))
    mockApi((path) => {
      if (path.endsWith('/plans/plan-1')) return { summary: { ...plan, page_count: 25 }, namespace_candidate: 'docs-one', artifact_hash: 'a'.repeat(64), retrieval: null, source_activity: { credentials_required: false, api_calls_occurred: false } }
      const previewMatch = path.match(/\/pages\/(\d+)$/)
      if (previewMatch) {
        const page = pages[Number(previewMatch[1])]
        return { page, markdown: `preview ${page.index + 1}`, truncated: false }
      }
      if (path.includes('/pages')) return { items: pages, total: pages.length, offset: 0, limit: 100 }
      if (path.includes('/chunks')) {
        const offset = Number(new URL(`http://localhost${path}`).searchParams.get('offset') ?? 0)
        return { items: [{ index: offset, row_id: `row-${offset}`, title: `Chunk ${offset + 1}`, canonical_url: '', section_path: '', chunk_index: offset, content: `chunk ${offset + 1}`, truncated: false }], total: 11, offset, limit: 10 }
      }
      throw new Error(`Unexpected path ${path}`)
    })
    renderRoute('/plans/plan-1')
    expect(await screen.findByText('preview 1')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Next pages' }))
    await userEvent.click(screen.getByRole('button', { name: '21. Page 21' }))
    expect(await screen.findByText('preview 21')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Next chunks' }))

    expect(await screen.findByText('chunk 11')).toBeInTheDocument()
    expect(screen.getByText('21–25 of 25')).toBeInTheDocument()
    expect(screen.getByText('preview 21')).toBeInTheDocument()
    expect(screen.queryByText('preview 1')).not.toBeInTheDocument()
  })

  it('clears stale preview errors on a successful chunk-page transition', async () => {
    let previewCalls = 0
    mockApi((path) => {
      if (path.endsWith('/plans/plan-1')) return { summary: plan, namespace_candidate: 'docs-one', artifact_hash: 'a'.repeat(64), retrieval: null, source_activity: { credentials_required: false, api_calls_occurred: false } }
      if (path.includes('/pages/0')) {
        previewCalls += 1
        if (previewCalls === 1) return json({ error: { code: 'page_unavailable', message: 'Old preview failed.' } }, 400)
        return { page: { index: 0, title: 'Page', canonical_url: 'https://example.test', status: 200, content_type: 'text/markdown' }, markdown: 'fresh preview', truncated: false }
      }
      if (path.includes('/pages')) return { items: [{ index: 0, title: 'Page', canonical_url: 'https://example.test', status: 200, content_type: 'text/markdown' }], total: 1, offset: 0, limit: 100 }
      if (path.includes('/chunks')) return { items: [{ index: 0, row_id: 'row', title: 'Chunk', canonical_url: '', section_path: '', chunk_index: 0, content: 'chunk', truncated: false }], total: 11, offset: 0, limit: 10 }
      throw new Error(`Unexpected path ${path}`)
    })
    renderRoute('/plans/plan-1')
    expect(await screen.findByRole('alert')).toHaveTextContent('Old preview failed')
    await userEvent.click(screen.getByRole('button', { name: 'Next chunks' }))
    expect(await screen.findByText('fresh preview')).toBeInTheDocument()
    expect(screen.queryByText(/Old preview failed/)).not.toBeInTheDocument()
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

  it('exposes no mutation controls across every review route', async () => {
    mockApi((path) => {
      if (path.includes('/dashboard')) return dashboard
      if (path === '/api/v1/namespaces/docs-one') return { summary: namespaces.items[0], plans: [plan], state: null, retrieval: null }
      if (path.includes('/namespaces')) return namespaces
      if (path.endsWith('/plans/plan-1')) return { summary: plan, namespace_candidate: 'docs-one', artifact_hash: 'a'.repeat(64), retrieval: null, source_activity: { credentials_required: false, api_calls_occurred: false } }
      if (path.includes('/pages/0')) return { page: { index: 0, title: 'Page', canonical_url: '', status: 200, content_type: 'text/markdown' }, markdown: 'preview', truncated: false }
      if (path.includes('/pages')) return { items: [{ index: 0, title: 'Page', canonical_url: '', status: 200, content_type: 'text/markdown' }], total: 1, offset: 0, limit: 100 }
      if (path.includes('/chunks')) return { items: [], total: 0, offset: 0, limit: 10 }
      if (path.includes('/plans')) return { items: [plan], total: 1, offset: 0, limit: 100, errors: [] }
      throw new Error(`Unexpected path ${path}`)
    })
    for (const route of ['/', '/namespaces', '/namespaces/docs-one', '/plans', '/plans/plan-1', '/search', '/graphs']) {
      const view = renderRoute(route)
      await screen.findByText('Read only')
      const controls = [...screen.queryAllByRole('button'), ...screen.queryAllByRole('link')]
      expect(controls.map((control) => control.textContent ?? '')).not.toEqual(expect.arrayContaining([expect.stringMatching(/^(apply|delete|register catalog|crawl source)$/i)]))
      view.unmount()
    }
  })
})
