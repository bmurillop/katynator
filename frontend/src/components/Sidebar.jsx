import { NavLink, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import { listTransactions } from '../api/transactions'
import { listUnresolved } from '../api/unresolvedEntities'

const navItems = [
  { to: '/',              label: 'Panel',          icon: '▦', exact: true },
  { to: '/transacciones', label: 'Transacciones',  icon: '↕' },
  { to: '/cuentas',       label: 'Cuentas',        icon: '🏦' },
  { to: '/bandeja',       label: 'Bandeja',        icon: '⚑', badge: true },
  { to: '/entidades',     label: 'Entidades',      icon: '◈' },
  { to: '/categorias',    label: 'Categorías',     icon: '⊞' },
  { to: '/configuracion', label: 'Configuración',  icon: '⚙' },
]

function useInboxCount() {
  const { data: txns } = useQuery({
    queryKey: ['inbox-badge-txns'],
    queryFn: () => listTransactions({ needs_review: true, page: 1, page_size: 1 }),
    refetchInterval: 60_000,
    staleTime: 30_000,
  })
  const { data: unresolved } = useQuery({
    queryKey: ['inbox-badge-unresolved'],
    queryFn: () => listUnresolved({ status: 'pending', page: 1, page_size: 1 }),
    refetchInterval: 60_000,
    staleTime: 30_000,
  })
  return (txns?.total ?? 0) + (unresolved?.total ?? 0)
}

export default function Sidebar({ onClose }) {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const inboxCount = useInboxCount()

  const handleLogout = async () => {
    await signOut()
    navigate('/login')
  }

  return (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-brown-600/40">
        <div className="flex items-center justify-between">
          <span className="text-xl font-black tracking-tight">
            <span className="text-amber-500">MY</span>{' '}
            <span className="text-cream">Finanzas</span>
          </span>
          <button onClick={onClose} className="lg:hidden text-cream/50 hover:text-cream">
            ✕
          </button>
        </div>
        <p className="text-xs text-cream/40 mt-0.5">Tu gestor financiero familiar</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {navItems.map(({ to, label, icon, exact, badge }) => (
          <NavLink
            key={to}
            to={to}
            end={exact}
            onClick={onClose}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-amber-500/15 text-amber-500 border-l-2 border-amber-500 pl-[10px]'
                  : 'text-cream/70 hover:text-cream hover:bg-brown-600/30'
              }`
            }
          >
            <span className="w-5 text-center">{icon}</span>
            <span className="flex-1">{label}</span>
            {badge && inboxCount > 0 && (
              <span className="bg-amber-500 text-brown-900 text-[10px] font-bold rounded-full px-1.5 leading-5 min-w-[20px] text-center">
                {inboxCount > 99 ? '99+' : inboxCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User footer */}
      <div className="px-4 py-4 border-t border-brown-600/40">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-full bg-amber-500/20 flex items-center justify-center text-amber-500 font-bold text-sm uppercase">
            {user?.email?.[0]}
          </div>
          <div className="min-w-0">
            <p className="text-sm text-cream font-medium truncate">{user?.email}</p>
            <p className="text-xs text-cream/40 capitalize">{user?.role}</p>
          </div>
        </div>
        <button onClick={handleLogout} className="w-full btn-ghost text-sm text-left">
          Cerrar sesión
        </button>
      </div>
    </div>
  )
}
