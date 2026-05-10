import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import { listPersons, createPerson, updatePerson, deletePerson } from '../api/persons'
import { listUsers, createUser, updateUser, resetPassword } from '../api/users'
import { listCategories, createCategory, updateCategory } from '../api/categories'

function Section({ title, children }) {
  return (
    <div className="card space-y-4">
      <h2 className="text-sm font-semibold text-ink/60 uppercase tracking-wide">{title}</h2>
      {children}
    </div>
  )
}

// ── Category form ─────────────────────────────────────────────────────────────

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
        <input type="text" className="input w-44" value={name} onChange={(e) => setName(e.target.value)}
          placeholder="Nombre de categoría…" autoFocus required />
      </div>
      <div>
        <label className="block text-xs text-ink/50 mb-1">Color</label>
        <input type="color" className="h-9 w-12 rounded-lg border border-brown-600/40 cursor-pointer p-0.5 bg-white"
          value={color} onChange={(e) => setColor(e.target.value)} />
      </div>
      <div>
        <label className="block text-xs text-ink/50 mb-1">Ícono</label>
        <input type="text" className="input w-16 text-center" value={icon}
          onChange={(e) => setIcon(e.target.value)} placeholder="🍕" maxLength={4} />
      </div>
      {error && <p className="w-full text-xs text-red-500">{error}</p>}
      <button type="submit" disabled={saving || !name.trim()} className="btn-primary text-sm">
        {saving ? '…' : initial ? 'Guardar' : 'Crear'}
      </button>
      <button type="button" onClick={onCancel} className="btn-ghost text-sm">Cancelar</button>
    </form>
  )
}

// ── User modals ───────────────────────────────────────────────────────────────

function InviteUserModal({ persons, onClose, onSaved }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('member')
  const [personId, setPersonId] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSave = async () => {
    if (!email.trim() || !password) return
    setSaving(true)
    setError('')
    try {
      await createUser({ email: email.trim(), password, role, person_id: personId || null })
      onSaved()
    } catch (e) {
      setError(e.response?.data?.detail || 'Error al crear el usuario')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-ink">Invitar usuario</h2>
          <button onClick={onClose} className="text-ink/30 hover:text-ink text-xl leading-none">✕</button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-ink/60 mb-1">Correo electrónico</label>
            <input type="email" className="input text-sm" value={email}
              onChange={(e) => setEmail(e.target.value)} placeholder="usuario@ejemplo.com" autoFocus />
          </div>
          <div>
            <label className="block text-xs font-medium text-ink/60 mb-1">Contraseña temporal</label>
            <input type="text" className="input text-sm font-mono" value={password}
              onChange={(e) => setPassword(e.target.value)} placeholder="El usuario deberá cambiarla" />
          </div>
          <div>
            <label className="block text-xs font-medium text-ink/60 mb-1">Rol</label>
            <select className="select text-sm" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="member">Miembro</option>
              <option value="admin">Administrador</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-ink/60 mb-1">Miembro de la familia (opcional)</label>
            <select className="select text-sm" value={personId} onChange={(e) => setPersonId(e.target.value)}>
              <option value="">— Crear automáticamente —</option>
              {(persons || []).map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <p className="text-[10px] text-ink/40 mt-1">Si no seleccionas uno, se crea un miembro con el nombre del correo.</p>
          </div>
          <p className="text-xs text-amber-600 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
            No se envía ningún correo. Comparte la contraseña temporal con el usuario de forma directa (WhatsApp, en persona, etc.).
          </p>
        </div>

        {error && <p className="text-red-500 text-xs">{error}</p>}

        <div className="flex gap-2 pt-1">
          <button onClick={handleSave} disabled={saving || !email.trim() || !password} className="btn-primary text-sm flex-1">
            {saving ? 'Creando…' : 'Invitar'}
          </button>
          <button onClick={onClose} className="btn-ghost text-sm flex-1 border border-brown-600/30">Cancelar</button>
        </div>
      </div>
    </div>
  )
}

function EditUserModal({ targetUser, persons, currentUserId, onClose, onSaved }) {
  const [role, setRole] = useState(targetUser.role)
  const [personId, setPersonId] = useState(targetUser.person_id || '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const isSelf = targetUser.id === currentUserId

  const handleSave = async () => {
    setSaving(true)
    setError('')
    try {
      await updateUser(targetUser.id, { role, person_id: personId || null })
      onSaved()
    } catch (e) {
      setError(e.response?.data?.detail || 'Error al actualizar')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-ink">Editar usuario</h2>
          <button onClick={onClose} className="text-ink/30 hover:text-ink text-xl leading-none">✕</button>
        </div>

        <p className="text-sm text-ink/60 font-mono bg-[#F5EFE0] rounded px-3 py-2">{targetUser.email}</p>

        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-ink/60 mb-1">Rol</label>
            <select className="select text-sm" value={role} onChange={(e) => setRole(e.target.value)} disabled={isSelf}>
              <option value="member">Miembro</option>
              <option value="admin">Administrador</option>
            </select>
            {isSelf && <p className="text-[10px] text-ink/40 mt-1">No puedes cambiar tu propio rol.</p>}
          </div>
          <div>
            <label className="block text-xs font-medium text-ink/60 mb-1">Miembro de la familia</label>
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
          <button onClick={onClose} className="btn-ghost text-sm flex-1 border border-brown-600/30">Cancelar</button>
        </div>
      </div>
    </div>
  )
}

function ResetPasswordModal({ targetUser, onClose, onSaved }) {
  const [password, setPassword] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSave = async () => {
    if (!password) return
    setSaving(true)
    setError('')
    try {
      await resetPassword(targetUser.id, password)
      onSaved()
    } catch (e) {
      setError(e.response?.data?.detail || 'Error al restablecer')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-ink">Restablecer contraseña</h2>
          <button onClick={onClose} className="text-ink/30 hover:text-ink text-xl leading-none">✕</button>
        </div>

        <p className="text-sm text-ink/60">
          Se asignará una contraseña temporal a <span className="font-medium text-ink">{targetUser.email}</span>.
          El usuario deberá cambiarla al iniciar sesión.
        </p>

        <div>
          <label className="block text-xs font-medium text-ink/60 mb-1">Nueva contraseña temporal</label>
          <input type="text" className="input text-sm font-mono" value={password}
            onChange={(e) => setPassword(e.target.value)} placeholder="mínimo 8 caracteres" autoFocus />
        </div>

        {error && <p className="text-red-500 text-xs">{error}</p>}

        <div className="flex gap-2 pt-1">
          <button onClick={handleSave} disabled={saving || !password} className="btn-primary text-sm flex-1">
            {saving ? 'Guardando…' : 'Restablecer'}
          </button>
          <button onClick={onClose} className="btn-ghost text-sm flex-1 border border-brown-600/30">Cancelar</button>
        </div>
      </div>
    </div>
  )
}

// ── Main Settings ─────────────────────────────────────────────────────────────

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
    queryFn: listUsers,
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

  // ── User modal state ────────────────────────────────────────────────────────
  const [userModal, setUserModal] = useState(null) // null | 'invite' | { mode: 'edit'|'reset', user }

  const refreshUsers = () => {
    qc.invalidateQueries({ queryKey: ['users'] })
    qc.invalidateQueries({ queryKey: ['persons'] })
    setUserModal(null)
  }

  // ── Personas state ──────────────────────────────────────────────────────────
  const { data: persons } = useQuery({
    queryKey: ['persons'],
    queryFn: listPersons,
    enabled: isAdmin,
  })
  const [editingPerson, setEditingPerson] = useState(null)
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

  const [deleteConflict, setDeleteConflict] = useState(null)

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

  const personMap = Object.fromEntries((persons || []).map((p) => [p.id, p]))

  // ── Categories state ────────────────────────────────────────────────────────
  const { data: categories } = useQuery({ queryKey: ['categories'], queryFn: listCategories })
  const [showNewCat, setShowNewCat] = useState(false)
  const [editCatId, setEditCatId] = useState(null)

  const handleCreateCat = async (data) => {
    await createCategory(data)
    qc.invalidateQueries({ queryKey: ['categories'] })
    setShowNewCat(false)
  }

  const handleUpdateCat = async (id, data) => {
    await updateCategory(id, data)
    qc.invalidateQueries({ queryKey: ['categories'] })
    setEditCatId(null)
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
            <button onClick={handleSaveProvider} className="btn-primary text-sm shrink-0">Guardar</button>
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

      <Section title="Categorías">
        {isAdmin && (
          <div className="flex justify-end">
            {!showNewCat && (
              <button onClick={() => setShowNewCat(true)} className="btn-primary text-sm">
                + Nueva categoría
              </button>
            )}
          </div>
        )}

        {showNewCat && (
          <div>
            <CategoryForm onSave={handleCreateCat} onCancel={() => setShowNewCat(false)} />
          </div>
        )}

        <div className="overflow-hidden rounded-lg border border-brown-600/15">
          <table className="w-full">
            <thead className="bg-[#F5EFE0]/60 border-b border-brown-600/15">
              <tr>
                <th className="table-header w-10 text-center">Color</th>
                <th className="table-header">Nombre</th>
                <th className="table-header w-16 text-center">Ícono</th>
                <th className="table-header w-24">Estado</th>
                {isAdmin && <th className="table-header w-20"></th>}
              </tr>
            </thead>
            <tbody>
              {!categories?.length && (
                <tr>
                  <td colSpan={isAdmin ? 5 : 4} className="table-cell text-center text-ink/40 py-8">
                    Sin categorías.
                  </td>
                </tr>
              )}
              {categories?.map((cat) => (
                <tr key={cat.id} className="table-row">
                  <td className="table-cell">
                    <div className="w-5 h-5 rounded-full mx-auto border border-brown-600/20"
                      style={{ background: cat.color ?? '#C99828' }} />
                  </td>
                  <td className="table-cell">
                    {editCatId === cat.id ? (
                      <CategoryForm initial={cat}
                        onSave={(data) => handleUpdateCat(cat.id, data)}
                        onCancel={() => setEditCatId(null)} />
                    ) : (
                      <span className="font-medium text-ink text-sm">{cat.name}</span>
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
                      {!cat.is_system && editCatId !== cat.id && (
                        <button onClick={() => { setEditCatId(cat.id); setShowNewCat(false) }}
                          className="text-xs text-ink/40 hover:text-amber-500 transition-colors">
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
      </Section>

      {isAdmin && (
        <Section title="Usuarios">
          <div className="space-y-2">
            {(users || []).map((u) => (
              <div key={u.id} className="flex items-center justify-between bg-[#F5EFE0] rounded-lg px-4 py-3">
                <div>
                  <p className="text-sm text-ink font-medium">{u.email}</p>
                  <p className="text-xs text-ink/40">
                    <span className="capitalize">{u.role === 'admin' ? 'Administrador' : 'Miembro'}</span>
                    {u.person_id && personMap[u.person_id] ? ` · ${personMap[u.person_id].name}` : ''}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {u.must_change_password && (
                    <span className="badge bg-amber-500/20 text-amber-500 text-[10px]">Debe cambiar clave</span>
                  )}
                  <button
                    onClick={() => setUserModal({ mode: 'edit', user: u })}
                    className="text-xs text-ink/30 hover:text-amber-500 transition-colors"
                  >
                    ✎ Editar
                  </button>
                  <button
                    onClick={() => setUserModal({ mode: 'reset', user: u })}
                    className="text-xs text-ink/30 hover:text-red-500 transition-colors"
                  >
                    ↺ Clave
                  </button>
                </div>
              </div>
            ))}
          </div>
          <button onClick={() => setUserModal('invite')} className="btn-ghost text-sm border border-brown-600/30 w-full">
            + Invitar usuario
          </button>
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
                <div className="flex gap-3 shrink-0">
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
                    <>
                      <button onClick={() => openEditPerson(p)} className="text-xs text-ink/30 hover:text-amber-500 transition-colors">
                        ✎ Editar
                      </button>
                      <button onClick={() => handleDeletePerson(p)} className="text-xs text-ink/30 hover:text-red-500 transition-colors">
                        🗑 Eliminar
                      </button>
                    </>
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

      {/* ── Modals ── */}
      {userModal === 'invite' && (
        <InviteUserModal persons={persons} onClose={() => setUserModal(null)} onSaved={refreshUsers} />
      )}
      {userModal?.mode === 'edit' && (
        <EditUserModal
          targetUser={userModal.user}
          persons={persons}
          currentUserId={user?.id}
          onClose={() => setUserModal(null)}
          onSaved={refreshUsers}
        />
      )}
      {userModal?.mode === 'reset' && (
        <ResetPasswordModal targetUser={userModal.user} onClose={() => setUserModal(null)} onSaved={refreshUsers} />
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
            <button onClick={() => setDeleteConflict(null)} className="btn-primary text-sm w-full">Entendido</button>
          </div>
        </div>
      )}
    </div>
  )
}
