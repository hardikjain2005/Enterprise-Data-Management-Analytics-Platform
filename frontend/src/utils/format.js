const inrFormatter = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })
const numberFormatter = new Intl.NumberFormat('en-IN')

export const inr = (v) => (v === null || v === undefined ? '-' : inrFormatter.format(v))
export const num = (v) => (v === null || v === undefined ? '-' : numberFormatter.format(v))

// Indian short scale: 1 lakh = 1,00,000 ; 1 crore = 1,00,00,000
export function inrShort(v) {
  if (v === null || v === undefined) return '-'
  const abs = Math.abs(v)
  if (abs >= 1e7) return `₹${+(v / 1e7).toFixed(2)} Cr`   // + drops trailing zeros: 24.00 -> 24
  if (abs >= 1e5) return `₹${+(v / 1e5).toFixed(1)} L`
  if (abs >= 1e3) return `₹${+(v / 1e3).toFixed(1)} K`
  return `₹${Math.round(v)}`
}

export const date = (v) => (v ? new Date(v).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '-')
export const dateTime = (v) =>
  v ? new Date(v).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-'
export const monthLabel = (ym) => {
  const [y, m] = ym.split('-')
  return new Date(Number(y), Number(m) - 1, 1).toLocaleDateString('en-IN', { month: 'short', year: '2-digit' })
}
