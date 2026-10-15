import { useApi } from '../api/useApi'
import DataTable from '../components/DataTable'
import { BarsChart, TrendChart } from '../components/charts'
import { Badge, Card, ErrorBox, Loading, PageHeader } from '../components/ui'
import { inr, inrShort, monthLabel, num } from '../utils/format'

const pct = (v) => (v === null || v === undefined ? '-' : `${v > 0 ? '+' : ''}${v}%`)

export default function Analytics() {
  const sales = useApi('/analytics/sales')
  const customers = useApi('/analytics/customers')
  if (sales.loading || customers.loading) return <Loading />
  if (sales.error || customers.error) return <ErrorBox message={sales.error || customers.error} />
  const s = sales.data
  const c = customers.data

  return (
    <>
      <PageHeader title="Analytics" description="Computed with GROUP BY, views and window functions (SUM OVER, LAG, RANK)" />
      <div className="grid-2">
        <Card title="Cumulative revenue" subtitle="SUM(revenue) OVER (ORDER BY month)">
          <TrendChart data={s.monthly} x="sales_month" y="cumulative_revenue" name="Cumulative revenue"
                      valueFormatter={inrShort} xFormatter={monthLabel} />
        </Card>
        <Card title="Month-over-month growth" subtitle="LAG(revenue) OVER (ORDER BY month)">
          <TrendChart data={s.monthly.filter((m) => m.growth_pct !== null)} x="sales_month" y="growth_pct"
                      name="Growth" valueFormatter={pct} xFormatter={monthLabel} area={false} />
        </Card>
        <Card title="Revenue by category">
          <BarsChart data={s.by_category} x="category" y="revenue" name="Revenue" horizontal valueFormatter={inrShort} height={300} />
        </Card>
        <Card title="Revenue by customer segment">
          <BarsChart data={c.by_segment} x="segment" y="revenue" name="Revenue" valueFormatter={inrShort} height={300} />
        </Card>
        <Card title="Payments collected by method">
          <BarsChart data={s.by_payment_method} x="payment_method" y="amount" name="Collected" horizontal
                     valueFormatter={inrShort} xFormatter={(v) => v.replace('_', ' ')} />
        </Card>
        <Card title="New customers per month">
          <BarsChart data={c.new_customers_by_month} x="month" y="new_customers" name="New customers"
                     valueFormatter={num} xFormatter={monthLabel} />
        </Card>
      </div>
      <div className="grid-2">
        <Card title="Top 10 customers" subtitle="RANK() OVER (ORDER BY total_spent DESC)">
          <DataTable rowKey="customer_id" rows={c.top_customers} columns={[
            { key: 'rank', label: '#' },
            { key: 'customer_name', label: 'Customer' },
            { key: 'segment', label: 'Segment' },
            { key: 'tier', label: 'Tier', render: (r) => <Badge value={r.tier} /> },
            { key: 'total_orders', label: 'Orders', align: 'right' },
            { key: 'total_spent', label: 'Spent', align: 'right', render: (r) => inr(r.total_spent) },
          ]} />
        </Card>
        <Card title="Top 10 products">
          <DataTable rowKey="sku" rows={s.top_products} columns={[
            { key: 'product_name', label: 'Product' },
            { key: 'category', label: 'Category' },
            { key: 'units_sold', label: 'Units', align: 'right', render: (r) => num(r.units_sold) },
            { key: 'revenue', label: 'Revenue', align: 'right', render: (r) => inr(r.revenue) },
          ]} />
        </Card>
      </div>
      <Card title="Category share" subtitle="SUM(revenue) / SUM(SUM(revenue)) OVER ()">
        <DataTable rowKey="category" rows={s.by_category} columns={[
          { key: 'category', label: 'Category' },
          { key: 'units_sold', label: 'Units sold', align: 'right', render: (r) => num(r.units_sold) },
          { key: 'revenue', label: 'Revenue', align: 'right', render: (r) => inr(r.revenue) },
          { key: 'revenue_share_pct', label: 'Share', align: 'right', render: (r) => `${r.revenue_share_pct}%` },
        ]} />
      </Card>
    </>
  )
}
