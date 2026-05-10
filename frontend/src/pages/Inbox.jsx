import { useState, Fragment } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { listUnresolved, resolveToExisting, createEntityFromUnresolved, ignoreUnresolved } from '../api/unresolvedEntities'
import { listTransactions, updateTransaction, suggestCategoriesAI, suggestEntitiesAI } from '../api/transactions'
import { listEmails, retryEmail, triggerPoll } from '../api/emails'
import { listEntities } from '../api/entities'
import { listCategories } from '../api/categories'
import CurrencyAmount from '../components/CurrencyAmount'
import Pagination from '../components/Pagination'

const PAGE_SIZE = 20

// ── Unresolved entities tab ──────────────────────────────────────────────────

function EntityResolutionCard({ item, onDone }) {
  const [mode, setMode] = useState(null) // null | 'link' | 'create'
  const [search, setSearch] = useState('')
  const [entityId, setEntityId] = useState('')
  const [newName, setNewName] = useState(item.raw_name)
  const [newType, setNewType] = useState('merchant')
  const [saving, setSaving] = useState(false)
  const { data: entities, isFetching } = useQuery({
    queryKey: ['entities-search', search],
    queryFn: () => listEntities({ search: search || undefined, page_size: 30 }),
    enabled: mode === 'link',
  })

  const handleLink = async () => {
    if (!entityId) return
    setSaving(true)
    try { await resolveToExisting(item.id, entityId); onDone() } finally { setSaving(false) }
  }

  const handleCreate = async () => {
    if (!newName.trim()) return
    setSaving(true)
    try { await createEntityFromUnresolved(item.id, { canonical_name: newName, type: newType }); onDone() } finally { setSaving(false) }
  }

  const handleIgnore = async () => {
    setSaving(true)
    try { await ignoreUnresolved(item.id); onDone() } finally { setSaving(false) }
  }

  return (
    <div className="card space-y-3">
      <div>
        <p className="text-sm font-mono text-ink">{item.raw_name}</p>
        <p className="text-xs text-ink/40 mt-0.5">Normalizado: {item.normalized}</p>
        {item.suggestion_confidence != null && (
          <p className="text-xs text-amber-500 mt-0.5">
            Sugerencia: {(item.suggestion_confidence * 100).toFixed(0)}% de similitud
          </p>
        )}
      </div>

      {!mode && (
        <div className="flex flex-wrap gap-2">
          <button onClick={() => setMode('link')} className="btn-primary text-xs py-1.5 px-3">
            ✓ Vincular a entidad existente
          </button>
          <button onClick={() => setMode('create')} className="btn-ghost text-xs border border-brown-600/30 py-1.5 px-3">
            + Crear nueva entidad
          </button>
          <button onClick={handleIgnore} disabled={saving} className="btn-ghost text-xs text-ink/40 py-1.5 px-3">
            ✕ Ignorar
          </button>
        </div>
      )}

      {mode === 'link' && (
        <div className="space-y-2">
          <input
            type="text"
            className="input text-sm"
            placeholder="Buscar entidad…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setEntityId('') }}
            autoFocus
          />
          <select
            className="select text-sm"
            value={entityId}
            onChange={(e) => setEntityId(e.target.value)}
            size={Math.min((entities?.items?.length || 0) + 1, 6)}
          >
            <option value="">
              {isFetching ? 'Buscando…' : entities?.items?.length ? '— Seleccionar —' : '— Sin resultados —'}
            </option>
            {entities?.items?.map((e) => (
              <option key={e.id} value={e.id}>{e.canonical_name}</option>
            ))}
          </select>
          <div className="flex gap-2">
            <button onClick={handleLink} disabled={!entityId || saving} className="btn-primary text-xs">
              {saving ? '…' : 'Vincular'}
            </button>
            <button onClick={() => { setMode(null); setSearch('') }} className="btn-ghost text-xs">Cancelar</button>
          </div>
        </div>
      )}

      {mode === 'create' && (
        <div className="space-y-2">
          <input type="text" className="input text-sm" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Nombre canónico" />
          <select className="select text-sm" value={newType} onChange={(e) => setNewType(e.target.value)}>
            <option value="bank">Banco</option>
            <option value="merchant">Comercio</option>
            <option value="person">Persona</option>
            <option value="issuer">Emisor</option>
            <option value="income_source">Fuente de ingreso</option>
            <option value="other">Otro</option>
          </select>
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={!newName.trim() || saving} className="btn-primary text-xs">
              {saving ? '…' : 'Crear entidad'}
            </button>
            <button onClick={() => setMode(null)} className="btn-ghost text-xs">Cancelar</button>
          </div>
        </div>
      )}
    </div>
  )
}


function UnresolvedTab() {
  const [page, setPage] = useState(1)
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['unresolved', 'pending', page],
    queryFn: () => listUnresolved({ status: 'pending', page, page_size: PAGE_SIZE }),
  })

  const refresh = () => qc.invalidateQueries({ queryKey: ['unresolved'] })

  return (
    <div className="space-y-3">
      {isLoading && <p className="text-ink/40 text-sm">Cargando…</p>}
      {!isLoading && !data?.items?.length && (
        <div className="card text-center py-12 text-ink/40">
          <p className="text-4xl mb-3">✓</p>
          <p>Sin nombres pendientes de resolver.</p>
        </div>
      )}
      {data?.items?.map((item) => (
        <EntityResolutionCard key={item.id} item={item} onDone={refresh} />
      ))}
      {data && <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onPage={setPage} />}
    </div>
  )
}

// ── Transactions needs_review tab ────────────────────────────────────────────

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
    queryFn: () => listTransactions({ needs_review: true, page, page_size: PAGE_SIZE }),
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
    // Always send category_id so the backend upgrades ai_suggested → user_set
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
                <tr
                  className={`table-row cursor-pointer ${isOpen ? 'bg-amber-500/5' : ''}`}
                  onClick={() => toggle(txn.id)}
                >
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
                        {/* Category */}
                        <div className="flex-1 min-w-44">
                          <label className="block text-xs font-medium text-ink/60 mb-1">Categoría</label>
                          <select
                            className="select text-sm"
                            value={currentCatId || ''}
                            onChange={(e) => setEdit(txn.id, 'category_id', e.target.value || null)}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <option value="">— Sin categoría —</option>
                            {(categories || []).map((c) => (
                              <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                          </select>
                        </div>

                        {/* Entity */}
                        <div className="flex-1 min-w-52">
                          <label className="block text-xs font-medium text-ink/60 mb-1">Entidad</label>
                          <input
                            type="text"
                            className="input text-sm mb-1"
                            placeholder="Buscar entidad…"
                            value={entitySearch}
                            onChange={(e) => setEntitySearch(e.target.value)}
                            onClick={(e) => e.stopPropagation()}
                            autoFocus
                          />
                          <select
                            className="select text-sm"
                            value={currentEntityId || ''}
                            onChange={(e) => setEdit(txn.id, 'merchant_entity_id', e.target.value || null)}
                            onClick={(e) => e.stopPropagation()}
                            size={Math.min(filteredEntities.length + 1, 5)}
                          >
                            <option value="">— Sin entidad —</option>
                            {filteredEntities.map((e) => (
                              <option key={e.id} value={e.id}>{e.display_name || e.canonical_name}</option>
                            ))}
                          </select>
                        </div>

                        {/* Actions */}
                        <div className="flex flex-col gap-1.5 shrink-0 pb-0.5">
                          {txn.category_source === 'ai_suggested' && !('category_id' in (edits[txn.id] || {})) && (
                            <p className="text-[10px] text-violet-500 font-medium">
                              ✦ Sugerencia de IA · confirma o cambia abajo
                            </p>
                          )}
                          <div className="flex gap-2">
                            <button
                              onClick={(e) => { e.stopPropagation(); save(txn) }}
                              className="btn-primary text-xs py-1.5 px-4"
                            >
                              {txn.category_source === 'ai_suggested' && !('category_id' in (edits[txn.id] || {}))
                                ? '✓ Confirmar'
                                : 'Guardar y cerrar'}
                            </button>
                            <button
                              onClick={(e) => { e.stopPropagation(); dismiss(txn) }}
                              className="btn-ghost text-xs py-1.5 px-3 border border-brown-600/30"
                            >
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
      {txns && <Pagination page={page} pageSize={PAGE_SIZE} total={txns.total} onPage={setPage} />}
    </div>
    </div>
  )
}

// ── Failed emails tab ────────────────────────────────────────────────────────

function EmailsTab() {
  const [page, setPage] = useState(1)
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['emails-failed', page],
    queryFn: () => listEmails({ status: 'failed', page, page_size: PAGE_SIZE }),
  })

  const retry = async (id) => {
    await retryEmail(id)
    qc.invalidateQueries({ queryKey: ['emails-failed'] })
  }

  const poll = async () => {
    await triggerPoll()
    qc.invalidateQueries({ queryKey: ['emails-failed'] })
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button onClick={poll} className="btn-ghost text-sm border border-brown-600/30">
          ↻ Sondear IMAP ahora
        </button>
      </div>

      {isLoading && <p className="text-ink/40 text-sm">Cargando…</p>}
      {!isLoading && !data?.items?.length && (
        <div className="card text-center py-12 text-ink/40">
          <p className="text-4xl mb-3">✉</p>
          <p>Sin correos fallidos.</p>
        </div>
      )}

      <div className="space-y-3">
        {data?.items?.map((email) => (
          <div key={email.id} className="card border-red-300/50 space-y-2">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-ink">{email.subject || '(sin asunto)'}</p>
                <p className="text-xs text-ink/40">{email.sender} · {new Date(email.received_at).toLocaleDateString('es-CR')}</p>
              </div>
              <button onClick={() => retry(email.id)} className="btn-primary text-xs py-1.5 px-3 shrink-0">
                Reintentar
              </button>
            </div>
            {email.error_message && (
              <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2 font-mono break-all">
                {email.error_message}
              </p>
            )}
          </div>
        ))}
      </div>
      {data && <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onPage={setPage} />}
    </div>
  )
}

// ── Main Inbox ───────────────────────────────────────────────────────────────

const TABS = [
  { id: 'entidades', label: 'Entidades sin resolver' },
  { id: 'revision', label: 'Transacciones por revisar' },
  { id: 'correos', label: 'Correos fallidos' },
]

export default function Inbox() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = searchParams.get('tab') || 'entidades'

  const setTab = (id) => setSearchParams({ tab: id })

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-ink">Bandeja de entrada</h1>
        <p className="text-sm text-ink/50 mt-0.5">Elementos que requieren atención</p>
      </div>

      <div className="flex gap-1 border-b border-brown-600/20">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setTab(tab.id)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.id
                ? 'text-amber-500 border-amber-500'
                : 'text-ink/50 border-transparent hover:text-ink'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div>
        {activeTab === 'entidades' && <UnresolvedTab />}
        {activeTab === 'revision' && <ReviewTab />}
        {activeTab === 'correos' && <EmailsTab />}
      </div>
    </div>
  )
}
