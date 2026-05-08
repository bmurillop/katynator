import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { listEntities, getEntity, updateEntity, addPattern, deletePattern } from '../api/entities'
import Pagination from '../components/Pagination'

const typeLabel = {
  bank: 'Banco',
  merchant: 'Comercio',
  issuer: 'Emisor',
  person: 'Persona',
  income_source: 'Fuente de ingreso',
  other: 'Otro',
}

const PAGE_SIZE = 50

function EntityDetail({ entityId, onClose }) {
  const qc = useQueryClient()
  const { data: entity, isLoading } = useQuery({
    queryKey: ['entity', entityId],
    queryFn: () => getEntity(entityId),
  })

  // ── Edit state ──────────────────────────────────────────────────────────────
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

  const cancelEdit = () => setEditing(false)

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

  // ── Pattern state ───────────────────────────────────────────────────────────
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

            {/* ── Info / edit ── */}
            {editing ? (
              <div className="space-y-3 bg-[#F5EFE0] rounded-xl p-4">
                <div>
                  <label className="block text-xs font-medium text-ink/60 mb-1">Nombre canónico</label>
                  <input
                    type="text"
                    className="input text-sm"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-ink/60 mb-1">Nombre a mostrar (opcional)</label>
                  <input
                    type="text"
                    className="input text-sm"
                    value={editDisplay}
                    onChange={(e) => setEditDisplay(e.target.value)}
                    placeholder="Dejar vacío para usar el nombre canónico"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-ink/60 mb-1">Tipo</label>
                  <select className="select text-sm" value={editType} onChange={(e) => setEditType(e.target.value)}>
                    {Object.entries(typeLabel).map(([k, v]) => (
                      <option key={k} value={k}>{v}</option>
                    ))}
                  </select>
                </div>
                <div className="flex gap-2 pt-1">
                  <button onClick={saveEdit} disabled={saving || !editName.trim()} className="btn-primary text-xs py-1.5 px-4">
                    {saving ? '…' : 'Guardar'}
                  </button>
                  <button onClick={cancelEdit} className="btn-ghost text-xs py-1.5 px-4 border border-brown-600/30">
                    Cancelar
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  {entity.display_name && entity.display_name !== entity.canonical_name && (
                    <p className="text-xs text-ink/40">
                      Canónico: <span className="font-mono">{entity.canonical_name}</span>
                    </p>
                  )}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="badge bg-brown-600/15 text-brown-900">{typeLabel[entity.type] ?? entity.type}</span>
                    <span className={`badge ${entity.confirmed ? 'bg-green-800/20 text-green-700' : 'bg-amber-500/20 text-amber-500'}`}>
                      {entity.confirmed ? 'Confirmada' : 'Sin confirmar'}
                    </span>
                  </div>
                </div>
                <div className="flex gap-3 shrink-0 text-xs">
                  <button onClick={openEdit} className="text-ink/30 hover:text-amber-500 transition-colors">
                    ✎ Editar
                  </button>
                  <button onClick={handleConfirm} className="text-ink/30 hover:text-ink transition-colors">
                    {entity.confirmed ? 'Desconfirmar' : 'Confirmar'}
                  </button>
                </div>
              </div>
            )}

            {/* ── Patterns ── */}
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
                {!entity.patterns?.length && (
                  <p className="text-xs text-ink/30">Sin patrones registrados</p>
                )}
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  className="input text-sm"
                  placeholder="Agregar patrón…"
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

export default function Entities() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [selectedId, setSelectedId] = useState(null)

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
      {selectedId && <EntityDetail entityId={selectedId} onClose={() => setSelectedId(null)} />}

      <div>
        <h1 className="text-xl font-bold text-ink">Entidades</h1>
        <p className="text-sm text-ink/50 mt-0.5">{data?.total ?? 0} entidad{data?.total !== 1 ? 'es' : ''}</p>
      </div>

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
              {isLoading && (
                <tr><td colSpan={4} className="table-cell text-center text-ink/40 py-12">Cargando…</td></tr>
              )}
              {!isLoading && !data?.items?.length && (
                <tr><td colSpan={4} className="table-cell text-center text-ink/40 py-12">Sin entidades</td></tr>
              )}
              {data?.items?.map((e) => (
                <tr key={e.id} className="table-row cursor-pointer" onClick={() => setSelectedId(e.id)}>
                  <td className="table-cell font-medium text-ink">
                    {e.display_name || e.canonical_name}
                  </td>
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
