// Generic table. columns = [{ key, label, render?(row), align? }]
export default function DataTable({ columns, rows, rowKey, onRowClick, selectedKey, empty = 'No records found' }) {
  if (!rows?.length) return <div className="state">{empty}</div>
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={c.align === 'right' ? 'right' : ''}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row[rowKey]}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={`${onRowClick ? 'clickable' : ''} ${selectedKey === row[rowKey] ? 'selected' : ''}`}
            >
              {columns.map((c) => (
                <td key={c.key} className={c.align === 'right' ? 'right num' : ''}>
                  {c.render ? c.render(row) : row[c.key] ?? '-'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Pagination({ page, pageSize, total, onChange }) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  return (
    <div className="pagination">
      <span className="muted">
        {total === 0 ? '0 records' : `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} of ${total}`}
      </span>
      <div>
        <button disabled={page <= 1} onClick={() => onChange(page - 1)}>‹ Prev</button>
        <span className="muted"> Page {page} / {pages} </span>
        <button disabled={page >= pages} onClick={() => onChange(page + 1)}>Next ›</button>
      </div>
    </div>
  )
}
