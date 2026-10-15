import { useState } from 'react'
import { apiPatch, errorMessage } from '../api/client'
import { useApi } from '../api/useApi'
import DataTable, { Pagination } from '../components/DataTable'
import { Badge, Card, ErrorBox, Loading, PageHeader, Select, TextInput } from '../components/ui'
import { date, dateTime, inr } from '../utils/format'

const STATUSES = ['PENDING', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED']

function OrderDetail({ id, onClose, onChanged }) {
  const { data, loading, error, reload } = useApi(`/orders/${id}`)
  const [newStatus, setNewStatus] = useState('')
  const [message, setMessage] = useState(null)

  async function changeStatus() {
    setMessage(null)
    try {
      const r = await apiPatch(`/orders/${id}/status`, { status: newStatus })
      setMessage({ ok: true, text: `Status changed ${r.old_status} → ${r.new_status} (recorded in audit log)` })
      reload()
      onChanged()
    } catch (e) {
      // The text comes from SIGNAL in the stored procedure, e.g. "Invalid status transition"
      setMessage({ ok: false, text: errorMessage(e) })
    }
  }

  if (loading && !data) return <Card><Loading /></Card>
  if (error) return <Card><ErrorBox message={error} /></Card>
  return (
    <Card title={`Order ${data.order_number}`} subtitle={<button onClick={onClose}>Close ✕</button>}>
      <p className="muted">
        {dateTime(data.order_date)} · {data.customer_name} ({data.customer_code}) · handled by {data.handled_by || 'online'} ·{' '}
        <Badge value={data.status} /> <Badge value={data.payment_status} />
      </p>
      <div className="inline-form">
        <Select label="Change status (sp_update_order_status)" value={newStatus} onChange={setNewStatus}
                options={STATUSES.filter((s) => s !== data.status)} placeholder="Choose…" />
        <button className="primary" disabled={!newStatus} onClick={changeStatus}>Update</button>
        {message && <span className={message.ok ? 'ok-text' : 'error-text'}>{message.text}</span>}
      </div>
      <h3>Items</h3>
      <DataTable rowKey="order_item_id" rows={data.items} empty="This order has no items (see Data Quality)" columns={[
        { key: 'sku', label: 'SKU' },
        { key: 'product_name', label: 'Product' },
        { key: 'quantity', label: 'Qty', align: 'right' },
        { key: 'unit_price', label: 'Unit price', align: 'right', render: (r) => inr(r.unit_price) },
        { key: 'discount_pct', label: 'Discount', align: 'right', render: (r) => `${r.discount_pct}%` },
        { key: 'line_total', label: 'Line total', align: 'right', render: (r) => inr(r.line_total) },
      ]} />
      <p className="totals">Order total <strong>{inr(data.order_total)}</strong> · Paid <strong>{inr(data.amount_paid)}</strong> ·
        Balance <strong>{inr(data.balance_due)}</strong></p>
      <h3>Payments</h3>
      <DataTable rowKey="payment_id" rows={data.payments} empty="No payments yet" columns={[
        { key: 'payment_reference', label: 'Reference' },
        { key: 'payment_date', label: 'Date', render: (r) => dateTime(r.payment_date) },
        { key: 'payment_method', label: 'Method' },
        { key: 'status', label: 'Status', render: (r) => <Badge value={r.status} /> },
        { key: 'amount', label: 'Amount', align: 'right', render: (r) => inr(r.amount) },
      ]} />
    </Card>
  )
}

export default function Orders() {
  const [filters, setFilters] = useState({ search: '', status: '', payment_status: '', date_from: '', date_to: '' })
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState(null)
  const { data, loading, error, reload } = useApi('/orders', { ...filters, page, page_size: 15 })
  const update = (key) => (value) => { setFilters({ ...filters, [key]: value }); setPage(1) }

  return (
    <>
      <PageHeader title="Orders" description="From the view vw_order_summary. Click an order to see lines, payments and change its status." />
      <div className="filters">
        <TextInput label="Order number" value={filters.search} onChange={update('search')} placeholder="ORD-…" />
        <Select label="Status" value={filters.status} onChange={update('status')} options={STATUSES} />
        <Select label="Payment" value={filters.payment_status} onChange={update('payment_status')}
                options={['PAID', 'PARTIALLY_PAID', 'UNPAID', 'NOT_APPLICABLE']} />
        <TextInput label="From" type="date" value={filters.date_from} onChange={update('date_from')} />
        <TextInput label="To" type="date" value={filters.date_to} onChange={update('date_to')} />
      </div>
      {selected && <OrderDetail id={selected} onClose={() => setSelected(null)} onChanged={reload} />}
      <Card>
        {loading && !data ? <Loading /> : error ? <ErrorBox message={error} /> : (
          <>
            <DataTable rowKey="order_id" rows={data.items} onRowClick={(r) => setSelected(r.order_id)} selectedKey={selected}
                       columns={[
              { key: 'order_number', label: 'Order' },
              { key: 'order_date', label: 'Date', render: (r) => date(r.order_date) },
              { key: 'customer_name', label: 'Customer' },
              { key: 'segment', label: 'Segment' },
              { key: 'status', label: 'Status', render: (r) => <Badge value={r.status} /> },
              { key: 'payment_status', label: 'Payment', render: (r) => <Badge value={r.payment_status} /> },
              { key: 'item_count', label: 'Items', align: 'right' },
              { key: 'order_total', label: 'Total', align: 'right', render: (r) => inr(r.order_total) },
              { key: 'balance_due', label: 'Balance', align: 'right', render: (r) => inr(r.balance_due) },
            ]} />
            <Pagination page={page} pageSize={data.page_size} total={data.total} onChange={setPage} />
          </>
        )}
      </Card>
    </>
  )
}
