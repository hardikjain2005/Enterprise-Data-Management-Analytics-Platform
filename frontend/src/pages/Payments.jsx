import { useState } from 'react'
import { apiPost, errorMessage } from '../api/client'
import { useApi } from '../api/useApi'
import DataTable, { Pagination } from '../components/DataTable'
import { Badge, Card, ErrorBox, Loading, PageHeader, Select, TextInput } from '../components/ui'
import { dateTime, inr } from '../utils/format'

const METHODS = ['CARD', 'UPI', 'NET_BANKING', 'BANK_TRANSFER', 'WALLET']

function RecordPayment({ onSaved }) {
  const [form, setForm] = useState({ order_id: '', amount: '', payment_method: 'UPI', payment_reference: '' })
  const [message, setMessage] = useState(null)
  const set = (key) => (value) => setForm({ ...form, [key]: value })

  async function submit(e) {
    e.preventDefault()
    setMessage(null)
    try {
      const r = await apiPost('/payments', { ...form, order_id: Number(form.order_id), amount: Number(form.amount) })
      setMessage({ ok: true, text: `Payment #${r.payment_id} saved. Remaining balance: ${inr(r.remaining_balance)}` })
      setForm({ ...form, amount: '', payment_reference: '' })
      onSaved()
    } catch (err) {
      setMessage({ ok: false, text: errorMessage(err) })   // e.g. "Payment exceeds outstanding balance"
    }
  }

  return (
    <Card title="Record a payment" subtitle="runs the transactional stored procedure sp_record_payment">
      <form className="inline-form" onSubmit={submit}>
        <TextInput label="Order ID" type="number" value={form.order_id} onChange={set('order_id')} placeholder="e.g. 1480" />
        <TextInput label="Amount (₹)" type="number" value={form.amount} onChange={set('amount')} />
        <Select label="Method" value={form.payment_method} onChange={set('payment_method')} options={METHODS} placeholder="Choose…" />
        <TextInput label="Reference" value={form.payment_reference} onChange={set('payment_reference')} placeholder="TXN…" />
        <button className="primary" type="submit">Save payment</button>
      </form>
      {message && <p className={message.ok ? 'ok-text' : 'error-text'}>{message.text}</p>}
    </Card>
  )
}

export default function Payments() {
  const [filters, setFilters] = useState({ search: '', status: '', method: '', date_from: '', date_to: '' })
  const [page, setPage] = useState(1)
  const { data, loading, error, reload } = useApi('/payments', { ...filters, page, page_size: 15 })
  const update = (key) => (value) => { setFilters({ ...filters, [key]: value }); setPage(1) }

  return (
    <>
      <PageHeader title="Payments" description="Payment transactions received against orders" />
      <RecordPayment onSaved={reload} />
      <div className="filters">
        <TextInput label="Search" value={filters.search} onChange={update('search')} placeholder="Reference or order" />
        <Select label="Status" value={filters.status} onChange={update('status')} options={['COMPLETED', 'PENDING', 'FAILED', 'REFUNDED']} />
        <Select label="Method" value={filters.method} onChange={update('method')} options={METHODS} />
        <TextInput label="From" type="date" value={filters.date_from} onChange={update('date_from')} />
        <TextInput label="To" type="date" value={filters.date_to} onChange={update('date_to')} />
      </div>
      <Card>
        {loading && !data ? <Loading /> : error ? <ErrorBox message={error} /> : (
          <>
            <DataTable rowKey="payment_id" rows={data.items} columns={[
              { key: 'payment_reference', label: 'Reference' },
              { key: 'order_number', label: 'Order' },
              { key: 'payment_date', label: 'Date', render: (r) => dateTime(r.payment_date) },
              { key: 'payment_method', label: 'Method', render: (r) => r.payment_method.replace('_', ' ') },
              { key: 'status', label: 'Status', render: (r) => <Badge value={r.status} /> },
              { key: 'amount', label: 'Amount', align: 'right', render: (r) => inr(r.amount) },
            ]} />
            <Pagination page={page} pageSize={data.page_size} total={data.total} onChange={setPage} />
          </>
        )}
      </Card>
    </>
  )
}
