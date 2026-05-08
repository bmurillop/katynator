export default function Pagination({ page, pageSize, total, onPage }) {
  const totalPages = Math.ceil(total / pageSize)
  if (totalPages <= 1) return null

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-brown-600/20">
      <p className="text-xs text-ink/40">
        {((page - 1) * pageSize) + 1}–{Math.min(page * pageSize, total)} de {total}
      </p>
      <div className="flex gap-2">
        <button
          onClick={() => onPage(page - 1)}
          disabled={page === 1}
          className="btn-ghost text-sm py-1 px-3 disabled:opacity-30"
        >
          ← Anterior
        </button>
        <button
          onClick={() => onPage(page + 1)}
          disabled={page >= totalPages}
          className="btn-ghost text-sm py-1 px-3 disabled:opacity-30"
        >
          Siguiente →
        </button>
      </div>
    </div>
  )
}
