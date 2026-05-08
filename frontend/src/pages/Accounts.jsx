import { useQuery, useQueryClient } from '@tanstack/react-query'
import { listAccounts, updateAccount } from '../api/accounts'
import { listPersons } from '../api/persons'
import CurrencyAmount, { CurrencyBadge } from '../components/CurrencyAmount'

const accountTypeLabel = {
  savings: 'Ahorros',
  checking: 'Corriente',
  credit_card: 'Tarjeta de crédito',
  loan: 'Préstamo',
  other: 'Otro',
}

export default function Accounts() {
  const qc = useQueryClient()
  const { data: accounts, isLoading } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => listAccounts({ page_size: 100 }),
  })
  const { data: persons } = useQuery({ queryKey: ['persons'], queryFn: listPersons })

  const personMap = Object.fromEntries((persons || []).map((p) => [p.id, p]))

  const confirm = async (account) => {
    await updateAccount(account.id, { confirmed: true })
    qc.invalidateQueries({ queryKey: ['accounts'] })
  }

  const grouped = (accounts?.items || []).reduce((acc, a) => {
    const pid = a.person_id
    if (!acc[pid]) acc[pid] = []
    acc[pid].push(a)
    return acc
  }, {})

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-ink">Cuentas</h1>
        <p className="text-sm text-ink/50 mt-0.5">{accounts?.total ?? 0} cuenta{accounts?.total !== 1 ? 's' : ''}</p>
      </div>

      {isLoading && <p className="text-ink/40 text-sm">Cargando…</p>}

      {Object.entries(grouped).map(([personId, accs]) => (
        <div key={personId}>
          <h2 className="text-sm font-semibold text-ink/60 uppercase tracking-wide mb-3">
            {personMap[personId]?.name ?? 'Sin persona'}
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {accs.map((a) => (
              <div
                key={a.id}
                className={`card flex flex-col gap-3 ${!a.confirmed ? 'border-amber-500/40' : ''}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-ink">
                        {a.account_number_hint ? `···${a.account_number_hint}` : accountTypeLabel[a.account_type]}
                      </span>
                      <CurrencyBadge currency={a.currency} />
                    </div>
                    <p className="text-xs text-ink/40 mt-0.5">{accountTypeLabel[a.account_type]}</p>
                  </div>
                  {!a.confirmed && (
                    <span className="badge bg-amber-500/20 text-amber-500 text-[10px] shrink-0">Sin confirmar</span>
                  )}
                </div>

                {a.last_known_balance != null && (
                  <div>
                    <p className="text-xs text-ink/40">Saldo conocido</p>
                    <CurrencyAmount
                      amount={a.last_known_balance}
                      currency={a.currency}
                      className="text-lg font-bold"
                    />
                    {a.balance_as_of && (
                      <p className="text-[10px] text-ink/30">
                        al {new Date(a.balance_as_of + 'T12:00:00').toLocaleDateString('es-CR')}
                      </p>
                    )}
                  </div>
                )}

                {!a.confirmed && (
                  <button onClick={() => confirm(a)} className="btn-primary text-xs py-1.5">
                    Confirmar cuenta
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}

      {!isLoading && !accounts?.total && (
        <div className="card text-center py-12 text-ink/40">
          <p className="text-4xl mb-3">🏦</p>
          <p>No hay cuentas todavía.</p>
          <p className="text-sm mt-1">Se crearán automáticamente al procesar estados de cuenta.</p>
        </div>
      )}
    </div>
  )
}
