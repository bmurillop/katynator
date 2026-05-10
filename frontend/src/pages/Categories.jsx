import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { listCategories, createCategory, updateCategory } from '../api/categories'
import { listRules, createRule, deleteRule } from '../api/categoryRules'
import { listEntities } from '../api/entities'
import { useAuth } from '../context/AuthContext'

const matchTypeLabel = { any: 'Cualquier', contains: 'Contiene', starts_with: 'Empieza con', exact: 'Exacto', regex: 'Regex' }
const sourceLabel = { user_confirmed: 'Manual', ai_suggested: 'IA' }

// ── Category inline form ─────────────────────────────────────────────────────

function CategoryForm({ initial, onSave, onCancel }) {
  const [name, setName] = useState(initial?.name ?? '')
  const [color, setColor] = useState(initial?.color ?? '#C99828')
  const [icon, setIcon] = useState(initial?.icon ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!name.trim()) return
    setSaving(true)
    setError('')
    try {
      await onSave({ name: name.trim(), color: color || null, icon: icon.trim() || null })
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap gap-3 items-end">
      <div>
        <label className="block text-xs text-ink/50 mb-1">Nombre</label>
        <input
          type="text"
          className="input w-44"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Nombre de categoría…"
          autoFocus
          required
        />
      </div>
      <div>
        <label className="block text-xs text-ink/50 mb-1">Color</label>
        <input
          type="color"
          className="h-9 w-12 rounded-lg border border-brown-600/40 cursor-pointer p-0.5 bg-white"
          value={color}
          onChange={(e) => setColor(e.target.value)}
        />
      </div>
      <div>
        <label className="block text-xs text-ink/50 mb-1">Ícono</label>
        <input
          type="text"
          className="input w-16 text-center"
          value={icon}
          onChange={(e) => setIcon(e.target.value)}
          placeholder="🍕"
          maxLength={4}
        />
      </div>
      {error && <p className="w-full text-xs text-red-500">{error}</p>}
      <button type="submit" disabled={saving || !name.trim()} className="btn-primary text-sm">
        {saving ? '…' : initial ? 'Guardar' : 'Crear'}
      </button>
      <button type="button" onClick={onCancel} className="btn-ghost text-sm">Cancelar</button>
    </form>
  )
}

// ── New rule modal ───────────────────────────────────────────────────────────

function NewRuleModal({ categories, entities, onClose, onSaved }) {
  const [entityId, setEntityId] = useState('')
  const [memoPattern, setMemoPattern] = useState('')
  const [matchType, setMatchType] = useState('contains')
  const [categoryId, setCategoryId] = useState('')
  const [priority, setPriority] = useState(50)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const canSave = categoryId && (entityId || memoPattern.trim())

  const handleSave = async () => {
    if (!canSave) return
    setSaving(true)
    setError('')
    try {
      await createRule({
        entity_id: entityId || undefined,
        memo_pattern: memoPattern.trim() || undefined,
        match_type: matchType,
        category_id: categoryId,
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

        <div className="px-5 py-4 space-y-3">
          <div>
            <label className="block text-xs text-ink/50 mb-1">Entidad (opcional)</label>
            <select className="select" value={entityId} onChange={(e) => setEntityId(e.target.value)}>
              <option value="">— Cualquier entidad —</option>
              {entities?.items?.map((e) => (
                <option key={e.id} value={e.id}>{e.canonical_name}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-ink/50 mb-1">Patrón del memo (opcional)</label>
              <input
                type="text"
                className="input"
                placeholder="supermercado…"
                value={memoPattern}
                onChange={(e) => setMemoPattern(e.target.value)}
              />
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
              <label className="block text-xs text-ink/50 mb-1">Categoría *</label>
              <select className="select" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
                <option value="">— Seleccionar —</option>
                {categories?.map((c) => (
                  <option key={c.id} value={c.id}>{c.icon ? `${c.icon} ` : ''}{c.name}</option>
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

          {error && (
            <p className="text-red-500 text-xs bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>
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

// ── Main page ────────────────────────────────────────────────────────────────

export default function Categories() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [tab, setTab] = useState('categorias')
  const [showNewCat, setShowNewCat] = useState(false)
  const [editId, setEditId] = useState(null)
  const [showNewRule, setShowNewRule] = useState(false)
  const qc = useQueryClient()

  const { data: categories } = useQuery({ queryKey: ['categories'], queryFn: listCategories })
  const { data: rules } = useQuery({ queryKey: ['rules'], queryFn: listRules })
  const { data: entities } = useQuery({
    queryKey: ['entities-all'],
    queryFn: () => listEntities({ page_size: 200 }),
    enabled: tab === 'reglas' || showNewRule,
  })

  const entityMap = Object.fromEntries((entities?.items ?? []).map((e) => [e.id, e]))
  const catMap = Object.fromEntries((categories ?? []).map((c) => [c.id, c]))

  const handleCreateCat = async (data) => {
    await createCategory(data)
    qc.invalidateQueries({ queryKey: ['categories'] })
    setShowNewCat(false)
  }

  const handleUpdateCat = async (id, data) => {
    await updateCategory(id, data)
    qc.invalidateQueries({ queryKey: ['categories'] })
    setEditId(null)
  }

  const handleDeleteRule = async (id) => {
    await deleteRule(id)
    qc.invalidateQueries({ queryKey: ['rules'] })
  }

  const TABS = [
    { id: 'categorias', label: `Categorías${categories ? ` (${categories.length})` : ''}` },
    { id: 'reglas', label: `Reglas${rules ? ` (${rules.length})` : ''}` },
  ]

  return (
    <div className="space-y-4 max-w-4xl">
      {showNewRule && (
        <NewRuleModal
          categories={categories}
          entities={entities}
          onClose={() => setShowNewRule(false)}
          onSaved={() => { qc.invalidateQueries({ queryKey: ['rules'] }); setShowNewRule(false) }}
        />
      )}

      <div>
        <h1 className="text-xl font-bold text-ink">Categorías y Reglas</h1>
        <p className="text-sm text-ink/50 mt-0.5">Organización y clasificación automática de transacciones</p>
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

      {/* ── Categorías ─────────────────────────────────────────────────────── */}
      {tab === 'categorias' && (
        <div className="space-y-4">
          {isAdmin && (
            <div className="flex justify-end">
              {showNewCat ? null : (
                <button onClick={() => setShowNewCat(true)} className="btn-primary text-sm">
                  + Nueva categoría
                </button>
              )}
            </div>
          )}

          {showNewCat && (
            <div className="card">
              <p className="text-xs font-semibold text-ink/50 uppercase tracking-wide mb-3">Nueva categoría</p>
              <CategoryForm onSave={handleCreateCat} onCancel={() => setShowNewCat(false)} />
            </div>
          )}

          <div className="card p-0 overflow-hidden">
            <table className="w-full">
              <thead className="border-b border-brown-600/20">
                <tr>
                  <th className="table-header w-12 text-center">Color</th>
                  <th className="table-header">Nombre</th>
                  <th className="table-header w-20 text-center">Ícono</th>
                  <th className="table-header w-28">Estado</th>
                  {isAdmin && <th className="table-header w-20"></th>}
                </tr>
              </thead>
              <tbody>
                {!categories?.length && (
                  <tr>
                    <td colSpan={isAdmin ? 5 : 4} className="table-cell text-center text-ink/40 py-12">
                      Sin categorías. Crea la primera.
                    </td>
                  </tr>
                )}
                {categories?.map((cat) => (
                  <tr key={cat.id} className="table-row">
                    <td className="table-cell">
                      <div
                        className="w-5 h-5 rounded-full mx-auto border border-brown-600/20"
                        style={{ background: cat.color ?? '#C99828' }}
                      />
                    </td>
                    <td className="table-cell">
                      {editId === cat.id ? (
                        <CategoryForm
                          initial={cat}
                          onSave={(data) => handleUpdateCat(cat.id, data)}
                          onCancel={() => setEditId(null)}
                        />
                      ) : (
                        <span className="font-medium text-ink">{cat.name}</span>
                      )}
                    </td>
                    <td className="table-cell text-center text-lg">{cat.icon || '—'}</td>
                    <td className="table-cell">
                      {cat.is_system && (
                        <span className="badge bg-brown-600/15 text-brown-900 text-[10px]">Sistema</span>
                      )}
                    </td>
                    {isAdmin && (
                      <td className="table-cell">
                        {!cat.is_system && editId !== cat.id && (
                          <button
                            onClick={() => { setEditId(cat.id); setShowNewCat(false) }}
                            className="text-xs text-ink/40 hover:text-amber-500 transition-colors"
                          >
                            ✎ Editar
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Reglas ─────────────────────────────────────────────────────────── */}
      {tab === 'reglas' && (
        <div className="space-y-4">
          {isAdmin && (
            <div className="flex justify-end">
              <button onClick={() => setShowNewRule(true)} className="btn-primary text-sm">
                + Nueva regla
              </button>
            </div>
          )}

          <div className="card p-0 overflow-hidden">
            <table className="w-full">
              <thead className="border-b border-brown-600/20">
                <tr>
                  <th className="table-header">Condición</th>
                  <th className="table-header">Categoría</th>
                  <th className="table-header w-24 text-center">Prioridad</th>
                  <th className="table-header w-24">Fuente</th>
                  {isAdmin && <th className="table-header w-10"></th>}
                </tr>
              </thead>
              <tbody>
                {!rules?.length && (
                  <tr>
                    <td colSpan={isAdmin ? 5 : 4} className="table-cell text-center text-ink/40 py-12">
                      <p className="text-3xl mb-2">⊞</p>
                      Sin reglas definidas. Las reglas que creas en Transacciones aparecen aquí.
                    </td>
                  </tr>
                )}
                {rules?.map((rule) => {
                  const entity = rule.entity_id ? entityMap[rule.entity_id] : null
                  const cat = catMap[rule.category_id]
                  return (
                    <tr key={rule.id} className="table-row">
                      <td className="table-cell">
                        <div className="flex flex-wrap items-center gap-1.5">
                          {entity && (
                            <span className="badge bg-brown-600/15 text-brown-900">
                              {entity.canonical_name}
                            </span>
                          )}
                          {rule.memo_pattern && (
                            <span className="text-xs text-ink/60">
                              {matchTypeLabel[rule.match_type].toLowerCase()}{' '}
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
                        {cat ? (
                          <span
                            className="badge"
                            style={{
                              background: (cat.color ?? '#C99828') + '25',
                              color: cat.color ?? '#C99828',
                              border: `1px solid ${cat.color ?? '#C99828'}40`,
                            }}
                          >
                            {cat.icon && <span className="mr-1">{cat.icon}</span>}
                            {cat.name}
                          </span>
                        ) : (
                          <span className="text-xs text-ink/30">—</span>
                        )}
                      </td>
                      <td className="table-cell text-center text-ink/60 tabular-nums">
                        {rule.priority}
                      </td>
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
                        <td className="table-cell">
                          <button
                            onClick={() => handleDeleteRule(rule.id)}
                            className="text-red-400/60 hover:text-red-500 transition-colors"
                            title="Eliminar regla"
                          >
                            ✕
                          </button>
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
      )}
    </div>
  )
}
