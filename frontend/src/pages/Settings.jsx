import { useState } from 'react'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import { listPersons, createPerson, updatePerson, deletePerson } from '../api/persons'

function Section({ title, children }) {
  return (
    <div className="card space-y-4">
      <h2 className="text-sm font-semibold text-ink/60 uppercase tracking-wide">{title}</h2>
      {children}
    </div>
  )
}

export default function Settings() {
  const { user } = useAuth()
  const qc = useQueryClient()
  const isAdmin = user?.role === 'admin'

  const { data: settings } = useQuery({
    queryKey: ['settings'],
    queryFn: () => client.get('/settings').then((r) => r.data),
  })

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: () => client.get('/users').then((r) => r.data),
    enabled: isAdmin,
  })

  const [aiProvider, setAiProvider] = useState('')
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(false)

  const handleTestAI = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const r = await client.post('/settings/test-ai')
      setTestResult({ ok: true, message: r.data.message || 'Proveedor funcionando correctamente' })
    } catch (err) {
      setTestResult({ ok: false, message: err.response?.data?.detail || 'Error al probar el proveedor' })
    } finally {
      setTesting(false)
    }
  }

  const handleSaveProvider = async () => {
    await client.put('/settings/ai_provider', { value: aiProvider || settings?.ai_provider })
    qc.invalidateQueries({ queryKey: ['settings'] })
  }

  const currentProvider = settings?.ai_provider || 'gemini'

  // ── Personas state ──────────────────────────────────────────────────────────
  const { data: persons } = useQuery({
    queryKey: ['persons'],
    queryFn: listPersons,
    enabled: isAdmin,
  })
  const [editingPerson, setEditingPerson] = useState(null) // null | { id, name } | 'new'
  const [personName, setPersonName] = useState('')
  const [personSaving, setPersonSaving] = useState(false)

  const openNewPerson = () => { setEditingPerson('new'); setPersonName('') }
  const openEditPerson = (p) => { setEditingPerson(p); setPersonName(p.name) }
  const cancelPerson = () => { setEditingPerson(null); setPersonName('') }

  const savePerson = async () => {
    if (!personName.trim()) return
    setPersonSaving(true)
    try {
      if (editingPerson === 'new') {
        await createPerson({ name: personName.trim() })
      } else {
        await updatePerson(editingPerson.id, { name: personName.trim() })
      }
      qc.invalidateQueries({ queryKey: ['persons'] })
      cancelPerson()
    } finally {
      setPersonSaving(false)
    }
  }

  const [deleteConflict, setDeleteConflict] = useState(null) // null | { name, accounts, users }

  const handleDeletePerson = async (p) => {
    try {
      await deletePerson(p.id)
      qc.invalidateQueries({ queryKey: ['persons'] })
    } catch (e) {
      if (e.response?.status === 409) {
        setDeleteConflict({ name: p.name, ...e.response.data.detail })
      }
    }
  }

  return (
    <div className="space-y-5 max-w-2xl">
      <div>
        <h1 className="text-xl font-bold text-ink">Configuración</h1>
        <p className="text-sm text-ink/50 mt-0.5">Ajustes del sistema MY Finanzas</p>
      </div>

      <Section title="Proveedor de IA">
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="block text-xs text-ink/50 mb-1.5">Proveedor activo</label>
            <select
              className="select"
              value={aiProvider || currentProvider}
              onChange={(e) => setAiProvider(e.target.value)}
              disabled={!isAdmin}
            >
              <option value="gemini">Gemini (Google)</option>
              <option value="claude">Claude (Anthropic)</option>
              <option value="lmstudio">LM Studio (local)</option>
            </select>
          </div>
          {isAdmin && (
            <button onClick={handleSaveProvider} className="btn-primary text-sm shrink-0">
              Guardar
            </button>
          )}
        </div>

        <div className="flex gap-3 items-center">
          <button onClick={handleTestAI} disabled={testing} className="btn-ghost text-sm border border-brown-600/30">
            {testing ? 'Probando…' : '↻ Probar conexión'}
          </button>
          {testResult && (
            <p className={`text-sm ${testResult.ok ? 'text-green-600' : 'text-red-500'}`}>
              {testResult.ok ? '✓' : '✕'} {testResult.message}
            </p>
          )}
        </div>
      </Section>

      {isAdmin && (
        <Section title="Usuarios">
          <div className="space-y-2">
            {users?.map((u) => (
              <div key={u.id} className="flex items-center justify-between bg-[#F5EFE0] rounded-lg px-4 py-3">
                <div>
                  <p className="text-sm text-ink">{u.email}</p>
                  <p className="text-xs text-ink/40 capitalize">{u.role}</p>
                </div>
                <div className="flex items-center gap-2">
                  {u.must_change_password && (
                    <span className="badge bg-amber-500/20 text-amber-500 text-[10px]">Debe cambiar clave</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {isAdmin && (
        <Section title="Miembros de la familia">
          <div className="space-y-2">
            {(persons || []).map((p) => (
              <div key={p.id} className="flex items-center justify-between bg-[#F5EFE0] rounded-lg px-4 py-3">
                {editingPerson?.id === p.id ? (
                  <input
                    className="input text-sm flex-1 mr-3"
                    value={personName}
                    onChange={(e) => setPersonName(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') savePerson(); if (e.key === 'Escape') cancelPerson() }}
                    autoFocus
                  />
                ) : (
                  <p className="text-sm text-ink">{p.name}</p>
                )}
                <div className="flex gap-2 shrink-0">
                  {editingPerson?.id === p.id ? (
                    <>
                      <button onClick={savePerson} disabled={personSaving || !personName.trim()} className="btn-primary text-xs py-1 px-3">
                        {personSaving ? '…' : 'Guardar'}
                      </button>
                      <button onClick={cancelPerson} className="btn-ghost text-xs py-1 px-3 border border-brown-600/30">
                        Cancelar
                      </button>
                    </>
                  ) : (
                    <div className="flex gap-3">
                      <button onClick={() => openEditPerson(p)} className="text-xs text-ink/30 hover:text-amber-500 transition-colors">
                        ✎ Editar
                      </button>
                      <button onClick={() => handleDeletePerson(p)} className="text-xs text-ink/30 hover:text-red-500 transition-colors">
                        🗑 Eliminar
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {editingPerson === 'new' ? (
              <div className="flex items-center gap-2 bg-[#F5EFE0] rounded-lg px-4 py-3">
                <input
                  className="input text-sm flex-1"
                  placeholder="Nombre del miembro…"
                  value={personName}
                  onChange={(e) => setPersonName(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') savePerson(); if (e.key === 'Escape') cancelPerson() }}
                  autoFocus
                />
                <button onClick={savePerson} disabled={personSaving || !personName.trim()} className="btn-primary text-xs py-1 px-3 shrink-0">
                  {personSaving ? '…' : 'Agregar'}
                </button>
                <button onClick={cancelPerson} className="btn-ghost text-xs py-1 px-3 border border-brown-600/30 shrink-0">
                  Cancelar
                </button>
              </div>
            ) : (
              <button onClick={openNewPerson} className="btn-ghost text-sm border border-brown-600/30 w-full">
                + Agregar miembro
              </button>
            )}
          </div>
        </Section>
      )}

      {deleteConflict && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4">
            <h2 className="text-base font-semibold text-ink">No se puede eliminar a {deleteConflict.name}</h2>
            <p className="text-sm text-ink/60">Tiene los siguientes recursos asignados. Reasígnalos primero.</p>

            {deleteConflict.accounts?.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-ink/50 uppercase tracking-wide mb-1.5">Cuentas</p>
                <ul className="space-y-1">
                  {deleteConflict.accounts.map((a) => (
                    <li key={a.id} className="flex items-center gap-2 text-sm text-ink bg-[#F5EFE0] rounded px-3 py-2">
                      <span className="font-medium">{a.label}</span>
                      <span className="text-xs text-ink/40">{a.currency}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {deleteConflict.users?.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-ink/50 uppercase tracking-wide mb-1.5">Usuario vinculado</p>
                <ul className="space-y-1">
                  {deleteConflict.users.map((u) => (
                    <li key={u.id} className="text-sm text-ink bg-[#F5EFE0] rounded px-3 py-2">{u.email}</li>
                  ))}
                </ul>
              </div>
            )}

            <button onClick={() => setDeleteConflict(null)} className="btn-primary text-sm w-full">
              Entendido
            </button>
          </div>
        </div>
      )}

      <Section title="Acerca de">
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-ink/50">Versión</dt>
            <dd className="text-ink">1.0.0</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-ink/50">Hostname</dt>
            <dd className="text-ink font-mono">finanzas.internal</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-ink/50">Usuario</dt>
            <dd className="text-ink">{user?.email}</dd>
          </div>
        </dl>
      </Section>
    </div>
  )
}
