import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listTransactions, updateTransaction } from '../api/transactions'
import { listCategories } from '../api/categories'
import { listAccounts } from '../api/accounts'
import { createRule } from '../api/categoryRules'
import CurrencyAmount, { CurrencyBadge } from '../components/CurrencyAmount'
import Pagination from '../components/Pagination'

const PAGE_SIZE = 50

// Extract most distinctive token for memo-rule suggestion
function bestMemoToken(description) {
  const stopwords = new Set(['de', 'del', 'la', 'el', 'en', 'a', 'y', 'e', 'con', 'por', 'para', 'the', 'and', 'of'])
  const tokens = description.toLowerCase().replace(/[^a-záéíóúñ0-9\s]/gi, '').split(/\s+/)
  const candidate = tokens.find((t) => t.length > 3 && !stopwords.has(t) && !/^\d+$/.test(t))
  return candidate || null
}

function CategoryModal({ txn, categories, onClose, onSaved }) {
  const [categoryId, setCategoryId] = useState('')
  const [scope, setScope] = useState('transaction')
  const [memoToken, setMemoToken] = useState(bestMemoToken(txn.description_normalized) || '')
  const [saving, setSaving] = useState(false)
  const qc = useQueryClient()

  const handleSave = async () => {
    if (!categoryId) return
    setSaving(true)
    try {
      await updateTransaction(txn.id, {
        category_id: categoryId,
        category_source: 'user_set',
        needs_review: false,
      })

      if (scope !== 'transaction') {
        const rulePayload = { category_id: categoryId, match_type: 'any', priority: 50, source: 'user_confirmed' }
        if (scope === 'entity' && txn.merchant_entity_id) {
          rulePayload.entity_id = txn.merchant_entity_id
        } else if (scope === 'entity_memo' && txn.merchant_entity_id && memoToken) {
          rulePayload.entity_id = txn.merchant_entity_id
          rulePayload.memo_pattern = memoToken
          rulePayload.match_type = 'contains'
        } else if (scope === 'memo' && memoToken) {
          rulePayload.memo_pattern = memoToken
          rulePayload.match_type = 'contains'
        }
        if (rulePayload.entity_id || rulePayload.memo_pattern) {
          await createRule(rulePayload)
        }
      }

      qc.invalidateQueries({ queryKey: ['transactions'] })
      onSaved()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white border border-brown-600/20 rounded-xl w-full max-w-md shadow-2xl">
        <div className="px-5 py-4 border-b border-brown-600/15">
          <h3 className="font-semibold text-ink">Categorizar transacción</h3>
          <p className="text-xs text-ink/50 mt-0.5 truncate">{txn.description_raw}</p>
        </div>

        <div className="px-5 py-4 space-y-4">
          <div>
            <label className="block text-xs font-medium text-ink/60 mb-1.5">Categoría</label>
            <select className="select" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
              <option value="">— Seleccionar —</option>
              {categories?.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          {categoryId && (
            <div>
              <label className="block text-xs font-medium text-ink/60 mb-2">Aplicar esta categoría a:</label>
              <div className="space-y-2">
                {[
                  { value: 'transaction', label: 'Solo esta transacción' },
                  ...(txn.merchant_entity_id ? [
                    { value: 'entity', label: 'Todas las transacciones de esta entidad' },
                    ...(memoToken ? [{ value: 'entity_memo', label: `Entidad + memo contiene "${memoToken}" (recomendado)` }] : []),
                  ] : []),
                  ...(memoToken ? [{ value: 'memo', label: `Memo contiene "${memoToken}"` }] : []),
                ].map(({ value, label }) => (
                  <label key={value} className="flex items-start gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="scope"
                      value={value}
                      checked={scope === value}
                      onChange={() => setScope(value)}
                      className="mt-0.5 accent-amber-500"
                    />
                    <span className="text-sm text-ink/80">{label}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {(scope === 'entity_memo' || scope === 'memo') && (
            <div>
              <label className="block text-xs font-medium text-ink/60 mb-1.5">Patrón del memo</label>
              <input
                type="text"
                className="input"
                value={memoToken}
                onChange={(e) => setMemoToken(e.target.value)}
              />
            </div>
          )}
        </div>

        <div className="px-5 py-4 border-t border-brown-600/15 flex gap-2 justify-end">
          <button onClick={onClose} className="btn-ghost text-sm">Cancelar</button>
          <button onClick={handleSave} disabled={!categoryId || saving} className="btn-primary text-sm">
            {saving ? 'Guardando…' : 'Guardar'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Transactions() {
  const [page, setPage] = useState(1)
  const [currency, setCurrency] = useState('')
  const [needsReview, setNeedsReview] = useState(false)
  const [accountId, setAccountId] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [modalTxn, setModalTxn] = useState(null)
  const qc = useQueryClient()

  const params = {
    page, page_size: PAGE_SIZE,
    ...(currency && { currency }),
    ...(needsReview && { needs_review: true }),
    ...(accountId && { account_id: accountId }),
    ...(dateFrom && { date_from: dateFrom }),
    ...(dateTo && { date_to: dateTo }),
  }

  const { data, isLoading } = useQuery({
    queryKey: ['transactions', params],
    queryFn: () => listTransactions(params),
  })
  const { data: categories } = useQuery({ queryKey: ['categories'], queryFn: listCategories })
  const { data: accounts } = useQuery({ queryKey: ['accounts'], queryFn: () => listAccounts({ page_size: 100 }) })

  const catMap = Object.fromEntries((categories || []).map((c) => [c.id, c]))

  const toggleReview = async (txn) => {
    await updateTransaction(txn.id, { needs_review: !txn.needs_review })
    qc.invalidateQueries({ queryKey: ['transactions'] })
  }

  const resetPage = () => setPage(1)

  return (
    <div className="space-y-4">
      {modalTxn && (
        <CategoryModal
          txn={modalTxn}
          categories={categories}
          onClose={() => setModalTxn(null)}
          onSaved={() => setModalTxn(null)}
        />
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-ink">Transacciones</h1>
          {data && <p className="text-xs text-ink/40 mt-0.5">{data.total} resultado{data.total !== 1 ? 's' : ''}</p>}
        </div>
      </div>

      {/* Filters */}
      <div className="card flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-ink/50 mb-1">Moneda</label>
          <select className="select w-28" value={currency} onChange={(e) => { setCurrency(e.target.value); resetPage() }}>
            <option value="">Todas</option>
            <option value="CRC">CRC</option>
            <option value="USD">USD</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-ink/50 mb-1">Cuenta</label>
          <select className="select w-44" value={accountId} onChange={(e) => { setAccountId(e.target.value); resetPage() }}>
            <option value="">Todas</option>
            {accounts?.items?.map((a) => (
              <option key={a.id} value={a.id}>
                {a.account_number_hint || a.account_type} · {a.currency}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-ink/50 mb-1">Desde</label>
          <input type="date" className="input w-36" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); resetPage() }} />
        </div>
        <div>
          <label className="block text-xs text-ink/50 mb-1">Hasta</label>
          <input type="date" className="input w-36" value={dateTo} onChange={(e) => { setDateTo(e.target.value); resetPage() }} />
        </div>
        <label className="flex items-center gap-2 cursor-pointer mb-0.5">
          <input
            type="checkbox"
            checked={needsReview}
            onChange={(e) => { setNeedsReview(e.target.checked); resetPage() }}
            className="accent-amber-500 w-4 h-4"
          />
          <span className="text-sm text-ink/70">Solo pendientes de revisión</span>
        </label>
      </div>

      {/* Table */}
      <div className="card p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-brown-600/20">
              <tr>
                <th className="table-header">Fecha</th>
                <th className="table-header">Descripción</th>
                <th className="table-header text-right">Monto</th>
                <th className="table-header">Moneda</th>
                <th className="table-header">Categoría</th>
                <th className="table-header w-8"></th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr><td colSpan={6} className="table-cell text-center text-ink/40 py-12">Cargando…</td></tr>
              )}
              {!isLoading && !data?.items?.length && (
                <tr><td colSpan={6} className="table-cell text-center text-ink/40 py-12">Sin transacciones</td></tr>
              )}
              {data?.items?.map((txn) => (
                <tr key={txn.id} className={`table-row ${txn.needs_review ? 'bg-amber-500/5' : ''}`}>
                  <td className="table-cell whitespace-nowrap text-ink/50 text-xs">
                    {new Date(txn.date + 'T12:00:00').toLocaleDateString('es-CR')}
                  </td>
                  <td className="table-cell max-w-xs">
                    <p className="truncate text-ink/90">{txn.description_raw}</p>
                    {txn.needs_review && (
                      <span className="badge bg-amber-500/20 text-amber-500 text-[10px]">Revisar</span>
                    )}
                  </td>
                  <td className="table-cell text-right">
                    <CurrencyAmount amount={txn.amount} currency={txn.currency} direction={txn.direction} />
                  </td>
                  <td className="table-cell"><CurrencyBadge currency={txn.currency} /></td>
                  <td className="table-cell">
                    <button
                      onClick={() => setModalTxn(txn)}
                      className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                        txn.category_id
                          ? 'border-green-800/50 text-green-600 hover:border-green-600'
                          : 'border-brown-600/40 text-ink/40 hover:border-amber-500/50 hover:text-amber-500'
                      }`}
                    >
                      {txn.category_id ? catMap[txn.category_id]?.name ?? '—' : 'Sin categoría'}
                    </button>
                  </td>
                  <td className="table-cell">
                    <button
                      onClick={() => toggleReview(txn)}
                      title={txn.needs_review ? 'Marcar revisado' : 'Marcar para revisar'}
                      className={`text-xs ${txn.needs_review ? 'text-amber-500' : 'text-ink/20 hover:text-ink/50'}`}
                    >
                      ⚑
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {data && <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onPage={setPage} />}
      </div>
    </div>
  )
}
