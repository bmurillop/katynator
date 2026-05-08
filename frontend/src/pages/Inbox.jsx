import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { listUnresolved, resolveToExisting, createEntityFromUnresolved, ignoreUnresolved } from '../api/unresolvedEntities'
import { listTransactions, updateTransaction } from '../api/transactions'
import { listEmails, retryEmail, triggerPoll } from '../api/emails'
import { listEntities } from '../api/entities'
import { listCategories } from '../api/categories'
import CurrencyAmount, { CurrencyBadge } from '../components/CurrencyAmount'
import Pagination from '../components/Pagination'

const PAGE_SIZE = 20

// ── Unresolved entities tab ──────────────────────────────────────────────────

function EntityResolutionCard({ item, onDone }) {
  const [mode, setMode] = useState(null) // null | 'link' | 'create'
  const [entityId, setEntityId] = useState('')
  const [newName, setNewName] = useState(item.raw_name)
  const [newType, setNewType] = useState('merchant')
  const [saving, setSaving] = useState(false)
  const { data: entities } = useQuery({
    queryKey: ['entities-search', item.normalized],
    queryFn: () => listEntities({ search: item.raw_name.split(' ')[0], page_size: 20 }),
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
          <select className="select text-sm" value={entityId} onChange={(e) => setEntityId(e.target.value)}>
            <option value="">— Seleccionar entidad —</option>
            {entities?.items?.map((e) => (
              <option key={e.id} value={e.id}>{e.canonical_name}</option>
            ))}
          </select>
          <div className="flex gap-2">
            <button onClick={handleLink} disabled={!entityId || saving} className="btn-primary text-xs">
              {saving ? '…' : 'Vincular'}
            </button>
            <button onClick={() => setMode(null)} className="btn-ghost text-xs">Cancelar</button>
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
  const qc = useQueryClient()
  const { data: txns, isLoading } = useQuery({
    queryKey: ['transactions-review', page],
    queryFn: () => listTransactions({ needs_review: true, page, page_size: PAGE_SIZE }),
  })
  const { data: categories } = useQuery({ queryKey: ['categories'], queryFn: listCategories })
  const catMap = Object.fromEntries((categories || []).map((c) => [c.id, c]))

  const dismiss = async (id) => {
    await updateTransaction(id, { needs_review: false })
    qc.invalidateQueries({ queryKey: ['transactions-review'] })
  }

  return (
    <div className="card p-0 overflow-hidden">
      <table className="w-full">
        <thead className="border-b border-brown-600/20">
          <tr>
            <th className="table-header">Fecha</th>
            <th className="table-header">Descripción</th>
            <th className="table-header text-right">Monto</th>
            <th className="table-header">Moneda</th>
            <th className="table-header">Categoría</th>
            <th className="table-header"></th>
          </tr>
        </thead>
        <tbody>
          {isLoading && <tr><td colSpan={6} className="table-cell text-center text-ink/40 py-12">Cargando…</td></tr>}
          {!isLoading && !txns?.items?.length && (
            <tr><td colSpan={6} className="table-cell text-center text-ink/40 py-12">
              <p className="text-4xl mb-2">✓</p>Sin transacciones pendientes de revisión.
            </td></tr>
          )}
          {txns?.items?.map((txn) => (
            <tr key={txn.id} className="table-row">
              <td className="table-cell text-xs text-ink/50 whitespace-nowrap">
                {new Date(txn.date + 'T12:00:00').toLocaleDateString('es-CR')}
              </td>
              <td className="table-cell max-w-xs"><p className="truncate">{txn.description_raw}</p></td>
              <td className="table-cell text-right">
                <CurrencyAmount amount={txn.amount} currency={txn.currency} direction={txn.direction} />
              </td>
              <td className="table-cell"><CurrencyBadge currency={txn.currency} /></td>
              <td className="table-cell text-ink/50 text-xs">
                {txn.category_id ? catMap[txn.category_id]?.name : <span className="text-amber-500">Sin categoría</span>}
              </td>
              <td className="table-cell">
                <button onClick={() => dismiss(txn.id)} className="text-xs text-ink/30 hover:text-green-600">✓</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {txns && <Pagination page={page} pageSize={PAGE_SIZE} total={txns.total} onPage={setPage} />}
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
