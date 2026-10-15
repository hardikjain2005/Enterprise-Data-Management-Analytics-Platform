import { useState } from 'react'
import { useApi } from '../api/useApi'
import DataTable, { Pagination } from '../components/DataTable'
import { Badge, Card, ErrorBox, Loading, PageHeader, Select, TextInput } from '../components/ui'
import { dateTime } from '../utils/format'

// Show only the fields that changed (UPDATE), or all fields (INSERT / DELETE).
function Changes({ row }) {
  const before = row.old_values || {}
  const after = row.new_values || {}
  const keys = [...new Set([...Object.keys(before), ...Object.keys(after)])]
    .filter((k) => row.action !== 'UPDATE' || JSON.stringify(before[k]) !== JSON.stringify(after[k]))
  return (
    <div className="changes">
      {keys.map((k) => (
        <div key={k}>
          <code>{k}</code>:{' '}
          {row.action === 'UPDATE' ? <><s>{String(before[k])}</s> → <strong>{String(after[k])}</strong></>
            : String((row.action === 'DELETE' ? before : after)[k])}
        </div>
      ))}
    </div>
  )
}

export default function AuditLog() {
  const [filters, setFilters] = useState({ table: '', action: '', record_id: '', changed_by: '' })
  const [page, setPage] = useState(1)
  const { data, loading, error } = useApi('/audit-logs', { ...filters, page, page_size: 15 })
  const update = (key) => (value) => { setFilters({ ...filters, [key]: value }); setPage(1) }

  return (
    <>
      <PageHeader title="Audit Log" description="Written automatically by MySQL triggers; the table is append-only" />
      <div className="filters">
        <Select label="Table" value={filters.table} onChange={update('table')} options={['customers', 'products', 'orders', 'payments']} />
        <Select label="Action" value={filters.action} onChange={update('action')} options={['INSERT', 'UPDATE', 'DELETE']} />
        <TextInput label="Record ID" type="number" value={filters.record_id} onChange={update('record_id')} />
        <Select label="Changed by" value={filters.changed_by} onChange={update('changed_by')} options={['etl_pipeline', 'api', 'seed_script']} />
      </div>
      <Card>
        {loading && !data ? <Loading /> : error ? <ErrorBox message={error} /> : (
          <>
            <DataTable rowKey="audit_id" rows={data.items} columns={[
              { key: 'audit_id', label: '#' },
              { key: 'changed_at', label: 'When', render: (r) => dateTime(r.changed_at) },
              { key: 'table_name', label: 'Table' },
              { key: 'record_id', label: 'Record ID' },
              { key: 'action', label: 'Action', render: (r) => <Badge value={r.action} /> },
              { key: 'changed_by', label: 'Changed by' },
              { key: 'changes', label: 'Changes', render: (r) => <Changes row={r} /> },
            ]} />
            <Pagination page={page} pageSize={data.page_size} total={data.total} onChange={setPage} />
          </>
        )}
      </Card>
    </>
  )
}
