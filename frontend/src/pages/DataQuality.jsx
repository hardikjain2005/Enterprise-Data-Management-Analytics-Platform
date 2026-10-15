import { useState } from 'react'
import { apiPatch, apiPost, errorMessage } from '../api/client'
import { useApi } from '../api/useApi'
import DataTable, { Pagination } from '../components/DataTable'
import { BarsChart, COLORS } from '../components/charts'
import { Badge, Card, ErrorBox, Loading, PageHeader, Select, StatCard, TextInput } from '../components/ui'
import { dateTime, num } from '../utils/format'

const SEVERITY_COLOR = { CRITICAL: COLORS.status.critical, HIGH: COLORS.status.serious,
                         MEDIUM: COLORS.status.warning, LOW: COLORS.status.good }
const SEVERITY_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
const TYPES = ['MISSING_COLUMN', 'MISSING_VALUE', 'DUPLICATE_RECORD', 'INVALID_FORMAT', 'INVALID_DATE',
               'INVALID_VALUE', 'NEGATIVE_VALUE', 'INVALID_REFERENCE', 'BUSINESS_RULE']

export default function DataQuality() {
  const summary = useApi('/data-quality/summary')
  const [filters, setFilters] = useState({ status: 'OPEN', severity: '', table: '', issue_type: '', search: '' })
  const [page, setPage] = useState(1)
  const [message, setMessage] = useState(null)
  const issues = useApi('/data-quality/issues', { ...filters, page, page_size: 15 })
  const update = (key) => (value) => { setFilters({ ...filters, [key]: value }); setPage(1) }
  const refresh = () => { issues.reload(); summary.reload() }

  async function runChecks() {
    try {
      const r = await apiPost('/data-quality/run-checks')
      setMessage(`sp_run_data_quality_checks finished: ${r.new_issues_found} new issue(s)`)
      refresh()
    } catch (e) { setMessage(errorMessage(e)) }
  }

  async function setStatus(issue, resolution_status) {
    try {
      await apiPatch(`/data-quality/issues/${issue.issue_id}`, { resolution_status, resolution_note: 'Updated from dashboard' })
      refresh()
    } catch (e) { setMessage(errorMessage(e)) }
  }

  const s = summary.data
  const bySeverity = s ? SEVERITY_ORDER.map((sev) => ({ label: sev, count: s.by_severity.find((x) => x.label === sev)?.count || 0 })) : []

  return (
    <>
      <PageHeader title="Data Quality" description="Issues found by ETL validation (Python + SQL) and by in-database business-rule checks">
        <button className="primary" onClick={runChecks}>Run quality checks</button>
      </PageHeader>
      {message && <p className="ok-text">{message}</p>}

      {summary.loading ? <Loading /> : summary.error ? <ErrorBox message={summary.error} /> : (
        <>
          <div className="stats">
            <StatCard label="Total issues logged" value={num(s.total_issues)} />
            <StatCard label="Open" value={num(s.open_issues)} tone={s.open_issues ? 'serious' : 'good'} />
            {bySeverity.map((x) => <StatCard key={x.label} label={`Open · ${x.label.toLowerCase()}`} value={num(x.count)} />)}
          </div>
          <div className="grid-2">
            <Card title="Open issues by severity">
              <BarsChart data={bySeverity} x="label" y="count" name="Open issues" valueFormatter={num}
                         colorFor={(row) => SEVERITY_COLOR[row.label]} height={220} />
            </Card>
            <Card title="Open issues by rule">
              <BarsChart data={s.by_rule} x="label" y="count" name="Open issues" horizontal valueFormatter={num}
                         height={Math.max(220, s.by_rule.length * 24)} />
            </Card>
          </div>
        </>
      )}

      <div className="filters">
        <Select label="Status" value={filters.status} onChange={update('status')} options={['OPEN', 'RESOLVED', 'IGNORED']} />
        <Select label="Severity" value={filters.severity} onChange={update('severity')} options={SEVERITY_ORDER} />
        <Select label="Table" value={filters.table} onChange={update('table')}
                options={['customers', 'products', 'orders', 'order_items', 'payments']} />
        <Select label="Issue type" value={filters.issue_type} onChange={update('issue_type')} options={TYPES} />
        <TextInput label="Search" value={filters.search} onChange={update('search')} placeholder="Record or text" />
      </div>
      <Card title="Issues">
        {issues.loading && !issues.data ? <Loading /> : issues.error ? <ErrorBox message={issues.error} /> : (
          <>
            <DataTable rowKey="issue_id" rows={issues.data.items} columns={[
              { key: 'severity', label: 'Severity', render: (r) => <Badge value={r.severity} /> },
              { key: 'table_name', label: 'Table' },
              { key: 'record_identifier', label: 'Record' },
              { key: 'rule_name', label: 'Rule' },
              { key: 'description', label: 'Description' },
              { key: 'source_name', label: 'Source' },
              { key: 'detected_at', label: 'Detected', render: (r) => dateTime(r.detected_at) },
              { key: 'resolution_status', label: 'Status', render: (r) => <Badge value={r.resolution_status} /> },
              { key: 'actions', label: '', render: (r) => r.resolution_status === 'OPEN' ? (
                <span className="row-actions">
                  <button onClick={() => setStatus(r, 'RESOLVED')}>Resolve</button>
                  <button onClick={() => setStatus(r, 'IGNORED')}>Ignore</button>
                </span>
              ) : <button onClick={() => setStatus(r, 'OPEN')}>Reopen</button> },
            ]} />
            <Pagination page={page} pageSize={issues.data.page_size} total={issues.data.total} onChange={setPage} />
          </>
        )}
      </Card>
    </>
  )
}
