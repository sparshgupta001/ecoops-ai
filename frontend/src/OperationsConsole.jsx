import { useEffect, useMemo, useState } from 'react'
import {
  Activity, AlertTriangle, ArrowDownToLine, BookOpen, Check, CheckCircle2, ChevronRight,
  CircleDot, Clock3, CloudRain, Command, Database, Droplets, FileText, Gauge,
  LayoutDashboard, ListChecks, MapPin, Menu, Radio, RefreshCw, Search, ShieldCheck,
  SlidersHorizontal, Workflow, X, XCircle, Zap,
} from 'lucide-react'
import './App.css'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const NAV_ITEMS = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'Live Monitor', icon: Radio },
  { label: 'Agent Control Tower', icon: Workflow },
  { label: 'Risk Simulator', icon: SlidersHorizontal },
  { label: 'Incident Command', icon: ShieldCheck },
  { label: 'Knowledge & Evidence', icon: BookOpen },
  { label: 'Analytics & Audit', icon: Activity },
]
const ZONES = [
  { name: 'Block A', detail: 'Undergraduate hub', column: 'zone-a' },
  { name: 'Block C', detail: 'Engineering and labs', column: 'zone-c' },
  { name: 'Gate 2', detail: 'Student access route', column: 'gate-2' },
  { name: 'Parking Zone C', detail: 'Near the drainage line', column: 'parking-c' },
  { name: 'Service corridors', detail: 'Behind the Science Center', column: 'service' },
]
const DEFAULT_SCENARIO = { location: 'Block C', rainfall: 82, water_level: 54, forecast: 'heavy', drainage_capacity: 75, drainage_blockage: 10 }
const STAGE_LABELS = {
  risk_assessment: 'Risk assessment', impact_analysis: 'Impact analysis', knowledge_retrieval: 'Knowledge retrieval',
  response_planning: 'Response planning', human_approval: 'Human approval', notification: 'Notification',
}

async function request(path, options) {
  const response = await fetch(`${API_BASE}${path}`, options)
  const contentType = response.headers.get('content-type') || ''
  const body = contentType.includes('application/json') ? await response.json() : await response.text()
  if (!response.ok) throw new Error(body?.detail || body?.error || `Request failed (${response.status})`)
  return body
}

export default function OperationsConsole() {
  const [activePage, setActivePage] = useState('Overview')
  const [data, setData] = useState({ incidents: [], monitor: null, executions: [], knowledge: null, analytics: null })
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [selectedZone, setSelectedZone] = useState('Block C')
  const [selectedIncidentId, setSelectedIncidentId] = useState('')
  const [selectedExecutionId, setSelectedExecutionId] = useState('')

  const loadData = async (quiet = false) => {
    if (quiet) setRefreshing(true)
    const endpoints = [['incidents', '/api/incidents'], ['monitor', '/api/monitor'], ['executions', '/api/executions'], ['knowledge', '/api/knowledge'], ['analytics', '/api/analytics']]
    const results = await Promise.allSettled(endpoints.map(([, path]) => request(path)))
    setError('')
    const next = {}
    const errors = []
    results.forEach((result, index) => {
      const [key] = endpoints[index]
      if (result.status === 'fulfilled') next[key] = result.value
      else {
        next[key] = key === 'incidents' || key === 'executions' ? [] : null
        errors.push(result.reason.message)
      }
    })
    setData((current) => ({ ...current, ...next }))
    if (errors.length) setError(`Some operational data could not be loaded: ${errors.join('; ')}`)
    setLoading(false)
    setRefreshing(false)
  }

  useEffect(() => { queueMicrotask(() => { void loadData() }) }, [])
  const activeIncidents = data.incidents.filter((incident) => !['rejected', 'resolved'].includes(incident.status))
  const selectedIncident = data.incidents.find((item) => item.incident_id === selectedIncidentId) || data.incidents[0]
  const pageTitle = NAV_ITEMS.find((item) => item.label === activePage)
  const navigate = (page) => { setActivePage(page); setMobileNavOpen(false) }
  const reviewIncident = (incident) => { setSelectedIncidentId(incident.incident_id); navigate('Incident Command') }
  const onDecision = async (incidentId, approved) => {
    await request(`/api/incidents/${incidentId}/approve`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ approved, reviewer: 'operations-console' }) })
    await loadData(true)
  }
  const onTaskStatus = async (incidentId, taskId, status) => {
    await request(`/api/incidents/${incidentId}/tasks/${taskId}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }) })
    await loadData(true)
  }

  let content
  if (loading && !data.monitor && !data.incidents.length) content = <LoadingState label="Connecting to local operations API" />
  else if (activePage === 'Overview') content = <OverviewPage data={data} activeIncidents={activeIncidents} onZone={setSelectedZone} selectedZone={selectedZone} onIncident={reviewIncident} />
  else if (activePage === 'Live Monitor') content = <MonitorPage data={data} onIncident={reviewIncident} />
  else if (activePage === 'Agent Control Tower') content = <ControlTowerPage data={data} selectedId={selectedExecutionId} onSelect={setSelectedExecutionId} />
  else if (activePage === 'Risk Simulator') content = <SimulatorPage />
  else if (activePage === 'Incident Command') content = <IncidentPage incidents={data.incidents} selectedIncident={selectedIncident} selectedId={selectedIncidentId} onSelect={setSelectedIncidentId} onDecision={onDecision} onTaskStatus={onTaskStatus} />
  else if (activePage === 'Knowledge & Evidence') content = <KnowledgePage knowledge={data.knowledge} />
  else content = <AnalyticsPage analytics={data.analytics} />

  return <div className="app-shell">
    {mobileNavOpen && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)} />}
    <aside className={`sidebar ${mobileNavOpen ? 'sidebar-open' : ''}`}>
      <div className="brand-lockup"><div className="brand-mark"><Command size={19} /></div><div><strong>ecoops<span> / </span>ai</strong><small>ENVIRONMENTAL OPERATIONS</small></div><button className="icon-button sidebar-close" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)}><X size={18} /></button></div>
      <div className="workspace-label">WORKSPACE <span>LOCAL</span></div>
      <nav className="primary-nav" aria-label="Primary navigation">{NAV_ITEMS.map(({ label, icon: Icon }) => <button key={label} className={`nav-item ${activePage === label ? 'nav-item-active' : ''}`} onClick={() => navigate(label)} aria-current={activePage === label ? 'page' : undefined}><Icon size={17} /><span>{label}</span>{label === 'Incident Command' && activeIncidents.length > 0 && <span className="nav-count">{activeIncidents.length}</span>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="connection-card"><span className="connection-indicator" /><div><strong>LOCAL DEMO MODE</strong><small>No live sensor feed</small></div></div><div className="sidebar-foot"><Database size={13} /><span>Local records · optional AWS</span></div></div>
    </aside>
    <main className="main-panel">
      <header className="topbar"><button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMobileNavOpen(true)}><Menu size={20} /></button><div className="breadcrumb"><span>EcoOps</span><ChevronRight size={14} /><strong>{activePage}</strong></div><div className="topbar-actions"><span className="data-mode"><span />Scenario data</span><button className="icon-button refresh-button" aria-label="Refresh operational data" title="Refresh data" onClick={() => loadData(true)} disabled={refreshing}><RefreshCw size={16} className={refreshing ? 'spin' : ''} /></button></div></header>
      <div className="page-content"><div className="page-heading"><div><p className="section-kicker">ENVIRONMENTAL INTELLIGENCE</p><h1>{pageTitle?.label || activePage}</h1></div>{activePage === 'Overview' && <div className="freshness"><Clock3 size={14} /><span>{data.monitor?.data_freshness ? `Last record ${formatTime(data.monitor.data_freshness)}` : 'No recorded readings'}</span></div>}</div>
        {error && <div className="notice notice-error" role="alert"><AlertTriangle size={16} /><span>{error}</span><button className="notice-dismiss" aria-label="Dismiss error" onClick={() => setError('')}><X size={15} /></button></div>}
        {content}<footer className="page-footer"><span>EcoOps AI</span><span>Stored records and user-run scenarios · no connected sensors</span></footer>
      </div>
    </main>
  </div>
}

function OverviewPage({ data, activeIncidents, onZone, selectedZone, onIncident }) {
  const pending = activeIncidents.filter((incident) => incident.status === 'pending_approval').length
  const highRisk = activeIncidents.filter((incident) => ['HIGH', 'CRITICAL'].includes(incident.severity)).length
  const readings = data.monitor?.latest_readings
  const selectedIncident = data.incidents.find((incident) => incident.location.toLowerCase().includes(selectedZone.toLowerCase()))
  return <div className="page-stack">
    <div className="metric-grid"><Metric icon={AlertTriangle} label="Active incidents" value={activeIncidents.length} detail="Stored incident records" tone="orange" /><Metric icon={ShieldCheck} label="Awaiting approval" value={pending} detail="Human decision required" tone="amber" /><Metric icon={Zap} label="High / critical" value={highRisk} detail="Current incident records" tone="red" /><Metric icon={Droplets} label="Latest rainfall" value={readings ? `${readings.rainfall} mm` : '—'} detail={readings ? `Scenario · ${readings.location}` : 'No recorded reading'} tone="teal" /></div>
    <div className="overview-grid">
      <section className="surface map-surface"><SectionHeader title="Campus risk map" detail="Schematic · not geographically scaled" icon={MapPin} /><div className="map-layout"><div className="campus-schematic" role="group" aria-label="Select a campus zone. Schematic map, not geographically scaled."><div className="map-road map-road-horizontal" /><div className="map-road map-road-vertical" />{ZONES.map((zone, index) => { const incident = data.incidents.find((item) => item.location.toLowerCase().includes(zone.name.toLowerCase())); const level = incident?.severity?.toLowerCase() || 'unknown'; return <button key={zone.name} className={`zone-node ${zone.column} zone-${level} ${selectedZone === zone.name ? 'zone-selected' : ''}`} onClick={() => onZone(zone.name)} aria-pressed={selectedZone === zone.name}><span className="zone-pin"><span /></span><strong>{zone.name}</strong><small>{incident ? `${incident.severity} · recorded incident` : `Zone ${String(index + 1).padStart(2, '0')} · no incident record`}</small></button> })}<span className="map-label map-label-north">NORTH CAMPUS</span><span className="map-scale">Schematic only</span></div><div className="zone-inspector"><div className="inspector-label">SELECTED ZONE</div><h3>{selectedZone}</h3><p>{ZONES.find((zone) => zone.name === selectedZone)?.detail}</p>{selectedIncident ? <div className="zone-data"><StatusPill value={selectedIncident.severity} /><DataLine label="Rainfall" value={`${selectedIncident.environmental_data?.rainfall ?? '—'} mm`} /><DataLine label="Water level" value={`${selectedIncident.environmental_data?.water_level ?? '—'}%`} /><button className="text-action" onClick={() => onIncident(selectedIncident)}>Open incident <ChevronRight size={14} /></button></div> : <div className="empty-inline"><CircleDot size={15} /><span>No incident-linked readings are stored for this zone.</span></div>}</div></div><div className="map-legend"><Legend tone="critical" label="Critical" /><Legend tone="high" label="High" /><Legend tone="medium" label="Medium" /><Legend tone="low" label="Low" /><Legend tone="unknown" label="No record" /></div></section>
      <section className="surface distribution-surface"><SectionHeader title="Risk distribution" detail="Stored incidents by deterministic severity" icon={Gauge} /><SeverityChart incidents={data.incidents} /><div className="distribution-foot"><span>Threshold-derived severity, not calibrated probability.</span><span>{data.incidents.length} records</span></div></section>
    </div>
    <div className="overview-grid overview-grid-lower"><section className="surface trend-surface"><SectionHeader title="Incident trend" detail="Daily count from stored timestamps" icon={Activity} /><TrendChart points={data.analytics?.by_day || []} /></section><section className="surface readings-surface"><SectionHeader title="Latest environmental record" detail="Local scenario input · not a live sensor" icon={CloudRain} />{readings ? <div className="reading-list"><DataLine label="Location" value={readings.location} /><DataLine label="Rainfall" value={`${readings.rainfall} mm`} /><DataLine label="Water level" value={`${readings.water_level}%`} /><DataLine label="Forecast input" value={readings.forecast || 'normal'} /><div className="reading-source">Source: user-run analysis · {formatTime(data.monitor?.data_freshness)}</div></div> : <EmptyState icon={Droplets} title="No environmental records" detail="Run an analysis to create the first reading." />}</section></div>
    <section className="surface"><SectionHeader title="Recent incident timeline" detail="Most recently recorded incidents" icon={Clock3} action={<button className="text-action" onClick={() => data.incidents[0] && onIncident(data.incidents[0])} disabled={!data.incidents.length}>Open command center <ChevronRight size={14} /></button>} />{data.incidents.length ? <IncidentTimeline incidents={data.incidents.slice().sort((a, b) => b.timestamp.localeCompare(a.timestamp)).slice(0, 5)} onIncident={onIncident} /> : <EmptyState icon={ListChecks} title="No incidents recorded" detail="Incidents are created when analyses cross the existing high-risk thresholds." />}</section>
  </div>
}

function MonitorPage({ data, onIncident }) {
  const monitor = data.monitor
  const readings = monitor?.latest_readings
  const isLive = Boolean(monitor && !monitor.demo_mode && monitor.sensor_observation)
  const sensor = monitor?.sensor_observation

  return (
    <div className="page-stack">
      {isLive ? (
        <div className="notice notice-success">
          <Activity size={16} />
          <span>
            <strong>Live Sensor Telemetry Active.</strong> Ingested from sensor <code>{sensor?.sensor_id}</code> via <code>{sensor?.source}</code>. Provenance tracked and persisted locally.
          </span>
        </div>
      ) : (
        <div className="notice notice-neutral">
          <Radio size={16} />
          <span>
            <strong>Demo Fallback Mode.</strong> No live telemetry feed connected yet. Showing stored local scenario inputs as demo fallback. Submit readings to <code>POST /api/sensors/ingest</code> to activate live telemetry.
          </span>
        </div>
      )}

      <div className="two-column-layout">
        <section className="surface">
          <SectionHeader
            title={isLive ? "Latest sensor observation" : "Latest observed input"}
            detail={monitor?.data_freshness ? `Recorded ${formatTime(monitor.data_freshness)}` : 'No recorded input'}
            icon={isLive ? Activity : Droplets}
          />
          {readings ? (
            <div className="monitor-reading-grid">
              <ReadingTile label="Location" value={readings.location} icon={MapPin} />
              <ReadingTile label="Rainfall" value={readings.rainfall} unit="mm" icon={CloudRain} />
              <ReadingTile label="Standing water" value={readings.water_level} unit="%" icon={Droplets} />
              <ReadingTile label="Forecast" value={readings.forecast || 'normal'} unit="input" icon={Activity} />
            </div>
          ) : (
            <EmptyState icon={Database} title="Waiting for a stored observation" detail="Submit a sensor observation or run a scenario." />
          )}
        </section>

        <section className="surface">
          <SectionHeader title="Data provenance" detail="Current runtime source" icon={Database} />
          <div className="provenance-list">
            <DataLine label="Operating Mode" value={isLive ? "Live Telemetry" : "Demo Fallback"} />
            <DataLine label="Sensor Feed" value={isLive ? (sensor?.sensor_id || 'Active') : 'Demo Fallback (No live feed)'} />
            <DataLine label="Telemetry Source" value={isLive ? (sensor?.source || 'Local Ingest') : 'Stored scenario input'} />
            <DataLine label="Sensor Timestamp" value={sensor?.timestamp ? formatTime(sensor.timestamp) : (monitor?.data_freshness ? formatTime(monitor.data_freshness) : 'None')} />
            {isLive && sensor?.ingested_at && <DataLine label="Ingested At" value={formatTime(sensor.ingested_at)} />}
          </div>
        </section>
      </div>

      {monitor?.recent_sensor_observations?.length > 0 && (
        <section className="surface">
          <SectionHeader
            title="Recent sensor telemetry observations"
            detail={`${monitor.recent_sensor_observations.length} local observations ingested`}
            icon={Activity}
          />
          <SensorObservationList observations={monitor.recent_sensor_observations} />
        </section>
      )}

      <section className="surface">
        <SectionHeader title="Recorded investigation runs" detail={`${monitor?.recent_executions?.length || 0} most recent executions`} icon={Workflow} />
        {monitor?.recent_executions?.length ? <ExecutionList executions={monitor.recent_executions} /> : <EmptyState icon={Radio} title="No recorded runs" detail="A record is created when an analysis is submitted." />}
      </section>

      {data.incidents.length > 0 && (
        <section className="surface">
          <SectionHeader title="Incident-linked observations" detail="Open the incident to inspect its inputs" icon={AlertTriangle} />
          <IncidentTimeline incidents={data.incidents.slice(0, 5)} onIncident={onIncident} />
        </section>
      )}
    </div>
  )
}

function SensorObservationList({ observations }) {
  return (
    <div className="monitor-execution-list">
      {observations.map((obs) => (
        <div className="monitor-execution" key={obs.id}>
          <span className="execution-select-icon">
            <Radio size={15} />
          </span>
          <div>
            <strong>{obs.sensor_id} · {obs.location}</strong>
            <small>
              {obs.rainfall} mm rain · {obs.water_level}% water · {obs.source} · {formatTime(obs.timestamp)}
            </small>
          </div>
          <StatusPill value="ingested" />
        </div>
      ))}
    </div>
  )
}

function ControlTowerPage({ data, selectedId, onSelect }) {
  const executions = data.executions || []
  const selected = executions.find((execution) => execution.execution_id === selectedId) || executions[0]
  return <div className="page-stack"><div className="notice notice-neutral"><Workflow size={16} /><span>Transparent sequential Python orchestration. AI mode identifies only the interpretation provider; risk and other stages are deterministic functions.</span></div><div className="control-layout"><section className="surface execution-list-panel"><SectionHeader title="Investigations" detail={`${executions.length} stored runs`} icon={ListChecks} />{executions.length ? executions.map((execution) => <button key={execution.execution_id} className={`execution-select ${selected?.execution_id === execution.execution_id ? 'execution-selected' : ''}`} onClick={() => onSelect(execution.execution_id)}><span className="execution-select-icon"><Workflow size={16} /></span><span className="execution-select-copy"><strong>{execution.input?.location || 'Unknown location'}</strong><small>{execution.execution_id} · {formatTime(execution.started_at)}</small></span><StatusPill value={execution.status} /></button>) : <EmptyState icon={Workflow} title="No execution traces" detail="Submit an analysis to record real stage outputs." />}</section><section className="surface trace-panel">{selected ? <><div className="trace-heading"><div><p className="section-kicker">EXECUTION TRACE</p><h2>{selected.execution_id}</h2></div><StatusPill value={selected.status} /></div><div className="trace-meta"><span>{selected.orchestration?.replaceAll('_', ' ')}</span><span>AI mode: {selected.ai_mode || 'not recorded'}</span><span>Started {formatTime(selected.started_at)}</span></div><div className="stage-list">{(selected.stages || []).map((stage, index) => <StageCard key={`${stage.stage}-${index}`} stage={stage} index={index} />)}</div></> : <EmptyState icon={Workflow} title="Select an investigation" detail="Inspect actual stage input, output, timing, and evidence references." />}</section></div></div>
}

function StageCard({ stage, index }) {
  const [expanded, setExpanded] = useState(index === 0)
  const status = (stage.status || 'unknown').toLowerCase()
  const icon = status === 'completed' ? <Check size={15} /> : status === 'failed' ? <X size={15} /> : status === 'awaiting_approval' ? <Clock3 size={15} /> : <CircleDot size={15} />
  return <article className={`stage-card stage-${status}`}><button className="stage-summary" onClick={() => setExpanded(!expanded)} aria-expanded={expanded}><span className="stage-index">{icon}</span><span className="stage-main"><strong>{STAGE_LABELS[stage.stage] || stage.stage}</strong><small>{stage.status?.replaceAll('_', ' ')}</small></span><span className="stage-time">{stage.started_at ? formatTime(stage.started_at) : 'Not started'}</span><ChevronRight size={16} className={expanded ? 'rotate-90' : ''} /></button>{expanded && <div className="stage-details"><StructuredData label="Input" value={stage.input} /><StructuredData label="Output" value={stage.output} />{stage.evidence_references?.length > 0 && <div className="stage-evidence"><span>Evidence references</span>{stage.evidence_references.map((reference) => <code key={reference}>{reference}</code>)}</div>}{stage.error && <div className="stage-error"><AlertTriangle size={14} />{stage.error}</div>}{stage.completed_at && <div className="stage-completed">Completed {formatTime(stage.completed_at)}</div>}</div>}</article>
}

function SimulatorPage() {
  const [scenario, setScenario] = useState(DEFAULT_SCENARIO)
  const [runs, setRuns] = useState([])
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const update = (key, value) => setScenario((current) => ({ ...current, [key]: value }))
  const runScenario = async () => {
    setRunning(true); setError('')
    try {
      const result = await request('/api/scenarios/simulate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(scenario) })
      setRuns((current) => [{ id: crypto.randomUUID(), result }, ...current].slice(0, 4))
    } catch (err) { setError(err.message) } finally { setRunning(false) }
  }
  const reset = () => { setScenario(DEFAULT_SCENARIO); setRuns([]); setError('') }
  return <div className="page-stack"><div className="notice notice-neutral"><SlidersHorizontal size={16} /><span><strong>What-if simulation.</strong> Deterministic threshold results; not a calibrated forecast. Runs do not create incidents, persist records, call Bedrock, or send notifications.</span></div><div className="simulator-layout"><section className="surface simulator-controls"><SectionHeader title="Scenario inputs" detail="All values are simulated" icon={SlidersHorizontal} /><label className="field-label" htmlFor="sim-location">Location</label><select id="sim-location" value={scenario.location} onChange={(event) => update('location', event.target.value)}>{ZONES.map((zone) => <option key={zone.name}>{zone.name}</option>)}</select><RangeField label="Rainfall intensity" value={scenario.rainfall} min={0} max={200} unit="mm" onChange={(value) => update('rainfall', value)} /><RangeField label="Water level" value={scenario.water_level} min={0} max={100} unit="%" onChange={(value) => update('water_level', value)} /><div className="control-field"><label className="field-label" htmlFor="forecast">Forecast severity</label><select id="forecast" value={scenario.forecast} onChange={(event) => update('forecast', event.target.value)}><option value="normal">Normal</option><option value="watch">Watch</option><option value="heavy">Heavy</option><option value="extreme">Extreme</option></select></div><RangeField label="Drainage capacity" value={scenario.drainage_capacity} min={0} max={100} unit="%" onChange={(value) => update('drainage_capacity', value)} /><RangeField label="Drainage blockage" value={scenario.drainage_blockage} min={0} max={100} unit="%" onChange={(value) => update('drainage_blockage', value)} /><div className="sim-controls-footer"><button className="button-primary" onClick={runScenario} disabled={running}>{running ? <RefreshCw size={16} className="spin" /> : <Zap size={16} />}{running ? 'Calculating' : 'Run scenario'}</button><button className="button-quiet" onClick={reset}>Reset</button></div>{error && <div className="inline-error" role="alert">{error}</div>}</section><section className="surface simulation-results"><SectionHeader title="Scenario comparison" detail={`${runs.length} of 4 runs retained in this session`} icon={Activity} />{runs.length ? <div className="scenario-results">{runs.map((run, index) => <ScenarioResult key={run.id} run={run} previous={runs[index + 1]?.result} current={index === 0} />)}</div> : <EmptyState icon={CloudRain} title="No scenarios run" detail="Adjust controls and run a scenario. Results compare with the previous run." />}</section></div></div>
}

function ScenarioResult({ run, previous, current }) {
  const result = run.result
  const assessment = result.risk_assessment
  const delta = previous ? severityRank(assessment.severity) - severityRank(previous.risk_assessment.severity) : null
  return <article className={`scenario-card ${current ? 'scenario-current' : ''}`}><div className="scenario-card-heading"><div><span className="scenario-stamp">{current ? 'LATEST RUN' : 'COMPARISON'}</span><h3>{result.input.location}</h3></div><StatusPill value={assessment.severity} /></div><div className="scenario-facts"><DataLine label="Rainfall" value={`${result.input.rainfall} mm`} /><DataLine label="Observed water" value={`${result.input.water_level}%`} /><DataLine label="Effective water" value={`${assessment.effective_water_level}%`} /><DataLine label="Forecast input" value={result.input.forecast} /><DataLine label="Drainage adjustment" value={`+${assessment.drainage_adjustment} pts`} /></div>{delta !== null && <div className={`scenario-delta ${delta > 0 ? 'delta-up' : delta < 0 ? 'delta-down' : ''}`}>{delta > 0 ? `Severity increased ${delta} level${delta === 1 ? '' : 's'}` : delta < 0 ? `Severity decreased ${Math.abs(delta)} level${delta === -1 ? '' : 's'}` : 'Severity unchanged'} vs. prior run</div>}<div className="scenario-actions"><strong>Recommended response</strong><ul>{result.response_plan.recommended_actions.map((action) => <li key={action}>{action}</li>)}</ul></div><div className="scenario-impact"><span>Impact categories</span><div>{result.impact_analysis.impact.map((item) => <span key={item}>{item}</span>)}</div></div></article>
}

function IncidentPage({ incidents, selectedIncident, selectedId, onSelect, onDecision, onTaskStatus }) {
  const [search, setSearch] = useState('')
  const [severity, setSeverity] = useState('all')
  const [actionError, setActionError] = useState('')
  const filtered = useMemo(() => incidents.filter((incident) => `${incident.incident_id} ${incident.location}`.toLowerCase().includes(search.toLowerCase()) && (severity === 'all' || incident.severity === severity)), [incidents, search, severity])
  const decide = async (approved) => { setActionError(''); try { await onDecision(selectedIncident.incident_id, approved) } catch (err) { setActionError(err.message) } }
  const updateTask = async (task, status) => { setActionError(''); try { await onTaskStatus(selectedIncident.incident_id, task.task_id, status) } catch (err) { setActionError(err.message) } }
  return <div className="page-stack"><div className="incident-toolbar surface"><label className="search-box"><Search size={16} /><input aria-label="Search incidents" placeholder="Search location or incident ID" value={search} onChange={(event) => setSearch(event.target.value)} /></label><label className="filter-box"><span>Severity</span><select aria-label="Filter by severity" value={severity} onChange={(event) => setSeverity(event.target.value)}><option value="all">All severities</option><option>CRITICAL</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select></label><span className="record-count">{filtered.length} records</span></div><div className="incident-layout"><section className="surface incident-list-panel"><SectionHeader title="Incident register" detail="Stored incidents · newest first" icon={ShieldCheck} />{filtered.length ? filtered.slice().sort((a, b) => b.timestamp.localeCompare(a.timestamp)).map((incident) => <button key={incident.incident_id} className={`incident-select ${selectedIncident?.incident_id === incident.incident_id || selectedId === incident.incident_id ? 'incident-selected' : ''}`} onClick={() => onSelect(incident.incident_id)}><SeverityMarker severity={incident.severity} /><span className="incident-select-copy"><strong>{incident.location}</strong><small>{incident.incident_id} · {formatTime(incident.timestamp)}</small></span><StatusPill value={incident.status} /></button>) : <EmptyState icon={Search} title="No matching incidents" detail="Adjust the filter or run a qualifying analysis." />}</section><section className="surface incident-detail-panel">{selectedIncident ? <><div className="detail-heading"><div><p className="section-kicker">INCIDENT DETAIL</p><h2>{selectedIncident.location}</h2><small>{selectedIncident.incident_id}</small></div><StatusPill value={selectedIncident.status} /></div>{actionError && <div className="inline-error" role="alert">{actionError}</div>}<div className="detail-stats"><DetailStat label="Severity" value={selectedIncident.severity} /><DetailStat label="Risk type" value={selectedIncident.risk_type} /><DetailStat label="Detected" value={formatTime(selectedIncident.timestamp)} /></div><div className="approval-row"><div><strong>Human review</strong><small>{selectedIncident.approval_reviewer ? `Reviewed by ${selectedIncident.approval_reviewer}` : 'External notification requires an approval decision'}</small></div>{selectedIncident.status === 'pending_approval' ? <div className="button-row"><button className="button-primary button-compact" onClick={() => decide(true)}><Check size={15} />Approve</button><button className="button-danger button-compact" onClick={() => decide(false)}><X size={15} />Reject</button></div> : <StatusPill value={selectedIncident.status} />}</div><div className="detail-section"><SectionHeader title="Environmental input" detail="Recorded with the analysis" icon={Droplets} /><div className="detail-reading-grid"><DataLine label="Rainfall" value={`${selectedIncident.environmental_data?.rainfall ?? '—'} mm`} /><DataLine label="Water level" value={`${selectedIncident.environmental_data?.water_level ?? '—'}%`} /><DataLine label="Forecast" value={selectedIncident.environmental_data?.forecast || '—'} /><DataLine label="Captured" value={formatTime(selectedIncident.timestamp)} /></div></div><div className="detail-section"><SectionHeader title="Response tasks" detail="Task progress is recorded in the incident audit" icon={ListChecks} />{selectedIncident.tasks?.length ? <div className="task-list">{selectedIncident.tasks.map((task) => <TaskRow key={task.task_id} task={task} disabled={selectedIncident.status !== 'approved'} onStatus={(status) => updateTask(task, status)} />)}</div> : <p className="empty-caption">No tracked tasks are attached to this incident.</p>}</div><div className="detail-section"><SectionHeader title="Evidence and interpretation" detail="Incident-level evidence, not action-specific citations" icon={FileText} />{selectedIncident.ai_summary?.evidence?.length ? selectedIncident.ai_summary.evidence.map((evidence, index) => <EvidenceQuote key={`${evidence.source}-${index}`} evidence={evidence} />) : <div className="empty-inline"><FileText size={15} /><span>No retrieved document evidence was stored.</span></div>}{selectedIncident.ai_summary?.risk_explanation && <p className="interpretation-copy"><strong>Model interpretation ({selectedIncident.ai_summary.source || 'source unrecorded'}):</strong> {selectedIncident.ai_summary.risk_explanation}</p>}</div><div className="detail-section"><SectionHeader title="Event history" detail="Recorded audit events" icon={Clock3} />{selectedIncident.audit_events?.length ? <AuditTimeline events={selectedIncident.audit_events} /> : <p className="empty-caption">No audit events are stored.</p>}</div></> : <EmptyState icon={ShieldCheck} title="Select an incident" detail="Inspect readings, workflow status, tasks, evidence, and audit history." />}</section></div></div>
}

function KnowledgePage({ knowledge }) {
  const [selectedName, setSelectedName] = useState('')
  const documents = knowledge?.documents || []
  const selected = documents.find((document) => document.name === selectedName) || documents[0]
  return <div className="page-stack"><div className="notice notice-neutral"><BookOpen size={16} /><span>Verified evidence comes from local text documents. Relevance is shown only when recorded. Recommendations are not mapped to individual source passages.</span></div><div className="knowledge-layout"><section className="surface knowledge-list-panel"><SectionHeader title="Knowledge documents" detail={`${documents.length} local sources`} icon={Database} />{documents.length ? documents.map((document) => <button key={document.name} className={`document-select ${selected?.name === document.name ? 'document-selected' : ''}`} onClick={() => setSelectedName(document.name)}><FileText size={16} /><span><strong>{document.name}</strong><small>{document.type} · {document.used_by.length} incident references</small></span><ChevronRight size={15} /></button>) : <EmptyState icon={BookOpen} title="Knowledge index unavailable" detail="The local documents endpoint returned no records." />}</section><section className="surface evidence-detail-panel">{selected ? <><div className="detail-heading"><div><p className="section-kicker">VERIFIED DOCUMENT</p><h2>{selected.name}</h2><small>{selected.type} · repository source</small></div><span className="source-badge source-verified"><CheckCircle2 size={14} />Verified source</span></div><div className="document-excerpt">{selected.excerpt}</div><EvidenceClass tone="verified" title="Verified document" text="Text shown directly from the local repository. No external source or remote search was used." /><EvidenceClass tone="observation" title="Environmental observations" text="Recorded separately in incidents; they are not facts asserted by this document." /><EvidenceClass tone="generated" title="Model-generated interpretation" text="Interpretations are labeled by provider in incident details and are not verified document content." /><div className="detail-section"><SectionHeader title="Incident use" detail="Evidence association is incident-level" icon={ShieldCheck} />{selected.used_by.length ? selected.used_by.map((use) => <div className="document-use" key={use.incident_id}><div><strong>{use.location}</strong><small>{use.incident_id}</small></div><p>{use.recommendations?.join(' · ') || 'No response actions recorded.'}</p><span>Recommendation-to-source links were not recorded.</span></div>) : <p className="empty-caption">No stored incident references this source. Retrieval relevance is unavailable.</p>}</div></> : <EmptyState icon={BookOpen} title="Select a source" detail="Inspect document text and stored incident associations." />}</section></div></div>
}

function AnalyticsPage({ analytics }) {
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState('')
  const exportCsv = async () => {
    setExporting(true); setExportError('')
    try {
      const response = await fetch(`${API_BASE}/api/analytics/incidents.csv`)
      if (!response.ok) throw new Error(`Export failed (${response.status})`)
      const url = URL.createObjectURL(await response.blob())
      const link = document.createElement('a'); link.href = url; link.download = 'ecoops-incidents.csv'; link.click(); URL.revokeObjectURL(url)
    } catch (err) { setExportError(err.message) } finally { setExporting(false) }
  }
  if (!analytics) return <EmptyState icon={Activity} title="Analytics unavailable" detail="The local analytics API could not be loaded." />
  const approvals = analytics.approvals || { approved: 0, rejected: 0, pending: 0 }
  return <div className="page-stack"><div className="analytics-toolbar"><div className="notice notice-neutral"><Database size={16} /><span>{analytics.source}. No impact-reduction metrics are inferred.</span></div><button className="button-secondary" onClick={exportCsv} disabled={exporting}><ArrowDownToLine size={16} />{exporting ? 'Preparing CSV' : 'Export incidents CSV'}</button></div>{exportError && <div className="inline-error" role="alert">{exportError}</div>}<div className="metric-grid"><Metric icon={ShieldCheck} label="Incidents" value={analytics.incident_total} detail="Local stored records" tone="teal" /><Metric icon={CheckCircle2} label="Approved" value={approvals.approved} detail="Human decisions recorded" tone="green" /><Metric icon={XCircle} label="Rejected" value={approvals.rejected} detail="Human decisions recorded" tone="red" /><Metric icon={ListChecks} label="Task completion" value={analytics.tasks.completion_rate == null ? '—' : `${Math.round(analytics.tasks.completion_rate * 100)}%`} detail={`${analytics.tasks.completed} of ${analytics.tasks.total} tracked`} tone="amber" /></div><div className="overview-grid"><section className="surface"><SectionHeader title="Incidents by severity" detail="Stored records" icon={Gauge} /><SeverityChart counts={analytics.by_severity} /></section><section className="surface"><SectionHeader title="Response status" detail="Persisted status values" icon={ListChecks} /><CountChart counts={analytics.by_status} /></section></div><section className="surface"><SectionHeader title="Incident volume over time" detail="Calendar day from incident timestamps" icon={Activity} /><TrendChart points={analytics.by_day || []} /></section><section className="surface audit-summary"><SectionHeader title="Review timing" detail="Requires detection and decision timestamps" icon={Clock3} /><div className="audit-summary-value">{analytics.mean_detection_to_decision_seconds == null ? 'Not available' : formatDuration(analytics.mean_detection_to_decision_seconds)}<small>Mean detection-to-decision duration</small></div><p>Approval and rejection totals use stored current statuses. Historical changes are limited to recorded audit events.</p></section></div>
}

function Metric({ icon: Icon, label, value, detail, tone }) { return <section className="metric-card"><span className={`metric-icon metric-${tone}`}><Icon size={17} /></span><div className="metric-copy"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div></section> }
function SectionHeader({ title, detail, icon: Icon, action }) { return <div className="surface-header"><div className="surface-title"><span className="surface-icon"><Icon size={16} /></span><div><h2>{title}</h2><p>{detail}</p></div></div>{action && <div>{action}</div>}</div> }
function SeverityChart({ incidents, counts }) { const values = counts || (incidents || []).reduce((all, incident) => ({ ...all, [incident.severity]: (all[incident.severity] || 0) + 1 }), {}); const max = Math.max(1, ...Object.values(values)); return <div className="severity-chart">{['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((severity) => <div className="severity-row" key={severity}><span className={`chart-key key-${severity.toLowerCase()}`}>{severity}</span><div className="bar-track"><span className={`bar-fill fill-${severity.toLowerCase()}`} style={{ width: `${((values[severity] || 0) / max) * 100}%` }} /></div><strong>{values[severity] || 0}</strong></div>)}</div> }
function CountChart({ counts = {} }) { const entries = Object.entries(counts); const max = Math.max(1, ...entries.map(([, count]) => count)); return entries.length ? <div className="count-chart">{entries.map(([label, count]) => <div key={label} className="count-row"><span>{label.replaceAll('_', ' ')}</span><div className="bar-track"><span className="bar-fill fill-teal" style={{ width: `${(count / max) * 100}%` }} /></div><strong>{count}</strong></div>)}</div> : <EmptyState icon={ListChecks} title="No response statuses" detail="Counts appear when incidents are recorded." /> }
function TrendChart({ points }) { if (!points?.length) return <EmptyState icon={Activity} title="No time-series records" detail="A trend appears when incident timestamps are available." />; const chartPoints = points.slice(-14); const max = Math.max(1, ...chartPoints.map((point) => point.count)); return <div className="trend-chart" role="img" aria-label={`Incident counts for ${chartPoints.length} recorded dates`}><div className="trend-bars">{chartPoints.map((point) => <div className="trend-column" key={point.date} title={`${point.date}: ${point.count} incidents`}><span className="trend-value">{point.count}</span><span className="trend-bar" style={{ height: `${Math.max(4, (point.count / max) * 100)}%` }} /><span className="trend-date">{point.date.slice(5)}</span></div>)}</div><div className="trend-caption">Daily incident records · no record does not mean zero measured environmental risk.</div></div> }
function IncidentTimeline({ incidents, onIncident }) { return <div className="incident-timeline">{incidents.map((incident) => <button key={incident.incident_id} className="timeline-item" onClick={() => onIncident(incident)}><span className={`timeline-marker marker-${incident.severity.toLowerCase()}`} /><span className="timeline-main"><strong>{incident.location}</strong><small>{incident.incident_id} · {formatTime(incident.timestamp)}</small></span><StatusPill value={incident.status} /><ChevronRight size={15} /></button>)}</div> }
function ExecutionList({ executions }) { return <div className="monitor-execution-list">{executions.map((execution) => <div className="monitor-execution" key={execution.execution_id}><span className="execution-select-icon"><Workflow size={15} /></span><div><strong>{execution.input?.location || 'Unknown location'}</strong><small>{execution.execution_id} · {execution.stages?.length || 0} stages · {formatTime(execution.started_at)}</small></div><StatusPill value={execution.status} /></div>)}</div> }
function RangeField({ label, value, min, max, unit, onChange }) { const id = `range-${label.toLowerCase().replaceAll(' ', '-')}`; return <div className="range-field"><div className="range-heading"><label htmlFor={id}>{label}</label><strong>{value}<small> {unit}</small></strong></div><input id={id} type="range" min={min} max={max} value={value} onChange={(event) => onChange(Number(event.target.value))} /><div className="range-bounds"><span>{min}</span><span>{max} {unit}</span></div></div> }
function TaskRow({ task, disabled, onStatus }) { return <div className="task-row"><span className={`task-status status-${task.status}`}><CircleDot size={15} /></span><div className="task-copy"><strong>{task.title}</strong><small>{task.status.replaceAll('_', ' ')} · updated {formatTime(task.updated_at || task.created_at)}</small></div><select aria-label={`Update status for ${task.title}`} value={task.status} disabled={disabled} onChange={(event) => onStatus(event.target.value)}><option value="planned">Planned</option><option value="in_progress">In progress</option><option value="completed">Completed</option><option value="blocked">Blocked</option></select></div> }
function AuditTimeline({ events }) { return <div className="audit-timeline">{events.slice().reverse().map((event, index) => <div key={`${event.event}-${index}`} className="audit-event"><span className="audit-dot" /><div><strong>{event.event.replaceAll('_', ' ')}</strong><small>{event.actor || event.mode || 'system'} · {formatTime(event.timestamp)}</small>{event.notes && <p>{event.notes}</p>}</div></div>)}</div> }
function EvidenceQuote({ evidence }) { return <div className="evidence-quote"><div className="evidence-quote-head"><span><FileText size={14} />{evidence.source}</span>{evidence.relevance != null && <small>Token-match heuristic {Math.round(evidence.relevance * 100)}%</small>}</div><blockquote>{evidence.excerpt}</blockquote><small className="evidence-note">Verified document excerpt · incident-level association only</small></div> }
function normalizeTraceValue(value) { if (Array.isArray(value)) return value.map(normalizeTraceValue); if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, item]) => [key === 'probability' ? 'rule_derived_score' : key, normalizeTraceValue(item)])); return value }
function StructuredData({ label, value }) { const hasLegacyScore = value && typeof value === 'object' && Object.hasOwn(value, 'probability'); return <div className="structured-block"><span>{label}</span><pre>{value == null ? 'No output recorded' : JSON.stringify(normalizeTraceValue(value), null, 2)}</pre>{hasLegacyScore && <small>Legacy API field is shown as a deterministic rule-derived score, not a calibrated probability.</small>}</div> }
function ReadingTile({ label, value, unit, icon: Icon }) { return <div className="reading-tile"><span className="reading-tile-icon"><Icon size={16} /></span><small>{label}</small><strong>{value}<em>{unit && ` ${unit}`}</em></strong></div> }
function DetailStat({ label, value }) { return <div className="detail-stat"><span>{label}</span><strong>{value}</strong></div> }
function DataLine({ label, value }) { return <div className="data-line"><span>{label}</span><strong>{value}</strong></div> }
function StatusPill({ value }) { const normalized = String(value || 'unknown').toLowerCase().replaceAll(' ', '_'); return <span className={`status-pill status-${normalized}`}>{String(value || 'unknown').replaceAll('_', ' ')}</span> }
function SeverityMarker({ severity }) { return <span className={`severity-marker marker-${String(severity).toLowerCase()}`} /> }
function Legend({ tone, label }) { return <span className="legend-item"><span className={`legend-dot legend-${tone}`} />{label}</span> }
function EmptyState({ icon: Icon, title, detail }) { return <div className="empty-state"><span className="empty-icon"><Icon size={19} /></span><strong>{title}</strong><p>{detail}</p></div> }
function LoadingState({ label }) { return <div className="loading-state"><RefreshCw size={20} className="spin" /><span>{label}</span></div> }
function EvidenceClass({ tone, title, text }) { return <div className="evidence-classification"><span className={`evidence-label label-${tone}`}>{title}</span><p>{text}</p></div> }
function formatTime(value) { if (!value) return 'Time unavailable'; const date = new Date(value); return Number.isNaN(date.getTime()) ? 'Time unavailable' : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) }
function formatDuration(seconds) { if (seconds < 60) return `${Math.round(seconds)} sec`; if (seconds < 3600) return `${Math.round(seconds / 60)} min`; return `${(seconds / 3600).toFixed(1)} hr` }
function severityRank(value) { return ({ LOW: 1, MEDIUM: 2, HIGH: 3, CRITICAL: 4 })[value] || 0 }
