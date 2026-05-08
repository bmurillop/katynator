import { useState } from 'react'
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

function EditAccountModal({ account, persons, onClose, onSaved }) {
  const [nickname, setNickname] = useState(account.nickname || '')
  const [accountType, setAccountType] = useState(account.account_type)
  const [personId, setPersonId] = useState(account.person_id || '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSave = async () => {
    setSaving(true)
    setError('')
    try {
      await updateAccount(account.id, {
        nickname: nickname.trim() || null,
        account_type: accountType,
        person_id: personId || null,
      })
      onSaved()
    } catch (e) {
      setError(e.response?.data?.detail || 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-ink">Editar cuenta</h2>
          <button onClick={onClose} className="text-ink/30 hover:text-ink text-xl leading-none">✕</button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-ink/60 mb-1">Apodo (opcional)</label>
            <input
              type="text"
              className="input text-sm"
              placeholder="ej. Cuenta nómina, Visa personal…"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-ink/60 mb-1">Tipo de cuenta</label>
            <select className="select text-sm" value={accountType} onChange={(e) => setAccountType(e.target.value)}>
              {Object.entries(accountTypeLabel).map(([val, label]) => (
                <option key={val} value={val}>{label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-ink/60 mb-1">Titular</label>
            <select className="select text-sm" value={personId} onChange={(e) => setPersonId(e.target.value)}>
              <option value="">— Sin asignar —</option>
              {(persons || []).map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
        </div>

        {error && <p className="text-red-500 text-xs">{error}</p>}

        <div className="flex gap-2 pt-1">
          <button onClick={handleSave} disabled={saving} className="btn-primary text-sm flex-1">
            {saving ? 'Guardando…' : 'Guardar'}
          </button>
          <button onClick={onClose} className="btn-ghost text-sm flex-1 border border-brown-600/30">
            Cancelar
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Accounts() {
  const qc = useQueryClient()
  const [editing, setEditing] = useState(null)
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
                        {a.nickname || (a.account_number_hint ? `···${a.account_number_hint}` : accountTypeLabel[a.account_type])}
                      </span>
                      <CurrencyBadge currency={a.currency} />
                    </div>
                    <p className="text-xs text-ink/40 mt-0.5">
                      {accountTypeLabel[a.account_type]}
                      {a.nickname && a.account_number_hint ? ` · ···${a.account_number_hint}` : ''}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {!a.confirmed && (
                      <span className="badge bg-amber-500/20 text-amber-500 text-[10px]">Sin confirmar</span>
                    )}
                    <button
                      onClick={() => setEditing(a)}
                      className="text-xs text-ink/30 hover:text-amber-500 transition-colors"
                      title="Editar cuenta"
                    >
                      ✎
                    </button>
                  </div>
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

      {editing && (
        <EditAccountModal
          account={editing}
          persons={persons}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); qc.invalidateQueries({ queryKey: ['accounts'] }) }}
        />
      )}
    </div>
  )
}
