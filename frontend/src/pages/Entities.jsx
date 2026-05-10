import { useState, useDeferredValue } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { listEntities, getEntity, updateEntity, addPattern, deletePattern } from '../api/entities'
import { listEntityRules, createEntityRule, updateEntityRule, deleteEntityRule, previewEntityRule, applyEntityRule, reapplyEntityRules } from '../api/entityRules'
import { listUnresolved, resolveToExisting, createEntityFromUnresolved, ignoreUnresolved } from '../api/unresolvedEntities'
import { suggestEntitiesAI } from '../api/transactions'
import Pagination from '../components/Pagination'

const typeLabel = {
  bank: 'Banco',
  merchant: 'Comercio',
  issuer: 'Emisor',
  person: 'Persona',
  income_source: 'Fuente de ingreso',
  other: 'Otro',
}

const matchTypeLabel = { contains: 'Contiene', starts_with: 'Empieza con', exact: 'Exacto', regex: 'Regex' }

const PAGE_SIZE = 20

// ── Entity detail modal ──────────────────────────────────────────────────────

function EntityDetail({ entityId, onClose }) {
  const qc = useQueryClient()
  const { data: entity, isLoading } = useQuery({
    queryKey: ['entity', entityId],
    queryFn: () => getEntity(entityId),
  })

  const [editing, setEditing] = useState(false)
  const [editName, setEditName] = useState('')
  const [editDisplay, setEditDisplay] = useState('')
  const [editType, setEditType] = useState('')
  const [saving, setSaving] = useState(false)

  const openEdit = () => {
    setEditName(entity.canonical_name)
    setEditDisplay(entity.display_name || '')
    setEditType(entity.type)
    setEditing(true)
  }

  const saveEdit = async () => {
    setSaving(true)
    try {
      await updateEntity(entityId, {
        canonical_name: editName.trim(),
        display_name: editDisplay.trim() || null,
        type: editType,
      })
      qc.invalidateQueries({ queryKey: ['entity', entityId] })
      qc.invalidateQueries({ queryKey: ['entities'] })
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  const [newPattern, setNewPattern] = useState('')
  const [adding, setAdding] = useState(false)

  const handleAddPattern = async () => {
    if (!newPattern.trim()) return
    setAdding(true)
    try {
      await addPattern(entityId, { pattern: newPattern.trim() })
      setNewPattern('')
      qc.invalidateQueries({ queryKey: ['entity', entityId] })
    } finally {
      setAdding(false)
    }
  }

  const handleDeletePattern = async (patternId) => {
    await deletePattern(entityId, patternId)
    qc.invalidateQueries({ queryKey: ['entity', entityId] })
  }

  const handleConfirm = async () => {
    await updateEntity(entityId, { confirmed: !entity.confirmed })
    qc.invalidateQueries({ queryKey: ['entity', entityId] })
    qc.invalidateQueries({ queryKey: ['entities'] })
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white border border-brown-600/20 rounded-xl w-full max-w-lg shadow-2xl max-h-[85vh] flex flex-col">
        <div className="px-5 py-4 border-b border-brown-600/15 flex items-center justify-between">
          <h3 className="font-semibold text-ink">{isLoading ? '…' : entity?.canonical_name}</h3>
          <button onClick={onClose} className="text-ink/40 hover:text-ink">✕</button>
        </div>

        {entity && (
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
            {editing ? (
              <div className="space-y-3 bg-[#F5EFE0] rounded-xl p-4">
                <div>
                  <label className="block text-xs font-medium text-ink/60 mb-1">Nombre canónico</label>
                  <input type="text" className="input text-sm" value={editName} onChange={(e) => setEditName(e.target.value)} autoFocus />
                </div>
                <div>
                  <label className="block text-xs font-medium text-ink/60 mb-1">Nombre a mostrar (opcional)</label>
                  <input type="text" className="input text-sm" value={editDisplay} onChange={(e) => setEditDisplay(e.target.value)} placeholder="Dejar vacío para usar el nombre canónico" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-ink/60 mb-1">Tipo</label>
                  <select className="select text-sm" value={editType} onChange={(e) => setEditType(e.target.value)}>
                    {Object.entries(typeLabel).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
                <div className="flex gap-2 pt-1">
                  <button onClick={saveEdit} disabled={saving || !editName.trim()} className="btn-primary text-xs py-1.5 px-4">{saving ? '…' : 'Guardar'}</button>
                  <button onClick={() => setEditing(false)} className="btn-ghost text-xs py-1.5 px-4 border border-brown-600/30">Cancelar</button>
                </div>
              </div>
            ) : (
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  {entity.display_name && entity.display_name !== entity.canonical_name && (
                    <p className="text-xs text-ink/40">Canónico: <span className="font-mono">{entity.canonical_name}</span></p>
                  )}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="badge bg-brown-600/15 text-brown-900">{typeLabel[entity.type] ?? entity.type}</span>
                    <span className={`badge ${entity.confirmed ? 'bg-green-800/20 text-green-700' : 'bg-amber-500/20 text-amber-500'}`}>
                      {entity.confirmed ? 'Confirmada' : 'Sin confirmar'}
                    </span>
                  </div>
                </div>
                <div className="flex gap-3 shrink-0 text-xs">
                  <button onClick={openEdit} className="text-ink/30 hover:text-amber-500 transition-colors">✎ Editar</button>
                  <button onClick={handleConfirm} className="text-ink/30 hover:text-ink transition-colors">
                    {entity.confirmed ? 'Desconfirmar' : 'Confirmar'}
                  </button>
                </div>
              </div>
            )}

            <div>
              <h4 className="text-xs font-semibold text-ink/50 uppercase tracking-wide mb-2">
                Patrones ({entity.patterns?.length ?? 0})
              </h4>
              <div className="space-y-1 mb-3">
                {entity.patterns?.map((p) => (
                  <div key={p.id} className="flex items-center justify-between bg-[#F5EFE0] rounded-lg px-3 py-1.5">
                    <span className="text-sm text-ink/80 font-mono">{p.pattern}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-ink/30">{p.source}</span>
                      <button onClick={() => handleDeletePattern(p.id)} className="text-red-400/70 hover:text-red-500 text-xs">✕</button>
                    </div>
                  </div>
                ))}
                {!entity.patterns?.length && <p className="text-xs text-ink/30">Sin patrones registrados</p>}
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  className="input text-sm"
                  placeholder="Agregar patrón exacto…"
                  value={newPattern}
                  onChange={(e) => setNewPattern(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddPattern()}
                />
                <button onClick={handleAddPattern} disabled={adding} className="btn-primary text-sm shrink-0 px-3">
                  {adding ? '…' : 'Agregar'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Entity rule modal (create + edit) ────────────────────────────────────────

function EntityRuleModal({ rule, entities, onClose, onSaved }) {
  const isEdit = !!rule
  const [memoPattern, setMemoPattern] = useState(rule?.memo_pattern ?? '')
  const [matchType, setMatchType] = useState(rule?.match_type ?? 'contains')
  const [entityId, setEntityId] = useState(rule?.entity_id ?? '')
  const [priority, setPriority] = useState(rule?.priority ?? 50)
  const [applyNow, setApplyNow] = useState(!isEdit)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const deferred = useDeferredValue({ memoPattern, matchType })
  const { data: preview } = useQuery({
    queryKey: ['entity-rule-preview', deferred],
    queryFn: () => deferred.memoPattern.trim()
      ? previewEntityRule({ memo_pattern: deferred.memoPattern.trim(), match_type: deferred.matchType })
      : Promise.resolve({ count: 0 }),
    enabled: !!deferred.memoPattern.trim(),
  })

  const canSave = memoPattern.trim() && entityId

  const handleSave = async () => {
    if (!canSave) return
    setSaving(true)
    setError('')
    try {
      const payload = {
        memo_pattern: memoPattern.trim(),
        match_type: matchType,
        entity_id: entityId,
        priority: Number(priority),
        source: 'user_confirmed',
      }
      let saved
      if (isEdit) {
        saved = await updateEntityRule(rule.id, payload)
      } else {
        saved = await createEntityRule(payload)
      }
      if (applyNow && !isEdit) {
        await applyEntityRule(saved.id)
      }
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
          <h3 className="font-semibold text-ink">{isEdit ? 'Editar regla de entidad' : 'Nueva regla de entidad'}</h3>
          <p className="text-xs text-ink/50 mt-0.5">
            {isEdit ? 'Fuente cambiará a Manual al guardar' : 'Si el texto del memo coincide → asignar esa entidad'}
          </p>
        </div>
        <div className="px-5 py-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-ink/50 mb-1">Patrón del memo *</label>
              <input
                type="text"
                className="input font-mono"
                placeholder="perimercado…"
                value={memoPattern}
                onChange={(e) => setMemoPattern(e.target.value)}
                autoFocus
              />
            </div>
            <div>
              <label className="block text-xs text-ink/50 mb-1">Tipo de match</label>
              <select className="select" value={matchType} onChange={(e) => setMatchType(e.target.value)}>
                <option value="starts_with">Empieza con</option>
                <option value="contains">Contiene</option>
                <option value="exact">Exacto</option>
                <option value="regex">Regex</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-ink/50 mb-1">Entidad resultante *</label>
              <select className="select" value={entityId} onChange={(e) => setEntityId(e.target.value)}>
                <option value="">— Seleccionar —</option>
                {(entities?.items ?? []).map((e) => (
                  <option key={e.id} value={e.id}>{e.display_name || e.canonical_name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-ink/50 mb-1">Prioridad (1–100)</label>
              <input
                type="number"
                className="input"
                min={1}
                max={100}
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
              />
            </div>
          </div>

          {memoPattern.trim() && (
            <p className="text-xs text-ink/40">
              {preview ? `${preview.count} transacciones coinciden con este patrón` : 'Calculando…'}
            </p>
          )}

          {!isEdit && (
            <label className="flex items-center gap-2 cursor-pointer pt-1">
              <input
                type="checkbox"
                checked={applyNow}
                onChange={(e) => setApplyNow(e.target.checked)}
                className="accent-amber-500 w-4 h-4"
              />
              <span className="text-sm text-ink/70">Aplicar a transacciones existentes sin entidad</span>
            </label>
          )}

          {error && <p className="text-red-500 text-xs bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}
        </div>
        <div className="px-5 py-4 border-t border-brown-600/15 flex gap-2 justify-end">
          <button onClick={onClose} className="btn-ghost text-sm">Cancelar</button>
          <button onClick={handleSave} disabled={!canSave || saving} className="btn-primary text-sm">
            {saving ? 'Guardando…' : isEdit ? 'Guardar cambios' : 'Crear regla'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Entities list tab ────────────────────────────────────────────────────────

function EntitiesTab({ onSelect }) {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')

  const params = {
    page, page_size: PAGE_SIZE,
    ...(search && { search }),
    ...(typeFilter && { type: typeFilter }),
  }

  const { data, isLoading } = useQuery({
    queryKey: ['entities', params],
    queryFn: () => listEntities(params),
  })

  return (
    <div className="space-y-4">
      <div className="card flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-48">
          <label className="block text-xs text-ink/50 mb-1">Buscar</label>
          <input
            type="text"
            className="input"
            placeholder="Nombre de entidad…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          />
        </div>
        <div>
          <label className="block text-xs text-ink/50 mb-1">Tipo</label>
          <select className="select w-44" value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value); setPage(1) }}>
            <option value="">Todos</option>
            {Object.entries(typeLabel).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
      </div>

      <div className="card p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-brown-600/20">
              <tr>
                <th className="table-header">Nombre</th>
                <th className="table-header">Tipo</th>
                <th className="table-header">Patrones</th>
                <th className="table-header">Estado</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && <tr><td colSpan={4} className="table-cell text-center text-ink/40 py-12">Cargando…</td></tr>}
              {!isLoading && !data?.items?.length && <tr><td colSpan={4} className="table-cell text-center text-ink/40 py-12">Sin entidades</td></tr>}
              {data?.items?.map((e) => (
                <tr key={e.id} className="table-row cursor-pointer" onClick={() => onSelect(e.id)}>
                  <td className="table-cell font-medium text-ink">{e.display_name || e.canonical_name}</td>
                  <td className="table-cell">
                    <span className="badge bg-brown-600/15 text-brown-900">{typeLabel[e.type] ?? e.type}</span>
                  </td>
                  <td className="table-cell text-ink/40">—</td>
                  <td className="table-cell">
                    <span className={`badge ${e.confirmed ? 'bg-green-800/20 text-green-700' : 'bg-amber-500/20 text-amber-500'}`}>
                      {e.confirmed ? 'Confirmada' : 'Sin confirmar'}
                    </span>
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

// ── Unresolved entities tab ──────────────────────────────────────────────────

function EntityResolutionCard({ item, onDone }) {
  const [mode, setMode] = useState(null)
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
  const [suggesting, setSuggesting] = useState(false)
  const [suggestResult, setSuggestResult] = useState(null)
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['unresolved', 'pending', page],
    queryFn: () => listUnresolved({ status: 'pending', page, page_size: PAGE_SIZE }),
  })

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['unresolved'] })
    qc.invalidateQueries({ queryKey: ['inbox-badge-emails'] })
  }

  const handleSuggestAI = async () => {
    setSuggesting(true)
    setSuggestResult(null)
    try {
      const result = await suggestEntitiesAI()
      setSuggestResult(result)
      qc.invalidateQueries({ queryKey: ['unresolved'] })
      qc.invalidateQueries({ queryKey: ['transactions-review'] })
    } finally {
      setSuggesting(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          {suggestResult && (
            <p className="text-sm text-blue-600">◈ {suggestResult.suggested} entidades asignadas de {suggestResult.checked} sin entidad</p>
          )}
        </div>
        <button
          onClick={handleSuggestAI}
          disabled={suggesting}
          title="Pide a la IA que asocie una entidad a las transacciones sin entidad resuelta"
          className="btn-ghost text-sm border border-blue-300 text-blue-600 hover:bg-blue-50 disabled:opacity-50"
        >
          {suggesting ? 'Consultando IA…' : '◈ Sugerir con IA'}
        </button>
      </div>

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

// ── Entity rules tab ─────────────────────────────────────────────────────────

function EntityRulesTab({ isAdmin }) {
  const [showNew, setShowNew] = useState(false)
  const [editRule, setEditRule] = useState(null)
  const [reapplying, setReapplying] = useState(false)
  const [reapplyResult, setReapplyResult] = useState(null)
  const qc = useQueryClient()

  const { data: rules } = useQuery({ queryKey: ['entity-rules'], queryFn: listEntityRules })
  const { data: entities } = useQuery({
    queryKey: ['entities-all'],
    queryFn: () => listEntities({ page_size: 200 }),
  })

  const entityMap = Object.fromEntries((entities?.items ?? []).map((e) => [e.id, e]))

  const handleDelete = async (id) => {
    await deleteEntityRule(id)
    qc.invalidateQueries({ queryKey: ['entity-rules'] })
  }

  const handleReapply = async () => {
    setReapplying(true)
    setReapplyResult(null)
    try {
      const r = await reapplyEntityRules()
      setReapplyResult(r)
      qc.invalidateQueries({ queryKey: ['transactions-review'] })
    } finally {
      setReapplying(false)
    }
  }

  const onSaved = () => {
    qc.invalidateQueries({ queryKey: ['entity-rules'] })
    setShowNew(false)
    setEditRule(null)
  }

  return (
    <div className="space-y-4">
      {(showNew || editRule) && (
        <EntityRuleModal
          rule={editRule}
          entities={entities}
          onClose={() => { setShowNew(false); setEditRule(null) }}
          onSaved={onSaved}
        />
      )}

      <div className="flex items-center justify-between gap-3">
        <div>
          {reapplyResult && (
            <p className="text-sm text-green-700">
              ✓ {reapplyResult.applied} entidades asignadas de {reapplyResult.checked} sin entidad
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleReapply}
            disabled={reapplying}
            title="Vuelve a correr todas las reglas de entidad sobre transacciones existentes"
            className="btn-ghost text-sm border border-brown-600/30 disabled:opacity-50"
          >
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
              <th className="table-header">Patrón</th>
              <th className="table-header">Entidad resultante</th>
              <th className="table-header w-20 text-center">Prioridad</th>
              <th className="table-header w-20">Fuente</th>
              {isAdmin && <th className="table-header w-16"></th>}
            </tr>
          </thead>
          <tbody>
            {!rules?.length && (
              <tr>
                <td colSpan={isAdmin ? 5 : 4} className="table-cell text-center text-ink/40 py-12">
                  <p className="text-3xl mb-2">◈</p>
                  Sin reglas de entidad. Crea una para identificar automáticamente quién envía o recibe dinero.
                </td>
              </tr>
            )}
            {rules?.map((rule) => {
              const entity = entityMap[rule.entity_id]
              return (
                <tr
                  key={rule.id}
                  className={`table-row ${isAdmin ? 'cursor-pointer' : ''}`}
                  onClick={isAdmin ? () => setEditRule(rule) : undefined}
                >
                  <td className="table-cell">
                    <span className="text-xs text-ink/60">
                      {matchTypeLabel[rule.match_type]?.toLowerCase()}{' '}
                      <code className="bg-[#F5EFE0] px-1.5 py-0.5 rounded text-ink/80 font-mono">
                        {rule.memo_pattern}
                      </code>
                    </span>
                  </td>
                  <td className="table-cell">
                    {entity ? (
                      <span className="badge bg-brown-600/15 text-brown-900">
                        {entity.display_name || entity.canonical_name}
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
                      {rule.source === 'user_confirmed' ? 'Manual' : 'IA'}
                    </span>
                  </td>
                  {isAdmin && (
                    <td className="table-cell" onClick={(e) => e.stopPropagation()}>
                      <div className="flex gap-2 justify-end">
                        <button
                          onClick={() => setEditRule(rule)}
                          className="text-ink/30 hover:text-amber-500 transition-colors text-xs"
                          title="Editar"
                        >✎</button>
                        <button
                          onClick={() => handleDelete(rule.id)}
                          className="text-red-400/60 hover:text-red-500 transition-colors text-xs"
                          title="Eliminar"
                        >✕</button>
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
          Las reglas se evalúan en orden de prioridad (mayor número = mayor prioridad).
          Una regla coincidente evita la consulta a la IA y asigna la entidad directamente.
        </p>
      )}
    </div>
  )
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function Entities() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = searchParams.get('tab') || 'entidades'
  const setTab = (id) => setSearchParams({ tab: id })
  const [selectedId, setSelectedId] = useState(null)

  const { data: rules } = useQuery({ queryKey: ['entity-rules'], queryFn: listEntityRules })
  const { data: unresolvedCount } = useQuery({
    queryKey: ['unresolved-count'],
    queryFn: () => listUnresolved({ status: 'pending', page: 1, page_size: 1 }),
    refetchInterval: 60_000,
    staleTime: 30_000,
  })

  const isAdmin = true

  const TABS = [
    { id: 'entidades', label: 'Entidades',
      desc: 'Catálogo de entidades conocidas: comercios, bancos, personas y fuentes de ingreso. Haz clic en una para ver sus patrones de reconocimiento.' },
    { id: 'sin-resolver', label: `Sin resolver${unresolvedCount?.total ? ` (${unresolvedCount.total})` : ''}`,
      desc: 'Nombres de remitente/destinatario que el sistema no pudo asociar a ninguna entidad. Resuélvelos para mejorar el reconocimiento futuro.' },
    { id: 'reglas', label: `Reglas${rules ? ` (${rules.length})` : ''}`,
      desc: 'Reglas de entidad que asignan automáticamente una entidad basándose en patrones del memo o la descripción de la transacción.' },
  ]

  return (
    <div className="space-y-4 max-w-4xl">
      {selectedId && <EntityDetail entityId={selectedId} onClose={() => setSelectedId(null)} />}

      <div>
        <h1 className="text-xl font-bold text-ink">Entidades</h1>
        <p className="text-sm text-ink/50 mt-0.5">¿Quién? Bancos, comercios, personas y fuentes de ingreso</p>
      </div>

      <div className="flex gap-1 border-b border-brown-600/20">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === t.id
                ? 'text-amber-500 border-amber-500'
                : 'text-ink/50 border-transparent hover:text-ink'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {TABS.find((t) => t.id === tab)?.desc && (
        <p className="text-xs text-ink/50">{TABS.find((t) => t.id === tab).desc}</p>
      )}

      {tab === 'entidades' && <EntitiesTab onSelect={setSelectedId} />}
      {tab === 'sin-resolver' && <UnresolvedTab />}
      {tab === 'reglas' && <EntityRulesTab isAdmin={isAdmin} />}
    </div>
  )
}
