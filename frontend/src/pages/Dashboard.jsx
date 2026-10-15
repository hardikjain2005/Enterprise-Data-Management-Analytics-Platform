import { Link } from 'react-router-dom'
import { useApi } from '../api/useApi'
import DataTable from '../components/DataTable'
import { BarsChart, TrendChart } from '../components/charts'
import { Badge, Card, ErrorBox, Loading, PageHeader, StatCard } from '../components/ui'
import { dateTime, inrShort, monthLabel, num } from '../utils/format'

export default function Dashboard() {
  const summary = useApi('/dashboard/summary')
  const sales = useApi('/analytics/sales')

  if (summary.loading) return <Loading />
  if (summary.error) return <ErrorBox message={summary.error} />
  const s = summary.data

  return (
    <>
      <PageHeader title="Dashboard" description="Business KPIs and data-platform health at a glance" />

      <div className="stats">
        <StatCard label="Customers" value={num(s.total_customers)} hint={`${num(s.total_products)} products`} />
        <StatCard label="Orders" value={num(s.total_orders)} />
        <StatCard label="Revenue" value={inrShort(s.total_revenue)} hint="excluding cancelled orders" />
        <StatCard label="Payments collected" value={inrShort(s.total_payments)}
                  hint={`${inrShort(s.outstanding_balance)} outstanding`} />
        <StatCard label="ETL runs" value={num(s.etl_runs)} hint={`${s.failed_etl_runs} failed`}
                  tone={s.failed_etl_runs ? 'critical' : 'good'} />
        <StatCard label="Open data-quality issues" value={num(s.open_quality_issues)}
                  hint={`${s.critical_quality_issues} critical`} tone={s.critical_quality_issues ? 'serious' : 'good'} />
      </div>

      <div className="grid-2">
        <Card title="Monthly revenue" subtitle="non-cancelled orders">
          {sales.data ? (
            <TrendChart data={sales.data.monthly} x="sales_month" y="revenue" name="Revenue"
                        valueFormatter={inrShort} xFormatter={monthLabel} />
          ) : <Loading />}
        </Card>
        <Card title="Orders by status">
          <BarsChart data={s.orders_by_status} x="status" y="count" name="Orders" horizontal
                     xFormatter={(v) => v.charAt(0) + v.slice(1).toLowerCase()} valueFormatter={num} />
        </Card>
      </div>

      <Card title="Recent ETL executions" subtitle={<Link to="/etl">View all →</Link>}>
        <DataTable rowKey="execution_id" rows={s.recent_etl_executions} columns={[
          { key: 'execution_id', label: 'Run #' },
          { key: 'job_name', label: 'Job' },
          { key: 'started_at', label: 'Started', render: (r) => dateTime(r.started_at) },
          { key: 'status', label: 'Status', render: (r) => <Badge value={r.status} /> },
          { key: 'records_read', label: 'Read', align: 'right', render: (r) => num(r.records_read) },
          { key: 'records_rejected', label: 'Rejected', align: 'right', render: (r) => num(r.records_rejected) },
        ]} />
      </Card>
    </>
  )
}
