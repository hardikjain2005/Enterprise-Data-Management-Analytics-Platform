// Small presentational components shared by every page.

export function PageHeader({ title, description, children }) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        {description && <p className="muted">{description}</p>}
      </div>
      <div className="page-actions">{children}</div>
    </div>
  )
}

export function StatCard({ label, value, hint, tone }) {
  return (
    <div className={`stat-card ${tone ? `tone-${tone}` : ''}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  )
}

export function Card({ title, subtitle, children, className = '' }) {
  return (
    <section className={`card ${className}`}>
      {title && (
        <header className="card-header">
          <h2>{title}</h2>
          {subtitle && <span className="muted">{subtitle}</span>}
        </header>
      )}
      {children}
    </section>
  )
}

export const Loading = () => <div className="state">Loading…</div>
export const ErrorBox = ({ message }) => <div className="state error">⚠ {message}</div>

// Maps a status word to one of four reserved status tones. The word itself is
// always shown, so colour is never the only signal.
const TONES = {
  good: ['SUCCESS', 'PAID', 'DELIVERED', 'COMPLETED', 'RESOLVED', 'LOW'],
  warning: ['PARTIAL_SUCCESS', 'PARTIALLY_PAID', 'PENDING', 'PROCESSING', 'RUNNING', 'MEDIUM'],
  serious: ['SHIPPED', 'HIGH', 'UNPAID', 'REFUNDED'],
  critical: ['FAILED', 'CANCELLED', 'CRITICAL'],
}
const toneFor = (v) => Object.keys(TONES).find((t) => TONES[t].includes(v)) || 'neutral'

export function Badge({ value }) {
  if (!value) return <span className="muted">-</span>
  return (
    <span className={`badge badge-${toneFor(value)}`}>
      <span className="dot" />
      {String(value).replaceAll('_', ' ')}
    </span>
  )
}

export function Select({ label, value, onChange, options, placeholder = 'All' }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{placeholder}</option>
        {options.map((o) => {
          const [val, text] = Array.isArray(o) ? o : [o, String(o).replaceAll('_', ' ')]
          return <option key={val} value={val}>{text}</option>
        })}
      </select>
    </label>
  )
}

export function TextInput({ label, value, onChange, placeholder, type = 'text' }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type={type} value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
    </label>
  )
}
