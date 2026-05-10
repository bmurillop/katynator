import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { listEmails, retryEmail, triggerPoll } from '../api/emails'
import Pagination from '../components/Pagination'

const PAGE_SIZE = 20

export default function Inbox() {
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
    <div className="space-y-4 max-w-2xl">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-ink">Bandeja</h1>
          <p className="text-sm text-ink/50 mt-0.5">Correos con errores de procesamiento</p>
        </div>
        <button onClick={poll} className="btn-ghost text-sm border border-brown-600/30 shrink-0">
          ↻ Sondear IMAP ahora
        </button>
      </div>

      {isLoading && <p className="text-ink/40 text-sm">Cargando…</p>}

      {!isLoading && !data?.items?.length && (
        <div className="card text-center py-16 text-ink/40">
          <p className="text-5xl mb-3">✉</p>
          <p className="text-sm">Sin correos fallidos. El sistema está procesando todo correctamente.</p>
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
