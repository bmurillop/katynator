import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { changePassword, getMe } from '../api/auth'

export default function ChangePassword() {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { user, signOut, loadUser } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (next !== confirm) { setError('Las contraseñas no coinciden'); return }
    if (next.length < 8) { setError('La contraseña debe tener al menos 8 caracteres'); return }
    setLoading(true)
    try {
      await changePassword(current, next)
      await loadUser()
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al cambiar la contraseña')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-black tracking-tight">
            <span className="text-amber-500">MY</span>{' '}
            <span className="text-brown-900">Finanzas</span>
          </h1>
          <p className="text-ink/60 text-sm mt-2">Debes cambiar tu contraseña antes de continuar</p>
        </div>

        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-ink/60 mb-1.5">Contraseña actual</label>
              <input type="password" className="input" value={current} onChange={(e) => setCurrent(e.target.value)} required />
            </div>
            <div>
              <label className="block text-xs font-medium text-ink/60 mb-1.5">Nueva contraseña</label>
              <input type="password" className="input" value={next} onChange={(e) => setNext(e.target.value)} required />
            </div>
            <div>
              <label className="block text-xs font-medium text-ink/60 mb-1.5">Confirmar contraseña</label>
              <input type="password" className="input" value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
            </div>

            {error && (
              <p className="text-red-400 text-sm bg-red-900/20 border border-red-700/30 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
              {loading ? 'Guardando…' : 'Cambiar contraseña'}
            </button>
          </form>
        </div>

        <button onClick={() => signOut().then(() => navigate('/login'))} className="w-full text-center text-xs text-ink/30 hover:text-ink/60 mt-4">
          Cerrar sesión
        </button>
      </div>
    </div>
  )
}
