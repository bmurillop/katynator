import { useState, useDeferredValue, Fragment } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { listTransactions, updateTransaction, suggestCategoriesAI, suggestEntitiesAI } from '../api/transactions'
import { listCategories } from '../api/categories'
import { listAccounts } from '../api/accounts'
import { listRules, createRule, updateRule, deleteRule, previewRule, applyRule, reapplyRules } from '../api/categoryRules'
import { listEntities } from '../api/entities'
import { useAuth } from '../context/AuthContext'
import CurrencyAmount, { CurrencyBadge } from '../components/CurrencyAmount'
import Pagination from '../components/Pagination'

const PAGE_SIZE = 50
const REVIEW_PAGE_SIZE = 20

const MATCH_TYPE_LABELS = {
  starts_with: 'Empieza con',
  contains: 'Contiene',
  exact: 'Exacto',
}

const matchTypeLabelFull = { any: 'Cualquier', contains: 'Contiene', starts_with: 'Empieza con', exact: 'Exacto', regex: 'Regex' }
const sourceLabel = { user_confirmed: 'Manual', ai_suggested: 'IA' }

// ── Category modal (for transaction list inline classification) ───────────────

function CategoryModal({ txn, categories, onClose, onSaved }) {
  const isTransfer = txn.is_transfer
  const [mode, setMode] = useState(isTransfer ? 'transfer' : 'categorize')
  const [categoryId, setCategoryId] = useState(txn.category_id || '')
  const [scope, setScope] = useState(txn.merchant_entity_id ? 'entity' : 'transaction')
  const [limitToEntity, setLimitToEntity] = useState(!!txn.merchant_entity_id)
  const [memoPattern, setMemoPattern] = useState(txn.description_normalized)
  const [matchType, setMatchType] = useState('starts_with')
  const [applyToExisting, setApplyToExisting] = useState(true)
  const [saving, setSaving] = useState(false)
  const qc = useQueryClient()

  const deferredPattern = useDeferredValue(memoPattern)
  const deferredMatchType = useDeferredValue(matchType)

  const showPatternControls = scope === 'pattern'
  const previewParams = showPatternControls && deferredPattern
    ? {
        memo_pattern: deferredPattern,
        match_type: deferredMatchType,
        ...(limitToEntity && txn.merchant_entity_id ? { entity_id: txn.merchant_entity_id } : {}),
      }
    : null

  const { data: previewData } = useQuery({
    queryKey: ['rule-preview', previewParams],
    queryFn: () => previewRule(previewParams),
    enabled: !!previewParams,
    staleTime: 2000,
  })

  const canSave = mode === 'transfer' || (mode === 'categorize' && !!categoryId)

  const handleSave = async () => {
    if (!canSave) return
    setSaving(true)
    try {
      if (mode === 'transfer') {
        await updateTransaction(txn.id, { is_transfer: true, category_id: null, needs_review: false })
      } else {
        await updateTransaction(txn.id, { category_id: categoryId, category_source: 'user_set', is_transfer: false, needs_review: false })
      }

      if (scope !== 'transaction') {
        const rulePayload = {
          priority: 50,
          source: 'user_confirmed',
          match_type: 'any',
          ...(mode === 'transfer' ? { sets_transfer: true } : { category_id: categoryId }),
        }
        if (scope === 'entity' && txn.merchant_entity_id) {
          rulePayload.entity_id = txn.merchant_entity_id
        } else if (scope === 'pattern' && memoPattern.trim()) {
          rulePayload.memo_pattern = memoPattern.trim()
          rulePayload.match_type = matchType
          if (limitToEntity && txn.merchant_entity_id) {
            rulePayload.entity_id = txn.merchant_entity_id
          }
        }
        if (rulePayload.entity_id || rulePayload.memo_pattern) {
          const createdRule = await createRule(rulePayload)
          if (applyToExisting && createdRule?.id) {
            await applyRule(createdRule.id)
          }
        }
      }

      qc.invalidateQueries({ queryKey: ['transactions'] })
      onSaved()
    } finally {
      setSaving(false)
    }
  }

  const scopeOptions = [
    { value: 'transaction', label: 'Solo esta transacción' },
    ...(txn.merchant_entity_id ? [{ value: 'entity', label: 'Todas las de esta entidad' }] : []),
    { value: 'pattern', label: 'Por patrón de descripción' },
  ]

  const showScopeAndPattern = mode === 'transfer' || (mode === 'categorize' && !!categoryId)

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white border border-brown-600/20 rounded-xl w-full max-w-lg shadow-2xl">
        <div className="px-5 py-4 border-b border-brown-600/15">
          <h3 className="font-semibold text-ink">Clasificar transacción</h3>
          <p className="text-xs text-ink/50 mt-0.5 font-mono truncate">{txn.description_raw}</p>
        </div>

        <div className="px-5 py-4 space-y-4">
          <div className="flex rounded-lg border border-brown-600/20 overflow-hidden">
            {[
              { value: 'categorize', label: 'Gasto / Ingreso' },
              { value: 'transfer', label: '⇌ Transferencia interna' },
            ].map(({ value, label }) => (
              <button
                key={value}
                onClick={() => setMode(value)}
                className={`flex-1 py-2 text-sm font-medium transition-colors ${
                  mode === value
                    ? value === 'transfer'
                      ? 'bg-blue-50 text-blue-700 border-blue-200'
                      : 'bg-amber-500/10 text-amber-700'
                    : 'text-ink/50 hover:text-ink'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {mode === 'transfer' && (
            <p className="text-xs text-ink/50 bg-[#F5EFE0] rounded-lg px-3 py-2">
              Esta transacción se excluirá de todos los reportes de gastos e ingresos.
            </p>
          )}

          {mode === 'categorize' && (
            <div>
              <label className="block text-xs font-medium text-ink/60 mb-1.5">Categoría</label>
              <select className="select" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
                <option value="">— Seleccionar —</option>
                {categories?.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          )}

          {showScopeAndPattern && (
            <div>
              <label className="block text-xs font-medium text-ink/60 mb-2">Crear regla para:</label>
              <div className="space-y-2">
                {scopeOptions.map(({ value, label }) => (
                  <label key={value} className="flex items-center gap-2 cursor-pointer">
                    <input type="radio" name="scope" value={value} checked={scope === value}
                      onChange={() => setScope(value)} className="accent-amber-500" />
                    <span className="text-sm text-ink/80">{label}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {showScopeAndPattern && showPatternControls && (
            <div className="bg-[#F5EFE0] rounded-xl p-4 space-y-3">
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="block text-xs font-medium text-ink/60 mb-1">Patrón</label>
                  <input type="text" className="input text-sm font-mono" value={memoPattern}
                    onChange={(e) => setMemoPattern(e.target.value)} autoFocus />
                </div>
                <div>
                  <label className="block text-xs font-medium text-ink/60 mb-1">Tipo</label>
                  <select className="select text-sm" value={matchType} onChange={(e) => setMatchType(e.target.value)}>
                    {Object.entries(MATCH_TYPE_LABELS).map(([k, v]) => (
                      <option key={k} value={k}>{v}</option>
                    ))}
                  </select>
                </div>
              </div>

              {txn.merchant_entity_id && (
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={limitToEntity}
                    onChange={(e) => setLimitToEntity(e.target.checked)} className="accent-amber-500 w-4 h-4" />
                  <span className="text-sm text-ink/70">Limitar a esta entidad</span>
                </label>
              )}

              {previewData != null && (
                <div className="space-y-2">
                  <p className={`text-xs font-medium ${previewData.count > 0 ? 'text-green-700' : 'text-ink/40'}`}>
                    {previewData.count > 0
                      ? `Aplicaría a ${previewData.count} transacción${previewData.count !== 1 ? 'es' : ''} existente${previewData.count !== 1 ? 's' : ''}`
                      : 'Sin coincidencias en transacciones existentes'}
                  </p>
                  {previewData.count > 0 && (
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={applyToExisting}
                        onChange={(e) => setApplyToExisting(e.target.checked)} className="accent-amber-500 w-4 h-4" />
                      <span className="text-sm text-ink/70">Aplicar también a esas transacciones ahora</span>
                    </label>
                  )}
                </div>
              )}
            </div>
          )}

          {showScopeAndPattern && scope === 'entity' && txn.merchant_entity_id && (
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={applyToExisting}
                onChange={(e) => setApplyToExisting(e.target.checked)} className="accent-amber-500 w-4 h-4" />
              <span className="text-sm text-ink/70">Aplicar también a transacciones existentes de esta entidad</span>
            </label>
          )}
        </div>

        <div className="px-5 py-4 border-t border-brown-600/15 flex gap-2 justify-end">
          <button onClick={onClose} className="btn-ghost text-sm">Cancelar</button>
          <button onClick={handleSave} disabled={!canSave || saving} className="btn-primary text-sm">
            {saving ? 'Guardando…' : 'Guardar'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Shared rule form fields ───────────────────────────────────────────────────

function RuleFields({ entityId, setEntityId, memoPattern, setMemoPattern, matchType, setMatchType,
  categoryId, setCategoryId, setsTransfer, setSetsTransfer, priority, setPriority, categories, entities }) {
  return (
    <div className="space-y-3">
      <div>
        <label className="block text-xs text-ink/50 mb-1">Entidad (opcional)</label>
        <select className="select" value={entityId} onChange={(e) => setEntityId(e.target.value)}>
          <option value="">— Cualquier entidad —</option>
          {entities?.items?.map((e) => (
            <option key={e.id} value={e.id}>{e.display_name || e.canonical_name}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-ink/50 mb-1">Patrón del memo (opcional)</label>
          <input type="text" className="input font-mono" placeholder="pago tarjeta…"
            value={memoPattern} onChange={(e) => setMemoPattern(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs text-ink/50 mb-1">Tipo de match</label>
          <select className="select" value={matchType} onChange={(e) => setMatchType(e.target.value)}>
            <option value="starts_with">Empieza con</option>
            <option value="contains">Contiene</option>
            <option value="exact">Exacto</option>
            <option value="regex">Regex</option>
            <option value="any">Cualquier</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-ink/50 mb-1">
            {setsTransfer ? 'Tipo' : 'Categoría *'}
          </label>
          {setsTransfer ? (
            <div className="input flex items-center gap-2 text-blue-600 bg-blue-50/60 text-sm cursor-default">
              ⇌ Transferencia interna
            </div>
          ) : (
            <select className="select" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
              <option value="">— Seleccionar —</option>
              {categories?.map((c) => (
                <option key={c.id} value={c.id}>{c.icon ? `${c.icon} ` : ''}{c.name}</option>
              ))}
            </select>
          )}
        </div>
        <div>
          <label className="block text-xs text-ink/50 mb-1">Prioridad (1–100)</label>
          <input type="number" className="input" min={1} max={100} value={priority}
            onChange={(e) => setPriority(e.target.value)} />
        </div>
      </div>

      <label className="flex items-center gap-2 cursor-pointer pt-1">
        <input type="checkbox" checked={setsTransfer}
          onChange={(e) => { setSetsTransfer(e.target.checked); if (e.target.checked) setCategoryId('') }}
          className="accent-amber-500 w-4 h-4" />
        <span className="text-sm text-ink/70">Marcar como transferencia interna (excluir de reportes)</span>
      </label>
    </div>
  )
}

// ── New rule modal ────────────────────────────────────────────────────────────

function NewRuleModal({ categories, entities, onClose, onSaved }) {
  const [entityId, setEntityId] = useState('')
  const [memoPattern, setMemoPattern] = useState('')
  const [matchType, setMatchType] = useState('starts_with')
  const [categoryId, setCategoryId] = useState('')
  const [setsTransfer, setSetsTransfer] = useState(false)
  const [priority, setPriority] = useState(50)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const canSave = (setsTransfer || categoryId) && (entityId || memoPattern.trim())

  const handleSave = async () => {
    if (!canSave) return
    setSaving(true)
    setError('')
    try {
      await createRule({
        entity_id: entityId || undefined,
        memo_pattern: memoPattern.trim() || undefined,
        match_type: matchType,
        category_id: setsTransfer ? undefined : categoryId,
        sets_transfer: setsTransfer,
        priority: Number(priority),
        source: 'user_confirmed',
      })
      onSaved()
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al crear la regla')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white border border-brown-600/20 rounded-xl w-full max-w-md shadow-2xl">
        <div className="px-5 py-4 border-b border-brown-600/15">
          <h3 className="font-semibold text-ink">Nueva regla de categoría</h3>
          <p className="text-xs text-ink/50 mt-0.5">Debe especificar al menos entidad o patrón de memo</p>
        </div>
        <div className="px-5 py-4">
          <RuleFields {...{ entityId, setEntityId, memoPattern, setMemoPattern, matchType, setMatchType,
            categoryId, setCategoryId, setsTransfer, setSetsTransfer, priority, setPriority, categories, entities }} />
          {error && (
            <p className="text-red-500 text-xs bg-red-50 border border-red-200 rounded px-3 py-2 mt-3">{error}</p>
          )}
        </div>
        <div className="px-5 py-4 border-t border-brown-600/15 flex gap-2 justify-end">
          <button onClick={onClose} className="btn-ghost text-sm">Cancelar</button>
          <button onClick={handleSave} disabled={!canSave || saving} className="btn-primary text-sm">
            {saving ? 'Guardando…' : 'Crear regla'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Edit rule modal ───────────────────────────────────────────────────────────

function EditRuleModal({ rule, categories, entities, onClose, onSaved }) {
  const [entityId, setEntityId] = useState(rule.entity_id || '')
  const [memoPattern, setMemoPattern] = useState(rule.memo_pattern || '')
  const [matchType, setMatchType] = useState(rule.match_type)
  const [categoryId, setCategoryId] = useState(rule.category_id || '')
  const [setsTransfer, setSetsTransfer] = useState(rule.sets_transfer || false)
  const [priority, setPriority] = useState(rule.priority)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const canSave = (setsTransfer || categoryId) && (entityId || memoPattern.trim())

  const handleSave = async () => {
    if (!canSave) return
    setSaving(true)
    setError('')
    try {
      await updateRule(rule.id, {
        entity_id: entityId || null,
        memo_pattern: memoPattern.trim() || null,
        match_type: matchType,
        category_id: setsTransfer ? null : (categoryId || null),
        sets_transfer: setsTransfer,
        priority: Number(priority),
      })
      onSaved()
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white border border-brown-600/20 rounded-xl w-full max-w-md shadow-2xl">
        <div className="px-5 py-4 border-b border-brown-600/15">
          <h3 className="font-semibold text-ink">Editar regla de categoría</h3>
          <p className="text-xs text-ink/50 mt-0.5">Fuente cambiará a Manual al guardar</p>
        </div>
        <div className="px-5 py-4">
          <RuleFields {...{ entityId, setEntityId, memoPattern, setMemoPattern, matchType, setMatchType,
            categoryId, setCategoryId, setsTransfer, setSetsTransfer, priority, setPriority, categories, entities }} />
          {error && (
            <p className="text-red-500 text-xs bg-red-50 border border-red-200 rounded px-3 py-2 mt-3">{error}</p>
          )}
        </div>
        <div className="px-5 py-4 border-t border-brown-600/15 flex gap-2 justify-end">
          <button onClick={onClose} className="btn-ghost text-sm">Cancelar</button>
          <button onClick={handleSave} disabled={!canSave || saving} className="btn-primary text-sm">
            {saving ? 'Guardando…' : 'Guardar cambios'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Transaction list tab ──────────────────────────────────────────────────────

function TransactionListTab() {
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

      {data && <p className="text-xs text-ink/40">{data.total} resultado{data.total !== 1 ? 's' : ''}</p>}

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
          <input type="checkbox" checked={needsReview}
            onChange={(e) => { setNeedsReview(e.target.checked); resetPage() }}
            className="accent-amber-500 w-4 h-4" />
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
                <tr key={txn.id} className={`table-row ${txn.is_transfer ? 'opacity-50' : txn.needs_review ? 'bg-amber-500/5' : ''}`}>
                  <td className="table-cell whitespace-nowrap text-ink/50 text-xs">
                    {new Date(txn.date + 'T12:00:00').toLocaleDateString('es-CR')}
                  </td>
                  <td className="table-cell max-w-xs">
                    <p className="truncate text-ink/90">{txn.description_raw}</p>
                    <div className="flex gap-1 mt-0.5 flex-wrap">
                      {txn.is_transfer && <span className="badge bg-blue-100 text-blue-600 text-[10px]">⇌ Transferencia</span>}
                      {txn.needs_review && !txn.is_transfer && <span className="badge bg-amber-500/20 text-amber-500 text-[10px]">Revisar</span>}
                    </div>
                  </td>
                  <td className="table-cell text-right">
                    <CurrencyAmount amount={txn.amount} currency={txn.currency} direction={txn.direction} />
                  </td>
                  <td className="table-cell"><CurrencyBadge currency={txn.currency} /></td>
                  <td className="table-cell">
                    {txn.is_transfer ? (
                      <span className="text-xs text-ink/30 italic">excluida</span>
                    ) : (
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
                    )}
                  </td>
                  <td className="table-cell">
                    <div className="flex gap-2">
                      <button onClick={() => setModalTxn(txn)} title="Clasificar"
                        className="text-xs text-ink/20 hover:text-amber-500">✎</button>
                      {!txn.is_transfer && (
                        <button
                          onClick={() => toggleReview(txn)}
                          title={txn.needs_review ? 'Marcar revisado' : 'Marcar para revisar'}
                          className={`text-xs ${txn.needs_review ? 'text-amber-500' : 'text-ink/20 hover:text-ink/50'}`}
                        >⚑</button>
                      )}
                    </div>
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

// ── Review tab (transactions needing attention) ───────────────────────────────

function ReviewTab() {
  const [page, setPage] = useState(1)
  const [expanded, setExpanded] = useState(null)
  const [entitySearch, setEntitySearch] = useState('')
  const [edits, setEdits] = useState({})
  const [suggesting, setSuggesting] = useState(false)
  const [suggestResult, setSuggestResult] = useState(null)
  const [suggestingEntities, setSuggestingEntities] = useState(false)
  const [suggestEntitiesResult, setSuggestEntitiesResult] = useState(null)
  const qc = useQueryClient()

  const { data: txns, isLoading } = useQuery({
    queryKey: ['transactions-review', page],
    queryFn: () => listTransactions({ needs_review: true, page, page_size: REVIEW_PAGE_SIZE }),
  })
  const { data: categories } = useQuery({ queryKey: ['categories'], queryFn: listCategories })
  const { data: allEntities } = useQuery({
    queryKey: ['entities-all-review'],
    queryFn: () => listEntities({ page_size: 200 }),
  })

  const catMap = Object.fromEntries((categories || []).map((c) => [c.id, c]))
  const entityList = allEntities?.items || []
  const filteredEntities = entitySearch
    ? entityList.filter((e) =>
        (e.display_name || e.canonical_name).toLowerCase().includes(entitySearch.toLowerCase())
      )
    : entityList

  const setEdit = (id, field, value) =>
    setEdits((prev) => ({ ...prev, [id]: { ...prev[id], [field]: value } }))

  const toggle = (id) => {
    setExpanded((prev) => (prev === id ? null : id))
    setEntitySearch('')
  }

  const save = async (txn) => {
    const edit = edits[txn.id] || {}
    const patch = { needs_review: false }
    const catId = 'category_id' in edit ? edit.category_id : txn.category_id
    patch.category_id = catId || null
    if ('merchant_entity_id' in edit) patch.merchant_entity_id = edit.merchant_entity_id || null
    await updateTransaction(txn.id, patch)
    setEdits((prev) => { const n = { ...prev }; delete n[txn.id]; return n })
    setExpanded(null)
    qc.invalidateQueries({ queryKey: ['transactions-review'] })
  }

  const dismiss = async (txn) => {
    await updateTransaction(txn.id, { needs_review: false })
    setExpanded(null)
    qc.invalidateQueries({ queryKey: ['transactions-review'] })
  }

  const handleSuggestAI = async () => {
    setSuggesting(true)
    setSuggestResult(null)
    try {
      const result = await suggestCategoriesAI()
      setSuggestResult(result)
      qc.invalidateQueries({ queryKey: ['transactions-review'] })
    } finally {
      setSuggesting(false)
    }
  }

  const handleSuggestEntities = async () => {
    setSuggestingEntities(true)
    setSuggestEntitiesResult(null)
    try {
      const result = await suggestEntitiesAI()
      setSuggestEntitiesResult(result)
      qc.invalidateQueries({ queryKey: ['transactions-review'] })
    } finally {
      setSuggestingEntities(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="space-y-0.5">
          {suggestResult && (
            <p className="text-sm text-violet-600">✦ {suggestResult.suggested} categorías sugeridas de {suggestResult.checked} sin categoría</p>
          )}
          {suggestEntitiesResult && (
            <p className="text-sm text-blue-600">◈ {suggestEntitiesResult.suggested} entidades asignadas de {suggestEntitiesResult.checked} sin entidad</p>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSuggestEntities}
            disabled={suggestingEntities}
            className="btn-ghost text-sm border border-blue-300 text-blue-600 hover:bg-blue-50 disabled:opacity-50"
          >
            {suggestingEntities ? 'Consultando IA…' : '◈ Sugerir entidades'}
          </button>
          <button
            onClick={handleSuggestAI}
            disabled={suggesting}
            className="btn-ghost text-sm border border-violet-300 text-violet-600 hover:bg-violet-50 disabled:opacity-50"
          >
            {suggesting ? 'Consultando IA…' : '✦ Sugerir categorías'}
          </button>
        </div>
      </div>

      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead className="border-b border-brown-600/20">
            <tr>
              <th className="table-header">Fecha</th>
              <th className="table-header">Descripción</th>
              <th className="table-header">Entidad</th>
              <th className="table-header text-right">Monto</th>
              <th className="table-header">Categoría</th>
              <th className="table-header w-6"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={6} className="table-cell text-center text-ink/40 py-12">Cargando…</td></tr>}
            {!isLoading && !txns?.items?.length && (
              <tr><td colSpan={6} className="table-cell text-center text-ink/40 py-12">
                <p className="text-4xl mb-2">✓</p>Sin transacciones pendientes de revisión.
              </td></tr>
            )}
            {txns?.items?.map((txn) => {
              const isOpen = expanded === txn.id
              const edit = edits[txn.id] || {}
              const currentCatId = 'category_id' in edit ? edit.category_id : txn.category_id
              const currentEntityId = 'merchant_entity_id' in edit ? edit.merchant_entity_id : txn.merchant_entity_id
              const entityLabel = entityList.find((e) => e.id === txn.merchant_entity_id)
              return (
                <Fragment key={txn.id}>
                  <tr className={`table-row cursor-pointer ${isOpen ? 'bg-amber-500/5' : ''}`}
                    onClick={() => toggle(txn.id)}>
                    <td className="table-cell text-xs text-ink/50 whitespace-nowrap">
                      {new Date(txn.date + 'T12:00:00').toLocaleDateString('es-CR')}
                    </td>
                    <td className="table-cell max-w-xs">
                      <p className="truncate text-sm">{txn.description_raw}</p>
                    </td>
                    <td className="table-cell text-xs">
                      {entityLabel
                        ? <span className="text-ink/70">{entityLabel.display_name || entityLabel.canonical_name}</span>
                        : <span className="text-amber-500">Sin entidad</span>}
                    </td>
                    <td className="table-cell text-right">
                      <CurrencyAmount amount={txn.amount} currency={txn.currency} direction={txn.direction} />
                    </td>
                    <td className="table-cell text-xs">
                      {txn.category_id ? (
                        <span className="flex items-center gap-1.5">
                          <span className="text-ink/70">{catMap[txn.category_id]?.name}</span>
                          {txn.category_source === 'ai_suggested' && (
                            <span className="badge bg-violet-100 text-violet-600 text-[9px] py-0 leading-4">IA</span>
                          )}
                        </span>
                      ) : (
                        <span className="text-amber-500">Sin categoría</span>
                      )}
                    </td>
                    <td className="table-cell text-ink/30 text-xs text-center">{isOpen ? '▲' : '▼'}</td>
                  </tr>

                  {isOpen && (
                    <tr>
                      <td colSpan={6} className="bg-[#F5EFE0]/70 px-4 py-3 border-b border-brown-600/10">
                        <div className="flex flex-wrap gap-4 items-end">
                          <div className="flex-1 min-w-44">
                            <label className="block text-xs font-medium text-ink/60 mb-1">Categoría</label>
                            <select className="select text-sm" value={currentCatId || ''}
                              onChange={(e) => setEdit(txn.id, 'category_id', e.target.value || null)}
                              onClick={(e) => e.stopPropagation()}>
                              <option value="">— Sin categoría —</option>
                              {(categories || []).map((c) => (
                                <option key={c.id} value={c.id}>{c.name}</option>
                              ))}
                            </select>
                          </div>

                          <div className="flex-1 min-w-52">
                            <label className="block text-xs font-medium text-ink/60 mb-1">Entidad</label>
                            <input type="text" className="input text-sm mb-1" placeholder="Buscar entidad…"
                              value={entitySearch} onChange={(e) => setEntitySearch(e.target.value)}
                              onClick={(e) => e.stopPropagation()} autoFocus />
                            <select className="select text-sm" value={currentEntityId || ''}
                              onChange={(e) => setEdit(txn.id, 'merchant_entity_id', e.target.value || null)}
                              onClick={(e) => e.stopPropagation()}
                              size={Math.min(filteredEntities.length + 1, 5)}>
                              <option value="">— Sin entidad —</option>
                              {filteredEntities.map((e) => (
                                <option key={e.id} value={e.id}>{e.display_name || e.canonical_name}</option>
                              ))}
                            </select>
                          </div>

                          <div className="flex flex-col gap-1.5 shrink-0 pb-0.5">
                            {txn.category_source === 'ai_suggested' && !('category_id' in (edits[txn.id] || {})) && (
                              <p className="text-[10px] text-violet-500 font-medium">
                                ✦ Sugerencia de IA · confirma o cambia abajo
                              </p>
                            )}
                            <div className="flex gap-2">
                              <button onClick={(e) => { e.stopPropagation(); save(txn) }}
                                className="btn-primary text-xs py-1.5 px-4">
                                {txn.category_source === 'ai_suggested' && !('category_id' in (edits[txn.id] || {}))
                                  ? '✓ Confirmar'
                                  : 'Guardar y cerrar'}
                              </button>
                              <button onClick={(e) => { e.stopPropagation(); dismiss(txn) }}
                                className="btn-ghost text-xs py-1.5 px-3 border border-brown-600/30">
                                Solo cerrar
                              </button>
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
        {txns && <Pagination page={page} pageSize={REVIEW_PAGE_SIZE} total={txns.total} onPage={setPage} />}
      </div>
    </div>
  )
}

// ── Category rules tab ────────────────────────────────────────────────────────

function CategoryRulesTab({ isAdmin }) {
  const [showNew, setShowNew] = useState(false)
  const [editRule, setEditRule] = useState(null)
  const [reapplying, setReapplying] = useState(false)
  const [reapplyResult, setReapplyResult] = useState(null)
  const qc = useQueryClient()

  const { data: rules } = useQuery({ queryKey: ['rules'], queryFn: listRules })
  const { data: categories } = useQuery({ queryKey: ['categories'], queryFn: listCategories })
  const { data: entities } = useQuery({
    queryKey: ['entities-all'],
    queryFn: () => listEntities({ page_size: 200 }),
  })

  const entityMap = Object.fromEntries((entities?.items ?? []).map((e) => [e.id, e]))
  const catMap = Object.fromEntries((categories ?? []).map((c) => [c.id, c]))

  const handleDeleteRule = async (id) => {
    await deleteRule(id)
    qc.invalidateQueries({ queryKey: ['rules'] })
  }

  const handleReapply = async () => {
    setReapplying(true)
    setReapplyResult(null)
    try {
      const result = await reapplyRules()
      setReapplyResult(result)
      qc.invalidateQueries({ queryKey: ['transactions'] })
      qc.invalidateQueries({ queryKey: ['transactions-review'] })
    } finally {
      setReapplying(false)
    }
  }

  const onSaved = () => {
    qc.invalidateQueries({ queryKey: ['rules'] })
    setShowNew(false)
    setEditRule(null)
  }

  return (
    <div className="space-y-4">
      {showNew && (
        <NewRuleModal categories={categories} entities={entities}
          onClose={() => setShowNew(false)} onSaved={onSaved} />
      )}
      {editRule && (
        <EditRuleModal rule={editRule} categories={categories} entities={entities}
          onClose={() => setEditRule(null)} onSaved={onSaved} />
      )}

      <div className="flex items-center justify-between gap-3">
        <div>
          {reapplyResult && (
            <p className="text-sm text-green-700">
              ✓ {reapplyResult.applied} categorizada{reapplyResult.applied !== 1 ? 's' : ''} de {reapplyResult.checked} revisadas
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <button onClick={handleReapply} disabled={reapplying}
            className="btn-ghost text-sm border border-brown-600/30 disabled:opacity-50">
            {reapplying ? 'Aplicando…' : '↻ Re-aplicar reglas'}
          </button>
          {isAdmin && (
            <button onClick={() => setShowNew(true)} className="btn-primary text-sm">
              + Nueva regla
            </button>
          )}
        </div>
      </div>

      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead className="border-b border-brown-600/20">
            <tr>
              <th className="table-header">Condición</th>
              <th className="table-header">Resultado</th>
              <th className="table-header w-20 text-center">Prioridad</th>
              <th className="table-header w-20">Fuente</th>
              {isAdmin && <th className="table-header w-16"></th>}
            </tr>
          </thead>
          <tbody>
            {!rules?.length && (
              <tr>
                <td colSpan={isAdmin ? 5 : 4} className="table-cell text-center text-ink/40 py-12">
                  <p className="text-3xl mb-2">⊞</p>
                  Sin reglas definidas. Las reglas creadas en transacciones aparecen aquí.
                </td>
              </tr>
            )}
            {rules?.map((rule) => {
              const entity = rule.entity_id ? entityMap[rule.entity_id] : null
              const cat = catMap[rule.category_id]
              return (
                <tr key={rule.id}
                  className={`table-row ${isAdmin ? 'cursor-pointer' : ''}`}
                  onClick={isAdmin ? () => setEditRule(rule) : undefined}>
                  <td className="table-cell">
                    <div className="flex flex-wrap items-center gap-1.5">
                      {entity && (
                        <span className="badge bg-brown-600/15 text-brown-900">
                          {entity.display_name || entity.canonical_name}
                        </span>
                      )}
                      {rule.memo_pattern && (
                        <span className="text-xs text-ink/60">
                          {matchTypeLabelFull[rule.match_type]?.toLowerCase()}{' '}
                          <code className="bg-[#F5EFE0] px-1.5 py-0.5 rounded text-ink/80 font-mono">
                            {rule.memo_pattern}
                          </code>
                        </span>
                      )}
                      {!entity && !rule.memo_pattern && (
                        <span className="text-xs text-ink/30">—</span>
                      )}
                    </div>
                  </td>
                  <td className="table-cell">
                    {rule.sets_transfer ? (
                      <span className="badge bg-blue-100 text-blue-600 text-[10px]">⇌ Transferencia interna</span>
                    ) : cat ? (
                      <span className="badge" style={{
                        background: (cat.color ?? '#C99828') + '25',
                        color: cat.color ?? '#C99828',
                        border: `1px solid ${cat.color ?? '#C99828'}40`,
                      }}>
                        {cat.icon && <span className="mr-1">{cat.icon}</span>}
                        {cat.name}
                      </span>
                    ) : (
                      <span className="text-xs text-ink/30">—</span>
                    )}
                  </td>
                  <td className="table-cell text-center text-ink/60 tabular-nums">{rule.priority}</td>
                  <td className="table-cell">
                    <span className={`badge text-[10px] ${
                      rule.source === 'user_confirmed'
                        ? 'bg-green-800/20 text-green-700'
                        : 'bg-amber-500/20 text-amber-500'
                    }`}>
                      {sourceLabel[rule.source] ?? rule.source}
                    </span>
                  </td>
                  {isAdmin && (
                    <td className="table-cell" onClick={(e) => e.stopPropagation()}>
                      <div className="flex gap-2 justify-end">
                        <button onClick={() => setEditRule(rule)}
                          className="text-ink/30 hover:text-amber-500 transition-colors text-xs" title="Editar">✎</button>
                        <button onClick={() => handleDeleteRule(rule.id)}
                          className="text-red-400/60 hover:text-red-500 transition-colors text-xs" title="Eliminar">✕</button>
                      </div>
                    </td>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {rules?.length > 0 && (
        <p className="text-xs text-ink/40 px-1">
          Las reglas se aplican en orden de prioridad (mayor número = mayor prioridad).
          Una regla más específica (entidad + memo) siempre gana sobre una más general.
        </p>
      )}
    </div>
  )
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function Transactions() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = searchParams.get('tab') || 'transacciones'
  const setTab = (id) => setSearchParams({ tab: id })

  const { data: rules } = useQuery({ queryKey: ['rules'], queryFn: listRules })
  const { data: reviewCount } = useQuery({
    queryKey: ['transactions-review-count'],
    queryFn: () => listTransactions({ needs_review: true, page: 1, page_size: 1 }),
    refetchInterval: 60_000,
    staleTime: 30_000,
  })

  const TABS = [
    { id: 'transacciones', label: 'Transacciones' },
    { id: 'revision', label: `Por revisar${reviewCount?.total ? ` (${reviewCount.total})` : ''}` },
    { id: 'reglas', label: `Reglas${rules ? ` (${rules.length})` : ''}` },
  ]

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-ink">Transacciones</h1>
        <p className="text-sm text-ink/50 mt-0.5">Movimientos, revisión e reglas de categoría</p>
      </div>

      <div className="flex gap-1 border-b border-brown-600/20">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === t.id
                ? 'text-amber-500 border-amber-500'
                : 'text-ink/50 border-transparent hover:text-ink'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'transacciones' && <TransactionListTab />}
      {activeTab === 'revision' && <ReviewTab />}
      {activeTab === 'reglas' && <CategoryRulesTab isAdmin={isAdmin} />}
    </div>
  )
}
