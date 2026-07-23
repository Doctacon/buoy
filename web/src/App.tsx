import { FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from 'react'
import {
  Link,
  NavLink,
  Navigate,
  Route,
  Routes,
  useParams,
  useSearchParams,
} from 'react-router-dom'
import { api, RequestError } from './api'
import type {
  ArtifactError,
  Capabilities,
  ChunkInventory,
  DashboardData,
  DiffSummary,
  NamespaceDetail,
  NamespaceSummary,
  PageInventory,
  PagePreview,
  PlanDetail,
  PlanInventory,
  PlanSummary,
  RemoteNamespaceStatus,
  RemoteSnapshot,
  RemoteStatus,
  RetrievalSettings,
  SearchResponse,
  SourceProvenance,
  Warning,
} from './types'

type RemoteState = {
  snapshot: RemoteSnapshot | null
  refreshing: boolean
  refreshError: string | null
  refresh: () => Promise<void>
}

function useResource<T>(loader: () => Promise<T>, dependencies: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let current = true
    setData(null)
    setError(null)
    loader().then(
      (value) => current && setData(value),
      (reason: unknown) =>
        current && setError(reason instanceof Error ? reason.message : 'The request could not be completed.'),
    )
    return () => {
      current = false
    }
    // The caller supplies stable primitive dependencies; loader is intentionally not included.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...dependencies, attempt])

  return { data, error, retry: () => setAttempt((value) => value + 1) }
}

function App() {
  const [snapshot, setSnapshot] = useState<RemoteSnapshot | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshError, setRefreshError] = useState<string | null>(null)

  async function refresh() {
    setRefreshing(true)
    setSnapshot(null)
    setRefreshError(null)
    try {
      setSnapshot(await api.refreshRemote())
    } catch (error) {
      setSnapshot(null)
      setRefreshError(error instanceof Error ? error.message : 'Remote status could not be refreshed.')
    } finally {
      setRefreshing(false)
    }
  }

  const remote: RemoteState = { snapshot, refreshing, refreshError, refresh }
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className="site-header">
        <Link className="brand" to="/" aria-label="Buoy Command Center home">
          <img src="/buoy.svg" alt="" width="52" height="52" />
          <span><strong>Buoy</strong><small>Command Center</small></span>
        </Link>
        <span className="read-only-badge">Read only</span>
      </header>
      <nav className="primary-nav" aria-label="Primary navigation">
        {[
          ['/', 'Dashboard'],
          ['/namespaces', 'Namespaces'],
          ['/plans', 'Plans'],
          ['/search', 'Search'],
          ['/graphs', 'Graphs'],
        ].map(([to, label]) => (
          <NavLink key={to} to={to} end={to === '/'}>{label}</NavLink>
        ))}
      </nav>
      <main id="main-content">
        <Routes>
          <Route path="/" element={<Dashboard remote={remote} />} />
          <Route path="/namespaces" element={<Namespaces remote={remote} />} />
          <Route path="/namespaces/:namespace" element={<NamespaceScreen remote={remote} />} />
          <Route path="/plans" element={<Plans />} />
          <Route path="/plans/:planId" element={<PlanScreen />} />
          <Route path="/search" element={<Search />} />
          <Route path="/graphs" element={<Graphs />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer>Sources originate knowledge. Buoy plans and namespaces remain reviewable snapshots.</footer>
    </div>
  )
}

function PageTitle({ eyebrow, title, children }: { eyebrow: string; title: string; children: ReactNode }) {
  return (
    <header className="page-title">
      <p className="eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      <p>{children}</p>
    </header>
  )
}

function Loading({ label }: { label: string }) {
  return <div className="state-card" role="status" aria-live="polite"><span className="spinner" />{label}</div>
}

function ErrorState({ message, retry }: { message: string; retry: () => void }) {
  return (
    <div className="state-card error-state" role="alert">
      <strong>Unable to load this view</strong>
      <p>{message}</p>
      <button type="button" onClick={retry}>Retry</button>
    </div>
  )
}

function Empty({ children }: { children: ReactNode }) {
  return <div className="state-card empty-state"><strong>Nothing here yet</strong><p>{children}</p></div>
}

function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'good' | 'warn' | 'bad' | 'neutral' }) {
  return <span className={`badge badge-${tone}`}>{children}</span>
}

function value(value: string | number | boolean | null | undefined) {
  if (value === null || value === undefined || value === '') return 'Unknown'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return String(value)
}

function timestamp(input: string | null) {
  if (!input) return 'Unknown time'
  const date = new Date(input)
  return Number.isNaN(date.valueOf()) ? input : date.toLocaleString()
}

function sourceLabel(source: SourceProvenance | null) {
  if (!source) return 'Unknown source'
  const kinds: Record<SourceProvenance['kind'], string> = {
    website: 'Website', github_repo: 'GitHub repository', document: 'Document', database: 'Database relation', unknown: 'Unknown source',
  }
  return kinds[source.kind]
}

function Source({ source }: { source: SourceProvenance | null }) {
  if (!source) return <p>Source provenance is unavailable.</p>
  return (
    <dl className="details-grid">
      <div><dt>Source kind</dt><dd>{sourceLabel(source)}</dd></div>
      <div><dt>Source title</dt><dd>{value(source.title)}</dd></div>
      {source.repository && <div><dt>Repository</dt><dd>{source.repository}</dd></div>}
      {source.filename && <div><dt>File</dt><dd>{source.filename}</dd></div>}
      {source.database_backend && <div><dt>Backend</dt><dd>{source.database_backend}</dd></div>}
      {source.database_source_id && <div><dt>Source ID</dt><dd>{source.database_source_id}</dd></div>}
      {source.database_relation && <div><dt>Relation</dt><dd>{source.database_relation}</dd></div>}
      {source.uri && <div><dt>Safe source URI</dt><dd><SafeLink href={source.uri}>{source.uri}</SafeLink></dd></div>}
    </dl>
  )
}

function SafeLink({ href, children }: { href: string; children: ReactNode }) {
  if (!/^https?:\/\//i.test(href)) return <span>{children}</span>
  return <a href={href} target="_blank" rel="noreferrer">{children}<span className="sr-only"> (opens in a new tab)</span></a>
}

function WarningList({ title, items }: { title: string; items: Warning[] | ArtifactError[] }) {
  if (!items.length) return null
  return (
    <section className="panel warning-panel">
      <h2>{title}</h2>
      <ul>{items.map((item, index) => <li key={`${item.code}-${index}`}><strong>{item.code}</strong>: {item.message}</li>)}</ul>
    </section>
  )
}

function RemoteNotice({ snapshot, refreshError = null }: { snapshot: RemoteSnapshot | null; refreshError?: string | null }) {
  if (refreshError) {
    return <p className="notice" role="alert"><strong>Remote status: Latest refresh failed.</strong> No previous snapshot is being presented as current. {refreshError}</p>
  }
  if (!snapshot) {
    return <p className="notice"><strong>Remote status: Not checked.</strong> No remote credentials were read and no remote API calls occurred.</p>
  }
  return (
    <div className="notice" aria-live="polite">
      <strong>Remote status: {snapshot.state.replaceAll('_', ' ')}.</strong>{' '}
      Credentials required: {value(snapshot.credentials_required)}. API calls occurred: {value(snapshot.api_calls_occurred)}. Writes occurred: {value(snapshot.writes_occurred)}.
      {snapshot.error && <span> {snapshot.error.message}</span>}
      {snapshot.namespaces_truncated && <strong> Showing {snapshot.namespaces.length} of {snapshot.namespace_total} namespaces; snapshot truncated.</strong>}
    </div>
  )
}

function Dashboard({ remote }: { remote: RemoteState }) {
  const resource = useResource(async () => {
    const [dashboard, capabilities] = await Promise.all([api.dashboard(), api.capabilities()])
    return { dashboard, capabilities }
  })
  return (
    <>
      <PageTitle eyebrow="Local overview" title="Command Center">Review local plans, searchable applied snapshots, and operational attention without changing data.</PageTitle>
      <section className="panel remote-panel" aria-labelledby="remote-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Explicit remote activity</p><h2 id="remote-heading">Remote namespace status</h2></div>
          <button type="button" onClick={remote.refresh} disabled={remote.refreshing}>
            {remote.refreshing ? 'Refreshing…' : 'Refresh remote status'}
          </button>
        </div>
        <RemoteNotice snapshot={remote.snapshot} refreshError={remote.refreshError} />
        <p className="muted">Refresh reads live namespaces and catalog cards from turbopuffer. It never writes or persists a snapshot.</p>
      </section>
      {resource.error ? <ErrorState message={resource.error} retry={resource.retry} /> : !resource.data ? <Loading label="Loading local dashboard…" /> : <DashboardContent data={resource.data.dashboard} capabilities={resource.data.capabilities} />}
    </>
  )
}

function DashboardContent({ data, capabilities }: { data: DashboardData; capabilities: Capabilities }) {
  return (
    <>
      <section className="metric-grid" aria-label="Local inventory counts">
        {[
          ['Plans', data.plan_count],
          ['Namespaces', data.namespace_count],
          ['Applied namespaces', data.applied_namespace_count],
          ['Pending changes', data.pending_namespace_count],
          ['Active rows', data.active_row_count ?? 'Unknown'],
          ['Artifact errors', data.artifact_error_count],
        ].map(([label, count]) => <article className="metric" key={label}><span>{label}</span><strong>{count}</strong></article>)}
      </section>
      <section className="panel" aria-labelledby="readiness-heading">
        <h2 id="readiness-heading">Local readiness</h2>
        <dl className="details-grid">
          <div><dt>Artifacts root available</dt><dd>{value(capabilities.artifacts_root_available)}</dd></div>
          <div><dt>State root available</dt><dd>{value(capabilities.state_root_available)}</dd></div>
          <div><dt>turbopuffer credentials configured</dt><dd>{value(capabilities.turbopuffer_credentials_available)}</dd></div>
          <div><dt>UI build available</dt><dd>{value(capabilities.ui_build_available)}</dd></div>
          <div><dt>BigQuery extra installed</dt><dd>{value(capabilities.bigquery_extra_installed)}</dd></div>
          <div><dt>Snowflake extra installed</dt><dd>{value(capabilities.snowflake_extra_installed)}</dd></div>
        </dl>
      </section>
      <div className="two-column">
        <section className="panel"><h2>Recent plans</h2>{data.recent_plans.length ? <PlanCards plans={data.recent_plans} /> : <Empty>Saved plans will appear here after a local plan is created.</Empty>}</section>
        <section className="panel"><h2>Attention</h2>{data.attention_items.length ? <ul className="attention-list">{data.attention_items.map((item, index) => <li key={`${item.code}-${index}`}><strong>{item.code}</strong><span>{item.message}</span></li>)}</ul> : <Empty>No local warnings require attention.</Empty>}</section>
      </div>
      <WarningList title="Artifact errors" items={data.artifact_errors} />
    </>
  )
}

function PlanCards({ plans }: { plans: PlanSummary[] }) {
  return <ul className="card-list">{plans.map((plan) => <li key={plan.plan_id}><Link to={`/plans/${encodeURIComponent(plan.plan_id)}`}><strong>{plan.plan_id}</strong><span>{plan.namespace} · {timestamp(plan.created_at)}</span></Link></li>)}</ul>
}

function remoteFor(namespace: string, snapshot: RemoteSnapshot | null): RemoteNamespaceStatus | null {
  return snapshot?.namespaces.find((item) => item.namespace === namespace) ?? null
}

function remoteStatusLabel(status: RemoteStatus | undefined) {
  return (status ?? 'not_checked').replaceAll('_', ' ')
}

type MergedNamespace = { namespace: string; local: NamespaceSummary | null; remote: RemoteNamespaceStatus | null }

function Namespaces({ remote }: { remote: RemoteState }) {
  const resource = useResource(api.namespaces)
  const [query, setQuery] = useState('')
  const [source, setSource] = useState('all')
  const [local, setLocal] = useState('all')
  const [remoteFilter, setRemoteFilter] = useState('all')
  const [catalog, setCatalog] = useState('all')
  const merged = useMemo(() => {
    const rows = new Map<string, MergedNamespace>()
    for (const item of resource.data?.items ?? []) rows.set(item.namespace, { namespace: item.namespace, local: item, remote: null })
    for (const item of remote.snapshot?.namespaces ?? []) {
      const current = rows.get(item.namespace)
      rows.set(item.namespace, { namespace: item.namespace, local: current?.local ?? null, remote: item })
    }
    return [...rows.values()].sort((left, right) => left.namespace.localeCompare(right.namespace))
  }, [resource.data, remote.snapshot])
  const filtered = useMemo(() => merged.filter((item) => {
    const sourceKind = item.local?.source?.kind ?? item.remote?.source_kind ?? 'unknown'
    const localStatus = item.local?.local_status ?? 'remote-only'
    return item.namespace.toLowerCase().includes(query.toLowerCase())
      && (source === 'all' || sourceKind === source)
      && (local === 'all' || local === localStatus)
      && (remoteFilter === 'all' || remoteStatusLabel(item.remote?.status) === remoteFilter)
      && (catalog === 'all' || (catalog === 'present' ? item.remote?.card_present === true : catalog === 'missing' ? item.remote?.card_present === false : item.remote?.card_present == null))
  }), [merged, query, source, local, remoteFilter, catalog])

  return (
    <>
      <PageTitle eyebrow="Applied snapshots" title="Namespaces">Namespaces are searchable applied snapshots. Catalog cards describe them and support routing; they do not originate source knowledge.</PageTitle>
      <RemoteNotice snapshot={remote.snapshot} refreshError={remote.refreshError} />
      <section className="panel filters" aria-label="Namespace filters">
        <label>Namespace <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter by ID" /></label>
        <label>Source kind <select value={source} onChange={(event) => setSource(event.target.value)}><option value="all">All</option><option value="website">Website</option><option value="github_repo">GitHub repository</option><option value="document">Document</option><option value="database">Database</option><option value="unknown">Unknown</option></select></label>
        <label>Local status <select value={local} onChange={(event) => setLocal(event.target.value)}><option value="all">All</option><option value="planned">Planned</option><option value="applied">Applied</option><option value="pending_changes">Pending changes</option><option value="conflict">Conflict</option><option value="error">Error</option><option value="remote-only">No local snapshot</option></select></label>
        <label>Remote status <select value={remoteFilter} onChange={(event) => setRemoteFilter(event.target.value)}><option value="all">All</option><option value="not checked">Not checked</option><option value="eligible">Eligible</option><option value="local only">Local only</option><option value="missing card">Missing card</option><option value="stale target">Stale target</option><option value="disabled">Disabled</option><option value="incompatible">Incompatible</option></select></label>
        <label>Catalog card <select value={catalog} onChange={(event) => setCatalog(event.target.value)}><option value="all">All</option><option value="not-checked">Not checked</option><option value="present">Present</option><option value="missing">Missing</option></select></label>
      </section>
      {resource.error ? <ErrorState message={resource.error} retry={resource.retry} /> : !resource.data ? <Loading label="Loading namespaces…" /> : !filtered.length ? <Empty>No namespaces match the current filters.</Empty> : <NamespaceTable items={filtered} total={merged.length} />}
      {resource.data && <WarningList title="Local artifact errors" items={resource.data.errors} />}
    </>
  )
}

function NamespaceTable({ items, total }: { items: MergedNamespace[]; total: number }) {
  return (
    <section className="table-wrap" aria-label={`${items.length} of ${total} namespaces`}>
      <table><thead><tr><th>Namespace</th><th>Source</th><th>Local</th><th>Remote</th><th>Catalog</th><th>Plans</th><th>Active rows</th><th>Retained stale</th><th>Planned upserts</th><th>Planned stale</th></tr></thead>
        <tbody>{items.map((item) => {
          const status = item.remote
          const source = item.local?.source ? sourceLabel(item.local.source) : status?.source_kind?.replaceAll('_', ' ') ?? 'Unknown source'
          const sourceTitle = item.local?.source?.title ?? status?.title
          const localStatus = item.local?.local_status
          return <tr key={item.namespace}><th scope="row">{item.local ? <Link to={`/namespaces/${encodeURIComponent(item.namespace)}`}>{item.namespace}</Link> : item.namespace}</th><td>{source}{sourceTitle && <span className="muted"> · {sourceTitle}</span>}</td><td><Badge tone={localStatus === 'applied' ? 'good' : localStatus === 'pending_changes' || localStatus === 'conflict' || localStatus === 'error' ? 'warn' : 'neutral'}>{!item.local ? 'No local snapshot' : localStatus ? localStatus.replaceAll('_', ' ') : 'Unknown'}</Badge></td><td><Badge tone={status?.status === 'eligible' ? 'good' : status?.status && status.status !== 'not_checked' && status.status !== 'local_only' ? 'warn' : 'neutral'}>{remoteStatusLabel(status?.status)}</Badge></td><td>{status?.card_present == null ? 'Not checked' : value(status.card_present)}</td><td>{value(item.local?.plan_count)}</td><td>{value(item.local?.active_rows)}</td><td>{value(item.local?.retained_stale_rows)}</td><td>{value(item.local?.latest_planned_upserts)}</td><td>{value(item.local?.latest_planned_stale_rows)}</td></tr>
        })}</tbody></table>
    </section>
  )
}

function NamespaceScreen({ remote }: { remote: RemoteState }) {
  const { namespace = '' } = useParams()
  const resource = useResource(() => api.namespace(namespace), [namespace])
  return (
    <>{resource.error ? <><PageTitle eyebrow="Namespace" title={namespace}>Review this local namespace snapshot.</PageTitle><ErrorState message={resource.error} retry={resource.retry} /></> : !resource.data ? <Loading label="Loading namespace detail…" /> : <NamespaceContent detail={resource.data} remote={remoteFor(namespace, remote.snapshot)} />}</>
  )
}

function NamespaceContent({ detail, remote }: { detail: NamespaceDetail; remote: RemoteNamespaceStatus | null }) {
  const item = detail.summary
  return (
    <>
      <PageTitle eyebrow="Namespace" title={item.namespace}>A searchable applied snapshot assembled from reviewed plans. Opening this screen performs no remote activity.</PageTitle>
      <div className="action-row"><Link className="button-link" to={`/search?namespace=${encodeURIComponent(item.namespace)}`}>Search this namespace</Link><Link className="secondary-link" to="/graphs">View graph roadmap</Link></div>
      <section className="metric-grid" aria-label="Namespace overview"><article className="metric"><span>Local state</span><strong>{item.local_status.replaceAll('_', ' ')}</strong></article><article className="metric"><span>Remote status</span><strong>{remote ? remoteStatusLabel(remote.status) : 'Not checked'}</strong></article><article className="metric"><span>Catalog status</span><strong>{remote ? remote.card_present === true ? 'Present' : remote.card_present === false ? 'Missing' : 'Not checked' : 'Not checked'}</strong></article><article className="metric"><span>Plans</span><strong>{item.plan_count}</strong></article><article className="metric"><span>Active rows</span><strong>{value(item.active_rows)}</strong></article><article className="metric"><span>Retained stale rows</span><strong>{value(item.retained_stale_rows)}</strong></article><article className="metric"><span>Documents / pages</span><strong>{value(item.document_count)}</strong></article><article className="metric"><span>Chunks</span><strong>{value(item.chunk_count)}</strong></article><article className="metric"><span>Latest plan</span><strong>{value(item.latest_plan_id)}</strong></article><article className="metric"><span>Latest apply</span><strong>{value(item.last_apply_id)}</strong></article><article className="metric"><span>Planned upserts</span><strong>{value(item.latest_planned_upserts)}</strong></article><article className="metric"><span>Planned stale</span><strong>{value(item.latest_planned_stale_rows)}</strong></article></section>
      <div className="two-column"><section className="panel"><h2>Safe source provenance</h2><Source source={item.source} /></section><section className="panel"><h2>Retrieval settings</h2><Retrieval settings={detail.retrieval} /></section></div>
      <section className="panel"><h2>Applied state</h2>{detail.state ? <dl className="details-grid"><div><dt>Updated</dt><dd>{timestamp(detail.state.updated_at)}</dd></div><div><dt>Last plan</dt><dd>{value(detail.state.last_plan_id)}</dd></div><div><dt>Active rows</dt><dd>{detail.state.active_rows}</dd></div><div><dt>Retained stale rows</dt><dd>{detail.state.retained_stale_rows}</dd></div></dl> : item.applied ? <p>Multiple applied-state identities claim this namespace. Applied-state identity is ambiguous, so row counts and last-apply details are unknown.</p> : <p>No applied state is present. Plans remain proposals until reviewed through the CLI workflow.</p>}</section>
      <section className="panel"><h2>Plans and diffs</h2>{detail.plans.length ? <div className="plan-detail-list">{detail.plans.map((plan) => <article key={plan.plan_id}><h3><Link to={`/plans/${encodeURIComponent(plan.plan_id)}`}>{plan.plan_id}</Link></h3><p>{timestamp(plan.created_at)}</p><Diff diff={plan.diff} /></article>)}</div> : <Empty>No saved plans are associated with this namespace.</Empty>}</section>
      <section className="panel placeholder-panel"><p className="eyebrow">Future capability</p><h2>Evidence-backed semantic graph</h2><p>No knowledge graph has been built for this namespace.</p><Link to="/graphs">See the proposed flow</Link></section>
      <WarningList title="Namespace warnings" items={item.warnings} />
    </>
  )
}

function Retrieval({ settings }: { settings: RetrievalSettings | null }) {
  if (!settings) return <p>Retrieval settings are unavailable.</p>
  return <dl className="details-grid"><div><dt>Embedding model</dt><dd>{value(settings.embedding_model)}</dd></div><div><dt>Precision</dt><dd>{value(settings.embedding_precision)}</dd></div><div><dt>Retrieval region</dt><dd>{value(settings.region)}</dd></div><div><dt>Ranking mode</dt><dd>{value(settings.ranking_mode)}</dd></div><div><dt>Profile</dt><dd>{value(settings.ranking_profile)}</dd></div><div><dt>Pool</dt><dd>{value(settings.ranking_pool)}</dd></div><div><dt>Aggregation</dt><dd>{value(settings.ranking_aggregation)}</dd></div></dl>
}

function Diff({ diff }: { diff: DiffSummary }) {
  const rows: Array<[string, number | boolean | null]> = [['First apply', diff.first_apply], ['Pages added', diff.pages_added], ['Pages changed', diff.pages_changed], ['Pages unchanged', diff.pages_unchanged], ['Pages removed', diff.pages_removed], ['Chunks unchanged', diff.chunks_unchanged], ['Chunks to embed', diff.chunks_to_embed], ['Rows to upsert', diff.rows_to_upsert], ['Stale rows', diff.stale_rows], ['Retained stale rows', diff.retained_stale_rows]]
  return <dl className="diff-grid">{rows.map(([label, count]) => <div key={label}><dt>{label}</dt><dd>{value(count)}</dd></div>)}</dl>
}

function Plans() {
  const resource = useResource(api.plans)
  return (
    <>
      <PageTitle eyebrow="Reviewed snapshots and proposals" title="Plan history">Saved plans are deterministic local artifacts: reviewed snapshots and proposed changes, not source-of-truth content.</PageTitle>
      {resource.error ? <ErrorState message={resource.error} retry={resource.retry} /> : !resource.data ? <Loading label="Loading plan history…" /> : !resource.data.items.length ? <Empty>Saved plan history will appear here.</Empty> : <PlanTable inventory={resource.data} />}
      {resource.data && <WarningList title="Artifact errors" items={resource.data.errors} />}
    </>
  )
}

function PlanTable({ inventory }: { inventory: PlanInventory }) {
  return <section className="table-wrap" aria-label={`${inventory.total} plans`}><table><thead><tr><th>Plan</th><th>Created</th><th>Namespace</th><th>Source</th><th>Pages</th><th>Chunks</th><th>Proposed rows</th><th>First apply</th><th>Source credentials</th><th>Source API calls</th></tr></thead><tbody>{inventory.items.map((plan) => <tr key={plan.plan_id}><th scope="row"><Link to={`/plans/${encodeURIComponent(plan.plan_id)}`}>{plan.plan_id}</Link></th><td>{timestamp(plan.created_at)}</td><td>{plan.namespace}</td><td>{sourceLabel(plan.source)}</td><td>{value(plan.page_count)}</td><td>{value(plan.chunk_count)}</td><td>{value(plan.diff.rows_to_upsert)}</td><td>{value(plan.diff.first_apply)}</td><td>{value(plan.source_activity.credentials_required)}</td><td>{value(plan.source_activity.api_calls_occurred)}</td></tr>)}</tbody></table></section>
}

function PlanScreen() {
  const { planId = '' } = useParams()
  const [chunkOffset, setChunkOffset] = useState(0)
  const [pageOffset, setPageOffset] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const [detail, setDetail] = useState<PlanDetail | null>(null)
  const [pages, setPages] = useState<PageInventory | null>(null)
  const [chunks, setChunks] = useState<ChunkInventory | null>(null)
  const [preview, setPreview] = useState<PagePreview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const selectedPage = useRef<{ planId: string; index: number } | null>(null)

  useEffect(() => {
    let current = true
    setDetail(null); setPages(null); setChunks(null); setPreview(null); setError(null); setPreviewError(null)
    Promise.all([api.plan(planId), api.pages(planId), api.chunks(planId, chunkOffset)]).then(async ([nextDetail, nextPages, nextChunks]) => {
      if (!current) return
      setDetail(nextDetail); setPages(nextPages); setChunks(nextChunks)
      if (nextPages.items.length) {
        setPreviewError(null)
        const retainedIndex = selectedPage.current?.planId === planId
          ? selectedPage.current.index
          : nextPages.items[0].index
        const previewIndex = nextPages.items.some((page) => page.index === retainedIndex)
          ? retainedIndex
          : nextPages.items[0].index
        selectedPage.current = { planId, index: previewIndex }
        try {
          const nextPreview = await api.page(planId, previewIndex)
          if (current) setPreview(nextPreview)
        } catch (reason) {
          if (current) setPreviewError(reason instanceof Error ? reason.message : 'Page preview could not be loaded.')
        }
      }
    }, (reason: unknown) => current && setError(reason instanceof Error ? reason.message : 'Plan detail could not be loaded.'))
    return () => { current = false }
  }, [planId, chunkOffset, attempt])

  useEffect(() => { setPageOffset(0); setChunkOffset(0) }, [planId])

  async function loadPreview(index: number) {
    selectedPage.current = { planId, index }
    setPreviewError(null)
    try { setPreview(await api.page(planId, index)) }
    catch (reason) { setPreviewError(reason instanceof Error ? reason.message : 'Page preview could not be loaded.') }
  }

  if (error) return <><PageTitle eyebrow="Plan" title={planId}>Review this saved plan artifact.</PageTitle><ErrorState message={error} retry={() => setAttempt((value) => value + 1)} /></>
  if (!detail || !pages || !chunks) return <Loading label="Loading plan detail and bounded previews…" />
  return <PlanContent detail={detail} pages={pages} chunks={chunks} preview={preview} previewError={previewError} loadPreview={loadPreview} pageOffset={pageOffset} setPageOffset={setPageOffset} chunkOffset={chunkOffset} setChunkOffset={setChunkOffset} />
}

function PlanContent({ detail, pages, chunks, preview, previewError, loadPreview, pageOffset, setPageOffset, chunkOffset, setChunkOffset }: { detail: PlanDetail; pages: PageInventory; chunks: ChunkInventory; preview: PagePreview | null; previewError: string | null; loadPreview: (index: number) => void; pageOffset: number; setPageOffset: (offset: number) => void; chunkOffset: number; setChunkOffset: (offset: number) => void }) {
  const plan = detail.summary
  const visiblePages = pages.items.slice(pageOffset, pageOffset + 20)
  const warehouse = plan.source.kind === 'database' && ['bigquery', 'snowflake'].includes(plan.source.database_backend ?? '')
  return (
    <>
      <PageTitle eyebrow="Plan artifact" title={plan.plan_id}>Review identity, provenance, proposed diff, and bounded plain-text evidence. Phase 1 is read only.</PageTitle>
      <p className="notice"><strong>Read-only review.</strong> This screen cannot apply a plan, change a namespace, or contact the source.</p>
      {warehouse && <p className="notice"><strong>Remote-source plan.</strong> This saved plan can be reviewed without reconnecting to the source warehouse.</p>}
      <section className="panel"><h2>Identity and provenance</h2><dl className="details-grid"><div><dt>Namespace</dt><dd><Link to={`/namespaces/${encodeURIComponent(plan.namespace)}`}>{plan.namespace}</Link></dd></div><div><dt>Candidate</dt><dd>{detail.namespace_candidate}</dd></div><div><dt>Site ID</dt><dd>{plan.site_id}</dd></div><div><dt>Created</dt><dd>{timestamp(plan.created_at)}</dd></div><div><dt>Artifact hash</dt><dd className="break-word">{value(detail.artifact_hash)}</dd></div><div><dt>Pages / chunks</dt><dd>{value(plan.page_count)} / {value(plan.chunk_count)}</dd></div></dl><Source source={plan.source} /></section>
      <div className="two-column"><section className="panel"><h2>Source activity when this plan was created</h2><dl className="details-grid"><div><dt>Source credentials required</dt><dd>{value(detail.source_activity.credentials_required)}</dd></div><div><dt>Source API calls occurred</dt><dd>{value(detail.source_activity.api_calls_occurred)}</dd></div></dl><p className="muted">These fields describe recorded plan creation activity, not activity from opening this page.</p></section><section className="panel"><h2>Embedding and retrieval contract</h2><Retrieval settings={detail.retrieval} /></section></div>
      <section className="panel"><h2>Proposed diff</h2><Diff diff={plan.diff} /></section>
      <section className="panel"><div className="section-heading"><h2>Pages and plain-text Markdown preview</h2><span>{pages.total ? `${pageOffset + 1}–${Math.min(pageOffset + visiblePages.length, pages.total)} of ${pages.total}` : '0 pages'}</span></div>{pages.items.length ? <><div className="page-selector" role="group" aria-label="Select page preview">{visiblePages.map((page) => <button className="secondary-button" type="button" key={page.index} onClick={() => loadPreview(page.index)}>{page.index + 1}. {page.title}</button>)}</div><div className="pagination"><button type="button" className="secondary-button" disabled={pageOffset === 0} onClick={() => setPageOffset(Math.max(0, pageOffset - 20))}>Previous pages</button><button type="button" className="secondary-button" disabled={pageOffset + visiblePages.length >= pages.total} onClick={() => setPageOffset(pageOffset + 20)}>Next pages</button></div>{previewError && <p role="alert" className="inline-error">{previewError} Select the page again to retry.</p>}{preview && <article className="preview"><h3>{preview.page.title}</h3><p><SafeLink href={preview.page.canonical_url}>{preview.page.canonical_url || 'Citation unavailable'}</SafeLink></p><pre>{preview.markdown}</pre>{preview.truncated && <p className="muted">Preview truncated by the server limit.</p>}</article>}</> : <Empty>This plan contains no page previews.</Empty>}</section>
      <section className="panel"><div className="section-heading"><h2>Chunk previews</h2><span>{chunks.total ? `${chunkOffset + 1}–${Math.min(chunkOffset + chunks.items.length, chunks.total)} of ${chunks.total}` : '0 chunks'}</span></div>{chunks.items.length ? <div className="chunk-list">{chunks.items.map((chunk) => <article key={chunk.index}><h3>{chunk.title || `Chunk ${chunk.index + 1}`}</h3><p>{chunk.section_path}</p><pre>{chunk.content}</pre><p className="muted"><SafeLink href={chunk.canonical_url}>{chunk.canonical_url || 'Citation unavailable'}</SafeLink>{chunk.truncated ? ' · Preview truncated' : ''}</p></article>)}</div> : <Empty>This plan contains no chunks.</Empty>}<div className="pagination"><button type="button" className="secondary-button" disabled={chunkOffset === 0} onClick={() => setChunkOffset(Math.max(0, chunkOffset - 10))}>Previous chunks</button><button type="button" className="secondary-button" disabled={chunkOffset + chunks.items.length >= chunks.total} onClick={() => setChunkOffset(chunkOffset + 10)}>Next chunks</button></div></section>
      <WarningList title="Plan warnings and errors" items={plan.warnings} />
    </>
  )
}

function Search() {
  const [parameters] = useSearchParams()
  const initialNamespace = parameters.get('namespace') ?? ''
  const [mode, setMode] = useState(initialNamespace ? 'explicit' : 'automatic')
  const [query, setQuery] = useState('')
  const [namespaces, setNamespaces] = useState(initialNamespace)
  const [topK, setTopK] = useState(5)
  const [routeTopK, setRouteTopK] = useState(3)
  const [candidates, setCandidates] = useState(200)
  const [docKind, setDocKind] = useState('')
  const [rankingMode, setRankingMode] = useState('')
  const [rankingProfile, setRankingProfile] = useState('')
  const [rankingPool, setRankingPool] = useState('')
  const [rankingAggregation, setRankingAggregation] = useState('')
  const [result, setResult] = useState<SearchResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [searching, setSearching] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError(null); setResult(null)
    const selected = namespaces.split(',').map((item) => item.trim()).filter(Boolean)
    if (!query.trim()) { setError('Enter a search query.'); return }
    if (mode === 'explicit' && !selected.length) { setError('Enter at least one explicit namespace.'); return }
    if (selected.length > 10) { setError('Enter at most 10 explicit namespaces.'); return }
    setSearching(true)
    const payload: Record<string, unknown> = { query, automatic: mode === 'automatic', namespaces: mode === 'explicit' ? selected : [], top_k: topK, candidates, route_top_k: mode === 'automatic' ? routeTopK : 3 }
    if (docKind.trim()) payload.doc_kind = docKind.trim()
    if (rankingMode) payload.ranking_mode = rankingMode
    if (rankingProfile) payload.ranking_profile = rankingProfile
    if (rankingPool) payload.ranking_pool = Number(rankingPool)
    if (rankingAggregation) payload.ranking_aggregation = rankingAggregation
    try {
      const response = await api.search(payload)
      setResult(response)
      if (response.state === 'error') setError(response.error?.message ?? 'Search could not be completed.')
    } catch (reason) {
      setError(reason instanceof RequestError ? reason.message : 'Search could not be completed.')
    } finally { setSearching(false) }
  }

  return (
    <>
      <PageTitle eyebrow="Explicit remote operation" title="Search">Search remote applied namespaces with citations. Explicit selection bypasses automatic routing.</PageTitle>
      <p className="notice"><strong>Execution impact.</strong> Submitting may read the process turbopuffer credential, make remote API calls, and load a local embedding model. It never writes. Merely opening this screen does none of those things.</p>
      <form className="panel search-form" onSubmit={submit}>
        <fieldset><legend>Routing</legend><label className="radio"><input type="radio" name="routing" value="automatic" checked={mode === 'automatic'} onChange={() => setMode('automatic')} /> Automatic catalog routing</label><label className="radio"><input type="radio" name="routing" value="explicit" checked={mode === 'explicit'} onChange={() => setMode('explicit')} /> Explicit namespaces</label></fieldset>
        <label className="full-width">Query <textarea maxLength={4000} required value={query} onChange={(event) => setQuery(event.target.value)} rows={3} /></label>
        {mode === 'explicit' ? <label className="full-width">Namespaces <input value={namespaces} onChange={(event) => setNamespaces(event.target.value)} placeholder="docs-one, docs-two" aria-describedby="namespace-help" /><small id="namespace-help">Comma-separated; at most 10. Explicit selection bypasses routing.</small></label> : <label>Namespaces selected by routing <input value="Automatic" disabled /></label>}
        {mode === 'automatic' && <label>Route top K <input type="number" min="1" max="10" value={routeTopK} onChange={(event) => setRouteTopK(Number(event.target.value))} /></label>}
        <label>Result top K <input type="number" min="1" max="100" value={topK} onChange={(event) => setTopK(Number(event.target.value))} /></label>
        <label>Candidate pool <input type="number" min="1" max="1000" value={candidates} onChange={(event) => setCandidates(Number(event.target.value))} /></label>
        <details className="full-width"><summary>Ranking filters and overrides</summary><div className="form-grid"><label>Document kind <input maxLength={128} value={docKind} onChange={(event) => setDocKind(event.target.value)} /></label><label>Ranking mode <select value={rankingMode} onChange={(event) => setRankingMode(event.target.value)}><option value="">Namespace default</option><option value="chunk">Chunk</option><option value="file">File</option><option value="page">Page</option></select></label><label>Ranking profile <select value={rankingProfile} onChange={(event) => setRankingProfile(event.target.value)}><option value="">Namespace default</option><option value="none">None</option><option value="repo_code">Repository code</option></select></label><label>Ranking pool <input type="number" min="1" max="1000" value={rankingPool} onChange={(event) => setRankingPool(event.target.value)} /></label><label>Aggregation <select value={rankingAggregation} onChange={(event) => setRankingAggregation(event.target.value)}><option value="">Namespace default</option><option value="max">Max</option><option value="adaptive_sum_3">Adaptive sum 3</option><option value="capped_sum_3">Capped sum 3</option></select></label></div></details>
        <button type="submit" disabled={searching}>{searching ? 'Searching…' : 'Run search'}</button>
      </form>
      {searching && <Loading label="Searching remote namespaces…" />}
      {error && <p className="state-card error-state" role="alert"><strong>Search was not completed.</strong> {error} Check the inputs or process credentials, then try again.</p>}
      {result && <SearchResults result={result} />}
    </>
  )
}

function SearchResults({ result }: { result: SearchResponse }) {
  const diagnostics = Object.keys(result.diagnostics).length ? JSON.stringify(result.diagnostics, null, 2) : 'No diagnostics were returned.'
  return (
    <section className="panel" aria-labelledby="results-heading"><div className="section-heading"><h2 id="results-heading">Search results</h2><Badge tone={result.state === 'success' ? 'good' : 'bad'}>{result.state}</Badge></div><p className="notice">Routing: {result.automatic ? 'Automatic' : 'Explicit'}. Credentials required: {value(result.credentials_required)}. API calls occurred: {value(result.api_calls_occurred)}. Writes occurred: {value(result.writes_occurred)}.</p><p>Namespaces: {result.namespaces.length ? result.namespaces.join(', ') : 'None selected'}</p><h3>Safe diagnostics</h3><pre aria-label="Search diagnostics">{diagnostics}</pre>{result.state === 'success' && !result.hits.length ? <Empty>No matching evidence was returned. Refine the query or selection and search again.</Empty> : <ol className="result-list">{result.hits.map((hit, index) => <li key={`${hit.namespace}-${index}`}><article><div className="result-heading"><h3>{hit.title || 'Untitled result'}</h3><Badge>{hit.namespace}</Badge></div>{hit.section && <p className="eyebrow">{hit.section}</p>}<dl className="details-grid"><div><dt>Score</dt><dd><pre aria-label={`Score for ${hit.title || 'result'}`}>{Object.keys(hit.score).length ? JSON.stringify(hit.score, null, 2) : 'No score diagnostics were returned.'}</pre></dd></div></dl><pre>{hit.content_preview}</pre>{hit.content_truncated && <p className="muted">Content preview truncated.</p>}<p><SafeLink href={hit.citation}>{hit.citation || 'Citation unavailable'}</SafeLink></p>{hit.tags.length > 0 && <ul className="tag-list" aria-label="Tags">{hit.tags.map((tag) => <li key={tag}>{tag}</li>)}</ul>}</article></li>)}</ol>}</section>
  )
}

function Graphs() {
  return (
    <>
      <PageTitle eyebrow="Future capability" title="Evidence-backed semantic graphs">Phase 1 labels the future path without extracting, storing, editing, or fabricating graph data.</PageTitle>
      <p className="notice"><strong>No graph data exists in Command Center Phase 1.</strong> The cards below describe a proposed evidence flow only.</p>
      <section className="flow" aria-label="Future evidence-backed graph flow">
        <article><span>1</span><h2>Select namespaces</h2><p>Choose searchable applied snapshots with known provenance and compatibility.</p></article>
        <div aria-hidden="true">→</div>
        <article><span>2</span><h2>Derive an evidence-backed graph snapshot</h2><p>Future assertions must remain linked to exact namespace evidence and extraction provenance.</p></article>
        <div aria-hidden="true">→</div>
        <article><span>3</span><h2>Explore taxonomy and ontology</h2><p>Future navigation may inspect governed terms and relationships without replacing source authority.</p></article>
      </section>
      <section className="panel"><h2>Product boundary</h2><p>Sources originate knowledge. Plans are reviewed snapshots and proposed changes. Namespaces are searchable applied snapshots. Catalog cards describe and route to namespaces. Any future graph will be a derived semantic model backed by namespace evidence.</p></section>
    </>
  )
}

export default App
