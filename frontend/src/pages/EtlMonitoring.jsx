import { useState } from 'react'
import { useApi } from '../api/useApi'
import DataTable, { Pagination } from '../components/DataTable'
import { BarsChart } from '../components/charts'
import { Badge, Card, ErrorBox, Loading, PageHeader, Select } from '../components/ui'
import { dateTime, num } from '../utils/format'

export default function EtlMonitoring() {
  const jobs = useApi('/etl/jobs')
  const [jobId, setJobId] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const logs = useApi('/etl/logs', { job_id: jobId, status, page, page_size: 15 })

  return (
    <>
      <PageHeader title="ETL Monitoring" description="Job definitions (etl_jobs) and every run (etl_execution_logs)" />
      <Card title="Jobs and their latest run" subtitle="view vw_etl_job_status">
        {jobs.loading ? <Loading /> : jobs.error ? <ErrorBox message={jobs.error} /> : (
          <DataTable rowKey="job_id" rows={jobs.data} columns={[
            { key: 'job_name', label: 'Job' },
            { key: 'source_name', label: 'Source system' },
            { key: 'source_file', label: 'File' },
            { key: 'target_table', label: 'Target table' },
            { key: 'last_status', label: 'Last status', render: (r) => <Badge value={r.last_status} /> },
            { key: 'last_started_at', label: 'Last run', render: (r) => dateTime(r.last_started_at) },
            { key: 'total_runs', label: 'Runs', align: 'right' },
            { key: 'failed_runs', label: 'Failed', align: 'right' },
          ]} />
        )}
      </Card>

      {logs.data && (
        <Card title="Rows rejected per run" subtitle="hover a bar for the exact count">
          <BarsChart data={[...logs.data.items].reverse().map((l) => ({ ...l, run: `#${l.execution_id} ${l.job_name.replace('load_', '')}` }))}
                     x="run" y="records_rejected" name="Rejected rows" valueFormatter={num} height={220} />
        </Card>
      )}

      <div className="filters">
        <Select label="Job" value={jobId} onChange={(v) => { setJobId(v); setPage(1) }}
                options={(jobs.data || []).map((j) => [j.job_id, j.job_name])} />
        <Select label="Status" value={status} onChange={(v) => { setStatus(v); setPage(1) }}
                options={['SUCCESS', 'PARTIAL_SUCCESS', 'FAILED', 'RUNNING']} />
      </div>
      <Card title="Execution log">
        {logs.loading && !logs.data ? <Loading /> : logs.error ? <ErrorBox message={logs.error} /> : (
          <>
            <DataTable rowKey="execution_id" rows={logs.data.items} columns={[
              { key: 'execution_id', label: 'Run #' },
              { key: 'job_name', label: 'Job' },
              { key: 'started_at', label: 'Started', render: (r) => dateTime(r.started_at) },
              { key: 'duration_ms', label: 'Duration', align: 'right', render: (r) => (r.duration_ms === null ? '-' : `${r.duration_ms} ms`) },
              { key: 'status', label: 'Status', render: (r) => <Badge value={r.status} /> },
              { key: 'records_read', label: 'Read', align: 'right', render: (r) => num(r.records_read) },
              { key: 'records_inserted', label: 'Inserted', align: 'right', render: (r) => num(r.records_inserted) },
              { key: 'records_updated', label: 'Updated', align: 'right', render: (r) => num(r.records_updated) },
              { key: 'records_rejected', label: 'Rejected', align: 'right', render: (r) => num(r.records_rejected) },
              { key: 'error_count', label: 'Issues', align: 'right' },
              { key: 'error_message', label: 'Error', render: (r) => r.error_message || '' },
            ]} />
            <Pagination page={page} pageSize={logs.data.page_size} total={logs.data.total} onChange={setPage} />
          </>
        )}
      </Card>
    </>
  )
}
