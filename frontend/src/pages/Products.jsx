import { useState } from 'react'
import { useApi } from '../api/useApi'
import DataTable, { Pagination } from '../components/DataTable'
import { Card, ErrorBox, Loading, PageHeader, Select, TextInput } from '../components/ui'
import { inr, num } from '../utils/format'

export default function Products() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [page, setPage] = useState(1)
  const categories = useApi('/products/categories')
  const { data, loading, error } = useApi('/products', { search, category, page, page_size: 15 })

  return (
    <>
      <PageHeader title="Products" description="From the view vw_product_performance (sales per product, ranked within category)" />
      <div className="filters">
        <TextInput label="Search" value={search} onChange={(v) => { setSearch(v); setPage(1) }} placeholder="Name or SKU" />
        <Select label="Category" value={category} onChange={(v) => { setCategory(v); setPage(1) }} options={categories.data || []} />
      </div>
      <Card>
        {loading && !data ? <Loading /> : error ? <ErrorBox message={error} /> : (
          <>
            <DataTable rowKey="product_id" rows={data.items} columns={[
              { key: 'sku', label: 'SKU' },
              { key: 'product_name', label: 'Product' },
              { key: 'category', label: 'Category' },
              { key: 'unit_price', label: 'Price', align: 'right', render: (r) => inr(r.unit_price) },
              { key: 'stock_quantity', label: 'Stock', align: 'right', render: (r) => num(r.stock_quantity) },
              { key: 'units_sold', label: 'Units sold', align: 'right', render: (r) => num(r.units_sold) },
              { key: 'revenue', label: 'Revenue', align: 'right', render: (r) => inr(r.revenue) },
              { key: 'rank_in_category', label: 'Rank in category', align: 'right', render: (r) => `#${r.rank_in_category}` },
            ]} />
            <Pagination page={page} pageSize={data.page_size} total={data.total} onChange={setPage} />
          </>
        )}
      </Card>
    </>
  )
}
