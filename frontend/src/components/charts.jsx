// Thin wrappers around Recharts so every chart shares the same look:
// one series colour, recessive grid/axes, rounded bar ends, hover tooltips.
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart,
  ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

export const COLORS = {
  series1: '#2a78d6',
  series2: '#eb6834',
  grid: '#e1e0d9',
  axis: '#898781',
  status: { good: '#0ca30c', warning: '#fab219', serious: '#ec835a', critical: '#d03b3b' },
}

const axisProps = { stroke: COLORS.axis, tick: { fill: COLORS.axis, fontSize: 12 }, tickLine: false, axisLine: false }

function ChartTooltip({ active, payload, label, valueFormatter, labelFormatter }) {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tooltip">
      <div className="tooltip-label">{labelFormatter ? labelFormatter(label) : label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} className="tooltip-row">
          <span className="swatch" style={{ background: p.color || p.payload.fill }} />
          <span>{p.name}</span>
          <strong>{valueFormatter ? valueFormatter(p.value) : p.value}</strong>
        </div>
      ))}
    </div>
  )
}

export function TrendChart({ data, x, y, name, valueFormatter, xFormatter, height = 260, area = true }) {
  const Chart = area ? AreaChart : LineChart
  return (
    <ResponsiveContainer width="100%" height={height}>
      <Chart data={data} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={COLORS.grid} vertical={false} />
        <XAxis dataKey={x} {...axisProps} tickFormatter={xFormatter} minTickGap={16} />
        <YAxis {...axisProps} tickFormatter={valueFormatter} width={72} />
        <Tooltip content={<ChartTooltip valueFormatter={valueFormatter} labelFormatter={xFormatter} />}
                 cursor={{ stroke: COLORS.axis, strokeDasharray: '3 3' }} />
        {area ? (
          <Area type="monotone" dataKey={y} name={name} stroke={COLORS.series1} strokeWidth={2}
                fill={COLORS.series1} fillOpacity={0.12} activeDot={{ r: 5, strokeWidth: 2, stroke: '#fff' }} />
        ) : (
          <Line type="linear" dataKey={y} name={name} stroke={COLORS.series1} strokeWidth={2}
                dot={false} activeDot={{ r: 5, strokeWidth: 2, stroke: '#fff' }} />
        )}
        {!area && <ReferenceLine y={0} stroke={COLORS.axis} />}
      </Chart>
    </ResponsiveContainer>
  )
}

// Vertical or horizontal bar chart. colorFor(row) can override the colour per bar (status charts).
export function BarsChart({ data, x, y, name, valueFormatter, xFormatter, horizontal = false, height = 260, colorFor }) {
  const radius = horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout={horizontal ? 'vertical' : 'horizontal'}
                margin={{ top: 10, right: 16, left: 0, bottom: 0 }} barCategoryGap={horizontal ? 6 : '20%'}>
        <CartesianGrid stroke={COLORS.grid} horizontal={!horizontal} vertical={horizontal} />
        {horizontal ? (
          <>
            <XAxis type="number" {...axisProps} tickFormatter={valueFormatter} />
            <YAxis type="category" dataKey={x} {...axisProps} width={130} tickFormatter={xFormatter} />
          </>
        ) : (
          <>
            <XAxis dataKey={x} {...axisProps} tickFormatter={xFormatter} minTickGap={8} />
            <YAxis {...axisProps} tickFormatter={valueFormatter} width={72} />
          </>
        )}
        <Tooltip content={<ChartTooltip valueFormatter={valueFormatter} labelFormatter={xFormatter} />}
                 cursor={{ fill: 'rgba(11,11,11,0.04)' }} />
        <Bar dataKey={y} name={name} fill={COLORS.series1} radius={radius} maxBarSize={36}>
          {colorFor && data.map((row, i) => <Cell key={i} fill={colorFor(row)} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
