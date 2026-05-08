const formatters = {
  CRC: new Intl.NumberFormat('es-CR', { style: 'currency', currency: 'CRC', minimumFractionDigits: 2 }),
  USD: new Intl.NumberFormat('es-CR', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }),
}

export default function CurrencyAmount({ amount, currency, direction, className = '' }) {
  const formatter = formatters[currency] ?? formatters.CRC
  const isCredit = direction === 'credit'

  return (
    <span
      className={`font-mono tabular-nums ${
        isCredit ? 'text-green-600' : 'text-ink/90'
      } ${className}`}
    >
      {isCredit ? '+' : ''}{formatter.format(Number(amount))}
    </span>
  )
}

export function CurrencyBadge({ currency }) {
  return (
    <span className={`badge text-[10px] font-bold ${
      currency === 'USD'
        ? 'bg-green-800/40 text-green-600'
        : 'bg-amber-500/20 text-amber-500'
    }`}>
      {currency}
    </span>
  )
}
