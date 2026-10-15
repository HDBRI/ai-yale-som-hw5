// Left rail: the tickets, pinned like order stubs on a kitchen spike.
import type { ApprovalItem, Ticket } from '../types'

const TYPE_ICON: Record<string, string> = { customer_order: '🛍️', rent_notice: '🔑', price_override: '🏷️' }
const TYPE_LABEL: Record<string, string> = { customer_order: 'Customer order', rent_notice: 'Rent notice', price_override: 'Price override' }

interface Props {
  tickets: Ticket[]
  selectedId: number | null
  approvals: ApprovalItem[]
  onSelect: (id: number) => void
}

export function TicketSpike({ tickets, selectedId, approvals, onSelect }: Props) {
  return (
    <aside className="spike">
      <div className="rail-title"><span className="pin" />Ticket spike</div>
      {tickets.map((t, i) => {
        const waiting = approvals.filter(a => a.ticket_id === t.id && a.status === 'pending').length
        return (
          <button
            key={t.id}
            className={`stub ${t.state} ${selectedId === t.id ? 'selected' : ''} ${t.running ? 'running' : ''}`}
            style={{ ['--tilt' as string]: `${(i % 2 ? 1 : -1) * 1.2}deg` }}
            onClick={() => onSelect(t.id)}
          >
            <div className="stub-top">
              <span className="stub-id">#{t.id}</span>
              <span className="stub-type">{TYPE_ICON[t.type] ?? '📌'} {TYPE_LABEL[t.type] ?? t.type}</span>
            </div>
            <div className="stub-subject">{t.subject}</div>
            <div className="stub-from">from {t.requester}</div>
            {t.sku && <div className="stub-line">{t.qty} × {t.sku} · size {t.size}</div>}
            <div className="stub-foot">
              <span className={`pill st-${t.status}`}>{t.running ? 'team working…' : t.status.replace('_', ' ')}</span>
              {waiting > 0 && <span className="pill needs">✍️ {waiting} to sign</span>}
            </div>
            {t.state === 'resolved' && <div className="stamp">RESOLVED</div>}
          </button>
        )
      })}
    </aside>
  )
}
