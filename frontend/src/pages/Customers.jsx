import { useState } from 'react'
import { useApi } from '../api/useApi'
import DataTable, { Pagination } from '../components/DataTable'
import { Badge, Card, ErrorBox, Loading, PageHeader, Select, StatCard, TextInput } from '../components/ui'
import { date, inr, num } from '../utils/format'

function CustomerDetail({ id, onClose }) {
  const { data, loading, error } = useApi(`/customers/${id}`)
  if (loading) return <Card><Loading /></Card>
  if (error) return <Card><ErrorBox message={error} /></Card>
  const s = data.summary
  return (
    <Card title={`${data.first_name} ${data.last_name}`} subtitle={<button onClick={onClose}>Close ✕</button>}>
      <p className="muted">{data.customer_code} · {data.email} · {data.phone || 'no phone'} · {data.city}, {data.country}</p>
      <p className="muted small">Summary below comes from the stored procedure <code>sp_get_customer_summary</code>.</p>
      <div className="stats compact">
        <StatCard label="Orders" value={num(s.total_orders)} hint={`${s.cancelled_orders} cancelled`} />
        <StatCard label="Total spent" value={inr(s.total_spent)} />
        <StatCard label="Total paid" value={inr(s.total_paid)} />
        <StatCard label="Tier" value={<Badge value={s.tier} />} hint={`Customer since ${date(data.signup_date)}`} />
      </div>
      <h3>Recent orders</h3>
      <DataTable rowKey="order_id" rows={data.recent_orders} columns={[
        { key: 'order_number', label: 'Order' },
        { key: 'order_date', label: 'Date', render: (r) => date(r.order_date) },
        { key: 'status', label: 'Status', render: (r) => <Badge value={r.status} /> },
        { key: 'payment_status', label: 'Payment', render: (r) => <Badge value={r.payment_status} /> },
        { key: 'order_total', label: 'Total', align: 'right', render: (r) => inr(r.order_total) },
      ]} />
    </Card>
  )
}

export default function Customers() {
  const [filters, setFilters] = useState({ search: '', segment: '', tier: '', sort: 'total_spent' })
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState(null)
  const { data, loading, error } = useApi('/customers', { ...filters, page, page_size: 15 })
  const update = (key) => (value) => { setFilters({ ...filters, [key]: value }); setPage(1) }

  return (
    <>
      <PageHeader title="Customers" description="From the view vw_customer_360 (customer + lifetime metrics)" />
      <div className="filters">
        <TextInput label="Search" value={filters.search} onChange={update('search')} placeholder="Name, email or code" />
        <Select label="Segment" value={filters.segment} onChange={update('segment')} options={['Retail', 'SMB', 'Corporate']} />
        <Select label="Tier" value={filters.tier} onChange={update('tier')} options={['PLATINUM', 'GOLD', 'SILVER', 'BRONZE']} />
        <Select label="Sort by" value={filters.sort} onChange={update('sort')} placeholder="Total spent"
                options={[['total_orders', 'Total orders'], ['signup_date', 'Newest'], ['customer_code', 'Customer code']]} />
      </div>
      {selected && <CustomerDetail id={selected} onClose={() => setSelected(null)} />}
      <Card>
        {loading && !data ? <Loading /> : error ? <ErrorBox message={error} /> : (
          <>
            <DataTable rowKey="customer_id" rows={data.items} onRowClick={(r) => setSelected(r.customer_id)}
                       selectedKey={selected} columns={[
              { key: 'customer_code', label: 'Code' },
              { key: 'customer_name', label: 'Name' },
              { key: 'city', label: 'City' },
              { key: 'segment', label: 'Segment' },
              { key: 'tier', label: 'Tier', render: (r) => <Badge value={r.tier} /> },
              { key: 'total_orders', label: 'Orders', align: 'right' },
              { key: 'total_spent', label: 'Total spent', align: 'right', render: (r) => inr(r.total_spent) },
              { key: 'last_order_date', label: 'Last order', render: (r) => date(r.last_order_date) },
            ]} />
            <Pagination page={page} pageSize={data.page_size} total={data.total} onChange={setPage} />
          </>
        )}
      </Card>
    </>
  )
}
