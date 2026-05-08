import { useQuery } from '@tanstack/react-query'
import { BarChart } from '@tremor/react'
import { getSummary, getMonthlySummary } from '../api/transactions'
import { listAccounts } from '../api/accounts'
import { listEmails } from '../api/emails'
import { listUnresolved } from '../api/unresolvedEntities'
import CurrencyAmount, { CurrencyBadge } from '../components/CurrencyAmount'
import { Link } from 'react-router-dom'

const MONTH_FMT = new Intl.DateTimeFormat('es-CR', { month: 'short', year: '2-digit' })
const formatMonth = (ym) => {
  const [y, m] = ym.split('-').map(Number)
  return MONTH_FMT.format(new Date(y, m - 1, 1))
}

function buildChartData(monthly, cur) {
  if (!monthly?.items) return []
  const byMonth = {}
  monthly.items
    .filter((i) => i.currency === cur)
    .forEach((i) => {
      if (!byMonth[i.month]) byMonth[i.month] = { _month: i.month, Gastos: 0, Ingresos: 0 }
      if (i.direction === 'debit') byMonth[i.month].Gastos = Number(i.total)
      else byMonth[i.month].Ingresos = Number(i.total)
    })
  return Object.values(byMonth)
    .sort((a, b) => a._month.localeCompare(b._month))
    .map(({ _month, ...rest }) => ({ month: formatMonth(_month), ...rest }))
}

function StatCard({ label, value, sub, accent }) {
  return (
    <div className="card flex flex-col gap-1">
      <p className="text-xs text-ink/50 font-medium uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold ${accent || 'text-ink'}`}>{value}</p>
      {sub && <p className="text-xs text-ink/40">{sub}</p>}
    </div>
  )
}

function CurrencySection({ label, cur, summary, monthly }) {
  const getTotal = (dir) => summary?.summaries?.find((s) => s.direction === dir)?.total ?? 0
  const getCount = (dir) => summary?.summaries?.find((s) => s.direction === dir)?.count ?? 0
  const chartData = buildChartData(monthly, cur)
  const fmtVal = (v) =>
    cur === 'CRC'
      ? `₡${Intl.NumberFormat('es-CR').format(Math.round(v))}`
      : `$${Intl.NumberFormat('es-CR').format(v)}`

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-semibold text-ink/60 uppercase tracking-wide">{label}</h2>
        <CurrencyBadge currency={cur} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard
          label="Gastos (total)"
          value={<CurrencyAmount amount={getTotal('debit')} currency={cur} />}
          sub={`${getCount('debit')} transacciones`}
        />
        <StatCard
          label="Ingresos (total)"
          value={<CurrencyAmount amount={getTotal('credit')} currency={cur} direction="credit" />}
          sub={`${getCount('credit')} transacciones`}
          accent="text-green-600"
        />
      </div>
      {chartData.length > 1 && (
        <div className="card">
          <p className="text-xs text-ink/40 font-medium uppercase tracking-wide mb-3">Últimos meses</p>
          <BarChart
            data={chartData}
            index="month"
            categories={['Gastos', 'Ingresos']}
            colors={['rose', 'emerald']}
            valueFormatter={fmtVal}
            showLegend
            showGridLines={false}
            className="h-40"
          />
        </div>
      )}
    </div>
  )
}

export default function Dashboard() {
  const { data: crcSummary } = useQuery({
    queryKey: ['summary', 'CRC'],
    queryFn: () => getSummary({ currency: 'CRC' }),
  })
  const { data: usdSummary } = useQuery({
    queryKey: ['summary', 'USD'],
    queryFn: () => getSummary({ currency: 'USD' }),
  })
  const { data: monthly } = useQuery({
    queryKey: ['summary-monthly'],
    queryFn: () => getMonthlySummary({ months: 6 }),
  })
  const { data: accounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => listAccounts({ page_size: 50 }),
  })
  const { data: emails } = useQuery({
    queryKey: ['emails', 'failed'],
    queryFn: () => listEmails({ status: 'failed', page_size: 5 }),
  })
  const { data: unresolved } = useQuery({
    queryKey: ['unresolved', 'pending'],
    queryFn: () => listUnresolved({ status: 'pending', page_size: 1 }),
  })

  const unconfirmedCount = accounts?.items?.filter((a) => !a.confirmed).length ?? 0
  const failedEmailCount = emails?.total ?? 0
  const pendingEntityCount = unresolved?.total ?? 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-ink">Panel</h1>
        <p className="text-sm text-ink/50 mt-0.5">Resumen financiero familiar</p>
      </div>

      <CurrencySection label="Colones (CRC)" cur="CRC" summary={crcSummary} monthly={monthly} />
      <CurrencySection label="Dólares (USD)" cur="USD" summary={usdSummary} monthly={monthly} />

      {(unconfirmedCount > 0 || failedEmailCount > 0 || pendingEntityCount > 0) && (
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-ink/60 uppercase tracking-wide">Atención requerida</h2>
          {pendingEntityCount > 0 && (
            <Link to="/bandeja" className="card flex items-center gap-3 hover:border-amber-500/50 transition-colors cursor-pointer">
              <span className="text-amber-500 text-lg">⚑</span>
              <div>
                <p className="text-sm font-medium text-ink">{pendingEntityCount} nombre{pendingEntityCount !== 1 ? 's' : ''} sin resolver</p>
                <p className="text-xs text-ink/40">Ir a la bandeja para revisar</p>
              </div>
            </Link>
          )}
          {unconfirmedCount > 0 && (
            <Link to="/cuentas" className="card flex items-center gap-3 hover:border-amber-500/50 transition-colors cursor-pointer">
              <span className="text-amber-500 text-lg">🏦</span>
              <div>
                <p className="text-sm font-medium text-ink">{unconfirmedCount} cuenta{unconfirmedCount !== 1 ? 's' : ''} sin confirmar</p>
                <p className="text-xs text-ink/40">Revisa y confirma tus cuentas</p>
              </div>
            </Link>
          )}
          {failedEmailCount > 0 && (
            <Link to="/bandeja?tab=correos" className="card flex items-center gap-3 hover:border-amber-500/50 transition-colors cursor-pointer">
              <span className="text-red-500 text-lg">✉</span>
              <div>
                <p className="text-sm font-medium text-ink">{failedEmailCount} correo{failedEmailCount !== 1 ? 's' : ''} con error</p>
                <p className="text-xs text-ink/40">Ver correos fallidos</p>
              </div>
            </Link>
          )}
        </div>
      )}
    </div>
  )
}
